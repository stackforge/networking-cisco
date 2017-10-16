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

* HSRP-based high availability (HA)  whereby a Neutron router is supported by
  two (or more) ASR1k routers, one actively doing L3 forwarding, the others
  ready to take over in case of disruptions

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

.. note:: The ASR1k L3P and CFGA assume that nobody else manipulates the
    configurations the CFGA makes in the ASR1k routers used in the Openstack
    neutron deployment. If router administrators do not honor this
    assumption the CFGA may be unable to perform its configuration tasks.

Limitations
^^^^^^^^^^^
* The Neutron deployment must use VLAN-based network segmentation. That is, the
  L2 substrate must be controlled by ML2's VLAN technology driver.

* Access to Nova's Metadata service via Neutron routers is not supported.
  The deployment can instead provide access via Neutron's DHCP namespaces (when
  IPAM is implemented using Neutron DHCP agents. Alternatively, metadata can
  be provided to Nova virtual machines using Nova's config drive feature.

* Only one router can be attached to a particular internal neutron network.
  If a user attempts to attach router to an internal network that already has
  another router attached to it the L3P will reject the request.

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

#. Add credential information to the configuration file under the section
   ``[hosting_device_credentials]``. The format is as follows:

    * :samp:`[cisco_hosting_device_credential:{UUID}]` of hosting device
    credentials
    * :samp:`name={NAME}` of credentials
    * :samp:`description={description}` string of credentials
    * :samp:`user_name={USERNAME}`, username of credentials
    * :samp:`password={PASSWORD}`, password of credentials
    * :samp:`type={TYPE}`, *currently not used*

   The credentials are used by a CFGA when configuring ASR1k routers. For
   that reason the router administrator needs to pre-configure those
   credentials in the ASR1k devices

   The following is an example:

    .. code-block:: ini

        [hosting_device_credentials]
        [cisco_hosting_device_credential:1]
        name="Universal credential"
        description="Credential used for all hosting devices"
        user_name=stack
        password=cisco
        type=

    .. end

    .. note::
      As the credential definitions are tightly coupled to Cisco device
      management they may be placed in the file
      ``cisco_device_manager_plugin.ini``.

#. Define hosting device templates for ASR1k devices and devices supporting
   Linux network namespace-based routers.  The hosting device template
   definition should be placed in the ``[hosting_device_templates]`` section
   with the following format:

    * :samp:`[cisco_hosting_device_template:{UUID}]` of hosting device template
    * :samp:`name={NAME}` given to hosting devices created using this template
    * :samp:`enabled={True|False}`, ``True`` if template enabled, ``False``
        otherwise
    * :samp:`host_category={VM|Hardware|Network_Node}`
    * :samp:`service_types={SERVICE_TYPES}`, *currently not used*
    * :samp:`image={IMAGE}`, name or UUID of Glance image, *not used for ASR1k*
    * :samp:`flavor={UUID}` of Nova VM flavor, *not used for ASR1k*
    * :samp:`default_credentials_id={UUID}` of default credentials
    * :samp:`configuration_mechanism={MECHANISM}`, *currently not used*
    * :samp:`protocol_port={PORT}` udp/tcp port for management
    * :samp:`booting_time={SECONDS}`, typical booting time of devices based
        on this template
    * :samp:`slot_capacity={INTEGER}`, abstract metric specifying capacity to
        host logical resources like neutron routers
    * :samp:`desired_slots_free={INTEGER}`, desired number of slots to keep
        available at all times
    * :samp:`tenant_bound={TENANT_SPEC}`, list of tenant UUIDs to which template
        is available, if empty available to all tenants
    * :samp:`device_driver={MODULE}` to be used as hosting device driver
    * :samp:`plugging_driver={MODULE}` to be used as plugging driver

   The hosting device template stores information that is common for a
   certain type of devices devices (like the ASR1k). The information is used
   by the DMP and the CFGA to tailor how to they manage devices of the type
   in question.

   The following is an example with template 1 for devices using
   namespaces and template 2 for ASR1k devices):

    .. code-block:: ini

        [hosting_devices_templates]
        [cisco_hosting_device_template:1]
        name=NetworkNode
        enabled=True
        host_category=Network_Node
        service_types=router:FW:VPN
        image=
        flavor=
        default_credentials_id=1
        configuration_mechanism=
        protocol_port=22
        booting_time=360
        slot_capacity=2000
        desired_slots_free=0
        tenant_bound=
        device_driver=networking_cisco.plugins.cisco.device_manager.hosting_device_drivers.noop_hd_driver.NoopHostingDeviceDriver
        plugging_driver=networking_cisco.plugins.cisco.device_manager.plugging_drivers.noop_plugging_driver.NoopPluggingDriver

        [cisco_hosting_device_template:3]
        name="ASR1k template"
        enabled=True
        host_category=Hardware
        service_types=router
        image=
        flavor=
        default_credentials_id=1
        configuration_mechanism=
        protocol_port=22
        booting_time=360
        slot_capacity=2000
        desired_slots_free=0
        tenant_bound=
        device_driver=networking_cisco.plugins.cisco.device_manager.hosting_device_drivers.noop_hd_driver.NoopHostingDeviceDriver
        plugging_driver=networking_cisco.plugins.cisco.device_manager.plugging_drivers.hw_vlan_trunking_driver.HwVLANTrunkingPlugDriver

    .. end

   A normal deployment need not modify any of the values in the example above.

    .. note::
      As the hosting device template definitions are tightly coupled to Cisco
      device management they may be placed in the file
      ``cisco_device_manager_plugin.ini``.

