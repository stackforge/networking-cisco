===========================================
Nexus Mechanism Driver Administration Guide
===========================================

There are two ways to configure the nexus ML2 Mechanism driver either directly
in the neutron configuration files or via TripleO config for Openstack on
Openstack configurations.

This guide focuses on the neutron start-up files then follows up with
samples of Tripleo configuration files.  You will find similarities
between the neutron start-up files and Tripleo sample configurations
since tripleo config files ultimately cause the generation of neutron
start-up configuration files.  These neutron start-up files are most often
placed beneath the directory ``/etc/neutron/plugins/ml2`` on the controller
node.

For a description of what activites are performed by the Nexus Driver
for VLAN and VXLAN configuration, refer to
:doc:`Nexus MD Overview and Architecture documentation </reference/ml2-nexus>`.

.. _nexus_vlan_startup:

Configuring Neutron directly for Nexus
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
VLAN Configuration
------------------
To configure the Nexus ML2 Mechanism Driver for use with neutron VLAN networks,
do the following:

#. Update the neutron configuration file commonly named ``ml2_conf.ini`` with
   sample configuration described in this document. This file is most
   commonly found in the directory ``/etc/neutron/plugins/ml2``.

   .. note::
      Cisco specific ML2 configuration may be isolated in the file
      ``ml2_conf_cisco.ini`` file while keeping Neutron specific
      configuration parameters in file ``ml2_conf.ini``.

#. Add the Nexus switch information to the configuration file. Multiple switches
   can be configured in this file as well as multiple compute hosts for each
   switch.  This information includes:

   * The IP address of the switch
   * The Nexus switch credential username and password
   * The compute hostname and Nexus port of the node that is connected to the
     switch (For non-baremetal only)
   * vpc ids pool (baremetal only).  It is required when automated port-channel
     creation is desired.
   * intfcfg.port-channel (baremetal only).  This is an optional config
     which allows the user to custom configure port-channel as they are
     getting created.
     The custom config will substitute the default config
     :command:`spanning-tree port type edge trunk;no lacp suspend-individual`.
     See :ref:`nexus_vlan_create` for more details on
     what gets configured during port-channel creation.

   For detail description of the nexus mechanism driver options in the neutron
   configuration files, refer to
   :doc:`Nexus Configuration Reference </configuration/ml2-nexus>`.

#. Include the configuration file on the command line when the neutron-server
   is started. For example:

   .. code-block:: console

       /usr/local/bin/neutron-server --config-file /etc/neutron/neutron.conf --config-file /etc/neutron/plugins/ml2/ml2_conf.ini  --config-file /etc/neutron/plugins/ml2/ml2_conf_cisco.ini

   .. end

Sample configuration with ethernet interfaces
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The sample configuration which follows contains configuration for both
Baremetal and standard configuration as they can co-exist at the same time.
If baremetal is not deployed, then those baremetal configuration variables
identified below can be omitted.  Host to interface mapping configurations can
also be omitted if only baremetal deployments exist. For configuration
activities performed during VLAN creation and removal, refer to
:ref:`nexus_vlan_create` and :ref:`nexus_vlan_remove` sections.

.. code-block:: ini

    [ml2]
    #- This neutron config specifies to use vlan type driver and uses
    #  Cisco nexus mechanism driver.
    type_drivers = vlan
    tenant_network_types = vlan
    mechanism_drivers = openvswitch,cisco_nexus

    #- This neutron config specifies the vlan range to use.
    [ml2_type_vlan]
    network_vlan_ranges = physnet1:1400:3900

    [ml2_cisco]
    #- switch_heartbeat_time is optional since it now defaults to 30 seconds
    #  where previously it defaulted to 0 for disabled.  This causes a
    #  keep-alive event to be sent to each Nexus switch for the amount of
    #  seconds configured. If a failure is detected, the configuration will be
    #  replayed once the switch is restored.
    switch_heartbeat_time = 30

    #- Beneath this section header 'ml2_mech_cisco_nexus:' followed by the IP
    #  address of the Nexus switch are configuration which only applies to
    #  this switch.
    [ml2_mech_cisco_nexus:192.168.1.1]

    #- Provide the Nexus login credentials
    username=admin
    password=mySecretPasswordForNexus

    #- Non-baremetal config only - Hostname and port used on the switch for
    #  this compute host.  Where 1/2 indicates the "interface ethernet 1/2"
    #  port on the switch and compute-1 is the compute host name
    compute-1=1/2

    #- Baremetal config only - Provide pool of vpc ids for use when creating
    #  port-channels.  The following allows for a pool of ids 1001 thru 1025
    #  and also 1030.
    vpc_pool=1001-1025,1030

    #- Baremetal config only - Provide custom port-channel Nexus 9K commands
    #  for use when creating port-channels for baremetal events.
    intfcfg.portchannel=no lacp suspend-individual;spanning-tree port type edge trunk

