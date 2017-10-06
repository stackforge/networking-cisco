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

from oslo_config import cfg
import re

from networking_cisco._i18n import _
from networking_cisco.config import base
from networking_cisco.plugins.ml2.drivers.cisco.nexus import (
    constants as const)
from networking_cisco.plugins.ml2.drivers.cisco.nexus import (
    nexus_db_v2 as nxos_db)
from networking_cisco.plugins.ml2.drivers.cisco.nexus import (
    nexus_helpers as nexus_help)

nexus_sub_opts = [
    cfg.StrOpt('username',
        help=_('The username for Nexus Switch administrator. This '
               'is required for baremetal and non-baremetal deployments.')),
    cfg.StrOpt('password',
        help=_('The password for Nexus Switch administrator. This '
               'is required for baremetal and non-baremetal deployments.')),
    cfg.StrOpt('physnet',
        help=_('This is only valid if VXLAN overlay is configured.  The '
               'physical network name defined in the network_vlan_ranges '
               'variable (defined under the ml2_type_vlan section) that this '
               'switch is controlling.  The configured "physnet" is the '
               'physical network domain that is connected to this switch. '
               'The vlan ranges defined in network_vlan_ranges for a physical '
               'network are allocated dynamically and are unique per physical '
               'network. These dynamic vlans may be reused across physical '
               'networks.  This is configured for non-baremetal only.')),
    cfg.StrOpt('nve_src_intf',
        help=_('Only valid if VXLAN overlay is configured and '
               'vxlan_global_config is set to True. The NVE source interface '
               'is a loopback interface that is configured on the switch with '
               'valid /32 IP address. This /32 IP address must be known by '
               'the transient devices in the transport network and the remote '
               'VTEPs.  This is accomplished by advertising it through a '
               'dynamic routing protocol in the transport network. If '
               'nve_src_intf is not defined then a default setting of 0 which '
               'is used which creates "loopback0".  This is configured for '
               'non-baremetal only.')),
    cfg.StrOpt('vpc_pool',
        help=_('This is port-channel/VPC allocation pool of ids for baremetal '
               'configurations only.  When there is a list of ethernet '
               'interfaces provided by Ironic to neutron in a port binding '
               'event, these are assumed to be a port-channel type '
               'configuration.  Ironic only knows about ethernet interfaces '
               'so it is up to the Nexus Driver to either learn the '
               'port channel if the user preconfigured the channel-group on '
               'the ethernet interfaces otherwise the driver will create a '
               'new port-channel and apply the channel-group to the ethernet '
               'interfaces.  This pool is the reserved port-channel IDs '
               'available for allocation by the Nexus driver for each switch. '
               'The full format for this variable is '
               'vpc_pool=<start_vpc_no-end_vpc_no> | '
               '<vpc_no> {,<start_vpc_no-end_vpc_no> | <vpc_no>}. The "-" in '
               '<start_vpc_no,end_vpc_no> allows you to configure a range '
               'from start to end and <vpc_no> allows just individual '
               'numbers.  There can be any number of ranges and numbers '
               'separated by commas. There is no default value.  If not '
               'configured, the port-channel will only handle learned cases '
               'and attempts to create port-channels will fail since there is '
               'no id pool available from which to allocate an id. Once '
               'defined, it can be redefined by changing the variable and '
               'restarting neutron. Existing VPC ids in the database are '
               'gathered and compared against the new vpc_pool config.  New '
               'configured vpcids not found in the database are added.  '
               'Inactive entries in the database not found in the new '
               'configured vpcids list are removed. An example of this '
               'configuration is `vpc_pool=1001-1025,1028`.')),
    cfg.StrOpt('intfcfg.portchannel',
        help=_('String of Nexus port-channel config cli for use when '
               'baremetal port-channels are created. Any number of '
               'Nexus port-channel commands separated by ";" can be '
               'provided.  When there are multiple interfaces in a baremetal '
               'event, the nexus driver checks to determine whether a port '
               'channel is already applied to the interfaces; otherwise, it '
               'creates a port channel. This optional configuration allows '
               'the administrator to custom configure the port-channel.  '
               'When this option is not configured, the nexus '
               'driver defaults to configuring "spanning-tree port type edge '
               'trunk;no lacp suspend-individual" beneath the port-channel. '
               'An example of this configuration is "intfcfg.portchannel=no '
               'lacp suspend-individual;spanning-tree port type edge '
               'trunk".')),
    cfg.IntOpt('ssh_port', default=22, deprecated_for_removal=True,
        help=_('TCP port for connecting via SSH to manage the switch. This '
               'is port number 22 unless the switch has been configured '
               'otherwise. Since this variable is associated '
               'to the ncclient driver which is being deprecated, this '
               'variable too will be deprecated.')),
    base.RemainderOpt('compute_hosts')]

