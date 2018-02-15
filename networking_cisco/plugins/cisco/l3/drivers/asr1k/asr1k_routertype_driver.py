# Copyright 2015 Cisco Systems, Inc.  All rights reserved.
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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import uuidutils
from sqlalchemy.orm import exc
from sqlalchemy.sql import expression as expr

from neutron.db import models_v2

from neutron_lib import constants as l3_constants
from neutron_lib import exceptions as n_exc

from networking_cisco._i18n import _
from networking_cisco import backwards_compatibility as bc
from networking_cisco.backwards_compatibility import l3_const
from networking_cisco.backwards_compatibility import l3_exceptions
from networking_cisco.plugins.cisco.common import cisco_constants
from networking_cisco.plugins.cisco.db.l3 import ha_db
from networking_cisco.plugins.cisco.db.l3 import l3_models
from networking_cisco.plugins.cisco.db.l3.l3_router_appliance_db import (
    L3RouterApplianceDBMixin)
from networking_cisco.plugins.cisco.extensions import routerhostingdevice
from networking_cisco.plugins.cisco.extensions import routerrole
from networking_cisco.plugins.cisco.extensions import routertype
from networking_cisco.plugins.cisco.extensions import routertypeawarescheduler
from networking_cisco.plugins.cisco.l3 import drivers


LOG = logging.getLogger(__name__)


DEVICE_OWNER_GLOBAL_ROUTER_GW = cisco_constants.DEVICE_OWNER_GLOBAL_ROUTER_GW
HOSTING_DEVICE_ATTR = routerhostingdevice.HOSTING_DEVICE_ATTR
ROUTER_ROLE_GLOBAL = cisco_constants.ROUTER_ROLE_GLOBAL
ROUTER_ROLE_LOGICAL_GLOBAL = cisco_constants.ROUTER_ROLE_LOGICAL_GLOBAL
ROUTER_ROLE_HA_REDUNDANCY = cisco_constants.ROUTER_ROLE_HA_REDUNDANCY

TENANT_HSRP_GRP_RANGE = 1
TENANT_HSRP_GRP_OFFSET = 1064
EXT_HSRP_GRP_RANGE = 1
EXT_HSRP_GRP_OFFSET = 1064

N_ROUTER_PREFIX = 'nrouter-'
DEV_NAME_LEN = 14


class TopologyNotSupportedByRouterError(n_exc.Conflict):
    message = _("Requested topology cannot be supported by router.")


