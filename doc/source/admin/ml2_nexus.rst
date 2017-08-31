===================================
Cisco ML2 Nexus Plugin
===================================

1. General
----------
The Cisco ML2 Nexus Plugin is responsible for configuring the Nexus 9K.  

This guide describes a number of configuration files from which to
configure the ML2 Nexus driver.  It depends on which
install method chosen whether it is devstack or by way of Tripleo.
Either method results in changes to file(s) beneath the directory
/etc/neutron/plugins/ml2.  These files contain the configuration which
are ultimately passed into neutron when it is started. This guide
contains a description of the configuration needed in devstack, tripleo, and neutron configuration files.

2. Nexus Files Of Interest
--------------------------
networking-cisco repository location is:
https://github.com/openstack/networking-cisco

This next file is very important as it describes in detail each configuration
variable available to the ML2 Nexus Mechanism Driver.  Throughout this
document, it show sample configuration using variables defined in this file.
{networking-cisco location}/etc/neutron/plugins/ml2/ml2_conf_cisco.ini

Code location for the ML2 Nexus Mechanism Driver:
{networking-cisco location}/networking_cisco/plugins/ml2/drivers/cisco/nexus

Location of installed neutron configuration files after running devstack or exercising
tripleo config files is as follows:
/etc/neutron/plugins/ml2

3. VLAN Configurations
----------------------
3.1 VLAN Configuration in neutron config files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To configure a file for use during neutron start-up, do the following:

1. Create a configuration file using the syntax template networking_cisco/etc/neutron/plugins/ml2/ml2_conf_cisco.ini
   from networking-cisco repository.  This file contains a detail description of variables defined in sample
   config as well as other less used variables.
2. Add the Nexus switch information to a configuration file. Include the following information (see the examples below):

   * The IP address of the switch
   * The Nexus switch credential username and password
   * The hostname and port of the node that is connected to the switch (non-baremetal only)
   * vpc ids pool is for baremetal only.  It is an required when automated port-channel creation is
     desired.
   * intfcfg.port-channel is for baremetal only.  This is an optional config which allows the user
     to custom configure port-channel as they are getting created.  The custom config will substitute
     the default config 'spanning-tree port type edge trunk;no lacp suspend-individual'.
     See the user guide for more details on port-channel creation.
3. Include the configuration file on the command line when the neutron-server is started. You can configure multiple switches as well as multiple hosts per switch.

Sample neutron start-up configuration with ethernet interfaces:
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
The sample configuration which follows contains configuration for both Baremetal
and standard configuration as they can co-exist at the same time.  If baremetal is not
deployed, then those baremetal configuration variables identified below can
be omitted.  Host to interface mapping configurations can also be omitted if
only baremetal deployments exist. See the user guide for details on
VLAN creation and removal.

 ::

    [ml2]
    #- This neutron config specifies to use vlan type driver and use
    #  cisco nexus mechanism driver.
    tenant_network_types = vlan
    mechanism_drivers = openvswitch,cisco_nexus
     
    #- This neutron config specifies the vlan range to use.
    [ml2_type_vlan]
    network_vlan_ranges = physnet1:1400:3900
     
    [ml2_cisco]
    #- switch_heartbeat_time is optional since it now defaults to 30 seconds where
    #  previously it defaulted to 0 for disabled.  This causes a keep-alive event to be
    #  sent to each Nexus switch for the amount of seconds configured. If a failure
    #  is detected, the configuration will be replayed once the switch is restored.
    switch_heartbeat_time = 30
     
    #- Use section header 'ml2_mech_cisco_nexus:' followed by the IP address of the Nexus switch.
    [ml2_mech_cisco_nexus:192.168.1.1]

    #- Provide the Nexus login information
    username=admin
    password=mySecretPasswordForNexus

    #- Non-baremetal config only - Hostname and port used on the switch for this compute host.
    #  Where 1/2 indicates the "interface ethernet 1/2" port on the switch and compute-1 is
    #  the host name
    compute-1=1/2

    #- Baremetal config only - Provide range of vpc ids for use when creating port-channels.
    #  The following allows for a pool of ids 1001 thru 1025 and also 1030.
    vpc_pool=1001-1025,1030

    #- Baremetal config only - Provide custom port-channel Nexus 9K commands for use when
    #  creating port-channels for baremetal events.
    intfcfg.portchannel=no lacp suspend-individual;spanning-tree port type edge trunk

