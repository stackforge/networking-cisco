# Copyright (c) 2016 Cisco Systems
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

from aim import aim_manager
from neutron.plugins.ml2 import driver_api


class APICNameMapper(object):
    def bridge_domain(tenant, id, name):
        # REVISIT(rkukura): Temporary implementation
        return 'BD_' + id


class APICMechanismDriver(driver_api.MechanismDriver):

    def initialize(self):
        self.aim = aim_manager.AimManager()
        self.mapper = APICNameMapper()

    def create_network_precommit(self, context):
        # REVISIT(rkukura): We should probably ignore the network if
        # context.network_segments contains no segments with
        # network_type 'opflex'.

        # TODO(rkukura): Deal with shared, external, nat_enabled, ...

        aim_context = aim_manager.AimContext(context.session)
        tenant = self.aim.get_tenant(aim_context,
                                     context.current['tenant_id'])
        id = context.current['id']
        name = context.current['name']
        dn = self.mapper.bridge_domain(tenant, id, name)
        self.aim.create_bridge_domain(aim_context, tenant=tenant, id=id, dn=dn)

        # TODO(rkukura): Do we need to update extension attributes
        # such as 'apic:dn', 'apic:status', or 'apic:status_detail' in
        # context.current, or will the extension driver do this before
        # the results are returned to the client?

    def update_network_precommit(self, context):
        # REVISIT(rkukura): Do we need to check if the tenant's name
        # has changed, or is that immutable?

        # REVISIT(rkukura): Can changing anything else, such as the
        # 'shared' attribute, effect the DN?

        name = context.current['name']
        if name != context.original['name']:
            aim_context = aim_manager.AimContext(context.session)
            tenant = self.aim.get_tenant(aim_context,
                                         context.current['tenant_id'])
            id = context.current['id']
            dn = self.mapper.bridge_domain(tenant, id, name)
            self.aim.update_bridge_domain(aim_context, id=id, dn=dn)

        # TODO(rkukura): Do we need to update extension attributes
        # such as 'apic:dn', 'apic:status', or 'apic:status_detail' in
        # context.current, or will the extension driver do this?

    def delete_network_precommit(self, context):
        aim_context = aim_manager.AimContext(context.session)
        self.aim.delete_bridge_domain(aim_context, id=id)

    def create_subnet_precommit(self, context):
        pass

    def update_subnet_precommit(self, context):
        pass

    def delete_subnet_precommit(self, context):
        pass

    def create_port_precommit(self, context):
        pass

    def update_port_precommit(self, context):
        pass

    def delete_port_precommit(self, context):
        pass

    def bind_port(self, context):
        pass

    def check_vlan_transparency(self, context):
        pass

    def get_workers(self):
        return ()
