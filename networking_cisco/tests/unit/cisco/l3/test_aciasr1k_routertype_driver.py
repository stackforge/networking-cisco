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

import mock
from oslo_utils import uuidutils
import webob.exc

from neutron.api.v2 import attributes
from neutron.common import exceptions as n_exc
from neutron import context
from neutron.extensions import l3

from networking_cisco.plugins.cisco.common import cisco_constants
from networking_cisco.plugins.cisco.extensions import routerhostingdevice
from networking_cisco.plugins.cisco.extensions import routerrole
from networking_cisco.plugins.cisco.extensions import routertypeawarescheduler
from networking_cisco.tests.unit.cisco.l3 import (
    test_asr1k_routertype_driver as asr1k)

_uuid = uuidutils.generate_uuid

EXTERNAL_GW_INFO = l3.EXTERNAL_GW_INFO
AGENT_TYPE_L3_CFG = cisco_constants.AGENT_TYPE_L3_CFG
ROUTER_ROLE_GLOBAL = cisco_constants.ROUTER_ROLE_GLOBAL
ROUTER_ROLE_LOGICAL_GLOBAL = cisco_constants.ROUTER_ROLE_LOGICAL_GLOBAL
ROUTER_ROLE_HA_REDUNDANCY = cisco_constants.ROUTER_ROLE_HA_REDUNDANCY
LOGICAL_ROUTER_ROLE_NAME = cisco_constants.LOGICAL_ROUTER_ROLE_NAME
ROUTER_ROLE_ATTR = routerrole.ROUTER_ROLE_ATTR
HOSTING_DEVICE_ATTR = routerhostingdevice.HOSTING_DEVICE_ATTR
AUTO_SCHEDULE_ATTR = routertypeawarescheduler.AUTO_SCHEDULE_ATTR
ASR_MODULE = ('networking_cisco.plugins.cisco.l3.drivers.asr1k.'
              'aci_asr1k_routertype_driver')
ASR_DRIVER = ASR_MODULE + '.AciASR1kL3RouterDriver'
ASR1K_ROUTER_TYPE = asr1k.Asr1kRouterTypeDriverTestCase.router_type
TEST_NET_CFG = {'Datacenter-Out': {
                    'gateway': '1.103.2.1',
                    'host_pool_cidr': '1.103.2.0/24',
                    'host_cidr_ver': 4, }}


