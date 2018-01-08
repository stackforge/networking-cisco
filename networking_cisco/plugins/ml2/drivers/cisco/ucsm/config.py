# Copyright 2015-2016 Cisco Systems, Inc.
# All rights reserved.
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
from oslo_config import types
from oslo_log import log as logging

from networking_cisco._i18n import _

from networking_cisco.config import base

from networking_cisco.plugins.ml2.drivers.cisco.ucsm import constants as const

LOG = logging.getLogger(__name__)

""" Cisco UCS Manager ML2 Mechanism driver specific configuration.

Following are user configurable options for UCS Manager ML2 Mechanism
driver. The ucsm_username, ucsm_password, and ucsm_ip are
required options in single UCS Manager mode. A repetitive block starting
with ml2_cisco_ucsm_ip signals multi-UCSM configuration. When both are
present, the multi-UCSM config will only take effect.
"""

CONF = cfg.CONF


class EthPortType(types.String):

    def __call__(self, value):
        value = super(EthPortType, self).__call__(value)
        return const.ETH_PREFIX + value


class SPTemplateListType(types.ConfigType):

    def __init__(self, type_name="SPTemplateList"):
        super(SPTemplateListType, self).__init__(type_name=type_name)

    def __call__(self, value):
        if isinstance(value, dict):
            return value

        sp_templates = {}
        sp_template_mappings = (value or "").split()

        for mapping in sp_template_mappings:
            data = mapping.split(":")
            if len(data) != 3:
                raise cfg.Error(_('UCS Mech Driver: Invalid Service '
                                  'Profile Template config %s') % mapping)
            host_list = data[2].split(',')
            for host in host_list:
                sp_templates[host] = (None, data[0], data[1])
        return sp_templates


ml2_cisco_ucsm_opts = [
    cfg.StrOpt('ucsm_ip',
               help=_('Cisco UCS Manager IP address. This is a required field '
                      'to communicate with a Cisco UCS Manager.')),
    cfg.StrOpt('ucsm_username',
               help=_('Username for UCS Manager. This is a required field '
                      'to communicate with a Cisco UCS Manager.')),
    cfg.StrOpt('ucsm_password',
               secret=True,  # do not expose value in the logs
               help=_('Password for UCS Manager. This is a required field '
                      'to communicate with a Cisco UCS Manager.')),
    cfg.DictOpt('supported_pci_devs',
                default={"1137": "0071",
                         "8086": "10c9"},
                help=_('List of comma separated vendor_id:product_id of '
                       'SR_IOV capable devices supported by this MD. This MD '
                       'supports both VM-FEX and SR-IOV devices.')),
    cfg.ListOpt('ucsm_host_list',
                help=_('List of comma separated Host:Service Profile tuples '
                       'providing the Service Profile associated with each '
                       'Host to be supported by this MD.')),
    cfg.ListOpt('ucsm_virtio_eth_ports',
                default=[const.ETH_PREFIX + const.ETH0,
                         const.ETH_PREFIX + const.ETH1],
                item_type=EthPortType(),
                help=_('List of comma separated names of ports that could '
                       'be used to configure VLANs for Neutron virtio '
                       'ports. The names should match the names on the '
                       'UCS Manager.')),
    cfg.StrOpt('sriov_qos_policy',
               help=_('Name of QoS Policy pre-defined in UCSM, to be '
                      'applied to all VM-FEX Port Profiles. This is '
                      'an optional parameter.')),
    cfg.BoolOpt('ucsm_https_verify',
               default=True,
               help=_('When set to False, the UCSM driver will not check '
                      'the SSL certificate on the UCSM leaving the connection '
                      'path insecure and vulnerable to man-in-the-middle '
                      'attacks. This is a global configuration which means '
                      'that it applies to all UCSMs in the system.')),
]

