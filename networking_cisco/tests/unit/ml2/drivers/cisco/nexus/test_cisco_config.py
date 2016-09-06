# Copyright (c) 2014 Cisco Systems, Inc.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_config import cfg

from networking_cisco.plugins.ml2.drivers.cisco.nexus import (
    config as cisco_config)

from neutron.tests import base

from networking_cisco.tests import base as nc_base

test_config_file = """
[ml2_mech_cisco_nexus:1.1.1.1]
username=admin
password=mySecretPassword
ssh_port=22
compute1=1/1
compute2=1/2
compute5=1/3,1/4

[ml2_mech_cisco_nexus:2.2.2.2]
username=admin
password=mySecretPassword
ssh_port=22
compute3=1/1
compute4=1/2
compute5=portchannel:20,portchannel:30
"""


class TestCiscoNexusPluginConfig(base.BaseTestCase):

    def setUp(self):
        super(TestCiscoNexusPluginConfig, self).setUp()
        nc_base.load_config_file(test_config_file)

    def test_create_device_dictionary(self):
        """Test creation of the device dictionary based on nexus config."""
        expected_dev_dict = {
            ('1.1.1.1', 'username'): 'admin',
            ('1.1.1.1', 'password'): 'mySecretPassword',
            ('1.1.1.1', 'ssh_port'): 22,
            ('1.1.1.1', 'physnet'): None,
            ('1.1.1.1', 'compute1'): '1/1',
            ('1.1.1.1', 'compute2'): '1/2',
            ('1.1.1.1', 'compute5'): '1/3,1/4',
            ('2.2.2.2', 'username'): 'admin',
            ('2.2.2.2', 'password'): 'mySecretPassword',
            ('2.2.2.2', 'ssh_port'): 22,
            ('2.2.2.2', 'physnet'): None,
            ('2.2.2.2', 'compute3'): '1/1',
            ('2.2.2.2', 'compute4'): '1/2',
            ('2.2.2.2', 'compute5'): 'portchannel:20,portchannel:30',
        }

        cisco_config.ML2MechCiscoConfig()
        self.assertEqual(expected_dev_dict,
                         cisco_config.ML2MechCiscoConfig.nexus_dict)

    def test_config_using_subsection_option(self):
        expected = {
            '1.1.1.1': {
                'username': 'admin',
                'password': 'mySecretPassword',
                'ssh_port': 22,
                'physnet': None,
                'compute_hosts': {
                    'compute1': '1/1',
                    'compute2': '1/2',
                    'compute5': '1/3,1/4'
                }
            }, '2.2.2.2': {
                'username': 'admin',
                'password': 'mySecretPassword',
                'ssh_port': 22,
                'physnet': None,
                'compute_hosts': {
                    'compute3': '1/1',
                    'compute4': '1/2',
                    'compute5': 'portchannel:20,portchannel:30'
                }
            }
        }

        for switch_ip, options in expected.items():
            for opt_name, option in options.items():
                self.assertEqual(
                    option, cfg.CONF.ml2_cisco.nexus_switches.get(
                        switch_ip).get(opt_name))