Sample neutron start-up configuration with vPC interfaces:
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
In addition to supporting ethernet interfaces, multi-homed hosts using vPC configurations
are supported.  To configure this for non-baremetal case, the administrator must do some
pre-configuration on the nexus switch and the compute host.  These prerequisites are as
follows:

* The vPC must already be configured on the Nexus 9K device as described in `Nexus9K_NXOS_vPC_Cfg_Guide <https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus9000/sw/7-x/interfaces/configuration/guide/b_Cisco_Nexus_9000_Series_NX-OS_Interfaces_Configuration_Guide_7x/b_Cisco_Nexus_9000_Series_NX-OS_Interfaces_Configuration_Guide_7x_chapter_01000.html>`_
* The data interfaces on the compute host must be bonded. This bonded interface must be attached to the external bridge.

The only variance from the ethernet configuration shown previously is the host to
interface mapping so this is the only change shown below:
::

    [ml2_mech_cisco_nexus:192.168.1.1]
    compute-host1=port-channel:2

    [ml2_mech_cisco_nexus:192.168.2.2]
    compute-host1=port-channel:2

Sample neutron start-up configuration with multiple ethernet interfaces:
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
There are some L2 topologies in which traffic from a physical server can come into
multiple interfaces on the ToR switch configured by the Nexus plugin.  In the
case of server directly attached to ToR, this is easily taken care of by 
port-channel/bonding.  However, if an intermediary device (e.g. Cisco UCS Fabric
Interconnect) is placed between the server and the Top of Rack switch, then
server traffic has the possibility of coming into multiple interfaces on the same
switch.  So the user needs to be able to specify multiple interfaces per host.
The following shows how to configure multiple interfaces per host.  Again since
only the host to interface mapping is the only variance to the ethernet
configuration, only the show to interface mapping is shown.

::

    [ml2_mech_cisco_nexus:192.168.1.1]
    compute-host1=1/11,1/12

3.2 VLAN Configuration in Tripleo
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The Cisco specific implementation is deployed by modifying the tripleO environment file 'Tripleo_nexus_ucsm_Env_File <https://github.com/openstack/tripleo-heat-templates/tree/master/environments/neutron-ml2-cisco-nexus-ucsm.yaml>`_ and updating the contents with the deployment specific content. Note that with TripleO deployment the server names are not known before deployment, so the MAC address of the server must be used in place of the server name.
Descriptions of the parameters can be found at `Tripleo_Nexus_Ucsm_Parm_file <https://github.com/openstack/tripleo-heat-templates/tree/master/puppet/extraconfig/all_nodes/neutron-ml2-cisco-nexus-ucsm.j2.yaml>`_
In this file, you can see how the parameter below are mapped to neutron variables.  With these neutron variable names, even more details can be
found in the 'configuration template' file in the networking-cisco repo.  See 'File of Interest' section for location of this file.

Sample Config:
::

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


3.3 VLAN Configuration in DevStack
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This section covers how to configure devstack local.conf file with Nexus VLAN details using devstack.  It does not reiterate devstack install details which can be found at other documentation sites such as:

* For general devstack information, refer to `Devstack <https://docs.openstack.org/devstack/>`_
* For general ML2 devstack details, refer to `ML2_devstack <https://wiki.openstack.org/wiki/Neutron/ML2#ML2_Configuration/>`_

To configure ML2 Nexus plugin in devstack, the first step required in the local.conf file is to pull in the networking-cisco repository.  The following will cause the nexus code base to get installed.  

::

    [[local|localrc]]
    enable_plugin networking-cisco https://github.com/openstack/networking-cisco
    enable_service net-cisco

