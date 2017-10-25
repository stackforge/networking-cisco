#!/usr/bin/env bash

# Many of neutron's repos suffer from the problem of depending on neutron,
# but it not existing on pypi. This ensures its installed into the test environment.
set -ex

ZUUL_CLONER=/usr/zuul-env/bin/zuul-cloner
NEUTRON_BRANCH=${NEUTRON_BRANCH:-${DEFAULT_NEUTRON_BRANCH:-master}}
NEUTRONCLIENT_BRANCH=${NEUTRONCLIENT_BRANCH:-${DEFAULT_NEUTRONCLIENT_BRANCH:-master}}
UPPER_CONSTRAINTS_FILE=${UPPER_CONSTRAINTS_FILE:-unconstrained}

install_cmd="pip install -U"

if [ "$UPPER_CONSTRAINTS_FILE" != "unconstrained" ]; then
    if [ -d "/home/zuul/src/git.openstack.org/openstack/requirements" ]; then
        (cd /home/zuul/src/git.openstack.org/openstack/requirements && \
         git checkout $NEUTRON_BRANCH)
        UPPER_CONSTRAINTS_FILE=/home/zuul/src/git.openstack.org/openstack/requirements/upper-constraints.txt
    fi
    install_cmd="$install_cmd -c$UPPER_CONSTRAINTS_FILE"
fi

if [ -d "/home/zuul/src/git.openstack.org/openstack/python-neutronclient" ]; then
    (cd /home/zuul/src/git.openstack.org/openstack/python-neutronclient && \
     git checkout $NEUTRONCLIENT_BRANCH && \
     pip install -e .)
fi

if $(python -c "import neutronclient" 2> /dev/null); then
    echo "Neutronclient already installed."
else
    # Install neutron client from git.openstack.org
    # Dont use upper contraints here because python-neutronclient is in upperconstraints
    pip install -e git+https://git.openstack.org/openstack/python-neutronclient@$NEUTRONCLIENT_BRANCH#egg=python-neutronclient
fi

if [ -d "/home/zuul/src/git.openstack.org/openstack/neutron" ]; then
    (cd /home/zuul/src/git.openstack.org/openstack/neutron && \
     git checkout $NEUTRON_BRANCH && \
     $install_cmd -e .)
fi

if $(python -c "import neutron" 2> /dev/null); then
    echo "Neutron already installed."
else
    # Install neutron from git.openstack.org
    $install_cmd -e git+https://git.openstack.org/openstack/neutron@$NEUTRON_BRANCH#egg=neutron
fi

# Install the rest of the requirements as normal
$install_cmd -U $*

exit $?
