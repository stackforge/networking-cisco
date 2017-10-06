If you would like to contribute to the development of networking-cisco,
you must follow the steps as outlined by the Openstack page:

   http://docs.openstack.org/infra/manual/developers.html

Once those steps have been completed, changes to networking-cisco
should be submitted for review via the Gerrit tool, following
the workflow documented at:

   http://docs.openstack.org/infra/manual/developers.html#development-workflow

Pull requests submitted through GitHub will be ignored.

Bugs should be filed on Launchpad, not GitHub:

   https://bugs.launchpad.net/networking-cisco

Tox environments provided in networking-cisco:

* py27, py34 - Unit tests run against Mitaka neutron, on different python2.7 and python3.4
* newton - Unit tests run against Newton neutron with python2.7
* master - Unit tests run against master neutron with python2.7
* coverage - provides a report on the test coverage
* compare-coverage - compares coverage reports from before and after the current changes
* pep8 - Checks code against the pep8 and OpenStack hacking rules
* genconfig - Generate sample configuration files included in the documentation
* docs - Generates documentation for viewing (hint: Run `genconfig` first)

Devstack is used by developers to install Openstack and not intended
for production use.  To get details on using devstack, refer to other
documentation links such as:

* For general devstack information, refer to
  `Devstack <https://docs.openstack.org/devstack/>`_
* For general ML2 devstack details, refer to
  `ML2_devstack <https://wiki.openstack.org/wiki/Neutron/ML2#ML2_Configuration/>`_

As discussed in these links, ``local.conf`` is devstack's configuration file
for defining Openstack installations.  To include installing the
networking-cisco repository, add the following configuration.  For further
Cisco feature configuration details using Devstack, look for other
plugin/driver subsections in the Cisco contributor guide for sample devstack
configurations.

.. code-block:: ini

    [[local|localrc]]
    enable_plugin networking-cisco https://github.com/openstack/networking-cisco

.. end