class ASR1kL3RouterDriver(drivers.L3RouterBaseDriver):

    def create_router_precommit(self, context, router_context):
        pass

    def create_router_postcommit(self, context, router_context):
        pass

    def update_router_precommit(self, context, router_context):
        pass

    def update_router_postcommit(self, context, router_context):
        # Whenever a gateway is added to, or removed from, a router hosted on
        # a hosting device, we must ensure that a global router is running
        # (for add operation) or not running (for remove operation) on that
        # hosting device.
        current = router_context.current
        if current[HOSTING_DEVICE_ATTR] is None:
            return
        e_context = context.elevated()
        if current['gw_port_id']:
            self._conditionally_add_global_router(e_context, current)
        else:
            self._conditionally_remove_global_router(
                e_context, router_context.original, True)

    def delete_router_precommit(self, context, router_context):
        pass

    def delete_router_postcommit(self, context, router_context):
        pass

    def schedule_router_precommit(self, context, router_context):
        pass

    def schedule_router_postcommit(self, context, router_context):
        # When the hosting device hosts a Neutron router with external
        # connectivity, a "global" router (modeled as a Neutron router) must
        # also run on the hosting device (outside of any VRF) to enable the
        # connectivity.
        current = router_context.current
        if current['gw_port_id'] and current[HOSTING_DEVICE_ATTR] is not None:
            self._conditionally_add_global_router(context.elevated(), current)

    def unschedule_router_precommit(self, context, router_context):
        pass

    def unschedule_router_postcommit(self, context, router_context):
        # When there is no longer any router with external gateway hosted on
        # a hosting device, the global router on that hosting device can also
        # be removed.
        current = router_context.current
        hd_id = current[HOSTING_DEVICE_ATTR]
        if current['gw_port_id'] and hd_id is not None:
            self._conditionally_remove_global_router(context.elevated(),
                                                     current)

    def add_router_interface_precommit(self, context, r_port_context):
        # Inside an ASR1k, VLAN sub-interfaces are used to connect to internal
        # neutron networks. Only one such sub-interface can be created for each
        # VLAN. As the VLAN sub-interface is added to the VRF representing the
        # Neutron router, we must only allow one Neutron router to attach to a
        # particular Neutron subnet/network.
        if (r_port_context.router_context.current[routerrole.ROUTER_ROLE_ATTR]
                == ROUTER_ROLE_HA_REDUNDANCY):
            # redundancy routers can be exempt as we check the user visible
            # routers and the request will be rejected there.
            return
        e_context = context.elevated()
        if r_port_context.current is None:
            sn = self._core_plugin.get_subnet(e_context,
                                              r_port_context.current_subnet_id)
            net_id = sn['network_id']
        else:
            net_id = r_port_context.current['network_id']
        router_id = r_port_context.router_context.current['id']
        filters = {'network_id': [net_id],
                   'device_owner': [bc.constants.DEVICE_OWNER_ROUTER_INTF]}
        for port in self._core_plugin.get_ports(e_context, filters=filters):
            device_id = port['device_id']
            if device_id is None:
                continue
            try:
                router = self._l3_plugin.get_router(e_context, device_id)
                if (router[routerrole.ROUTER_ROLE_ATTR] is None and
                        router['id'] != router_id):
                    # only a single router can connect to multiple subnets
                    # on the same internal network
                    raise TopologyNotSupportedByRouterError()
            except n_exc.NotFound:
                if self._l3_plugin.get_ha_group(e_context, device_id):
                    # Since this is a port for the HA VIP address, we can
                    # safely ignore it
                    continue
                else:
                    LOG.warning(
                        'Spurious router port %s prevents attachement from'
                        ' being performed. Try attaching again later, and '
                        'if the operation then fails again, remove the '
                        'spurious port', port['id'])
                    raise TopologyNotSupportedByRouterError()

    def add_router_interface_postcommit(self, context, r_port_context):
        pass

    def remove_router_interface_precommit(self, context, r_port_context):
        pass

    def remove_router_interface_postcommit(self, context, r_port_context):
        pass

    def create_floatingip_precommit(self, context, fip_context):
        pass

    def create_floatingip_postcommit(self, context, fip_context):
        pass

    def update_floatingip_precommit(self, context, fip_context):
        pass

    def update_floatingip_postcommit(self, context, fip_context):
        pass

    def delete_floatingip_precommit(self, context, fip_context):
        pass

    def delete_floatingip_postcommit(self, context, fip_context):
        pass

    def ha_interface_ip_address_needed(self, context, router, port,
                                       ha_settings_db, ha_group_uuid):
        if port['device_owner'] == bc.constants.DEVICE_OWNER_ROUTER_GW:
            return False
        else:
            return True

    def generate_ha_group_id(self, context, router, port, ha_settings_db,
                             ha_group_uuid):
        if port['device_owner'] in {bc.constants.DEVICE_OWNER_ROUTER_GW,
                                    DEVICE_OWNER_GLOBAL_ROUTER_GW}:
            ri_name = self._router_name(router['id'])[8:DEV_NAME_LEN]
            group_id = int(ri_name, 16) % TENANT_HSRP_GRP_RANGE
            group_id += TENANT_HSRP_GRP_OFFSET
            return group_id
        else:
            net_id_digits = port['network_id'][:6]
            group_id = int(net_id_digits, 16) % EXT_HSRP_GRP_RANGE
            group_id += EXT_HSRP_GRP_OFFSET
            return group_id

    def pre_backlog_processing(self, context):
        LOG.info('Performing pre-backlog processing')
        filters = {routerrole.ROUTER_ROLE_ATTR: [ROUTER_ROLE_GLOBAL]}
        global_routers = self._l3_plugin.get_routers(context, filters=filters)
        if not global_routers:
            LOG.debug("There are no global routers")
            return
        for gr in global_routers:
            filters = {
                HOSTING_DEVICE_ATTR: [gr[HOSTING_DEVICE_ATTR]],
                routerrole.ROUTER_ROLE_ATTR: [ROUTER_ROLE_HA_REDUNDANCY, None]
            }
            invert_filters = {'gw_port_id': [None]}
            num_rtrs = self._l3_plugin.get_routers_count_extended(
                context, filters=filters, invert_filters=invert_filters)
            LOG.debug("Global router %(name)s[%(id)s] with hosting_device "
                      "%(hd)s has %(num)d routers with gw_port set on that "
                      "device",
                      {'name': gr['name'], 'id': gr['id'],
                       'hd': gr[HOSTING_DEVICE_ATTR], 'num': num_rtrs, })
            if num_rtrs == 0:
                LOG.info(
                    "Global router %(name)s[id:%(id)s] is present for "
                    "hosting device %(hd)s but there are no tenant or "
                    "redundancy routers with gateway set on that hosting "
                    "device. Proceeding to delete global router.",
                    {'name': gr['name'], 'id': gr['id'],
                     'hd': gr[HOSTING_DEVICE_ATTR]})
                self._delete_global_router(context, gr['id'])
                filters = {
                    #TODO(bmelande): Filter on routertype of global router
                    #routertype.TYPE_ATTR: [routertype_id],
                    routerrole.ROUTER_ROLE_ATTR: [ROUTER_ROLE_LOGICAL_GLOBAL]}
                log_global_routers = self._l3_plugin.get_routers(
                    context, filters=filters)
                if log_global_routers:
                    log_global_router_id = log_global_routers[0]['id']
                    self._delete_global_router(context, log_global_router_id,
                                               logical=True)

    def post_backlog_processing(self, context):
        pass

    # ---------------- Create workflow functions -----------------

    def _conditionally_add_global_router(self, context, tenant_router):
        # We could filter on hosting device id but we don't so we get all
        # global routers for this router type. We can then use that count to
        # determine which ha priority a new global router should get.
        filters = {
            routertype.TYPE_ATTR: [tenant_router[routertype.TYPE_ATTR]],
            routerrole.ROUTER_ROLE_ATTR: [ROUTER_ROLE_GLOBAL]}
        global_routers = self._l3_plugin.get_routers(
            context, filters=filters)
        hd_to_gr_dict = {r[HOSTING_DEVICE_ATTR]: r for r in global_routers}
        hosting_device_id = tenant_router[HOSTING_DEVICE_ATTR]
        ext_nw_id = tenant_router[l3_const.EXTERNAL_GW_INFO]['network_id']
        global_router = hd_to_gr_dict.get(hosting_device_id)
        logical_global_router = self._get_logical_global_router(context,
                                                                tenant_router)
        self._conditionally_add_auxiliary_external_gateway_port(
            context, logical_global_router, ext_nw_id, tenant_router, True)
        if global_router is None:
            # must create global router on hosting device
            global_router = self._create_global_router(
                context, hosting_device_id, hd_to_gr_dict, tenant_router,
                logical_global_router)
        self._conditionally_add_auxiliary_external_gateway_port(
            context, global_router, ext_nw_id, tenant_router)
        self._l3_plugin.add_type_and_hosting_device_info(context,
                                                         global_router)
        for ni in self._l3_plugin.get_notifiers(context, [global_router]):
            if ni['notifier']:
                ni['notifier'].routers_updated(context, ni['routers'])

    def _conditionally_add_auxiliary_external_gateway_port(
            self, context, global_router, ext_net_id, tenant_router,
            provision_ha=False, port_type=DEVICE_OWNER_GLOBAL_ROUTER_GW):
        # tbe global router may or may not have an interface on the
        # external network that the tenant router uses
        filters = {
            'device_id': [global_router['id']],
            'device_owner': [port_type]}
        ext_net_port = {
            p['network_id']: p for p in
            self._core_plugin.get_ports(context, filters=filters)}
        if ext_net_id in ext_net_port:
            # already connected to the external network, called if
            # new subnets are added to the network
            aux_gw_port = self._update_auxiliary_external_gateway_port(
                context, global_router, ext_net_id, ext_net_port)
            if provision_ha:
                for subnet in aux_gw_port[ext_net_id]['fixed_ips']:
                    self._provision_port_ha(context, aux_gw_port[ext_net_id],
                                            subnet, global_router)
        else:
            # not connected to the external network, so let's fix that
            aux_gw_port = self._create_auxiliary_external_gateway_port(
                context, global_router, ext_net_id, tenant_router, port_type)
            if provision_ha:
                for subnet in aux_gw_port['fixed_ips']:
                    self._provision_port_ha(context, aux_gw_port, subnet,
                                            global_router)

    def _update_auxiliary_external_gateway_port(
            self, context, global_router, ext_net_id, port):
        # When a new subnet is added to an external network, the auxillary
        # gateway port in the global router must be updated with the new
        # subnet_id so an ip from that subnet is assigned to the gateway port
        ext_network = self._core_plugin.get_network(context, ext_net_id)
        fixed_ips = port[ext_net_id]['fixed_ips']
        # fetch the subnets the port is currently connected to
        subnet_id_list = [fixedip['subnet_id'] for fixedip in fixed_ips]
        # add the new subnet
        for subnet_id in ext_network['subnets']:
            if subnet_id not in subnet_id_list:
                fixed_ip = {'subnet_id': subnet_id}
                fixed_ips.append(fixed_ip)
                self._core_plugin.update_port(context, port[ext_net_id]['id'],
                                              ({'port': {'fixed_ips':
                                                         fixed_ips}}))
        return port

    def _create_auxiliary_external_gateway_port(
            self, context, global_router, ext_net_id, tenant_router,
            port_type=DEVICE_OWNER_GLOBAL_ROUTER_GW):
        # When a global router is connected to an external network then a
        # special type of gateway port is created on that network. Such a
        # port is called auxiliary gateway ports. It has an ip address on
        # each subnet of the external network. A (logical) global router
        # never has a traditional Neutron gateway port.
        filters = {
            'device_id': [tenant_router['id']],
            'device_owner': [l3_constants.DEVICE_OWNER_ROUTER_GW]}
        # fetch the gateway port of the *tenant* router so we can determine
        # the CIDR of that port's subnet
        gw_port = self._core_plugin.get_ports(context,
                                              filters=filters)[0]
        fixed_ips = self._get_fixed_ips_subnets(context, gw_port)
        global_router_id = global_router['id']
        aux_gw_port = self._core_plugin.create_port(context, {
            'port': {
                'tenant_id': '',  # intentionally not set
                'network_id': ext_net_id,
                'mac_address': bc.constants.ATTR_NOT_SPECIFIED,
                'fixed_ips': fixed_ips,
                'device_id': global_router_id,
                'device_owner': port_type,
                'admin_state_up': True,
                'name': ''}})
        router_port = bc.RouterPort(
                port_id=aux_gw_port['id'],
                router_id=global_router_id,
                port_type=port_type)
        context.session.add(router_port)
        return aux_gw_port

    def _create_global_router(
            self, context, hosting_device_id, hd_to_gr_dict, tenant_router,
            logical_global_router):
        r_spec = {'router': {
            # global routers are not tied to any tenant
            'tenant_id': '',
            'name': self._global_router_name(hosting_device_id),
            'admin_state_up': True}}
        global_router, r_hd_b_db = self._l3_plugin.do_create_router(
            context, r_spec, tenant_router[routertype.TYPE_ATTR], False,
            True, hosting_device_id, ROUTER_ROLE_GLOBAL)
        # make the global router a redundancy router for the logical
        # global router (which we treat as a hidden "user visible
        # router" (how's that for a contradiction of terms! :-) )
        with context.session.begin(subtransactions=True):
            ha_priority = (
                ha_db.DEFAULT_MASTER_PRIORITY -
                len(hd_to_gr_dict) * ha_db.PRIORITY_INCREASE_STEP)
            r_b_b = ha_db.RouterRedundancyBinding(
                redundancy_router_id=global_router['id'],
                priority=ha_priority,
                user_router_id=logical_global_router['id'])
            context.session.add(r_b_b)
        return global_router

    def _get_logical_global_router(self, context, tenant_router):
        # Since HA is also enabled on the global routers on each hosting device
        # those global routers need HA settings and VIPs. We represent that
        # using a Neutron router that is never instantiated/hosted. That
        # Neutron router is referred to as the "logical global" router.
        filters = {routertype.TYPE_ATTR: [tenant_router[routertype.TYPE_ATTR]],
                   routerrole.ROUTER_ROLE_ATTR: [ROUTER_ROLE_LOGICAL_GLOBAL]}
        logical_global_routers = self._l3_plugin.get_routers(
            context, filters=filters)
        if not logical_global_routers:
            # must create logical global router
            logical_global_router = self._create_logical_global_router(
                context, tenant_router)
        else:
            logical_global_router = logical_global_routers[0]
            self._update_ha_redundancy_level(context, logical_global_router, 1)
        return logical_global_router

    def _create_logical_global_router(self, context, tenant_router):
        r_spec = {'router': {
            # global routers are not tied to any tenant
            'tenant_id': '',
            'name': self._global_router_name('', logical=True),
            'admin_state_up': True,
            # set auto-schedule to false to keep this router un-hosted
            routertypeawarescheduler.AUTO_SCHEDULE_ATTR: False}}
        # notifications should never be sent for this logical router!
        logical_global_router, r_hd_b_db = (
            self._l3_plugin.do_create_router(
                context, r_spec, tenant_router[routertype.TYPE_ATTR],
                False, True, None, ROUTER_ROLE_LOGICAL_GLOBAL))
        with context.session.begin(subtransactions=True):
            r_ha_s_db = ha_db.RouterHASetting(
                router_id=logical_global_router['id'],
                ha_type=cfg.CONF.ha.default_ha_mechanism,
                redundancy_level=1,
                priority=ha_db.DEFAULT_MASTER_PRIORITY,
                probe_connectivity=False,
                probe_target=None,
                probe_interval=None)
            context.session.add(r_ha_s_db)
        return logical_global_router

    def _get_fixed_ips_subnets(self, context, gw_port):
        nw = self._core_plugin.get_network(context, gw_port['network_id'])
        subnets = [{'subnet_id': s} for s in nw['subnets']]
        return subnets

    def _provision_port_ha(self, context, ha_port, subnet, router,
                           ha_binding_db=None):
        ha_group_uuid = uuidutils.generate_uuid()
        router_id = router['id']
        with context.session.begin(subtransactions=True):
            ha_subnet_group = self._get_ha_group_by_ha_port_subnet_id(
                                   context, ha_port['id'], subnet['subnet_id'])
            if ha_subnet_group is not None:
                return
            if ha_binding_db is None:
                ha_binding_db = self._get_ha_binding(context, router_id)
            group_id = self.generate_ha_group_id(
                context, router,
                {'device_owner': DEVICE_OWNER_GLOBAL_ROUTER_GW}, ha_binding_db,
                ha_group_uuid)
            r_ha_g = ha_db.RouterHAGroup(
                id=ha_group_uuid,
                tenant_id='',
                ha_type=ha_binding_db.ha_type,
                group_identity=group_id,
                ha_port_id=ha_port['id'],
                extra_port_id=None,
                subnet_id=subnet['subnet_id'],
                user_router_id=router_id,
                timers_config='',
                tracking_config='',
                other_config='')
            context.session.add(r_ha_g)

    def _get_ha_binding(self, context, router_id):
        with context.session.begin(subtransactions=True):
            query = context.session.query(ha_db.RouterHASetting)
            query = query.filter(
                ha_db.RouterHASetting.router_id == router_id)
            return query.first()

    def _get_ha_group_by_ha_port_subnet_id(self, context, port_id, subnet_id):
        with context.session.begin(subtransactions=True):
            query = context.session.query(ha_db.RouterHAGroup)
            query = query.filter(ha_db.RouterHAGroup.ha_port_id == port_id,
                                 ha_db.RouterHAGroup.subnet_id == subnet_id)
            try:
                r_ha_g = query.one()
            except (exc.NoResultFound, exc.MultipleResultsFound):
                return
            return r_ha_g

    # ---------------- Remove workflow functions -----------------

    def _conditionally_remove_global_router(self, context, tenant_router,
                                            update_operation=False):
        filters = {routertype.TYPE_ATTR: [tenant_router[routertype.TYPE_ATTR]],
                   routerrole.ROUTER_ROLE_ATTR: [ROUTER_ROLE_GLOBAL],
                   HOSTING_DEVICE_ATTR: [tenant_router[HOSTING_DEVICE_ATTR]]}
        global_routers = self._l3_plugin.get_routers(context,
                                                     filters=filters)
        hd_to_gr_dict = {r[HOSTING_DEVICE_ATTR]: r for r in global_routers}
        if global_routers:
            global_router_id = global_routers[0]['id']
            if not tenant_router or not tenant_router[
                    l3_const.EXTERNAL_GW_INFO]:
                # let l3 plugin's periodic backlog processing take care of the
                # clean up of the global router
                return
            ext_net_id = tenant_router[l3_const.EXTERNAL_GW_INFO]['network_id']
            routertype_id = tenant_router[routertype.TYPE_ATTR]
            hd_id = tenant_router[HOSTING_DEVICE_ATTR]
            global_router = hd_to_gr_dict.get(hd_id)
            port_deleted = self._conditionally_remove_auxiliary_gateway_port(
                context, global_router_id, ext_net_id, routertype_id, hd_id,
                update_operation)
            if port_deleted is False:
                # since no auxiliary gateway port was deleted we can
                # abort no since auxiliary gateway port count cannot
                # have reached zero
                return
            filters = {
                'device_id': [global_router_id],
                'device_owner': [DEVICE_OWNER_GLOBAL_ROUTER_GW]}
            num_aux_gw_ports = self._core_plugin.get_ports_count(
                context, filters=filters)
            if num_aux_gw_ports == 0:
                # global router not needed any more so we delete it
                self._delete_global_router(context, global_router_id)
                do_notify = False
            else:
                do_notify = True
            # process logical global router to remove its port
            self._conditionally_remove_auxiliary_gateway_vip_port(
                context, ext_net_id, routertype_id)
            self._l3_plugin.add_type_and_hosting_device_info(context,
                                                             global_router)
            if do_notify is True:
                for ni in self._l3_plugin.get_notifiers(context,
                                                        [global_router]):
                    if ni['notifier']:
                        ni['notifier'].routers_updated(context, ni['routers'])

    def _conditionally_remove_auxiliary_gateway_port(
            self, context, router_id, ext_net_id, routertype_id,
            hosting_device_id, update_operation=False):
        num_rtrs = self._get_gateway_routers_count(
            context, ext_net_id, routertype_id, None, hosting_device_id)
        if ((num_rtrs <= 1 and update_operation is False) or
                (num_rtrs == 0 and update_operation is True)):
            # there are no tenant routers *on ext_net_id* that are serviced by
            # this global router so it's aux gw port can be deleted
            self._delete_auxiliary_gateway_ports(context, router_id,
                                                 ext_net_id)
            return True
        return False

    def _conditionally_remove_auxiliary_gateway_vip_port(
            self, context, ext_net_id, routertype_id):
        filters = {routertype.TYPE_ATTR: [routertype_id],
                   routerrole.ROUTER_ROLE_ATTR: [ROUTER_ROLE_LOGICAL_GLOBAL]}
        log_global_routers = self._l3_plugin.get_routers(context,
                                                         filters=filters)
        if not log_global_routers:
            return
        self._update_ha_redundancy_level(context, log_global_routers[0], -1)
        log_global_router_id = log_global_routers[0]['id']
        num_global_rtrs = self._get_gateway_routers_count(
            context, ext_net_id, routertype_id, ROUTER_ROLE_GLOBAL)
        if num_global_rtrs == 0:
            # there are no global routers *on ext_net_id* that are serviced by
            # this logical global router so it's aux gw VIP port can be deleted
            self._delete_auxiliary_gateway_ports(context, log_global_router_id,
                                                 ext_net_id)
        filters[routerrole.ROUTER_ROLE_ATTR] = [ROUTER_ROLE_GLOBAL]
        total_num_global_rtrs = self._l3_plugin.get_routers_count(
            context, filters=filters)
        if total_num_global_rtrs == 0:
            # there are no global routers left that are serviced by this
            # logical global router so it can be deleted
            self._delete_global_router(context, log_global_router_id, True)
        return False

    def _delete_auxiliary_gateway_ports(
            self, context, router_id, net_id=None,
            port_type=DEVICE_OWNER_GLOBAL_ROUTER_GW):
        filters = {
            'device_id': [router_id],
            'device_owner': [port_type]}
        if net_id is not None:
            filters['network_id'] = [net_id]
        for port in self._core_plugin.get_ports(context, filters=filters):
            try:
                self._core_plugin.delete_port(context, port['id'],
                                              l3_port_check=False)
            except (exc.ObjectDeletedError, n_exc.PortNotFound) as e:
                LOG.info('Unable to delete port for Global router '
                         '%(r_id)s. It has likely been concurrently '
                         'deleted. %(err)s', {'r_id': router_id,
                                              'err': e})

    def _delete_global_router(self, context, global_router_id, logical=False):
        # ensure we clean up any stale auxiliary gateway ports
        self._delete_auxiliary_gateway_ports(context, global_router_id)
        try:
            if logical is True:
                # We use parent class method as no special operations beyond
                # what the base implemenation does are needed for logical
                # global router
                super(L3RouterApplianceDBMixin, self._l3_plugin).delete_router(
                        context, global_router_id)
            else:
                self._l3_plugin.delete_router(
                    context, global_router_id, unschedule=False)
        except (exc.ObjectDeletedError, l3_exceptions.RouterNotFound) as e:
            g_r_type = 'Logical Global' if logical is True else 'Global'
            LOG.info('Unable to delete %(g_r_type)s router %(r_id)s. It '
                     'has likely been concurrently deleted. %(err)s',
                     {'g_r_type': g_r_type, 'r_id': global_router_id,
                     'err': e})
        except Exception as e:
            g_r_type = 'Logical Global' if logical is True else 'Global'
            LOG.debug('Failed to delete %(g_r_type)s router %(r_id). It may '
                      'have been deleted concurrently. Error details: '
                      '%(err)s',
                      {'g_r_type': g_r_type, 'r_id': global_router_id,
                       'err': e})

    def _get_gateway_routers_count(self, context, ext_net_id, routertype_id,
                                   router_role, hosting_device_id=None):
        # Determine number of routers (with routertype_id and router_role)
        # that act as gateway to ext_net_id and that are hosted on
        # hosting_device_id (if specified).
        query = context.session.query(bc.Router)
        if router_role in [None, ROUTER_ROLE_HA_REDUNDANCY]:
            # tenant router roles
            query = query.join(models_v2.Port,
                               models_v2.Port.id == bc.Router.gw_port_id)
            role_filter = expr.or_(
                l3_models.RouterHostingDeviceBinding.role == expr.null(),
                l3_models.RouterHostingDeviceBinding.role ==
                ROUTER_ROLE_HA_REDUNDANCY)
        else:
            # global and logical global routers
            query = query.join(models_v2.Port,
                               models_v2.Port.device_owner == bc.Router.id)
            role_filter = (
                l3_models.RouterHostingDeviceBinding.role == router_role)
        query = query.join(
            l3_models.RouterHostingDeviceBinding,
            l3_models.RouterHostingDeviceBinding.router_id == bc.Router.id)
        query = query.filter(
            role_filter,
            models_v2.Port.network_id == ext_net_id,
            l3_models.RouterHostingDeviceBinding.router_type_id ==
            routertype_id)
        if hosting_device_id is not None:
            query = query.filter(
                l3_models.RouterHostingDeviceBinding.hosting_device_id ==
                hosting_device_id)
        return query.count()

    # ---------------- General support functions -----------------

    def _update_ha_redundancy_level(self, context, logical_global_router,
                                    delta):
        with context.session.begin(subtransactions=True):
            log_g_router_db = self._l3_plugin._get_router(
                context, logical_global_router['id'])
            log_g_router_db.ha_settings.redundancy_level += delta
            context.session.add(log_g_router_db.ha_settings)

    def _router_name(self, router_id):
        return N_ROUTER_PREFIX + router_id

    def _global_router_name(self, hosting_device_id, logical=False):
        if logical is True:
            return cisco_constants.LOGICAL_ROUTER_ROLE_NAME
        else:
            return '%s-%s' % (cisco_constants.ROUTER_ROLE_NAME_PREFIX,
                              hosting_device_id[-cisco_constants.ROLE_ID_LEN:])

    @property
    def _core_plugin(self):
        return bc.get_plugin()

    @property
    def _l3_plugin(self):
        return bc.get_plugin(bc.constants.L3)
