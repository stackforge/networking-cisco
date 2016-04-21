# Copyright 2014 Cisco Systems, Inc.  All rights reserved.
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
from oslo_serialization import jsonutils

import mock
import os

from neutron.tests import base

from networking_cisco.plugins.cisco.cfg_agent.device_drivers.asr1k import (
    asr1k_cfg_syncer)

from networking_cisco.plugins.cisco.cfg_agent.device_drivers.asr1k import (
    asr1k_routing_driver as driver)

from networking_cisco.plugins.cisco.common.htparser import HTParser


cfg.CONF.register_opts(driver.ASR1K_DRIVER_OPTS, "multi_region")


class ASR1kCfgSyncer(base.BaseTestCase):

    def _read_neutron_db_data(self):
        """
        helper function for reading the dummy neutron router db
        """
        root_dir = os.path.dirname(__file__)
        with open(root_dir +
                  '/../etc/cfg_syncer/neutron_router_db.json',
                  'r') as fp:
            self.router_db_info = jsonutils.load(fp)

    def _read_asr_running_cfg(self, file_name='asr_running_cfg.json'):
        """
        helper function for reading sample asr running cfg files (json format)
        """
        root_dir = os.path.dirname(__file__)
        asr_running_cfg = (
            '/../etc/cfg_syncer/%s' % (file_name))

        with open(root_dir + asr_running_cfg, 'r') as fp:
            asr_running_cfg_json = jsonutils.load(fp)
            return asr_running_cfg_json

    def setUp(self):
        super(ASR1kCfgSyncer, self).setUp()

        self._read_neutron_db_data()
        self.hosting_device_info = \
            {'id': '00000000-0000-0000-0000-000000000003'}
        self.driver = mock.Mock()
        self.config_syncer = asr1k_cfg_syncer.ConfigSyncer(self.router_db_info,
                                                      self.driver,
                                                      self.hosting_device_info)

    def tearDown(self):
        super(ASR1kCfgSyncer, self).tearDown()

    def test_clean_interfaces_basic_multi_region_enabled(self):
        """
        In this test, we are simulating a cfg-sync, clean_interfaces for
        region 0000002 cfg-agent.  Running-cfg only exists for region
        0000001.

        At the end of test, we should expect zero entries in invalid_cfg.
        """

        cfg.CONF.set_override('enable_multi_region', True, 'multi_region')
        cfg.CONF.set_override('region_id', '0000002', 'multi_region')
        cfg.CONF.set_override('other_region_ids', ['0000001'], 'multi_region')

        intf_segment_dict = self.config_syncer.intf_segment_dict
        segment_nat_dict = self.config_syncer.segment_nat_dict

        invalid_cfg = []
        conn = self.driver._get_connection()

        asr_running_cfg = self._read_asr_running_cfg(
            file_name='asr_running_cfg_no_R2.json')

        parsed_cfg = HTParser(asr_running_cfg)

        invalid_cfg += self.config_syncer.clean_interfaces(conn,
                                              intf_segment_dict,
                                              segment_nat_dict,
                                              parsed_cfg)
        self.assertEqual(0, len(invalid_cfg))

    def test_clean_interfaces_multi_region_disabled(self):
        """
        In this test, we are simulating a cfg-sync, clean_interfaces for
        region 0000002 cfg-agent.  Running-cfg only exists for region
        0000001, but multi_region is disabled.

        At the end of test, we should expect zero entries in invalid_cfg.
        """
        cfg.CONF.set_override('enable_multi_region', False, 'multi_region')

        intf_segment_dict = self.config_syncer.intf_segment_dict
        segment_nat_dict = self.config_syncer.segment_nat_dict

        invalid_cfg = []
        conn = self.driver._get_connection()

        asr_running_cfg = self._read_asr_running_cfg(
            file_name='asr_running_cfg_no_R2.json')

        parsed_cfg = HTParser(asr_running_cfg)

        invalid_cfg += self.config_syncer.clean_interfaces(conn,
                                              intf_segment_dict,
                                              segment_nat_dict,
                                              parsed_cfg)
        self.assertEqual(0, len(invalid_cfg))

    def test_clean_interfaces_R2_run_cfg_present_multi_region_enabled(self):
        """
        In this test, we are simulating a cfg-sync, clean_interfaces for
        region 0000002 cfg-agent.  Existing running-cfg exists for region
        0000001 and 0000002.

        At the end of test, we should expect zero entries in invalid_cfg.
        """
        cfg.CONF.set_override('enable_multi_region', True, 'multi_region')
        cfg.CONF.set_override('region_id', '0000002', 'multi_region')
        cfg.CONF.set_override('other_region_ids', ['0000001'], 'multi_region')

        intf_segment_dict = self.config_syncer.intf_segment_dict
        segment_nat_dict = self.config_syncer.segment_nat_dict

        invalid_cfg = []
        conn = self.driver._get_connection()

        asr_running_cfg = self._read_asr_running_cfg()

        # This will trigger gateway only testing
        # asr_running_cfg = \
        #    self._read_asr_running_cfg('asr_basic_running_cfg.json')
        parsed_cfg = HTParser(asr_running_cfg)

        invalid_cfg += self.config_syncer.clean_interfaces(conn,
                                              intf_segment_dict,
                                              segment_nat_dict,
                                              parsed_cfg)
        # disabled for now
        # self.assertEqual(0, len(invalid_cfg))
