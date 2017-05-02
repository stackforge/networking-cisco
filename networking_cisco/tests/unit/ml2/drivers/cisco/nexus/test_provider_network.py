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

from networking_cisco import backwards_compatibility as bc
from networking_cisco.plugins.ml2.drivers.cisco.nexus import mech_cisco_nexus
from networking_cisco.plugins.ml2.drivers.cisco.nexus import nexus_db_v2

from neutron.tests.unit import testlib_api

NETWORK_ID = 'test_network_id'
VLAN_ID = 'test_vlan_id'
NETWORK = {'id': NETWORK_ID,
           'is_provider_network': True,
           'network_type': 'vlan',
           'segmentation_id': VLAN_ID,
           bc.providernet.SEGMENTATION_ID: VLAN_ID}
PORT = {'device_id': 'test_device_id',
        bc.portbindings.VNIC_TYPE: 'normal',
        bc.portbindings.HOST_ID: 'test_host_id'}


class TestCiscoNexusProvider(testlib_api.SqlTestCase):
    """Test the provider network code added to the cisco nexus MD."""

    def setUp(self):
        super(TestCiscoNexusProvider, self).setUp()
        self._nexus_md = mech_cisco_nexus.CiscoNexusMechanismDriver()
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
        func = mock.Mock()
        self._nexus_md.create_network_precommit(self.context)
        self._nexus_md._port_action_vlan(PORT, NETWORK, func, 0)

        func.assert_called_once_with(
            mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, True)

    def test_port_action_vlan_no_provider(self):
        func = mock.Mock()
        self._nexus_md._port_action_vlan(PORT, NETWORK, func, 0)

        func.assert_called_once_with(
            mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, False)