.. end

Sample configuration with vPC interfaces
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
In addition to supporting ethernet interfaces, multi-homed hosts using
vPC configurations are supported.  To configure this for non-baremetal
case, the administrator must do some pre-configuration on the nexus
switch and the compute host.  These prerequisites are as follows:

#. The vPC must already be configured on the Nexus 9K device as described in
   `Nexus9K NXOS vPC Cfg Guide <https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus9000/sw/7-x/interfaces/configuration/guide/b_Cisco_Nexus_9000_Series_NX-OS_Interfaces_Configuration_Guide_7x/b_Cisco_Nexus_9000_Series_NX-OS_Interfaces_Configuration_Guide_7x_chapter_01000.html>`_.
#. The data interfaces on the compute host must be bonded. This bonded
   interface must be attached to the external bridge.

For baremetal case, Nexus driver will only configure the bonding on the TOR.
The bonding on the baremetal server can be done one of two ways:

#. The network config is passed into the instance using config-drive from
   nova/ironic.  Therefore, if the instance has something like cloud-init
   or glean which can read the config-drive it’ll set up the bond.
#. If the instance image doesn’t have one of those tools then it is down to
   the tenant/owner of the instance to set it up manually.

The only variance from the ethernet configuration shown previously is the host
to interface mapping so this is the only change shown below for non-baremetal
configuration:

.. code-block:: ini

    [ml2_mech_cisco_nexus:192.168.1.1]
    compute-host1=port-channel:2

    [ml2_mech_cisco_nexus:192.168.2.2]
    compute-host1=port-channel:2

.. end

Sample configuration with multiple ethernet interfaces
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
There are some L2 topologies in which traffic from a physical server can come
into multiple interfaces on the ToR switch configured by the Nexus Driver.
In the case of server directly attached to ToR, this is easily taken care of by
port-channel/bonding.  However, if an intermediary device (e.g. Cisco UCS
Fabric Interconnect) is placed between the server and the Top of Rack switch,
then server traffic has the possibility of coming into multiple interfaces on
the same switch.  So the user needs to be able to specify multiple interfaces
per host.

The following shows how to configure multiple interfaces per host.
Since only the host to interface mapping is the only variance to the
ethernet configuration, only the change to host to interface mapping is shown.

.. code-block:: ini

    [ml2_mech_cisco_nexus:192.168.1.1]
    compute-host1=1/11,1/12

.. end

.. _neutron_vxlan_startup:

VXLAN Overlay Configuration
---------------------------

Limitations
^^^^^^^^^^^
VXLAN Overlay Configuration is supported on normal VM configurations and not
baremetal.  Because of this, host to interface mapping in the ML2 Nexus
configuration section is always required.

Prerequisites
^^^^^^^^^^^^^
The Cisco Nexus ML2 driver does not configure the features described in the
“Considerations for the Transport Network” section of
`Nexus9K NXOS VXLAN Cfg Guide <http://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus9000/sw/6-x/vxlan/configuration/guide/b_Cisco_Nexus_9000_Series_NX-OS_VXLAN_Configuration_Guide.pdf>`_.
The administrator must perform such configuration before configuring the
Nexus driver for VXLAN. Do all of the following that are relevant to your
installation:

* Configure a loopback IP address
* Configure IP multicast, PIM, and rendezvous point (RP) in the core
* Configure the default gateway for VXLAN VLANs on external routing devices
* Configure VXLAN related feature commands: :command:`feature nv overlay`
  and :command:`feature vn-segment-vlan-based`
* Configure NVE interface and assign loopback address

Nexus Driver VXLAN Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To support VXLAN configuration on a top-of-rack Nexus switch, add the following
additional Nexus Driver configuration settings:

#. Configure an additional setting named ``physnet`` under the
   ``ml2_mech_cisco_nexus`` section header.
#. Configure the VLAN range in the ``ml2_type_vlan`` section as shown in the
   Sample which follows. The ``ml2_type_vlan`` section header format is
   defined in the ``/etc/neutron/plugins/ml2/ml2_conf.ini``.
