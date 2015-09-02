# Copyright 2015 Cisco Systems, Inc.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock
from oslo_config import cfg

from neutron.common import config as neutron_config
from neutron.plugins.ml2 import config as ml2_config
from neutron.tests import base

from networking_cisco.plugins.ml2.drivers.cisco.ucsm import config

UCSM_IP_ADDRESS_1 = '1.1.1.1'
UCSM_USERNAME_1 = 'username1'
UCSM_PASSWORD_1 = 'password1'
HOST_LIST_1 = 'Hostname1', 'Hostname2'

UCSM_USERNAME_2 = 'username2'
UCSM_PASSWORD_2 = 'password2'
HOST_LIST_2 = 'Hostname3', 'Hostname4'

UCSM_PHY_NETS = 'test_physnet'
UCSM_HOST_MAPPING = ['Hostname1:Serviceprofile1', 'Hostname2:Serviceprofile2',
    'Hostname3:Serviceprofile3', 'Hostname4:Serviceprofile4']


class ConfigMixin(object):

    """Mock config for UCSM driver."""

    mocked_parser = None

    def set_up_mocks(self):
        # Mock the configuration file

        args = ['--config-file', base.etcdir('neutron.conf')]
        neutron_config.init(args=args)

        # Configure the ML2 mechanism drivers and network types
        ml2_opts = {
            'mechanism_drivers': ['cisco_ucsm'],
            'tenant_network_types': ['vlan'],
        }
        for opt, val in ml2_opts.items():
            ml2_config.cfg.CONF.set_override(opt, val, 'ml2')

        # Configure the Cisco UCS Manager mechanism driver
        test_config = {
            'ucsm_host_mapping': UCSM_HOST_MAPPING,
        }

        for opt, val in test_config.items():
            config.cfg.CONF.set_override(opt, val, 'ml2_cisco_ucsm')

        ucsm_test_config = {
            'ucsm_ip:1.1.1.1': {
                'ucsm_username': UCSM_USERNAME_1,
                'ucsm_password': UCSM_PASSWORD_1,
                'ucsm_host_list': HOST_LIST_1,
            },
            'ucsm_ip:2.2.2.2': {
                'ucsm_username': UCSM_USERNAME_2,
                'ucsm_password': UCSM_PASSWORD_2,
                'ucsm_host_list': HOST_LIST_2,
            },
        }
        self.mocked_parser = mock.patch.object(
            cfg, 'MultiConfigParser').start()
        self.mocked_parser.return_value.read.return_value = [ucsm_test_config]
        self.mocked_parser.return_value.parsed = [ucsm_test_config]
