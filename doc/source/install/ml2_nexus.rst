===================================
Cisco ML2 Nexus Plugin
===================================

1. General
----------

This is an installation guide for enabling the Cisco ML2 Nexus
Plugin support on OpenStack.

For details on the Cisco Nexus 9K switch, refer to the following link:
https://www.cisco.com/c/en/us/products/switches/nexus-9000-series-switches/index.html
Select the 'Support' option for information on upgrade/downgrade guides,
configuration and technical references.

This guide only covers details on ML2 Nexus plugin install and does not cover OpenStack installation.

2. Prerequisites
----------------

The prerequisites for installing the ML2 Nexus plugin is as follows:

    - Cisco NX-OS 7.0(3)I5 (minimum required for REST API Driver)
    - The ML2 Nexus plugin have been tested on these OSs.
        RHEL 6.1 or above
        Ubuntu 14.04 or above
    - Your Nexus switch must be set-up as described in the next section.

3. Nexus Switch Set-up
----------------------
1. Your Nexus switch must be connected to a management network separate from the OpenStack data network. The plugin communicates with the switch over this network to set up your data flows.
2. The ML2 Nexus Rest API Driver requires 'feature nxapi' to be enabled on the switch.
3. Each compute host on the cloud must be connected to the switch using an interface dedicated solely to OpenStack data traffic.
4. All other switch configuration not listed in the administrator and user guide (for example configuring interfaces with 'no shutdown') must be performed by the Nexus switch administrator.


4. Ml2 Nexus plugin Installation
--------------------------------

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
