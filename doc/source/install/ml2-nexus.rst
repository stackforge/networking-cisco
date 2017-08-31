======================
Cisco ML2 Nexus Plugin
======================

General
~~~~~~~

This is an installation guide for enabling the Cisco ML2 Nexus
Plugin support on OpenStack.

For details on the Cisco Nexus 9K switch, refer to the following link:
https://www.cisco.com/c/en/us/products/switches/nexus-9000-series-switches/index.html
Select the 'Support' option for information on upgrade/downgrade guides,
configuration and technical references.

This guide only covers details on ML2 Nexus plugin install and does not cover OpenStack installation.

Prerequisites
~~~~~~~~~~~~~

The prerequisites for installing the ML2 Nexus plugin is as follows:

    - Cisco NX-OS 7.0(3)I5 (minimum required for REST API Driver)
    - The ML2 Nexus plugin have been tested on these OSs.
        RHEL 6.1 or above
        Ubuntu 14.04 or above
    - Your Nexus switch must be set-up as described in the next section.
    - Requires neutron installation as described `Neutron Pike install <https://docs.openstack.org/neutron/pike/install/>`

Nexus Switch Set-up
~~~~~~~~~~~~~~~~~~~
1. Your Nexus switch must be connected to a management network separate from the OpenStack data network. The plugin communicates with the switch over this network to set up your data flows.
2. The ML2 Nexus Rest API Driver requires 'feature nxapi' to be enabled on the switch.
3. Each compute host on the cloud must be connected to the switch using an interface dedicated solely to OpenStack data traffic.
4. Some pre-configuration must be performed by the Nexus switch administrator.  For instance,
    - All participating interfaces must be enabled with 'no shutdown'.
    - If using port-channels, 
      * peer-link configuration must always be pre-configured.
      * the port-channel configuration must be preconfigured for non-baremetal cases or
        for baremetal cases when administrator prefers to have port-channels learned
        versus automatically creating port-channels using 'vpc-pool' Nexus driver config.
        When port-channels are learned, the interfaces must also be configured as members
        of the port-channel.
    - For VXLAN Overlay Configurations, enable the feature using the following Nexus CLI:
        feature nv overlay
        feature vn-segment-vlan-based
        interface nve1
            no shutdown
            source-interface loopback  x   # where x is same as Nexus driver config 'nve_src_intf'




Ml2 Nexus plugin Installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To get released versions of networking-cisco are avaiable via either
    ``http://tarballs.openstack.org/networking-cisco`` or 
    ``https://pypi.python.org/pypi/networking-cisco``
The neutron release is ``http://tarballs.openstack.org/neutron/``

To install the Nexus ML2 driver, do as follows:

pip install networking-cisco



:4.1 Using devstack:

In this scenario, the ML2 Nexus plugin will be installed along with OpenStack
using devstack.

1. Clone devstack and checkout the branch (ex: Ocata, Newton, etc) you want to install.

2. Add networking-cisco repo as an external repository:

   ::

    > cat local.conf
    [[local|localrc]]
    enable_plugin networking-cisco https://git.openstack.org/openstack/networking-cisco.git
    enable_service net-cisco

3. Configure the ML2 Nexus Plugin (Refer to the admin guide for more details)

4. :command:`./stack.sh`
