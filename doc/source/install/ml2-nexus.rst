=========================================
Nexus Mechanism Driver Installation Guide
=========================================

This is an installation guide for enabling the Nexus Mechanism Driver (MD)
support on OpenStack.  This guide only covers details on the Nexus MD install
and does not cover OpenStack or Nexus 9K switch installation.
The `Prerequisites`_ section contains links for this.

Prerequisites
~~~~~~~~~~~~~

The prerequisites for installing the ML2 Nexus MD are as follows:

* Cisco Nexus 9K image version - NX-OS 7.0(3)I5 (minimum required for REST API
  Driver). Refer to `Nexus 9K docs <https://www.cisco.com/c/en/us/products/switches/nexus-9000-series-switches/index.html>`_
  for upgrade/downgrade instructions.  From this link, select the 'Support'
  option in the middle of the page for information on upgrade/downgrade
  guides, configuration and technical references.
* The ML2 Nexus MD have been tested on these OSs.

    * RHEL 6.1 or above
    * Ubuntu 14.04 or above

* Your Nexus switch must be set-up as described in the next section
  `Nexus Switch Setup`_.
* Requires neutron installation as described `Neutron Pike install <https://docs.openstack.org/neutron/pike/install/>`_
* If the administrator has chosen to override the default RESTAPI driver
  which configures the Nexus device, the ncclient driver will be used
  instead which requires the following to be installed:

    * ``Paramiko`` library, the SSHv2 protocol library for python
    * The ``ncclient`` (minimum version v0.4.2) python library for NETCONF
      clients.  Install the ncclient library by using the pip package
      manager at your shell prompt:
      :command:`pip install ncclient == 0.4.2`

Nexus Switch Setup
~~~~~~~~~~~~~~~~~~~

This section lists what is required to prepare the Nexus switch for operation
with the Nexus Driver.

#. Your Nexus switch must be connected to a management network separate from
   the OpenStack data network. The Nexus MD *must* be able to access this
   network so it can communicate with the switch to set up your data flows.
#. The ML2 Nexus Rest API Driver requires :command:`feature nxapi` to be
   enabled on the switch.
#. Each compute host on the cloud must be connected to the switch using an
   interface dedicated solely to OpenStack data traffic.
#. Some pre-configuration must be performed by the Nexus switch administrator.
   For instance:
   * All participating compute host interfaces must be enabled with :command:`no shutdown`.

   * Possible port-channels pre-configuration:

     * Peer-link configuration must always be pre-configured.
     * The port-channel configuration must be preconfigured for all
       non-baremetal cases. For baremetal cases, when administrator prefers
       to have port-channels learned versus automatically creating
       port-channels using ``vpc-pool`` Nexus driver config.
     * When port-channels are learned, the interfaces must also be configured
       as members of the port-channel.

   * For VXLAN Overlay Configurations, enable the feature using the following
     Nexus CLI:

     .. code-block:: ini

           feature nv overlay
           feature vn-segment-vlan-based
           interface nve1
               no shutdown
               source-interface loopback x
               # where x is same value as Nexus driver config 'nve_src_intf'
     .. end


ML2 Nexus MD Installation
~~~~~~~~~~~~~~~~~~~~~~~~~

#. Released versions of networking-cisco are available via either:

   .. code-block:: ini

       http://tarballs.openstack.org/networking-cisco
       https://pypi.python.org/pypi/networking-cisco
   .. end

   The neutron release is http://tarballs.openstack.org/neutron

#. To install the Nexus ML2 driver, do as follows:

     * When using pip for installs, do either:

       .. code-block:: ini

           pip install networking-cisco
           pip install <path to downloaded networking-cisco tarball>
       .. end

     * To install the Nexus ML2 mechanism driver without pip, do:

       .. code-block:: ini

           tar -zxfv <downloaded networking-cisco tarball>
           cd ./networking-cisco-<version>
           python setup.py install
       .. end

       If installing without pip, you should ensure that the python
       dependencies are all installed. They can be found in
       ``requirements.txt`` in the untarred directory.

    * To install the Nexus ML2 mechanism driver from system packages, do:

      .. code-block:: ini

          yum install python-networking-cisco
      .. end

#. Recent additions to Nexus ML2 data requires a data base migration to be
   performed.  This can be done by running:

   :command:`su -s /bin/sh -c "neutron-db-manage --config-file /etc/neutron/neutron.conf --config-file /etc/neutron/plugins/ml2/ml2_conf.ini --config-file /etc/neutron/plugins/ml2/ml2_conf_cisco.ini upgrade head" neutron`

#. Configure Nexus ML2 Driver.
   Once the networking-cisco code is installed, it needs to be configured and
   enabled in Neutron, the :doc:`admin doc </admin/ml2-nexus>` provides full
   details on how to create the neutron configs for various use cases.  For
   details on each configuration parameters, refer to
   :doc:`Nexus Configuration doc </configuration/ml2-nexus>`.

   Below is a simple VLAN configuration which can be applied to
   ML2 neutron config files ``ml2_conf.ini`` and possibly
   ``ml2_conf_cisco.ini`` located in directory ``/etc/neutron/plugins/ml2``.
   The file ``ml2_conf_cisco.ini`` is optional if you'd like to isolate
   cisco specific parameters.

   .. code-block:: ini

       [ml2]
       #- This neutron config specifies to use vlan type driver and use
       #  cisco nexus mechanism driver.
       type_drivers = vlan
       tenant_network_types = vlan
       mechanism_drivers = openvswitch,cisco_nexus

       #- This neutron config specifies the vlan range to use.
       [ml2_type_vlan]
       network_vlan_ranges = physnet1:1400:3900

       #- Provide Nexus credentials, compute host, and nexus interface
       [ml2_mech_cisco_nexus:192.168.1.1]
       username=admin
       password=mySecretPasswordForNexus
       compute-1=1/2
   .. end
#. Restart neutron to pick-up configuration changes.

   .. code-block:: ini

       service neutron-service restart

   .. end