ml2_cisco_ucsm_subopts = [
    cfg.StrOpt('ucsm_username',
               help=_('Username for UCS Manager. This is a required field '
                      'to communicate with a Cisco UCS Manager.')),
    cfg.StrOpt('ucsm_password',
               secret=True,  # do not expose value in the logs
               help=_('Password for UCS Manager. This is a required field '
                      'to communicate with a Cisco UCS Manager.')),
    cfg.ListOpt('ucsm_virtio_eth_ports',
                default=[const.ETH_PREFIX + const.ETH0,
                         const.ETH_PREFIX + const.ETH1],
                item_type=EthPortType(),
                help=_('List of comma separated names of ports that could '
                       'be used to configure VLANs for Neutron virtio '
                       'ports. The names should match the names on the '
                       'UCS Manager.')),
    cfg.DictOpt('ucsm_host_list',
                help=_('List of comma separated Host:Service Profile tuples '
                       'providing the Service Profile associated with each '
                       'Host to be supported by this MD.')),
    cfg.StrOpt('sriov_qos_policy',
               help=_('Name of QoS Policy pre-defined in UCSM, to be '
                      'applied to all VM-FEX Port Profiles. This is '
                      'an optional parameter.')),
    cfg.StrOpt('vnic_template_list'),
    cfg.Opt('sp_template_list', type=SPTemplateListType(),
            default={})
]

sriov_opts = [
    base.RemainderOpt('network_vlans')
]

ucsms = base.SubsectionOpt(
    'ml2_cisco_ucsm_ip',
    dest='ucsms',
    help=_("Subgroups that allow you to specify the UCSMs to be "
           "managed by the UCSM ML2 driver."),
    subopts=ml2_cisco_ucsm_subopts)

CONF.register_opts(ml2_cisco_ucsm_opts, "ml2_cisco_ucsm")
CONF.register_opt(ucsms, "ml2_cisco_ucsm")
CONF.register_opts(sriov_opts, "sriov_multivlan_trunk")


def load_single_ucsm_config():
    # If no valid single configuration, skip this
    if not CONF.ml2_cisco_ucsm.ucsm_ip:
        return

    # Clear any previously loaded single ucsm config
    CONF.clear_override("ucsms", group="ml2_cisco_ucsm")

    if CONF.ml2_cisco_ucsm.ucsm_ip in CONF.ml2_cisco_ucsm.ucsms:
        raise Exception(_("UCSM %s defined in main UCSM config group and as a "
                        "UCSM config group."))

    # Create a group to represent the single ucsms config
    CONF.register_opts(ml2_cisco_ucsm_subopts, "single_ucsm_config")

    # Inject config values from main ml2_cisco_ucsm group into the single ucsm
    # group
    for opt in ml2_cisco_ucsm_subopts:
        if opt.dest not in CONF.ml2_cisco_ucsm:
            continue
        CONF.set_override(opt.dest, CONF.ml2_cisco_ucsm[opt.dest],
                          group="single_ucsm_config")

    # Inject the single UCSM into the ucsms dictionary as an override so we can
    # clear it again later
    ucsms = dict(CONF.ml2_cisco_ucsm.ucsms)
    ucsms[CONF.ml2_cisco_ucsm.ucsm_ip] = CONF.single_ucsm_config
    CONF.set_override("ucsms", ucsms, group="ml2_cisco_ucsm")


