===========================================
UCSM Mechanism Driver Administration Guide
===========================================
The configuration parameters for the ML2 UCSM Mechanism Driver can be
specified in a configuration file along with other Neutron configuration
parameters. Another approach could be to use TripleO config for Openstack
over Openstack installations.

For a description of functionalities supported by the UCSM Driver
for VLAN and SR-IOV configuration, please refer to
:doc:`/reference/ml2-ucsm`.

.. _ucsm_vlan_startup:

UCSM Driver configuration co-existing with Neutron parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#. Configuration for Cisco specific ML2 mechanism drivers can be added
   to the file containing Neutron specific configuration, by specifying it
   under a driver specific section header. UCSM driver configuration needs
   to be under the section header ``[ml2_cisco_ucsm]``.

#. This Neutron configuration file is often called ``ml2_conf.ini`` and
   frequently resides in ``/etc/neutron/plugins/ml2``.

#. This configuration file needs to provided on the command line when the neutron-server
   is started. For example:

   .. code-block:: console

       /usr/local/bin/neutron-server --config-file /etc/neutron/neutron.conf --config-file /etc/neutron/plugins/ml2/ml2_conf.ini  --config-file /etc/neutron/plugins/ml2/ml2_conf_cisco.ini

   .. end

#. If your setup has a single UCSM, then it may be sufficient to specify
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
   for Neutron virtual port configurations. Of all the ethernet ports
   or vNICs available on the UCS Servers, provide only the ones that
   are set aside for Neutron virtual port use.

#. The Include the configuration file on the command line when the neutron-server
   is started. For example:

   .. code-block:: console

       /usr/local/bin/neutron-server --config-file /etc/neutron/neutron.conf --config-file /etc/neutron/plugins/ml2/ml2_conf.ini  --config-file /etc/neutron/plugins/ml2/ml2_conf_cisco.ini

   .. end


#. List of vNIC Templates that are associated with Neutron physical
   networks. This is an optional config and needs to be specified
   only when all the vNICs spread across multiple UCS Servers are
   all connected to a common physical network and share a common
   configuration via a UCSM vNIC Template. This configuration requires
   the admin to specify the Neutron physical networks, the vNIC
   Template representing all ports that need to be configured for
   that physical network and the list of vNICs that are part of
   that template.

#. List of supported SR-IOV devices specified as a list of vendor and
   product ids. This is an optional parameter and will default to
   the vendor and product_id pairs for Cisco VICs and Intel NICs.

#. For use cases where a SR-IOV port attached to a Nova VM can
   potentially carry a list of application specific VLANs. For this
   configuration, the UCSM driver expects a a mapping between a
   Neutron Network and the list of application specific VLANs that
   can be expected on a SR-IOV port on this Neutron Network. This
   is also an optional config.

   .. note::
      The VLAN ids associated with a Neutron Network should not be
      confused with the VLAN-id range of the Neutron Network itself.
      SR-IOV ports created on these Neutron networks essentially
      act as trunk ports that can carry application specific
      traffic on VLANs specified in this config.

