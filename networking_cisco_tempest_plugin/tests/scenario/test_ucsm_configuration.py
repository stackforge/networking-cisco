# Copyright 2017 Cisco Systems
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

from oslo_config import cfg

from tempest.api.network import base
from tempest import config
from tempest.lib import decorators

from ucsmsdk.ucshandle import UcsHandle

CONF = config.CONF

tempest_ucsm_opts = [
    cfg.StrOpt('service_profile'),
    cfg.StrOpt('ucsm_ip'),
    cfg.StrOpt('ucsm_username'),
    cfg.StrOpt('ucsm_password')
]

CONF.register_opts(tempest_ucsm_opts, 'ucsm')


class TestUCSMConfiguration(base.BaseAdminNetworkTest):

    """This tests UCSM configuration with ml2 driver

    Steps:
    1. Create network
    2. Create subnet
    3. Query UCSM for changes
    4. Check VLAN set on UCSM

    """
    @decorators.attr(type='smoke')
    @decorators.idempotent_id('bdbb5441-9204-419d-a225-b4fdbfb1a1a8')
    def test_ucsm_config_scenario(self):
        # Create a network
        network = self.create_network()
        self.addCleanup(self.networks_client.delete_network, network['id'])
        self.assertEqual('ACTIVE', network['status'])
        # Find a cidr that is not in use yet and create a subnet with it
        self.create_subnet(network)

        admin_network = self.admin_networks_client.show_network(network['id'])
        network_vlan = admin_network['network']['provider:segmentation_id']

        # Connect to UCSM
        handle = UcsHandle(CONF.ucsm.ucsm_ip, CONF.ucsm.ucsm_username,
                CONF.ucsm.ucsm_password)
        handle.login()

        # Check Service profile is on UCSM
        sp = handle.query_dn('org-root/ls-' + CONF.ucsm.service_profile)
        self.assertIsNotNone(sp)

        # Check vlan exists
        vlan = handle.query_dn('fabric/lan/net-OS-' + network_vlan)
        self.assertEqual(network_vlan, getattr(vlan, 'id', None))

        # Check vlan is associated with a vnic on service profile
        vnic_vlan_eth0 = handle.query_dn('org-root/ls-' +
                CONF.ucsm.service_profile + '/ether-eth0/if-OS-' +
                network_vlan)
        self.assertEqual(network_vlan, getattr(vnic_vlan_eth0, 'vnet', None))
        vnic_vlan_eth1 = handle.query_dn('org-root/ls-' +
                CONF.ucsm.service_profile + '/ether-eth1/if-OS-' +
                network_vlan)
        self.assertEqual(network_vlan, getattr(vnic_vlan_eth1, 'vnet', None))
