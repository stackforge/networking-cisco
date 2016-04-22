# Copyright 2016 Cisco Systems, Inc.  All rights reserved.
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

from neutron.tests import base

from networking_cisco.plugins.cisco.cpnr import dhcpopts


class TestDhcpopts(base.BaseTestCase):
    def test_format_for_options(self):
        expected = '20:a9:fe:a9:fe:0a:0a:00:02'
        value = dhcpopts.format_for_options('classless-static-routes',
                        '32.169.254.169.254 10.10.0.2')
        self.assertEqual(expected, value)

        expected = '01'
        flag = True
        value = dhcpopts.format_for_options('ip-forwarding', flag)
        self.assertEqual(expected, value)

        expected = '00:00:01:2c'
        value = dhcpopts.format_for_options('dhcp-renewal-time', 300)
        self.assertEqual(expected, value)

        expected = '65:78:61:6d:70:6c:65:2e:63:6f:6d:2e'
        value = dhcpopts.format_for_options('domain-name', 'example.com.')
        self.assertEqual(expected, value)
