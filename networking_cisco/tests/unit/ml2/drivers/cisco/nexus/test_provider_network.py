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

from neutron.tests import base

from networking_cisco import backwards_compatibility as bc
from networking_cisco.plugins.ml2.drivers.cisco.nexus.extensions import (
    cisco_providernet)
from networking_cisco.plugins.ml2.drivers.cisco.nexus import mech_cisco_nexus
from networking_cisco.plugins.ml2.drivers.cisco.nexus import nexus_db_v2

from neutron.plugins.ml2 import driver_api as api
from neutron.tests.unit import testlib_api

NETWORK_ID = 'test_network_id'
VLAN_ID = 'test_vlan_id'
NETWORK = {'id': NETWORK_ID,
           'is_provider_network': True,
           api.NETWORK_TYPE: 'vlan',
           api.SEGMENTATION_ID: VLAN_ID,
           bc.providernet.SEGMENTATION_ID: VLAN_ID}
PORT = {'device_id': 'test_device_id',
        bc.portbindings.VNIC_TYPE: 'normal',
        bc.portbindings.HOST_ID: 'test_host_id'}


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
