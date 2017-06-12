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

import sqlalchemy as sa
from sqlalchemy.ext import declarative
from sqlalchemy import orm


class HasProject(object):

    project_id = sa.Column(sa.String(255, index=True))

    def get_tenant_id(self):
        return self.project_id

    def set_tenant_id(self, value):
        self.project_id = value

    @declarative.declared_attr
    def tenant_id(cls):
        return orm.synonym(
            'project_id',
            descriptor=property(cls.get_tenant_id, cls.set_tenant_id))