class AciAsr1kRouterTypeDriverTestCase(
        asr1k.Asr1kRouterTypeDriverTestCase):

    router_type = 'AciASR1k_Neutron_router'
    external_network = {'name': 'ext-net-1',
                        'preexisting': False,
                        'external_epg': 'default-Datacenter-Out',
                        'host_pool_cidr': '10.1.2.1/24',
                        'encap': 'vlan-1031',
                        'switch': '401',
                        'port': '1/48',
                        'cidr_exposed': '1.103.2.254/24',
                        'gateway_ip': '1.103.2.1',
                        'router_id': '1.0.0.2',
                        'vlan_range': '1080:1090'}

    def setUp(self):
        super(AciAsr1kRouterTypeDriverTestCase, self).setUp()
        self.aci_driver = mock.patch(ASR_DRIVER + '.apic_driver',
                                     return_value=mock.Mock())
        self.aci_driver.start()

    def tearDown(self):
        self.aci_driver.stop()
        super(AciAsr1kRouterTypeDriverTestCase, self).tearDown()

    def _create_req(self, resource, data, id,
                    expected_code=webob.exc.HTTPOk.code,
                    fmt=None, subresource=None, neutron_context=None):
        req = self.new_update_request(resource, data, id,
                                      fmt=fmt,
                                      subresource=subresource)
        if neutron_context:
            # create a specific auth context for this request
            req.environ['neutron.context'] = neutron_context
        res = req.get_response(self._api_for_resource(resource))
        self.assertEqual(expected_code, res.status_int)
        return self.deserialize(self.fmt, res)

    def _test_router_update_set_gw_adds_global_router(self, set_context=False):
        tenant_id = _uuid()
        with self.network(tenant_id=tenant_id,
                          name='Datacenter-Out') as n_external:
            res = self._create_subnet(self.fmt, n_external['network']['id'],
                                      cidr='1.103.2.0/24', tenant_id=tenant_id)
            s = self.deserialize(self.fmt, res)
            self._set_net_external(s['subnet']['network_id'])
            # add a second subnet, just to verify that when we create
            # the global router that it picks the correct subnet
            res = self._create_subnet(self.fmt, n_external['network']['id'],
                                      cidr='1.103.3.0/24', tenant_id=tenant_id)
            s2 = self.deserialize(self.fmt, res)
            self._set_net_external(s2['subnet']['network_id'])
            with self.router(tenant_id=tenant_id,
                             set_context=set_context) as router1,\
                    self.router(name='router2', tenant_id=tenant_id,
                                set_context=set_context) as router2:
                r1 = router1['router']
                r2 = router2['router']
                # backlog processing will trigger one routers_updated
                # notification containing r1 and r2
                self.l3_plugin._process_backlogged_routers()
                # should have no global router yet
                r_ids = {r1['id'], r2['id']}
                self._verify_updated_routers(r_ids)
                ext_gw = {'network_id': s['subnet']['network_id']}
                r_spec = {'router': {l3.EXTERNAL_GW_INFO: ext_gw}}
                r1_after = self._update('routers', r1['id'], r_spec)['router']
                hd_id = r1_after[HOSTING_DEVICE_ATTR]
                # should now have one global router
                self._verify_updated_routers(r_ids, hd_id)
                self._update('routers', r2['id'], r_spec)
                # should still have only one global router
                self._verify_updated_routers(r_ids, hd_id)

    def _test_gw_router_create_add_interface(self, set_context=False):
        tenant_id = _uuid()
        with self.network(tenant_id=tenant_id) as n_external:
            res = self._create_subnet(self.fmt, n_external['network']['id'],
                                      cidr='10.0.1.0/24', tenant_id=tenant_id)
            s = self.deserialize(self.fmt, res)
            self._set_net_external(s['subnet']['network_id'])
            ext_gw = {'network_id': s['subnet']['network_id']}
            with self.router(tenant_id=tenant_id, external_gateway_info=ext_gw,
                             set_context=set_context) as router1:
                r1 = router1['router']
                self.l3_plugin._process_backlogged_routers()
                r1_after = self._show('routers', r1['id'])['router']
                hd_id = r1_after[HOSTING_DEVICE_ATTR]
                # should have one global router now
                self._verify_created_routers({r1['id']}, hd_id)
                with self.network(tenant_id=tenant_id) as n_internal:
                    res = self._create_subnet(self.fmt,
                                              n_internal['network']['id'],
                                              cidr='20.0.1.0/24',
                                              tenant_id=tenant_id)
                    s_int = self.deserialize(self.fmt, res)
                    self._set_net_external(s_int['subnet']['network_id'])
                    port = {'port': {'name': 'port',
                                     'network_id':
                                         s_int['subnet']['network_id'],
                                     'mac_address':
                                         attributes.ATTR_NOT_SPECIFIED,
                                     'fixed_ips':
                                         attributes.ATTR_NOT_SPECIFIED,
                                     'admin_state_up': True,
                                     'device_id': '',
                                     'device_owner': '',
                                     'tenant_id': s['subnet']['tenant_id']}}
                    ctx = context.Context('', '', is_admin=True)
                    port_db = self.core_plugin.create_port(ctx, port)
                    data = {'router_id': r1['id'], 'port_id': port_db['id']}
                    self._create_req('routers', data, r1['id'],
                                     subresource='add_router_interface')

    def test_gw_router_add_interface(self):
        self._test_gw_router_create_add_interface()

    def _test_gw_router_create_remove_interface(self, set_context=False):
        tenant_id = _uuid()
        with self.network(tenant_id=tenant_id,
                          name='Datacenter-Out') as n_external:
            res = self._create_subnet(self.fmt, n_external['network']['id'],
                                      cidr='10.0.1.0/24', tenant_id=tenant_id)
            s = self.deserialize(self.fmt, res)
            self._set_net_external(s['subnet']['network_id'])
            ext_gw = {'network_id': s['subnet']['network_id']}
            with self.router(tenant_id=tenant_id, external_gateway_info=ext_gw,
                             set_context=set_context) as router1:
                r1 = router1['router']
                self.l3_plugin._process_backlogged_routers()
                r1_after = self._show('routers', r1['id'])['router']
                hd_id = r1_after[HOSTING_DEVICE_ATTR]
                # should have one global router now
                self._verify_created_routers({r1['id']}, hd_id)
                with self.network(tenant_id=tenant_id) as n_internal:
                    res = self._create_subnet(self.fmt,
                                              n_internal['network']['id'],
                                              cidr='20.0.1.0/24',
                                              tenant_id=tenant_id)
                    s_int = self.deserialize(self.fmt, res)
                    self._set_net_external(s_int['subnet']['network_id'])
                    port = {'port': {'name': 'port',
                                     'network_id':
                                         s_int['subnet']['network_id'],
                                     'mac_address':
                                         attributes.ATTR_NOT_SPECIFIED,
                                     'fixed_ips':
                                         attributes.ATTR_NOT_SPECIFIED,
                                     'admin_state_up': True,
                                     'device_id': '',
                                     'device_owner': '',
                                     'tenant_id': s['subnet']['tenant_id']}}
                    ctx = context.Context('', '', is_admin=True)
                    port_db = self.core_plugin.create_port(ctx, port)
                    data = {'router_id': r1['id'], 'port_id': port_db['id']}
                    self._create_req('routers', data, r1['id'],
                                     subresource='add_router_interface')
                    self._create_req('routers', data, r1['id'],
                                     subresource='remove_router_interface')

    def test_gw_router_remove_interface(self):
        self._test_gw_router_create_remove_interface()

    def _test_router_update_unset_gw_keeps_global_router(self,
                                                         set_context=False):
        tenant_id = _uuid()
        with self.network(tenant_id=tenant_id,
                          name='Datacenter-Out') as n_external:
            res = self._create_subnet(self.fmt, n_external['network']['id'],
                                      cidr='10.0.1.0/24', tenant_id=tenant_id)
            s = self.deserialize(self.fmt, res)
            self._set_net_external(s['subnet']['network_id'])
            ext_gw = {'network_id': s['subnet']['network_id']}
            with self.router(tenant_id=tenant_id,
                             external_gateway_info=ext_gw,
                             set_context=set_context) as router1,\
                    self.router(name='router2', tenant_id=tenant_id,
                                external_gateway_info=ext_gw,
                                set_context=set_context) as router2:
                r1 = router1['router']
                r2 = router2['router']
                # backlog processing will trigger one routers_updated
                # notification containing r1 and r2
                self.l3_plugin._process_backlogged_routers()
                r1_after = self._show('routers', r1['id'])['router']
                hd_id = r1_after[HOSTING_DEVICE_ATTR]
                r_ids = {r1['id'], r2['id']}
                # should have one global router now
                self._verify_updated_routers(r_ids, hd_id, 0)
                r_spec = {'router': {l3.EXTERNAL_GW_INFO: None}}
                self._update('routers', r1['id'], r_spec)
                # should still have one global router
                self._verify_updated_routers(r_ids, hd_id, 0)
                self._update('routers', r2['id'], r_spec)
                # should have no global router now
                self._verify_updated_routers(r_ids)

    def _populate_hosting_driver(self):
        # This is here just to poulate the hosting driver
        tenant_id = _uuid()
        with self.network(tenant_id=tenant_id,
                          name='Datacenter-Out') as n_external:
            res = self._create_subnet(self.fmt, n_external['network']['id'],
                                      cidr='10.0.1.0/24', tenant_id=tenant_id)
            s = self.deserialize(self.fmt, res)
            self._set_net_external(s['subnet']['network_id'])
            ext_gw = {'network_id': s['subnet']['network_id']}
            with self.router(tenant_id=tenant_id, external_gateway_info=ext_gw,
                             set_context=False):
                self.l3_plugin._process_backlogged_routers()

    def test_update_router_no_hosting_device(self):
        class DummyRouterContext(object):

            def __init__(self, dummy_router):
                self.current = dummy_router

        dummy_router = {HOSTING_DEVICE_ATTR: None}
        dummy_router_context = DummyRouterContext(dummy_router)
        ctx = context.Context('', '', is_admin=True)
        self._populate_hosting_driver()
        mock_driver = mock.Mock()
        self.l3_plugin._router_drivers[ASR1K_ROUTER_TYPE] = mock_driver
        mock_driver.update_router_postcommit = mock.Mock()
        drv = self.l3_plugin._get_router_type_driver(ctx, self.router_type)
        drv.update_router_postcommit(ctx, dummy_router_context)
        mock_driver.update_router_postcommit.assert_not_called()

    def test_remove_router_interface_with_invalid_port_exception(self):
        class DummyRouterPortContext(object):

            def __init__(self, port_db):
                self.current = port_db

        self._populate_hosting_driver()
        ctx = context.Context('', '', is_admin=True)
        drv = self.l3_plugin._get_router_type_driver(ctx, self.router_type)
        with self.subnet() as private_sub:
            with self.port(private_sub) as p_port:
                port_db = p_port['port']
                dummy_router_port_context = DummyRouterPortContext(port_db)
                self.assertRaises(n_exc.UnsupportedPortDeviceOwner,
                                  drv.remove_router_interface_precommit,
                                  ctx, dummy_router_port_context)

    def test_update_floatingip_with_and_without_id(self):

        class DummyFloatingIpContext(object):

            def __init__(self, floatingip, original):
                self.current = floatingip
                self.original = original

        # This is here just to poulate the hosting driver
        FIP_ID1 = 'foo'
        FIP_ID2 = 'bar'
        tenant_id = _uuid()
        ctx = context.Context('', '', is_admin=True)
        fip_with_id1 = {'id': FIP_ID1}
        fip_with_id2 = {'id': FIP_ID2}
        fip_without_id = {}
        with self.network(tenant_id=tenant_id,
                          name='Datacenter-Out') as n_external:
            res = self._create_subnet(self.fmt, n_external['network']['id'],
                                      cidr='10.0.1.0/24', tenant_id=tenant_id)
            s = self.deserialize(self.fmt, res)
            self._set_net_external(s['subnet']['network_id'])
            ext_gw = {'network_id': s['subnet']['network_id']}
            with self.router(tenant_id=tenant_id, external_gateway_info=ext_gw,
                             set_context=False):
                self.l3_plugin._process_backlogged_routers()
            drv = self.l3_plugin._get_router_type_driver(ctx, self.router_type)
            drv._apic_driver = mock.Mock()
            apic_driver = drv.apic_driver

            curr = fip_without_id
            orig = fip_with_id1
            fip_ctx = DummyFloatingIpContext(curr, orig)
            drv.update_floatingip_precommit(ctx, fip_ctx)
            apic_driver.update_floatingip_precommit.assert_called_with(ctx,
                FIP_ID1, curr)
            apic_driver.update_floatingip_precommit.reset_mocks()
            drv.update_floatingip_postcommit(ctx, fip_ctx)
            apic_driver.update_floatingip_postcommit.assert_called_with(ctx,
                FIP_ID1, curr)
            apic_driver.update_floatingip_postcommit.reset_mocks()
            curr = fip_with_id2
            orig = fip_with_id1
            fip_ctx = DummyFloatingIpContext(curr, orig)
            drv.update_floatingip_precommit(ctx, fip_ctx)
            apic_driver.update_floatingip_precommit.assert_called_with(ctx,
                FIP_ID2, curr)
            apic_driver.update_floatingip_precommit.reset_mocks()
            drv.update_floatingip_postcommit(ctx, fip_ctx)
            apic_driver.update_floatingip_postcommit.assert_called_with(ctx,
                FIP_ID2, curr)


