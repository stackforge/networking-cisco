================
networking-cisco
================

The networking-cisco project's goal is to provide support for Cisco networking
hardware and software in OpenStack deployments. This includes ML2 drivers and
agents for neutron, as well as other pieces of software which interact with
neutron to best utilise your Cisco products with OpenStack.

* Free software: Apache license
* Documentation: http://docwiki.cisco.com/wiki/OpenStack
* Source: http://git.openstack.org/cgit/openstack/networking-cisco
* Bugs: http://bugs.launchpad.net/networking-cisco

Releases and Version Support
----------------------------

From Mitaka forward, networking-cisco is branchless and releases will be made
from master. We have a goal to maintain compatibility with multiple versions of
OpenStack for as long as possible starting from version 4.0.0 which is
compatible with both Mitaka and Newton OpenStack releases.

* 4.X.X Mitaka, Newton, Ocata onwards
* 3.X.X Mitaka
* 2.X.X Liberty

Supported Equipment and Products
--------------------------------

* Nexus Series Switches
  * ML2 Mechanism driver - cisco_nexus
  * ML2 VXLAN Type driver - nexus_vxlan

* UCS Manager
  * ML2 Mechanism driver - cisco_ucsm

* Cisco Nexus 1000v
  * ML2 Mechanism driver - cisco_n1kv
  * Neutron Service plugins - cisco_n1kv_profile, cisco_n1kv_net_profile

* ASR 1000
  * ...