#. Configure the network VNI ranges and multicast ranges in the
   ``ml2_type_nexus_vxlan`` section.  These variables are described in
   more detail in :doc:`Nexus Configuration Reference </configuration/ml2-nexus>`.

Sample VXLAN configuration with Ethernet interfaces
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code-block:: ini

        [ml2]
        #- This neutron config specifies to use nexus_vxlan,vlan type driver
        #  and use cisco nexus mechanism driver.
        type_drivers = nexus_vxlan,vlan
        tenant_network_types = nexus_vxlan
        mechanism_drivers = openvswitch,cisco_nexus

        [ml2_type_vlan]
        network_vlan_ranges = physnet1:100:109

        [ml2_mech_cisco_nexus:192.168.1.1]
        # Provide the Nexus log in information
        username=admin
        password=mySecretPasswordForNexus

        # Hostname and port used on the switch for this compute host.
        # Where 1/2 indicates the "interface ethernet 1/2" port on the switch.
        compute-1=1/2

        # Where physnet1 is a physical network name listed in the ML2 VLAN
        # section header [ml2_type_vlan].
        physnet=physnet1

        [ml2_type_nexus_vxlan]
        # Comma-separated list of <vni_min>:<vni_max> tuples enumerating
        # ranges of VXLAN VNI IDs that are available for tenant network allocation.
        vni_ranges=50000:55000

        # Multicast groups for the VXLAN interface. When configured, will
        # enable sending all broadcast traffic to this multicast group.
        # Comma separated list of min:max ranges of multicast IP's
        # NOTE: must be a valid multicast IP, invalid IP's will be discarded
        mcast_ranges=225.1.1.1:225.1.1.2

.. end

.. _nexus_nodhcp_startup:

Additional configuration when the DHCP agent is not running on the Network Node
--------------------------------------------------------------------------------
If a DHCP Agent is not running on the network node then the network node
physical connection to the Nexus switch must be added to all compute hosts
that require access to the network node. As an example, if the network node
is physically connected to Nexus switch 192.168.1.1 port 1/10 then the
following configuration is required.

.. code-block:: ini

        <SKIPPED Other Config defined in VLAN/VXLAN sections>
        [ml2_mech_cisco_nexus:192.168.1.1]
        ComputeHostA=1/8,1/10
        ComputeHostB=1/9,1/10
        username=admin
        password=secretPassword
        ssh_port=22
        physnet=physnet1

        [ml2_mech_cisco_nexus:192.168.1.2]
        ComputeHostC=1/10
        username=admin
        password=secretPassword
        ssh_port=22
        physnet=physnet1

.. end


Configuring Neutron via OpenStack on OpenStack (TripleO) for Nexus
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
In this file, you can see how the parameters below are mapped to neutron
variables.  With these neutron variable names, more details can be
found in :doc:`Nexus Configuration Reference </configuration/ml2-nexus>`.

.. code-block:: yaml

    resource_registry:
      OS::TripleO::AllNodesExtraConfig: /usr/share/openstack-tripleo-heat-templates/puppet/extraconfig/all_nodes/neutron-ml2-cisco-nexus-ucsm.yaml

    parameter_defaults:
      NeutronMechanismDrivers: 'openvswitch,cisco_nexus'
      NetworkNexusConfig: {
        "N9K-9372PX-1": {
            "ip_address": "192.168.1.1",
            "nve_src_intf": 0,
            "password": "mySecretPasswordForNexus",
            "physnet": "datacentre",
            "servers": {
                "54:A2:74:CC:73:51": {
                    "ports": "1/2"
                }
            },
            "ssh_port": 22,
            "username": "admin",
            "vpc_pool": "1001-1025,1030",
            "intfcfg.portchannel": "no lacp suspend-individual;spanning-tree port type edge trunk"
        }
      }
      NetworkNexusManagedPhysicalNetwork: datacentre
      NetworkNexusPersistentSwitchConfig: 'false'
      NetworkNexusNeverCacheSshConnection: 'false'
      NetworkNexusSwitchHeartbeatTime: 30
      NetworkNexusSwitchReplayCount: 3
      NetworkNexusCfgDriver: 'restapi'
      NetworkNexusProviderVlanAutoCreate: 'true'
      NetworkNexusProviderVlanAutoTrunk: 'true'
      NetworkNexusVxlanGlobalConfig: 'false'
      NetworkNexusHostKeyChecks: 'false'
      NeutronNetworkVLANRanges: 'datacentre:2000:2500'
      NetworkNexusVxlanVniRanges: '0:0'
      NetworkNexusVxlanMcastRanges: '0.0.0.0:0.0.0.0'

