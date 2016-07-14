# Copyright 2016 Cisco Systems, Inc.  All rights reserved.
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

from oslo_log import log as logging
from oslo_utils import importutils

from neutron.common import constants as l3_constants
from neutron.common import exceptions as n_exc
from neutron import context as nctx
from neutron.extensions import l3
from neutron import manager

from networking_cisco.plugins.cisco.common import cisco_constants
from networking_cisco.plugins.cisco.db.l3 import ha_db
from networking_cisco.plugins.cisco.extensions import routerhostingdevice
from networking_cisco.plugins.cisco.extensions import routerrole
from networking_cisco.plugins.cisco.extensions import routertype
from networking_cisco.plugins.cisco.extensions import routertypeawarescheduler
from networking_cisco.plugins.cisco.l3.drivers.asr1k import (
    asr1k_routertype_driver as asr1k)
from networking_cisco._i18n import _LE, _LI

LOG = logging.getLogger(__name__)

HOSTING_DEVICE_ATTR = routerhostingdevice.HOSTING_DEVICE_ATTR
ROUTER_ROLE_GLOBAL = cisco_constants.ROUTER_ROLE_GLOBAL
ROUTER_ROLE_LOGICAL_GLOBAL = cisco_constants.ROUTER_ROLE_LOGICAL_GLOBAL


APIC_ML2_L3DRIVER_KLASS = (
    'apic_ml2.neutron.services.l3_router.apic_driver.ApicL3Driver')
GBP_L3DRIVER_KLASS = (
    'gbpservice.neutron.services.l3_router.apic_driver.ApicGBPL3Driver')
HOSTING_DEVICE_ATTR = routerhostingdevice.HOSTING_DEVICE_ATTR