class AciAsr1kHARouterTypeDriverTestCase(
        asr1k.Asr1kHARouterTypeDriverTestCase):

    # For the HA tests we need more than one hosting device
    router_type = 'AciASR1k_Neutron_router'
    _is_ha_tests = True

    def setUp(self):
        super(AciAsr1kHARouterTypeDriverTestCase, self).setUp()
        self.aci_driver = mock.patch(ASR_DRIVER + '.apic_driver',
                                     return_value=mock.Mock())
        self.aci_driver.start()

    def tearDown(self):
        self.aci_driver.stop()
        super(AciAsr1kHARouterTypeDriverTestCase, self).tearDown()

    def _test_router_update_set_gw_adds_global_router(self, set_context=False):
        tenant_id = _uuid()
        with self.network(tenant_id=tenant_id,
                          name='Datacenter-Out') as n_external:
            res = self._create_subnet(self.fmt, n_external['network']['id'],
                                      cidr='1.103.2.0/24', tenant_id=tenant_id)
            s = self.deserialize(self.fmt, res)
            self._set_net_external(s['subnet']['network_id'])
            with self.router(tenant_id=tenant_id,
                             set_context=set_context) as router1,\
                    self.router(name='router2', tenant_id=tenant_id,
                                set_context=set_context) as router2:
                r1 = router1['router']
                r2 = router2['router']
                # backlog processing to schedule the routers
                self.l3_plugin._process_backlogged_routers()
                # should have no global router yet
                r_ids = [r1['id'], r2['id']]
                self._verify_ha_created_routers(r_ids, 1, has_gw=[False,
                                                                  False])
                ext_gw = {'network_id': s['subnet']['network_id']}
                r_spec = {'router': {l3.EXTERNAL_GW_INFO: ext_gw}}
                self._update('routers', r1['id'], r_spec)
                # should now have two global routers, one for hosting device
                # of user visible router r1 and one for the hosting device r1's
                # redundancy router
                hd_ids = self._verify_ha_updated_router(r1['id'])
                self._update('routers', r2['id'], r_spec)
                self._verify_ha_updated_router(r2['id'], hd_ids)

    def _test_router_update_unset_gw_keeps_global_router(self,
                                                         set_context=False):
        tenant_id = _uuid()
        with self.network(tenant_id=tenant_id,
                          name='Datacenter-Out') as n_external:
            res = self._create_subnet(self.fmt, n_external['network']['id'],
                                      cidr='10.0.1.0/24', tenant_id=tenant_id)
            s = self.deserialize(self.fmt, res)
            self._set_net_external(s['subnet']['network_id'])
            ext_gw = {'network_id': s['subnet']['network_id']}
            with self.router(tenant_id=tenant_id, external_gateway_info=ext_gw,
                             set_context=set_context) as router1,\
                    self.router(name='router2', tenant_id=tenant_id,
                                external_gateway_info=ext_gw,
                                set_context=set_context) as router2:
                r1 = router1['router']
                r2 = router2['router']
                # make sure we have only two eligible hosting devices
                # in this test
                qp = "template_id=00000000-0000-0000-0000-000000000008"
                hds = self._list('hosting_devices', query_params=qp)
                self._delete('hosting_devices',
                             hds['hosting_devices'][1]['id'])
                # backlog processing to schedule the routers
                self.l3_plugin._process_backlogged_routers()
                self._verify_ha_created_routers([r1['id'], r2['id']])
                r_spec = {'router': {l3.EXTERNAL_GW_INFO: None}}
                self._update('routers', r1['id'], r_spec)
                # should still have two global routers, we verify using r2
                self._verify_ha_updated_router(r2['id'])
                self._update('routers', r2['id'], r_spec)
                # should have no global routers now, we verify using r1
                self._verify_ha_updated_router(r2['id'], has_gw=False)

    def _test_gw_router_create_adds_global_router(self, set_context=False):
        tenant_id = _uuid()
        with self.network(tenant_id=tenant_id,
                          name='Datacenter-Out') as n_external:
            res = self._create_subnet(self.fmt, n_external['network']['id'],
                                      cidr='10.0.1.0/24', tenant_id=tenant_id)
            s = self.deserialize(self.fmt, res)
            self._set_net_external(s['subnet']['network_id'])
            ext_gw = {'network_id': s['subnet']['network_id']}
            with self.router(tenant_id=tenant_id, external_gateway_info=ext_gw,
                             set_context=set_context) as router1:
                r = router1['router']
                self.l3_plugin._process_backlogged_routers()
                # should now have one user-visible router, its single
                # redundancy router and two global routers (one for each of
                # the hosting devices of the aforementioned routers)
                self._verify_ha_created_routers([r['id']])


