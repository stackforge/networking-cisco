# Copyright 2015 Cisco Systems Inc.
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

from neutron.api.v2 import attributes
from neutron.db import common_db_mixin
from neutron.extensions import providernet as pnet
from neutron.i18n import _LI
from neutron.plugins.ml2 import driver_api as api
from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class CiscoProviderNetDriver(api.ExtensionDriver,
                             common_db_mixin.CommonDbMixin):
    _supported_extension_alias = 'provider'

    def initialize(self):
        LOG.info(_LI("CiscoProviderNetDriver initialization complete"))

    @property
    def extension_alias(self):
        return self._supported_extension_alias

    def process_create_network(self, context, data, result):
        value = data.get(pnet.SEGMENTATION_ID)
        if value is not attributes.ATTR_NOT_SPECIFIED:
            result['is_provider_network'] = True
