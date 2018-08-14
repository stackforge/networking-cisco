# Copyright 2018 Cisco Systems, Inc.  All rights reserved.
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

from networking_cisco.backwards_compatibility import neutron_version as nv


if nv.NEUTRON_VERSION >= nv.NEUTRON_ROCKY_VERSION:
    from neutron_lib.api.attributes import *  # noqa
else:
    from neutron.api.v2.attributes import *  # noqa
    from neutron.api.v2 import attributes as _attributes
    RESOURCES = _attributes.RESOURCE_ATTRIBUTE_MAP