.. end

VXLAN Configuration
-------------------
The Cisco specific implementation is deployed by modifying the tripleO
environment file `Tripleo Nexus Ucsm Env File <https://github.com/openstack/tripleo-heat-templates/tree/master/environments/neutron-ml2-cisco-nexus-ucsm.yaml>`_
and updating the contents with the deployment specific content. Note that with
TripleO deployment, the server names are not known before deployment. Instead,
the MAC address of the server must be used in place of the server name.
Descriptions of the parameters can be found at `Tripleo Nexus Ucsm Parm file <https://github.com/openstack/tripleo-heat-templates/tree/master/puppet/extraconfig/all_nodes/neutron-ml2-cisco-nexus-ucsm.j2.yaml>`_.
In this file, you can see how the parameters below are mapped to neutron
variables.  With these neutron variable names, more details can be
found in :doc:`Nexus Configuration Reference </configuration/ml2-nexus>`.

.. code-block:: yaml

        resource_registry:
          OS::TripleO::AllNodesExtraConfig: /usr/share/openstack-tripleo-heat-templates/puppet/extraconfig/all_nodes/neutron-ml2-cisco-nexus-ucsm.yaml

        parameter_defaults:
          NeutronMechanismDrivers: 'openvswitch,cisco_nexus'
          NetworkNexusConfig: {
            "N9K-9372PX-1": {
                "ip_address": "192.168.1.1",
                "nve_src_intf": 0,
                "password": "secretPassword",
                "physnet": "datacentre",
                "servers": {
                    "54:A2:74:CC:73:51": {
                        "ports": "1/10"
                    }
                },
                "ssh_port": 22,
                "username": "admin"
            }
           "N9K-9372PX-2": {
                "ip_address": "192.168.1.2",
                "nve_src_intf": 0,
                "password": "secretPassword",
                "physnet": "datacentre",
                "servers": {
                    "54:A2:74:CC:73:AB": {
                        "ports": "1/10"
                    }
                   "54:A2:74:CC:73:CD": {
                        "ports": "1/11"
                    }
                },
                "ssh_port": 22,
                "username": "admin"
            }
          }

          NetworkNexusManagedPhysicalNetwork: datacentre
          NetworkNexusPersistentSwitchConfig: 'false'
          NetworkNexusNeverCacheSshConnection: 'false'
          NetworkNexusSwitchHeartbeatTime: 30
          NetworkNexusSwitchReplayCount: 3
          NetworkNexusCfgDriver: 'restapi'
          NetworkNexusProviderVlanAutoCreate: 'true'
          NetworkNexusProviderVlanAutoTrunk: 'true'
          NetworkNexusVxlanGlobalConfig: 'false'
          NetworkNexusHostKeyChecks: 'false'
          NeutronNetworkVLANRanges: 'datacentre:2000:2500'
          NetworkNexusVxlanVniRanges: '50000:55000'
          NetworkNexusVxlanMcastRanges: '225.1.1.1:225.1.1.2'

.. end

.. note::
    If setting ``NetworkNexusManagedPhysicalNetwork``, the per-port
    ``physnet`` value needs to be the same as
    ``NetworkNexusManagedPhysicalNetwork``.

Additional configuration when the DHCP agent is not running on the Network Node
--------------------------------------------------------------------------------
The following is the Tripleo version of configuring what was described in
the section :ref:`nexus_nodhcp_startup`.

.. code-block:: yaml

        <Skipped other config details defined in VLAN/VXLAN sections>

        parameter_defaults:
          NeutronMechanismDrivers: 'openvswitch,cisco_nexus'
          NetworkNexusConfig: {
            "N9K-9372PX-1": {
                "ip_address": "192.168.1.1",
                "nve_src_intf": 0,
                "password": "secretPassword",
                "physnet": "datacentre",
                "servers": {
                    "54:A2:74:CC:73:51": {
                        "ports": "1/10"
                    }
                },
                "ssh_port": 22,
                "username": "admin"
            }
            "N9K-9372PX-2": {
                "ip_address": "192.168.1.2",
                "nve_src_intf": 0,
                "password": "secretPassword",
                "physnet": "datacentre",
                "servers": {
                    "54:A2:74:CC:73:AB": {
                        "ports": "1/10"
                   }
                   "54:A2:74:CC:73:CD": {
                        "ports": "1/11"
                    }
                },
                "ssh_port": 22,
                "username": "admin"
            }
          }
        <Skipped other config details defined in VLAN/VXLAN sections>