class UcsmConfig(object):
    """ML2 Cisco UCSM Mechanism Driver Configuration class."""
    def __init__(self):
        load_single_ucsm_config()

    @property
    def ucsm_host_dict(self):
        host_dict = {}
        if CONF.ml2_cisco_ucsm.ucsms:
            for ip, ucsm in CONF.ml2_cisco_ucsm.ucsms.items():
                for host, sp in (ucsm.ucsm_host_list or {}).items():
                    host_dict[host] = ip
        return host_dict

    @property
    def ucsm_sp_dict(self):
        sp_dict = {}
        if CONF.ml2_cisco_ucsm.ucsms:
            for ip, ucsm in CONF.ml2_cisco_ucsm.ucsms.items():
                for host, sp in (ucsm.ucsm_host_list or {}).items():
                    if '/' not in sp:
                        sp_dict[(ip, host)] = (
                            const.SERVICE_PROFILE_PATH_PREFIX + sp.strip())
                    else:
                        sp_dict[(ip, host)] = sp.strip()
        return sp_dict

    def add_sp_template_config_for_host(self, host, ucsm_ip,
                                        sp_template_path,
                                        sp_template):
        ucsms = CONF.ml2_cisco_ucsm.ucsms

        # First get all sp templates from all ucsms
        templates = {}
        for ip, ucsm in ucsms.items():
            if (set(templates.keys()) & set(ucsm.sp_template_list.keys())):
                raise Exception(_("Same host defined twice and is therefore "
                                "abiguous"))
            templates.update(ucsm.sp_template_list)

        # Then inject or replace the host to add. Doing this to the list of all
        # UCSMs ensures we handle the case when a host moves between UCSMs
        templates[host] = (ucsm_ip, sp_template_path, sp_template)

        # Last set an override on the orginal sp template configs to save the
        # new sp template
        ucsm_template_map = {}
        for host, info in templates.items():
            ucsm = ucsm_template_map.setdefault(info[0], {})
            ucsm[host] = info

        for ucsm, sps in ucsm_template_map.items():
            CONF.set_override("sp_template_list", sps, ucsms[ucsm]._group)

    def update_sp_template_config(self, host_id, ucsm_ip,
                                  sp_template_with_path):
        sp_template_info = sp_template_with_path.rsplit('/', 1)
        LOG.debug('SP Template path: %s SP Template: %s',
            sp_template_info[0], sp_template_info[1])
        self.add_sp_template_config_for_host(
            host_id, ucsm_ip, sp_template_info[0], sp_template_info[1])

    def _vnic_template_data_for_ucsm_ip(self, ucsm_ip):
        if ucsm_ip not in CONF.ml2_cisco_ucsm.ucsms:
            return []
        template_list = CONF.ml2_cisco_ucsm.ucsms[ucsm_ip].vnic_template_list
        mappings = []
        vnic_template_mappings = template_list.split()
        for mapping in vnic_template_mappings:
            data = mapping.split(":")
            if len(data) != 3:
                raise cfg.Error(_("UCS Mech Driver: Invalid VNIC Template "
                                  "config: %s") % mapping)
            data[1] = data[1] or const.VNIC_TEMPLATE_PARENT_DN
            mappings.append(data)
        return mappings

    def is_vnic_template_configured(self):
        for ip, ucsm in CONF.ml2_cisco_ucsm.ucsms.items():
            if ucsm.vnic_template_list:
                return True
        return False

    def get_vnic_template_for_physnet(self, ucsm_ip, physnet):
        vnic_template_mappings = self._vnic_template_data_for_ucsm_ip(ucsm_ip)
        for mapping in vnic_template_mappings:
            if mapping[0] == physnet:
                return (mapping[1], mapping[2])
        return (None, None)

    def get_vnic_template_for_ucsm_ip(self, ucsm_ip):
        vnic_template_info_list = []
        vnic_template_mappings = self._vnic_template_data_for_ucsm_ip(ucsm_ip)
        for mapping in vnic_template_mappings:
            vnic_template_info_list.append((mapping[1], mapping[2]))
        return vnic_template_info_list

    def get_sriov_multivlan_trunk_config(self, network):
        vlans = []
        config = cfg.CONF.sriov_multivlan_trunk.network_vlans.get(network)
        if not config:
            return vlans

        vlanlist = config.split(',')
        for vlan in vlanlist:
            if '-' in vlan:
                start_vlan, sep, end_vlan = (vlan.partition('-'))
                vlans.extend(list(range(int(start_vlan.strip()),
                                        int(end_vlan.strip()) + 1, 1)))
            else:
                vlans.append(int(vlan))
        return vlans

    def get_sriov_qos_policy(self, ucsm_ip):
        return (CONF.ml2_cisco_ucsm.ucsms[ucsm_ip].sriov_qos_policy or
                CONF.ml2_cisco_ucsm.sriov_qos_policy)
