# Copyright (c) 2017 Cisco Systems, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import copy
import mock
import testtools

from networking_cisco import backwards_compatibility as bc
from networking_cisco.plugins.ml2.drivers.cisco.nexus import (
    mech_cisco_nexus as md_cisco_nexus)

from neutron.api.v2 import attributes
from neutron.extensions import dns
from neutron.tests.unit.db import test_db_base_plugin_v2


PORT_ID = 'fake_port_id'
TRUNK_ID = 'fake_trunk_id'
DNS_NAME = 'test_dns_name'
VM_NAME = 'test_vm_name'
SEGMENTATION_VLAN = 'vlan'
SEGMENTATION_ID1 = 101
SEGMENTATION_ID2 = 102

SUBPORTS = [
    {'segmentation_type': SEGMENTATION_VLAN, 'port_id': PORT_ID,
     'segmentation_id': SEGMENTATION_ID1},
    {'segmentation_type': SEGMENTATION_VLAN, 'port_id': PORT_ID,
     'segmentation_id': SEGMENTATION_ID2}]

TRUNK = {
    'status': bc.constants.PORT_STATUS_ACTIVE,
    'sub_ports': SUBPORTS,
    'name': 'trunk0',
    'admin_state_up': 'true',
    'tenant_id': 'fake_tenant_id',
    'project_id': 'fake_project_id',
    'port_id': PORT_ID,
    'id': TRUNK_ID,
    'description': 'fake trunk port'}

PROFILE_BAREMETAL = [{"switch_info": "test_value"}]

SUBPORT = {
    'status': bc.constants.PORT_STATUS_ACTIVE,
    'port_id': PORT_ID,
    'segmentation_id': SEGMENTATION_ID1}

PORT_BAREMETAL = {
    'status': bc.constants.PORT_STATUS_ACTIVE,
    'id': PORT_ID,
    bc.portbindings.VNIC_TYPE: bc.portbindings.VNIC_BAREMETAL,
    dns.DNSNAME: DNS_NAME,
    bc.portbindings.PROFILE: {"local_link_information": PROFILE_BAREMETAL},
    'trunk_details': {'trunk_id': TRUNK_ID, 'sub_ports': SUBPORTS}}

PORT_VM = {
    'status': bc.constants.PORT_STATUS_ACTIVE,
    'id': PORT_ID,
    bc.portbindings.VNIC_TYPE: bc.portbindings.VNIC_NORMAL,
    bc.portbindings.HOST_ID: VM_NAME,
    bc.portbindings.PROFILE: {},
    'trunk_details': {'trunk_id': TRUNK_ID, 'sub_ports': SUBPORTS}}


class TestSubPort(object):
    port_id = PORT_ID
    trunk_id = TRUNK_ID
    segmentation_type = SEGMENTATION_VLAN
    segmentation_id = SEGMENTATION_ID1


class TestTrunk(object):
    admin_state_up = 'test_admin_state'
    id = TRUNK_ID
    tenant_id = 'test_tenant_id'
    name = 'test_trunk_name'
    port_id = PORT_ID
    status = bc.constants.PORT_STATUS_ACTIVE
    sub_ports = SUBPORTS
    update = mock.Mock()


@testtools.skipIf(bc.NEUTRON_VERSION < bc.NEUTRON_OCATA_VERSION,
                  "Test not applicable prior to stable/ocata.")
