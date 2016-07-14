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
import unittest
import webob.exc

from neutron.api.v2 import attributes
from neutron import context
from neutron.extensions import l3
from oslo_utils import uuidutils

from networking_cisco.plugins.cisco.common import cisco_constants
from networking_cisco.plugins.cisco.extensions import routerhostingdevice
from networking_cisco.plugins.cisco.extensions import routerrole
from networking_cisco.plugins.cisco.extensions import routertypeawarescheduler
from networking_cisco.tests.unit.cisco.l3 import (
    test_asr1k_routertype_driver as asr1k_test)
from networking_cisco.tests.unit.cisco.l3 import (
    test_l3_routertype_aware_schedulers as cisco_test_case)

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
ASR1K_ROUTER_TYPE = asr1k_test.Asr1kRouterTypeDriverTestCase.router_type
TEST_NET_CFG = {'Datacenter-Out': {
                    'gateway': '1.103.2.1',
                    'host_pool_cidr': '1.103.2.0/24',
                    'host_cidr_ver': 4, }}


class AciAsr1kRouterTypeDriverTestCase(
        asr1k_test.Asr1kRouterTypeDriverTestCase):

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
    external_mgmt_network = {'name': 'ext-net-2',
                             'preexisting': False,
                             'external_epg': 'default-Management-Out',
                             'host_pool_cidr': '10.1.3.1/24',
                             'encap': 'vlan-1031',
                             'switch': '401',
                             'port': '1/48',
                             'cidr_exposed': '1.103.3.254/24',
                             'gateway_ip': '1.103.3.1',
                             'router_id': '1.0.0.3',
                             'vlan_range': '1180:1190'}

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

    def _test_create_gateway_router(self, set_context=False,
                                    same_tenant=True, same_ext_net=True):
        tenant_id_1 = _uuid()
        tenant_id_2 = tenant_id_1 if same_tenant is True else _uuid()
        with self.network(tenant_id=tenant_id_1,
                          name='Datacenter-Out') as n_external_1,\
                self.network(tenant_id=tenant_id_2,
                             name='Management-Out') as n_external_2:
            ext_net_1_id = n_external_1['network']['id']
            self._set_net_external(ext_net_1_id)
            self._create_subnet(self.fmt, ext_net_1_id, cidr='10.0.1.0/24',
                                tenant_id=tenant_id_1)
            if same_ext_net is False:
                ext_net_2_id = n_external_2['network']['id']
                self._set_net_external(ext_net_2_id)
                self._create_subnet(self.fmt, ext_net_2_id, cidr='10.0.2.0/24',
                                    tenant_id=tenant_id_2)
            else:
                ext_net_2_id = ext_net_1_id
            ext_gw_1 = {'network_id': ext_net_1_id}
            ext_gw_2 = {'network_id': ext_net_2_id}
            with self.router(
                    tenant_id=tenant_id_1, external_gateway_info=ext_gw_1,
                    set_context=set_context) as router1:
                r1 = router1['router']
                self.l3_plugin._process_backlogged_routers()
                r1_after = self._show('routers', r1['id'])['router']
                hd_id = r1_after[HOSTING_DEVICE_ATTR]
                # should have one global router now
                self._verify_routers({r1['id']}, {ext_net_1_id}, hd_id)
                with self.router(
                        tenant_id=tenant_id_2, external_gateway_info=ext_gw_1,
                        set_context=set_context) as router2:
                    r2 = router2['router']
                    self.l3_plugin._process_backlogged_routers()
                    # should still have only one global router
                    self._verify_routers({r1['id'], r2['id']}, {ext_net_1_id},
                                         hd_id)
                    with self.router(name='router2', tenant_id=tenant_id_2,
                                     external_gateway_info=ext_gw_2,
                                     set_context=set_context) as router3:
                        r3 = router3['router']
                        self.l3_plugin._process_backlogged_routers()
                        # should still have only one global router but now with
                        # one extra auxiliary gateway port
                        self._verify_routers(
                            {r1['id'], r2['id'], r3['id']},
                            {ext_net_1_id, ext_net_2_id}, hd_id)

    def _test_gw_router_create_add_interface(self, set_context=False):
        tenant_id = _uuid()
        with self.network(tenant_id=tenant_id) as n_external:
            ext_net_id = n_external['network']['id']
            res = self._create_subnet(self.fmt, ext_net_id,
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
                self._verify_routers({r1['id']}, {ext_net_id}, hd_id=hd_id)
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
            ext_net_id = n_external['network']['id']
            res = self._create_subnet(self.fmt, ext_net_id,
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
                self._verify_routers({r1['id']}, {ext_net_id}, hd_id=hd_id)
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
            ext_net_id = n_external['network']['id']
            res = self._create_subnet(self.fmt, ext_net_id,
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
                self._verify_routers(r_ids, {ext_net_id}, hd_id, [0])
                r_spec = {'router': {l3.EXTERNAL_GW_INFO: None}}
                self._update('routers', r1['id'], r_spec)
                # should still have one global router
                self._verify_routers(r_ids, {ext_net_id}, hd_id, [0])
                self._update('routers', r2['id'], r_spec)
                # should have no global router now
                self._verify_routers(r_ids, {ext_net_id})

    def _test_create_router_adds_no_aux_gw_port_to_global_router(
            self, set_context=False, same_tenant=True):
        tenant_id_1 = _uuid()
        tenant_id_2 = tenant_id_1 if same_tenant is True else _uuid()
        with self.network(tenant_id=tenant_id_1,
                          name='Datacenter-Out') as n_external_1:
            ext_net_1_id = n_external_1['network']['id']
            self._set_net_external(ext_net_1_id)
            self._create_subnet(self.fmt, ext_net_1_id, cidr='10.0.1.0/24',
                                tenant_id=tenant_id_1)
            ext_gw_1 = {'network_id': ext_net_1_id}
            with self.router(
                    tenant_id=tenant_id_1, external_gateway_info=ext_gw_1,
                    set_context=set_context) as router1:
                r1 = router1['router']
                self.l3_plugin._process_backlogged_routers()
                r1_after = self._show('routers', r1['id'])['router']
                hd_id = r1_after[HOSTING_DEVICE_ATTR]
            with self.router(tenant_id=tenant_id_2,
                             set_context=set_context) as router2:
                r2 = router2['router']
                # backlog processing will trigger one routers_updated
                # notification containing r1 and r2
                self.l3_plugin._process_backlogged_routers()
                self._verify_routers({r1['id'], r2['id']}, {ext_net_1_id},
                                     hd_id)

    @unittest.skip("Behavior allowed in ACI integration")
    def test_router_interface_add_refused_for_unsupported_topology(self):
        pass

    @unittest.skip("Behavior allowed in ACI integration")
    def test_router_interface_add_refused_for_unsupported_topology_dt(self):
        pass


class AciAsr1kHARouterTypeDriverTestCase(
        asr1k_test.Asr1kHARouterTypeDriverTestCase):

    # For the HA tests we need more than one hosting device
    router_type = 'AciASR1k_Neutron_router'
    _is_ha_tests = True

    def setUp(self):
        super(AciAsr1kHARouterTypeDriverTestCase, self).setUp()
        self.aci_driver = mock.patch(ASR_DRIVER + '.apic_driver',
                                     return_value=mock.Mock())
        self.drv = self.aci_driver.start()

    def tearDown(self):
        self.aci_driver.stop()
        super(AciAsr1kHARouterTypeDriverTestCase, self).tearDown()

    def test_delete_floating_ip_pre_and_post(self):
        with self.subnet() as ext_s, self.subnet(cidr='10.0.1.0/24') as s:
            s1 = ext_s['subnet']
            ext_net_id = s1['network_id']
            self._set_net_external(ext_net_id)
            with self.router(
                    external_gateway_info={'network_id': ext_net_id}) as r,\
                    self.port(s) as p:
                self._router_interface_action('add', r['router']['id'], None,
                                              p['port']['id'])
                p1 = p['port']
                fip = {'floatingip': {'floating_network_id': ext_net_id,
                                      'port_id': p1['id'],
                                      'tenant_id': s1['tenant_id']}}
                ctx = context.get_admin_context()
                floating_ip = self.l3_plugin.create_floatingip(ctx, fip)
                self.l3_plugin.delete_floatingip(ctx, floating_ip['id'])
                self.drv.delete_floatingip_precommit.assert_called_once_with(
                    ctx, floating_ip['id'])
                self.drv.delete_floatingip_postcommit.assert_called_once_with(
                    ctx, floating_ip['id'])

    @unittest.skip("Behavior allowed in ACI integration")
    def test_router_interface_add_refused_for_unsupported_topology(self):
        pass

    @unittest.skip("Behavior allowed in ACI integration")
    def test_router_interface_add_refused_for_unsupported_topology_dt(self):
        pass


class L3CfgAgentAciAsr1kRouterTypeDriverTestCase(
        asr1k_test.L3CfgAgentAsr1kRouterTypeDriverTestCase):

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


class AciAsr1kRouterTypeDriverNeutronTestCase(
        cisco_test_case.L3RoutertypeAwareHostingDeviceSchedulerTestCaseBase):

    router_type = 'AciASR1k_Neutron_router'

    def setUp(self):
        super(AciAsr1kRouterTypeDriverNeutronTestCase, self).setUp()
        self.dummy_gbp_l3 = mock.Mock()
        self.l3_plugin._core_plugin.mechanism_manager = mock.MagicMock()

    @unittest.skip("Duplicate from other test class")
    def test_agent_registration_bad_timestamp(self):
        pass

    @unittest.skip("Duplicate from other test class")
    def test_agent_registration_invalid_timestamp_allowed(self):
        pass

    def test_get_apic_driver(self):
        tenant_id = _uuid()
        ctx = context.Context('', '', is_admin=True)
        with self.router(tenant_id=tenant_id) as router1:
            self.l3_plugin._process_backlogged_routers()
            r1 = router1['router']
            router_type_id = self.l3_plugin.get_router_type_id(ctx,
                r1['id'])
            with mock.patch('oslo_utils.importutils.import_object',
                            return_value=self.dummy_gbp_l3):
                driver = self.l3_plugin._get_router_type_driver(context,
                    router_type_id)
                self.assertEqual(self.dummy_gbp_l3, driver.apic_driver)
