#!/bin/sh

# Many of neutron's repos suffer from the problem of depending on neutron,
# but it not existing on pypi. This ensures its installed into the test environment.

echo "Downloading Ironic Master"
wget -N http://tarballs.openstack.org/neutron/neutron-master.tar.gz -O .neutron-master.tar.gz

echo "Installing Neutron!"
pip install -U .neutron-master.tar.gz

echo "Installing everything else!"
pip install -U $*

exit $?
