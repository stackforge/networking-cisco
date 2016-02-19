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
#

from binascii import hexlify
import mock
import socket
import unittest

from networking_cisco.plugins.cisco.cpnr.cpnr_client import UnexpectedError
from networking_cisco.plugins.cisco.cpnr.dns_relay import cfg
from networking_cisco.plugins.cisco.cpnr.dns_relay import DnsPacket
from networking_cisco.plugins.cisco.cpnr.dns_relay import DnsRelayAgent
from networking_cisco.plugins.cisco.cpnr.dns_relay import OPTS


class TestDnsRelayAgent(unittest.TestCase):

    def setUp(self):
        super(TestDnsRelayAgent, self).setUp()

    def test_namespace_monitor(self):
        pass

    def test_server_network_relay(self):
        pass

    def test_client_network_relay(self):
        pass

    @mock.patch('networking_cisco.plugins.cisco.cpnr.dns_relay.netns')
    @mock.patch('socket.socket')
    def test_open_dns_ext_socket(self,
                                 mock_socket,
                                 mock_netns):
        cfg.CONF.register_opts(OPTS, 'cisco_pnr')
        relay = DnsRelayAgent()

        mock_netns.iflist.return_value = []
        mock_netns.iflist.return_value.append(('lo', '127.0.0.1', '255.0.0.0'))

        sock = mock_socket.return_value
        sock.getsockname.return_value = ('127.0.0.1', 123456)

        sock, addr, port = relay._open_dns_ext_socket()

        mock_socket.assert_has_calls([
            mock.call(socket.AF_INET, socket.SOCK_DGRAM),
            mock.call().bind(('127.0.0.1', 0)),
            mock.call().getsockname(),
            mock.call().connect(('127.0.0.1', 53))]
        )

        # check exception thrown if no interfaces
        with self.assertRaises(UnexpectedError):
            mock_netns.iflist.return_value = []
            sock, addr, port = relay._open_dns_ext_socket()

        # check exception thrown if no matching interfaces
        with self.assertRaises(UnexpectedError):
            mock_netns.iflist.return_value = []
            mock_netns.iflist.return_value.append(('eth0', '10.0.0.10',
                                                   '255.255.255.0'))
            sock, addr, port = relay._open_dns_ext_socket()

        # check matching interface found if not first in list
        mock_netns.iflist.return_value = []
        mock_netns.iflist.return_value.append(('eth0', '10.0.0.10',
                                               '255.255.255.0'))
        mock_netns.iflist.return_value.append(('lo', '127.0.0.1', '255.0.0.0'))
        sock, addr, port = relay._open_dns_ext_socket()

    @mock.patch('networking_cisco.plugins.cisco.cpnr.dns_relay.netns')
    @mock.patch('socket.socket')
    def test_open_dns_int_socket(self,
                                 mock_socket,
                                 mock_netns):
        cfg.CONF.register_opts(OPTS, 'cisco_pnr')
        relay = DnsRelayAgent()

        mock_netns.iflist.return_value = []
        mock_netns.iflist.return_value.append(('eth0', '10.21.1.13',
                                               '255.255.255.0'))
        sock, addr, port = relay._open_dns_int_socket()

        self.assertTrue(mock_netns.iflist.called, "Failed to call iflist.")

        mock_socket.assert_has_calls([
            mock.call(socket.AF_INET, socket.SOCK_DGRAM),
            mock.call().setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1),
            mock.call().bind(('10.21.1.13', 53))]
        )

        # check exception thrown if no interfaces
        with self.assertRaises(UnexpectedError):
            mock_netns.iflist.return_value = []
            sock, addr, port = relay._open_dns_int_socket()

    def test_cleanup_stale_requests(self):
        pass

    def test_convert_namespace_to_viewid(self):
        cfg.CONF.register_opts(OPTS, 'cisco_pnr')
        relay = DnsRelayAgent()

        namespace = 'qdhcp-d7c31f74-5d9e-47b7-86f2-64879023c04d'
        viewid = relay._convert_namespace_to_viewid(namespace)
        tmp = 0x64879023c04d & 0x7fffffff
        self.assertEqual(viewid, str(tmp))


