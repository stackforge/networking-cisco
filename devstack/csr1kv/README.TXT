The easy way to do everything in one go:
./csr1kv_install_all.sh <neutron> <n1kv> <full_devstack_dir_path/localrc>

# The first parameter is the name of Openstack network service,
# i.e., it should be 'neutron'.

# The second parameter should be n1kv when Cisco n1kv plugin is used.
# *If* you have the openvswitch plugin patched for trunking support
# then you can set it to ovs.

That's it!


You can run the scripts manually in the following order:
Note that the keystone script must always be run once before
the other scripts can be used.

$ source [path to devstack directory]/openrc admin demo
$ ./setup_keystone_for_csr1kv_l3.sh <neutron>
$ source [path to devstack directory]/openrc quantum L3AdminTenant
$ ./setup_nova_and_glance_for_csrk1v.sh <neutron> <n1kv> <full_devstack_dir_path/localrc>
$ ./setup_neutron_for_csr1kv.sh <neutron> <n1kv> <full_devstack_dir_path/localrc>
$ sudo -E ./setup_l3cfgagent_networking.sh <neutron> <n1kv>
$ source [path to devstack directory]/openrc admin demo
$ ./setup_test_networks.sh <neutron> <n1kv>
$ ./setup_interface_on_extnet1_for_demo.sh <neutron> <n1kv>
