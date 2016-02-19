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
#

import mock
import unittest

from networking_cisco.plugins.cisco.cpnr.cpnr_client import CpnrClient


# This method will be used by the mock to replace requests.request
def mocked_requests_request(*args, **kwargs):
    class MockResponse(object):
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code
            self.content = {"key1": "value1"}
            self.links = {'url': 'http://cpnr.com:8080/web-services/rest/'
                    'resource/DHCPServer', 'rel': 'last'}

        def json(self):
            return self.json_data

        def raise_for_status(self):
            return 404

    if args[0] == ('http://cpnr.com:8080/web-services/rest/'
                   'resource/t?vpnId=vpn1234?viewId=view123&'
                   'zoneOrigin=test.com'):
        return MockResponse({"key1": "value1"}, 200)
    else:
        return MockResponse({"key2": "value2"}, 200)

    return MockResponse({}, 404)


class TestCpnrClient(unittest.TestCase):

    def setUp(self):
        super(TestCpnrClient, self).setUp()

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    def test_buildurl(self, url):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                        'admin', 0)
        expected_url = ('http://cpnr.com:8080/web-services/rest/'
                        'resource/t?vpnId=vpn1234?viewId=view123&'
                        'zoneOrigin=test.com')
        return_url = mock_client._build_url('t', 'vpn1234', 'view123',
                        'test.com')
        self.assertEqual(expected_url, return_url)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_get_dhcp_server(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.get_dhcp_server()
        self.assertEqual(return_val, {"key2": "value2"})

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_get_client_classes(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.get_client_classes()
        self.assertEqual(return_val, {"key2": "value2"})

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_get_client_class(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.get_client_class('myclientclass')
        self.assertEqual(return_val, {"key2": "value2"})

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_get_vpns(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.get_vpns()
        self.assertEqual(return_val, {"key2": "value2"})

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_get_scopes(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.get_scopes()
        self.assertEqual(return_val, {"key2": "value2"})

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_get_scope(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.get_scope('myscope')
        self.assertEqual(return_val, {"key2": "value2"})

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_get_client_entries(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.get_client_entries()
        self.assertEqual(return_val, {"key2": "value2"})

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_get_client_entry(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.get_client_entry('myclinetentry')
        self.assertEqual(return_val, {"key2": "value2"})

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_get_leases(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.get_leases('vpn123')
        self.assertEqual(return_val, {"key2": "value2"})

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_get_dns_server(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.get_dns_server()
        self.assertEqual(return_val, {"key2": "value2"})

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_get_dns_forwarders(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.get_dns_forwarders()
        self.assertEqual(return_val, {"key2": "value2"})

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_get_dns_forwarder(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.get_dns_forwarder('myforwarder')
        self.assertEqual(return_val, {"key2": "value2"})

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_get_dns_views(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.get_dns_views()
        self.assertEqual(return_val, {"key2": "value2"})

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_get_dns_view(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.get_dns_view('mydnsview')
        self.assertEqual(return_val, {"key2": "value2"})

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_get_ccm_zones(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.get_ccm_zones()
        self.assertEqual(return_val, {"key2": "value2"})

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_get_ccm_zone(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.get_ccm_zone('myzone')
        self.assertEqual(return_val, {"key2": "value2"})

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_get_ccm_reverse_zones(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.get_ccm_reverse_zones()
        self.assertEqual(return_val, {"key2": "value2"})

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_get_ccm_reverse_zone(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.get_ccm_reverse_zone('myreversezone')
        self.assertEqual(return_val, {"key2": "value2"})

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_get_ccm_hosts(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.get_ccm_hosts()
        self.assertEqual(return_val, {"key2": "value2"})

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_get_ccm_host(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.get_ccm_host('myhost')
        self.assertEqual(return_val, {"key2": "value2"})

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_create_scope(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.create_scope('myscope')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_create_client_class(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.create_client_class('myclientclass')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_create_vpn(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.create_vpn('myclientclass')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_create_client_entry(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.create_client_entry('mycliententry')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_create_dns_forwarder(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                'admin', 0)
        return_val = mock_client.create_dns_forwarder('mydnsforwarder')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_create_dns_view(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.create_dns_view('mydnsview')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_create_ccm_zone(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.create_ccm_zone('myccmzone')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_create_ccm_reverse_zone(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.create_ccm_reverse_zone('myccmreversezone')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_create_ccm_host(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.create_ccm_host('myccmhost')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_update_dhcp_server(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.update_dhcp_server('updatedhcpserver')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_update_client_class(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.update_client_class('updateclientclass',
                                                     'newclientclass')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_update_vpn(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.update_vpn('updatevpn', 'newvpn')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_update_scope(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.update_scope('updatescope', 'newscope')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_update_client_entry(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.update_client_entry('updatecliententry',
                                                     'newcliententry')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_update_dns_server(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.update_dns_server('updatednsserver')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_update_dns_forwarder(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.update_dns_forwarder('updatednsforwarder',
                                                      'newforwarder')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_update_dns_view(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.update_dns_view('updatednsview', 'newdnsview')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_update_ccm_zone(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.update_ccm_zone('updateccmzone', 'newzone',
                                                 None)
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_update_ccm_reverse_zone(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.update_ccm_reverse_zone(
                                        'updateccmreversezone',
                                        'newreversezone',
                                        None)
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_update_ccm_host(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.update_ccm_host('updateccmhost', 'newccmhost',
                                                 None)
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_delete_client_class(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.delete_client_class('deleteclientclass')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_delete_vpn(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.delete_vpn('deletevpn')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_delete_scope(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.delete_scope('deletescope')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_delete_client_entry(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.delete_client_entry('deletecliententry')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_delete_dns_forwarder(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.delete_dns_forwarder('deletednsforwarder')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_delete_dns_view(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.delete_dns_view('deletednsview')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_delete_ccm_zone(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.delete_ccm_zone('deleteccmzone')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_delete_ccm_reverse_zone(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.delete_ccm_reverse_zone('delccmreversezone')
        self.assertEqual(return_val, None)

    @mock.patch('networking_cisco.plugins.cisco.cpnr.cpnr_client.CpnrClient')
    @mock.patch('requests.request', side_effect=mocked_requests_request)
    def test_delete_ccm_host(self, method, val):
        mock_client = CpnrClient('http', 'cpnr.com', '8080', 'admin',
                                 'admin', 0)
        return_val = mock_client.delete_ccm_host('deleteccmhost')
        self.assertEqual(return_val, None)
