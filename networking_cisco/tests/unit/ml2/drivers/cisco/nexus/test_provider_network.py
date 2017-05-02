# Copyright (c) 2017 Cisco Systems, Inc.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock
from oslo_config import cfg

from neutron.tests import base

from networking_cisco import backwards_compatibility as bc
from networking_cisco.plugins.ml2.drivers.cisco.nexus import (
    exceptions as excep)
from networking_cisco.plugins.ml2.drivers.cisco.nexus import (
    nexus_restapi_network_driver as rest_driver)
from networking_cisco.plugins.ml2.drivers.cisco.nexus.extensions import (
    cisco_providernet)
from networking_cisco.plugins.ml2.drivers.cisco.nexus import mech_cisco_nexus
from networking_cisco.plugins.ml2.drivers.cisco.nexus import nexus_db_v2
from neutron.plugins.ml2 import driver_api as api
from neutron.tests.unit import testlib_api

NETWORK_ID = 'test_network_id'
VLAN_ID = 'test_vlan_id'
DEVICE_ID = 'test_device_id'
HOST_ID = 'test_host_id'
PVLAN_NAME_PREFIX = 'test_prefix_p'
VLAN_NAME_PREFIX = 'test_prefix'
IP_ADDR = 'test_ipaddr'
INTF_TYPE = 'test_intf_type'
NEXUS_PORT = 'test_nexus_port'
IS_NATIVE = True
NO_VNI = 0
NETWORK = {'id': NETWORK_ID,
           'is_provider_network': True,
           api.NETWORK_TYPE: 'vlan',
           api.SEGMENTATION_ID: VLAN_ID,
           bc.providernet.SEGMENTATION_ID: VLAN_ID}
PORT = {'device_id': DEVICE_ID,
        bc.portbindings.VNIC_TYPE: 'normal',
        bc.portbindings.HOST_ID: HOST_ID}


class TestCiscoNexusProvider(testlib_api.SqlTestCase):
    """Test the provider network code added to the cisco nexus MD."""

    def setUp(self):
        super(TestCiscoNexusProvider, self).setUp()
        self._nexus_md = mech_cisco_nexus.CiscoNexusMechanismDriver()
        self._nexus_md._get_port_uuid = mock.Mock(return_value='test_uuid')
        self._func = mock.Mock()
        self.context = mock.Mock()
        self.context.current = NETWORK

    def test_create_network(self):
        self._nexus_md.create_network_precommit(self.context)

        self.assertTrue(nexus_db_v2.is_provider_network(NETWORK_ID))
        self.assertTrue(nexus_db_v2.is_provider_vlan(VLAN_ID))

    def test_create_network_no_provider(self):
        NETWORK_NO_PROVIDER = NETWORK.copy()
        del NETWORK_NO_PROVIDER['is_provider_network']
        self.context.current = NETWORK_NO_PROVIDER
        self._nexus_md.create_network_precommit(self.context)

        self.assertFalse(nexus_db_v2.is_provider_network(NETWORK_ID))
        self.assertFalse(nexus_db_v2.is_provider_vlan(VLAN_ID))

    def test_create_network_false_provider(self):
        NETWORK_FALSE_PROVIDER = NETWORK.copy()
        NETWORK_FALSE_PROVIDER['is_provider_network'] = False
        self.context.current = NETWORK_FALSE_PROVIDER
        self._nexus_md.create_network_precommit(self.context)

        self.assertFalse(nexus_db_v2.is_provider_network(NETWORK_ID))
        self.assertFalse(nexus_db_v2.is_provider_vlan(VLAN_ID))

    def test_delete_network(self):
        self._nexus_md.create_network_precommit(self.context)
        self._nexus_md.delete_network_postcommit(self.context)

        self.assertFalse(nexus_db_v2.is_provider_network(NETWORK_ID))
        self.assertFalse(nexus_db_v2.is_provider_vlan(VLAN_ID))

    def test_delete_network_no_id(self):
        mock_subport_get_object = mock.patch.object(
            nexus_db_v2, 'delete_provider_network').start()
        self._nexus_md.delete_network_postcommit(self.context)

        self.assertFalse(mock_subport_get_object.call_count)

    def test_port_action_vlan_provider(self):
        self._nexus_md.create_network_precommit(self.context)
        self._nexus_md._port_action_vlan(PORT, NETWORK, self._func, 0)

        self._func.assert_called_once_with(
            mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, True)

    def test_port_action_vlan_no_provider(self):
        self._nexus_md._port_action_vlan(PORT, NETWORK, self._func, 0)

        self._func.assert_called_once_with(
            mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, False)