class L3CfgAgentAciAsr1kRouterTypeDriverTestCase(
        asr1k.L3CfgAgentAsr1kRouterTypeDriverTestCase):

    _is_ha_tests = True

    def setUp(self):
        super(L3CfgAgentAciAsr1kRouterTypeDriverTestCase, self).setUp()
        self.aci_driver = mock.patch(ASR_DRIVER + '.apic_driver',
                                     return_value=mock.Mock())
        self.aci_driver.start()

    def tearDown(self):
        self.aci_driver.stop()
        super(L3CfgAgentAciAsr1kRouterTypeDriverTestCase, self).tearDown()

    def _test_notify_op_agent(self, target_func, *args):
        kargs = [item for item in args]
        kargs.append(self._l3_cfg_agent_mock)
        target_func(*kargs)

    def _validate_ha_fip_ops(self, notifyApi, routers, first_operation):
        # 2 x add gateway (one for user visible router), one for redundancy
        # routers
        # 3 x add interface (one for each router),
        # 1 x update of floatingip (with 3 routers included),
        # 1 x deletion of floatingip (with 3 routers included)
        notify_call_1 = notifyApi.routers_updated.mock_calls[4]
        self.assertEqual(first_operation, notify_call_1[1][2])
        r_ids = {r['id'] for r in notify_call_1[1][1]}
        for r in routers:
            self.assertIn(r['id'], r_ids)
            r_ids.remove(r['id'])
        self.assertEqual(0, len(r_ids))
        delete_call = notifyApi.routers_updated.mock_calls[5]
        self.assertEqual('delete_floatingip', delete_call[1][2])
        r_ids = {r['id'] for r in delete_call[1][1]}
        for r in routers:
            self.assertIn(r['id'], r_ids)
            r_ids.remove(r['id'])
        self.assertEqual(0, len(r_ids))
        self.assertEqual(6, notifyApi.routers_updated.call_count)

    def _test_ha_floatingip_update_cfg_agent(self, notifyApi):
        with self.subnet() as private_sub:
            with self.port(private_sub) as p_port:
                private_port = p_port['port']
                with self.floatingip_no_assoc(private_sub) as fl_ip:
                    fip = fl_ip['floatingip']
                    routers = self._list('routers')['routers']
                    fip_spec = {'floatingip': {'port_id': private_port['id']}}
                    self._update('floatingips', fip['id'], fip_spec)
        self._validate_ha_fip_ops(notifyApi, routers, 'update_floatingip')

    def test_ha_floatingip_update_cfg_agent(self):
        self._test_notify_op_agent(self._test_ha_floatingip_update_cfg_agent)
