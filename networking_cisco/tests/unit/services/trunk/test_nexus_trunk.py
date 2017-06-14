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

import mock
import unittest

from oslo_config import cfg

from networking_cisco import backwards_compatibility as bc

from networking_cisco.plugins.ml2.drivers.cisco.nexus import (
    constants as const)
from networking_cisco.plugins.ml2.drivers.cisco.nexus import (
    mech_cisco_nexus as md_cisco_nexus)

from neutron.callbacks import events
from neutron.extensions import dns
from neutron.tests.unit.db import test_db_base_plugin_v2
from neutron.tests.unit import testlib_api


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

SUBPORT = {
    'status': bc.constants.PORT_STATUS_ACTIVE,
    'port_id': PORT_ID,
    'segmentation_id': SEGMENTATION_ID1}

PORT_BAREMETAL = {
    'status': bc.constants.PORT_STATUS_ACTIVE,
    bc.portbindings.VNIC_TYPE: bc.portbindings.VNIC_BAREMETAL,
    dns.DNSNAME: DNS_NAME,
    bc.portbindings.PROFILE: {"local_link_information": []}}

PORT_VM = {
    'status': bc.constants.PORT_STATUS_ACTIVE,
    bc.portbindings.VNIC_TYPE: bc.portbindings.VNIC_NORMAL,
    bc.portbindings.HOST_ID: VM_NAME,
    bc.portbindings.PROFILE: {}}

PORT_SUBPORT = {
    'status': bc.constants.PORT_STATUS_ACTIVE,
    bc.portbindings.PROFILE: {}}


@unittest.skipIf(bc.NEUTRON_VERSION < bc.NEUTRON_OCATA_VERSION,
                 "Test not applicable prior to stable/ocata.")