#. Register ASR1k devices in the device repository. The information that
   needs to be provided should be placed in the ``[hosting_devices]``
   section and should be formatted as:

    * :samp:`[cisco_hosting_device:{UUID}]` of hosting device
    * :samp:`template_id={UUID}` of hosting device template for this hosting
    device
    * :samp:`credentials_id={UUID}` of credentials for this hosting device
    * :samp:`name={NAME}` of device, e.g., its name in DNS
    * :samp:`description={DESCRIPTION}` arbitrary description of the device
    * :samp:`device_id={MANUFACTURER_ID}` of the device, e.g., its serial
    number
    * :samp:`admin_state_up=True|False`, ``True`` if device is active,
    ``False`` otherwise
    * :samp:`management_ip_address={IP ADDRESS}` of device's management
    network interface
    * :samp:`protocol_port={PORT}` udp/tcp port of hosting device's
    management process
    * :samp:`tenant_bound={UUID}` of tenant allowed to have neutron routers on
    the hosting device, if empty any tenant can have neutron routers on it
    * :samp:`auto_delete={True|False}`, only relevant for VM-based hosting
    devices, so value is ignored for ASR1k devices

    If any of the ``UUID`` values are given as an integer they will
    automatically be converted into a proper UUID when the hosting device is
    added to the database.. Hence, ``1`` becomes
    ``00000000-0000-0000-0000-000000000001``.

   Once registered the L3P starts scheduling neutron routers to those devices
   that have ``admin_state_up`` set to True. Neutron routers already scheduled
   to a disabled hosting device continue to operate as normal.

   In the example below two ASR1k routers are registered as hosting devices
   based on hosting device template 3 and to use credentials 1 as defined in
   the earlier examples:

    .. code-block:: ini

        [hosting_devices]
        [cisco_hosting_device:3]
        template_id=3
        credentials_id=1
        name="ASR1k device 1"
        description="ASR1k in rack 2"
        device_id=SN:abcd1234efgh
        admin_state_up=True
        management_ip_address=10.0.100.5
        protocol_port=22
        tenant_bound=
        auto_delete=False

        [cisco_hosting_device:4]
        template_id=3
        credentials_id=1
        name="ASR1k device 2"
        description="ASR1k in rack 4"
        device_id=SN:efgh5678ijkl
        admin_state_up=True
        management_ip_address=10.0.100.6
        protocol_port=22
        tenant_bound=
        auto_delete=False

    .. end

   The ASR1k routers have to be configured by the router administrator to
   accept the credentials specified in the hosting device database record.

   The plugging driver for VLAN trunking needs to be configured with the
   ASR1k interfaces to use for tenant data traffic. This information is
   placed in the section ``[plugging_drivers]`` and  should be structured as
   follows:

    * :samp:`[HwVLANTrunkingPlugDriver:{UUID}`] of hosting device
    * :samp:`internal_net_interface_{NUMBER}={NETWORK_SPEC}:{INTERFACE_NAME}`
    * :samp:`external_net_interface_{NUMBER}={NETWORK_SPEC}:{INTERFACE_NAME}`

   The ``NETWORK_SPEC`` can be '*', which matches any network UUID, or a
   specific network UUID, or a comma separated list of network UUIDs.

   The example below illustrates how to specify that ``Port-channel 10``
   in for hosting devices 3 and 4 will carry all tenant network traffic :

    .. code-block:: ini

        [plugging_drivers]
        [HwVLANTrunkingPlugDriver:3]
        internal_net_interface_1=*:Port-channel10
        external_net_interface_1=*:Port-channel10

        [HwVLANTrunkingPlugDriver:4]
        internal_net_interface_1=*:Port-channel10
        external_net_interface_1=*:Port-channel10

    .. end

    .. note::
      As the hosting device definitions and plugging driver configurations
      are tightly coupled to Cisco device management they may be placed in
      the file ``cisco_device_manager_plugin.ini``.