The following sample configuration will provide you with Nexus VLAN Configuration.  As with
neutron configuration shown earlier, this configuration supports both standard (legacy)
as well as Baremetal.  As you can see there is a lot of similarity between
the two so details in the neutron config file section apply here.  

 Sample Config:
 ::

    [[local|localrc]]
    enable_plugin networking-cisco https://github.com/openstack/networking-cisco
    enable_service net-cisco

    # Set openstack passwords here.  For example, ADMIN_PASSWORD=ItsASecret

    # disable_service/enable_service here. For example,
    # disable_service tempest
    # enable_service q-svc

    # bring in latest code from repo.  (RECLONE=yes; OFFLINE=False)

    Q_PLUGIN=ml2
    Q_ML2_PLUGIN_MECHANISM_DRIVERS=openvswitch,cisco_nexus
    Q_ML2_TENANT_NETWORK_TYPE=vlan
    ML2_VLAN_RANGES=physnet1:100:109
    ENABLE_TENANT_TUNNELS=False
    ENABLE_TENANT_VLANS=True
    PHYSICAL_NETWORK=physnet1
    OVS_PHYSICAL_BRIDGE=br-eth1

    [[post-config|/etc/neutron/plugins/ml2/ml2_conf.ini]]
    [ml2_cisco]
    switch_heartbeat_time = 30

    [ml2_mech_cisco_nexus:192.168.1.1]
    ComputeHostA=1/10
    username=admin
    password=mySecretPasswordForNexus
    vpc_pool=1001-1025,1030
    intfcfg.portchannel=no lacp suspend-individual;spanning-tree port type edge trunk

    [ml2_mech_cisco_nexus:192.168.2.2]
    ComputeHostB=1/10
    username=admin
    password=mySecretPasswordForNexus
    vpc_pool=1001-1025,1030
    intfcfg.portchannel=no lacp suspend-individual;spanning-tree port type edge trunk

4. VXLAN Overlay Configurations
-------------------------------

VXLAN Overlay Configuration is supported on legacy configurations but not baremetal.  Because of this, host to interace mapping is required.

4.1 Prerequisites:
^^^^^^^^^^^^^^^^^^
The Cisco Nexus ML2 driver does not configure the features described in the “Considerations for the Transport Network” section of `Nexus9K_NXOS_VXLAN_Cfg_Guide <http://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus9000/sw/6-x/vxlan/configuration/guide/b_Cisco_Nexus_9000_Series_NX-OS_VXLAN_Configuration_Guide.pdf>`_. The administrator must perform such configuration before configuring the plugin for VXLAN. Do all of the following that are relevant to your installation:

* Configure a loopback IP address
* Configure IP multicast, PIM, and rendezvous point (RP) in the core
* Configure the default gateway for VXLAN VLANs on external routing devices
* Configure VXLAN related feature commands: "feature nv overlay" and "feature vn-segment-vlan-based"
* Configure NVE interface and assign loopback address

4.2 VXLAN Configuration in neutron config files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To support VXLAN configuration on a top-of-rack Nexus switch, add the following configuration settings:

1. Configure an additional setting named physnet under the ml2_mech_cisco_nexus section header.
2. Configure the VLAN range in the ml2_type_vlan section.as shown in the following example. The ml2_type_vlan section header format is defined in the etc/neutron/plugins/ml2/ml2_conf.ini.sample file of the neutron repo.

3. Configure the network VNI ranges and multicast ranges in the ml2_type_nexus_vlan section. This section carries variables to provide VXLAN information required by the Nexus switch.  The section header [ml2_type_nexus_vxlan] and variables are described in the file etc/neutron/plugins/ml2/ml2_conf_cisco.ini of the networking-cisco repo. 

Below is a sample configuration which shows what each of these additional settings.

    Sample Config:
    ::

        [ml2_mech_cisco_nexus:192.168.1.1]
        # Hostname and port used on the switch for this compute host.
        # Where 1/2 indicates the "interface ethernet 1/2" port on the switch.
        compute-1=1/2

        # Provide the Nexus log in information
        username=admin
        password=mySecretPasswordForNexus

        # Where physnet1 is a physical network name listed in the ML2 VLAN section header [ml2_type_vlan].
        physnet=physnet1

        [ml2_type_vlan]
        network_vlan_ranges = physnet1:100:109

        [ml2_type_nexus_vxlan]
        # Comma-separated list of <vni_min>:<vni_max> tuples enumerating
        # ranges of VXLAN VNI IDs that are available for tenant network allocation.
        vni_ranges=50000:55000

        # Multicast groups for the VXLAN interface. When configured, will
        # enable sending all broadcast traffic to this multicast group. Comma separated
        # list of min:max ranges of multicast IP's 
        # NOTE: must be a valid multicast IP, invalid IP's will be discarded
        mcast_ranges=225.1.1.1:225.1.1.2

