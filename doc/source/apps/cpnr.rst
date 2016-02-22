===================================
Cisco Prime Network Registrar
===================================

1. General
----------

This is an installation guide for enabling cisco prime network registar support on OpenStack

Please refer to cisco prime network regustar installtion for how to install and bring up
the CPNR. The Neutron dhcp agent in an OpenStack setup should be communicated to the CPNR DHCP 
server to lease an IP address and communicated to CPNR DNS server to resolve a DNS query. 

This guide does not cover OpenStack installation.


2. Prerequisites
----------------
The prerequisites for installing CPNR OpenStack enabler are the
following:

    - Install CPNR plugins
    - Disable Dnsmaq or other DNS/DHCP services
	
3. CPNR plugin Installation
------------------------------

:3.1 Using devstack:

In this scenario,  will be installed along with openstack using devstack

    1. Clone devstack.

    2. Add this repo as an external repository:
		> cat local.conf
		[[local|localrc]]
		enable_plugin networking-cisco https://git.openstack.org/openstack/networking-cisco.git
		enable_service net-cisco.

    3. Run ./stack.sh

:3.2 On a setup with OpenStack already installed:

In this scenario, CPNR will be installed on a setup which has already OpenStack installed:

1. Clone networking-cisco_.

   .. _networking-cisco: https://github.com/openstack/networking-cisco
   
2. The following modifications are needed in:

  ::
   
    2.1 dhcp_agent.ini

	change the DHCP driver from dnsmasq to CPNR.

	[DEFAULT]
	#dhcp_driver = neutron.agent.linux.dhcp.Dnsmasq
	dhcp_driver = neutron.plugins.cisco.cpnr.dhcp_driver.CpnrDriver

	Add the folowing new section to the dhcp_agent.ini file with the details for contacting the CPNR local server.

	[cisco_pnr]
	http_server = http://<cpnr_localcluster_ipaddress>:8080
	http_username = <cpnr_localcluster_username>
	http_password = <cpnr_localcluster_password>
	external_interface = eth0
	dhcp_server_addr = <cpnr_localcluster_ipaddress>
	dhcp_server_port = 67
	dns_server_addr = <cpnr_localcluster_ipaddress>
	dns_server_port = 53

	Change the http_server and dhcp_server_addr to the IP address of the local PNR VM. Change the http_password to the same password as was provided in the answers file. If you are using HTTPS with a valid SSL certificate, change the scheme in http_server config variable to 'https' and the port number in the address to the appropriate port (usually 8443). If you do not want to verify SSL certificates, add a config variable to dhcp_agent.ini.

	[cisco_pnr]
	insecure = True

	Note that using the insecure variable is NOT recommended in production

	
4. ``cd networking-cisco``

5. Run ``sudo python  networking_cisco/plugins/cisco/cpnr/setup.py install``
	
6. After changing dhcp_agent.ini, restart the DHCP agent.
	systemctl restart neutron-dhcp-agent

7. Start the relay from the command line as a detached background process.

	nohup python dhcp_relay.py --config-file /etc/neutron/dhcp_agent.ini --log-file /var/log/neutron/dhcp-relay.log &
	nohup python dns_relay.py --config-file /etc/neutron/dhcp_agent.ini --log-file /var/log/neutron/dns-relay.log & 
        
