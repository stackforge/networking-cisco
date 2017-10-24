=======================================
UCSM Mechanism Driver Contributor Guide
=======================================

DevStack Configuration Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For introductory details on DevStack, refer to :doc:`/contributor/howto`.
This section focuses on how to set the UCSM driver related configuration
within DevStack's configuration file ``local.conf``. These changes should
follow the section which installs networking-cisco repository as described
in :doc:`/contributor/howto`.

Configuration required for neutron Virtual Port Support
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The following parameters need to be provided to Devstack so that the
UCSM driver can be initialized with its configuration. The parameters provided
to ``local.conf`` are similar to the configuration options provided to neutron
and describer in section :ref:`ucsm_driver_startup`.

.. code-block:: ini

    [[local|localrc]]
    enable_plugin networking-cisco https://github.com/openstack/networking-cisco

    # Set openstack passwords here.  For example, ADMIN_PASSWORD=ItsASecret

    # disable_service/enable_service here. For example,
    # disable_service tempest
    # enable_service q-svc

    # bring in latest code from repo.  (RECLONE=yes; OFFLINE=False)

    Q_PLUGIN=ml2
    Q_ML2_PLUGIN_MECHANISM_DRIVERS=openvswitch,cisco_ucsm
    Q_ML2_TENANT_NETWORK_TYPE=vlan
    ML2_VLAN_RANGES=physnet1:100:109
    ENABLE_TENANT_TUNNELS=False
    ENABLE_TENANT_VLANS=True
    PHYSICAL_NETWORK=physnet1
    OVS_PHYSICAL_BRIDGE=br-eth1

    [[post-config|/etc/neutron/plugins/ml2/ml2_conf.ini]]
    # Single UCSM Config format

    ucsm_ip=1.1.1.1
    ucsm_username=user
    ucsm_password=password

    # Hostname to Service profile mapping for UCS Manager
    # controlled compute hosts
    ucsm_host_list=Hostname1:/serviceprofilepath1/Serviceprofile1, Hostname2:Serviceprofile2

    # Service Profile Template config per UCSM. This is a mapping of Service Profile
    # Template to the list of UCS Servers controlled by this template.
    sp_template_list = SP_Template1_path:SP_Template1:S1,S2 SP_Template2_path:SP_Template2:S3,S4

    # SR-IOV and VM-FEX vendors supported by this plugin
    # xxxx:yyyy represents vendor_id:product_id
    # This config is optional.
    supported_pci_devs=['2222:3333', '4444:5555']

    # Ethernet port names to be used for virtio ports
    ucsm_virtio_eth_ports = neutron-eth0, neutron-eth1

    # If there are multiple UCSMs in the setup, then the above
    # config needs to be specified in the multi-UCSM format
    # for each UCSM
    [ml2_cisco_ucsm_ip:1.1.1.1]
    ucsm_username = username
    ucsm_password = password
    ucsm_virtio_eth_ports = eth0, eth1
    ucsm_host_list=Hostname1:Serviceprofile1, Hostname2:Serviceprofile2
    sp_template_list = SP_Template1_path:SP_Template1:S1,S2 SP_Template2_path:SP_Template2:S3,S4


    # The following config applies to all the UCSMs in the cloud and
    # hence need to be specified once and not per UCSM.
    # VNIC Profile Template config per UCSM.
    vnic_template_list = physnet1:vnic_template_path1:vt11,vt12 physnet2:vnic_template_path2:vt21,vt22

    # SR-IOV Multi-VLAN trunk config section
    [sriov_multivlan_trunk]
    test_network1=5,7-9
    test_network2=500,701 - 709

.. end
