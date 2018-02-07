# Copyright (c) 2013-2016 Cisco Systems, Inc.
# All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Implements a Nexus-OS NETCONF over SSHv2 API Client
"""

import re
import six
import time
import warnings

from debtcollector import removals
from oslo_concurrency import lockutils
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import importutils

from networking_cisco.ml2_drivers.nexus import (
    constants as const)
from networking_cisco.ml2_drivers.nexus import (
    exceptions as cexc)
from networking_cisco.ml2_drivers.nexus import (
    nexus_base_network_driver as basedrvr)
from networking_cisco.ml2_drivers.nexus import (
    nexus_snippets as snipp)

LOG = logging.getLogger(__name__)
warnings.simplefilter('always')


@removals.removed_class('CiscoNexusSshDriver',
                        message="CiscoNexusSshDriver replaced by "
                                "default CiscoNexusRestapiDriver.",
                        version="Cisco 5.1.0",
                        removal_version="Cisco 7.0.0")
class CiscoNexusSshDriver(basedrvr.CiscoNexusBaseDriver):
    """Nexus Driver Main Class."""
    def __init__(self, nexus_switches):
        super(CiscoNexusSshDriver, self).__init__(nexus_switches)
        self.ncclient = None
        self.connections = {}
        self.init_ssh_caching()
        LOG.debug("ML2 Nexus SSH Drivers initialized.")

    # Driver lock introduced to prevent replay thread and
    # transaction thread from closing each others
    # session before complete.
    @lockutils.synchronized('cisco-nexus-drvrlock')
    def keep_ssh_caching(self):
        self._close_ssh_session = False

    # Driver lock introduced to prevent replay thread and
    # transaction thread from closing each others
    # session before complete.
    @lockutils.synchronized('cisco-nexus-drvrlock')
    def init_ssh_caching(self):
        self._close_ssh_session = True if (
            cfg.CONF.ml2_cisco.never_cache_ssh_connection or
            (cfg.CONF.rpc_workers + cfg.CONF.api_workers) >=
            const.MAX_NEXUS_SSH_SESSIONS) else False

    def _import_client(self):
        """Import the NETCONF client (ncclient) module.

        The ncclient module is not installed as part of the normal Neutron
        distributions. It is imported dynamically in this module so that
        the import can be mocked, allowing unit testing without requiring
        the installation of ncclient.

        """
        return importutils.import_module('ncclient.manager')

    def _get_close_ssh_session(self):
        return self._close_ssh_session

    def _close_session(self, mgr, nexus_host):
        """Close the connection to the nexus switch."""
        starttime = time.time()
        if mgr:
            self.connections.pop(nexus_host, None)
            mgr.close_session()
            self.capture_and_print_timeshot(
                starttime, "close",
                switch=nexus_host)
        else:
            self.capture_and_print_timeshot(
                starttime, "nomgr_close",
                switch=nexus_host)

    # Driver lock introduced to prevent replay thread and
    # transaction thread from closing each others
    # session before complete.
    @lockutils.synchronized('cisco-nexus-drvrlock')
    def close_session(self, nexus_host):
        mgr = self._nxos_connect(nexus_host)
        self._close_session(mgr, nexus_host)

    # Driver lock introduced to prevent replay thread and
    # transaction thread from closing each others
    # session before complete.
    @lockutils.synchronized('cisco-nexus-drvrlock')
    def _get_config(self, nexus_host, filter='',
                    check_to_close_session=True):
        """Get Nexus Host Configuration

        :param nexus_host: IP address of switch
        :param filter: filter string in XML format
        :returns: Configuration requested in string format
        """

        # For loop added to handle stale ncclient handle after switch reboot.
        # If the attempt fails,
        #     close the session, save first exception
        #     loop back around
        #     try again
        #     then quit
        for retry_count in (1, 2):
            mgr = self._nxos_connect(nexus_host)
            starttime = time.time()
            try:
                data_xml = mgr.get(filter=('subtree', filter)).data_xml
            except Exception as e:
                self.capture_and_print_timeshot(
                    starttime, "geterr", retry_count, switch=nexus_host)
                try:
                    self._close_session(mgr, nexus_host)
                except Exception:
                    pass

                # if transaction is snipp.EXEC_GET_INVENTORY_SNIPPET,
                # don't retry since this is used as a ping to
                # validate connection and retry is already built
                # into replay code.
                if snipp.EXEC_GET_INVENTORY_SNIPPET == filter:
                    raise cexc.NexusConfigFailed(nexus_host=nexus_host,
                                                 config=filter,
                                                 exc=e)

                # if first try, save first exception and retry
                if retry_count == 1:
                    first_exc = e
                else:
                    raise cexc.NexusConfigFailed(nexus_host=nexus_host,
                                                 config=filter,
                                                 exc=first_exc)
            else:
                self.capture_and_print_timeshot(
                    starttime, "get",
                    switch=nexus_host)
                if check_to_close_session and self._get_close_ssh_session():
                    self._close_session(mgr, nexus_host)
                return data_xml

    # Driver lock introduced to prevent replay thread and
    # transaction thread from closing each others
    # session before complete.
    @lockutils.synchronized('cisco-nexus-drvrlock')
    def _edit_config(self, nexus_host, target='running', config='',
                     allowed_exc_strs=None, check_to_close_session=True):
        """Modify switch config for a target config type.

        :param nexus_host: IP address of switch to configure
        :param target: Target config type
        :param config: Configuration string in XML format
        :param allowed_exc_strs: Exceptions which have any of these strings
                                 as a subset of their exception message
                                 (str(exception)) can be ignored
        :param check_to_close_session: Set to False when configured to close
                                       the ssh session is not to be checked.

        :raises: NexusConfigFailed: if _edit_config() encountered an exception
                                    not containing one of allowed_exc_strs

        """
        if not allowed_exc_strs:
            allowed_exc_strs = []

        # For loop added to handle stale ncclient handle after switch reboot.
        # If the attempt fails and not an allowed exception,
        #     close the session, save first exception
        #     loop back around
        #     try again
        #     then quit
        for retry_count in (1, 2):
            mgr = self._nxos_connect(nexus_host)
            LOG.debug("NexusDriver edit config for host %s: %s",
                      nexus_host, config)
            starttime = time.time()
            try:
                mgr.edit_config(target=target, config=config)
                break
            except Exception as e:
                self.capture_and_print_timeshot(
                    starttime, "editerr", retry_count, switch=nexus_host)

                for exc_str in allowed_exc_strs:
                    if exc_str in six.u(str(e)):
                        return
                try:
                    self._close_session(mgr, nexus_host)
                except Exception:
                    pass
                if retry_count == 1:
                    first_exc = e
                else:
                    # Raise a Neutron exception. Include a description of
                    # the original ncclient exception.
                    raise cexc.NexusConfigFailed(nexus_host=nexus_host,
                                                 config=config,
                                                 exc=first_exc)

        self.capture_and_print_timeshot(
            starttime, "edit",
            switch=nexus_host)

        # if configured, close the ncclient ssh session.
        if check_to_close_session and self._get_close_ssh_session():
            self._close_session(mgr, nexus_host)

    def _nxos_connect(self, nexus_host):
        """Make SSH connection to the Nexus Switch."""

        starttime = time.time()
        if hasattr(self.connections.get(nexus_host), 'connected'):
            self.capture_and_print_timeshot(
                starttime, "cacheconnect",
                switch=nexus_host)
            return self.connections[nexus_host]

        if not self.ncclient:
            self.ncclient = self._import_client()
        nexus_ssh_port = int(self.nexus_switches[nexus_host][const.SSHPORT])
        nexus_user = self.nexus_switches[nexus_host][const.USERNAME]
        nexus_password = self.nexus_switches[nexus_host][const.PASSWORD]
        hostkey_verify = cfg.CONF.ml2_cisco.host_key_checks
        try:
            # With new ncclient version, we can pass device_params...
            man = self.ncclient.connect(
                host=nexus_host,
                port=nexus_ssh_port,
                username=nexus_user,
                password=nexus_password,
                hostkey_verify=hostkey_verify,
                timeout=30,
                device_params={
                    "name": "nexus",
                    'ssh_subsystem_name': 'xmlagent'})
        except Exception as e:
            # Raise a Neutron exception. Include a description of
            # the original ncclient exception.
            self.capture_and_print_timeshot(
                starttime, "connecterr",
                switch=nexus_host)
            raise cexc.NexusConnectFailed(nexus_host=nexus_host, exc=e)

        self.capture_and_print_timeshot(
            starttime, "connect",
            switch=nexus_host)
        self.connections[nexus_host] = man
        return self.connections[nexus_host]

    def create_xml_snippet(self, customized_config):
        """Create XML snippet.

        Creates the Proper XML structure for the Nexus Switch Configuration.
        and also does 'copy run start' if configured to do so.  This
        latter command allows configuration to persist on the switch after
        reboot.
        """
        if cfg.CONF.ml2_cisco.persistent_switch_config:
            customized_config += (snipp.EXEC_SAVE_CONF_SNIPPET)

        conf_xml_snippet = snipp.EXEC_CONF_SNIPPET % (customized_config)
        return conf_xml_snippet

    def get_interface_switch(self, nexus_host,
                             intf_type, interface):
        """Get the interface data from host.

        :param nexus_host: IP address of Nexus switch
        :param intf_type:  String which specifies interface type.
                           example: ethernet
        :param interface:  String indicating which interface.
                           example: 1/19
        :returns response:
        """

        confstr = snipp.EXEC_GET_INTF_SNIPPET % (intf_type, interface)
        starttime = time.time()
        response = self._get_config(nexus_host, confstr)
        self.capture_and_print_timeshot(starttime, "getif",
            switch=nexus_host)
        LOG.debug("GET call returned interface %(if_type)s %(interface)s "
            "config", {'if_type': intf_type, 'interface': interface})
        return response

    def initialize_baremetal_switch_interfaces(self, interfaces):
        """Initialize Nexus interfaces and for initial baremetal event."""

        self.initialize_all_switch_interfaces(interfaces)

    def initialize_all_switch_interfaces(self, interfaces, switch_ip=None,
                                         replay=True):
        """Configure Nexus interface and get port channel number.

        :param interfaces:  List of interfaces for a given switch.
                            ch_grp can be altered as last arg
                            to each interface. If no ch_grp,
                            this arg will be zero.
        :param switch_ip: IP address of Nexus switch
        :param replay: Whether in replay path
        """

        if not interfaces:
            return

        starttime = time.time()
        ifs = []
        for i, (nexus_host, intf_type, nexus_port, is_native,
            ch_grp_saved) in enumerate(interfaces):
            response = self.get_interface_switch(
                           nexus_host, intf_type, nexus_port)
            if ch_grp_saved == 0:
                # Collect the port-channel number from response
                mo = re.search("channel-group\s(\d*)\s", response)
                try:
                    ch_grp = int(mo.group(1))
                except Exception:
                    ch_grp = 0
                #substitute content of ch_grp
                no_chgrp_len = len(interfaces[i]) - 1
                interfaces[i] = interfaces[i][:no_chgrp_len] + (ch_grp,)
            else:
                ch_grp = ch_grp_saved
            if ch_grp is not 0:
                # if channel-group exists, init port-channel
                # instead of the provided ethernet interface
                intf_type = 'port-channel'
                nexus_port = str(ch_grp)
            if (response and
               "switchport trunk allowed vlan" in response):
                pass
            else:
                ifs.append(self._build_intf_confstr(
                           snipp.CMD_INT_VLAN_SNIPPET,
                           intf_type, nexus_port, 'None'))
        if ifs:
            confstr = self.create_xml_snippet(''.join(ifs))
            self._edit_config(nexus_host, target='running',
                              config=confstr)
        self.capture_and_print_timeshot(
            starttime, "get_allif",
            switch=nexus_host)

    def get_nexus_type(self, nexus_host):
        """Given the nexus host, get the type of Nexus switch.

        :param nexus_host: IP address of Nexus switch
        :returns: Nexus type
        """

        confstr = snipp.EXEC_GET_INVENTORY_SNIPPET
        starttime = time.time()
        response = self._get_config(nexus_host, confstr)
        self.capture_and_print_timeshot(
            starttime, "gettype",
            switch=nexus_host)
        if response:
            nexus_type = re.findall(
                "\<[mod:]*desc\>\"*Nexus\s*(\d)\d+\s*[0-9A-Z]+\s*"
                "[cC]hassis\s*\"*\<\/[mod:]*desc\>",
                response)
            if len(nexus_type) > 0:
                LOG.debug("GET call returned Nexus type %d",
                    int(nexus_type[0]))
                return int(nexus_type[0])
        LOG.warning("GET call failed to return Nexus type")
        return -1

    def _extract_line_item_data(self, obj, which, re_str):

        data = obj.re_search_children(which)
        if len(data) == 1:
            data = re.findall(re_str, data[0].text)

        return data[0] if len(data) == 1 else None

    def set_all_vlan_states(self, nexus_host, vlanid_range):
        """Set the VLAN states to active."""
        starttime = time.time()
        LOG.debug("NexusDriver: ")

        snippet = snipp.CMD_VLAN_CREATE_SNIPPET % vlanid_range
        self.capture_and_print_timeshot(
            starttime, "set_all_vlan_states",
            switch=nexus_host)
        self.send_edit_string(nexus_host, None, snippet)

    def get_create_vlan(self, nexus_host, vlanid, vni, conf_str):
        """Returns an XML snippet for create VLAN on a Nexus Switch."""
        LOG.debug("NexusDriver: ")

        starttime = time.time()
        if vni:
            snippet = (snipp.CMD_VLAN_CONF_VNSEGMENT_SNIPPET %
                       (vlanid, vni))
        else:
            snippet = snipp.CMD_VLAN_CREATE_SNIPPET % vlanid

        self.capture_and_print_timeshot(
            starttime, "get_create_vlan",
            switch=nexus_host)

        conf_str += snippet
        return conf_str

    def create_vlan(self, nexus_host, vlanid, vni):
        """Create a VLAN on a Nexus Switch.

        Creates a VLAN given the VLAN ID possibly VxLAN ID.
        """

        LOG.debug("NexusDriver: ")

        starttime = time.time()
        confstr = ''
        confstr = self.get_create_vlan(nexus_host, vlanid, vni, confstr)

        self.send_edit_string(nexus_host, None, confstr,
                              check_to_close_session=False)

        self.capture_and_print_timeshot(
            starttime, "create_vlan_seg",
            switch=nexus_host)

    def delete_vlan(self, nexus_host, vlanid):
        """Delete a VLAN on Nexus Switch given the VLAN ID."""
        confstr = snipp.CMD_NO_VLAN_CONF_SNIPPET % vlanid
        confstr = self.create_xml_snippet(confstr)
        starttime = time.time()
        self._edit_config(nexus_host, target='running', config=confstr,
                          allowed_exc_strs=["None of the VLANs exist"])
        self.capture_and_print_timeshot(
            starttime, "del_vlan",
            switch=nexus_host)

    def _build_intf_confstr(self, snippet, intf_type, interface, vlanid):
        """Build the VLAN config string xml snippet to be used."""
        confstr = snippet % (intf_type, interface, vlanid, intf_type)
        return confstr

    def _get_enable_vlan_on_trunk_int(self, nexus_host, vlanid, intf_type,
                                 interface, is_native, confstr=''):
        """Prepares an XML snippet for VLAN on a trunk interface.

        :param nexus_host: IP address of Nexus switch
        :param vlanid:     Vlanid(s) to add to interface
        :param intf_type:  String which specifies interface type.
                           example: ethernet
        :param interface:  String indicating which interface.
                           example: 1/19
        :param confstr:    last confstr
        :returns           XML snippet
        """
        starttime = time.time()

        snippets = []
        if is_native:
            snippets.append(snipp.CMD_INT_VLAN_NATIVE_SNIPPET)

        snippets.append(snipp.CMD_INT_VLAN_ADD_SNIPPET)

        for snip in snippets:
            confstr += self._build_intf_confstr(
                snippet=snip,
                intf_type=intf_type,
                interface=interface,
                vlanid=vlanid)

        self.capture_and_print_timeshot(
            starttime, "createif",
            switch=nexus_host)

        return confstr

    def disable_vlan_on_trunk_int(self, nexus_host, vlanid, intf_type,
                                  interface, is_native):
        """Disable a VLAN on a trunk interface."""
        starttime = time.time()

        confstr = ''
        if is_native:
            snippet = snipp.CMD_NO_VLAN_INT_NATIVE_SNIPPET
            confstr = (snippet %
                       (intf_type, interface, intf_type))
        snippet = snipp.CMD_NO_VLAN_INT_SNIPPET
        confstr += (snippet %
                   (intf_type, interface, vlanid, intf_type))

        confstr = self.create_xml_snippet(confstr)
        self._edit_config(nexus_host, target='running', config=confstr)
        self.capture_and_print_timeshot(
            starttime, "delif",
            switch=nexus_host)

    def send_edit_string(self, nexus_host, path, confstr,
                         check_to_close_session=True):
        """Sends any XML snippet to Nexus switch."""

        starttime = time.time()
        confstr = self.create_xml_snippet(confstr)
        self._edit_config(nexus_host, target='running',
                          config=confstr,
                          allowed_exc_strs=["VLAN with the same name exists",
                                             "Can't modify state for extended",
                                            "Command is only allowed on VLAN"],
                          check_to_close_session=check_to_close_session)

        self.capture_and_print_timeshot(
            starttime, "send_edit",
            switch=nexus_host)

    def send_enable_vlan_on_trunk_int(self, nexus_host, vlanid, intf_type,
                                      interface, is_native):
        """Gathers and sends an interface trunk XML snippet."""
        confstr = self._get_enable_vlan_on_trunk_int(
                      nexus_host, vlanid,
                      intf_type, interface, is_native)
        self.send_edit_string(nexus_host, None, confstr)

    def create_and_trunk_vlan(self, nexus_host, vlan_id, intf_type,
                              nexus_port, vni, is_native):
        """Create VLAN and trunk it on the specified ports."""
        starttime = time.time()
        self.create_vlan(nexus_host, vlan_id, vni)
        LOG.debug("NexusDriver created VLAN: %s", vlan_id)
        if nexus_port:
            self.send_enable_vlan_on_trunk_int(
                nexus_host, vlan_id,
                intf_type, nexus_port,
                is_native)
        self.capture_and_print_timeshot(
            starttime, "create_all",
            switch=nexus_host)

    def enable_vxlan_feature(self, nexus_host, nve_int_num, src_intf):
        """Enable VXLAN on the switch."""

        starttime = time.time()

        # Configure the "feature" commands and NVE interface
        # (without "member" subcommand configuration).
        # The Nexus 9K will not allow the "interface nve" configuration
        # until the "feature nv overlay" command is issued and installed.
        # To get around the N9K failing on the "interface nve" command
        # send the two XML snippets down separately.
        confstr = self.create_xml_snippet(snipp.CMD_FEATURE_VXLAN_SNIPPET)
        LOG.debug("NexusDriver: ")
        self._edit_config(nexus_host, config=confstr)

        confstr = self.create_xml_snippet((snipp.CMD_INT_NVE_SNIPPET %
                                           (nve_int_num, src_intf)))
        LOG.debug("NexusDriver: ")
        self._edit_config(nexus_host, config=confstr)
        self.capture_and_print_timeshot(
            starttime, "enable_vxlan",
            switch=nexus_host)

    def disable_vxlan_feature(self, nexus_host):
        """Disable VXLAN on the switch."""

        starttime = time.time()

        # Removing the "feature" commands also removes the  NVE interface.
        confstr = self.create_xml_snippet(snipp.CMD_NO_FEATURE_VXLAN_SNIPPET)
        LOG.debug("NexusDriver: ")
        self._edit_config(nexus_host, config=confstr)

        self.capture_and_print_timeshot(
            starttime, "disable_vxlan",
            switch=nexus_host)

    def create_nve_member(self, nexus_host, nve_int_num, vni, mcast_group):
        """Add a member configuration to the NVE interface."""

        starttime = time.time()
        confstr = self.create_xml_snippet((snipp.CMD_INT_NVE_MEMBER_SNIPPET %
                                           (nve_int_num, vni, mcast_group)))
        LOG.debug("NexusDriver: ")
        self._edit_config(nexus_host, config=confstr)

        self.capture_and_print_timeshot(
            starttime, "create_nve",
            switch=nexus_host)

    def delete_nve_member(self, nexus_host, nve_int_num, vni):
        """Delete a member configuration on the NVE interface."""

        starttime = time.time()

        confstr = self.create_xml_snippet((snipp.CMD_INT_NVE_NO_MEMBER_SNIPPET
                                           % (nve_int_num, vni)))
        LOG.debug("NexusDriver: ")
        self._edit_config(nexus_host, config=confstr)

        self.capture_and_print_timeshot(
            starttime, "delete_nve",
            switch=nexus_host)
