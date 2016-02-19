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

from networking_cisco.plugins.cisco.cpnr.cpnr_client import UnexpectedError
from networking_cisco.plugins.cisco.cpnr.dhcp_relay import cfg
from networking_cisco.plugins.cisco.cpnr.dhcp_relay import DhcpPacket
from networking_cisco.plugins.cisco.cpnr.dhcp_relay import DhcpRelayAgent
from networking_cisco.plugins.cisco.cpnr.dhcp_relay import OPTS
import unittest


class TestDhcpRelayAgent(unittest.TestCase):

    def setUp(self):
        super(TestDhcpRelayAgent, self).setUp()

    def test_namespace_monitor(self):
        pass

    def test_server_network_relay(self):
        pass

    def test_client_network_relay(self):
        pass

    @mock.patch('networking_cisco.plugins.cisco.cpnr.dhcp_relay.netns')
    @mock.patch('socket.socket')
    def test_open_dhcp_ext_socket(self, mock_socket, mock_netns):
        cfg.CONF.register_opts(OPTS, 'cisco_pnr')
        relay = DhcpRelayAgent()
        mock_netns.iflist.return_value = []
        mock_netns.iflist.return_value.append(('lo', '127.0.0.1',
                                               '255.0.0.0'))
        sock, addr = relay._open_dhcp_ext_socket()

        self.assertTrue(mock_netns.iflist.called, "Failed to call iflist.")

        mock_socket.assert_has_calls([
            mock.call(socket.AF_INET, socket.SOCK_DGRAM),
            mock.call().bind(('127.0.0.1', 67)),
            mock.call().connect(('127.0.0.1', 67))]
        )

        # check exception thrown if no interfaces
        with self.assertRaises(UnexpectedError):
            mock_netns.iflist.return_value = []
            sock, addr = relay._open_dhcp_ext_socket()

        # check exception thrown if no matching interfaces
        with self.assertRaises(UnexpectedError):
            mock_netns.iflist.return_value = []
            mock_netns.iflist.return_value.append(('eth1', '10.0.1.3',
                                                   '255.255.255.0'))
            sock, addr = relay._open_dhcp_ext_socket()

        # check matching interface found if not first in list
        mock_netns.iflist.return_value.append(('eth0', '10.0.0.10',
                                               '255.255.255.0'))
        mock_netns.iflist.return_value.append(('lo', '127.0.0.1',
                                               '255.0.0.0'))
        sock, addr = relay._open_dhcp_ext_socket()

    @mock.patch('networking_cisco.plugins.cisco.cpnr.dhcp_relay.netns')
    @mock.patch('socket.socket')
    def test_open_dhcp_int_socket(self, mock_socket, mock_netns):
        cfg.CONF.register_opts(OPTS, 'cisco_pnr')
        relay = DhcpRelayAgent()

        mock_netns.iflist.return_value = []
        mock_netns.iflist.return_value.append(('eth0', '10.1.1.7',
                                               '255.255.255.0'))
        recv_s, send_s, addr = relay._open_dhcp_int_socket()

        self.assertTrue(mock_netns.iflist.called, "Failed to call iflist.")

        mock_socket.assert_has_calls([
            mock.call(socket.AF_INET, socket.SOCK_DGRAM),
            mock.call().setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1),
            mock.call().setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1),
            mock.call().bind(('0.0.0.0', 67)),
            mock.call(socket.AF_INET, socket.SOCK_DGRAM),
            mock.call().setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1),
            mock.call().setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1),
            mock.call().bind(('10.1.1.7', 67))]
        )

        # check exception thrown if no interfaces
        with self.assertRaises(UnexpectedError):
            mock_netns.iflist.return_value = []
            recv_s, send_s, addr = relay._open_dhcp_int_socket()

    def test_convert_ns_to_vpnid(self):
        cfg.CONF.register_opts(OPTS, 'cisco_pnr')
        relay = DhcpRelayAgent()
        namespace = 'qdhcp-a207e329-9476-4746-91a7-fb1cce171a81'
        vpnid = relay._convert_ns_to_vpnid(namespace)
        expected = 'a7fb1cce171a81'
        self.assertEqual(vpnid, expected)


class TestDhcpPacket(unittest.TestCase):

    def setUp(self):
        super(TestDhcpPacket, self).setUp()

    def test_parse(self):
        # DHCP packet contains relay agent option 82
        with open('networking_cisco/tests/unit/cisco/'
                  'cpnr/data/dhcp_packet.txt', 'rt') as dhcp_file:
            lines = [line.strip() for line in dhcp_file]
            data = ''.join(lines)
            buf = bytearray.fromhex(data)
            packet = DhcpPacket.parse(buf)
            # Test client address
            self.assertEqual(packet.get_ciaddr(), '0.0.0.0')
            # Test relay agent options
            expected_relay_options = {152: b'',
                                      11: '10.10.1.2',
                                      5: '10.10.1.2',
                                      151: b'a7fb1cce171a81'}
            actual_packet_options = {code: packet.get_relay_option(code)
                                     for code in [152, 11, 5, 151]}
            self.assertEqual(actual_packet_options, expected_relay_options)

            # Unsuccessful case of undefined relay agent sub-options
            with self.assertRaises(KeyError):
                packet.get_relay_option(220)

    def test_data(self):
        with open('networking_cisco/tests/unit/cisco/'
                  'cpnr/data/dhcp_packet.txt', 'rt') as dhcp_file:
            lines = [line.strip() for line in dhcp_file]
            data = ''.join(lines)
            buf = bytearray.fromhex(data)
            pktbuf = bytearray(4096)
            pktbuf[0:len(buf)] = buf
            packet = DhcpPacket.parse(pktbuf)
            hex_data = hexlify(packet.data())
            self.assertNotEqual(-1, hex_data.find(hexlify(packet.ciaddr)))
            self.assertNotEqual(-1, hex_data.find(hexlify(packet.giaddr)))

            expected_relay_options = {152: b'',
                                      11: '10.10.1.2',
                                      5: '10.10.1.2',
                                      151: b'a7fb1cce171a81'}
            # Find relay agent sub-options in data
            self.assertNotEqual(-1, hex_data.find(
                self.get_relay_opt_hex(expected_relay_options[11])))
            self.assertNotEqual(-1, hex_data.find(
                self.get_relay_opt_hex(expected_relay_options[5])))
            self.assertNotEqual(-1, hex_data.find(
                b"01" + expected_relay_options[151]))
            self.assertNotEqual(-1, hex_data.find(
                expected_relay_options[152]))

    def get_relay_opt_hex(self, value):
        return hexlify(socket.inet_aton(value))
