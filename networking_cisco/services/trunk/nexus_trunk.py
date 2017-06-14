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

from oslo_config import cfg
from oslo_log import log

from neutron.api.v2 import attributes
from neutron.callbacks import events
from neutron.callbacks import registry
from neutron.extensions import dns
from neutron.services.trunk import constants as trunk_consts
from neutron.services.trunk.drivers import base as trunk_base

from networking_cisco.plugins.ml2.drivers.cisco.nexus import (
    constants as const)

LOG = log.getLogger(__name__)
NO_VNI = 0
NO_PROVIDER_NETWORK = False


class NexusTrunkHandler(object):
    """Cisco Nexus Trunk Handler.

    This class contains methods called by the trunk infrastruture
    to be processed by the cisco_nexus MD.
    """

    def __init__(self):
        # To prevent recursive importing.
        from networking_cisco import backwards_compatibility
        from networking_cisco.plugins.ml2.drivers.cisco.nexus import (
            mech_cisco_nexus as md_cisco_nexus)

        self.bc = backwards_compatibility
        self.md = md_cisco_nexus.CiscoNexusMechanismDriver()
        self.plugin = self.bc.get_plugin()

    def _is_baremetal(self, port):
        return (port[self.bc.portbindings.VNIC_TYPE] ==
                self.bc.portbindings.VNIC_BAREMETAL)

    def trunk_update_postcommit(self, resource, event, trunk_plugin, payload):
        current_trunk_data = payload.current_trunk.to_dict()
        trunkport = self.plugin.get_port(
            payload.context, current_trunk_data['port_id'])

        if self._is_baremetal(trunkport):
            for subport in current_trunk_data['sub_ports']:
                self.plugin.update_port(payload.context, subport['port_id'],
                    {attributes.PORT:
                     {'status': current_trunk_data['status']}})

    def subport_precommit(self, resource, event, trunk_plugin, payload):
        trunkport = self.plugin.get_port(
            payload.context, payload.current_trunk.port_id)
        host_id = (trunkport.get(dns.DNSNAME) if self._is_baremetal(trunkport)
                   else trunkport.get(self.bc.portbindings.HOST_ID))
        if (trunkport['status'] != self.bc.constants.PORT_STATUS_ACTIVE or
            not host_id):
            return

        subport = payload.subports[0]
        subport_dict = self.plugin.get_port(payload.context, subport.port_id)

        # For baremetal, create in subport_postcommit. The subport must
        # exist in the trunk database for calls from MD code checks to
        # work. Opposite is true for deletes.
        if event == events.PRECOMMIT_DELETE:
            self.md._delete_nxos_db(
                subport_dict, subport.segmentation_id, subport.port_id,
                host_id, NO_VNI, NO_PROVIDER_NETWORK)
            self.md._delete_switch_entry(
                subport_dict, subport.segmentation_id, subport.port_id,
                host_id, NO_VNI, NO_PROVIDER_NETWORK)

    def subport_postcommit(self, resource, event, trunk_plugin, payload):
        trunkport = self.plugin.get_port(
            payload.context, payload.current_trunk.port_id)
        host_id = (trunkport.get(dns.DNSNAME) if self._is_baremetal(trunkport)
                   else trunkport.get(self.bc.portbindings.HOST_ID))
        if (trunkport['status'] != self.bc.constants.PORT_STATUS_ACTIVE or
            not host_id):
            return

        subport = payload.subports[0]
        trunk_subport_dict = subport.to_dict()
        subport_dict = self.plugin.get_port(
            payload.context, trunk_subport_dict['port_id'])

        # For baremetal deployments, set the neutron port attributes
        # for the subport to match the parent port.
        if self._is_baremetal(trunkport):
            if event == events.AFTER_CREATE:
                self.plugin.update_port(
                    payload.context, trunk_subport_dict['port_id'],
                    {attributes.PORT:
                     {self.bc.portbindings.HOST_ID: host_id,
                      self.bc.portbindings.VNIC_TYPE:
                          self.bc.portbindings.VNIC_BAREMETAL,
                      self.bc.portbindings.PROFILE:
                          trunkport[self.bc.portbindings.PROFILE],
                      'device_owner': trunk_consts.TRUNK_SUBPORT_OWNER,
                      'status': self.bc.constants.PORT_STATUS_ACTIVE}})
            elif event == events.AFTER_DELETE:
                self.plugin.update_port(
                    payload.context, trunk_subport_dict['port_id'],
                    {attributes.PORT:
                     {'status': self.bc.constants.PORT_STATUS_DOWN}})

        # After trunk subport database has completed, configure nexus
        # switch.
        if event == events.AFTER_CREATE:
            self.md._configure_nxos_db(
                subport_dict, trunk_subport_dict['segmentation_id'],
                trunk_subport_dict['port_id'], host_id, NO_VNI,
                NO_PROVIDER_NETWORK)
            self.md._configure_port_entries(
                subport_dict, trunk_subport_dict['segmentation_id'],
                trunk_subport_dict['port_id'], host_id, NO_VNI,
                NO_PROVIDER_NETWORK)


class NexusTrunkDriver(trunk_base.DriverBase):
    """Cisco Nexus Trunk Driver.

    This class contains methods required to work with the trunk infrastruture.
    """

    @property
    def is_loaded(self):
        try:
            return (const.CISCO_NEXUS_ML2_MECH_DRIVER_V2 in
                    cfg.CONF.ml2.mechanism_drivers)
        except cfg.NoSuchOptError:
            return False

    def register(self, resource, event, trigger, **kwargs):
        super(NexusTrunkDriver, self).register(
            resource, event, trigger, **kwargs)
        self._handler = NexusTrunkHandler()

        registry.subscribe(self._handler.trunk_update_postcommit,
                           trunk_consts.TRUNK, events.AFTER_UPDATE)
        registry.subscribe(self._handler.subport_precommit,
                           trunk_consts.SUBPORTS, events.PRECOMMIT_DELETE)
        for event in (events.AFTER_CREATE, events.AFTER_DELETE):
            registry.subscribe(self._handler.subport_postcommit,
                               trunk_consts.SUBPORTS, event)

    @classmethod
    def create(cls):
        # To prevent recursive importing.
        from networking_cisco import backwards_compatibility as bc

        SUPPORTED_INTERFACES = (
            bc.portbindings.VIF_TYPE_OVS,
            bc.portbindings.VIF_TYPE_VHOST_USER,
        )

        SUPPORTED_SEGMENTATION_TYPES = (
            trunk_consts.VLAN,
        )

        return cls(const.CISCO_NEXUS_ML2_MECH_DRIVER_V2,
                   SUPPORTED_INTERFACES,
                   SUPPORTED_SEGMENTATION_TYPES,
                   None,
                   can_trunk_bound_port=True)
