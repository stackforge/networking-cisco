# Copyright 2015 Cisco Systems, Inc.
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
from oslo_log import log as logging

from networking_cisco.plugins.ml2.drivers.cisco.ucsm import constants as const

LOG = logging.getLogger(__name__)

""" Cisco UCS Manager ML2 Mechanism driver specific configuration.

Following are user configurable options for UCS Manager ML2 Mechanism
driver. The ucsm_username, ucsm_password, and ucsm_ip are
required options. Additional configuration knobs are provided to pre-
create UCS Manager port profiles.
"""

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
    cfg.ListOpt('supported_pci_devs',
                default=[const.PCI_INFO_CISCO_VIC_1240,
                         const.PCI_INFO_INTEL_82599],
                help=_('List of comma separated vendor_id:product_id of '
                       'SR_IOV capable devices supported by this MD. This MD '
                       'supports both VM-FEX and SR-IOV devices.')),
    cfg.ListOpt('ucsm_host_list',
                help=_('List of comma separated Host:Service Profile tuples '
                       'providing the Service Profile associated with each '
                       'Host to be supported by this MD.')),
    cfg.ListOpt('ucsm_host_mapping',
                help=_('List of comma separated Host:Service Profile tuples '
                       'providing the Service Profile associated with each '
                       'Host to be supported by this MD.')),
]

cfg.CONF.register_opts(ml2_cisco_ucsm_opts, "ml2_cisco_ucsm")


class UcsmConfig(object):
    """ML2 Cisco UCSM Mechanism Driver Configuration class."""
    ucsm_dict = {}
    host_dict = {}

    def __init__(self):
        self._create_ucsm_dict()
        self._create_ucsm_host_dict()

    def _create_ucsm_dict(self):
        """Create the ML2 device cisco dictionary.

        Read data from the ml2_conf_cisco.ini device supported sections.
        """
        multi_parser = cfg.MultiConfigParser()
        read_ok = multi_parser.read(cfg.CONF.config_file)

        if len(read_ok) != len(cfg.CONF.config_file):
            raise cfg.Error(_("Some config files were not parsed properly"))

        for parsed_file in multi_parser.parsed:
            for parsed_item in parsed_file.keys():
                dev_id, sep, dev_ip = parsed_item.partition(':')
                if dev_id.lower() == 'ucsm_ip':
                    for dev_key, value in parsed_file[parsed_item].items():
                        self.ucsm_dict[dev_ip, dev_key] = value[0]

    def _create_ucsm_host_dict(self):
        host_config_list = cfg.CONF.ml2_cisco_ucsm.ucsm_host_mapping
        for host in host_config_list:
            host_sp = host.split(':')
            if len(host_sp) != 2:
                raise cfg.Error(_('UCS Mech Driver: Invalid Host Service '
                                  'Profile config: %s') % host)
            key = host_sp[0]
            self.host_dict[key] = host_sp[1]
            LOG.debug('Host:Service Profile: %s : %s', key, host_sp[1])

    def get_service_profile_for_host(self, hostname):
        return self.host_dict[hostname]

    def get_ucsm_for_host(self, hostname):
        for (dev_ip, dev_key) in self.ucsm_dict:
            if dev_key in "ucsm_host_list":
                host_list = self.ucsm_dict[dev_ip, dev_key]
                if hostname in host_list:
                    LOG.debug("Found UCSM IP: %s", dev_ip)
                    username = self.ucsm_dict[dev_ip, 'ucsm_username']
                    password = self.ucsm_dict[dev_ip, 'ucsm_password']
                    return dev_ip, username, password

    def get_ucsm_ip_for_host(self, hostname):
        ucsm_ip, username, password = self.get_ucsm_for_host(hostname)
        return ucsm_ip

    def parse_pci_vendor_config(self):
        vendor_list = []
        vendor_config_list = cfg.CONF.ml2_cisco_ucsm.supported_pci_devs
        for vendor in vendor_config_list:
            vendor_product = vendor.split(':')
            if len(vendor_product) != 2:
                raise cfg.Error(_('UCS Mech Driver: Invalid PCI device '
                                  'config: %s') % vendor)
            vendor_list.append(vendor)
        return vendor_list
