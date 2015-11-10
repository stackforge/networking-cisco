# Copyright 2015 Cisco Systems, Inc.
# All rights reserved.
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
#

from __future__ import print_function

from neutronclient.common import extension


class NetworkProfileBindings(extension.NeutronClientExtension):
    resource = 'network_profile_binding'
    resource_plural = '%ss' % resource
    object_path = '/%s' % resource_plural
    resource_path = '/%s/%%s' % resource_plural
    versions = ['2.0']
    allow_names = True


class NetworkProfileBindingList(extension.ClientExtensionList,
                               NetworkProfileBindings):
    """List network profiles that belong to a given tenant."""

    shell_command = 'cisco-network-profile-binding-list'

    list_columns = ['tenant_id', 'profile_id']
    pagination_support = True
    sorting_support = True
