# Copyright (c) 2014-2016 Cisco Systems, Inc.
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
import six

from networking_cisco.plugins.ml2.drivers.cisco.nexus import (
    config as cisco_config)
from networking_cisco.plugins.ml2.drivers.cisco.nexus import (
    nexus_helpers as nexus_help)
from networking_cisco.plugins.ml2.drivers.cisco.nexus import nexus_db_v2

from neutron.tests.unit import testlib_api

from networking_cisco.tests import base as nc_base

test_config_file = """
[ml2_mech_cisco_nexus:1.1.1.1]
username=admin
password=mySecretPassword
ssh_port=22
nve_src_intf=2
physnet=physnet1
vpc_pool=5,10
intfcfg.portchannel=user cmd1;user cmd2
https_verify=True
https_local_certificate=/path/to/your/local-certificate-file.crt
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

# Assign non-integer to ssh_port for error
test_error_config_file = """
[ml2_mech_cisco_nexus:1.1.1.1]
username=admin
password=mySecretPassword
ssh_port='abc'
nve_src_intf=2
physnet=physnet1
compute1=1/1
"""


class TestCiscoNexusPluginConfig(testlib_api.SqlTestCase):

    def setUp(self):
        super(TestCiscoNexusPluginConfig, self).setUp()
        nc_base.load_config_file(test_config_file)

    def test_config_using_subsection_option(self):
        expected = {
            '1.1.1.1': {
                'username': 'admin',
                'password': 'mySecretPassword',
                'ssh_port': 22,
                'nve_src_intf': '2',
                'physnet': 'physnet1',
                'vpc_pool': '5,10',
                'intfcfg.portchannel': 'user cmd1;user cmd2',
                'https_verify': True,
                'https_local_certificate': (
                    '/path/to/your/local-certificate-file.crt'),
                'host_port_mapping': {
                    'compute1': '1/1',
                    'compute2': '1/2',
                    'compute5': '1/3,1/4'
                }
            }, '2.2.2.2': {
                'username': 'admin',
                'password': 'mySecretPassword',
                'ssh_port': 22,
                'physnet': None,
                'nve_src_intf': None,
                'vpc_pool': None,
                'intfcfg.portchannel': None,
                'https_verify': False,
                'https_local_certificate': None,
                'host_port_mapping': {
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


class TestCiscoNexusPluginConfigError(testlib_api.SqlTestCase):

    def setUp(self):
        super(TestCiscoNexusPluginConfigError, self).setUp()
        nc_base.load_config_file(test_error_config_file)

    def test_create_device_error(self):
        """Test error during create of the Nexus device dictionary."""

        e = self.assertRaises(cfg.ConfigFileValueError,
            cfg.CONF.ml2_cisco.nexus_switches.get('1.1.1.1').get,
            "ssh_port")
        x = six.u(str(e))
        self.assertIn("Value for option ssh_port is not valid: "
                      "invalid literal for int() with base 10: "
                      "'abc'", x)
