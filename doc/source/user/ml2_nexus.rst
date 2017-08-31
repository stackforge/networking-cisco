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
of the neutron config file. (ref: section header ml2_mech_cisco_nexus)

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
port-event is received by the nexus driver.  If the port exists in the
nexus driver's port data base, the driver will be removed the data base
entry as well as remove trunk vlan on the Nexus 9K device.  

To remove the trunk vlan from interface on the Nexus switch, it
sends 'switchport trunk allowed vlan remove <vlanid>'.  The driver
also checks if the vlan is used on any other interfaces.  If not,
it will remove the vlan from the Nexus switch as well by issuing
'no vlan <vlanid>'.

4. VXLAN Overlay Creation
-------------------------
VXLAN Overlay creation does similar basic vlan trunk config as described
in VLAN Creation section.  Prior to doing vlan trunk config, the VLAN
is mapped to a VXLAN Network Identifier (VNI) and applied to
nve (network virtualization edge) interface.  Specifically, the
steps done for the user is as follows:

* Create nve interface, assign an mcast group to a vni which is
  associated to the nve interface.  So the configuration applied is as
  follows:
    int nve1
        member vni <vni-id> mcast-group <mcast-addr>
* Associate the vni to a vlan.  The configuration applied is as follows:
    vlan <vlanid>
      vn-segment <vni-id>

5. VXLAN Overlay Removal
------------------------
VXLAN Overlay removal does similar basic vlan trunk removal as described
in VLAN Destroy section.  Additional it removes the vni member from
the nve interface as well as vlan segment if there are no other ports
referencing it.

6. Configuration Replay
-----------------------
Configuration replay is enabled by default.  The configuration variable
'switch_heartbeat_time' defined under the section header 'ml2_cisco'
affects the replay behavior. The default is 30 seconds which is the
amount of time the nexus driver performs a keep-alive against each
known Nexus switch. If connectivity is lost, it continues to
check for a sign of life.  Once the switch is restored, the nexus
driver will replay all known configuration for this switch. If this
feature is not wanted, the variable should be set to 0.  If neutron
restarts, configuration for all known nexus switches is replayed.

