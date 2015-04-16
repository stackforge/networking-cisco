# Copyright (c) 2014 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from collections import namedtuple
import hashlib
import mock

from networking_cisco.plugins.ml2.drivers.cisco.n1kv import (
    constants as n1kv_const)
from networking_cisco.plugins.ml2.drivers.cisco.n1kv import (
    n1kv_client)
from networking_cisco.plugins.ml2.drivers.cisco.n1kv import (
    n1kv_sync)
from test_cisco_n1kv_mech import TestN1KVMechanismDriver


class TestN1kvSyncDriver(TestN1KVMechanismDriver):
    """Test N1kv md5 based sync between neutron and VSM."""

    TEST_VSM_NETWORK_PROFILES = ['thisisatestnetworkprofile', ]
    TEST_VSM_NETWORKS = ['abcdefghijklmnopqrstuvwxyz',
                         'abcdefghijklmnopqrstuvwxy2', ]
    TEST_VSM_SUBNETS = ['thisisthefirsttestsubnet', ]
    TEST_VSM_PORTS = ['thisisthefirsttestport', 'thisisthesecondtestport', ]

    TEST_NEUTRON_NETWORK_PROFILES = TEST_VSM_NETWORK_PROFILES[:]
    TEST_NEUTRON_NETWORKS = TEST_VSM_NETWORKS[:]
    TEST_NEUTRON_SUBNETS = TEST_VSM_SUBNETS[:]
    TEST_NEUTRON_PORTS = TEST_VSM_PORTS[:]

    def setUp(self):
        super(TestN1kvSyncDriver, self).setUp()

        # fake n1kv_client.Client.list_md5_hashes() for getting VSM MD5
        # hashes
        list_md5_patcher = mock.patch(n1kv_client.__name__ +
                                      ".Client.list_md5_hashes")
        fake_list_md5 = list_md5_patcher.start()
        fake_list_md5.return_value = self._fake_get_vsm_md5_hashes()

        # fake SyncDriver._get_neutron_resource() for getting resources on
        # Neutron
        self.sync_driver = n1kv_sync.N1kvSyncDriver(None)
        self.sync_driver._get_neutron_resource = mock.MagicMock(
            side_effect=self._fake_get_neutron_res)

    def _fake_get_neutron_res(self, res):
        """
        Mock function replacing SyncDriver._get_neutron_resource().

        It would be called from SyncDriver._md5_hash_comparison() function
        :param res: network_profiles, networks, subnets or ports
        :return: list of objects or dictionaries for all entries belonging
                 to res
        """
        res_list = getattr(self, 'TEST_NEUTRON_' + res.upper())
        net_profile = namedtuple('NetProfile', ('id',))
        if res == n1kv_const.NETWORK_PROFILES:
            return [net_profile(np) for np in res_list]
        return [{'id': x} for x in res_list]

    def _fake_get_vsm_md5_hashes(self, *args):
        """
        Mock function replacing n1kv_client.Client.list_md5_hashes().

        It would be eventually called from SyncDriver._md5_hash_comparison()
        function
        :param args: Parameters for the original function. Have no use within
                     this mocked function
        :return: Dictionary with all VSM md5 hashes (including consolidated
                 md5) as would have been returned by VSM REST APIs
        """
        res_order = [n1kv_const.NETWORK_PROFILE_MD5, n1kv_const.SUBNET_MD5,
                     n1kv_const.NETWORK_MD5, n1kv_const.PORT_MD5]

        res_md5 = {md5_res: hashlib.md5() for md5_res in res_order}
        for (res, md5) in res_md5.items():
            res_name = 'TEST_VSM_' + res.split('_md5')[0].upper() + 'S'
            map(lambda uuid: md5.update(uuid), sorted(getattr(self, res_name)))
            res_md5[res] = md5.hexdigest()

        consolidated_md5 = hashlib.md5()
        map(lambda x: consolidated_md5.update(res_md5[x]), res_order)
        res_md5[n1kv_const.CONSOLIDATED_MD5] = consolidated_md5.hexdigest()

        vsm_md5_hashes = {
            'md5_hashes': {
                'properties': res_md5
            }
        }
        return vsm_md5_hashes

    def test_md5_hash_comparison_all(self):
        """Compare Neutron-VSM MD5 hashes with identical configurations."""
        # test with identical VSM-neutron configurations
        self.sync_driver._md5_hash_comparison(None)
        self.assertFalse(any(self.sync_driver.sync_resource.values()))

    def test_md5_hash_comparison_networks(self):
        """
        Compare Neutron-VSM MD5 hashes for Networks.

        Test whether or not Neutron-VSM sync would be triggered for three test
        cases:
        i)   when neutron-VSM have identical networks
        ii)  when VSM has a missing network
        iii) when VSM has an extra network
        """
        # test network MD5 hashes with identical VSM-neutron configurations
        self.sync_driver._md5_hash_comparison(None)
        self.assertFalse(self.sync_driver.sync_resource[n1kv_const.NETWORKS])

        # test network MD5 mismatch with missing VSM network
        self.TEST_VSM_NETWORKS.remove('abcdefghijklmnopqrstuvwxy2')
        self.sync_driver._md5_hash_comparison(None)
        self.assertTrue(self.sync_driver.sync_resource[n1kv_const.NETWORKS])
        # restore TEST_VSM_NETWORKS to synced state
        self.TEST_VSM_NETWORKS.append('abcdefghijklmnopqrstuvwxy2')

        # test network MD5 mismatch with extra VSM network
        self.TEST_VSM_NETWORKS.append('thisisanextranetworkonVSM')
        self.sync_driver._md5_hash_comparison(None)
        self.assertTrue(self.sync_driver.sync_resource[n1kv_const.NETWORKS])
        # restore TEST_VSM_NETWORKS to synced state
        self.TEST_VSM_NETWORKS.remove('thisisanextranetworkonVSM')

    def test_md5_hash_comparison_ports(self):
        """
        Compare Neutron-VSM MD5 hashes for Ports.

        Test whether or not Neutron-VSM sync would be triggered for three test
        cases:
        i)   when neutron-VSM have identical ports
        ii)  when VSM has a missing port
        iii) when VSM has an extra port
        """
        # test port MD5 hashes with identical VSM-neutron configurations
        self.sync_driver._md5_hash_comparison(None)
        self.assertFalse(self.sync_driver.sync_resource[n1kv_const.PORTS])

        # test port MD5 mismatch with missing VSM port
        self.TEST_VSM_PORTS.remove('thisisthesecondtestport')
        self.sync_driver._md5_hash_comparison(None)
        self.assertTrue(self.sync_driver.sync_resource[n1kv_const.PORTS])
        # restore TEST_VSM_NETWORKS to synced state
        self.TEST_VSM_NETWORKS.append('thisisthesecondtestport')

        # test port MD5 mismatch with extra VSM port
        self.TEST_VSM_PORTS.append('thisisanextraportonVSM')
        self.sync_driver._md5_hash_comparison(None)
        self.assertTrue(self.sync_driver.sync_resource[n1kv_const.PORTS])
        self.TEST_VSM_PORTS.remove('thisisanextraportonVSM')