.. end

Configuration Replay applied to the Nexus Switch
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The Nexus mechanism driver performs a keep-alive against each known Nexus
switch every 30 seconds. If communication is lost due to switch reboot
or loss of network connectivity, it continues to check for a sign of life.
Once the switch recovers, the nexus driver will replay all known configuration
for this switch. If neutron restarts, configuration for all known nexus
switches is replayed. The time period to perform keep-alives for each switch
can be altered by the configuration variable ``switch_heartbeat_time``
defined under the section header ``[ml2_cisco]``.  If this feature is not
wanted, the variable should be set to 0 which disables it.  Refer to the
:doc:`Nexus Configuration Reference </configuration/ml2-nexus>` for more
details on this setting.


Troubleshooting
~~~~~~~~~~~~~~~~
Error Handling
--------------
All Nexus Mechanism Driver log messages appear in the same log file as
neutron.  To isolate nexus log messages from other neutron log entries,
just grep on 'nexus'.  The location of Openstack log messages vary according
to each install implementation.

The details in this section identify common problems which can be
encountered, error messages that can be seen for each problem, and
then the actions the user can take to resolve each problem. At times, the
problems can not be resolved by the administrator which requires intervention
by Cisco Tech Support.  If this is the only recourse left, then gather the
following information to provide to Tech Support so they can better
assist you.

* If an installer is being used for deployment, identify what installer is
  being used and provide a copy of its log files.

* Provide compressed Openstack log files::

      tar -xvfz openstack-log-files.tar.gz {Openstack log directory}

* Provide a copy of the current configuration of all participating
  Nexus Switches in your network. This can be done with the Nexus command::

      copy run off-load-nexus-config-for-viewing

* Provide a network diagram with connection details.

.. note::
   The Nexus MD has two different configuration drivers (REST API, ncclient).
   Since the ncclient driver is being deprecated, the documentation in this
   section is written from the perspective of the REST API driver only.

Create Event Failures
^^^^^^^^^^^^^^^^^^^^^
Description:
############
As events for port creation are received, the Nexus MD makes sure at least
one of the switches for each event are active.  If it fails to reach a
switch, Message 1 below will appear.  After checking all switches and
it is determined there are no active switches needed for this event, then the
exception (message 2 below) will appear and the event is rejected.

Message:
########
* Failed to ping switch ip {switch_ip} error {exp_err}
* NexusConnectFailed: <snip> Create Failed: Port event can not be processed at
  this time.

Corrective action:
##################
Refer to `corrective action` section in
`Connection loss with Nexus Switch`_ for steps to narrow down why switch(s)
are not active.

Update/Delete Event Failures
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Description:
############
As Update or Delete configuration events are received, there are a couple
exceptions which can be raised by Nexus MD Driver.  When events are
sent to the configuration driver, they can fail during the authorization
phase (NexusConnectFailed) or during the actual configuration
(NexusConfigFailed).  The following illustrates what appears
for these exceptions:

NexusConnectFailed: Unable to connect to Nexus {switch-ipaddr}.
    Reason: {error returned from underlying restapi or from the nexus switch}
NexusConfigFailed: Failed to configure Nexus switch: {switch-ipaddr}
    Config: restapi path: restapi body
    Reason: {error returned from underlying restapi or from the nexus switch}

Notice the NexusConfigFailed exception has a Config: parameter. This provides
information of what object the driver was trying to configure (restapi path)
and what value(s) the driver was trying to change (restapi body).

The exception is accompanied by a reason parameter which returns the exact
error received by the Nexus MD RESTAPI driver from one of two sources:

* The lower layer restapi code could be returning an error. See the section
  `Connection loss with Nexus Switch`_ for an example of an error
  from the lower layer restapi driver.
* The error comes from the Nexus Switch itself.  See the section
  `Missing Nexus Switch VXLAN Prerequisite Config`_ for an example of
  an error generated by Nexus Switch.

This `Reason` clause provides the details needed to narrow down the error.

Since the Reason clause is the most informative piece to the error message,
it will be reduced to the following for the remainder of `Error Handling`
section.

Message:
########
NexusConfigFailed: <SNIP>, Reason: HTTPConnectionPool(
    host={switch-ipaddr}, port=80): Read timed out. (
    read timeout=30)
NexusConnectFailed: <SNIP>, Reason: Update Port Failed: Nexus Switch is down
    or replay in progress.

