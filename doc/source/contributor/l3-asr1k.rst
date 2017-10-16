==================================================
ASR1000 L3 Router Service Plugin Contributor Guide
==================================================

Using Devstack
~~~~~~~~~~~~~~
Devstack is used by developers to install Openstack.  It is not intended for
production use.

To install the ASR1k L3 router service plugin along with OpenStack
using devstack do as follows:

#.  Clone devstack and checkout the branch (ex: Ocata, Newton, etc) you want
    to install.

#.  Configure the ASR1k L3 router service plugin in ``local.conf`` file as
    shown in examples which follow.

#.  Run :command:`./stack.sh`  to install and :command:`./unstack.sh` to
    uninstall.

Devstack configuration examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
This section describes how to configure the ``local.conf`` file with
ASR1k-based L3 routing details for devstack deployment. Configurations for
VLAN-based L2 are also needed to get a working Devstack deployment with the
ASR1k. How to do that for the ML2 Nexus driver is described in
:doc:`../configuration/ml2-nexus`. Alternatively, the L2 could be provided by
Linux bridge or Open vswitch. How to configure the ML2 drivers for those
technologies we refer to the general ML2 devstack documentation (see below).

General devstack install details are found at other documentation links
such as:

* For general devstack information, refer to
  `Devstack <https://docs.openstack.org/devstack/>`_
* For general ML2 devstack details, refer to
  `ML2_devstack <https://wiki.openstack.org/wiki/Neutron/ML2#ML2_Configuration/>`_

To configure ASR1k L3 router service driver in devstack, the first step
required in the ``local.conf`` file is to pull in the networking-cisco
repository.

.. code-block:: ini

    [[local|localrc]]
    enable_plugin networking-cisco https://github.com/openstack/networking-cisco
    enable_service net-cisco

.. end

Devstack also needs to be instructed to enable and configure the L3P, DMP and
CFGA which is done by inserting the following lines in ``local.conf``

.. code-block:: ini

    Q_CISCO_ASR1K_ENABLED=True

    enable_service ciscocfgagent
    enable_service q-ciscorouter
    enable_service q-ciscodevicemanager

    [[post-config|/etc/neutron/neutron.conf]]

    [DEFAULT]
    api_extensions_path = extensions:/opt/stack/networking-cisco/networking_cisco/plugins/cisco/extensions

.. end

Defining credentials, hosting device templates, hosting devices and router types
--------------------------------------------------------------------------------
Devstack can automatically include definitions of credentials, hosting device
templates, hosting devices and router types in configuration files that are
given as arguments to neutron server and the CFGA when they are started.

The actual definitions to be included has to be provided to devstack. This is
done using two text files:

* ``cisco_device_manager_plugin.inject``
* ``cisco_router_plugin.inject``

If these files exist in the devstack root directory when the
:command:`./stack.sh` command is executed, devstack will append their contents
to configuration files that neutron server consumes when it starts.

A cisco_device_manager_plugin.inject sample file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The sample inject file below can be viewed as a raw text
`cisco_device_manager_plugin.inject <../../../devstack/inject_files/cisco_device_manager_plugin.inject>`_
file.

.. literalinclude:: ../../../devstack/inject_files/cisco_device_manager_plugin.inject

A ``cisco_router_plugin.inject`` sample file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The sample inject file below can be viewed as a raw text
`cisco_router_plugin.inject <../../../devstack/inject_files/cisco_router_plugin.inject>`_
file.

.. literalinclude:: ../../../devstack/inject_files/cisco_router_plugin.inject

Source Code Location
~~~~~~~~~~~~~~~~~~~~
Code location for the ML2 Nexus Mechanism Driver are found in the following directory:

``{networking-cisco install directory}/networking_cisco/plugins/cisco``