class AciASR1kL3RouterDriver(asr1k.ASR1kL3RouterDriver):

    def __init__(self):
        super(AciASR1kL3RouterDriver, self).__init__()
        self._apic_driver = None

    @property
    def apic_driver(self):
        """Get APIC driver

        There are different drivers for the GBP workflow
        and Neutron workflow for APIC. First see if the GBP
        workflow is active, and if so get the APIC driver for it.
        If the GBP service isn't installed, try to get the driver
        from the Neutron (APIC ML2) workflow.
        """
        if not self._apic_driver:
            try:
                if manager.NeutronManager.get_service_plugins()[
                    'GROUP_POLICY'].policy_driver_manager.policy_drivers[
                        'apic'].obj:
                    self._apic_driver = importutils.import_object(
                        GBP_L3DRIVER_KLASS,
                        nctx.get_admin_context_without_session()
                    )
                    self._apic_driver._plugin = self._l3_plugin
            except KeyError:
                    LOG.info(_LI("GBP service plugin not present -- skipping "
                                 "dynamic load of GBP L3 APIC driver."))
            except Exception:
                    LOG.error(_LE("GBP service plugin present, but dynamic "
                                  "load of GBP L3 APIC driver failed."))
                    return self._apic_driver
            if not self._apic_driver:
                try:
                    core_plugin = self._l3_plugin._core_plugin
                    if core_plugin.mechanism_manager.mech_drivers[
                            'cisco_apic_ml2'].obj:
                        self._apic_driver = importutils.import_object(
                            APIC_ML2_L3DRIVER_KLASS,
                            nctx.get_admin_context_without_session()
                        )
                        self._apic_driver._plugin = self._l3_plugin
                except KeyError:
                        LOG.error(_LE("APIC ML2 service plugin not present: "
                                      "no APIC L3 driver could be found "
                                      "(skipping dynamic load of APIC ML2 "
                                      "L3 driver."))
                except Exception:
                    LOG.error(_LE("APIC ML2 service plugin present, but "
                                  "dynamic load of APIC ML2 L3 driver "
                                  "failed."))
        return self._apic_driver

    def _get_router_id_from_port(self, r_port_context):
        current = r_port_context.current
        if (current['device_owner'] == l3_constants.DEVICE_OWNER_ROUTER_GW or
            current['device_owner'] == l3_constants.DEVICE_OWNER_ROUTER_INTF):
            return current['device_id']
        else:
            raise n_exc.UnsupportedPortDeviceOwner(
                op="remove router interface", port_id=current['id'],
                device_owner=current['device_owner'])

    def create_router_precommit(self, context, router_context):
        pass

    def create_router_postcommit(self, context, router_context):
        pass

    def update_router_precommit(self, context, router_context):
        pass

    def update_router_postcommit(self, context, router_context):
        current = router_context.current
        if current.get(HOSTING_DEVICE_ATTR) is None:
            return
        super(AciASR1kL3RouterDriver, self).update_router_postcommit(
            context, router_context)

        context._plugin = self
        if current and current['tenant_id'] != '':
            self.apic_driver.update_router_postcommit(context, current)

    def delete_router_precommit(self, context, router_context):
        # TODO(tbachman): remove setting of _plugin?
        context._plugin = self
        router = router_context.current
        router_id = router['id']
        if router['tenant_id'] != '':
            self.apic_driver.delete_router_precommit(context, router_id)

    def delete_router_postcommit(self, context, router_context):
        pass

    def schedule_router_precommit(self, context, router_context):
        pass

    def schedule_router_postcommit(self, context, router_context):
        super(AciASR1kL3RouterDriver, self).schedule_router_postcommit(
            context, router_context)

    def unschedule_router_precommit(self, context, router_context):
        pass

    def unschedule_router_postcommit(self, context, router_context):
        super(AciASR1kL3RouterDriver, self).unschedule_router_postcommit(
            context, router_context)

    def add_router_interface_precommit(self, context, r_port_context):
        super(AciASR1kL3RouterDriver, self).add_router_interface_precommit(
            context, r_port_context)
        pass

    def add_router_interface_postcommit(self, context, r_port_context):
        port = r_port_context.current
        router_id = r_port_context.current_router
        interface_info = {'port_id': port['id']}
        if port['tenant_id'] != '':
            self.apic_driver.add_router_interface_postcommit(
                context, router_id, interface_info)

    def remove_router_interface_precommit(self, context, r_port_context):
        port = r_port_context.current
        router_id = self._get_router_id_from_port(r_port_context)
        interface_info = {'port_id': port['id']}
        if port['tenant_id'] != '':
            self.apic_driver.remove_router_interface_precommit(
                context, router_id, interface_info)

    def remove_router_interface_postcommit(self, context, r_port_context):
        pass

    def create_floatingip_precommit(self, context, fip_context):
        self.apic_driver.create_floatingip_precommit(
            context, fip_context.current)

    def create_floatingip_postcommit(self, context, fip_context):
        self.apic_driver.create_floatingip_postcommit(
            context, fip_context.current)

    def update_floatingip_precommit(self, context, fip_context):
        floatingip = fip_context.current
        fip_id = floatingip.get('id')
        if not fip_id:
            fip_id = fip_context.original['id']
        self.apic_driver.update_floatingip_precommit(
            context, fip_id, floatingip)

    def update_floatingip_postcommit(self, context, fip_context):
        floatingip = fip_context.current
        context.current = floatingip
        fip_id = floatingip.get('id')
        if not fip_id:
            fip_id = fip_context.original['id']
        self.apic_driver.update_floatingip_postcommit(
            context, fip_id, floatingip)

    def delete_floatingip_precommit(self, context, fip_context):
        self.apic_driver.delete_floatingip_precommit(
            context, fip_context.current)

    def delete_floatingip_postcommit(self, context, fip_context):
        self.apic_driver.delete_floatingip_postcommit(
            context, fip_context.current)

    def _conditionally_add_global_router(self, context, router):
        """Create global router, if needed.

        This override of the parent class is needed in order
        to ensure that the proper subnet is used for the external
        gateway port. In the GBP workflow, there can be multiple
        subnets on the external network. In order to ensure that
        the global router's gateway port is on the same subnet
        as the user router, we pass in the subnet ID for the GW.
        """
        # We could filter on hosting device id but we don't so we get all
        # global routers for this router type. We can then use that count to
        # determine which ha priority a new global router should get.
        filters = {
            routerrole.ROUTER_ROLE_ATTR: [ROUTER_ROLE_GLOBAL],
            routertype.TYPE_ATTR: [router[routertype.TYPE_ATTR]]}
        global_routers = {
            r[HOSTING_DEVICE_ATTR]: r for r in self._l3_plugin.get_routers(
                context, filters=filters, fields=[HOSTING_DEVICE_ATTR])}
        hosting_device_id = router[HOSTING_DEVICE_ATTR]
        if hosting_device_id not in global_routers:
            # must create global router on hosting device
            # all global routers are connected to the external network
            ext_nw = router[l3.EXTERNAL_GW_INFO]['network_id']
            fixed_ips = router['external_gateway_info']['external_fixed_ips']
            ext_ips = [{'subnet_id': fixed_ips[0]['subnet_id']}]
            r_spec = {'router': {
                # global routers are not tied to any tenant
                'tenant_id': '',
                'name': self._global_router_name(hosting_device_id),
                'admin_state_up': True,
                l3.EXTERNAL_GW_INFO: {'network_id': ext_nw,
                                      'external_fixed_ips': ext_ips}}}
            global_router, r_hd_b_db = self._l3_plugin.do_create_router(
                context, r_spec, router[routertype.TYPE_ATTR], False, True,
                hosting_device_id, ROUTER_ROLE_GLOBAL)
            log_global_router = (
                self._conditionally_add_logical_global_router(context,
                                                              router))
            # make the global router a redundancy router for the logical
            # global router (which we treat as a hidden "user visible
            # router" (how's that for a contradiction! :-) )
            with context.session.begin(subtransactions=True):
                ha_priority = (
                    ha_db.DEFAULT_MASTER_PRIORITY -
                    len(global_routers) * ha_db.PRIORITY_INCREASE_STEP)
                r_b_b = ha_db.RouterRedundancyBinding(
                    redundancy_router_id=global_router['id'],
                    priority=ha_priority,
                    user_router_id=log_global_router['id'])
                context.session.add(r_b_b)
            self._l3_plugin.add_type_and_hosting_device_info(context,
                                                             global_router)
            for ni in self._l3_plugin.get_notifiers(context, [global_router]):
                if ni['notifier']:
                    ni['notifier'].routers_updated(context, ni['routers'])

    def _conditionally_add_logical_global_router(self, context, router):
        """Create logical global router, if needed.

        This override of the parent class is needed in order
        to ensure that the proper subnet is used for the external
        gateway port. In the GBP workflow, there can be multiple
        subnets on the external network. In order to ensure that
        the logical global router's gateway port is on the same subnet
        as the user router, we pass in the subnet ID for the GW.
        """
        # Since HA is also enabled on the global routers on each hosting device
        # those global routers need HA settings and VIPs. We represent that
        # using a Neutron router that is never instantiated/hosted. That
        # Neutron router is referred to as the "logical global" router.
        filters = {routerrole.ROUTER_ROLE_ATTR: [ROUTER_ROLE_LOGICAL_GLOBAL],
                   routertype.TYPE_ATTR: [router[routertype.TYPE_ATTR]]}
        logical_global_routers = self._l3_plugin.get_routers(
            context, filters=filters)
        if not logical_global_routers:
            ext_nw = router[l3.EXTERNAL_GW_INFO]['network_id']
            fixed_ips = router['external_gateway_info']['external_fixed_ips']
            ext_ips = [{'subnet_id': fixed_ips[0]['subnet_id']}]
            r_spec = {'router': {
                # global routers are not tied to any tenant
                'tenant_id': '',
                'name': self._global_router_name('', logical=True),
                'admin_state_up': True,
                l3.EXTERNAL_GW_INFO: {'network_id': ext_nw,
                                      'external_fixed_ips': ext_ips},
                # set auto-schedule to false to keep this router un-hosted
                routertypeawarescheduler.AUTO_SCHEDULE_ATTR: False}}
            # notifications should never be sent for this logical router!
            logical_global_router, r_hd_b_db = (
                self._l3_plugin.do_create_router(
                    context, r_spec, router[routertype.TYPE_ATTR], False,
                    True, None, ROUTER_ROLE_LOGICAL_GLOBAL))
            self._provision_ha(context, logical_global_router)
        else:
            logical_global_router = logical_global_routers[0]
            with context.session.begin(subtransactions=True):
                self._update_ha_redundancy_level(context,
                                                 logical_global_router, 1)
        return logical_global_router
