# Copyright 2017 Cisco Systems, Inc.  All rights reserved.
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

import hashlib
import logging
import netaddr
import uuid

from neutron.common import constants
from oslo_config import cfg

from networking_cisco._i18n import _LE, _LI
from networking_cisco.plugins.cisco.cfg_agent import cfg_exceptions as cfg_exc
from networking_cisco.plugins.cisco.cfg_agent.device_drivers.asr1k import (
    aci_asr1k_cfg_syncer as syncer)
from networking_cisco.plugins.cisco.cfg_agent.device_drivers.asr1k import (
    aci_asr1k_snippets as snippets)
from networking_cisco.plugins.cisco.cfg_agent.device_drivers.asr1k import (
    asr1k_routing_driver as asr1k)
from networking_cisco.plugins.cisco.cfg_agent.device_drivers.asr1k import (
    asr1k_snippets)
from networking_cisco.plugins.cisco.cfg_agent.device_drivers.csr1kv import (
    cisco_csr1kv_snippets as csr_snippets)
from networking_cisco.plugins.cisco.cfg_agent.service_helpers import (
    routing_svc_helper as helper)
from networking_cisco.plugins.cisco.common import cisco_constants
from networking_cisco.plugins.cisco.extensions import ha
from networking_cisco.plugins.cisco.extensions import routerrole


LOG = logging.getLogger(__name__)


DEVICE_OWNER_ROUTER_GW = constants.DEVICE_OWNER_ROUTER_GW
HA_INFO = 'ha_info'
NAT_POOL_PREFIX = 'snat_id-'
ROUTER_ROLE_ATTR = routerrole.ROUTER_ROLE_ATTR
ROUTER_ROLE_HA_REDUNDANCY = cisco_constants.ROUTER_ROLE_HA_REDUNDANCY
ROUTER_ROLE_GLOBAL = cisco_constants.ROUTER_ROLE_GLOBAL