#. Define router types for neutron routers to be hosted in devices supporting
   Linux network namespaces and in ASR1k devices.  The information that
   needs to be provided should be placed in the ``[router_types]`` section.
   The following is the format:

    * :samp:`[cisco_router_type:{UUID}]` of router type
    * :samp:`name={NAME}` of router type, should preferably be unique
    * :samp:`description={DESCRIPTION} of router type
    * :samp:`template_id={UUID}` of hosting device template for this router
    type
    * :samp:`ha_enabled_by_default={True|False}`, ``True`` if HA should be
    enabled by default, False otherwise
    * :samp:`shared={True|False}`, ``True`` if routertype is available to all
    tenants, ``False `` otherwise
    * :samp:`slot_need={NUMBER}` of slots this router type consumes in hosting
    devices
    * :samp:`scheduler={MODULE}` to be used as scheduler for router of this
    type
    * :samp:`driver={MODULE}` to be used by router plugin as router type
    driver
    * :samp:`cfg_agent_service_helper={MODULE}` to be used by CFGA as
    service helper driver
    * :samp:`cfg_agent_driver={MODULE}` to be used by CFGA agent for device
    configurations

   A router type is associated with a hosting device template. Neutron routers
   based on a particular router type will only be scheduled to hosting devices
   based on the same hosting device template.

   In the example below a router type is defined for neutron routers
   implemented as Linux network namespaces and for neutron routers implemented
   in ASR1k devices. The hosting device templates refers to the ones defined
   in the earlier hosting device template example:

    .. code-block:: ini

        [router_types]
        [cisco_router_type:1]
        name=Namespace_Neutron_router
        description="Neutron router implemented in Linux network namespace"
        template_id=1
        ha_enabled_by_default=False
        shared=True
        slot_need=0
        scheduler=
        driver=
        cfg_agent_service_helper=
        cfg_agent_driver=

        [cisco_router_type:3]
        name=ASR1k_router
        description="Neutron router implemented in Cisco ASR1k device"
        template_id=3
        ha_enabled_by_default=True
        shared=True
        slot_need=2
        scheduler=networking_cisco.plugins.cisco.l3.schedulers.l3_router_hosting_device_scheduler.L3RouterHostingDeviceHARandomScheduler
        driver=networking_cisco.plugins.cisco.l3.drivers.asr1k.asr1k_routertype_driver.ASR1kL3RouterDriver
        cfg_agent_service_helper=networking_cisco.plugins.cisco.cfg_agent.service_helpers.routing_svc_helper.RoutingServiceHelper
        cfg_agent_driver=networking_cisco.plugins.cisco.cfg_agent.device_drivers.asr1k.asr1k_routing_driver.ASR1kRoutingDriver

    .. end

   A normal deployment need not modify any of the values in the example above
   as long as the templates referred to are correct.

   To make all neutron routers being created by users be scheduled to ASR1k
   devices the ``default_router_type`` configuration option in the
   ``[routing]`` section should be set to the name of the router type
   defined for ASR1k devices. For the example above this would be done by:

    .. code-block:: ini

        [routing]
        default_router_type = ASR1k_router

    .. end

    .. note::
      As the router type definitions are tightly coupled to Cisco ASR1000 L3
       router service plugin they may be placed in the file
      ``cisco_router_plugin.ini``.

#. Include the configuration files on the command line when the neutron-server
   is started. For example:

   .. code-block:: console

       /usr/local/bin/neutron-server --config-file /etc/neutron/neutron.conf --config-file /etc/neutron/plugins/ml2/ml2_conf.ini --config-file /etc/neutron/plugins/ml2/ml2_conf_cisco.ini --config-file /etc/neutron/plugins/cisco/cisco_router_plugin.ini --config-file /etc/neutron/plugins/cisco/cisco_device_manager_plugin.ini

   .. end

High-Availability for Neutron routers in ASR1k devices
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The HA is implemented using the HSRP feature of IOS XE.

When a user creates a neutron router that has HA enabled, the L3P will
automatically create a second neutron router with the same name but with
``_HA_backup_1`` added to the name. We refer to this second router as a
*redundancy router* and it is hidden from non-admin users. We refer to the
HA-enabled router that the user created as the *user-visible router*,

The router-list command issued by a neutron *admin* user:

.. code-block:: console

    (neutron) router-list
    +--------------------------------------+---------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------+
    | id                                   | name                            | external_gateway_info                                                                                                                       |
    +--------------------------------------+---------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------+
    | 0924ad2f-9858-4f2c-b4ea-f2aff15da682 | router1_HA_backup_1             | {"network_id": "09ec988a-948e-42da-b5d1-b15c341f653c", "external_fixed_ips": [{"subnet_id": "e732b00d-027c-45d4-a68a-10f1535000f4",         |
    |                                      |                                 | "ip_address": "172.16.6.35"}]}                                                                                                              |
    | 2c8265be-6df1-49eb-b8e9-e8c0aea19f44 | router1                         | {"network_id": "09ec988a-948e-42da-b5d1-b15c341f653c", "external_fixed_ips": [{"subnet_id": "e732b00d-027c-45d4-a68a-10f1535000f4",         |
    |                                      |                                 | "ip_address": "172.16.6.34"}]}                                                                                                              |
    +--------------------------------------+---------------------------------+---------------------------------------------------------------------------------------------------------------------------------------------+

.. end

The same router-list command issued by a *non-admin* user:

.. code-block:: console

    (neutron) router-list
    +--------------------------------------+---------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | id                                   | name    | external_gateway_info                                                                                                                                              |
    +--------------------------------------+---------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    | 2c8265be-6df1-49eb-b8e9-e8c0aea19f44 | router1 | {"network_id": "09ec988a-948e-42da-b5d1-b15c341f653c", "external_fixed_ips": [{"subnet_id": "e732b00d-027c-45d4-a68a-10f1535000f4", "ip_address": "172.16.6.34"}]} |
    +--------------------------------------+---------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------+

.. end

The L3P uses an HA aware scheduler that will schedule the user-visible router
and its redundancy router on different ASR1k devices. The CFGAs managing
those ASR1k devices apply configurations for the user-visible router and its
 redundancy router so that they form an HSRP-based HA pair.

Configuration Replay onto ASR1k Router
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The CFGA performs a keep-alive against each ASR1k router that it manages.
If communication is lost due to router reboot or loss of network connectivity,
it continues to check for a sign of life. Once the router recovers, the
CFGA will replay all Neutron specific configurations for this router.
Similarly, if a CFGA is restarted, the Neutron specific configuration for all
ASR1k routers it manages are replayed. Other configurations in the router
are not touched by the replay mechanism.

The time period to perform keep-alives for each router can be altered by the
configuration variable ``heartbeat_interval`` defined under the section
header ``[cfg_agent]``.  If this feature is not wanted, the configuration
variable ``enable_heartbeat`` should be set to False which disables it. Refer
to the :doc:`ASR1000 Configuration Reference</configuration/l3-asr1k>` for
more details on these settings.

High-Availability for Configuration Agents
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
As no configurations can be made to an ASR1k router if the CFGA managing that
router is dead, a high-availability mechanism is implemented for CFGA. The
CFGA HA requires that at least two CFGA are deployed. If a CFGA dies, the
DMP will select another CFGA to take over management of the hosting devices
(the ASR1k routers) that were managed by the dead CFGA.

In more detail the HA works as follows:
Whenever an REST API update operation is performed on a neutron router, a
notification will be sent to the CFGA managing the ASR1k that hosts the
neutron router. At that point the status of the CFGA is checked. If it is
dead (= has not sent status report recently), the hosting device will be
un-assigned from that CFGA. The time interval after which a device is
considered dead can be modified using the ``cfg_agent_down_time``
configuration option.

After that, an attempt to reschedule the hosting devices to another CFGA will
be performed. If it succeeds, the hosting device will be assigned to that CFGA
and then the notification will be sent. If not, the hosting device will not be
assigned to any config agent but new re-scheduling attempts will be performed
periodically.

Every 20 seconds (configurable through the configuration option
``cfg_agent_monitoring_interval``), any CFGA that has not been checked in the
last 20 seconds (because of a notification) will be checked. If the CFGA is
determined to be dead, all hosting devices handled by that CFGA will be
un-assigned from that CFGA.

An attempt to re-schedule each of those hosting devices to other CFGA will be
performed. Those attempts that succeed will result in the corresponding ASR1k
router being assigned to the CFGA returned by the scheduler. Those attempts
that fail will result in the ASR1k remaining un-assigned.

Hence, an ASR1k will either be re-scheduled as a consequence of a neutron
router notification or by the periodic CFGA status check.

Scheduling of hosting devices to configuration agents
-----------------------------------------------------
Two hosting device to CFGA schedulers are available. Which one a deployment
will use is determined by the ``configuration_agent_scheduler_driver``
configuration option in the ``[general]`` section.

Random
^^^^^^
* Hosting-device is randomly assigned to the first available cfg-agent

* Two hosting-devices can end up being assigned to the same cfg-agent

* configuration_agent_scheduler_driver = networking_cisco.plugins.cisco.device_manager.scheduler.hosting_device_cfg_agent_scheduler.HostingDeviceCfgAgentScheduler

Stingy
^^^^^^
* Attempts to load-balance across available cfg-agents

* Hosting device is assigned to the cfg-agent with the least load

* configuration_agent_scheduler_driver = networking_cisco.plugins.cisco.device_manager.scheduler.hosting_device_cfg_agent_scheduler.StingyHostingDeviceCfgAgentScheduler

Troubleshooting
~~~~~~~~~~~~~~~
Guidance how to triage and troubleshoot a deployment that uses the ASR1000 L3
router service plugin is found here, :doc:`troubleshooting/l3-asr1k`.