Corrective action:
##################
#. Check the section :ref:`connect_loss` for the most likely lower layer
   restapi error.
#. Errors returned by the Nexus switch cannot be documented in this
   section.  You can determine what update failed by analyzing what's in
   the Config: clause of the exception and manually applying the same action
   using the Nexus switch CLI.
#. The NexusConnectFailed error shown in message section is a special case
   where the reason is generated by Nexus MD.  In this case, the Nexus MD
   receives update events from neutron but configuration replay has not fully
   initialized or in process of reconfiguring the switch, or the switch is
   down.  This may be a temporary glitch.  Updates are resent to Nexus MD
   and the switch is configured when the switch becomes active.

.. _connect_loss:

Connection loss with Nexus Switch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Description:
############
The most likely error to encounter is loss of connectivity to the Nexus
switch either due to Nexus switch rebooting or breakage in the network
itself.  One or either of the exceptions shown below can occur during
configuration events.   The first occurs if the driver was performing an
authorization request prior to configuration.  The latter occurs if the
driver was attempting a configuration request.  Either case will fail with a
timeout error as shown in the Message section below.

Messages:
#########
NexusConnectFailed: <SNIP>, Reason: HTTPConnectionPool(
    host={switch-ipaddr}, port=80): Max retries exceeded with url:
    /api/aaaLogin.json (Caused by ConnectTimeoutError(
    'Connection to {switch-ipaddr} timed out.  (connect timeout=60)'))
NexusConfigFailed: <SNIP>, Reason: HTTPConnectionPool(
    host={switch-ipaddr}, port=80): Read timed out. (read timeout=30)

Corrective action:
##################

* Check if the Nexus switch is accessible from the Openstack
  Controller node by issuing a ping to the Nexus Switch ip address.
* If the switch is accessible, check the nexus port binding data base as
  described in section :ref:`db_show` and look for
  RESERVED_NEXUS_SWITCH_DEVICE_ID_R1.  Check the following if the switch is
  shown as INACTIVE.

  #. Check the credentials configured for this switch in the neutron start-up
     configuration file.  Make sure the switch IP address is correct and
     the credential information is correct. See the various configuration
     examples in the section
     :ref:`nexus_vlan_startup` for details.
  #. Check that 'feature nxapi` is configured on the Nexus Switch when the
     Nexus Mechanism driver is configured to use the RESTAPI Config driver.
     For details, see `nexus_driver` configuration parameter in the
     :doc:`Nexus Configuration Reference </configuration/ml2-nexus>`.

* If the switch is not accessible, isolate where in the network a
  failure has occurred.  

  #. Is Nexus Switch management interface down?
  #. Is there a failure in intermediary device between the Openstack
     Controller and Nexus Switch? 
  #. Can the next hop device be reached?

* Check if the switch is running by accessing the console.

Configuration Replay messages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Description:
############
The Nexus MD driver periodically performs a get request to the nexus switch
to make sure the communication path is open.  A log message (See 1 shown below)
is generated the first time the get request fails.  The Nexus MD will
indefinitely continue to send the get request until it is successful
as indicated by log message 2 below.  Once connectivity is established, the
configuration for this Nexus switch is replayed and successful completion of
the reconfiguration is show in the log message 3 below.  For failures during
the replay of the switch configuration, refer to the section
`Replay of Configuration Data Failed`_.

Message:
########
1. Lost connection to switch ip {switch_ip}
2. Re-established connection to switch  ip {switch_ip}
3. Restore of Nexus switch ip {switch_ip} is complete

Corrective action:
##################
1. To monitor the state of the target switch from the perspective of
   the Nexus MD, database commands can be used.  Refer to section
   :ref:`db_show` and look for RESERVED_NEXUS_SWITCH_DEVICE_ID_R1.
2. Fix any failed connectivity issues as described in
   :ref:`connect_loss`.
   
Replay of Configuration Data Failed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Description:
############
The Nexus MD driver has detected the Nexus switch is up and it is attempting
to reconfigure.  Occasionally configurations will fail since the switch is
not fully ready to handle configurations.  The messages below show some
messages which can be seen for this failure.

Message:
########
#. Unexpected exception while replaying entries for switch {switch_ip}
   Reason:
#. Error encountered restoring vlans for switch {switch_ip}
#. Error encountered restoring vxlans for switch {switch_ip}

Corrective action:
##################
This may be a temporary glitch and should recover on next replay retry.
If the problem persists, contact Tech Support for assistance.

