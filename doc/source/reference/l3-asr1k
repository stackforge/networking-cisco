==========================================================
ASR1000 L3 Router Service Plugin Overview and Architecture
==========================================================

Introduction
~~~~~~~~~~~~
The ASR1k L3 router service plugin (L3P) represents each Neutron routers as
a virtual routing and forwarding table (VRF) to ensure isolation. Each neutron
router port maps to a VLAN sub-interface in the ASR1k. These sub-interfaces
can either reside on ethernet interfaces or a port-channel interfaces.

The ASR1k L3P assumes that nobody else manipulates the configurations it
makes in the ASR1k routers used in the Openstack neutron deployment.