# Copyright (c) 2013-2016 Cisco Systems, Inc.
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


import sqlalchemy as sa

from networking_cisco import backwards_compatibility as bc


class NexusPortBinding(bc.model_base.BASEV2):
    """Represents a binding of VM's to nexus ports."""

    __tablename__ = "cisco_ml2_nexusport_bindings"

    binding_id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    port_id = sa.Column(sa.String(255))
    vlan_id = sa.Column(sa.Integer, nullable=False)
    vni = sa.Column(sa.Integer)
    switch_ip = sa.Column(sa.String(255))
    instance_id = sa.Column(sa.String(255))
    channel_group = sa.Column(sa.Integer, default=0)
    is_native = sa.Column(sa.Boolean(), nullable=False, default=False,
                          server_default=sa.sql.false())

    def __repr__(self):
        """Just the binding, without the id key."""
        return ("<NexusPortBinding(%s,%s,%s,%s,%s,%s,%s)>" %
                (self.port_id, self.vlan_id, self.vni, self.switch_ip,
                 self.instance_id,
                 self.channel_group,
                 'True' if self.is_native else 'False'))

    def __hash__(self):
        return hash(self.__repr__())

    def __eq__(self, other):
        """Compare only the binding, without the id key."""
        return (
            self.port_id == other.port_id and
            self.vlan_id == other.vlan_id and
            self.vni == other.vni and
            self.switch_ip == other.switch_ip and
            self.instance_id == other.instance_id and
            self.channel_group == other.channel_group and
            self.is_native_vlan == other.is_native_vlan
        )


class NexusNVEBinding(bc.model_base.BASEV2):
    """Represents Network Virtualization Endpoint configuration."""

    __tablename__ = "cisco_ml2_nexus_nve"

    vni = sa.Column(sa.Integer, primary_key=True, nullable=False)
    device_id = sa.Column(sa.String(255), primary_key=True)
    switch_ip = sa.Column(sa.String(255), primary_key=True)
    mcast_group = sa.Column(sa.String(255))

    def __repr__(self):
        return ("<NexusNVEBinding(%s,%s,%s,%s)>" %
                (self.vni, self.switch_ip, self.device_id, self.mcast_group))


class NexusVxlanAllocation(bc.model_base.BASEV2):

    __tablename__ = 'ml2_nexus_vxlan_allocations'

    vxlan_vni = sa.Column(sa.Integer, nullable=False, primary_key=True,
                          autoincrement=False)
    allocated = sa.Column(sa.Boolean, nullable=False, default=False,
                          server_default=sa.sql.false())


class NexusMcastGroup(bc.model_base.BASEV2, bc.model_base.HasId):

    __tablename__ = 'ml2_nexus_vxlan_mcast_groups'

    mcast_group = sa.Column(sa.String(64), nullable=False)
    associated_vni = sa.Column(sa.Integer,
                               sa.ForeignKey(
                                   'ml2_nexus_vxlan_allocations.vxlan_vni',
                                   ondelete="CASCADE"),
                               nullable=False)


class NexusHostMapping(bc.model_base.BASEV2):

    """Nexus Host to interface Mapping."""

    __tablename__ = 'cisco_ml2_nexus_host_interface_mapping'

    host_id = sa.Column(sa.String(255), nullable=False, primary_key=True,
                        index=True)
    switch_ip = sa.Column(sa.String(255), nullable=False, primary_key=True,
                          index=True)
    if_id = sa.Column(sa.String(255), nullable=False, primary_key=True)
    ch_grp = sa.Column(sa.Integer(), nullable=False)
    is_static = sa.Column(sa.Boolean(), nullable=False)


class NexusVPCAlloc(bc.model_base.BASEV2):
    """Nexus Port Channel Allocation."""

    __tablename__ = 'cisco_ml2_nexus_vpc_alloc'

    switch_ip = sa.Column(sa.String(64), nullable=False,
                          primary_key=True)
    vpc_id = sa.Column(sa.Integer, nullable=False, primary_key=True,
                       autoincrement=False)

    # learned indicates this ch_grp was predefined on Nexus Switch
    # as opposed to ML2 Nexus driver creating the port channel #
    learned = sa.Column(sa.Boolean, nullable=False)

    # active indicates this ch_grp is in use
    active = sa.Column(sa.Boolean, nullable=False)


class NexusProviderNetwork(bc.model_base.BASEV2):

    __tablename__ = 'cisco_ml2_nexus_provider_networks'

    network_id = sa.Column(sa.String(36), nullable=False, primary_key=True)
    vlan_id = sa.Column(sa.Integer, nullable=False, index=True)
