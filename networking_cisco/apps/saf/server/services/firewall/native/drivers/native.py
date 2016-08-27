# Copyright 2016 Cisco Systems, Inc.
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
#

import time

from networking_cisco._i18n import _LE, _LI
from networking_cisco.apps.saf.common import config
from networking_cisco.apps.saf.common import dfa_logger as logging
from networking_cisco.apps.saf.server import dfa_openstack_helper as OsHelper
from networking_cisco.apps.saf.server.services.firewall.native import (
    fabric_setup_base as FP)
from networking_cisco.apps.saf.server.services.firewall.native import (
    fw_constants as fw_const)
from networking_cisco.apps.saf.server.services.firewall.native.drivers import (
    base)


LOG = logging.getLogger(__name__)
Q_PRIORITY = 30 + 4


class NativeFirewall(base.BaseDriver, FP.FabricApi):

    """Native Firewall Driver """

    def __init__(self):
        """Class init """
        LOG.debug("Initializing Native Firewall")
        super(NativeFirewall, self).__init__()
        self.tenant_dict = {}
        self.os_helper = OsHelper.DfaNeutronHelper()
        self.cfg = config.CiscoDFAConfig().cfg
        self.mgmt_ip_addr = None
        self.dcnm_obj = None
        self.que_obj = None

    def initialize(self, cfg_dict):
        """Initialization routine """
        LOG.debug("Initialize for NativeFirewall")
        self.mgmt_ip_addr = cfg_dict.get('mgmt_ip_addr')

    def populate_event_que(self, que_obj):
        """Populate the event queue object """
        LOG.debug("Pop Event for NativeFirewall")
        self.que_obj = que_obj

    def populate_dcnm_obj(self, dcnm_obj):
        """Populate the DCNM object """
        LOG.debug("Pop DCNM for NativeFirewall")
        self.dcnm_obj = dcnm_obj

    def is_device_virtual(self):
        """Returns if device is virtual """
        return True

    def get_name(self):
        """Returns the name of the FW appliance """
        # Put it in a constant fixme(padkrish)
        return 'native'

    def get_max_quota(self):
        # Return the right value fixme
        """
        Returns the number of Firewall instances

        Returns the maximum number of Firewall instance that a single Firewall
        can support
        """
        return 50

    def attach_intf_router(self, tenant_id, tenant_name, rtr_id):
        """Routine to attach the interface to the router """
        in_sub = self.get_in_subnet_id(tenant_id)
        out_sub = self.get_out_subnet_id(tenant_id)
        # Modify Hard coded Name fixme
        subnet_lst = set()
        subnet_lst.add(in_sub)
        subnet_lst.add(out_sub)
        ret = self.os_helper.add_intf_router(rtr_id, tenant_id, subnet_lst)
        return ret, in_sub, out_sub

    def get_rtr_id(self, tenant_id, tenant_name):
        """Retrieve the router ID """
        rtr_id = None
        if tenant_id in self.tenant_dict:
            if 'rtr_id' in self.tenant_dict.get(tenant_id):
                rtr_id = self.tenant_dict.get(tenant_id).get('rtr_id')
        if rtr_id is None:
            rtr_list = self.os_helper.get_rtr_by_name('FW_RTR_' + tenant_name)
            if len(rtr_list) > 0:
                rtr_id = rtr_list[0].get('id')
        return rtr_id

    def delete_intf_router(self, tenant_id, tenant_name, rtr_id):
        """Routine to delete the router """
        in_sub = self.get_in_subnet_id(tenant_id)
        out_sub = self.get_out_subnet_id(tenant_id)
        subnet_lst = set()
        subnet_lst.add(in_sub)
        subnet_lst.add(out_sub)
        rtr_id = None
        rtr_id = self.get_rtr_id(tenant_id, tenant_name)
        if rtr_id is not None:
            ret = self.os_helper.delete_intf_router(tenant_name, tenant_id,
                                                    rtr_id, subnet_lst)
            if not ret:
                LOG.error(_LE("Failed to delete router intf id %(rtr)s, "
                              "tenant %(tenant)s"),
                          {'rtr': rtr_id, 'tenant': tenant_id})
            return ret
        else:
            LOG.error(_LE("Invalid router ID, can't delete interface from "
                          "router"))

    def prepare_rtr_vm_msg(self, tenant_id, tenant_name, rtr_id, net_id,
                           subnet_id, seg, status):
        """
        Prepare the message to be sent to Event queue for VDP trigger.

        This is actually called for a subnet add to a router. This function
        prepares a VM's VNIC create/delete message
        """
        max_get_rtr_info_retry = True
        attempt = 0
        while max_get_rtr_info_retry:
            port_data = self.os_helper.get_router_port_subnet(subnet_id)
            if port_data is None:
                LOG.error(_LE("Unable to get router port data"))
                return None
            if port_data.get('binding:host_id') == '':
                time.sleep(3)
                attempt = attempt + 1
                if attempt > 3:
                    max_get_rtr_info_retry = False
                    LOG.error(_LE("Unable to get router binding host data, "
                                  "Max attempts reached"))
            else:
                max_get_rtr_info_retry = False
        if status is 'up':
            event_type = 'service.vnic.create'
        else:
            event_type = 'service.vnic.delete'
        vnic_data = {'status': status, 'mac': port_data.get('mac_address'),
                     'segid': seg, 'host': port_data.get('binding:host_id')}
        if vnic_data['host'] == '':
            LOG.error(_LE("Null host for seg %(seg)s subnet %(subnet)s"),
                      {'seg': seg, 'subnet': subnet_id})
            if self.tenant_dict.get(tenant_id).get('host') is None:
                LOG.error(_LE("Null host for tenant %(tenant)s seg %(seg)s "
                              "subnet %(subnet)s"),
                          {'tenant': tenant_id, 'seg': seg,
                           'subnet': subnet_id})
                return None
            else:
                vnic_data['host'] = self.tenant_dict.get(tenant_id).get('host')
        else:
            self.tenant_dict[tenant_id]['host'] = vnic_data['host']
        vm_ip = port_data.get('fixed_ips')[0].get('ip_address')
        vnic_data.update({'port_id': port_data.get('id'), 'network_id': net_id,
                          'vm_name': 'FW_SRVC_RTR_' + tenant_name,
                          'vm_ip': vm_ip, 'vm_uuid': rtr_id, 'gw_mac': None,
                          'fwd_mod': 'anycast_gateway'})
        payload = {'service': vnic_data}
        data = (event_type, payload)
        return data

    def send_rtr_port_msg(self, tenant_id, tenant_name, rtr_id, net_id,
                          subnet_id, seg, status):
        """Sends the router port message to the queue """
        data = self.prepare_rtr_vm_msg(tenant_id, tenant_name, rtr_id,
                                       net_id, subnet_id, seg, status)
        if data is None:
            return False
        timestamp = time.ctime()
        pri = Q_PRIORITY
        LOG.info(_LI("Sending native FW data into queue %(data)s"),
                 {'data': data})
        self.que_obj.put((pri, timestamp, data))
        return True

    def create_tenant_dict(self, tenant_id, rtr_id=None):
        """Tenant dict creation """
        self.tenant_dict[tenant_id] = {'host': None, 'rtr_id': rtr_id}

    def _create_fw(self, tenant_id, data):
        """Internal routine that gets called when a FW is created """
        LOG.debug("In creating Native FW data is %s", data)
        tenant_name = data.get('tenant_name')
        in_seg, in_vlan = self.get_in_seg_vlan(tenant_id)
        out_seg, out_vlan = self.get_out_seg_vlan(tenant_id)
        # self.get_mgmt_ip_addr(tenant_id)
        # self.get_vlan_in_out(tenant_id)
        # Check if router is already added and only then add, needed for
        # restart cases since native doesn't have a special DB fixme
        rtr_id = data.get('router_id')
        ret, in_sub, out_sub = self.attach_intf_router(tenant_id,
                                                       tenant_name, rtr_id)
        if not ret:
            LOG.error(_LE("Native FW: Attach intf router failed for tenant "
                          "%s"), tenant_id)
            return False
        self.create_tenant_dict(tenant_id, rtr_id)

        in_ip, in_start, in_end, in_gw, in_sec_gw = (
            self.get_in_ip_addr(tenant_id))
        out_ip, out_start, out_end, out_gw, out_sec_gw = (
            self.get_out_ip_addr(tenant_id))
        excl_list = [in_ip, out_ip]

        # Program DCNM to update profile's static IP address on OUT part
        ip_list = self.os_helper.get_subnet_nwk_excl(tenant_id, excl_list)
        srvc_node_ip = self.get_out_srvc_node_ip_addr(tenant_id)
        ret = self.dcnm_obj.update_partition_static_route(
            tenant_name, fw_const.SERV_PART_NAME, ip_list,
            vrf_prof=self.cfg.firewall.fw_service_part_vrf_profile,
            service_node_ip=srvc_node_ip)
        if not ret:
            LOG.error(_LE("Unable to update DCNM ext profile with static "
                          "route %s"), rtr_id)
            self.delete_intf_router(tenant_id, tenant_name, rtr_id)
            return False

        # Program the default GW in router namespace
        ret = False
        attempt = 0
        if out_gw != 0:
            while not ret and attempt <= 3:
                time.sleep(5)
                ret = self.os_helper.program_rtr_default_gw(tenant_id, rtr_id,
                                                            out_gw)
                attempt = attempt + 1
        if not ret:
            LOG.error(_LE("Unable to program default GW in router %s"),
                      rtr_id)
            self.delete_intf_router(tenant_id, tenant_name, rtr_id)
            return False

        # Program router namespace to have all tenant networks to be routed
        # to IN service network
        ret = False
        if in_gw != 0:
            ret = self.os_helper.program_rtr_all_nwk_next_hop(
                tenant_id, rtr_id, in_gw, excl_list)
            if not ret:
                LOG.error(_LE("Unable to program default router next hop %s"),
                          rtr_id)
                self.delete_intf_router(tenant_id, tenant_name, rtr_id)
                return False

        # Send message for router port auto config for in service nwk
        in_net = self.get_in_net_id(tenant_id)
        ret = self.send_rtr_port_msg(tenant_id, tenant_name + '_in', rtr_id,
                                     in_net, in_sub, in_seg, 'up')
        if not ret:
            LOG.error(_LE("Sending router port message failed for in network "
                          "tenant %(tenant)s subnet %(seg)s"),
                      {'tenant': tenant_id, 'seg': in_seg})
            self.delete_intf_router(tenant_id, tenant_name, rtr_id)
            return False

        # Send message for router port auto config for out service nwk
        out_net = self.get_out_net_id(tenant_id)
        ret = self.send_rtr_port_msg(tenant_id, tenant_name + '_out', rtr_id,
                                     out_net, out_sub, out_seg, 'up')
        if not ret:
            LOG.error(_LE("Sending router port message failed for out network "
                          "tenant %(tenant)s subnet %(seg)s"),
                      {'tenant': tenant_id, 'seg': out_seg})
            ret = self.send_rtr_port_msg(tenant_id, tenant_name + '_in',
                                         rtr_id, in_net, in_sub, in_seg,
                                         'down')
            if not ret:
                LOG.error(_LE("Error case, sending router port message for in "
                              "nwk tenant %(tenant)s subnet %(seg)s"),
                          {'tenant': tenant_id, 'seg': in_seg})
            self.delete_intf_router(tenant_id, tenant_name, rtr_id)
            return False
        return True

    def create_fw(self, tenant_id, data):
        """Top level routine called when a FW is created """
        try:
            return self._create_fw(tenant_id, data)
        except Exception as exc:
            LOG.error(_LE("Failed to create FW for device native, tenant "
                          "%(tenant)s data %(data)s Exc %(exc)s"),
                      {'tenant': tenant_id, 'data': data, 'exc': exc})
            return False

    def _delete_fw(self, tenant_id, data):
        """Internal routine called when a FW is deleted """
        LOG.debug("In Delete fw data is %s", data)
        # Do the necessary stuffs in ASA
        tenant_name = data.get('tenant_name')
        in_seg, in_vlan = self.get_in_seg_vlan(tenant_id)
        out_seg, out_vlan = self.get_out_seg_vlan(tenant_id)
        in_net = self.get_in_net_id(tenant_id)
        out_net = self.get_out_net_id(tenant_id)
        in_sub = self.get_in_subnet_id(tenant_id)
        out_sub = self.get_out_subnet_id(tenant_id)

        rtr_id = data.get('router_id')
        if rtr_id is None:
            LOG.error(_LE("Router ID unknown for tenant %s"), tenant_id)
            return False

        if tenant_id not in self.tenant_dict:
            self.create_tenant_dict(tenant_id, rtr_id)
        ret = self.send_rtr_port_msg(tenant_id, tenant_name + '_in', rtr_id,
                                     in_net, in_sub, in_seg, 'down')
        if not ret:
            LOG.error(_LE("Error case, sending router port message for in nwk"
                          " tenant %(tenant)s subnet %(seg)s"),
                      {'tenant': tenant_id, 'seg': in_seg})
        ret = self.send_rtr_port_msg(tenant_id, tenant_name + '_out', rtr_id,
                                     out_net, out_sub, out_seg, 'down')
        if not ret:
            LOG.error(_LE("Sending router port message failed for out network "
                          "tenant %(tenant)s subnet %(seg)s"),
                      {'tenant': tenant_id, 'seg': out_seg})
        # Usually sending message to queue doesn't fail!!!

        rtr_ret = self.delete_intf_router(tenant_id, tenant_name, rtr_id)
        if not rtr_ret:
            LOG.error(_LE("Unable to delete router for tenant %s, error case"),
                      tenant_id)
            return rtr_ret
        del self.tenant_dict[tenant_id]
        return rtr_ret

    def delete_fw(self, tenant_id, data):
        """Top level routine called when a FW is deleted """
        try:
            ret = self._delete_fw(tenant_id, data)
            return ret
        except Exception as exc:
            LOG.error(_LE("Failed to delete FW for device native, tenant "
                          "%(tenant)s data %(data)s Exc %(exc)s"),
                      {'tenant': tenant_id, 'data': data, 'exc': exc})
            return False

    def modify_fw(self, tenant_id, data):
        """
        Modify Firewall attributes.

        Routine called when Firewall attributes gets modified. Nothing to be
        done for native FW.
        """
        LOG.debug("In Modify fw data is %s", data)

    def _program_dcnm_static_route(self, tenant_id, tenant_name):
        """Program DCNM Static Route """
        in_ip, in_start, in_end, in_gw, in_sec_gw = \
            self.get_in_ip_addr(tenant_id)
        if in_gw is None:
            LOG.error(_LE("No FW service GW present"))
            return False
        out_ip, out_start, out_end, out_gw, out_sec_gw = \
            self.get_out_ip_addr(tenant_id)

        # Program DCNM to update profile's static IP address on OUT part
        excl_list = []
        excl_list.append(in_ip)
        excl_list.append(out_ip)
        subnet_lst = self.os_helper.get_subnet_nwk_excl(tenant_id, excl_list,
                                                        excl_part=True)
        # This count is for telling DCNM to insert the static route in a
        # particular position. Total networks created - exclusive list as
        # above - the network that just got created.
        srvc_node_ip = self.get_out_srvc_node_ip_addr(tenant_id)
        ret = self.dcnm_obj.update_partition_static_route(
            tenant_name, fw_const.SERV_PART_NAME, subnet_lst,
            vrf_prof=self.cfg.firewall.fw_service_part_vrf_profile,
            service_node_ip=srvc_node_ip)
        if not ret:
            LOG.error(_LE("Unable to update DCNM ext profile with static "
                          "route"))
            return False
        return True

    def nwk_create_notif(self, tenant_id, tenant_name, cidr):
        """
        Tenant Network create Notification.

        Restart is not supported currently for this. fixme(padkrish)
        """
        rtr_id = self.get_rtr_id(tenant_id, tenant_name)
        if rtr_id is None:
            LOG.error(_LE("Rout ID not present for tenant"))
            return False
        ret = self._program_dcnm_static_route(tenant_id, tenant_name)
        if not ret:
            LOG.error(_LE("Program DCNM with static routes failed "
                          "for router %s"), rtr_id)
            return False

        # Program router namespace to have this network to be routed
        # to IN service network
        in_ip, in_start, in_end, in_gw, in_sec_gw = \
            self.get_in_ip_addr(tenant_id)
        if in_gw is None:
            LOG.error(_LE("No FW service GW present"))
            return False
        ret = self.os_helper.program_rtr_nwk_next_hop(rtr_id, in_gw, cidr)
        if not ret:
            LOG.error(_LE("Unable to program default router next hop %s"),
                      rtr_id)
            return False
        return True

    def nwk_delete_notif(self, tenant_id, tenant_name, nwk_id):
        """
        Tenant Network delete Notification

        Restart is not supported currently for this. fixme(padkrish)
        """
        rtr_id = self.get_rtr_id(tenant_id, tenant_name)
        if rtr_id is None:
            LOG.error(_LE("Rout ID not present for tenant"))
            return False
        ret = self._program_dcnm_static_route(tenant_id, tenant_name)
        if not ret:
            LOG.error(_LE("Program DCNM with static routes failed for "
                          "router %s"), rtr_id)
            return False

        # Program router namespace to have this network to be routed
        # to IN service network
        in_ip, in_start, in_end, in_gw, in_sec_gw = \
            self.get_in_ip_addr(tenant_id)
        if in_gw is None:
            LOG.error(_LE("No FW service GW present"))
            return False
        out_ip, out_start, out_end, out_gw, out_sec_gw = \
            self.get_out_ip_addr(tenant_id)
        excl_list = []
        excl_list.append(in_ip)
        excl_list.append(out_ip)
        subnet_lst = self.os_helper.get_subnet_nwk_excl(tenant_id, excl_list,
                                                        excl_part=True)
        ret = self.os_helper.remove_rtr_nwk_next_hop(rtr_id, in_gw,
                                                     subnet_lst, excl_list)
        if not ret:
            LOG.error(_LE("Unable to program default router next hop %s"),
                      rtr_id)
            return False
        return True
