# Copyright 2017 Cisco Systems, Inc.  All rights reserved.
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

import mock

from oslo_config import cfg

from networking_cisco.plugins.cisco.cfg_agent.device_drivers.asr1k import (
    aci_asr1k_cfg_syncer)
from networking_cisco.plugins.cisco.common.htparser import LineItem
from networking_cisco.tests.unit.cisco.cfg_agent import (
    test_asr1k_cfg_syncer as test_sync)

INVALID_CFG_LIST_1 = [('ip nat inside source static 10.2.0.5 172.16.0.126 '
                       'vrf nrouter-3ea5f9 redundancy '
                       'neutron-hsrp-1064-3000'),
                      ('ip nat inside source list neutron_acl_2564_47f1a63e '
                       'pool nrouter-3ea5f9_nat_pool vrf nrouter-3ea5f9 '
                       'overload'),
                      ('ip nat pool nrouter-3ea5f9_nat_pool 172.16.0.124 '
                       '172.16.0.124 netmask 255.255.0.0'),
                      ('ip route vrf nrouter-3ea5f9 0.0.0.0 0.0.0.0 '
                       'Port-channel10.3000 172.16.0.1'),
                      'ip access-list standard neutron_acl_2564_47f1a63e',
                      'interface Port-channel10.2564',
                      'interface Port-channel10.3000',
                      'nrouter-3ea5f9']

INVALID_CFG_LIST_2 = [('ip nat inside source static 10.2.0.5 172.16.0.126 '
                       'vrf nrouter-3ea5f9-0000002 redundancy '
                       'neutron-hsrp-1064-3000'),
                      ('ip nat inside source list '
                       'neutron_acl_0000002_2564_47f1a63e pool '
                       'nrouter-3ea5f9-0000002_nat_pool vrf '
                       'nrouter-3ea5f9-0000002 overload'),
                      ('ip nat pool nrouter-3ea5f9-0000002_nat_pool '
                       '172.16.0.124 172.16.0.124 netmask 255.255.0.0'),
                      ('ip route vrf nrouter-3ea5f9-0000002 0.0.0.0 0.0.0.0 '
                       'Port-channel10.3000 172.16.0.1'),
                      ('ip access-list standard '
                       'neutron_acl_0000002_2564_47f1a63e'),
                      'interface Port-channel10.2564',
                      'interface Port-channel10.3000',
                      'nrouter-3ea5f9-0000002']


class AciASR1kCfgSyncer(test_sync.ASR1kCfgSyncer):

    def setUp(self):
        super(AciASR1kCfgSyncer, self).setUp()

        self.config_syncer = aci_asr1k_cfg_syncer.ConfigSyncer(
            self.router_db_info, self.driver, self.hosting_device_info)

    def test_delete_invalid_cfg_empty_routers_list(self):
        cfg.CONF.set_override('enable_multi_region', False, 'multi_region')

        router_db_info = []

        self.config_syncer = aci_asr1k_cfg_syncer.ConfigSyncer(router_db_info,
                                                      self.driver,
                                                      self.hosting_device_info)
        self.config_syncer.get_running_config = mock.Mock(
            return_value=test_sync.ASR_BASIC_RUNNING_CFG_NO_MULTI_REGION)

        invalid_cfg = self.config_syncer.delete_invalid_cfg()
        self.assertEqual(8, len(invalid_cfg))
        for actual_cfg, expected_cfg in zip(invalid_cfg, INVALID_CFG_LIST_1):
            if isinstance(actual_cfg, LineItem):
                check_string = actual_cfg.line
            else:
                check_string = actual_cfg
            self.assertEqual(expected_cfg, check_string)

    def test_delete_invalid_cfg_with_multi_region_and_empty_routers_list(self):
        """
        This test verifies that the  cfg-syncer will delete invalid cfg
        if the neutron-db (routers dictionary list) happens to be empty.

        Since the neutron-db router_db_info is empty, all region 0000002
        running-config should be deleted.
        """
        cfg.CONF.set_override('enable_multi_region', True, 'multi_region')
        cfg.CONF.set_override('region_id', '0000002', 'multi_region')
        cfg.CONF.set_override('other_region_ids', ['0000001'], 'multi_region')
        router_db_info = []
        self.config_syncer = aci_asr1k_cfg_syncer.ConfigSyncer(router_db_info,
                                                      self.driver,
                                                      self.hosting_device_info)
        self.config_syncer.get_running_config = mock.Mock(
            return_value=test_sync.ASR_BASIC_RUNNING_CFG)
        invalid_cfg = self.config_syncer.delete_invalid_cfg()
        self.assertEqual(8, len(invalid_cfg))
        for actual_cfg, expected_cfg in zip(invalid_cfg, INVALID_CFG_LIST_2):
            if isinstance(actual_cfg, LineItem):
                check_string = actual_cfg.line
            else:
                check_string = actual_cfg
            self.assertEqual(expected_cfg, check_string)
