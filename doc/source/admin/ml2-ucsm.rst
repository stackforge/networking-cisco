==========================================
UCSM Mechanism Driver Administration Guide
==========================================
The configuration parameters for the ML2 UCSM Mechanism Driver can be
specified in a configuration file along with other neutron configuration
parameters. Another approach could be to use TripleO config for Openstack
over Openstack installations.

For a description of functionalities supported by the UCSM Driver
for VLAN and SR-IOV configuration, please refer to
:doc:`/reference/ml2-ucsm`.

.. _ucsm_driver_startup:

UCSM Driver configuration along with neutron parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#. Configuration for Cisco specific ML2 mechanism drivers can be added
   to the file containing neutron specific configuration, by specifying it
   under a driver specific section header. UCSM driver configuration needs
   to be under the section header ``[ml2_cisco_ucsm]``. This neutron
   configuration file is often called ``ml2_conf.ini`` and frequently
   resides in ``/etc/neutron/plugins/ml2``.

  .. note::
     It is also possible to place this configuration into a separate
     file for example ``ml2_conf_cisco.ini`` to keep these
     configurations separate from existing configuration in file
     ``ml2_conf.ini``.

#. This configuration file needs to provided on the command line when the neutron-server
   is started. For example:

   .. code-block:: console

       /usr/local/bin/neutron-server --config-file /etc/neutron/neutron.conf \
           --config-file /etc/neutron/plugins/ml2/ml2_conf.ini  \
           --config-file /etc/neutron/plugins/ml2/ml2_conf_cisco.ini

   .. end

#. In a Openstack setup with a single UCSM, then it may be sufficient to specify
   the UCSM information, in the single-UCSM format which requires the
   following parameters:

   * Management IP address of the UCSM
   * Admin username to login to the UCSM
   * Admin password
   * Hostname to Service Profile Mapping for all the servers that are
     controlled by this UCSM and are part of the Openstack cloud.xi

     .. note::
        The Service Profile (SP) associated with a server can also be a
        Service Profile Template (SPT). If the SP or the SPT are not
        created at the root level on the UCSM, the path to the SP or
        SPT needs to be provided as part of the above configuration.

#. List of ethernet ports or vNICs on the UCS Servers that can be used
   for neutron virtual port configurations. Of all the ethernet ports
   or vNICs available on the UCS Servers, provide only the ones that
   are set aside for neutron virtual port use.

#. List of vNIC Templates that are associated with neutron physical
   networks. This is an optional config and needs to be specified
   only when vNICs spread across multiple UCS Servers are all
   connected to a common physical network and need to be configured
   identiaclly by the UCSM driver.
   configuration via a UCSM vNIC Template. This configuration requires
   the admin to specify the neutron physical networks, the vNIC
   Templates representing all ports that need to be configured for
   that physical network and the path on the UCSM where the vNIC
   Templates are defined.

#. List of supported SR-IOV devices specified as a list of vendor and
   product ids. This is an optional parameter and will default to
   the vendor and product_id pairs for Cisco VICs and Intel NICs.

#. For use cases where a SR-IOV port attached to a Nova VM can
   potentially carry a list of application specific VLANs. For this
   configuration, the UCSM driver expects a a mapping between a
   neutron Network and the list of application specific VLANs that
   can be expected on a SR-IOV port on this neutron Network. This
   is also an optional config.

   .. note::
      The VLAN ids associated with a neutron network should not be
      confused with the VLAN-id range of the neutron network itself.
      SR-IOV ports created on these neutron networks essentially
      act as trunk ports that can carry application specific
      traffic on VLANs specified in this config.

#. In a setup that utilizes multiple UCSMs, UCSM specific configuration
   parameters need to be repeated for each UCSM under a repeatable section
   starting with the UCSM IP specified in this format:
   ``[ml2_cisco_ucsm_ip:<UCSM IP address>]``

Configuring UCSM Driver via TripleO
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

VLAN Configuration
------------------
The Cisco specific implementation is deployed by modifying the tripleo
environment file
`Tripleo Nexus Ucsm Env File <https://github.com/openstack/tripleo-heat-templates/tree/master/environments/neutron-ml2-cisco-nexus-ucsm.yaml>`_
and updating the contents with the deployment specific content. Note that
with TripleO deployment, the server names are not known before deployment
so the MAC address of the server must be used in place of the server name.
Descriptions of the parameters can be found at
`Tripleo Nexus Ucsm Parm file <https://github.com/openstack/tripleo-heat-templates/tree/master/puppet/extraconfig/all_nodes/neutron-ml2-cisco-nexus-ucsm.j2.yaml>`_.

.. code-block:: yaml

        resource_registry:
          OS::TripleO::AllNodesExtraConfig: /usr/share/openstack-tripleo-heat-templates/puppet/extraconfig/all_nodes/neutron-ml2-cisco-nexus-ucsm.yaml
          OS::TripleO::Compute::Net::SoftwareConfig: /home/stack/templates/nic-configs/compute.yaml
          OS::TripleO::Controller::Net::SoftwareConfig: /home/stack/templates/nic-configs/controller.yaml

        parameter_defaults:

          NetworkUCSMIp: '10.86.1.10'
          NetworkUCSMUsername: 'neutron'
          NetworkUCSMPassword: 'cisco123'
          NetworkUCSMHostList: '06:00:C0:06:00:E0:bxb6-C6-compute-2,06:00:C0:05:00:E0:bxb6-C5-compute-1,06:00:C0:03:00:E0:bxb6-C3-control-2,06:00:C0:07:00:E0:bxb6-C7-compute-3,06:00:C0:04:00:E0:bxb6-C4-control-3,06:00:C0:02:00:E0:bxb6-C2-control-1'

          ControllerExtraConfig:
            neutron::plugins::ml2::mechanism_drivers: ['openvswitch', 'cisco_ucsm']

