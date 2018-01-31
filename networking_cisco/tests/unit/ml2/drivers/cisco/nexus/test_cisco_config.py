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
intfcfg_portchannel=user cmd1;user cmd2
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

# Make sure intfcfg.portchannel still works
test_deprecate_config_file = """
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

# Assign non-integer to ssh_port for error
dict_mapping_config_file = """
[ml2_mech_cisco_nexus:1.1.1.1]
username=admin
password=mySecretPassword
nve_src_intf=2
physnet=physnet1
host_ports_mapping=compute1:[1/1],
                   compute2:[1/2],
                   compute3:[1/3, port-channel30]
"""


class TestCiscoNexusPluginConfigBase(testlib_api.SqlTestCase):

    def setUp(self):
        super(TestCiscoNexusPluginConfigBase, self).setUp()
        cfg.CONF.clear()


class TestCiscoNexusPluginConfig(TestCiscoNexusPluginConfigBase):

    def test_config_using_subsection_option(self):
        nc_base.load_config_file(test_config_file)
        expected = {
            '1.1.1.1': {
                'username': 'admin',
                'password': 'mySecretPassword',
                'ssh_port': 22,
                'nve_src_intf': '2',
                'physnet': 'physnet1',
                'vpc_pool': '5,10',
                'intfcfg_portchannel': 'user cmd1;user cmd2',
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
                'intfcfg_portchannel': None,
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

    def test_deprecated_intfcfg_portchannel(self):
        nc_base.load_config_file(test_deprecate_config_file)
        """Test creation deprecated intfcfg_portchannel works."""
        expected = {
            '1.1.1.1': {
                'username': 'admin',
                'password': 'mySecretPassword',
                'ssh_port': 22,
                'nve_src_intf': '2',
                'physnet': 'physnet1',
                'vpc_pool': '5,10',
                'intfcfg_portchannel': 'user cmd1;user cmd2',
                'https_verify': True,
                'https_local_certificate': (
                    '/path/to/your/local-certificate-file.crt'),
                'host_port_mapping': {
                    'compute1': '1/1',
                    'compute2': '1/2',
                    'compute5': '1/3,1/4'
                }
            }
        }

        for switch_ip, options in expected.items():
            for opt_name, option in options.items():
                self.assertEqual(
                    option, cfg.CONF.ml2_cisco.nexus_switches.get(
                        switch_ip).get(opt_name))

    def test_create_device_error(self):
        nc_base.load_config_file(test_error_config_file)
        """Test error during create of the Nexus device dictionary."""

        e = self.assertRaises(cfg.ConfigFileValueError,
            cfg.CONF.ml2_cisco.nexus_switches.get('1.1.1.1').get,
            "ssh_port")
        x = six.u(str(e))
        self.assertIn("Value for option ssh_port is not valid: "
                      "invalid literal for int() with base 10: "
                      "'abc'", x)

    def test_dict_host_port_mapping(self):
        nc_base.load_config_file(dict_mapping_config_file)
        """Test port_host_mapping dictionary works."""
        expected = {
            '1.1.1.1': {
                'username': 'admin',
                'password': 'mySecretPassword',
                'host_ports_mapping': {
                    'compute1': ['1/1'],
                    'compute2': ['1/2'],
                    'compute3': ['1/3', 'port-channel30']
                }
            }
        }

        for switch_ip, options in expected.items():
            for opt_name, option in options.items():
                self.assertEqual(
                    option, cfg.CONF.ml2_cisco.nexus_switches.get(
                        switch_ip).get(opt_name))
