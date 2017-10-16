==================================================
ASR1000 L3 Router Service Plugin Contributor Guide
==================================================

Using Devstack
~~~~~~~~~~~~~~
Devstack is used by developers to install Openstack.  It is not intended for
production use.

To install the ASR1k L3 router service plugin along with OpenStack
using devstack do as follows:

#. Clone devstack and checkout the branch (ex: Ocata, Newton, etc) you want
   to install.

#. Configure the ASR1k L3 router service plugin in ``local.conf`` file as
shown in examples which follow.

#. Run :command:`./stack.sh`  to install and :command:`./unstack.sh` to
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