class TestNexusTrunkHandler(test_db_base_plugin_v2.NeutronDbPluginV2TestCase):
    def setUp(self):
        from neutron.objects import trunk as trunk_objects
        from neutron.services.trunk import constants as trunk_consts

        super(TestNexusTrunkHandler, self).setUp()

        self.trunk_consts = trunk_consts
        self.handler = bc.trunk.NexusMDTrunkHandler()
        self.plugin = bc.get_plugin()
        self.plugin.get_port = mock.Mock()
        self.plugin.update_port = mock.Mock()
        self.mock_subport_get_object = mock.patch.object(
            trunk_objects.SubPort, 'get_object',
            return_value=TestSubPort).start()
        self.mock_trunk_get_object = mock.patch.object(
            trunk_objects.Trunk, 'get_object',
            return_value=TestTrunk).start()
        self.mock_md_method = mock.patch.object(
            md_cisco_nexus.CiscoNexusMechanismDriver,
            '_configure_nxos_db').start()

    def _test_process_subports(self, port, host_id):
        self.plugin.get_port.return_value = port
        self.handler.process_subports(port, self.mock_md_method)

        self.assertEqual(2, self.mock_md_method.call_count)
        self.mock_md_method.assert_called_with(
            port, mock.ANY, PORT_ID, host_id,
            bc.nexus_trunk.NO_VNI, bc.nexus_trunk.NO_PROVIDER_NETWORK)

    def _test_update_subports(self, port, host_id):
        self.handler.update_subports(port)

        self.assertEqual(2, self.plugin.update_port.call_count)
        self.plugin.update_port.assert_called_with(mock.ANY, PORT_ID,
            {attributes.PORT:
             {bc.portbindings.HOST_ID: host_id,
              bc.portbindings.VNIC_TYPE: bc.portbindings.VNIC_BAREMETAL,
              bc.portbindings.PROFILE: port[bc.portbindings.PROFILE],
              'device_owner': self.trunk_consts.TRUNK_SUBPORT_OWNER,
              'status': bc.constants.PORT_STATUS_ACTIVE}})

        self.mock_trunk_get_object.called_once_with(mock.ANY, id=TRUNK_ID)
        TestTrunk.update.called_once_with(
            status=self.trunk_consts.ACTIVE_STATUS)

    def test_is_trunk_parentport(self):
        return_value = self.handler.is_trunk_parentport(PORT_VM)

        self.assertTrue(return_value)

    def test_is_trunk_parentport_no_trunk(self):
        PORT_VM_NO_TRUNK = PORT_VM.copy()
        del PORT_VM_NO_TRUNK['trunk_details']
        return_value = self.handler.is_trunk_parentport(PORT_VM_NO_TRUNK)

        self.assertFalse(return_value)

    def test_is_trunk_subport_no_subport(self):
        self.mock_subport_get_object.return_value = None
        PORT_VM['device_owner'] = self.trunk_consts.TRUNK_SUBPORT_OWNER
        return_value = self.handler.is_trunk_subport(PORT_VM)

        self.assertTrue(return_value)

    def test_is_trunk_subport_wrong_deviceowner(self):
        self.mock_subport_get_object.return_value = TestSubPort
        PORT_VM['device_owner'] = 'fake_owner'
        return_value = self.handler.is_trunk_subport(PORT_VM)

        self.assertTrue(return_value)

    def test_is_trunk_subport_no_subport_invalid_deviceowner(self):
        self.mock_subport_get_object.return_value = None
        PORT_VM['device_owner'] = 'fake_owner'
        return_value = self.handler.is_trunk_subport(PORT_VM)

        self.assertFalse(return_value)

    def test_get_trunk_subport(self):
        subport = self.handler.get_trunk_subport(PORT_VM)

        self.assertEqual(TestSubPort, subport)
        self.mock_subport_get_object.assert_called_once_with(
            mock.ANY, port_id=PORT_VM['id'])

    def test_is_trunk_subport_baremetal(self):
        self.plugin.get_port.return_value = PORT_BAREMETAL
        return_value = self.handler.is_trunk_subport_baremetal(PORT_BAREMETAL)

        self.assertTrue(return_value)
        self.mock_subport_get_object.assert_called_once_with(
            mock.ANY, port_id=PORT_BAREMETAL['id'])
        self.mock_trunk_get_object.assert_called_once_with(
            mock.ANY, id=TestSubPort().trunk_id)

    def test_is_trunk_subport_baremetal_no_subport(self):
        self.mock_subport_get_object.return_value = None
        return_value = self.handler.is_trunk_subport_baremetal(PORT_BAREMETAL)

        self.assertFalse(return_value)
        self.mock_subport_get_object.assert_called_once_with(
            mock.ANY, port_id=PORT_BAREMETAL['id'])
        self.assertFalse(self.mock_trunk_get_object.call_count)

    def test_is_trunk_subport_baremetal_vm_port(self):
        self.plugin.get_port.return_value = PORT_VM
        return_value = self.handler.is_trunk_subport_baremetal(PORT_VM)

        self.assertFalse(return_value)

    def test_get_link_info_from_subport(self):
        return_value = self.handler.get_link_info(PORT_BAREMETAL)

        self.assertEqual(PROFILE_BAREMETAL, return_value)

    def test_get_link_info_from_parent(self):
        PORT_BAREMETAL_NO_LINK_INFO = copy.deepcopy(PORT_BAREMETAL)
        del (PORT_BAREMETAL_NO_LINK_INFO[bc.portbindings.PROFILE]
             ["local_link_information"])
        self.plugin.get_port.return_value = PORT_BAREMETAL
        return_value = self.handler.get_link_info(PORT_BAREMETAL_NO_LINK_INFO)

        self.assertEqual(PROFILE_BAREMETAL, return_value)

    def test_process_subports_vm(self):
        self._test_process_subports(PORT_VM, VM_NAME)

    def test_process_subports_baremetal(self):
        self._test_process_subports(PORT_BAREMETAL, DNS_NAME)

    def test_update_subports_vm(self):
        self._test_update_subports(PORT_VM, VM_NAME)

    def test_update_subports_baremetal(self):
        self._test_update_subports(PORT_BAREMETAL, DNS_NAME)
