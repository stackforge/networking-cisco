# Copyright 2017 Cisco Systems, Inc.
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
#

import datetime
import mock
import time

from neutron.tests import base

from networking_cisco.apps.saf.common import config
from networking_cisco.apps.saf.common import utils
from networking_cisco.apps.saf.db import dfa_db_models as dbm
from networking_cisco.apps.saf.server import cisco_dfa_rest as cdr
from networking_cisco.apps.saf.server import dfa_events_handler as deh
from networking_cisco.apps.saf.server import dfa_fail_recovery as dfr
from networking_cisco.apps.saf.server import dfa_server as ds
from networking_cisco.apps.saf.server.services.firewall.native import (
    fw_mgr as fw_native)

FAKE_DCNM_VERSION = '10.1.1'
FAKE_NETWORK_NAME = 'test_dfa_network'
FAKE_NETWORK_ID = '949fdd05-a26a-4819-a829-9fc2285de6ff'
FAKE_CFG_PROF_ID = '8c30f360ffe948109c28ab56f69a82e1'
FAKE_SEG_ID = 12345
FAKE_PROJECT_NAME = 'test_dfa_project'
FAKE_ORCH_ID = 'test_openstack'
FAKE_PROJECT_ID = 'aee5da7e699444889c662cf7ec1c8de7'
FAKE_CFG_PROFILE_NAME = 'defaultNetworkL2Profile'
FAKE_CFG_TYPE = 'IPVLAN'
FAKE_INSTANCE_NAME = 'test_dfa_instance'
FAKE_SUBNET_ID = '1a3c5ee1-cb92-4fd8-bff1-8312ac295d64'
FAKE_PORT_ID = 'ea0d92cf-d0cb-4ed2-bbcf-ed7c6aaea4cb'
FAKE_DEVICE_ID = '20305657-78b7-48f4-a7cd-1edf3edbfcad'
FAKE_SECURITY_GRP_ID = '4b5b387d-cf21-4594-b926-f5a5c602295f'
FAKE_MAC_ADDR = 'fa:16:3e:70:15:c4'
FAKE_IP_ADDR = '23.24.25.4'
FAKE_GW_ADDR = '23.24.25.1'
FAKE_DHCP_IP_START = '23.24.25.2'
FAKE_DHCP_IP_END = '23.24.25.254'
FAKE_HOST_ID = 'test_dfa_host'
FAKE_FWD_MODE = 'proxy-gateway'
FAKE_DCNM_USERNAME = 'cisco'
FAKE_DCNM_PASSWD = 'password'
FAKE_DCNM_IP = '1.1.2.2'
PRI_MEDIUM_START = 20


class FakeClass(object):
    """Fake class"""
    @classmethod
    def imitate(cls, *others):
        for other in others:
            for name in other.__dict__:
                try:
                    setattr(cls, name, mock.Mock())
                except (TypeError, AttributeError):
                    pass
        return cls


class FakeProject(object):
    """Fake Project class."""
    def __init__(self, proj_id, name, dci_id, desc):
        self.id = proj_id
        self.name = name
        self.dci_id = dci_id
        self.description = desc


