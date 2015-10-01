#!/bin/sh

# Many of neutron's repos suffer from the problem of depending on neutron,
# but it not existing on pypi. This ensures its installed into the test environment.
set -ex

ZUUL_CLONER=/usr/zuul-env/bin/zuul-cloner

zuul_install () {
  # Use zuul-cloner to clone openstack/neutron, this will ensure the Depends-On
  # references are retreived from zuul and rebased into the repo, then installed.
  $ZUUL_CLONER --cache-dir /opt/git --workspace /tmp git://git.openstack.org openstack/neutron
  pip install /tmp/openstack/neutron
}

local_install () {
  # Download or update neutron-master tarball and install
  wget -N http://tarballs.openstack.org/neutron/neutron-master.tar.gz -O .neutron-master.tar.gz
  pip install .neutron-master.tar.gz
}

# Install neutron if not already installed, attempt to use the zuul cloner, and
# fall back to using the local install method if that fails.
python -c "import neutron" 2> /dev/null || zuul_install || local_install

# Install the rest of the requirements as normal
pip install -U $*

exit $?