class AciASR1kRoutingDriver(asr1k.ASR1kRoutingDriver):

    def __init__(self, **device_params):
        super(AciASR1kRoutingDriver, self).__init__(**device_params)
        self._fullsync = False
        self._deployment_id = "zxy"
        self.hosting_device = {'id': device_params.get('id'),
                               'device_id': device_params.get('device_id')}
        self._template_dict = {'vrf': self._set_vrf,
                               'vrf_pid': self._set_vrf_pid,
                               'rid': self._set_router_id}
        self._router_ids_by_snat_id = {}
        self._subnets_by_ext_net = {}
        # We need to limit the prefix to the overall DEV_NAME_LEN
        self.NAT_POOL_ID_LEN = self.DEV_NAME_LEN - len(NAT_POOL_PREFIX)

    # ============== Public functions ==============
    def router_added(self, ri):
        # No-Op -- this is managed by the service handler
        pass

    def internal_network_added(self, ri, port):
        if not self._is_port_v6(port):
            if self._is_global_router(ri):
                # The global router is modeled as the default vrf
                # in the ASR.  When an external gateway is configured,
                # a normal "internal" interface is created in the default
                # vrf that is in the same subnet as the ext-net.
                LOG.debug("global router handling")
                self.external_gateway_added(ri, port)
            else:
                LOG.debug("Adding IPv4 internal network port: %(port)s "
                          "for router %(r_id)s", {'port': port, 'r_id': ri.id})
                self._create_sub_interface(
                    ri, port, is_external=False)
                # If interface config is present, then use that
                # to perform additional configuration to the interface
                # (used to configure dynamic routing per sub-interface).
                # If it's not present, assume static routing is used,
                # so configure routes for the tenant networks
                if_configs = port['hosting_info'].get('interface_config')
                if if_configs and isinstance(if_configs, list):
                    self._add_interface_config(ri, port, if_configs)
                else:
                    self._add_tenant_net_route(ri, port)

    def external_gateway_removed(self, ri, ext_gw_port):
        if not self._is_global_router(ri):
            g_configs = ext_gw_port['hosting_info'].get('global_config')
            if g_configs and isinstance(g_configs, list):
                self._remove_global_config(ri, ext_gw_port, g_configs)
            if ext_gw_port['hosting_info'].get('snat_subnets'):
                self._set_snat_pools_from_hosting_info(ri, ext_gw_port, True)
            self._set_subnets_for_ext_net(ri, ext_gw_port)
        else:
            self._remove_secondary_ips(ri, ext_gw_port)
        super(AciASR1kRoutingDriver, self).external_gateway_removed(ri,
            ext_gw_port)

    def _handle_external_gateway_added_global_router(self, ri, ext_gw_port):
        super(AciASR1kRoutingDriver,
              self)._handle_external_gateway_added_global_router(ri,
                                                                 ext_gw_port)
        self._add_secondary_ips(ri, ext_gw_port)

    def _add_secondary_ips(self, ri, ext_gw_port):
        net_name = ext_gw_port.get('hosting_info', {}).get('network_name')
        if not net_name:
            return
        subnets = self._subnets_by_ext_net.get(net_name, [])
        for subnet in subnets:
            net = netaddr.IPNetwork(subnet['cidr'])
            secondary_ip = netaddr.IPAddress(net.value +
                                             (net.hostmask.value - 1))
            self._asr_do_add_secondary_ip(secondary_ip,
                                          ext_gw_port, net.netmask)

    def _remove_secondary_ips(self, ri, ext_gw_port):
        net_name = ext_gw_port.get('hosting_info', {}).get('network_name')
        if not net_name:
            return
        subnets = self._subnets_by_ext_net.get(net_name, [])
        for subnet in subnets:
            net = netaddr.IPNetwork(subnet['cidr'])
            secondary_ip = netaddr.IPAddress(net.value +
                                             (net.hostmask.value - 1))
            self._asr_do_remove_secondary_ip(secondary_ip,
                                             ext_gw_port, net.netmask)

    def _create_sub_interface(self, ri, port, is_external=False, gw_ip=""):
        vlan = self._get_interface_vlan_from_hosting_port(port)
        if (self._fullsync and
                int(vlan) in self._existing_cfg_dict['interfaces']):
            LOG.info(_LI("Sub-interface already exists, skipping"))
            return
        vrf_name = self._get_vrf_name(ri)
        hsrp_ip = self._get_interface_ip_from_hosting_port(ri, port,
            is_external=is_external)
        net_mask = self._get_interface_subnet_from_hosting_port(
            ri, port, is_external=is_external)
        # If the router's gateway isn't set, then we can't get the
        # relevant information -- skip configuration
        if hsrp_ip is None or net_mask is None:
            return

        sub_interface = self._get_interface_name_from_hosting_port(port)
        self._do_create_sub_interface(sub_interface, vlan, vrf_name, hsrp_ip,
                                      net_mask, is_external)
        # Always do HSRP
        if ri.router.get(ha.ENABLED, False):
            if port.get(ha.HA_INFO) is not None:
                self._add_ha_hsrp(ri, port, is_external=is_external)
            else:
                # We are missing HA data, candidate for retrying
                params = {'r_id': ri.router_id, 'p_id': port['id'],
                          'port': port}
                raise cfg_exc.HAParamsMissingException(**params)

    def _add_interface_config(self, ri, port, if_configs):
        sub_interface = self._get_interface_name_from_hosting_port(port)
        for if_config in if_configs:
            conf_str = (snippets.SET_INTERFACE_CONFIG % (sub_interface,
                (self._replace_template_vars(ri, port, if_config))))
            self._edit_running_config(conf_str, 'SET_INTERFACE_CONFIG')

    def _remove_interface_config(self, ri, port, if_configs):
        sub_interface = self._get_interface_name_from_hosting_port(port)
        for if_config in if_configs:
            conf_str = (snippets.REMOVE_INTERFACE_CONFIG % (sub_interface,
                (self._replace_template_vars(ri, port, if_config))))
            self._edit_running_config(conf_str, 'REMOVE_INTERFACE_CONFIG')

    def _add_ha_hsrp(self, ri, port, is_external=False):
        priority = None
        if ri.router.get(ROUTER_ROLE_ATTR) in (ROUTER_ROLE_HA_REDUNDANCY,
                                               ROUTER_ROLE_GLOBAL):
            for router in ri.router[ha.DETAILS][ha.REDUNDANCY_ROUTERS]:
                if ri.router['id'] == router['id']:
                    priority = router[ha.PRIORITY]
        else:
            priority = ri.router[ha.DETAILS][ha.PRIORITY]
        port_ha_info = port[ha.HA_INFO]
        group = port_ha_info['group']
        ip = self._get_interface_ip_from_hosting_port(ri, port,
            is_external=is_external)
        if is_external:
            ha_ip = port_ha_info['ha_port']['fixed_ips'][0]['ip_address']
        else:
            # TODO(tbachman): needs fixing
            ha_ip = netaddr.IPAddress(netaddr.IPAddress(ip).value + 1).format()
        vlan = self._get_interface_vlan_from_hosting_port(port)
        if ip and group and priority:
            vrf_name = self._get_vrf_name(ri)
            sub_interface = self._get_interface_name_from_hosting_port(port)
            self._do_set_ha_hsrp(sub_interface, vrf_name,
                                 priority, group, ha_ip, vlan)

    def _add_tenant_net_route(self, ri, port):
        if self._fullsync and (ri.router_id in
                               self._existing_cfg_dict['routes']):
            LOG.debug("Tenant network route already exists, skipping")
            return
        cidr = port['subnets'][0]['cidr']
        if cidr:
            vrf_name = self._get_vrf_name(ri)
            out_itfc = self._get_interface_name_from_hosting_port(port)
            ip = netaddr.IPNetwork(cidr)
            subnet, mask = ip.network.format(), ip.netmask.format()
            gateway_ip = self._get_interface_gateway_ip_from_hosting_port(
                ri, port)
            # If the gateway isn't set, then we can't set the route
            if not gateway_ip:
                return
            conf_str = snippets.SET_TENANT_ROUTE_WITH_INTF % (
                vrf_name, subnet, mask, out_itfc, gateway_ip)
            self._edit_running_config(conf_str, 'SET_TENANT_ROUTE_WITH_INTF')

    def _remove_tenant_net_route(self, ri, port):
        cidr = port['subnets'][0]['cidr']
        if cidr:
            vrf_name = self._get_vrf_name(ri)
            out_itfc = self._get_interface_name_from_hosting_port(port)
            ip = netaddr.IPNetwork(cidr)
            subnet, mask = ip.network.format(), ip.netmask.format()
            gateway_ip = self._get_interface_gateway_ip_from_hosting_port(
                ri, port)
            conf_str = snippets.REMOVE_TENANT_ROUTE_WITH_INTF % (
                vrf_name, subnet, mask, out_itfc, gateway_ip)
            self._edit_running_config(conf_str,
                                      'REMOVE_TENANT_ROUTE_WITH_INTF')

    def _get_info_port(self, ri, port):
        return ri.ex_gw_port or ri.router.get('gw_port', port)

    def _get_interface_ip_from_hosting_port(self, ri, port, is_external=False):
        """
        Extract the underlying subinterface IP for a port.

        Get the IP for the ASR's subinterface using the appropriate field.
        For external ports, it's the first fixed IP. For internal ports,
        this is obtained from the hosting_info attribute's 'cidr_exposed'
        property.
        """
        if is_external:
            return port['fixed_ips'][0]['ip_address']
        else:
            try:
                info_port = self._get_info_port(ri, port)
                cidr = info_port['hosting_info']['cidr_exposed']
                return cidr.split("/")[0]
            except KeyError as e:
                params = {'key': e}
                raise cfg_exc.DriverExpectedKeyNotSetException(**params)

    def _get_interface_gateway_ip_from_hosting_port(self, ri, port):
        """
        Extract the next hop IP for a subinterface.

        Get the gateway/next hop IP for the subinterface. This
        is contained in the hosting_info attribute's 'gateway_ip'
        property.
        """
        try:
            info_port = self._get_info_port(ri, port)
            ip = info_port['hosting_info']['gateway_ip']
            return ip
        except KeyError as e:
            params = {'key': e}
            raise cfg_exc.DriverExpectedKeyNotSetException(**params)

    def _get_interface_subnet_from_hosting_port(self, ri,
                                                port, is_external=False):
        """
        Extract the CIDR information for the interposing subnet.

        Get the subnet for the subinterface. This is obtained from the
        hosting_info attribute's 'cidr_exposed' property.
        """
        if is_external:
            return netaddr.IPNetwork(port['ip_cidr']).netmask.format()
        else:
            try:
                info_port = self._get_info_port(ri, port)
                cidr_exposed = info_port['hosting_info']['cidr_exposed']
                return netaddr.IPNetwork(cidr_exposed).netmask.format()
            except KeyError as e:
                params = {'key': e}
                raise cfg_exc.DriverExpectedKeyNotSetException(**params)

    def internal_network_removed(self, ri, port, itfc_deleted=True):
        if_configs = port['hosting_info'].get('interface_config')
        if if_configs and isinstance(if_configs, list) and itfc_deleted:
            self._remove_interface_config(ri, port, if_configs)
        else:
            self._remove_tenant_net_route(ri, port)
        if itfc_deleted:
            self._remove_sub_interface(port)

    def cleanup_invalid_cfg(self, hd, routers):

        cfg_syncer = syncer.ConfigSyncer(routers, self, hd)
        cfg_syncer.delete_invalid_cfg()

    # ============== Internal "preparation" functions  ==============

    def _create_vrf(self, ri):
        # just get the VRF -- creation is done
        # by the service handler
        self._get_vrf_name(ri)

    def _do_create_vrf(self, vrf_name):
        vrf_str = snippets.VRF_CONFIG % vrf_name
        conf_str = csr_snippets.CREATE_VRF % vrf_name
        if not self._cfg_exists(vrf_str):
            self._edit_running_config(conf_str, 'CREATE_VRF')

    def _get_vrf_name(self, ri):
        """
        For ACI, there are different mappings for VRFs. The
        VRF is passed down as a parameter of the gateway port.
        As a result, the VRF isn't available until the gateway
        port on the router has been set, so defer setting it if
        we don't have this parameter yet.
        """
        # Look at the router just passed to us first, and if
        # that isn't there, look for the router we used to have
        # (indicates that the gateway port is being cleared, but
        # means that the infromation is still useful)
        if (ri.router.get('gw_port') and
                ri.router['gw_port'].get('hosting_info') and
                ri.router['gw_port']['hosting_info'].get('vrf_id')):
            ext_gw_port = ri.router['gw_port']
        elif (ri.ex_gw_port and ri.ex_gw_port.get('hosting_info') and
                ri.ex_gw_port['hosting_info'].get('vrf_id')):
            ext_gw_port = ri.ex_gw_port
        else:
            return None
        vrf_tag = ext_gw_port['hosting_info']['vrf_id']
        vlan = ext_gw_port['hosting_info'].get('segmentation_id')
        if not vlan:
            return None
        # Create a unique VRF by adding the VLAN to the existing
        # VRF ID, and creating a new UUID using an MD5 hash
        vrf_string = vrf_tag.encode('utf-8') + hex(vlan)[2:]
        vrf_tag = str(uuid.uuid3(uuid.NAMESPACE_DNS, vrf_string))
        vrf_id = (helper.N_ROUTER_PREFIX + vrf_tag)[:self.DEV_NAME_LEN]
        is_multi_region_enabled = cfg.CONF.multi_region.enable_multi_region

        if is_multi_region_enabled:
            region_id = cfg.CONF.multi_region.region_id
            vrf_name = "%s-%s" % (vrf_id, region_id)
        else:
            vrf_name = vrf_id
        return vrf_name

    def _add_floating_ip(self, ri, ex_gw_port, floating_ip, fixed_ip):
        vrf_name = self._get_vrf_name(ri)
        self._asr_do_add_floating_ip(floating_ip, fixed_ip,
                                     vrf_name, ex_gw_port)

        # We need to make sure that our external interface has an IP address
        # on the same subnet as the floating IP (needed in order to handle ARPs
        # on the external interface). Search for the matching subnet for this
        # FIP, and use the highest host address as a secondary address on that
        # interface
        subnets = ri.router['gw_port'].get('extra_subnets', [])
        subnet = self._get_matching_subnet(subnets, floating_ip)
        if subnet:
            secondary_ip = netaddr.IPAddress(subnet.value +
                                             (subnet.hostmask.value - 1))
            self._asr_do_add_secondary_ip(secondary_ip,
                                          ex_gw_port, subnet.netmask)

    def _remove_floating_ip(self, ri, ext_gw_port, floating_ip, fixed_ip):
        vrf_name = self._get_vrf_name(ri)
        self._asr_do_remove_floating_ip(floating_ip,
                                        fixed_ip,
                                        vrf_name,
                                        ext_gw_port)
        # A secondary IP address may need to be removed from the external
        # interface. Check the known subnets to see which one contains
        # the floating IP, then search for any other floating IPs on that
        # subnet. If there aren't any, then the secondary IP can safely
        # be removed.
        subnets = ri.router['gw_port'].get('extra_subnets', [])
        subnet = self._get_matching_subnet(subnets, floating_ip)
        if not subnet:
            return
        secondary_ip = netaddr.IPAddress(subnet.value +
                                         (subnet.hostmask.value - 1))
        # We only remove the secondary IP if there aren't any more FIPs
        # for this subnet
        # FIXME(tbachman): should check across all routers
        # FIXME(tbachman): should already have this list (local cache?)
        other_fips = False
        for curr_fip in ri.router.get(constants.FLOATINGIP_KEY, []):
            # skip the FIP we're deleting
            if curr_fip['floating_ip_address'] == floating_ip:
                continue
            fip = netaddr.IPAddress(curr_fip['floating_ip_address'])
            if (fip.value & subnet.netmask.value) == subnet.value:
                other_fips = True
                break
        if other_fips:
            return

        self._asr_do_remove_secondary_ip(secondary_ip,
                                         ext_gw_port, subnet.netmask)

    def _get_matching_subnet(self, subnets, ip):
        target_ip = netaddr.IPAddress(ip)
        for subnet in subnets:
            net = netaddr.IPNetwork(subnet['cidr'])
            if target_ip in net:
                return net
        return None

    def _asr_do_add_secondary_ip(self, secondary_ip, port, netmask):
        sub_interface = self._get_interface_name_from_hosting_port(port)
        conf_str = (snippets.ADD_SECONDARY_IP % (
                       sub_interface, secondary_ip, netmask))
        self._edit_running_config(conf_str, 'ADD_SECONDARY_IP')

    def _asr_do_remove_secondary_ip(self, secondary_ip, port, netmask):
        sub_interface = self._get_interface_name_from_hosting_port(port)
        conf_str = (snippets.REMOVE_SECONDARY_IP % (
                       sub_interface, secondary_ip, netmask))
        self._edit_running_config(conf_str, 'REMOVE_SECONDARY_IP')

    def _asr_do_add_floating_ip(self, floating_ip,
                                fixed_ip, vrf, ex_gw_port):
        """
        To implement a floating ip, an ip static nat is configured in the
        underlying router ex_gw_port contains data to derive the vlan
        associated with related subnet for the fixed ip.  The vlan in turn
        is applied to the redundancy parameter for setting the IP NAT.
        """
        LOG.debug("add floating_ip: %(fip)s, fixed_ip: %(fixed_ip)s, "
                  "vrf: %(vrf)s, ex_gw_port: %(port)s",
                  {'fip': floating_ip, 'fixed_ip': fixed_ip, 'vrf': vrf,
                   'port': ex_gw_port})

        if ex_gw_port.get(ha.HA_INFO):
            hsrp_grp = ex_gw_port[ha.HA_INFO]['group']
            vlan = ex_gw_port['hosting_info']['segmentation_id']

            confstr = (asr1k_snippets.SET_STATIC_SRC_TRL_NO_VRF_MATCH %
                (fixed_ip, floating_ip, vrf, hsrp_grp, vlan))
        else:
            confstr = (snippets.SET_STATIC_SRC_TRL_NO_VRF_MATCH %
                (fixed_ip, floating_ip, vrf))
        self._edit_running_config(confstr, 'SET_STATIC_SRC_TRL_NO_VRF_MATCH')

    def _asr_do_remove_floating_ip(self, floating_ip,
                                   fixed_ip, vrf, ex_gw_port):
        if ex_gw_port.get(ha.HA_INFO):
            hsrp_grp = ex_gw_port[ha.HA_INFO]['group']
            vlan = ex_gw_port['hosting_info']['segmentation_id']

            confstr = (asr1k_snippets.REMOVE_STATIC_SRC_TRL_NO_VRF_MATCH %
                (fixed_ip, floating_ip, vrf, hsrp_grp, vlan))
        else:
            confstr = (snippets.REMOVE_STATIC_SRC_TRL_NO_VRF_MATCH %
                (fixed_ip, floating_ip, vrf))
        self._edit_running_config(confstr,
                                  'REMOVE_STATIC_SRC_TRL_NO_VRF_MATCH')

    def _snat_prefix(self, subnet):
        snat_id = NAT_POOL_PREFIX + subnet['id'][:self.NAT_POOL_ID_LEN]
        if cfg.CONF.multi_region.enable_multi_region:
            prefix = "%s-%s" % (snat_id, cfg.CONF.multi_region.region_id)
        else:
            prefix = snat_id
        return prefix

    def _get_snat_prefix(self, ri, ext_port):
        subnets = ext_port['hosting_info'].get('snat_subnets', [])
        if subnets:
            # TODO(tbachman) Currently we'll only have a single
            # subnet, but this may change in the future
            return self._snat_prefix(subnets[0])

    def _do_set_snat_pool(self, pool_name, pool_start,
                          pool_end, pool_net, is_delete):
        try:
            if is_delete:
                conf_str = asr1k_snippets.DELETE_NAT_POOL % (
                    pool_name, pool_start, pool_end, pool_net)
                # TODO(update so that hosting device name is passed down)
                self._edit_running_config(conf_str, 'DELETE_NAT_POOL')

            else:
                conf_str = asr1k_snippets.CREATE_NAT_POOL % (
                    pool_name, pool_start, pool_end, pool_net)
                # TODO(update so that hosting device name is passed down)
                self._edit_running_config(conf_str, 'CREATE_NAT_POOL')
        except Exception as cse:
            LOG.error(_LE("Temporary disable NAT_POOL exception handling: "
                          "%s"), cse)

    def _set_snat_pools_from_hosting_info(self, ri, gw_port, is_delete):
        # TODO(tbachma ): unique naming for more than one pool
        for subnet in gw_port['hosting_info'].get('snat_subnets', []):
            if is_delete:
                self._remove_rid_from_snat_list(ri, gw_port, subnet)
            else:
                self._add_rid_to_snat_list(ri, gw_port, subnet)

    def _set_nat_pool(self, ri, gw_port, is_delete):
        # NOOP -- set when external GW is set
        pass

    def _handle_external_gateway_added_normal_router(self, ri, ext_gw_port):
        super(AciASR1kRoutingDriver,
              self)._handle_external_gateway_added_normal_router(ri,
                  ext_gw_port)
        # Global conifguration parameters are passed using the user
        # router. Check to see if there is any global config, and if it's
        # not already configured, add it in
        g_configs = ext_gw_port['hosting_info'].get('global_config')
        if g_configs and isinstance(g_configs, list):
            self._set_global_config(ri, ext_gw_port, g_configs)
        if ext_gw_port['hosting_info'].get('snat_subnets'):
            self._set_snat_pools_from_hosting_info(ri, ext_gw_port, False)
        self._set_subnets_for_ext_net(ri, ext_gw_port)

    def _set_global_config(self, ri, port, g_configs):
        for g_config in g_configs:
            asr_str = [snippets.GLOBAL_CONFIG_PREFIX]
            self._config_cmd(ri, port, asr_str, g_config)
            asr_str.append(snippets.GLOBAL_CONFIG_POSTFIX)
            self._edit_running_config(''.join(asr_str), 'SET_GLOBAL_CONFIG')

    def _remove_global_config(self, ri, port, g_configs):
        for g_config in g_configs:
            asr_str = [snippets.GLOBAL_CONFIG_PREFIX]
            self._config_cmd(ri, port, asr_str, g_config, remove=True)
            asr_str.append(snippets.GLOBAL_CONFIG_POSTFIX)
            self._edit_running_config(''.join(asr_str), 'REMOVE_GLOBAL_CONFIG')

    def _replace_template_vars(self, ri, port, config):
        kwargs = {}
        for key in self._template_dict.keys():
            if '{' + key + '}' in config:
                kwargs[key] = self._template_dict[key](ri, port, config)
        return config.format(**kwargs)

    def _config_cmd(self, ri, port, asr_str, g_config, remove=False):
        if isinstance(g_config, list):
            for config in g_config:
                self._config_cmd(ri, port, asr_str, config, remove)
        else:
            if remove:
                snippet = snippets.REMOVE_GLOBAL_CONFIG
            else:
                snippet = snippets.SET_GLOBAL_CONFIG
            asr_str.append(snippet %
                (self._replace_template_vars(ri, port, g_config)))

    def _set_vrf(self, ri, port, config):
        return self._get_vrf_name(ri)

    def _set_vrf_pid(self, ri, port, config):
        # Convert a VRF to a process ID for a router instance
        vrf = self._get_vrf_name(ri).replace('nrouter-', '')[:6]
        # strip to 4 characters to limit pid to 16-bit value
        # (limit on ASR)
        # TODO(tbachman): fix to ensure PID uniqueness
        pid = int(hashlib.md5(vrf.encode('utf-8')).hexdigest()[:4], 16)
        return str(pid)

    def _set_router_id(self, ri, port, config):
        # Convert a VRF to a router ID for a router instance
        vrf = self._get_vrf_name(ri).replace('nrouter-', '')[:6]
        rid = netaddr.IPAddress(int(vrf, 16))
        return str(rid)

    def _get_snat_pool_name(self, subnet):
        snat_prefix = self._snat_prefix(subnet)
        return "%s_nat_pool" % (snat_prefix)

    def _add_rid_to_snat_list(self, ri, ext_gw_port, subnet):
        net = netaddr.IPNetwork(subnet['cidr'])
        snat_id = self._get_snat_pool_name(subnet)
        if not self._router_ids_by_snat_id.get(snat_id):
            LOG.debug("++ CREATING SNAT POOL %s" % snat_id)
            self._do_set_snat_pool(snat_id, subnet['ip'],
                                   subnet['ip'], str(net.netmask), False)
        self._router_ids_by_snat_id.setdefault(snat_id, set()).add(
            ri.router['id'])

    def _remove_rid_from_snat_list(self, ri, ext_gw_port, subnet):
        net = netaddr.IPNetwork(subnet['cidr'])
        snat_id = self._get_snat_pool_name(subnet)
        if self._router_ids_by_snat_id.get(snat_id) and (
                ri.router['id'] in self._router_ids_by_snat_id[snat_id]):
            self._router_ids_by_snat_id[snat_id].remove(ri.router['id'])
            # If this is the last router for this SNAT ID, then we can
            # safely delete the nat pool from the router config
            # (handled by the driver)
            if not self._router_ids_by_snat_id.get(snat_id):
                LOG.debug("++ REMOVING SNAT POOL %s" % snat_id)
                self._do_set_snat_pool(snat_id, subnet['ip'],
                                       subnet['ip'], str(net.netmask), True)
                del self._router_ids_by_snat_id[snat_id]

    def _make_subnet_dict(self, snat):
        # Set the GW IP, assuming it's .1
        net = netaddr.IPNetwork(snat['cidr'])
        gateway_ip = str(netaddr.IPAddress(net.value + 1))
        return {"ipv6_ra_mode": None,
                "cidr": snat['cidr'],
                "gateway_ip": gateway_ip,
                "id": snat['id']}

    def _set_subnets_for_ext_net(self, ri, ext_gw_port):
        """Collect subnets for a given external network.

        This handles both setting and clearing of the
        subnets configured on an external network. It includes
        the SNAT subnets. All routers conecting to a given
        external network should have the same state for subnets,
        so setting and clearing should be achieved through
        using the state from any router connected to that network.
        """
        net_name = ext_gw_port['hosting_info']['network_name']
        self._subnets_by_ext_net[net_name] = []
        if ri.ex_gw_port and not ri.router.get('gw_port'):
            return
        if ext_gw_port['extra_subnets']:
            self._subnets_by_ext_net[net_name] = ext_gw_port['extra_subnets']
        for snat in ext_gw_port['hosting_info'].get('snat_subnets', []):
            subnet = self._make_subnet_dict(snat)
            if subnet['cidr'] == ext_gw_port['subnets'][0]['cidr']:
                continue
            if subnet not in self._subnets_by_ext_net[net_name]:
                self._subnets_by_ext_net[net_name].append(subnet)
