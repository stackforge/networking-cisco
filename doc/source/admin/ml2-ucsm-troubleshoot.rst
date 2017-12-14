Introduction
------------

This section lists some issues that could be encountred during the installation
and operation of the UCS Manager driver. For each of these scenarios, there is
an attempt to identify the probable root cause for that issue and a way to return
to a successful state.

The UCS Manager driver logs important information regarding its operation
in the Neutron server log file. Please refer to this log file to while trying to
troubleshoot your driver installation.


The UCS Manager driver prefixes any configuration it adds to the UCS Manager
with ``OS-``. This driver creates VLAN Profiles, Port-Profiles and updates
Service Profiles (SP) and SP Templates in addition to updating vNIC Templates.
For this to be successful, the UCS Manager driver should be able to connect to the
UCS Manager and push down configuration. Here are some common reasons why
configuration might be missing on the UCS Manager. Please refer to the Neutron
server log file for error messages reported by the UCS Manager driver to root
cause the issue.

Connection to UCS Manager Failed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Description
^^^^^^^^^^^
If you see that the driver is reporting a UCS Manager connection failure with
the following error message, then the SSL Certificate verification on the UCS
Manager has failed and this would prevent the driver from connecting to the
UCS Manager.

Error Message
^^^^^^^^^^^^^
UcsmConnectFailed: Unable to connect to UCS Manager <IP address>. Reason: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed (_ssl.c:590)>.

Corrective Action
^^^^^^^^^^^^^^^^^
If you want the SSL certificate check to proceed, please make sure UCS Manager
has a valid SSL certificate associated with it. Instructions can be found at:

`Cisco UCS Manager Administration Management Guide 3.1 <http://www.cisco.com/c/en/us/td/docs/unified_computing/ucs/ucs-manager/GUI-User-Guides/Admin-Management/3-1/b_Cisco_UCS_Admin_Mgmt_Guide_3_1/b_Cisco_UCS_Admin_Mgmt_Guide_3_1_chapter_0110.html>`_


SSL certificate checking can be disabled by setting the configuration variable
``ucsm_https_verify`` to False. This will be available starting from release x.x

Description
^^^^^^^^^^^
The UCSM driver needs IP address and login credentials for all the UCS Managers
that it needs to configure. Any issues with providing this configuration would
result in connectivity issues to the UCS Manager(s).

Error Message
^^^^^^^^^^^^^
UCS Manager network driver failed to get login credentials for UCSM <IP address>

Corrective Action
^^^^^^^^^^^^^^^^^
Please check if the UCS Manager IP address, username and password are provided
in the configuration file passed to Neutron server process and that they are
accurate. Ping the UCS Manager IP address to check if you have network connectivity.

Configuration missing on the UCS Manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Description
^^^^^^^^^^^
If the connection to the UCS Manager is successful, when a Neutron network is created
with DHCP service enabled, a VLAN Profile should be created on the UCS Manager. This
configuration will program the Fabric Interconnect to send traffic on the VLAN associated
with the Neutron network to the TOR switch.

Issue
^^^^^
VLAN Profile with the id ``OS-<VLAN-id>`` not configured on the UCS Manager.

Corrective Action
^^^^^^^^^^^^^^^^^
Make sure that the Neutron Network created is of type VLAN and Neutron is configured
to use the VLAN type driver. This configuration can be provided as follows:

[ml2]
...
type_drivers = vlan
tenant_network_types = vlan

Description
^^^^^^^^^^^
Once the VLAN profiles are created, vNICs on the UCS Servers acting as Openstack
Controllers would also be updated with VLAN configuration. The vNICs on UCS Servers
acting as compute hosts will be updated with VLAN configuration when VMs are created on
those compute hosts.

Issue
^^^^^
VLAN configuration missing on the vNICs on either the Controller or Compute nodes.

Corrective Action
^^^^^^^^^^^^^^^^^
1. Check if the hostname to SP mapping provided to the UCSM driver via the
``ucsm_host_list`` are accurate.

2. Check if the SP on the UCS Manager is at the root or in a sub directory.
If it is in a subdirectory, please provide the full path in the ``ucsm_host_list``
config.

3. Check if the SP is still attached to a SP Template. In that case, for the
UCSM driver to be able to modify this SP, it should be unbound from the
Template.

4. If the UCSM driver is required to modify the Serviec Profile Template, then the driver
needs to be provided with the ``sp_template_list`` configuration.

5. The next configuration parameter to check would be the ``ucsm_virtio_eth_ports``. This
configuration should contain the list of vNICS on the SP or the SP Template
that is available for the UCSM driver to configure tenant VLANs on.


