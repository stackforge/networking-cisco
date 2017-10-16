======================================================
ASR1000 L3 Router Service Plugin Troubleshooting Guide
======================================================

* To verify that the L3P, DMP and CFGA and the ASR1k routers are operating
  correctly the following steps can be performed:

    #. Check the "neutron agent-list” command to make sure that at least one
       cisco-cfg-agent is running and happy [:-)] and any default L3 agent
       is disabled [xxx]:

        .. code-block:: console

            [root@tme166 ~(keystone_admin)]# neutron agent-list
            +--------------------------------------+--------------------+------------------+-------+----------------+---------------------------+
            | id                                   | agent_type         | host             | alive | admin_state_up | binary                    |
            +--------------------------------------+--------------------+------------------+-------+----------------+---------------------------+
            | 019fdca0-6310-43f6-ae57-005fbbd1f672 | L3 agent           | tme166.cisco.com | xxx   | True           | neutron-l3-agent          |
            | 1595c8ce-3ec5-4a01-a1d8-c53cd0cd4970 | DHCP agent         | tme166.cisco.com | :-)   | True           | neutron-dhcp-agent        |
            | 61971f98-75f0-4d03-a130-88f7228c51a1 | Open vSwitch agent | tme167.cisco.com | :-)   | True           | neutron-openvswitch-agent |
            | 8d0de547-a7b8-4c33-849b-b0a7e38198b0 | Metadata agent     | tme166.cisco.com | :-)   | True           | neutron-metadata-agent    |
            | cdfc51b4-88b6-4d84-bfa3-2900914375cc | Open vSwitch agent | tme166.cisco.com | :-)   | True           | neutron-openvswitch-agent |
            | fbc8f44b-64cd-4ab1-91d8-32dbdf10d281 | Cisco cfg agent    | tme166.cisco.com | :-)   | True           | neutron-cisco-cfg-agent   |
            +--------------------------------------+--------------------+------------------+-------+----------------+---------------------------+

        .. end

    #. If cisco-cfg-agent is not running [xxx] then check the output of
       :command:`systemctl status neutron-cisco-cfg-agent.service` to make
       sure that its loaded and active or any errors that it shows.

    #. Check the logs for config-agent at
       ``/var/log/neutron/cisco-cfg-agent.log`` and see if there are any
       errors or tracebacks.

    #. Verify that a hosting-device-template for ASR1k routers is defined:

        .. code-block:: console

            [root@tme166 ~(keystone_admin)]# neutron cisco-hosting-device-template-list
            +--------------------------------------+-----------------+---------------+---------------+---------+
            | id                                   | name            | host_category | service_types | enabled |
            +--------------------------------------+-----------------+---------------+---------------+---------+
            | 00000000-0000-0000-0000-000000000001 | NetworkNode     | Network_Node  | router:FW:VPN | True    |
            | 00000000-0000-0000-0000-000000000003 | ASR1k template  | Hardware      | router        | True    |
            +--------------------------------------+-----------------+---------------+---------------+---------+

        .. end

        :note:`The above command must be performed as administrator.`

        If the Cisco extensions to neutronclient are not installed a query
        to the neutron ``cisco_hosting_device_templates`` DB table can instead
        be performed. The following shows how this is done when MySQL is used:

        .. code-block:: console

               mysql -e "use neutron; select * from cisco_hosting_device_templates;"

        .. end

    #. Verify that the ASR1k routers are registered in the device repository:

        .. code-block:: console

            [root@tme166 ~(keystone_admin)]# neutron cisco-hosting-device-list
            +--------------------------------------+----------------+--------------------------------------+----------------+--------+
            | id                                   | name           | template_id                          | admin_state_up | status |
            +--------------------------------------+----------------+--------------------------------------+----------------+--------+
            | 00000000-0000-0000-0000-000000000003 | ASR1k device 1 | 00000000-0000-0000-0000-000000000003 | True           | ACTIVE |
            | 00000000-0000-0000-0000-000000000004 | ASR1k device 2 | 00000000-0000-0000-0000-000000000003 | True           | ACTIVE |
            +--------------------------------------+----------------+--------------------------------------+----------------+--------+

        .. end

        :note:`The above command must be performed as administrator.`

        Alternatively, as a DB query:

        .. code-block:: console

               mysql -e "use neutron; select * from cisco_hosting_devices;"

        .. end

    #. Verify that a router type for ASR1k routers is defined:

        .. code-block:: console

            [root@tme166 ~(keystone_admin)]# neutron cisco-router-type-list
            +--------------------------------------+--------------------------+-------------------------------------------------------+--------------------------------------+
            | id                                   | name                     | description                                           | template_id                          |
            +--------------------------------------+--------------------------+-------------------------------------------------------+--------------------------------------+
            | 00000000-0000-0000-0000-000000000001 | Namespace_Neutron_router | Neutron router implemented in Linux network namespace | 00000000-0000-0000-0000-000000000001 |
            | 00000000-0000-0000-0000-000000000003 | ASR1k_router             | Neutron router implemented in Cisco ASR1k device      | 00000000-0000-0000-0000-000000000003 |
            +--------------------------------------+--------------------------+-------------------------------------------------------+--------------------------------------+

        .. end

        Alternatively, do:

        .. code-block:: console

               mysql -e "use neutron; select * from cisco_router_types;"

        .. end

    #. Verify that there is ip connectivity between the controllers and the
       ASR1K routers.

    #. Check the netconf sessions on the ASR1K using the “show netconf session”
       command.

    #. Collect logs from ``/var/log/neutron/server.log`` and
       ``/var/log/neutron/cisco-cfg-agent.log``.

    #. If new code is being pulled for bug fixes, run the steps from the
       install guide :doc:`install/howto` and restart Neutron and
       cisco-cfg-agent services.
