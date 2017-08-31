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
are ultimately passed into neutron when it is started. Details
in this guide contain a description of the configuration needed in
devstack, tripleo, and neutron configuration files.

2. Nexus Files Of Interest
--------------------
Location of the Mechanism Driver code:
{install_dir}/networking-cisco/networking_cisco/plugins/ml2/drivers/cisco/nexus

Location of configuration template with detailed descriptions of each variable:
{install_dir}/networking-cisco/etc/neutron/plugins/ml2/ml2_conf_cisco.ini

Location of installed neutron configuration files after running devstack:
/etc/neutron/plugins/ml2

3. VLAN Configuration
---------------------
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

   In the following sample configuration, it contains configuration for both Baremetal
   and standard configuration as they can coexist at the same time.  If baremetal is not
   being deployed, then those baremetal configuration variables identified below can
   be omitted.  See the user guide for details on VLAN creation and removal.

   Sample neutron start-up Config with ethernet interfaces:

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
      #  previously it defaulted to 0 for disabled.  This causes keep-alive to be
      #  sent to each Nexus switch for the amount of seconds configured. If a failure
      #  is detected, the configuration will be replayed once the switch is restored.
      switch_heartbeat_time = 30
       
      #- Use section header 'ml2_mech_cisco_nexus:' followed by the IP address of the Nexus switch.
      [ml2_mech_cisco_nexus:1.1.1.1]

      #- Provide the Nexus login information
      username=admin
      password=mySecretPasswordForNexus

      #- Hostname and port used on the switch for this compute host. (non-baremetal config only)
      #  Where 1/2 indicates the "interface ethernet 1/2" port on the switch and compute-1 is
      #  the host name
      compute-1=1/2

      #- Provide range of vpc ids for use when creating port-channels for baremetal events.
      #  The following allows for a pool of ids 1001 thru 1025 and 1030.
      vpc_pool=1001-1025,1030

      #- Provide custom port-channel Nexus 9K commands for use when creating port-channels
      #  for baremetal events.
      intfcfg.portchannel=no lacp suspend-individual;spanning-tree port type edge trunk

   In addition to supporting ethernet interfaces, multi-homed hosts using vPC configurations
   are supported.  To configure this for non-baremetal case, the administrator must do some
   pre-configuration on the nexus switch and the compute host.  These prerequisites are as
   follows:
   * The vPC must already be configured on the Nexus 9K device as described:
(https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus9000/sw/7-x/interfaces/configuration/guide/b_Cisco_Nexus_9000_Series_NX-OS_Interfaces_Configuration_Guide_7x/b_Cisco_Nexus_9000_Series_NX-OS_Interfaces_Configuration_Guide_7x_chapter_01000.html)
   * The data interfaces on the compute host must be bonded. This bonded interface must be attached to the external bridge.

   The only variance from the ethernet configuration shown previously is the host to
   interface mapping so only this change is shown below:

   Sample neutron start-up Config with vPC interfaces:

   ::
      [ml2_mech_cisco_nexus:1.1.1.1]
      compute-host1=port-channel:2

      [ml2_mech_cisco_nexus:2.2.2.2]
      compute-host1=port-channel:2

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

   Sample neutron start-up Config with multiple ethernet interfaces:

   ::
      [ml2_mech_cisco_nexus:1.1.1.1]
      compute-host1=1/11,1/12

3.2 VLAN Configuration in Tripleo
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The Cisco specific implementation is deployed by modifying the tripleO environment file environments/neutron-ml2-cisco-nexus-ucsm.yaml and updating the contents with the deployment specific content. Note that with TripleO deployment the server names are not known before deployment, so the MAC address of the server must be used in place of the server name.
Descriptions of the parameters can be found at CB_TBD  https://github.com/openstack/tripleo-heat-templates/blob/master/puppet/extraconfig/all_nodes/neutron-ml2-cisco-nexus-ucsm.yam

   Sample Config:

   ::

      resource_registry:
        OS::TripleO::AllNodesExtraConfig: /usr/share/openstack-tripleo-heat-templates/puppet/extraconfig/all_nodes/neutron-ml2-cisco-nexus-ucsm.yaml
 
      parameter_defaults:
        NeutronMechanismDrivers: 'openvswitch,cisco_nexus'
        NetworkNexusConfig: {
          "N9K-9372PX-1": {
              "ip_address": "1.1.1.1", 
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
* https://docs.openstack.org/devstack/
* https://wiki.openstack.org/wiki/Neutron/ML2#ML2_Configuration

To configure ML2 Nexus plugin in devstack, the first step required in the local.conf file is to pull in the networking-cisco repository.  The following will cause the nexus code base to get installed.  
   ::
      [[local|localrc]]
      enable_plugin networking-cisco https://github.com/openstack/networking-cisco
      enable_service net-cisco

The instructions at https://wiki.openstack.org/wiki/Neutron/ML2#ML2_Configuration describe at high level how to configure Devstack with ML2 plugins. how to configure DevStack with the Cisco Nexus mechanism driver. To use VLAN with the DevStack configuration, do the following additional configuration step:

If the DevStack deployment is using Neutron code from the upstream repository, to download the Cisco mechanism driver code from upstream add these two settings to the local.conf file.

The following sample configuration wil provide you with Nexus VLAN Configuration.  As with
neutron configuration shown earlier, this configuration supports both standard (legacy)
configuration as well as Baremetal.  As you can see there is a lot of similarity between
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

      [ml2_mech_cisco_nexus:1.1.1.1]
      ComputeHostA=1/10
      username=admin
      password=mySecretPasswordForNexus
      vpc_pool=1001-1025,1030
      intfcfg.portchannel=no lacp suspend-individual;spanning-tree port type edge trunk

      [ml2_mech_cisco_nexus:2.2.2.2]
      ComputeHostB=1/10
      username=admin
      password=mySecretPasswordForNexus
      vpc_pool=1001-1025,1030
      intfcfg.portchannel=no lacp suspend-individual;spanning-tree port type edge trunk



