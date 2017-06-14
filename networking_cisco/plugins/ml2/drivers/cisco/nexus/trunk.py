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

from oslo_log import log

#from networking_cisco import backwards_compatibility as bc
#import networking_cisco.backwards_compatibility as bc

from neutron.api.v2 import attributes
from neutron.extensions import dns
from neutron.objects import trunk as trunk_objects
from neutron.services.trunk import constants as trunk_consts


LOG = log.getLogger(__name__)
NO_VNI = 0
NO_PROVIDER_NETWORK = False


class NexusMDTrunkHandler(object):
    """Cisco Nexus Mechanism Driver Trunk Handler.

    This class contains methods called by the cisco_nexus MD for
    processing trunk subports.
    """
    def __init__(self):
        from networking_cisco import backwards_compatibility as bc
        self.bc = bc

    def _is_baremetal(self, port):
        return (port[self.bc.portbindings.VNIC_TYPE] ==
                self.bc.portbindings.VNIC_BAREMETAL)

    def is_trunk_parentport(self, port):
        return 'trunk_details' in port

    def is_trunk_subport(self, port):
        # Check for subports by (1) on creates, subport will be present in
        # trunk database (2) on deletes, port device_owner will indicate
        # subport type.
        if (port['device_owner'] == trunk_consts.TRUNK_SUBPORT_OWNER or
            trunk_objects.SubPort.get_object(self.bc.get_context(),
                                             port_id=port['id'])):
            return True
        else:
            return False

    def get_trunk_subport(self, port):
        return (trunk_objects.SubPort.get_object(
            self.bc.get_context(), port_id=port['id']))

    def is_trunk_subport_baremetal(self, port):
        context = self.bc.get_context()
        el_context = context.elevated()

        subport_obj = trunk_objects.SubPort.get_object(
            el_context, port_id=port['id'])
        if subport_obj:
            trunk_obj = trunk_objects.Trunk.get_object(
                el_context, id=subport_obj.trunk_id)
            trunk_port = self.bc.get_plugin().get_port(
                el_context, trunk_obj.port_id)
            return self._is_baremetal(trunk_port)
        else:
            return False

    def get_link_info(self, subport):
        # To avoid updating baremetal related methods (API parameters)
        # in mech_cisco_nexus, access link information from both
        # parent and trunk subports.

        # When accessed by delete events the link information
        # will be available in the trunks's subport.
        all_link_info = subport[self.bc.portbindings.PROFILE].get(
            'local_link_information')

        # if not found in subport then
        #   create event. Access link information from
        #   trunk's parent port.
        if not all_link_info:
            context = self.bc.get_context()
            subport_obj = trunk_objects.SubPort.get_object(
                context, port_id=subport['id'])
            if subport_obj:
                el_context = context.elevated()
                trunk_obj = trunk_objects.Trunk.get_object(
                    el_context, id=subport_obj.trunk_id)
                parent_port = self.bc.get_plugin().get_port(
                    el_context, trunk_obj.port_id)
                all_link_info = (parent_port[self.bc.portbindings.PROFILE].get(
                    'local_link_information'))
        return all_link_info

    def process_subports(self, port, func):
        host_id = (port.get(dns.DNSNAME) if self._is_baremetal(port) else
                   port.get(self.bc.portbindings.HOST_ID))
        if host_id:
            trunk_details = port.get('trunk_details')
            subports = trunk_details['sub_ports']
            context = self.bc.get_context()
            el_context = context.elevated()
            for subport in subports:
                sub_port = self.bc.get_plugin().get_port(
                        el_context, subport['port_id'])
                func(sub_port, subport['segmentation_id'], subport['port_id'],
                     host_id, NO_VNI, NO_PROVIDER_NETWORK)

    def update_subports(self, port):
        """Set port attributes for trunk subports.

        For baremetal deployments, set the neturon port attributes
        during the bind_port event.
        """
        trunk_details = port.get('trunk_details')
        subports = trunk_details['sub_ports']
        host_id = (port.get(dns.DNSNAME) if self._is_baremetal(port) else
                   port.get(self.bc.portbindings.HOST_ID))
        context = self.bc.get_context()
        el_context = context.elevated()

        for subport in subports:
            self.bc.get_plugin().update_port(el_context, subport['port_id'],
                {attributes.PORT:
                 {self.bc.portbindings.HOST_ID: host_id,
                  self.bc.portbindings.VNIC_TYPE:
                      self.bc.portbindings.VNIC_BAREMETAL,
                  self.bc.portbindings.PROFILE:
                      port.get(self.bc.portbindings.PROFILE),
                  'device_owner': trunk_consts.TRUNK_SUBPORT_OWNER,
                  'status': self.bc.constants.PORT_STATUS_ACTIVE}})

        # Set trunk to ACTIVE status.
        trunk_obj = trunk_objects.Trunk.get_object(
            el_context, id=trunk_details['trunk_id'])
        trunk_obj.update(status=trunk_consts.ACTIVE_STATUS)