class TestCiscoNexusProviderExtension(base.BaseTestCase):
    """Test the provider network extension class used by the cisco nexus MD."""

    def setUp(self):
        super(TestCiscoNexusProviderExtension, self).setUp()
        self._context = mock.Mock()
        self._data = {}
        self._result = {}
        self._provider_net_driver = cisco_providernet.CiscoProviderNetDriver()

    def test_extension_alias(self):
        self.assertTrue(self._provider_net_driver.extension_alias ==
                        'provider')

    def test_create_network_vlan(self):
        self._data[bc.providernet.SEGMENTATION_ID] = VLAN_ID
        self._provider_net_driver.process_create_network(
            self._context, self._data, self._result)

        self.assertTrue(self._result['is_provider_network'])

    def test_create_network_no_vlan(self):
        self._provider_net_driver.process_create_network(
            self._context, self._data, self._result)

        self.assertFalse(self._result.get('is_provider_network'))

    def test_create_network_none_vlan(self):
        self._data[bc.providernet.SEGMENTATION_ID] = None
        self._provider_net_driver.process_create_network(
            self._context, self._data, self._result)

        self.assertFalse(self._result.get('is_provider_network'))


class TestCiscoNexusProviderConfiguration(base.BaseTestCase):
    """Test the provider network configuration used by the cisco nexus MD."""

    def setUp(self):
        super(TestCiscoNexusProviderConfiguration, self).setUp()
        mock.patch.object(rest_driver.CiscoNexusRestapiDriver,
                          '__init__', return_value=None).start()
        self._nexus_md = mech_cisco_nexus.CiscoNexusMechanismDriver()
        self._nexus_md.driver = rest_driver.CiscoNexusRestapiDriver()
        self._get_active_host_connections_mock = mock.patch.object(
            mech_cisco_nexus.CiscoNexusMechanismDriver,
            '_get_active_port_connections',
            return_value=[[IP_ADDR, INTF_TYPE, NEXUS_PORT, IS_NATIVE,
                           None]]).start()
        self._create_and_trunk_vlan_mock = mock.patch.object(
            rest_driver.CiscoNexusRestapiDriver,
            'create_and_trunk_vlan').start()
        self._create_vlan_mock = mock.patch.object(
            rest_driver.CiscoNexusRestapiDriver,
            'create_vlan').start()
        self._send_enable_vlan_on_trunk_int_mock = mock.patch.object(
            rest_driver.CiscoNexusRestapiDriver,
            'send_enable_vlan_on_trunk_int').start()
        self._disable_vlan_on_trunk_int_mock = mock.patch.object(
            rest_driver.CiscoNexusRestapiDriver,
            'disable_vlan_on_trunk_int').start()
        self._get_nexusvlan_binding_mock = mock.patch.object(
            nexus_db_v2, 'get_nexusvlan_binding').start()
        mock.patch.object(
            nexus_db_v2, 'get_port_vlan_switch_binding',
            side_effect=excep.NexusPortBindingNotFound).start()
        mock.patch.object(
            mech_cisco_nexus.CiscoNexusMechanismDriver,
            '_delete_port_channel_resources').start()

    def _set_provider_configuration(
            self, auto_create, auto_trunk, name_prefix):
        cfg.CONF.set_override('provider_vlan_auto_create', auto_create,
                              'ml2_cisco')
        cfg.CONF.set_override('provider_vlan_auto_trunk', auto_trunk,
                              'ml2_cisco')
        cfg.CONF.set_override('provider_vlan_name_prefix', name_prefix,
                              'ml2_cisco')
        cfg.CONF.set_override('vlan_name_prefix', VLAN_NAME_PREFIX,
                              'ml2_cisco')

    def _test_pnet_configure(
            self, auto_create, auto_trunk, name_prefix, is_provider_vlan=True):
        self._set_provider_configuration(auto_create, auto_trunk, name_prefix)
        self._nexus_md._configure_port_binding(
            is_provider_vlan, None, IS_NATIVE, IP_ADDR, VLAN_ID, INTF_TYPE,
            NEXUS_PORT, NO_VNI)

    def _test_pnet_delete(
            self, auto_create, auto_trunk, name_prefix, is_provider_vlan=True):
        self._set_provider_configuration(auto_create, auto_trunk, name_prefix)
        self._nexus_md._delete_switch_entry(
            PORT, VLAN_ID, DEVICE_ID, HOST_ID, NO_VNI, is_provider_vlan)

    def test_pnet_configure_create_and_trunk(self):
        self._test_pnet_configure(
            auto_create=True, auto_trunk=True, name_prefix=PVLAN_NAME_PREFIX)

        self._create_and_trunk_vlan_mock.assert_called_once_with(
            IP_ADDR, VLAN_ID, PVLAN_NAME_PREFIX + VLAN_ID,
            INTF_TYPE, NEXUS_PORT, NO_VNI, True)
        self.assertFalse(self._create_vlan_mock.call_count)
        self.assertFalse(self._send_enable_vlan_on_trunk_int_mock.call_count)

    def test_pnet_configure_create(self):
        self._test_pnet_configure(
            auto_create=True, auto_trunk=False, name_prefix=PVLAN_NAME_PREFIX)

        self.assertFalse(self._create_and_trunk_vlan_mock.call_count)
        self._create_vlan_mock.assert_called_once_with(
            IP_ADDR, VLAN_ID, PVLAN_NAME_PREFIX + VLAN_ID, NO_VNI)
        self.assertFalse(self._send_enable_vlan_on_trunk_int_mock.call_count)

    def test_pnet_configure_trunk(self):
        self._test_pnet_configure(
            auto_create=False, auto_trunk=True, name_prefix=PVLAN_NAME_PREFIX)

        self.assertFalse(self._create_and_trunk_vlan_mock.call_count)
        self.assertFalse(self._create_vlan_mock.call_count)
        self._send_enable_vlan_on_trunk_int_mock.assert_called_once_with(
            IP_ADDR, VLAN_ID, INTF_TYPE, NEXUS_PORT, True)

    def test_pnet_configure_not_providernet(self):
        self._test_pnet_configure(
            auto_create=False, auto_trunk=False, name_prefix=PVLAN_NAME_PREFIX,
            is_provider_vlan=False)

        self._create_and_trunk_vlan_mock.assert_called_once_with(
            IP_ADDR, VLAN_ID, VLAN_NAME_PREFIX + VLAN_ID,
            INTF_TYPE, NEXUS_PORT, NO_VNI, True)
        self.assertFalse(self._create_vlan_mock.call_count)
        self.assertFalse(self._send_enable_vlan_on_trunk_int_mock.call_count)

    def test_pnet_delete_create_and_trunk(self):
        self._test_pnet_delete(
            auto_create=True, auto_trunk=True, name_prefix=PVLAN_NAME_PREFIX)

        self._disable_vlan_on_trunk_int_mock.assert_called_once_with(
            IP_ADDR, VLAN_ID, INTF_TYPE, NEXUS_PORT, IS_NATIVE)
        self._get_nexusvlan_binding_mock.assert_called_once_with(
            VLAN_ID, IP_ADDR)

    def test_pnet_delete_trunk(self):
        self._test_pnet_delete(
            auto_create=False, auto_trunk=True, name_prefix=PVLAN_NAME_PREFIX)

        self._disable_vlan_on_trunk_int_mock.assert_called_once_with(
            IP_ADDR, VLAN_ID, INTF_TYPE, NEXUS_PORT, IS_NATIVE)
        self.assertFalse(self._get_nexusvlan_binding_mock.call_count)

    def test_pnet_delete_create(self):
        self._test_pnet_delete(
            auto_create=True, auto_trunk=False, name_prefix=PVLAN_NAME_PREFIX)

        self.assertFalse(self._disable_vlan_on_trunk_int_mock.call_count)
        self._get_nexusvlan_binding_mock.assert_called_once_with(
            VLAN_ID, IP_ADDR)

    def test_pnet_delete_not_providernet(self):
        self._test_pnet_delete(
            auto_create=False, auto_trunk=False, name_prefix=PVLAN_NAME_PREFIX,
            is_provider_vlan=False)

        self._disable_vlan_on_trunk_int_mock.assert_called_once_with(
            IP_ADDR, VLAN_ID, INTF_TYPE, NEXUS_PORT, IS_NATIVE)
        self._get_nexusvlan_binding_mock.assert_called_once_with(
            VLAN_ID, IP_ADDR)
