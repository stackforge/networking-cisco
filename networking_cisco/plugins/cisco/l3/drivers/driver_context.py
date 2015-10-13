# Copyright 2015 Cisco Systems, Inc.  All rights reserved.
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

# These resource contexts are adopted from a blueprint implementation what was
# started by Gary Duan, vArmour. That implementation was eventually abandoned.


class L3ContextBase(object):

    def __init__(self):
        # this is used to pass parameters from precommit() to postcommit()
        self._params = None

    @property
    def params(self):
        return self._params

    @params.setter
    def params(self, value):
        self._params = value


class RouterContext(L3ContextBase):

    def __init__(self, router, old_router=None):
        self._router = router
        self._original_router = old_router

    @property
    def current(self):
        return self._router

    @property
    def original(self):
        return self._original_router


class RouterPortContext(L3ContextBase):

    def __init__(self, port, old_port=None):
        self._port = port
        self._original_port = old_port

    @property
    def current(self):
        return self._port

    @property
    def original(self):
        return self._original_port

    @property
    def current_router(self):
        return self._port['device_id']

    @property
    def original_router(self):
        return self._original_port['device_id']


class FloatingipContext(L3ContextBase):

    def __init__(self, fip, old_fip=None):
        self._fip = fip
        self._original_fip = old_fip

    @property
    def current(self):
        return self._fip

    @property
    def original(self):
        return self._original_fip

    @property
    def current_router(self):
        return self._fip['router_id']

    @property
    def original_router(self):
        return self._original_fip['router_id']
