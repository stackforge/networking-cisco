===================================
Cisco ML2 Nexus Plugin
===================================

1. General
----------
The Cisco ML2 Nexus Plugin is responsible for configuration the 
Nexus 9K.  

This adminstrator guide describes a number of configuration files
from which to configure ML2 Nexus driver.  It depends on which
install method chosen whether it is devstack or by way of Tripleo.
Either method results in changes to file(s) beneath the directory
/etc/neutron/plugins/ml2.  These files contain the configuration which
are ultimately passed into neutron when it is started. Details
in this guide contain a description of the configuration needed in
devstack, tripleo, and neutron configuration files.

2. Devstack VLAN Config
-----------------------

3. ini VLAN Config Files
