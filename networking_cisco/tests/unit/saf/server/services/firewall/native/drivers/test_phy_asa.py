# Copyrigh 2016 Cisco Systems.
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


import collections
import copy

import mock

import base64
from oslo_serialization import jsonutils

from neutron.tests import base as base_test

from networking_cisco.apps.saf.server.services.firewall.native import (
    fabric_setup_base as FP)
from networking_cisco.apps.saf.server.services.firewall.native.drivers import (
    base)
from networking_cisco.apps.saf.server.services.firewall.native.drivers import (
    phy_asa)


TENANT_NAME = 'TenantA'
TENANT_ID = '0000-1111-2222-5555'
FW_ID = '0000-aaaa-bbbb-ccce'
FW_NAME = 'FwA'
POLCY_ID = '0000-aaaa-bbbb-cccc'
FW_TYPE = 'TE'
ROUTER_ID = '0000-aaaa-bbbb-5555'
RULE_ID = '0000-aaaa-bbbb-cccd'
PROTOCOL = 'tcp'
MGMT_IP = '3.3.3.3'
SRC_IP = '1.1.1.1'
DST_IP = '2.2.2.2'
SRC_PORT = 34
DST_PORT = 43
RULE_NAME = 'RuleA'
IN_SUBNET = '100.100.11.0'
IN_MASK = '255.255.255.0'
IN_SUBNET_AND_MASK = '100.100.11.0/24'
IN_START = '100.100.11.3'
IN_SEC_GW = '100.100.11.254'
IN_GW = '100.100.11.2'
IN_FABRIC_GW = '100.100.11.1'
IN_END = '100.100.11.254'
SEGMENTATION_ID = 87999
OUT_SEGMENTATION_ID = 88000
VLAN_ID = 770
OUT_VLAN_ID = 771
OUT_SUBNET = '200.200.11.0'
OUT_MASK = '255.255.255.0'
OUT_SUBNET_AND_MASK = '200.200.11.0/24'
RTR_SUBNET_AND_MASK = '9.9.9.0/24'
OUT_START = '200.200.11.3'
OUT_SEC_GW = '200.200.11.254'
OUT_GW = '200.200.11.2'
OUT_FABRIC_GW = '200.200.11.1'
OUT_END = '200.200.11.254'
INTF_IN = 'e1/1'
INTF_OUT = 'e1/2'

try:
    OrderedDict = collections.OrderedDict
except AttributeError:
    import ordereddict
    OrderedDict = ordereddict.OrderedDict


class FakeClass(object):
    """Fake class"""
    @classmethod
    def imitate(cls, *others):
        for other in others:
            for name in other.__dict__:
                try:
                    setattr(cls, name, mock.Mock())
                except (TypeError, AttributeError):
                    pass
        return cls

    @classmethod
    def set_return(cls, class_name, fn_name, return_val):
        getattr(cls, fn_name).return_value = return_val


