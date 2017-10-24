========================================
UCSM Mechanism Driver Installation Guide
========================================

This installation guide details enabling the Cisco Unified Computing
System Manager (UCSM) Mechanism Driver (MD) to configure UCS Servers
and Fabric Interconnects via Openstack.

Prerequisites
~~~~~~~~~~~~~

The prerequisites for installing the ML2 UCSM MD are as follows:

* Cisco UCS B or C series servers connected to a Fabric Interconnect
  running UCS Manager version 2.1 or above. Please refer to
  'UCSM Install and Upgrade Guides <https://www.cisco.com/c/en/us/support/servers-unified-computing/ucs-manager/products-installation-guides-list.html>'_
  for information on UCSM installation.

* UCS servers associated with a Service Profile or Service Profile Template
  on the UCS Manager. The vNICs for Openstack use identified before hand.
  Instructions on how to do this via the UCSM GUI can be found in 'UCS
  Manager Server Management Guide <https://www.cisco.com/c/en/us/td/docs/unified_computing/ucs/ucs-manager/GUI-User-Guides/Server-Mgmt/3-2/b_Cisco_UCS_Manager_Server_Mgmt_Guide_3_2.html>'

* Openstack Neutron installed according to instructions in 'Neutron Install
  Guide <https://docs.openstack.org/neutron/latest/install/>`_

* Openstack running on the OSs:
     * RHEL 6.1 or above OR
     * Ubuntu 14.04 or above


ML2 UCSM MD Installation
~~~~~~~~~~~~~~~~~~~~~~~~

#. Install networking-cisco repository as described in the section
   :doc:`How to install networking-cisco </install/howto>`.
#. Configure UCSM ML2 Driver.
   Once the networking-cisco code is installed, it needs to be configured and
   enabled in Neutron, the :doc:`admin guide </admin/ml2-ucsm>` provides full
   details on how to create the neutron configuration for various use cases.
   For details on each configuration options, refer to
   :doc:`UCSM Configuration Reference</configuration/ml2-ucsm>`.

   Below is a simple VLAN configuration which can be applied to
   ML2 neutron config files ``ml2_conf.ini`` and possibly
   ``ml2_conf_cisco.ini``.
   The file ``ml2_conf_cisco.ini`` is optional if you'd like to isolate
   cisco specific parameters.

   .. code-block:: ini

       [ml2]
       #- This neutron config specifies to use vlan type driver and use
       #  cisco ucsm mechanism driver.
       type_drivers = vlan
       tenant_network_types = vlan
       mechanism_drivers = openvswitch,cisco_ucsm

       #- This neutron config specifies the vlan range to use.
       [ml2_type_vlan]
       network_vlan_ranges = physnet1:1400:3900

       #- Provide UCSM IP and credentials
       #  This format can be used when there is 1 UCSM to be configured.
       [ml2_cisco_ucsm]
       ucsm_ip=10.10.10.10
       ucsm_username=admin
       ucsm_password=mysecretpassword

       ucsm_host_list=controller-1:Controller-SP, compute-1:Compute-SP
       ucsm_virtio_eth_ports=ucs-eth-0, ucs-eth-1

   .. end
#. Restart neutron to pick-up configuration changes.

   .. code-block:: console

       $ service neutron-service restart

   .. end

