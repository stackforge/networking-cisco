=====================================================
ASR1000 L3 Router Service Plugin Administration Guide
=====================================================

The ASR1000 L3 Router Service Plugin (L3P) implements Neutron's L3 routing
service API on the Cisco ASR1000 family of routers.

Specifically it provides the following features:

* L3 forwarding between subnets on tenants' Neutron L2 networks

* Support for for overlapping IP address ranges between different tenants (so
each tenant could use the same RFC-1918 IPv4 address space)

* P-NAT overload for connections originating on private subnets behind a
tenant's Neutron gateway routers connected to external Neutron networks

* Floating IP, i.e., static NAT of a private IP address on a internal Neutron
subnet to a public IP address on an external Neutron subnet/network

* Static routes on Neutron routers

* HSRP-based high availability whereby a Neutron router is supported by two
(or more) ASR1k routers, one actively doing L3 forwarding, the others ready
to take over in case of disruptions

Component overview
~~~~~~~~~~~~~~~~~~
To implement Neutron routers in ASR1000 routers the ASR1k L3P relies on two
additional Cisco components: a device manager plugin (DMP) for Neutron
 server and a configuration agent (CFGA).

The DMP manages a device repository in which ASR1k routers are registered. A
router in the DMP repository is referred to as a *hosting device*. Neutron
server should be configured so that it loads both the DMP and the L3P when it
starts.

The CFGA is a standalone component that needs to be separately started as
Neutron server cannot be configured to take care of that. The CFGA monitors
hosting devices as well as performs configurations in them upon instruction
from the L3P or the DMP. That communication is done using the regular AMQP
message bus that is used by Openstack services.

Limitations
^^^^^^^^^^^
* The Neutron deployment must use VLAN-based network segmentation. That is, the
L2 substrate must be controlled by ML2's VLAN technology driver.

* Access to Nova's Metadata service via Neutron routers is not supported.
The deployment can instead provide access via Neutron's DHCP namespaces (when
IPAM is implemented using Neutron DHCP agents. Alternatively, metadata can
be provided to Nova virtual machines using Nova's config drive feature.

Configuring Neutron directly for ASR1000
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#. Update the neutron configuration file commonly named ``neutron.conf`` so
   that neutron server will load the device manager and L3 service plugins.
   This file is most commonly found in the directory ``/etc/neutron``. The
   ``service_plugins`` configuration option should contain the following two
    items:
    * ``

    .. code-block:: ini
        [DEFAULT]
        service_plugins = networking_cisco.plugins.cisco.service_plugins.cisco_device_manager_plugin.CiscoDeviceManagerPlugin,networking_cisco.plugins.cisco.service_plugins.cisco_router_plugin.CiscoRouterPlugin
    .. end

#. Include the configuration files on the command line when the neutron-server
   is started. For example:

   .. code-block:: console

       /usr/local/bin/neutron-server --config-file /etc/neutron/neutron.conf --config-file /etc/neutron/plugins/ml2/ml2_conf.ini --config-file /etc/neutron/plugins/ml2/ml2_conf_cisco.ini --config-file /etc/neutron/plugins/cisco/cisco_router_plugin.ini --config-file /etc/neutron/plugins/cisco/cisco_device_manager_plugin.ini

   .. end



Sample configuration with ethernet interfaces
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Sample configuration with vPC interfaces
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Configuration Replay onto Nexus Switch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Troubleshooting
~~~~~~~~~~~~~~~
