===============================================
UCSM Mechanism Driver Overview and Architecture
===============================================

Introduction
~~~~~~~~~~~~
The ML2 UCSM driver translates Neutron ML2 port and network configuration
into configuration for Fabric Interconnects and vNICs on the UCS Servers.
This driver supports configuration of neutron virtual and SR-IOV ports
on VLAN networks. It communicates with the UCSM via the Cisco UCS Python
SDK (version 0.8.2).

.. _ucsm_sriov_support:

SR-IOV port Support
~~~~~~~~~~~~~~~~~~~
The UCSM driver supports binding of SR-IOV ports created on Cisco VICs and
Intel NICs available on UCS Servers. VMs with SR-IOV ports enjoy greater
network performance because these ports bypass the virtual switch on the
compute host's kernel and end packets directly to the Fabric Interconnect.

Before virtual functions (VFs) on compute hosts can be configured by the
UCSM driver to be assigned to a specific VM and a neutron network, please
make sure the pre-requisites listed in the Install guide are met.