class TestDnsPacket(unittest.TestCase):

    def setUp(self):
        super(TestDnsPacket, self).setUp()

    def test_parse(self):
        # test regular DNS request
        fh = open('networking_cisco/tests/unit/'
                  'cisco/cpnr/data/dns_req.txt', 'rt')
        line = fh.read().strip()
        buf = bytearray.fromhex(line)
        pkt = DnsPacket.parse(buf, 28)
        self.assertEqual(pkt.get_msgid(), 0x84a5)
        self.assertEqual(pkt.isreq, True)
        self.assertEqual(pkt.arcnt, 0)
        self.assertEqual(pkt.optlen, 0)
        self.assertEqual(pkt.txt_insert_pos, 28)
        fh.close()

        # test DNS request with EDNS0
        fh = open('networking_cisco/tests/unit/'
                  'cisco/cpnr/data/dns_req_edns0.txt', 'rt')
        line = fh.read().strip()
        buf = bytearray.fromhex(line)
        pkt = DnsPacket.parse(buf, 38)
        self.assertEqual(pkt.get_msgid(), 0x8171)
        self.assertEqual(pkt.isreq, True)
        self.assertEqual(pkt.arcnt, 1)
        self.assertEqual(pkt.optlen, 10)
        self.assertEqual(pkt.txt_insert_pos, 28)
        fh.close()

        # test regular DNS response
        fh = open('networking_cisco/tests/unit/'
                  'cisco/cpnr/data/dns_rsp.txt', 'rt')
        line = fh.read().strip()
        buf = bytearray.fromhex(line)
        pkt = DnsPacket.parse(buf, 44)
        self.assertEqual(pkt.get_msgid(), 0xb65e)
        self.assertEqual(pkt.isreq, False)
        self.assertEqual(pkt.arcnt, 0)
        self.assertEqual(pkt.optlen, 0)
        self.assertEqual(pkt.txt_insert_pos, -1)
        fh.close()

    def test_set_viewid(self):
        pkt = DnsPacket()
        pkt.set_viewid('123456789')
        self.assertEqual(pkt.viewid, '123456789')

    def test_data(self):
        # call with regular DNS request
        fh = open('networking_cisco/tests/unit/cisco/'
                  'cpnr/data/dns_req.txt', 'rt')
        line = fh.read().strip()
        buf = bytearray.fromhex(line)
        pktbuf = bytearray(4096)
        pktbuf[0:len(buf)] = buf
        pkt = DnsPacket.parse(pktbuf, 28)
        pkt.set_viewid('123456')
        mod_buf = pkt.data()
        self.assertEqual(pkt.arcnt, 1)
        hextxtstr = hexlify(DnsPacket.TXT_RR)
        hexstr = hexlify(mod_buf)
        self.assertNotEqual(-1, hexstr.find(hextxtstr))
        fh.close()

        # call with DNS request with EDNS0
        fh = open('networking_cisco/tests/unit/cisco/cpnr'
                  '/data/dns_req_edns0.txt', 'rt')
        line = fh.read().strip()
        buf = bytearray.fromhex(line)
        pktbuf = bytearray(4096)
        pktbuf[0:len(buf)] = buf
        pkt = DnsPacket.parse(pktbuf, 38)
        pkt.set_viewid('123456')
        mod_buf = pkt.data()
        self.assertEqual(pkt.arcnt, 2)
        hexstr = hexlify(mod_buf)
        self.assertNotEqual(-1, hexstr.find(hextxtstr))
        fh.close()

    def test_skip_over_domain_name(self):
        # test skip over name at beginning, end up on ^
        # 4test5cisco3com0^
        bytes = bytearray(b'\x04\x74\x65\x73\x74\x05\x63\x69\x73\x63'
                          b'\x6f\x03\x63\x6f\x6d\x00\x5e')
        pos = DnsPacket.skip_over_domain_name(bytes, 0)
        self.assertEqual(pos, 16)
        self.assertEqual(chr(bytes[pos]), '^')

        # test skip over name in the middle, end up on ^
        # 2552552552554test5cisco3com0^
        bytes = bytearray(b'\xff\xff\xff\xff\x04\x74\x65\x73\x74\x05\x63'
                          b'\x69\x73\x63\x6f\x03\x63\x6f\x6d\x00\x5e')
        pos = DnsPacket.skip_over_domain_name(bytes, 4)
        self.assertEqual(pos, 20)
        self.assertEqual(chr(bytes[pos]), '^')

        # test skip over length and pointer at beginning, end up on ^
        bytes = bytearray(b'\xc0\x55\x5e')
        pos = DnsPacket.skip_over_domain_name(bytes, 0)
        self.assertEqual(pos, 2)
        self.assertEqual(chr(bytes[pos]), '^')

        # test skip over length and pointer in the middle, end up on ^
        bytes = bytearray(b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xc0\x55\x5e')
        pos = DnsPacket.skip_over_domain_name(bytes, 9)
        self.assertEqual(pos, 11)
        self.assertEqual(chr(bytes[pos]), '^')