Nexus Switch is not getting configured
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Description:
############
The only difference between this case and what is described in the section
`Connection loss with Nexus Switch`_ is the nexus switch has never
been successfully configured after neutron start-up.  Refer to the connection loss section for
more details to triage this case.

Message:
########
There's no specific error message for this other than some show in
`Connection loss with Nexus Switch`_ section.

Corrective action:
##################
It's likely due to connection loss or never having a connection with the
switch.  See the `Connection loss with Nexus Switch`_ for more triage hints
details like how to check the state of the switch and configuration errors
that can occur.

No Nexus switch configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Description:
############
If no Nexus switch configuration is found, the error message below will be
seen in the neutron log file.

Message:
########
No switch bindings in the port data base

Corrective action:
##################
#. Check Sample configurations throughout this guide on configuring switch
   details.  Specifically look for the section header `ml2_mech_cisco_nexus`.
   Also refer to the
   :doc:`Nexus Configuration Reference </configuration/ml2-nexus>`.
#. When neutron is started, make sure the Nexus configuration is in
   the configuration file provided to neutron at start-up.

Missing Nexus Switch VXLAN Prerequisite Config
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Description:
############
An attempt was made to configure `member vni <vni-id> mcast-group <mcast-ip>`
beneath `int nve 1` but an error was returned by the REST API configuration
driver used by the Nexus MD.  Possible reasons are:

1. Nexus switch can't find configured object. See message section below
   for sample detail in reason space of exception.
2. loss of connectivity with switch. See :ref:`connect_loss`.

