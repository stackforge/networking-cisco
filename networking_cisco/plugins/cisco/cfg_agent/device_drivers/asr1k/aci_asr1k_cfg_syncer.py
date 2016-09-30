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

from oslo_config import cfg
from oslo_log import log as logging

from networking_cisco.plugins.cisco.cfg_agent.device_drivers.asr1k import (
    asr1k_cfg_syncer as syncer)


LOG = logging.getLogger(__name__)


IP_REGEX = "(?:[0-9]{1,3}\.){3}[0-9]{1,3}"

SET_ROUTE_REGEX = ("ip route vrf " +
    syncer.NROUTER_REGEX + " " + IP_REGEX + " " + IP_REGEX +
    " \S+\.(\d+) (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")
SET_ROUTE_MULTI_REGION_REGEX = ("ip route vrf " +
    syncer.NROUTER_MULTI_REGION_REGEX + " " +
    IP_REGEX + " " + IP_REGEX +
    " \S+\.(\d+) (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")


class ConfigSyncer(syncer.ConfigSyncer):

    def __init__(self, router_db_info, driver,
                 hosting_device_info, test_mode=False):
        super(ConfigSyncer, self).__init__(router_db_info,
                                           driver,
                                           hosting_device_info,
                                           test_mode=test_mode)
        if (cfg.CONF.multi_region.enable_multi_region):
            self.route_regex = SET_ROUTE_MULTI_REGION_REGEX
        else:
            self.route_regex = SET_ROUTE_REGEX