class TestRpcCallback(base.BaseTestCase):
    """Test cases for DFA Server class."""

    def setUp(self):
        super(TestRpcCallback, self).setUp()

        self.dcnmpatcher = mock.patch(cdr.__name__ + '.DFARESTClient')
        self.mdcnm = self.dcnmpatcher.start()
        self.keys_patcher = mock.patch(deh.__name__ + '.EventsHandler')
        self.mkeys = self.keys_patcher.start()
        ds.DfaServer.__bases__ = (FakeClass.imitate(
            dfr.DfaFailureRecovery, dbm.DfaDBMixin, fw_native.FwMgr),)
        ds.DfaServer.get_all_projects.return_value = []
        ds.DfaServer.get_all_networks.return_value = []
        ds.DfaServer.register_segment_dcnm = mock.Mock()
        ds.DfaServer._setup_rpc = mock.Mock()
        config.default_dcnm_opts['dcnm']['dcnm_ip'] = FAKE_DCNM_IP
        config.default_dcnm_opts['dcnm']['dcnm_user'] = FAKE_DCNM_USERNAME
        config.default_dcnm_opts['dcnm']['dcnm_password'] = FAKE_DCNM_PASSWD
        config.default_dcnm_opts['dcnm']['timeout_resp'] = 0.01
        config.default_dcnm_opts['dcnm']['segmentation_id_min'] = 10000
        config.default_dcnm_opts['dcnm']['segmentation_id_max'] = 20000
        config.default_dcnm_opts['dcnm']['orchestrator_id'] = FAKE_ORCH_ID
        self.cfg = config.CiscoDFAConfig().cfg
        self.segid = int(self.cfg.dcnm.segmentation_id_min) + 10
        self.seg_Drvr = mock.patch(
            'networking_cisco.apps.saf.db.dfa_db_models.'
            'DfaSegmentTypeDriver').start()
        self.topologyDb = mock.patch(
            'networking_cisco.apps.saf.db.dfa_db_models.'
            'TopologyDiscoveryDb').start()
        self.dfa_server = ds.DfaServer(self.cfg)
        self.rpc_obj = ds.RpcCallBacks(self.dfa_server)

    def test_cli_get_networks(self):
        payload = {'id': None,
                   'name': FAKE_NETWORK_NAME,
                   'tenant_name': FAKE_PROJECT_NAME,
                   'tenant_id': FAKE_PROJECT_ID}
        networks = {}
        with mock.patch.object(self.dfa_server, 'get_network_by_filters',
                        return_value=networks) as mock_get_network, \
                mock.patch.object(self.dfa_server, 'get_project_name',
                        return_value=FAKE_PROJECT_NAME) as mock_get_project:
            self.rpc_obj.cli_get_networks(None, payload)

        mock_get_network.assert_called_once_with(payload)
        self.assertFalse(mock_get_project.called)

        networks = [utils.Dict2Obj({'name': FAKE_NETWORK_NAME,
                     'id': FAKE_NETWORK_ID,
                     'tenant_id': FAKE_PROJECT_ID,
                     'segmentation_id': FAKE_SEG_ID,
                     'vlan': '123',
                     'md': '0',
                     'cfgp': FAKE_CFG_PROFILE_NAME,
                     'result': 'SUCCESS',
                     'tenant_name': FAKE_PROJECT_NAME,
                     'source': 'openstack'})]
        with mock.patch.object(self.dfa_server, 'get_network_by_filters',
                        return_value=networks) as mock_get_network, \
                mock.patch.object(self.dfa_server, 'get_project_name',
                        return_value=FAKE_PROJECT_NAME) as mock_get_project:
            self.rpc_obj.cli_get_networks(None, payload)

        self.assertTrue(mock_get_network.called)
        mock_get_project.assert_called_once_with(FAKE_PROJECT_ID)

    def test_cli_get_instances(self):
        payload = {'name': FAKE_INSTANCE_NAME, 'port': FAKE_PORT_ID}
        instances = {}
        networks = {}
        with mock.patch.object(self.dfa_server, 'get_vms_by_filters',
                        return_value=instances) as mock_get_instance, \
                mock.patch.object(self.dfa_server, 'get_port_reason',
                        return_value=None) as mock_get_reason, \
                mock.patch.object(self.dfa_server, 'get_network',
                        return_value=networks) as mock_get_network, \
                mock.patch.object(self.dfa_server, 'get_project_name',
                        return_value=FAKE_PROJECT_NAME) as mock_get_project:
            self.rpc_obj.cli_get_instances(None, payload)

        mock_get_instance.assert_called_once_with(payload)
        self.assertFalse(mock_get_reason.called)
        self.assertFalse(mock_get_network.called)
        self.assertFalse(mock_get_project.called)

        instances = [utils.Dict2Obj({'name': FAKE_NETWORK_NAME,
                     'id': FAKE_NETWORK_ID,
                     'tenant_id': FAKE_PROJECT_ID,
                     'segmentation_id': FAKE_SEG_ID,
                     'vlan': '123',
                     'md': '0',
                     'cfgp': FAKE_CFG_PROFILE_NAME,
                     'result': 'SUCCESS',
                     'tenant_name': FAKE_PROJECT_NAME,
                     'source': 'openstack'})]
        with mock.patch.object(self.dfa_server, 'get_vms_by_filters',
                        return_value=instances) as mock_get_instance, \
                mock.patch.object(self.dfa_server, 'get_port_reason',
                        return_value=None) as mock_get_reason, \
                mock.patch.object(self.dfa_server, 'get_network',
                        return_value=networks) as mock_get_network, \
                mock.patch.object(self.dfa_server, 'get_project_name',
                        return_value=FAKE_PROJECT_NAME) as mock_get_project:
            self.rpc_obj.cli_get_instances(None, payload)

        mock_get_instance.assert_called_once_with(payload)
        self.assertTrue(mock_get_network.called)
        self.assertFalse(mock_get_reason.called)
        self.assertFalse(mock_get_project.called)

        networks = utils.Dict2Obj({'id': None,
                   'name': FAKE_NETWORK_NAME,
                   'tenant_name': FAKE_PROJECT_NAME,
                   'tenant_id': FAKE_PROJECT_ID})
        with mock.patch.object(self.dfa_server, 'get_vms_by_filters',
                        return_value=instances) as mock_get_instance, \
                mock.patch.object(self.dfa_server, 'get_port_reason',
                        return_value=None) as mock_get_reason, \
                mock.patch.object(self.dfa_server, 'get_network',
                        return_value=networks) as mock_get_network, \
                mock.patch.object(self.dfa_server, 'get_project_name',
                        return_value=FAKE_PROJECT_NAME) as mock_get_project:
            self.rpc_obj.cli_get_instances(None, payload)

        mock_get_instance.assert_called_once_with(payload)
        self.assertTrue(mock_get_network.called)
        self.assertTrue(mock_get_reason.called)
        self.assertTrue(mock_get_project.called)

    def test_cli_get_projects(self):
        payload = {'name': FAKE_PROJECT_NAME, 'tenant_id': FAKE_PROJECT_ID}

        projects = {}
        with mock.patch.object(self.dfa_server, 'get_project_by_filters',
                        return_value=projects) as mock_get_project:
            self.rpc_obj.cli_get_projects(None, payload)

        mock_get_project.assert_called_once_with(FAKE_PROJECT_NAME,
                                                 FAKE_PROJECT_ID)

    def test_get_fabric_summary(self):

        lan = {}
        with mock.patch.object(self.dfa_server.dcnm_client,
                        'default_lan_settings',
                        return_value=lan) as mock_get_lan, \
                mock.patch.object(self.dfa_server.dcnm_client, 'get_version',
                        return_value=FAKE_DCNM_VERSION) as mock_get_version:
            self.rpc_obj.get_fabric_summary(None, None)

        self.assertTrue(mock_get_lan.called)
        self.assertTrue(mock_get_version.called)

    def test_get_per_config_profile_detail(self):
        payload = {'profile': FAKE_CFG_PROFILE_NAME, 'ftype': FAKE_CFG_TYPE}
        cfg = {}
        with mock.patch.object(self.dfa_server.dcnm_client,
                '_config_profile_get_detail',
                return_value=cfg) as mock_get_config:
            res = self.rpc_obj.get_per_config_profile_detail(None, payload)

        mock_get_config.assert_called_once_with(FAKE_CFG_PROFILE_NAME,
                FAKE_CFG_TYPE)
        self.assertEqual(res, False)

        cfg = {'profile': FAKE_CFG_PROFILE_NAME}
        with mock.patch.object(self.dfa_server.dcnm_client,
                '_config_profile_get_detail',
                return_value=cfg) as mock_get_config:
            res = self.rpc_obj.get_per_config_profile_detail(None, payload)
        self.assertEqual(res, cfg)

    def test_get_config_profiles_detail(self):

        cfg = {}
        lan = {}
        with mock.patch.object(self.dfa_server.dcnm_client,
                '_config_profile_list', return_value=cfg) as mock_get_config, \
                mock.patch.object(self.dfa_server.dcnm_client,
                        'default_lan_settings',
                        return_value=lan) as mock_get_lan:
            res = self.rpc_obj.get_config_profiles_detail(None, None)

        self.assertTrue(mock_get_config.called)
        self.assertFalse(mock_get_lan.called)
        assert res is False

        cfg = [{'profile': FAKE_CFG_PROFILE_NAME, 'profileType': 'FPVLAN'}]
        with mock.patch.object(self.dfa_server.dcnm_client,
                '_config_profile_list', return_value=cfg) as mock_get_config, \
                mock.patch.object(self.dfa_server.dcnm_client,
                        'default_lan_settings',
                        return_value=lan) as mock_get_lan:
            res = self.rpc_obj.get_config_profiles_detail(None, None)

        self.assertTrue(mock_get_config.called)
        self.assertTrue(mock_get_lan.called)
        assert res is False

        lan = {'fabricEncapsulationMode': 'fabricpath'}
        with mock.patch.object(self.dfa_server.dcnm_client,
                '_config_profile_list', return_value=cfg) as mock_get_config, \
                mock.patch.object(self.dfa_server.dcnm_client,
                        'default_lan_settings',
                        return_value=lan) as mock_get_lan:
            res = self.rpc_obj.get_config_profiles_detail(None, None)

        self.assertTrue(mock_get_config.called)
        self.assertTrue(mock_get_lan.called)
        assert res is not False

    def test_get_all_networks_for_tenant(self):
        payload = {'tenant_id': FAKE_PROJECT_ID}

        networks = {}
        with mock.patch.object(self.dfa_server, 'get_network_by_filters',
                        return_value=networks) as mock_get_network, \
                mock.patch.object(self.dfa_server, 'get_project_name',
                        return_value=None) as mock_get_project:
            res = self.rpc_obj.get_all_networks_for_tenant(None, payload)

        mock_get_project.assert_called_once_with(FAKE_PROJECT_ID)
        self.assertTrue(mock_get_project.called)
        self.assertFalse(mock_get_network.called)
        assert res is False

        with mock.patch.object(self.dfa_server, 'get_network_by_filters',
                        return_value=networks) as mock_get_network, \
                mock.patch.object(self.dfa_server, 'get_project_name',
                        return_value=FAKE_PROJECT_NAME) as mock_get_project:
            res = self.rpc_obj.get_all_networks_for_tenant(None, payload)

        self.assertTrue(mock_get_project.called)
        self.assertTrue(mock_get_network.called)

    def test_get_instance_by_tenant_id(self):
        payload = {'tenant_id': FAKE_PROJECT_ID}

        vms = {}
        with mock.patch.object(self.dfa_server, 'get_project_name',
                        return_value=None) as mock_get_project, \
                mock.patch.object(self.dfa_server, 'get_vms_per_tenant',
                        return_value=vms) as mock_get_vms:
            res = self.rpc_obj.get_instance_by_tenant_id(None, payload)

        mock_get_project.assert_called_once_with(FAKE_PROJECT_ID)
        self.assertFalse(mock_get_vms.called)
        assert res is False

        vms = [[utils.Dict2Obj({'name': 'vm1', 'result': 'SUCCESS'}),
                utils.Dict2Obj({'name': 'net1'})]]
        with mock.patch.object(self.dfa_server, 'get_project_name',
                        return_value=FAKE_PROJECT_NAME) as mock_get_project, \
                mock.patch.object(self.dfa_server, 'get_port_reason',
                        retuen_value=None) as mock_port_reason, \
                mock.patch.object(self.dfa_server, 'get_vms_per_tenant',
                        return_value=vms) as mock_get_vms:
            res = self.rpc_obj.get_instance_by_tenant_id(None, payload)

        self.assertTrue(mock_get_vms.called)
        self.assertTrue(mock_port_reason.called)
        assert res is not False

    def test_get_project_detail(self):
        payload = {'tenant_id': FAKE_PROJECT_ID}

        projects = [None]
        with mock.patch.object(self.dfa_server, 'get_project_by_filters',
                        return_value=projects) as mock_get_project, \
                mock.patch.object(self.dfa_server, 'get_project_reason',
                        return_value=None) as mock_project_reason, \
                mock.patch.object(self.dfa_server.dcnm_client,
                        'get_partition_segmentId',
                        return_value=FAKE_SEG_ID) as mock_get_seg:
            res = self.rpc_obj.get_project_detail(None, payload)

        mock_get_project.assert_called_once_with(None, FAKE_PROJECT_ID)
        self.assertFalse(mock_project_reason.called)
        self.assertFalse(mock_get_seg.called)
        assert res is False

        projects = [utils.Dict2Obj({'name': FAKE_PROJECT_NAME})]
        with mock.patch.object(self.dfa_server, 'get_project_by_filters',
                        return_value=projects) as mock_get_project, \
                mock.patch.object(self.dfa_server, 'get_project_reason',
                        return_value=None) as mock_project_reason, \
                mock.patch.object(self.dfa_server.dcnm_client,
                        'get_partition_segmentId',
                        return_value=FAKE_SEG_ID) as mock_get_seg:
            res = self.rpc_obj.get_project_detail(None, payload)

        mock_get_seg.assert_called_once_with(FAKE_PROJECT_NAME, 'CTX')
        mock_project_reason.assert_called_once_with(FAKE_PROJECT_ID)
        assert res is not False

    def test_get_agents_details(self):
        agents = None
        with mock.patch.object(self.dfa_server, 'get_agents_by_filters',
                return_value=agents) as mock_get_agents:
            res = self.rpc_obj.get_agents_details(None, None)

        mock_get_agents.assert_called_once_with(None)
        assert res is False

        agents = [utils.Dict2Obj({'name': 'agent1',
                'heartbeat': datetime.datetime.now(),
                'created': datetime.datetime.now(),
                'configurations': utils.Dict2Obj({'topo': 'ens203'})})]
        with mock.patch.object(self.dfa_server, 'get_agents_by_filters',
                return_value=agents) as mock_get_agents:
            res = self.rpc_obj.get_agents_details(None, None)
        assert res is not False

    def test_get_agent_details_per_host(self):
        payload = {'host': 'agent1'}

        agents = None
        with mock.patch.object(self.dfa_server, 'get_agents_by_filters',
                return_value=agents) as mock_get_agents:
            res = self.rpc_obj.get_agent_details_per_host(None, payload)

        mock_get_agents.assert_called_once_with('agent1')
        assert res is False

        agents = utils.Dict2Obj({'host': 'agent1',
                                'heartbeat': datetime.datetime.now(),
                                'created': datetime.datetime.now(),
                                'configurations': {'topo': 'ens203'}}})
        with mock.patch.object(self.dfa_server, 'get_agents_by_filters',
                return_value=agents) as mock_get_agents:
            res = self.rpc_obj.get_agent_details_per_host(None, payload)
        assert res is not False

    def test_associate_profile_with_network(self):
        msg = {'tenant_id': FAKE_PROJECT_ID,
               'network_id': FAKE_NETWORK_ID,
               'config_profile': FAKE_CFG_PROFILE_NAME}
        event_type = 'associate.network.profile'

        payload = (event_type, msg)
        with mock.patch.object(self.dfa_server.pqueue, 'put',
                return_value=None) as mock_pqueue_put:
            self.rpc_obj.associate_profile_with_network(None, msg)

        mock_pqueue_put.assert_called_once_with((PRI_MEDIUM_START + 1,
                                                 time.ctime(),
                                                 payload))

    def test_associate_dci_id_to_project(self):
        payload = {'tenant_id': FAKE_PROJECT_ID,
                   'tenant_name': FAKE_PROJECT_NAME,
                   'dci_id': 1001}

        with mock.patch.object(self.dfa_server, 'get_project_name',
                    return_value=None) as mock_get_project, \
                mock.patch.object(self.dfa_server, 'update_project_entry',
                        return_value=None) as mock_update_project, \
                mock.patch.object(self.dfa_server.dcnm_client,
                        'update_project',
                        return_value=None) as mock_dcnm_update_project:
            res = self.rpc_obj.associate_dci_id_to_project(None, payload)

        mock_get_project.assert_called_once_with(FAKE_PROJECT_ID)
        self.assertFalse(mock_update_project.called)
        self.assertFalse(mock_dcnm_update_project.called)
        assert res is None

        with mock.patch.object(self.dfa_server, 'get_project_name',
                    return_value=FAKE_PROJECT_NAME) as mock_get_project, \
                mock.patch.object(self.dfa_server, 'update_project_entry',
                        return_value=None) as mock_update_project, \
                mock.patch.object(self.dfa_server.dcnm_client,
                        'update_project',
                        return_value=None) as mock_dcnm_update_project:
            res = self.rpc_obj.associate_dci_id_to_project(None, payload)

        self.assertTrue(mock_update_project.called)
        self.assertTrue(mock_dcnm_update_project.called)