ml2_cisco_opts = [
    cfg.StrOpt('managed_physical_network',
        help=_('The name of the physical_network managed via the Cisco Nexus '
               'Switch.  This string value must be present in the '
               'network_vlan_ranges variable in neutron start-up config '
               'file.')),
    cfg.BoolOpt('persistent_switch_config', default=False,
        deprecated_for_removal=True,
        help=_('To make Nexus device persistent by running the Nexus '
               'CLI "copy run start" after applying successful '
               'configurations. This will be deprecated along with '
               'nexus_driver since this is associated to the ncclient '
               'driver which is going away.')),
    cfg.BoolOpt('never_cache_ssh_connection', default=True,
        deprecated_for_removal=True,
        help=_('Prevent caching ssh connections to a Nexus switch. Set this '
               'to True when there are multiple neutron controllers and/or '
               'when there may be non-neutron ssh connections to the same '
               'Nexus device. Nexus devices have a limit of 8 such '
               'connections. When a single neutron controller has more than '
               '8 processes, caching is automatically disabled without regard '
               'to this option. This flag defaults to True which indicates '
               'that ssh connections to a Nexus switch are not cached when '
               'the neutron controller has fewer than 8 processes.  This will '
               'be deprecated along with nexus_driver since this is '
               'associated to the ncclient driver which is going away.')),
    cfg.IntOpt('switch_heartbeat_time', default=30,
        help=_('Time interval to check the state of all known Nexus device(s). '
               'This variable defaults to 30 seconds which checks each Nexus '
               'device every 30 seconds.  To disable configuration replay, '
               'set this variable to 0 seconds.')),
    cfg.BoolOpt('provider_vlan_auto_create', default=True,
        help=_('A flag indicating whether OpenStack networking should manage '
               'the creation and removal of VLANs for provider networks on '
               'the Nexus switches. If the flag is set to False, then '
               'OpenStack will not create or remove VLANs for provider '
               'networks and the administrator needs to manage these '
               'interfaces manually or by external orchestration.')),
    cfg.BoolOpt('provider_vlan_auto_trunk', default=True,
        help=_('A flag indicating whether OpenStack networking should manage '
               'the adding and removing of provider VLANs from trunk ports on '
               'the Nexus switches. If the flag is set to False then '
               'OpenStack will not add or remove provider VLANs from trunk '
               'ports and the administrator needs to manage these operations '
               'manually or by external orchestration.')),
    cfg.BoolOpt('vxlan_global_config', default=False,
        help=_('A flag indicating whether OpenStack networking should manage '
               'the creating and removing of the Nexus switch VXLAN global '
               'settings of "feature nv overlay", "feature '
               'vn-segment-vlan-based", "interface nve 1" and the NVE '
               'subcommand "source-interface loopback #". When set to the '
               'default of False, OpenStack will not add or remove these '
               'VXLAN settings, and the administrator needs to manage these '
               'operations manually or by external # orchestration.')),
    cfg.BoolOpt('host_key_checks', default=False, deprecated_for_removal=True,
        help=_('A flag to enable strict hostkey checks when connecting to '
               'Nexus switches. This flag defaults to False (No hostkey '
               'checks). This will be deprecated along with nexus_driver '
               'since this is associated to the ncclient driver which is '
               'going away.')),
    cfg.StrOpt('nexus_driver', default='restapi', deprecated_for_removal=True,
        help=_('Nexus MD has two driver methods to configure Nexus devices. '
               'The default choice has changed to "restapi" which replaces '
               'the original "ncclient" driver.  The RESTAPI driver has '
               'better performance with less Nexus session limits. '
               'Additionally, new feature development is applied only to the '
               'restapi driver. Plans are to remove ncclient driver in '
               'Cisco 7.0.0 release or networking-cisco repo.  To use the '
               'restapi driver, the Nexus 9K image version must be 7.0(3)I5(2)'
               ' or greater.  For short term, the original driver can be used '
               'by setting the nexus_driver to "ncclient".'
)),
]

nexus_switches = base.SubsectionOpt(
    'ml2_mech_cisco_nexus',
    dest='nexus_switches',
    help=_("Subgroups that allow you to specify the nexus switches to be "
           "managed by the nexus ML2 driver."),
    subopts=nexus_sub_opts)

cfg.CONF.register_opts(ml2_cisco_opts, "ml2_cisco")
cfg.CONF.register_opt(nexus_switches, "ml2_cisco")

#
# Format for ml2_conf_cisco.ini 'ml2_mech_cisco_nexus' is:
# {('<device ipaddr>', '<keyword>'): '<value>', ...}
#
# Example:
# {('1.1.1.1', 'username'): 'admin',
#  ('1.1.1.1', 'password'): 'mySecretPassword',
#  ('1.1.1.1', 'compute1'): '1/1', ...}
#


class ML2MechCiscoConfig(object):
    """ML2 Mechanism Driver Cisco Configuration class."""
    nexus_dict = {}

    def __init__(self):
        def insert_space(matchobj):
            # Command output format must be cmd1 ;cmd2 ; cmdn
            # and not cmd1;cmd2;cmdn or config will fail in Nexus.
            # This does formatting before storing in dictionary.
            test = matchobj.group(0)
            return test[0] + ' ;'
        nxos_db.remove_all_static_host_mappings()
        for switch_ip, switch in cfg.CONF.ml2_cisco.nexus_switches.items():
            for opt_name, value in switch.items():
                if opt_name == 'compute_hosts':
                    for host, ports in value.items():
                        for if_id in ports.split(','):
                            # first make format consistent
                            if_type, port = (
                                nexus_help.split_interface_name(if_id))
                            interface = nexus_help.format_interface_name(
                                if_type, port)
                            nxos_db.add_host_mapping(
                                host, switch_ip, interface, 0, True)
                elif value:
                    if opt_name == const.IF_PC:
                        self.nexus_dict[switch_ip, opt_name] = (
                            re.sub("\w;", insert_space, value))
                    else:
                        self.nexus_dict[(switch_ip, opt_name)] = value