4.3 VXLAN Configuration in Tripleo
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The Cisco specific implementation is deployed by modifying the tripleO environment file environments/neutron-ml2-cisco-nexus-ucsm.yaml in the tripleo-heat-template repo and updating the contents with the deployment specific content. Note that with TripleO deployment, the server names are not known before deployment. Instead, the MAC address of the server must be used in place of the server name.
Descriptions of the parameters can be found at puppet/extraconfig/all_nodes/neutron-ml2-cisco-nexus-ucsm.j2.yaml in the tripleo-heat-template repo.
In this file, you can see how the parameter below are mapped to neutron variables.  With these neutron variable names, even more details can be
found in the 'configuration template' file in the networking-cisco repo.  See 'File of Interest' section for location of this file.

    Sample Config:
    ::

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
          NetworkNexusVlanNamePrefix: 'q-'
          NetworkNexusSviRoundRobin: 'false'
          NetworkNexusProviderVlanNamePrefix: 'p-'
          NetworkNexusPersistentSwitchConfig: 'false'
          NetworkNexusSwitchHeartbeatTime: 30
          NetworkNexusSwitchReplayCount: 3
          NetworkNexusProviderVlanAutoCreate: 'true'
          NetworkNexusProviderVlanAutoTrunk: 'true'
          NetworkNexusVxlanGlobalConfig: 'false'
          NetworkNexusHostKeyChecks: 'false'
          NeutronNetworkVLANRanges: 'physnet1:100:109'
          NetworkNexusVxlanVniRanges: '50000:55000'
          NetworkNexusVxlanMcastRanges: '225.1.1.1:225.1.1.2'

Config Notes:
If setting NetworkNexusManagedPhysicalNetwork, the per-port "physnet" value needs to be the same.

4.4 VXLAN Configuration in DevStack
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Refer to the section 'VLAN Configuration in Devstack', for instructions on configuring devstack with Cisco Nexus Mechanism driver. 

To configure ML2 Nexus plugin in devstack, the first step required in the local.conf file is to pull in the networking-cisco repository.  The following will cause the nexus code base to get installed.  
   ::

      [[local|localrc]]
      enable_plugin networking-cisco https://github.com/openstack/networking-cisco
      enable_service net-cisco

The file local.conf is used as input configuration file for DevStack.  In addition to the standard local.conf settings, follow the local.conf file example below to configure the Nexus switch for VXLAN Terminal End Point (VTEP) support.

    Sample Config:
    ::

        [[local|localrc]]
        enable_plugin networking-cisco https://github.com/openstack/networking-cisco
        enable_service net-cisco

        Q_PLUGIN=ml2
        Q_ML2_PLUGIN_MECHANISM_DRIVERS=openvswitch,cisco_nexus
        Q_ML2_PLUGIN_TYPE_DRIVERS=nexus_vxlan,vlan
        Q_ML2_TENANT_NETWORK_TYPE=nexus_vxlan
        ML2_VLAN_RANGES=physnet1:100:109
        ENABLE_TENANT_TUNNELS=False
        ENABLE_TENANT_VLANS=True
        PHYSICAL_NETWORK=physnet1
        OVS_PHYSICAL_BRIDGE=br-eth1

        [[post-config|/etc/neutron/plugins/ml2/ml2_conf.ini]]
        [agent]
        minimize_polling=True
        tunnel_types=

        [ml2_cisco]
        switch_hearbeat_time = 30  # No longer required since 30 is now the default in this release.
        nexus_driver = restapi     # No longer required since restapi is now the default in this release.

        [ml2_mech_cisco_nexus:192.168.1.1]
        ComputeHostA=1/10
        username=admin
        password=secretPassword
        ssh_port=22
        physnet=physnet1

        [ml2_mech_cisco_nexus:192.168.1.2]
        ComputeHostB=1/10
        NetworkNode=1/11
        username=admin
        password=secretPassword
        ssh_port=22
        physnet=physnet1

        [ml2_type_nexus_vxlan]
        vni_ranges=50000:55000
        mcast_ranges=225.1.1.1:225.1.1.2

        [ml2_type_vlan]
        network_vlan_ranges = physnet1:100:109

5. Configuration for Non-DHCP Agent Enabled Network Node Topologies
-------------------------------------------------------------------
If a DHCP Agent is not running on the network node then the network node physical connection to the Nexus switch must be added to all compute hosts that require access to the network node. As an example if the network node is physically connected to nexus switch 192.168.1.1 port 1/10 then the following configuration is required.

    Sample neutron/devstack config:
    ::

        <SKIP Other Config defined in VLAN/VXLAN sections>
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

    Sample Tripleo config:
    ::

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

