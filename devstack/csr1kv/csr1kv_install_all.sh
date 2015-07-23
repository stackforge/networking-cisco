#!/bin/bash

# Runs all install and demo scripts in the right order.

# osn is the name of Openstack network service, i.e.,
# it should be 'neutron'.
osn=${1:-neutron}
plugin=${2:-n1kv}
localrc=$3
mysql_user=$4
mysql_password=$5
mgmt_ip=$6

if [[ ! -z $localrc && -f $localrc ]]; then
    eval $(grep ^Q_CISCO_CREATE_TEST_NETWORKS= $localrc)
fi
CREATE_TEST_NETWORKS=$(trueorfalse "False" $Q_CISCO_CREATE_TEST_NETWORKS)

source ~/devstack/openrc admin demo
echo "***************** Setting up Keystone for CSR1kv *****************"
./setup_keystone_for_csr1kv_l3.sh $osn
source ~/devstack/openrc $osn L3AdminTenant
echo "***************** Setting up Nova & Glance for CSR1kv *****************"
./setup_nova_and_glance_for_csr1kv_l3.sh $osn $plugin $localrc $mysql_user $mysql_password
echo "***************** Setting up Neutron for CSR1kv *****************"
./setup_neutron_for_csr1kv_l3.sh $osn $plugin $localrc
echo "***************** Setting up CfgAgent connectivity *****************"
./setup_l3cfgagent_networking.sh $osn $plugin $mgmt_ip
if [[ "$CREATE_TEST_NETWORKS" == "True" ]]; then
    source ~/devstack/openrc admin demo
    echo "***************** Setting up test networks *****************"
   ./setup_test_networks.sh $osn $plugin
   ./setup_interface_on_extnet1_for_demo.sh $osn $plugin
fi
echo 'Done!...'
