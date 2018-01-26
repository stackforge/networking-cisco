# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock
import socket
import ssl

from oslo_config import cfg

from neutron.tests import base

from networking_cisco.plugins.ml2.drivers.cisco.ucsm import ucs_ssl
from networking_cisco.plugins.ml2.drivers.cisco.ucsm import ucsm_network_driver

from ucsmsdk import ucsdriver


class TestCiscoUcsmSSL(base.BaseTestCase):

    """Unit tests for SSL overrides."""

    def test_SSLContext_verify_true(self):
        cfg.CONF.ml2_cisco_ucsm.ucsm_https_verify = True
        context = ucs_ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)

    def test_SSLContext_verify_false(self):
        cfg.CONF.ml2_cisco_ucsm.ucsm_https_verify = False
        context = ucs_ssl.SSLContext(ssl.PROTOCOL_SSLv23)
        self.assertEqual(context.verify_mode, ssl.CERT_NONE)

    def test_wrap_socket_verify_true(self):
        cfg.CONF.ml2_cisco_ucsm.ucsm_https_verify = True
        sock = socket.socket()
        context = ucs_ssl.wrap_socket(sock).context
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)

    def test_wrap_socket_verify_false(self):
        cfg.CONF.ml2_cisco_ucsm.ucsm_https_verify = False
        sock = socket.socket()
        context = ucs_ssl.wrap_socket(sock).context
        self.assertEqual(context.verify_mode, ssl.CERT_NONE)

    def test_wrap_socket_verify_false_cert_reqs_true(self):
        cfg.CONF.ml2_cisco_ucsm.ucsm_https_verify = False
        sock = socket.socket()
        context = ucs_ssl.wrap_socket(sock,
                                      cert_reqs=ssl.CERT_REQUIRED).context
        self.assertNotEqual(context.verify_mode, ssl.CERT_REQUIRED)

    def test_wrap_socket_verify_true_cert_reqs_false(self):
        cfg.CONF.ml2_cisco_ucsm.ucsm_https_verify = True
        sock = socket.socket()
        context = ucs_ssl.wrap_socket(sock,
                                      cert_reqs=ssl.CERT_NONE).context
        self.assertNotEqual(context.verify_mode, ssl.CERT_NONE)


class TestUcsmsdkPatch(base.BaseTestCase):

    """Unit tests for Cisco ML2 UCS Manager SSL override for ucsmsdk."""

    # Test monkey patched ssl lib gets loaded
    def test_ucsmsdk_ssl_monkey_patch(self):
        def mocked_create_host_and_sp_dicts_from_config(self):
            return

        mock.patch.object(ucsm_network_driver.CiscoUcsmDriver,
                          '_create_host_and_sp_dicts_from_config',
                          new=mocked_create_host_and_sp_dicts_from_config
                          ).start()

        network_driver = ucsm_network_driver.CiscoUcsmDriver()
        self.assertNotEqual(ucsdriver.ssl, ucs_ssl)

        network_driver._import_ucsmsdk()
        self.assertEqual(ucsdriver.ssl, ucs_ssl)

    def test_ucsmsdk_default_behaviour_of_ssl_cert_checking(self):
        # Test default behaviour of ucsmsdk cert checking
        def mocked_socket_connect(self, host, timeout=None, source=None):
            return socket.socket()

        mock.patch.object(ucsdriver.socket,
                          'create_connection',
                          new=mocked_socket_connect).start()

        # First connection method
        tls_context = ucsdriver.TLSConnection('127.0.0.1', port=7777)
        tls_context.connect()

        self.assertEqual(tls_context.sock.context.verify_mode, ssl.CERT_NONE)

        # Second connection method
        tls1_context = ucsdriver.TLS1Connection('127.0.0.1', port=7777)
        tls1_context.connect()

        self.assertEqual(tls1_context.sock.context.verify_mode, ssl.CERT_NONE)
