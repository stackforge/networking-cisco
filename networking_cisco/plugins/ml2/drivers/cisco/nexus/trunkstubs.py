# Copyright (c) 2017 Cisco Systems, Inc.
# All Rights Reserved.
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

# Dummy module containing the networking_cisco trunk APIs.
#
# Required for tox testing for neutron stable/mitaka.
# TODO(rcurran): Remove once networking_cisco is no longer supporting
#  stable/mitaka.


class NexusMDTrunkHandler(object):

    def _stub_trunk(self, port):
        return False

    is_trunk_parentport = _stub_trunk
    is_trunk_subport = _stub_trunk
    is_trunk_subport_baremetal = _stub_trunk


class NexusTrunkDriver(object):

    def create(self):
        pass