class TestNexusTrunkHandler(test_db_base_plugin_v2.NeutronDbPluginV2TestCase):
    def setUp(self):
        super(TestNexusTrunkHandler, self).setUp()

        self.handler = bc.nexus_trunk.NexusTrunkHandler()
        self.plugin = bc.get_plugin()
        self.plugin.update_port = mock.Mock()
        self.mock_delete_nxos_db = mock.patch.object(
            md_cisco_nexus.CiscoNexusMechanismDriver,
            '_delete_nxos_db').start()
        self.mock_delete_switch_entry = mock.patch.object(
            md_cisco_nexus.CiscoNexusMechanismDriver,
            '_delete_switch_entry').start()
        self.mock_configure_nxos_db = mock.patch.object(
            md_cisco_nexus.CiscoNexusMechanismDriver,
            '_configure_nxos_db').start()
        self.mock_configure_port_entries = mock.patch.object(
            md_cisco_nexus.CiscoNexusMechanismDriver,
            '_configure_port_entries').start()

    def _fake_trunk_payload(self):
        payload = mock.Mock()
        payload.current_trunk.status = bc.constants.PORT_STATUS_DOWN
        payload.current_trunk.to_dict = mock.Mock(return_value=TRUNK)
        payload.original_trunk.status = bc.constants.PORT_STATUS_DOWN
        payload.original_trunk.to_dict = mock.Mock(return_value=TRUNK)
        payload.subports = mock.MagicMock()
        payload.subports[0] = mock.Mock()
        payload.subports[0].segmentation_id = SEGMENTATION_ID1
        payload.subports[0].port_id = PORT_ID
        payload.subports[0].to_dict = mock.Mock(return_value=SUBPORT)
        return payload

    def _call_test_method(self, test_method, port, event=mock.ANY):
        self.plugin.get_port = mock.Mock(side_effect=[port, PORT_SUBPORT])
        method = getattr(self.handler, test_method)
        method(mock.ANY, event, mock.ANY, self._fake_trunk_payload())

    def _verify_subport_precommit(self, port, host_id):
        self.assertEqual(2, self.plugin.get_port.call_count)
        self.mock_delete_nxos_db.assert_called_once_with(
            PORT_SUBPORT, SEGMENTATION_ID1, PORT_ID, host_id,
            bc.nexus_trunk.NO_VNI, bc.nexus_trunk.NO_PROVIDER_NETWORK)
        self.mock_delete_switch_entry.assert_called_once_with(
            PORT_SUBPORT, SEGMENTATION_ID1, PORT_ID, host_id,
            bc.nexus_trunk.NO_VNI, bc.nexus_trunk.NO_PROVIDER_NETWORK)

    def _verify_subport_precommit_unsupported_event(self):
        self.assertEqual(2, self.plugin.get_port.call_count)
        self.assertFalse(self.mock_delete_nxos_db.call_count)
        self.assertFalse(self.mock_delete_switch_entry.call_count)

    def _verify_subport_postcommit(self, port, host_id):
        self.assertEqual(2, self.plugin.get_port.call_count)
        self.mock_configure_nxos_db.assert_called_once_with(
            PORT_SUBPORT, SEGMENTATION_ID1, PORT_ID, host_id,
            bc.nexus_trunk.NO_VNI, bc.nexus_trunk.NO_PROVIDER_NETWORK)
        self.mock_configure_port_entries.assert_called_once_with(
            PORT_SUBPORT, SEGMENTATION_ID1, PORT_ID, host_id,
            bc.nexus_trunk.NO_VNI, bc.nexus_trunk.NO_PROVIDER_NETWORK)

    def _verify_subport_postcommit_unsupported_event(self):
        self.assertEqual(2, self.plugin.get_port.call_count)
        self.assertFalse(self.mock_configure_nxos_db.call_count)
        self.assertFalse(self.mock_configure_port_entries.call_count)

    def test_trunk_update_postcommit_baremetal(self):
        self._call_test_method("trunk_update_postcommit", PORT_BAREMETAL)

        self.plugin.get_port.assert_called_once_with(mock.ANY, PORT_ID)
        self.assertEqual(
            len(TRUNK['sub_ports']), self.plugin.update_port.call_count)
        self.plugin.update_port.assert_called_with(mock.ANY, PORT_ID, mock.ANY)

    def test_trunk_update_postcommit_vm(self):
        self._call_test_method(
            "trunk_update_postcommit", PORT_VM, event=events.PRECOMMIT_DELETE)

        self.plugin.get_port.assert_called_once_with(mock.ANY, PORT_ID)
        self.assertFalse(self.plugin.update_port.call_count)

    def test_subport_precommit_baremetal(self):
        self._call_test_method(
            "subport_precommit", PORT_BAREMETAL, event=events.PRECOMMIT_DELETE)

        self._verify_subport_precommit(PORT_BAREMETAL, DNS_NAME)

    def test_subport_precommit_baremetal_no_dnsname(self):
        PORT_BAREMETAL_NO_DNSNAME = PORT_BAREMETAL.copy()
        del PORT_BAREMETAL_NO_DNSNAME[dns.DNSNAME]
        self._call_test_method(
            "subport_precommit", PORT_BAREMETAL_NO_DNSNAME,
            event=events.PRECOMMIT_DELETE)

        self.assertEqual(1, self.plugin.get_port.call_count)

    def test_subport_precommit_baremetal_unsupported_event(self):
        self._call_test_method(
            "subport_precommit", PORT_BAREMETAL, event=events.BEFORE_DELETE)

        self._verify_subport_precommit_unsupported_event()

    def test_subport_precommit_vm(self):
        self._call_test_method(
            "subport_precommit", PORT_VM, event=events.PRECOMMIT_DELETE)

        self._verify_subport_precommit(PORT_VM, VM_NAME)

    def test_subport_precommit_vm_no_hostid(self):
        PORT_VM_NO_HOSTID = PORT_VM.copy()
        del PORT_VM_NO_HOSTID[bc.portbindings.HOST_ID]
        self._call_test_method(
            "subport_precommit", PORT_VM_NO_HOSTID,
            event=events.PRECOMMIT_DELETE)

        self.assertEqual(1, self.plugin.get_port.call_count)

    def test_subport_precommit_vm_unsupported_event(self):
        self._call_test_method(
            "subport_precommit", PORT_VM, event=events.BEFORE_DELETE)

        self._verify_subport_precommit_unsupported_event()

    def test_subport_postcommit_baremetal_after_create(self):
        self._call_test_method(
            "subport_postcommit", PORT_BAREMETAL, event=events.AFTER_CREATE)

        self._verify_subport_postcommit(PORT_BAREMETAL, DNS_NAME)
        self.plugin.update_port.assert_called_with(mock.ANY, PORT_ID, mock.ANY)
        self.assertEqual(
            bc.constants.PORT_STATUS_ACTIVE,
            self.plugin.update_port.call_args[0][2]['port']['status'])

    def test_subport_postcommit_baremetal_after_delete(self):
        self._call_test_method(
            "subport_postcommit", PORT_BAREMETAL, event=events.AFTER_DELETE)

        self._verify_subport_postcommit_unsupported_event()
        self.plugin.update_port.assert_called_with(mock.ANY, PORT_ID, mock.ANY)
        self.assertEqual(
            bc.constants.PORT_STATUS_DOWN,
            self.plugin.update_port.call_args[0][2]['port']['status'])

    def test_subport_postcommit_baremetal_no_dnsname(self):
        PORT_BAREMETAL_NO_DNSNAME = PORT_BAREMETAL.copy()
        del PORT_BAREMETAL_NO_DNSNAME[dns.DNSNAME]
        self._call_test_method(
            "subport_postcommit", PORT_BAREMETAL_NO_DNSNAME,
            event=events.AFTER_CREATE)

        self.assertEqual(1, self.plugin.get_port.call_count)

    def test_subport_postcommit_baremetal_unsupported_event(self):
        self._call_test_method(
            "subport_postcommit", PORT_BAREMETAL, event=events.BEFORE_DELETE)

        self._verify_subport_postcommit_unsupported_event()

    def test_subport_postcommit_vm(self):
        self._call_test_method(
            "subport_postcommit", PORT_VM, event=events.AFTER_CREATE)

        self._verify_subport_postcommit(PORT_VM, VM_NAME)
        self.assertFalse(self.plugin.update_port.call_count)

    def test_subport_postcommit_vm_no_hostid(self):
        PORT_VM_NO_HOSTID = PORT_VM.copy()
        del PORT_VM_NO_HOSTID[bc.portbindings.HOST_ID]
        self._call_test_method(
            "subport_postcommit", PORT_VM_NO_HOSTID,
            event=events.AFTER_CREATE)

        self.assertEqual(1, self.plugin.get_port.call_count)

    def test_subport_postcommit_vm_unsupported_event(self):
        self._call_test_method(
            "subport_postcommit", PORT_VM, event=events.BEFORE_DELETE)

        self._verify_subport_postcommit_unsupported_event()


@unittest.skipIf(bc.NEUTRON_VERSION < bc.NEUTRON_OCATA_VERSION,
                 "Test not applicable prior to stable/ocata.")
class TestNexusTrunkDriver(testlib_api.SqlTestCase):
    def setUp(self):
        super(TestNexusTrunkDriver, self).setUp()

    def test_is_loaded(self):
        driver = bc.nexus_trunk.NexusTrunkDriver.create()
        cfg.CONF.set_override('mechanism_drivers',
                              ["logger", const.CISCO_NEXUS_ML2_MECH_DRIVER_V2],
                              group='ml2')
        self.assertTrue(driver.is_loaded)

        cfg.CONF.set_override('mechanism_drivers',
                              ['logger'],
                              group='ml2')
        self.assertFalse(driver.is_loaded)

        cfg.CONF.set_override('core_plugin', 'some_plugin')
        self.assertFalse(driver.is_loaded)
