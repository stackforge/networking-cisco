===================================
Cisco ML2 Nexus Plugin
===================================

1. Introduction
---------------
The Cisco ML2 Nexus Plugin adds and removes trunk vlans
on the Nexus 9K for both ethernet interfaces and port-channel
interfaces.  It also supports configuration of VXLAN Overlay,
Support of Baremetal but limited only VLAN configuration, and
it supports switch configuration replay.

2. VLAN Creation
----------------
When VMs are created or when subnets are created and dhcp is
enabled, port events are received by the nexus driver.
If there are switch credentials defined by the administrator
for the event, then the nexus driver will process the event.

The basic Nexus configuration actions taken by the nexus driver are

* configure the provided VLAN on the Nexus device,
* configure the interface as 'switchport mode trunk' if needed,
* initialize the interface with 'switchport trunk allowed vlan none'
  (only if no trunk vlan have been configured manually by the user),
* and add a trunk vlan onto the specified interface using the interface
  CLI 'switchport trunk allowed vlan add <vlanid>'.

In the case of non-baremetal port events, the Nexus driver uses the
host name from the port event to identify a switch and interface(s)
to configure.  The vlan used to configure the interface also comes
from the port event.  The administrator configures the host to
interface mapping in the ML2 Nexus Driver switch configuration section
of the neutron config file. (ref: ml2_mech_cisco_nexus)

In the case of baremetal port events, the switch and interface mapping
are contained in the event itself.  If there are multiple ethernet
interfaces defined in the event, this implies it is a port-channel.
When the Nexus driver sees multiple interfaces, it next determines
whether the interfaces are already configured as members of a
port-channel. If not, it creates a new port-channel interface and
adds the ethernet interfaces as members.  In more detail, it will

* allocate a port-channel id from vpc-pool configured by administrator,
* create the port-channel which includes 'switchport mode trunk',
  'switchport trunk allowed vlan none',  and vpc-id x,
* apply either more customizable port-channel config provided by
  administrator OR the default config 'spanning-tree port type edge
  trunk' and 'no lacp suspend-individual',
* and apply 'channel-group <vpcid> force mode-active' to the
  ethernet interface.

Regardless whether the port-channel is learned or created, the
trunk vlans are applied to the port-channel and inherited by
ethernet interfaces.  

3. VLAN Removal
---------------

When a VM is removed or a subnet is removed and dhcp is enabled, a delete
port-event is received by the nexus driver.  If port exists in the nexus
driver's port data base, the driver will be removed it as well on the
Nexus 9K device.  

To remove the trunk vlan from interface on the Nexus switch, it
sends 'switchport trunk allowed vlan remove <vlanid>'.  The driver
then checks if the vlan is used on any other interfaces.  If not,
it will remove the vlan from the Nexus switch as well.

4. VXLAN Creation
-----------------

5. VXLAN Removal
-----------------

6. Configuration Replay
-----------------------