class PhyAsaTest(base_test.BaseTestCase):
    """A test suite to exercise the Phy ASA Driver.  """

    def setUp(self):
        '''Setup for the test scripts '''
        super(PhyAsaTest, self).setUp()
        self._init_values()
        self.cfg_dict = self._fill_cfg()

        phy_asa.PhyAsa.__bases__ = (FakeClass.imitate(base.BaseDrvr,
                                                      FP.FabricApi),)
        self.phy_asa = phy_asa.PhyAsa()
        self.phy_asa.initialize(self.cfg_dict)

    def _init_values(self):
        self.tenant_name = TENANT_NAME
        self.tenant_id = TENANT_ID
        self.fw_id = FW_ID
        self.fw_name = FW_NAME
        self.rule_id = RULE_ID
        self.rule_dict = dict()
        self.rule_dict['protocol'] = PROTOCOL
        self.rule_dict['name'] = RULE_NAME
        self.rule_dict['enabled'] = True
        self.rule_dict['source_ip_address'] = SRC_IP
        self.rule_dict['destination_ip_address'] = DST_IP
        self.rule_dict['source_port'] = str(SRC_PORT)
        self.rule_dict['destination_port'] = str(DST_PORT)
        self.rule_dict['action'] = 'allow'
        self.in_subnet = IN_SUBNET
        self.in_subnet_and_mask = IN_SUBNET_AND_MASK
        self.in_gw = IN_GW
        self.in_start = IN_START
        self.in_sec_gw = IN_SEC_GW
        self.in_end = IN_END
        self.out_subnet = OUT_SUBNET
        self.out_subnet_and_mask = OUT_SUBNET_AND_MASK
        self.out_gw = OUT_GW
        self.out_sec_gw = OUT_SEC_GW
        self.out_start = OUT_START
        self.out_end = OUT_END
        self.in_fabric_gw = IN_FABRIC_GW
        self.out_fabric_gw = OUT_FABRIC_GW
        self.segmentation_id = SEGMENTATION_ID
        self.out_segmentation_id = OUT_SEGMENTATION_ID
        self.vlan_id = VLAN_ID
        self.out_vlan_id = OUT_VLAN_ID
        fw_data_rule_dict = {self.rule_id: self.rule_dict}
        self.fw_data = {'tenant_name': self.tenant_name, 'fw_id': self.fw_id,
                        'fw_name': self.fw_name, 'rules': fw_data_rule_dict}

    def _fill_cfg(self):
        config = {'mgmt_ip_addr': MGMT_IP, 'user': 'user',
                  'pwd': 'user', 'interface_in': INTF_IN,
                  'interface_out': INTF_OUT}
        return config

    def test_phy_asa_init(self):
        '''Wrapper for the init'''
        pass

    def _get_modified_fw_data(self):
        new_fw_data = copy.deepcopy(self.fw_data)
        new_fw_data.get('rules').get(self.rule_id)['action'] = 'deny'
        return new_fw_data

    def _get_asa_command(self):
        cmds = ["conf t", "changeto system"]
        inside_int = INTF_IN + '.' + str(self.vlan_id)
        cmds.append("int " + inside_int)
        cmds.append("vlan " + str(self.vlan_id))
        outside_int = INTF_OUT + '.' + str(self.out_vlan_id)
        cmds.append("int " + outside_int)
        cmds.append("vlan " + str(self.out_vlan_id))
        cmds.append("context " + self.tenant_name)
        cmds.append("allocate-interface " + inside_int)
        cmds.append("allocate-interface " + outside_int)
        cmds.append("config-url disk0:/" + self.tenant_name + ".cfg")
        cmds.append("write memory")
        cmds.append("changeto context " + self.tenant_name)
        cmds.append("int " + inside_int)
        cmds.append("nameif Inside")
        cmds.append("security-level 100")
        cmds.append("ip address " + self.in_gw + " " + IN_MASK)
        cmds.append("int " + outside_int)
        cmds.append("nameif Outside")
        cmds.append("security-level 0")
        cmds.append("ip address " + self.out_gw + " " + OUT_MASK)

        cmds.append("router ospf 1")
        cmds.append("network " + self.in_gw + " " + IN_MASK + " area 0")
        cmds.append("network " + self.out_gw + " " + OUT_MASK + " area 0")
        cmds.append("area 0")
        cmds.append("route Outside 0.0.0.0 0.0.0.0 " + self.out_fabric_gw +
                    " 1")
        cmds.append("route Outside 0.0.0.0 0.0.0.0 " + self.out_sec_gw + " 1")
        cmds.append("end")
        cmds.append("write memory")

        data = {"commands": cmds}
        return data

    def _get_asa_del_command(self):
        cmds = ["conf t", "changeto system"]
        cmds.append("no context " + self.tenant_name + " noconfirm")
        inside_int = INTF_IN + '.' + str(self.vlan_id)
        outside_int = INTF_OUT + '.' + str(self.out_vlan_id)
        cmds.append("no interface " + inside_int)
        cmds.append("no interface " + outside_int)
        cmds.append("write memory")
        cmds.append("del /noconfirm disk0:/" + self.tenant_name + ".cfg")

        data = {"commands": cmds}
        return data

    def _get_asa_pol_command(self):
        cmds = ["conf t", "changeto context " + self.tenant_name]
        acl = "access-list "
        acl = (acl + self.tenant_name + " extended " +
               'permit' + " " +
               self.rule_dict['protocol'] + " " + SRC_IP + " " +
               '255.255.255.255' + " eq " + str(SRC_PORT) + " " +
               DST_IP + " " + '255.255.255.255' + " eq " + str(DST_PORT) + " ")
        cmds.append(acl)
        cmds.append("access-group " + self.tenant_name + " global")
        cmds.append("write memory")

        data = {"commands": cmds}
        return data

    def _get_asa_modf_pol_command(self):
        cmds = ["conf t", "changeto context " + self.tenant_name]
        acl = "access-list "
        acl = (acl + self.tenant_name + " extended " +
               'permit' + " " +
               self.rule_dict['protocol'] + " " + SRC_IP + " " +
               '255.255.255.255' + " eq " + str(SRC_PORT) + " " +
               DST_IP + " " + '255.255.255.255' + " eq " + str(DST_PORT) + " ")
        cmds.append("no " + acl)
        acl = ("access-list " + self.tenant_name + " extended " +
               'deny' + " " +
               self.rule_dict['protocol'] + " " + SRC_IP + " " +
               '255.255.255.255' + " eq " + str(SRC_PORT) + " " +
               DST_IP + " " + '255.255.255.255' + " eq " + str(DST_PORT) + " ")
        cmds.append(acl)
        cmds.append("access-group " + self.tenant_name + " global")
        cmds.append("write memory")

        data = {"commands": cmds}
        return data

    def _test_create_fw(self):
        url = "https://" + MGMT_IP + "/api/cli"
        asa_payload = self._get_asa_command()
        asa_pol_payload = self._get_asa_pol_command()
        headers = {'Content-Type': 'application/json'}
        base64string = base64.encodestring('%s:%s' %
                                           ('user', 'user')).replace('\n', '')
        with mock.patch('urllib2.Request') as url_req,\
                mock.patch('urllib2.urlopen') as url_open:
            url_open.return_value.getcode.return_value = 202
            FakeClass.set_return(FP.FabricApi, 'get_in_ip_addr',
                                 [self.in_subnet, self.in_start,
                                  self.in_sec_gw, self.in_fabric_gw,
                                  self.in_end])
            FakeClass.set_return(FP.FabricApi, 'get_out_ip_addr',
                                 [self.out_subnet, self.out_start,
                                  self.out_sec_gw, self.out_fabric_gw,
                                  self.out_end])
            FakeClass.set_return(FP.FabricApi, 'get_in_srvc_node_ip_addr',
                                 self.in_gw)
            FakeClass.set_return(FP.FabricApi, 'get_out_srvc_node_ip_addr',
                                 self.out_gw)
            FakeClass.set_return(FP.FabricApi, 'get_in_seg_vlan',
                                 [self.segmentation_id, self.vlan_id])
            FakeClass.set_return(FP.FabricApi, 'get_out_seg_vlan',
                                 [self.out_segmentation_id, self.out_vlan_id])
            parent = mock.MagicMock()
            parent.attach_mock(url_req, 'url_req')
            self.phy_asa.create_fw(self.tenant_id, self.fw_data)
        expected_calls = [
            mock.call.url_req(url, jsonutils.dumps(asa_payload), headers),
            mock.call.url_req().add_header("Authorization",
                                           "Basic %s" % base64string),
            mock.call.url_req(url, jsonutils.dumps(asa_pol_payload), headers),
            mock.call.url_req().add_header("Authorization",
                                           "Basic %s" % base64string)]
        parent.assert_has_calls(expected_calls, any_order=False)
        self.assertEqual(url_open.called, True)

    def test_create_fw(self):
        """Create FW Test """
        self._test_create_fw()

    def _test_delete_fw(self):
        url = "https://" + MGMT_IP + "/api/cli"
        asa_del_payload = self._get_asa_del_command()
        headers = {'Content-Type': 'application/json'}
        base64string = base64.encodestring('%s:%s' %
                                           ('user', 'user')).replace('\n', '')
        with mock.patch('urllib2.Request') as url_req,\
                mock.patch('urllib2.urlopen') as url_open:
            url_open.return_value.getcode.return_value = 202
            FakeClass.set_return(FP.FabricApi, 'get_in_ip_addr',
                                 [self.in_subnet, self.in_start,
                                  self.in_sec_gw, self.in_fabric_gw,
                                  self.in_end])
            FakeClass.set_return(FP.FabricApi, 'get_out_ip_addr',
                                 [self.out_subnet, self.out_start,
                                  self.out_sec_gw, self.out_fabric_gw,
                                  self.out_end])
            FakeClass.set_return(FP.FabricApi, 'get_in_srvc_node_ip_addr',
                                 self.in_gw)
            FakeClass.set_return(FP.FabricApi, 'get_out_srvc_node_ip_addr',
                                 self.out_gw)
            FakeClass.set_return(FP.FabricApi, 'get_in_seg_vlan',
                                 [self.segmentation_id, self.vlan_id])
            FakeClass.set_return(FP.FabricApi, 'get_out_seg_vlan',
                                 [self.out_segmentation_id, self.out_vlan_id])
            parent = mock.MagicMock()
            parent.attach_mock(url_req, 'url_req')
            self.phy_asa.delete_fw(self.tenant_id, self.fw_data)
        expected_calls = [
            mock.call.url_req(url, jsonutils.dumps(asa_del_payload), headers),
            mock.call.url_req().add_header("Authorization",
                                           "Basic %s" % base64string)]
        parent.assert_has_calls(expected_calls, any_order=False)
        self.assertEqual(url_open.called, True)

    def test_delete_fw(self):
        """Delete FW Test """
        self._test_delete_fw()

    def _test_modify_fw(self):
        url = "https://" + MGMT_IP + "/api/cli"
        asa_payload = self._get_asa_command()
        asa_pol_payload = self._get_asa_pol_command()
        asa_modf_pol_payload = self._get_asa_modf_pol_command()
        headers = {'Content-Type': 'application/json'}
        base64string = base64.encodestring('%s:%s' %
                                           ('user', 'user')).replace('\n', '')
        with mock.patch('urllib2.Request') as url_req,\
                mock.patch('urllib2.urlopen') as url_open:
            url_open.return_value.getcode.return_value = 202
            FakeClass.set_return(FP.FabricApi, 'get_in_ip_addr',
                                 [self.in_subnet, self.in_start,
                                  self.in_sec_gw, self.in_fabric_gw,
                                  self.in_end])
            FakeClass.set_return(FP.FabricApi, 'get_out_ip_addr',
                                 [self.out_subnet, self.out_start,
                                  self.out_sec_gw, self.out_fabric_gw,
                                  self.out_end])
            FakeClass.set_return(FP.FabricApi, 'get_in_srvc_node_ip_addr',
                                 self.in_gw)
            FakeClass.set_return(FP.FabricApi, 'get_out_srvc_node_ip_addr',
                                 self.out_gw)
            FakeClass.set_return(FP.FabricApi, 'get_in_seg_vlan',
                                 [self.segmentation_id, self.vlan_id])
            FakeClass.set_return(FP.FabricApi, 'get_out_seg_vlan',
                                 [self.out_segmentation_id, self.out_vlan_id])
            parent = mock.MagicMock()
            parent.attach_mock(url_req, 'url_req')
            self.phy_asa.create_fw(self.tenant_id, self.fw_data)
            new_fw_data = self._get_modified_fw_data()
            self.phy_asa.modify_fw(self.tenant_id, new_fw_data)
        expected_calls = [
            mock.call.url_req(url, jsonutils.dumps(asa_payload), headers),
            mock.call.url_req().add_header("Authorization",
                                           "Basic %s" % base64string),
            mock.call.url_req(url, jsonutils.dumps(asa_pol_payload), headers),
            mock.call.url_req().add_header("Authorization",
                                           "Basic %s" % base64string),
            mock.call.url_req(url, jsonutils.dumps(asa_modf_pol_payload),
                              headers),
            mock.call.url_req().add_header("Authorization",
                                           "Basic %s" % base64string)]
        parent.assert_has_calls(expected_calls, any_order=False)
        self.assertEqual(url_open.called, True)

    def test_modify_fw(self):
        """Modify FW Test """
        self._test_modify_fw()