Message:
########
Failed to configure nve_member for switch {switch_ip}, vni {vni}
    Reason: NexusConfigFailed: <SNIP>, Reason::

        {"imdata":[{ "error": { "attributes": { "code": "102",
        "text": "configured object ((Dn0)) not found
        Dn0=sys\/epId-1\/nws\/vni-70037, "}

Corrective action:
##################
Some general VXLAN configuration must be in place prior to Nexus MD
driver attempting to configure vni and mcast-group configuration.  Refer
to the `Prerequisite` section of :ref:`neutron_vxlan_startup` and the
section :ref:`switch_setup` for more details.

Invalid `nexus-driver` Config Error
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Description:
############
If the `nexus_driver` configuration parameter is mis-configured, it will
prevent neutron from coming-up.  Refer to 
:doc:`Nexus Configuration Reference </configuration/ml2-nexus>`
for details on the `nexus_driver` parameter.

Message:
########
Error loading Nexus Config driver {cfg-chosen}

Corrective action:
##################
The message above reports what was found configured for this parameter
in the message field `cfg-chosen`.  Check it against the valid choices
shown in the configuration guide.

Invalid `vpc-pool` config error
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Description:
############
The `vpc_pool` configuration parameter is a pool created for automatically
creating port-channel ids for baremetal events.  As `vpc-pool` is parsed,
a number of errors can be detected and are reported in the messages below.
For a detail description of configuring `vpc-pool` parameter, refer to
:doc:`Nexus Configuration Reference </configuration/ml2-nexus>`. 

Message:
########
1. Unexpected value {bad-one} configured in vpc-pool config
   {full-config} for switch {switchip}. Ignoring entire config.
2. Incorrectly formatted range {bad-one} config in vpc-pool
   config {full-config} for switch {switchip}. Ignoring entire config.
3. Invalid Port-channel range value {bad-one} received in vpc-pool
   config {full-config} for switch {switchip}. Ignoring entire config.

Corrective action:
##################
In each message, the {bad-one} field is the portion of the {full-config} field
which is failing the parsing.  The {full-config} is what the user configured
for a given {switchip} in the `vpc_pool` configuration parameter.  Possible
issues for each message can be:

1. Values in the range are not numeric. Ex: 2-abc
2. There should only be a min-max value provided. More than two
   values separated by '-' can not be processed. Ex: 3-5-7
3. Values in range must meet valid port-channel range on Nexus
   where smallest is 1 and largest is 4096. ex: 0-5 or 4090-4097

Learned Port-channel Configuration Failures for Baremetal Events
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Description:
############
If a baremetal event is received with multiple ethernet interfaces, the first
in the list indicates how the rest will be treated.  If it is determined the
first interface is preconfigured as a member of a port-channel, the
expectation is the remaining interfaces should also be preconfigured as
members of the same port-channel.  If this is not the case, the exception
below will be raised.

Message:
########
1. NexusVPCLearnedNotConsistent: Learned Nexus channel group
   not consistent on this interface set: first interface
   {first}, second interface {second}.  Check Nexus
   Config and make consistent.
2. NexusVPCExpectedNoChgrp: Channel group state in baremetal
   interface set not consistent: first interface %(first)s,
   second interface %(second)s. Check Nexus Config and make consistent.

Corrective action:
##################
The message fields {first} and {second} each contain the host, interface
and the channel-group learned.  The {first} is the basis interface compared
to and the {second} is the interface that does not match the channel-group
of the {first}.

* Exception 1 is raised when the {first} is a member of a channel group and
  {second} does not match channel group of the {first}.
* Exception 2 is raised when the {first} is not a member of a channel group
  while the {second} is.

Log into each switch identified in {first} and {second} fields and make sure
each interface is a member of the same port-channel if learning is desired.
If automated port-channel creation is preferred, see `Automated Port-channel
Creation Failures for Baremetal Events`_. 

Automated Port-channel Creation Failures for Baremetal Events
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Description:
############
Baremetal events received with multiple ethernet interfaces are treated as
port-channel interfaces.   The first interface in the list indicates
how the rest will be treated.  If all interfaces are currently not members of
a port-channel, then the Nexus MD will try and create a port-channel provided
the Nexus MD configuration parameter `vpc-pool` has been defined for each
switch.  For details on the activity the Nexus MD performs to configure the
port-channel, refer to :ref:`nexus_vlan_create`.

Message:
########
1. NexusVPCAllocFailure: Unable to allocate vpcid for all switches {ip_list}
2. NexusVPCExpectedNoChgrp: Channel group state in baremetal
   interface set not consistent: first interface {first}, 
   {second} interface %(second)s.  Check Nexus Config and make consistent.

Corrective action:
##################
1. The first exception NexusVPCAllocFailure will be raised if the `vpc-pool`
   is not configured or the pool of one of the participating switches has been
   depleted.  The pools can be viewed using port mapping database query
   command as shown in :ref:`db_show`.  For details on configuring 'vpc-pool'
   parameter, refer to
   :doc:`Nexus Configuration Reference </configuration/ml2-nexus>`.
2. Exception 2 is raised when the {first} is not a member of a channel group
   while the {second} is.  Log into each switch identified in {first} and
   {second} fields and make sure each interface is not a member of
   port-channel.  If learning the port-channel is preferred, make sure
   all interfaces are configured as members to the same port-channel.

Invalid Baremetal event
^^^^^^^^^^^^^^^^^^^^^^^
Description:
############
A baremetal event has been received but the Nexus MD was unable to decode
the `switch_info` data in the message since it is not in valid format.
As a result, the event is ignored by Nexus MD driver.

Message:
########
switch_info can't be decoded {reason}

Corrective action:
##################
This error should not occur and suggest looking for earlier errors in
the log file.  If unable to triage further from log messages, contact
Tech Support for assistance.

.. _db_show:

How to view Nexus MD databases
------------------------------
To help triage issues, it may be helpful to peruse the following database
tables:

#. To view the content of the Nexus ML2 port binding database table:

   .. code-block:: console

       mysql -e "use neutron; select * from cisco_ml2_nexusport_bindings;"

   .. end

   In addition to port entries, the switch state is also saved in here.
   These special entries can be identified with an instance_id of
   ``RESERVED_NEXUS_SWITCH_DEVICE_ID_R1``.

   .. code-block:: console

       mysql -e "use neutron; select * from cisco_ml2_nexusport_bindings;"
       | grep RESERVED_NEXUS_SWITCH_DEVICE_ID_R1 | grep <your-switch-ip-address>

   .. end

#. To view the content of the Nexus ML2 port mapping database table:

   .. code-block:: console

       mysql -e "use neutron; select * from cisco_ml2_nexus_host_interface_mapping;"

   .. end

#. To view the content of the Nexus ML2 VPC ID port database table:

   .. code-block:: console

       mysql -e "use neutron; select * from cisco_ml2_nexus_vpc_alloc;"

   .. end

#. To view the content of the Nexus ML2 VNI allocation port database table:

   .. code-block:: console

       mysql -e "use neutron; select * from ml2_nexus_vxlan_allocations;"

   .. end

#. To view the content of the Nexus ML2 Mcast mapping database table:

   .. code-block:: console

       mysql -e "use neutron; select * from ml2_nexus_vxlan_mcast_groups;"
       mysql -e "use neutron; select * from cisco_ml2_nexus_nve;"

   .. end
