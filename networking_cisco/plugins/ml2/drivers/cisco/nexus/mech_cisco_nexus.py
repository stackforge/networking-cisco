# Copyright 2013 OpenStack Foundation
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
ML2 Mechanism Driver for Cisco Nexus platforms.
"""

import eventlet
import os
import threading
import time

from oslo_concurrency import lockutils
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils

from networking_cisco._i18n import _LE
from networking_cisco._i18n import _LI
from networking_cisco._i18n import _LW

from neutron.common import constants as n_const
from neutron.db import api as db_api
from neutron.extensions import portbindings
from neutron.plugins.common import constants as p_const
from neutron.plugins.ml2 import db as ml2_db
from neutron.plugins.ml2 import driver_api as api

from networking_cisco.plugins.ml2.drivers.cisco.nexus import (
    config as conf)
from networking_cisco.plugins.ml2.drivers.cisco.nexus import (
    constants as const)
from networking_cisco.plugins.ml2.drivers.cisco.nexus import (
    exceptions as excep)
from networking_cisco.plugins.ml2.drivers.cisco.nexus import (
    nexus_db_v2 as nxos_db)
from networking_cisco.plugins.ml2.drivers.cisco.nexus import (
    nexus_network_driver)

LOG = logging.getLogger(__name__)

HOST_NOT_FOUND = _LW("Host %s not defined in switch configuration section.")

# Delay the start of the monitor thread to avoid problems with Neutron server
# process forking. One problem observed was ncclient RPC sync close_session
# call hanging during initial _monitor_thread() processing to replay existing
# database.
DELAY_MONITOR_THREAD = 30


class CiscoNexusCfgMonitor(object):
    """Replay config on communication failure between OpenStack to Nexus."""

    def __init__(self, driver, mdriver):
        self._driver = driver
        self._mdriver = mdriver
        switch_connections = self._mdriver.get_switch_ips()
        for switch_ip in switch_connections:
            self._mdriver.set_switch_ip_and_active_state(
                switch_ip, const.SWITCH_INACTIVE)
            # this initialization occurs later for replay case
            if not self._mdriver.is_replay_enabled():
                try:
                    self._initialize_trunk_interfaces_to_none(switch_ip)
                except Exception:
                    pass

    def _configure_nexus_type(self, switch_ip, nexus_type):
        if nexus_type not in (const.NEXUS_3K, const.NEXUS_5K,
            const.NEXUS_7K, const.NEXUS_9K):
            LOG.error(_LE("Received invalid Nexus type %(nexus_type)d "
                "for switch ip %(switch_ip)s"),
                {'nexus_type': nexus_type, 'switch_ip': switch_ip})
            return
        if (self._mdriver.get_switch_nexus_type(switch_ip) ==
           const.NEXUS_TYPE_INVALID):
            self._mdriver.set_switch_nexus_type(switch_ip, nexus_type)

    def _initialize_trunk_interfaces_to_none(self, switch_ip):
        try:
            # The following determines if the switch interfaces are
            # in place.  If so, make sure they have a basic trunk
            # configuration applied to none.
            switch_ifs = self._mdriver._get_switch_interfaces(switch_ip)
            if not switch_ifs:
                LOG.debug("Skipping switch %s which has no configured "
                          "interfaces",
                          switch_ip)
                return
            self._driver.initialize_all_switch_interfaces(switch_ifs)
        except Exception:
            with excutils.save_and_reraise_exception():
                LOG.warn(_LW("Unable to initialize interfaces to "
                         "switch %(switch_ip)s"),
                         {'switch_ip': switch_ip})
                self._mdriver.register_switch_as_inactive(switch_ip,
                    'replay init_interface')

        # Only baremetal transactions will have these Reserved
        # port entries.  If found, determine if there's a change
        # then change dependent port bindings.
        for switch_ip, intf_type, port, is_native, ch_grp in switch_ifs:
            try:
                reserved = nxos_db.get_reserved_bindings(
                           const.NO_VLAN_OR_VNI_ID,
                           const.RESERVED_NEXUS_PORT_DEVICE_ID_R1,
                           switch_ip,
                           intf_type + ':' + port)
            except excep.NexusPortBindingNotFound:
                continue
            if reserved[0].channel_group != ch_grp:
                self._change_baremetal_interfaces(
                    switch_ip, intf_type, port,
                    reserved[0].channel_group, ch_grp)

        # When replay not enabled, this is call early during initialization.
        # To prevent bogus ssh handles from being copied to child processes,
        # release the handles now.
        if self._mdriver.is_replay_enabled():
            return
        try:
                mgr = self._driver.nxos_connect(switch_ip)
                self._driver._close_session(mgr, switch_ip)
        except Exception:
                LOG.warn(_LW("Failed to release connection after initialize "
                         "interfaces for switch %(switch_ip)s"),
                         {'switch_ip': switch_ip})

    def replay_config(self, switch_ip):
        """Sends pending config data in OpenStack to Nexus."""
        LOG.debug("Replaying config for switch ip %(switch_ip)s",
                  {'switch_ip': switch_ip})

        # Before replaying all config, initialize trunk interfaces
        # to none as required.  If this fails, the switch may not
        # be up all the way.  Quit and retry later.
        try:
            self._initialize_trunk_interfaces_to_none(switch_ip)
        except Exception:
            return

        nve_bindings = nxos_db.get_nve_switch_bindings(switch_ip)

        for x in nve_bindings:
            try:
                self._driver.create_nve_member(switch_ip,
                    const.NVE_INT_NUM, x.vni, x.mcast_group)
            except Exception as e:
                LOG.error(_LE("Failed to configure nve_member for "
                    "switch %(switch_ip)s, vni %(vni)s"
                    "Reason:%(reason)s "),
                    {'switch_ip': switch_ip, 'vni': x.vni,
                     'reason': e})
                self._mdriver.register_switch_as_inactive(switch_ip,
                    'replay create_nve_member')
                return

        try:
            port_bindings = nxos_db.get_nexusport_switch_bindings(switch_ip)
        except excep.NexusPortBindingNotFound:
            LOG.warn(_LW("No port entries found for switch ip "
                      "%(switch_ip)s during replay."),
                      {'switch_ip': switch_ip})
            return

        try:
            self._mdriver.configure_switch_entries(
                switch_ip, port_bindings)
        except Exception as e:
                LOG.error(_LE("Unexpected exception while replaying "
                    "entries for switch %(switch_ip)s, Reason:%(reason)s "),
                    {'switch_ip': switch_ip, 'reason': e})
                self._mdriver.register_switch_as_inactive(switch_ip,
                    'replay switch_entries')

    def check_connections(self):
        """Check connection between OpenStack to Nexus device."""
        switch_connections = self._mdriver.get_all_switch_ips()

        for switch_ip in switch_connections:
            state = self._mdriver.get_switch_ip_and_active_state(switch_ip)
            config_failure = self._mdriver.get_switch_replay_failure(
                const.FAIL_CONFIG, switch_ip)
            contact_failure = self._mdriver.get_switch_replay_failure(
                const.FAIL_CONTACT, switch_ip)
            LOG.debug("check_connections() switch "
                      "%(switch_ip)s state %(state)s "
                      "contact_failure %(contact_failure)d "
                      "config_failure %(config_failure)d ",
                      {'switch_ip': switch_ip, 'state': state,
                       'contact_failure': contact_failure,
                       'config_failure': config_failure})
            try:
                # Send a simple get nexus type to determine if
                # the switch is up
                nexus_type = self._driver.get_nexus_type(switch_ip)
            except Exception:
                if state != const.SWITCH_INACTIVE:
                    LOG.error(_LE("Lost connection to switch ip "
                        "%(switch_ip)s"), {'switch_ip': switch_ip})
                    self._mdriver.set_switch_ip_and_active_state(
                        switch_ip, const.SWITCH_INACTIVE)
                else:
                    self._mdriver.incr_switch_replay_failure(
                        const.FAIL_CONTACT, switch_ip)
            else:
                if state == const.SWITCH_RESTORE_S2:
                    try:
                        self._mdriver.configure_next_batch_of_vlans(switch_ip)
                    except Exception as e:
                        LOG.error(_LE("Unexpected exception while replaying "
                                  "entries for switch %(switch_ip)s, "
                                  "Reason:%(reason)s "),
                                  {'switch_ip': switch_ip, 'reason': e})
                        self._mdriver.register_switch_as_inactive(
                            switch_ip, 'replay next_vlan_batch')
                    continue

                if state == const.SWITCH_INACTIVE:
                    self._configure_nexus_type(switch_ip, nexus_type)
                    LOG.info(_LI("Re-established connection to switch "
                        "ip %(switch_ip)s"),
                        {'switch_ip': switch_ip})

                    self._mdriver.set_switch_ip_and_active_state(
                        switch_ip, const.SWITCH_RESTORE_S1)
                    self._driver.keep_ssh_caching()
                    self.replay_config(switch_ip)
                    self._driver.init_ssh_caching()

                    # If replay failed, it stops trying to configure db entries
                    # and sets switch state to inactive so this caller knows
                    # it failed.  If it did fail, we increment the
                    # retry counter else reset it to 0.
                    if self._mdriver.get_switch_ip_and_active_state(
                        switch_ip) == const.SWITCH_INACTIVE:
                        self._mdriver.incr_switch_replay_failure(
                            const.FAIL_CONFIG, switch_ip)
                        LOG.warn(_LW("Replay config failed for "
                            "ip %(switch_ip)s"),
                            {'switch_ip': switch_ip})
                    else:
                        self._mdriver.reset_switch_replay_failure(
                            const.FAIL_CONFIG, switch_ip)
                        self._mdriver.reset_switch_replay_failure(
                            const.FAIL_CONTACT, switch_ip)
                        LOG.info(_LI("Replay config successful for "
                            "ip %(switch_ip)s"),
                            {'switch_ip': switch_ip})


class CiscoNexusMechanismDriver(api.MechanismDriver):

    """Cisco Nexus ML2 Mechanism Driver."""

    def initialize(self):
        # Create ML2 device dictionary from ml2_conf.ini entries.
        conf.ML2MechCiscoConfig()

        # Extract configuration parameters from the configuration file.
        self._nexus_switches = conf.ML2MechCiscoConfig.nexus_dict
        LOG.debug("nexus_switches found = %s", self._nexus_switches)
        # Save dynamic switch information
        self._switch_state = {}

        self.driver = nexus_network_driver.CiscoNexusDriver()

        # This method is only called once regardless of number of
        # api/rpc workers defined.
        self._ppid = os.getpid()

        self.monitor = CiscoNexusCfgMonitor(self.driver, self)
        self.timer = None
        self.monitor_timeout = conf.cfg.CONF.ml2_cisco.switch_heartbeat_time
        self.monitor_lock = threading.Lock()
        # Start the monitor thread
        if self.is_replay_enabled():
            eventlet.spawn_after(DELAY_MONITOR_THREAD, self._monitor_thread)

    def is_replay_enabled(self):
        return conf.cfg.CONF.ml2_cisco.switch_heartbeat_time > 0

    def set_switch_ip_and_active_state(self, switch_ip, state):
        if not self.is_replay_enabled():
            return
        try:
            nxos_db.get_reserved_bindings(
                const.NO_VLAN_OR_VNI_ID,
                const.RESERVED_NEXUS_SWITCH_DEVICE_ID_R1,
                switch_ip)
        except excep.NexusPortBindingNotFound:
            # overload port_id to contain switch state
            nxos_db.add_nexusport_binding(
                state, const.NO_VLAN_OR_VNI_ID,
                const.NO_VLAN_OR_VNI_ID,
                switch_ip,
                const.RESERVED_NEXUS_SWITCH_DEVICE_ID_R1,
                False)
        # overload port_id to contain switch state
        nxos_db.update_reserved_binding(
            const.NO_VLAN_OR_VNI_ID,
            switch_ip,
            const.RESERVED_NEXUS_SWITCH_DEVICE_ID_R1,
            state)

    def get_switch_ip_and_active_state(self, switch_ip):
        if not self.is_replay_enabled():
            return const.SWITCH_ACTIVE
        binding = nxos_db.get_reserved_bindings(
                      const.NO_VLAN_OR_VNI_ID,
                      const.RESERVED_NEXUS_SWITCH_DEVICE_ID_R1,
                      switch_ip)
        if len(binding) == 1:
            return binding[0].port_id
        else:
            return const.SWITCH_INACTIVE

    def _switch_defined(self, switch_ip):
        """Verify this ip address is defined (for Nexus)."""

        if ((switch_ip, const.USERNAME) in self._nexus_switches and
           (switch_ip, const.PASSWORD) in self._nexus_switches):
            return True
        else:
            return False

    # There are two types of reserved bindings.
    # 1) The Switch binding purpose is to keep track
    #    of the switch state for when replay is enabled.
    #    Keeping it in the db, allows for all processes
    #    to determine known state of each switch.
    # 2) The reserved port binding is used with baremetal
    #    transactions which don't rely on host to interface
    #    mapping in the ini file.  It is learned from
    #    the transaction and kept in the data base
    #    for further reference.
    def _is_reserved_binding(self, binding):
        """Identifies switch & port operational bindings."""

        return (binding.instance_id in
               [const.RESERVED_NEXUS_SWITCH_DEVICE_ID_R1,
                const.RESERVED_NEXUS_PORT_DEVICE_ID_R1])

    def register_switch_as_inactive(self, switch_ip, func_name):
        self.set_switch_ip_and_active_state(switch_ip, const.SWITCH_INACTIVE)
        LOG.exception(
            _LE("Nexus Driver cisco_nexus failed in %(func_name)s"),
            {'func_name': func_name})

    def is_switch_active(self, switch_ip):
        if self.is_replay_enabled():
            switch_state = self.get_switch_ip_and_active_state(switch_ip)
            active_states = [const.SWITCH_ACTIVE, const.SWITCH_RESTORE_S2]
            return switch_state in active_states
        else:
            return True

    def set_switch_nexus_type(self, switch_ip, type):
        self._switch_state[switch_ip, '_nexus_type'] = type

    def get_switch_nexus_type(self, switch_ip):
        if (switch_ip, '_nexus_type') in self._switch_state:
            return self._switch_state[switch_ip, '_nexus_type']
        else:
            return -1

    def _save_switch_vlan_range(self, switch_ip, vlan_range):
        self._switch_state[switch_ip, '_vlan_range'] = vlan_range

    def _get_switch_vlan_range(self, switch_ip):
        if (switch_ip, '_vlan_range') in self._switch_state:
            return self._switch_state[switch_ip, '_vlan_range']
        else:
            return []

    def _save_switch_vxlan_range(self, switch_ip, vxlan_range):
        self._switch_state[switch_ip, '_vxlan_range'] = vxlan_range

    def _get_switch_vxlan_range(self, switch_ip):
        if (switch_ip, '_vxlan_range') in self._switch_state:
            return self._switch_state[switch_ip, '_vxlan_range']
        else:
            return []

    def _pop_vlan_range(self, switch_ip, size):
        """Extract a specific number of vlans from storage.

        Purpose: Can only send a limited number of vlans
        to Nexus at a time.

        Sample Use Cases:
        1) vlan_range is a list of vlans.  If there is a
        list 1000, 1001, 1002, thru 2000 and size is 6,
        then the result is '1000-1005' and 1006 thru 2000
        is pushed back into storage.
        2) if the list is 1000, 1003, 1004, 1006 thru 2000
        and size is 6, then the result is
        '1000, 1003-1004, 1006-1008' and 1009 thru 2000
        is pushed back into storage for next time.
        """
        vlan_range = self._get_switch_vlan_range(switch_ip)
        sized_range = ''
        fr = 0
        to = 0
        # if vlan_range not empty and haven't met requested size
        while size > 0 and vlan_range:
            vlan_id, vni, vlan_name = vlan_range.pop(0)
            size -= 1
            if fr == 0 and to == 0:
                fr = vlan_id
                to = vlan_id
            else:
                diff = vlan_id - to
                if diff == 1:
                    to = vlan_id
                else:
                    if fr == to:
                        sized_range += str(to) + ','
                    else:
                        sized_range += str(fr) + '-'
                        sized_range += str(to) + ','
                    fr = vlan_id
                    to = vlan_id
        if fr != 0:
            if fr == to:
                sized_range += str(to)
            else:
                sized_range += str(fr) + '-'
                sized_range += str(to)
            self._save_switch_vlan_range(switch_ip, vlan_range)

        return sized_range

    def _valid_replay_key(self, fail_key, switch_ip):
        if (switch_ip, const.REPLAY_FAILURES) not in self._switch_state:
            self._switch_state[switch_ip, const.REPLAY_FAILURES] = {
                const.FAIL_CONTACT: 0,
                const.FAIL_CONFIG: 0}

        return fail_key in self._switch_state[switch_ip,
                                              const.REPLAY_FAILURES]

    def reset_switch_replay_failure(self, fail_key, switch_ip):
        if self._valid_replay_key(fail_key, switch_ip):
            self._switch_state[switch_ip, const.REPLAY_FAILURES][fail_key] = 0

    def incr_switch_replay_failure(self, fail_key, switch_ip):
        if self._valid_replay_key(fail_key, switch_ip):
            self._switch_state[switch_ip, const.REPLAY_FAILURES][fail_key] += 1

    def get_switch_replay_failure(self, fail_key, switch_ip):
        if self._valid_replay_key(fail_key, switch_ip):
            return self._switch_state[switch_ip,
                   const.REPLAY_FAILURES][fail_key]
        else:
            return 0

    def get_all_switch_ips(self):
        """Using reserved switch binding get all switch ips."""

        switch_connections = []
        try:
            bindings = nxos_db.get_reserved_bindings(
                           const.NO_VLAN_OR_VNI_ID,
                           const.RESERVED_NEXUS_SWITCH_DEVICE_ID_R1)
        except excep.NexusPortBindingNotFound:
            LOG.error(_LE("No switch bindings in the port data base"))
            bindings = []
        for switch in bindings:
            switch_connections.append(switch.switch_ip)

        return switch_connections

    def _valid_network_segment(self, segment):
        return (cfg.CONF.ml2_cisco.managed_physical_network is None or
                cfg.CONF.ml2_cisco.managed_physical_network ==
                segment[api.PHYSICAL_NETWORK])

    def _is_supported_deviceowner(self, port):
        return (port['device_owner'].startswith('compute') or
                port['device_owner'].startswith('baremetal') or
                port['device_owner'] == n_const.DEVICE_OWNER_DHCP or
                port['device_owner'] == n_const.DEVICE_OWNER_ROUTER_HA_INTF)

    def _is_status_active(self, port):
        return port['status'] == n_const.PORT_STATUS_ACTIVE

    # _is_baremetal()
    # There are two types of transactions.
    # First is the transaction which is dependent on
    # host to interface mapping config stored in the
    # ml2_conf.ini file. The VNIC type for this is
    # 'normal' which is the assumed condition.
    # Second there is the baremetal case which comes
    # about by project ironic where the interfaces
    # are provided in the host transaction. In this
    # case the VNIC_TYPE is 'baremetal'.
    #
    def _is_baremetal(self, port):
        """Identifies ironic baremetal transactions."""
        return (port[portbindings.VNIC_TYPE] ==
                portbindings.VNIC_BAREMETAL)

    def _get_baremetal_switch_info(self, link_info):
        """Get switch_info dictionary from context."""

        switch_info = {}
        if ('switch_info' in link_info and
            isinstance(link_info['switch_info'], dict)):
            switch_info = link_info['switch_info']

        return switch_info

    def _supported_baremetal_transaction(self, context):
        """Verify baremetal transaction is complete."""

        port = context.current

        if not self._is_baremetal(port):
            return False

        if portbindings.PROFILE not in port:
            return False

        profile = port[portbindings.PROFILE]

        if 'local_link_information' not in profile:
            return False

        all_link_info = profile['local_link_information']

        selected = False
        for link_info in all_link_info:

            if 'port_id' not in link_info:
                return False

            switch_info = self._get_baremetal_switch_info(
                              link_info)
            if not switch_info:
                return False

            if 'switch_ip' not in switch_info:
                return False

            switch_ip = switch_info['switch_ip']
            if self._switch_defined(switch_ip):
                selected = True
            else:
                LOG.warning(_LW("Skip switch %s.  Not configured "
                          "in ini file") % switch_ip)

        if not selected:
            return False

        selected = False
        for segment in context.segments_to_bind:

            # if valid 'vlan' type and vlan_id
            if (segment[api.NETWORK_TYPE] == p_const.TYPE_VLAN and
                segment[api.SEGMENTATION_ID]):
                context.set_binding(segment[api.ID],
                    portbindings.VIF_TYPE_OTHER,
                    {},
                    status=n_const.PORT_STATUS_ACTIVE)
                selected = True
                LOG.debug("Baremetal binding selected: segment ID %(id)s, "
                          "segment %(seg)s, phys net %(physnet)s, and "
                          "network type %(nettype)s with %(count)d "
                          "link_info",
                          {'id': segment[api.ID],
                           'seg': segment[api.SEGMENTATION_ID],
                           'physnet': segment[api.PHYSICAL_NETWORK],
                           'nettype': segment[api.NETWORK_TYPE],
                           'count': len(all_link_info)})

        return selected

    def _gather_configured_ports(self, switch_ip, attr, host_list):
        """Get all interfaces originally from ml2_conf_cisco files."""

        for port_id in (
            self._nexus_switches[switch_ip, attr].split(',')):
            if ':' in port_id:
                intf_type, port = port_id.split(':')
            else:
                intf_type, port = 'ethernet', port_id
            # is_native is False for VNIC_TYPE of normal
            host_list.append((switch_ip, intf_type, port,
                const.NOT_NATIVE))

    # _get_baremetal_switches()
    # This method is used to extract switch information
    # from transactions where VNIC_TYPE is baremetal.
    #
    # Input:   Received port transaction
    #
    # Returns: all_switches, active_switches
    #
    def _get_baremetal_switches(self, port):
        """Get switch ip addresses from baremetal transaction."""

        all_switches = set()
        active_switches = set()
        all_link_info = port[portbindings.PROFILE]['local_link_information']
        for link_info in all_link_info:
            switch_info = self._get_baremetal_switch_info(
                              link_info)
            if not switch_info:
                continue
            switch_ip = switch_info['switch_ip']

            # If not for Nexus
            if not self._switch_defined(switch_ip):
                continue

            all_switches.add(switch_ip)
            if self.is_switch_active(switch_ip):
                active_switches.add(switch_ip)

        return list(all_switches), list(active_switches)

    # _get_baremetal_connections
    # This method is used to extract switch/interface
    # information from transactions where VNIC_TYPE is
    # baremetal.
    #
    # Input:   - Received port transaction
    #          - Indicator for selecting connections with
    #            switches that are active
    #          - only return interfaces from the
    #            segment/transaction as opposed to
    #            say port channels which are learned.
    #
    # Returns: list of switch_ip, intf_type, port_id, is_native
    #
    def _get_baremetal_connections(self, port,
                                   only_active_switch=False,
                                   from_segment=False):
        """Get switch ips and interfaces from baremetal transaction."""

        connections = []

        all_link_info = port[portbindings.PROFILE]['local_link_information']
        for link_info in all_link_info:

            # Extract and store port info
            port_id = link_info['port_id']
            if ':' in port_id:
                intf_type, port = port_id.split(':')
            else:
                intf_type, port = 'ethernet', port_id

            # Determine if this switch is to be skipped
            switch_info = self._get_baremetal_switch_info(
                              link_info)
            if not switch_info:
                continue
            switch_ip = switch_info['switch_ip']

            # If not for Nexus
            if not self._switch_defined(switch_ip):
                continue

            # Requested connections for only active switches
            if (only_active_switch and
                not self.is_switch_active(switch_ip)):
                continue

            if 'is_native' in switch_info:
                is_native = switch_info['is_native']
            else:
                is_native = const.NOT_NATIVE
            if not from_segment:
                try:
                    reserved = nxos_db.get_reserved_bindings(
                        const.NO_VLAN_OR_VNI_ID,
                        const.RESERVED_NEXUS_PORT_DEVICE_ID_R1,
                        switch_ip,
                        intf_type + ':' + port)
                    if reserved[0].channel_group > 0:
                        intf_type = 'port-channel'
                        port = str(reserved[0].channel_group)
                except excep.NexusPortBindingNotFound:
                    pass

            connections.append((switch_ip, intf_type, port, is_native))

        return connections

    # _get_active_baremetal_connections
    # This method is used to extract switch/interface
    # information from transactions where VNIC_TYPE is
    # baremetal for only active switches.
    #
    # Input:   - Received port transaction
    #
    # Returns: list of switch_ip, intf_type, port_id, is_native
    #
    def _get_active_baremetal_connections(self, port):
        """Get active switch ips and interfaces from transaction."""

        return self._get_baremetal_connections(port, True)

    # _change_baremetal_interfaces
    #
    # This method is used to extract switch/interface
    # information from transactions where VNIC_TYPE is
    # baremetal for only active switches.
    # When interfaces are initialized during replay restore,
    # check to verify that ch-grps are the same.
    # if not, this function is called to handle change for the
    # following cases.
    # 1) If RESERVED port is zero and switch returns non-zero, then
    #    * create port-channel db entry
    #    * Update RESERVED port with non-zero port channel
    #    * delete db entry with port_id defined in port_binding.
    # 2) If RESERVED port is non-zero and switch returns non-zero
    #    and they don't match, then
    #    * create port-channel db entry with channel grp from switch,
    #    * Update RESERVED port with non-zero port channel received
    #      from switch,
    #    * delete port-channel db entry with with old-ch-grp from
    #      RESERVED port.
    # 3) If RESERVED port is non-zero and switch returns zero, then:
    #    * create port entry with port_id from RESERVED port
    #    * Update RESERVED port with zero channel-group
    #    * Delete port-channel db entry with old-ch-grp from RESERVED port
    #
    def _change_baremetal_interfaces(self, switch_ip, intf_type,
                                    port, old_ch_grp, ch_grp):
        """Restart detected port channel change. Update database."""

        if old_ch_grp == ch_grp:
            return

        # Get all bindings to this switch interface
        reserved_port_id = intf_type + ':' + port
        if old_ch_grp != 0:
            old_port_id = 'port-channel' + ':' + str(old_ch_grp)
        else:
            old_port_id = intf_type + ':' + port

        # Get all port instances related to this switch interface
        try:
            bindings = nxos_db.get_nexus_switchport_binding(
                           reserved_port_id, switch_ip)
        except Exception:
            return

        # process all port instances related to this switch interface
        # and change port channel group
        for row in bindings:

            if ch_grp != 0:
                new_port_id = 'port-channel' + ':' + str(ch_grp)
            else:
                new_port_id = intf_type + ':' + port

            # Add port binding with new channel-group
            try:
                nxos_db.get_nexusport_binding(
                    new_port_id, row.vlan_id,
                    switch_ip, row.instance_id)
            except excep.NexusPortBindingNotFound:
                nxos_db.add_nexusport_binding(
                    new_port_id, row.vlan_id, row.vni,
                    switch_ip, row.instance_id,
                    row.is_provider_vlan,
                    row.is_native)

            # Remove port binding with old channel-group
            try:
                nxos_db.remove_nexusport_binding(
                    old_port_id, row.vlan_id, row.vni,
                    switch_ip, row.instance_id,
                    row.is_provider_vlan)
            except Exception:
                # Something wrong.  Skip this  CB_FINISH
                continue

        # Update the reserved port binding with new channel group
        nxos_db.update_reserved_binding(
                const.NO_VLAN_OR_VNI_ID,
                switch_ip,
                const.RESERVED_NEXUS_PORT_DEVICE_ID_R1,
                intf_type + ':' + port,
                False,
                ch_grp)

    # _init_baremetal_trunk_interfaces()
    #
    # With Baremetal transactions, the interfaces aren't
    # known during initialization so they must be initialized
    # when the transactions are received.
    # * Reserved switch entries are added if needed.
    # * Reserved port entries are added.
    # * Port Bindings are added and initialized on the switch.
    # * We determine if port channel is configured on the
    #   interface and store it so we know to create a port-channel
    #   binding instead of that defined in the transaction.
    #   In this case, the RESERVED binding is the ethernet interface
    #   with port-channel stored in channel-group field.
    #   With this channe-group not 0, we know to create a port binding
    #   as a port-channel instead of interface ethernet.
    def _init_baremetal_trunk_interfaces(self, port_seg, segment, vni):
        """Initialize baremetal switch interfaces and DB entry."""

        # interfaces list requiring switch initialization and
        # reserved port and port_binding db entry creation
        list_to_init = []

        # interfaces list requiring reserved port and port_binding
        # db entry creation
        inactive_switch = []

        # interfaces list requiring creation of port_binding db entry
        reserved_exists = []

        all_switches, active_switches = (
            self._get_baremetal_switches(port_seg))
        if self.is_replay_enabled():
            for switch_ip in all_switches:
                # Add reserved switch entry only if it does not exist.
                try:
                    nxos_db.get_reserved_bindings(
                        const.NO_VLAN_OR_VNI_ID,
                        const.RESERVED_NEXUS_SWITCH_DEVICE_ID_R1,
                        switch_ip)
                except excep.NexusPortBindingNotFound:
                    # overload port_id to contain switch state
                    nxos_db.add_nexusport_binding(
                        const.SWITCH_INACTIVE,
                        const.NO_VLAN_OR_VNI_ID,
                        const.NO_VLAN_OR_VNI_ID,
                        switch_ip,
                        const.RESERVED_NEXUS_SWITCH_DEVICE_ID_R1)

        connections = self._get_baremetal_connections(
                          port_seg, False, True)
        for switch_ip, intf_type, port, is_native in connections:
            try:
                reserved = nxos_db.get_reserved_bindings(
                           const.NO_VLAN_OR_VNI_ID,
                           const.RESERVED_NEXUS_PORT_DEVICE_ID_R1,
                           switch_ip,
                           intf_type + ':' + port)
                reserved_exists.append(
                    (switch_ip, intf_type, port, is_native,
                    reserved[0].channel_group))
            except excep.NexusPortBindingNotFound:
                if self.is_switch_active(switch_ip):
                    # channel-group added later
                    list_to_init.append(
                        (switch_ip, intf_type, port, is_native))
                else:
                    inactive_switch.append(
                        (switch_ip, intf_type, port, is_native, 0))

        # channel_group is appended to tuples in list_to_init
        self.driver.initialize_all_switch_interfaces(list_to_init)

        # Add inactive list to list_to_init to create RESERVED
        # port data base entries
        list_to_init += inactive_switch
        for switch_ip, intf_type, port, is_native, ch_grp in list_to_init:
            nxos_db.add_nexusport_binding(
                intf_type + ':' + port,
                const.NO_VLAN_OR_VNI_ID,
                const.NO_VLAN_OR_VNI_ID,
                switch_ip,
                const.RESERVED_NEXUS_PORT_DEVICE_ID_R1,
                False,
                False,   # is_native used in this binding
                ch_grp)

        device_id = port_seg.get('device_id')
        vlan_id = segment.get(api.SEGMENTATION_ID)
        # TODO(rpothier) Add back in provider segment support.
        is_provider_vlan = False

        # Add reserved_exists list to list_to_init to create
        # port_binding data base entries
        list_to_init += reserved_exists
        for switch_ip, intf_type, port, is_native, chgrp in list_to_init:
            if chgrp is 0:
                port_id = intf_type + ':' + port
            else:
                port_id = 'port-channel' + ':' + str(chgrp)
            try:
                nxos_db.get_nexusport_binding(port_id, vlan_id, switch_ip,
                                              device_id)
            except excep.NexusPortBindingNotFound:
                nxos_db.add_nexusport_binding(
                    port_id, str(vlan_id), str(vni),
                    switch_ip, device_id,
                    is_provider_vlan,
                    is_native,
                    chgrp)

    # _get_host_switches()
    # This method is used to extract switch information
    # from transactions where VNIC_TYPE is normal.
    # Information is extracted from ini file which
    # is stored in _nexus_switches.
    #
    # Input:   host_name from transaction
    #
    # Returns: all_switches, active_switches
    #
    def _get_host_switches(self, host_id):
        """Get switch IPs from configured host mapping."""

        all_switches = set()
        active_switches = set()
        for switch_ip, attr in self._nexus_switches:
            if str(attr) == str(host_id):
                all_switches.add(switch_ip)
                if self.is_switch_active(switch_ip):
                    active_switches.add(switch_ip)

        return list(all_switches), list(active_switches)

    # _get_host_connections()
    # This method is used to extract switch/interface
    # information from ini files when VNIC_TYPE is
    # normal.  The ini files contain host to interface
    # mappings.
    #
    # Input:   - Host name
    #          - Indicator for selecting connections with
    #            switches that are active
    #
    # Returns: list of switch_ip, intf_type, port_id, is_native
    #
    def _get_host_connections(self, host_id,
                              only_active_switch=False):
        """Get switch IPs and interfaces from config host mapping."""

        host_found = False
        host_connections = []
        for switch_ip, attr in self._nexus_switches:
            if str(attr) == str(host_id):
                host_found = True
                if (only_active_switch and
                    not self.is_switch_active(switch_ip)):
                    continue
                self._gather_configured_ports(
                    switch_ip, attr, host_connections)

        if not host_found:
            LOG.warn(HOST_NOT_FOUND, host_id)

        return host_connections

    # _get_active_host_connections()
    # This method is used to extract switch/interface
    # information for only active switches.  The
    # data comes from ini files when VNIC_TYPE is
    # normal.  The ini files contain host to interface
    # mappings.
    #
    # Input:   - Host name
    #          - Indicator for selecting connections with
    #            switches that are active
    #
    # Returns: list of switch_ip, intf_type, port_id, is_native
    #
    def _get_active_host_connections(self, host_id):
        """Get active switch IPs and interfaces from config host."""

        return self._get_host_connections(host_id, True)

    def _get_port_connections(self, port, host_id,
                              only_active_switch=False):
        if host_id:
            return self._get_host_connections(
                       host_id, only_active_switch)
        else:
            return self._get_baremetal_connections(
                       port, only_active_switch)

    def _get_active_port_connections(self, port, host_id):
        return self._get_port_connections(port, host_id, True)

    #
    # _get_known_baremetal_interfaces()
    #
    # For a given switch, this returns all known RESERVED port
    # interfaces.  These learned by received baremetal
    # transactions.
    def _get_known_baremetal_interfaces(self, requested_switch_ip):
        """Get known baremetal interfaces from reserved DB."""

        switch_ifs = []

        try:
            port_info = nxos_db.get_reserved_bindings(
                            const.NO_VLAN_OR_VNI_ID,
                            const.RESERVED_NEXUS_PORT_DEVICE_ID_R1,
                            requested_switch_ip)
        except excep.NexusPortBindingNotFound:
            port_info = []

        for binding in port_info:
            port_id = binding.port_id
            if ':' in port_id:
                intf_type, port = port_id.split(':')
            else:
                intf_type, port = 'ethernet', port_id
            switch_ifs.append(
                (requested_switch_ip, intf_type, port,
                binding.is_native))
        return switch_ifs

    #
    # _get_config_switch_interfaces()
    #
    # For a given switch, this returns all known configured port
    # interfaces.  These configured in the ml2_conf.ini file.
    #
    def _get_config_switch_interfaces(self, requested_switch_ip):
        """Identify host entries to get interfaces."""

        switch_ifs = []
        defined_attributes = [const.USERNAME, const.PASSWORD, const.SSHPORT,
                              'physnet']
        for switch_ip, attr in self._nexus_switches:
            # if not in clearly defined attribute, it must be a host
            # with it's listed interfaces
            if (switch_ip == requested_switch_ip and
                str(attr) not in defined_attributes):
                self._gather_configured_ports(
                    switch_ip, attr, switch_ifs)

        return switch_ifs

    #
    # _get_switch_interfaces()
    #
    # For a given switch, return known configured and baremetal
    # interfaces.
    #
    def _get_switch_interfaces(self, requested_switch_ip):
        """Get known baremetal and config interfaces."""

        all_switch_ifs = self._get_config_switch_interfaces(
                             requested_switch_ip)
        all_switch_ifs += self._get_known_baremetal_interfaces(
                              requested_switch_ip)
        return all_switch_ifs

    def get_switch_ips(self):
        switch_connections = []
        for switch_ip, attr in self._nexus_switches:
            if str(attr) == 'username':
                switch_connections.append(switch_ip)

        return switch_connections

    def _get_switch_nve_info(self, host_id):
        host_nve_connections = []
        for switch_ip, attr in self._nexus_switches:
            if str(attr) == str(host_id):
                host_nve_connections.append(switch_ip)

        if not host_nve_connections:
            LOG.warn(HOST_NOT_FOUND, host_id)

        return host_nve_connections

    def _configure_nve_db(self, vni, device_id, mcast_group, host_id):
        """Create the nexus NVE database entry.

        Called during update precommit port event.
        """
        host_nve_connections = self._get_switch_nve_info(host_id)
        for switch_ip in host_nve_connections:
            if not nxos_db.get_nve_vni_member_bindings(vni, switch_ip,
                                                       device_id):
                nxos_db.add_nexusnve_binding(vni, switch_ip, device_id,
                                             mcast_group)

    def _configure_nve_member(self, vni, device_id, mcast_group, host_id):
        """Add "member vni" configuration to the NVE interface.

        Called during update postcommit port event.
        """
        host_nve_connections = self._get_switch_nve_info(host_id)

        for switch_ip in host_nve_connections:

            # If configured to set global VXLAN values then
            #   If this is the first database entry for this switch_ip
            #   then configure the "interface nve" entry on the switch.
            if cfg.CONF.ml2_cisco.vxlan_global_config:
                nve_bindings = nxos_db.get_nve_switch_bindings(switch_ip)
                if len(nve_bindings) == 1:
                    LOG.debug("Nexus: create NVE interface")
                    loopback = self._nexus_switches.get(
                                        (switch_ip, 'nve_src_intf'), '0')
                    self.driver.enable_vxlan_feature(switch_ip,
                        const.NVE_INT_NUM, loopback)

            # If this is the first database entry for this (VNI, switch_ip)
            # then configure the "member vni #" entry on the switch.
            member_bindings = nxos_db.get_nve_vni_switch_bindings(vni,
                                                                  switch_ip)
            if len(member_bindings) == 1:
                LOG.debug("Nexus: add member")
                self.driver.create_nve_member(switch_ip, const.NVE_INT_NUM,
                                              vni, mcast_group)

    def _delete_nve_db(self, vni, device_id, mcast_group, host_id):
        """Delete the nexus NVE database entry.

        Called during delete precommit port event.
        """
        rows = nxos_db.get_nve_vni_deviceid_bindings(vni, device_id)
        for row in rows:
            nxos_db.remove_nexusnve_binding(vni, row.switch_ip, device_id)

    def _delete_nve_member(self, vni, device_id, mcast_group, host_id):
        """Remove "member vni" configuration from the NVE interface.

        Called during delete postcommit port event.
        """
        host_nve_connections = self._get_switch_nve_info(host_id)
        for switch_ip in host_nve_connections:

            if not nxos_db.get_nve_vni_switch_bindings(vni, switch_ip):
                self.driver.delete_nve_member(switch_ip,
                    const.NVE_INT_NUM, vni)
            if (cfg.CONF.ml2_cisco.vxlan_global_config and
                not nxos_db.get_nve_switch_bindings(switch_ip)):
                self.driver.disable_vxlan_feature(switch_ip)

    def _configure_nxos_db(self, port, vlan_id, device_id, host_id, vni,
                           is_provider_vlan):
        """Create the nexus database entry.

        Called during update precommit port event.
        """
        host_connections = self._get_port_connections(port, host_id)
        for switch_ip, intf_type, nexus_port, is_native in host_connections:
            port_id = '%s:%s' % (intf_type, nexus_port)
            try:
                nxos_db.get_nexusport_binding(port_id, vlan_id, switch_ip,
                                              device_id)
            except excep.NexusPortBindingNotFound:
                nxos_db.add_nexusport_binding(port_id, str(vlan_id), str(vni),
                                              switch_ip, device_id,
                                              is_provider_vlan,
                                              is_native)

    def _gather_config_parms(self, is_provider_vlan, vlan_id):
        """Determine vlan_name, auto_create, auto_trunk from config."""
        if is_provider_vlan:
            vlan_name = cfg.CONF.ml2_cisco.provider_vlan_name_prefix
            auto_create = cfg.CONF.ml2_cisco.provider_vlan_auto_create
            auto_trunk = cfg.CONF.ml2_cisco.provider_vlan_auto_trunk
        else:
            vlan_name = cfg.CONF.ml2_cisco.vlan_name_prefix
            auto_create = True
            auto_trunk = True
        if auto_create:
            vlan_name_max_len = (
                const.NEXUS_MAX_VLAN_NAME_LEN - len(str(vlan_id)))
            if len(vlan_name) > vlan_name_max_len:
                vlan_name = vlan_name[:vlan_name_max_len]
                LOG.warn(_LW("Nexus: truncating vlan name to %s"),
                         vlan_name)
            vlan_name = vlan_name + str(vlan_id)
        return vlan_name, auto_create, auto_trunk

    def _configure_port_binding(self, is_provider_vlan, duplicate_type,
                                is_native,
                                switch_ip, vlan_id,
                                intf_type, nexus_port, vni):
        """Conditionally calls vlan and port Nexus drivers."""

        # This implies VLAN, VNI, and Port are all duplicate.
        # Then there is nothing to configure in Nexus.
        if duplicate_type == const.DUPLICATE_PORT:
            return

        vlan_name, auto_create, auto_trunk = self._gather_config_parms(
            is_provider_vlan, vlan_id)

        # if type DUPLICATE_VLAN, don't create vlan
        if duplicate_type == const.DUPLICATE_VLAN:
            auto_create = False

        if auto_create and auto_trunk:
            LOG.debug("Nexus: create vlan %s and add to interface",
                vlan_name)
            self.driver.create_and_trunk_vlan(
                switch_ip, vlan_id, vlan_name, intf_type,
                nexus_port, vni, is_native)
        elif auto_create:
            LOG.debug("Nexus: create vlan %s", vlan_name)
            self.driver.create_vlan_segment(switch_ip, vlan_id,
                                    vlan_name, vni)
        elif auto_trunk:
            LOG.debug("Nexus: trunk vlan %s", vlan_name)
            self.driver.send_enable_vlan_on_trunk_int(
                switch_ip, vlan_id,
                intf_type, nexus_port, is_native)

    def _get_compressed_vlan_list(self, pvlan_ids):
        """Generate a compressed vlan list ready for XML using a vlan set.

        Sample Use Case:

        Input vlan set:
        --------------
        1 - s = set([11, 50, 25, 30, 15, 16, 3, 8, 2, 1])
        2 - s = set([87, 11, 50, 25, 30, 15, 16, 3, 8, 2, 1, 88])

        Returned compressed XML list:
        ----------------------------
        1 - compressed_list = ['1-3', '8', '11', '15-16', '25', '30', '50']
        2 - compressed_list = ['1-3', '8', '11', '15-16', '25', '30',
                               '50', '87-88']
        """

        if not pvlan_ids:
            return []

        pvlan_list = list(pvlan_ids)
        pvlan_list.sort()
        compressed_list = []
        begin = -1
        prev_vlan = -1
        for port_vlan in pvlan_list:
            if prev_vlan == -1:
                prev_vlan = port_vlan
            else:
                if (port_vlan - prev_vlan) == 1:
                    if begin == -1:
                        begin = prev_vlan
                    prev_vlan = port_vlan
                else:
                    if begin == -1:
                        compressed_list.append(str(prev_vlan))
                    else:
                        compressed_list.append("%d-%d" % (begin, prev_vlan))
                        begin = -1
                    prev_vlan = port_vlan

        if begin == -1:
            compressed_list.append(str(prev_vlan))
        else:
            compressed_list.append("%s-%s" % (begin, prev_vlan))
        return compressed_list

    def _restore_port_binding(self,
                             switch_ip, pvlan_ids,
                             port, is_native):
        """Restores a set of vlans for a given port."""

        if ':' in port:
            intf_type, nexus_port = port.split(':')
        else:
            intf_type, nexus_port = 'ethernet', port

        concat_vlans = ''
        compressed_vlans = self._get_compressed_vlan_list(pvlan_ids)
        for pvlan in compressed_vlans:

            if concat_vlans == '':
                concat_vlans = "%s" % pvlan
            else:
                concat_vlans += ",%s" % pvlan

            # if string starts getting a bit long, send it.
            if len(concat_vlans) >= const.CREATE_PORT_VLAN_LENGTH:
                self.driver.send_enable_vlan_on_trunk_int(
                    switch_ip, concat_vlans,
                    intf_type, nexus_port, is_native)
                concat_vlans = ''

        # Send remaining vlans if any
        if len(concat_vlans):
            self.driver.send_enable_vlan_on_trunk_int(
                    switch_ip, concat_vlans,
                    intf_type, nexus_port, is_native)

    def _restore_vxlan_entries(self, switch_ip, vlans):
        """Restore vxlan entries on a Nexus switch."""

        count = 1
        conf_str = ''
        vnsegment_sent = 0
        # At this time, this will only configure vni information when needed
        while vnsegment_sent < const.CREATE_VLAN_BATCH and vlans:
            vlan_id, vni, vlan_name = vlans.pop(0)
            # Add it to the batch
            conf_str += self.driver.get_create_vlan(
                            switch_ip, vlan_id, vni)
            if (count == const.CREATE_VLAN_SEND_SIZE):
                self.driver.send_edit_string(switch_ip, conf_str)
                vnsegment_sent += count
                conf_str = ''
                count = 1
            else:
                count += 1

        if conf_str:
            vnsegment_sent += count
            self.driver.send_edit_string(switch_ip, conf_str)
            conf_str = ''
        LOG.debug("Switch %s VLAN vn-segment replay summary: %d",
                  switch_ip, vnsegment_sent)

    def _configure_port_entries(self, port, vlan_id, device_id, host_id, vni,
                                is_provider_vlan):
        """Create a nexus switch entry.

        if needed, create a VLAN in the appropriate switch or port and
        configure the appropriate interfaces for this VLAN.

        Called during update postcommit port event.
        """
        connections = self._get_active_port_connections(port, host_id)

        # (nexus_port,switch_ip) will be unique in each iteration.
        # But switch_ip will repeat if host has >1 connection to same switch.
        # So track which switch_ips already have vlan created in this loop.
        vlan_already_created = []
        starttime = time.time()

        for switch_ip, intf_type, nexus_port, is_native in connections:

            all_bindings = nxos_db.get_nexusvlan_binding(vlan_id, switch_ip)
            previous_bindings = [row for row in all_bindings
                    if row.instance_id != device_id]
            if previous_bindings and (switch_ip in vlan_already_created):
                duplicate_type = const.DUPLICATE_VLAN
            else:
                vlan_already_created.append(switch_ip)
                duplicate_type = const.NO_DUPLICATE
            port_starttime = time.time()
            try:
                self._configure_port_binding(
                    is_provider_vlan, duplicate_type,
                    is_native,
                    switch_ip, vlan_id,
                    intf_type, nexus_port,
                    vni)
            except Exception:
                with excutils.save_and_reraise_exception():
                    self.driver.capture_and_print_timeshot(
                        port_starttime, "port_configerr",
                        switch=switch_ip)
                    self.driver.capture_and_print_timeshot(
                        starttime, "configerr",
                        switch=switch_ip)
            self.driver.capture_and_print_timeshot(
                port_starttime, "port_config",
                switch=switch_ip)
        self.driver.capture_and_print_timeshot(
            starttime, "config")

    def configure_next_batch_of_vlans(self, switch_ip):
        """Get next batch of vlans and send them to Nexus."""

        next_range = self._pop_vlan_range(
                          switch_ip, const.CREATE_VLAN_BATCH)
        if next_range:
            try:
                self.driver.set_all_vlan_states(
                    switch_ip, next_range)
            except Exception:
                with excutils.save_and_reraise_exception():
                    LOG.error(_LE("Error encountered restoring vlans "
                        "for switch %(switch_ip)s"),
                        {'switch_ip': switch_ip})
                    self._save_switch_vlan_range(switch_ip, [])

        vxlan_range = self._get_switch_vxlan_range(switch_ip)
        if vxlan_range:
            try:
                self._restore_vxlan_entries(switch_ip, vxlan_range)
            except Exception:
                with excutils.save_and_reraise_exception():
                    LOG.error(_LE("Error encountered restoring vxlans "
                        "for switch %(switch_ip)s"),
                        {'switch_ip': switch_ip})
                    self._save_switch_vxlan_range(switch_ip, [])

        # if no more vlans to restore, we're done. go active.
        if (not self._get_switch_vlan_range(switch_ip) and
            not self._get_switch_vxlan_range(switch_ip)):
            self.set_switch_ip_and_active_state(
                switch_ip, const.SWITCH_ACTIVE)
            LOG.info(_LI("Restore of Nexus switch "
                "ip %(switch_ip)s is complete"),
                {'switch_ip': switch_ip})
        else:
            LOG.debug(("Restored batch of VLANS on "
                "Nexus switch ip %(switch_ip)s"),
                {'switch_ip': switch_ip})

    def configure_switch_entries(self, switch_ip, port_bindings):
        """Create a nexus switch entry in Nexus.

        The port_bindings is sorted by vlan_id, vni, port_id.
        When there is a change in vlan_id or vni, then vlan
        data is configured in Nexus device.
        Otherwise we check if there is a change in port_id
        where we configure the port with vlan trunk config.

        Called during switch replay event.
        """
        prev_vlan = -1
        prev_vni = -1
        prev_port = None
        prev_is_native = False
        starttime = time.time()

        port_bindings.sort(key=lambda x: (x.port_id, x.vlan_id, x.vni))
        self.driver.capture_and_print_timeshot(starttime, "replay_t2_aft_sort",
                                               switch=switch_ip)

        # Let's make these lists a set to exclude duplicates
        vlans = set()
        pvlans = set()
        interface_count = 0
        duplicate_port = 0
        vlan_count = 0
        for port in port_bindings:
            if self._is_reserved_binding(port):
                continue
            vlan_name, auto_create, auto_trunk = self._gather_config_parms(
                port.is_provider_vlan, port.vlan_id)
            if port.port_id == prev_port:
                if port.vlan_id == prev_vlan and port.vni == prev_vni:
                    # Same port/Same Vlan - skip duplicate
                    duplicate_port += 1
                    continue
                else:
                    # Same port/different Vlan - track it
                    vlan_count += 1
                    if auto_create:
                        vlans.add((port.vlan_id, port.vni, vlan_name))
                    if auto_trunk:
                        pvlans.add(port.vlan_id)
            else:
                # Different port - write out interface trunk on previous port
                if prev_port:
                    interface_count += 1
                    LOG.debug("Switch %s port %s replay summary: unique vlan "
                              "count %d, duplicate port entries %d",
                              switch_ip, prev_port, vlan_count, duplicate_port)
                duplicate_port = 0
                vlan_count = 0
                if pvlans:
                    self._restore_port_binding(
                        switch_ip, pvlans, prev_port, prev_is_native)
                    pvlans.clear()
                # Start tracking new port
                if auto_create:
                    vlans.add((port.vlan_id, port.vni, vlan_name))
                if auto_trunk:
                    pvlans.add(port.vlan_id)
                prev_port = port.port_id
                prev_is_native = port.is_native

        if pvlans:
            LOG.debug("Switch %s port %s replay summary: unique vlan "
                      "count %d, duplicate port entries %d",
                      switch_ip, port.port_id, vlan_count, duplicate_port)
            self._restore_port_binding(
                switch_ip, pvlans, prev_port, prev_is_native)

        LOG.debug("Replayed total %d ports for Switch %s",
                  interface_count + 1, switch_ip)

        self.driver.capture_and_print_timeshot(starttime, "replay_part_1",
                                               switch=switch_ip)
        vlans = list(vlans)
        if vlans:
            vlans.sort()
            vlan, vni, vlan_name = vlans[0]
            if vni == 0:
                self._save_switch_vlan_range(switch_ip, vlans)
            else:
                self._save_switch_vxlan_range(switch_ip, vlans)

        self.set_switch_ip_and_active_state(
            switch_ip, const.SWITCH_RESTORE_S2)
        self.configure_next_batch_of_vlans(switch_ip)
        self.driver.capture_and_print_timeshot(starttime, "replay_part_2",
                                               switch=switch_ip)

    def _delete_nxos_db(self, unused, vlan_id, device_id, host_id, vni,
                        is_provider_vlan):
        """Delete the nexus database entry.

        Called during delete precommit port event.
        """
        try:
            rows = nxos_db.get_nexusvm_bindings(vlan_id, device_id)
            for row in rows:
                nxos_db.remove_nexusport_binding(row.port_id, row.vlan_id,
                                    row.vni, row.switch_ip, row.instance_id,
                                    row.is_provider_vlan)
        except excep.NexusPortBindingNotFound:
            return

    def _delete_switch_entry(self, port, vlan_id, device_id, host_id, vni,
                             is_provider_vlan):
        """Delete the nexus switch entry.

        By accessing the current db entries determine if switch
        configuration can be removed.

        Called during delete postcommit port event.
        """
        connections = self._get_active_port_connections(port, host_id)

        # (nexus_port,switch_ip) will be unique in each iteration.
        # But switch_ip will repeat if host has >1 connection to same switch.
        # So track which switch_ips already have vlan removed in this loop.
        vlan_already_removed = []
        for switch_ip, intf_type, nexus_port, is_native in connections:

            # if there are no remaining db entries using this vlan on this
            # nexus switch port then remove vlan from the switchport trunk.
            port_id = '%s:%s' % (intf_type, nexus_port)
            auto_create = True
            auto_trunk = True
            if is_provider_vlan:
                auto_create = cfg.CONF.ml2_cisco.provider_vlan_auto_create
                auto_trunk = cfg.CONF.ml2_cisco.provider_vlan_auto_trunk

            try:
                nxos_db.get_port_vlan_switch_binding(port_id, vlan_id,
                                                     switch_ip)
            except excep.NexusPortBindingNotFound:
                pass
            else:
                continue

            if auto_trunk:
                self.driver.disable_vlan_on_trunk_int(
                    switch_ip, vlan_id, intf_type, nexus_port,
                    is_native)

            # if there are no remaining db entries using this vlan on this
            # nexus switch then remove the vlan.
            if auto_create:
                try:
                    nxos_db.get_nexusvlan_binding(vlan_id, switch_ip)
                except excep.NexusPortBindingNotFound:
                    # Do not perform a second time on same switch
                    if switch_ip not in vlan_already_removed:
                        self.driver.delete_vlan(switch_ip, vlan_id)
                        vlan_already_removed.append(switch_ip)

    def _is_segment_nexus_vxlan(self, segment):
        return segment[api.NETWORK_TYPE] == const.TYPE_NEXUS_VXLAN

    def _get_segments(self, top_segment, bottom_segment):
        # Return vlan segment and vxlan segment (if configured).
        if top_segment is None:
            return None, None
        elif self._is_segment_nexus_vxlan(top_segment):
            return bottom_segment, top_segment
        else:
            return top_segment, None

    def _is_vm_migrating(self, context, vlan_segment, orig_vlan_segment):
        if not vlan_segment and orig_vlan_segment:
            return (context.current.get(portbindings.HOST_ID) !=
                    context.original.get(portbindings.HOST_ID))

    def _log_missing_segment(self):
        LOG.warn(_LW("Nexus: Segment is None, Event not processed."))

    def _is_valid_segment(self, segment):
        valid_segment = True
        if segment:
            if (segment[api.NETWORK_TYPE] != p_const.TYPE_VLAN or
                not self._valid_network_segment(segment)):
                LOG.warn(_LW("Nexus: Segment is an invalid type or not "
                         "supported by this driver. Network type = "
                         "%(network_type)s Physical network = "
                         "%(phy_network)s. Event not processed."),
                         {'network_type': segment[api.NETWORK_TYPE],
                          'phy_network': segment[api.PHYSICAL_NETWORK]})
                valid_segment = False
        else:
            self._log_missing_segment()
            valid_segment = False

        return valid_segment

    def _port_action_vlan(self, port, segment, func, vni):
        """Verify configuration and then process event."""

        # Verify segment.
        if not self._is_valid_segment(segment):
            return

        device_id = port.get('device_id')
        # No host_id is another indicator this is a baremetal
        # transaction
        if self._is_baremetal(port):
            host_id = ''
        else:
            host_id = port.get(portbindings.HOST_ID)
        vlan_id = segment.get(api.SEGMENTATION_ID)
        # TODO(rpothier) Add back in provider segment support.
        is_provider = False
        settings = {"vlan_id": vlan_id,
                    "device_id": device_id,
                    "host_id": host_id,
                    "is_provider": is_provider is not None}
        missing_fields = [field for field, value in settings.items()
                          if (field != 'host_id' and not value)]
        if not missing_fields:
            func(port, vlan_id, device_id, host_id, vni, is_provider)
        else:
            raise excep.NexusMissingRequiredFields(
                fields=' '.join(missing_fields))

    def _port_action_vxlan(self, port, segment, func):
        """Verify configuration and then process event."""

        # If the segment is None, just log a warning message and return.
        if segment is None:
            self._log_missing_segment()
            return

        device_id = port.get('device_id')
        mcast_group = segment.get(api.PHYSICAL_NETWORK)
        host_id = port.get(portbindings.HOST_ID)
        vni = segment.get(api.SEGMENTATION_ID)

        if vni and device_id and mcast_group and host_id:
            func(vni, device_id, mcast_group, host_id)
            return vni
        else:
            fields = "vni " if not vni else ""
            fields += "device_id " if not device_id else ""
            fields += "mcast_group " if not mcast_group else ""
            fields += "host_id" if not host_id else ""
            raise excep.NexusMissingRequiredFields(fields=fields)

    def _monitor_thread(self):
        """Periodically restarts the monitor thread."""
        with self.monitor_lock:
            self.monitor.check_connections()

        self.timer = threading.Timer(self.monitor_timeout,
                                     self._monitor_thread)
        self.timer.start()

    def _stop_monitor_thread(self):
        """Terminates the monitor thread."""
        if self.timer:
            self.timer.cancel()
            self.timer = None

    @lockutils.synchronized('cisco-nexus-portlock')
    def create_port_postcommit(self, context):
        """Create port non-database commit event."""

        # No new events are handled until replay
        # thread has put the switch in active state.
        # If a switch is in active state, verify
        # the switch is still in active state
        # before accepting this new event.
        #
        # If create_port_postcommit fails, it causes
        # other openstack dbs to be cleared and
        # retries for new VMs will stop.  Subnet
        # transactions will continue to be retried.

        port = context.current
        if self._is_supported_deviceowner(port):
            if self._is_baremetal(context.current):
                host_id = ''
                all_switches, active_switches = (
                    self._get_baremetal_switches(context.current))
            else:
                host_id = context.current.get(portbindings.HOST_ID)
                all_switches, active_switches = (
                    self._get_host_switches(host_id))

            # Verify switch is still up before replay
            # thread checks.
            verified_active_switches = []
            for switch_ip in active_switches:
                try:
                    self.driver.get_nexus_type(switch_ip)
                    verified_active_switches.append(switch_ip)
                except Exception:
                    pass

            # if host_id is valid and there is no active
            # switches remaining
            if all_switches and not verified_active_switches:
                raise excep.NexusConnectFailed(
                    nexus_host=all_switches[0], config="None",
                    exc="Create Failed: Port event can not "
                    "be processed at this time.")

    @lockutils.synchronized('cisco-nexus-portlock')
    def update_port_precommit(self, context):
        """Update port pre-database transaction commit event."""
        vlan_segment, vxlan_segment = self._get_segments(
                                        context.top_bound_segment,
                                        context.bottom_bound_segment)
        orig_vlan_segment, orig_vxlan_segment = self._get_segments(
                                        context.original_top_bound_segment,
                                        context.original_bottom_bound_segment)

        # if VM migration is occurring then remove previous database entry
        # else process update event.
        if self._is_vm_migrating(context, vlan_segment, orig_vlan_segment):
            vni = self._port_action_vxlan(context.original, orig_vxlan_segment,
                        self._delete_nve_db) if orig_vxlan_segment else 0
            self._port_action_vlan(context.original, orig_vlan_segment,
                                   self._delete_nxos_db, vni)
        else:
            if (self._is_supported_deviceowner(context.current) and
                self._is_status_active(context.current) and
                not self._is_baremetal(context.current)):
                vni = self._port_action_vxlan(context.current, vxlan_segment,
                            self._configure_nve_db) if vxlan_segment else 0
                self._port_action_vlan(context.current, vlan_segment,
                                       self._configure_nxos_db, vni)

    @lockutils.synchronized('cisco-nexus-portlock')
    def update_port_postcommit(self, context):
        """Update port non-database commit event."""
        vlan_segment, vxlan_segment = self._get_segments(
                                        context.top_bound_segment,
                                        context.bottom_bound_segment)
        orig_vlan_segment, orig_vxlan_segment = self._get_segments(
                                        context.original_top_bound_segment,
                                        context.original_bottom_bound_segment)

        # if VM migration is occurring then remove previous nexus switch entry
        # else process update event.
        if self._is_vm_migrating(context, vlan_segment, orig_vlan_segment):
            vni = self._port_action_vxlan(context.original, orig_vxlan_segment,
                        self._delete_nve_member) if orig_vxlan_segment else 0
            self._port_action_vlan(context.original, orig_vlan_segment,
                                   self._delete_switch_entry, vni)
        else:
            if (self._is_supported_deviceowner(context.current) and
                self._is_status_active(context.current)):
                if self._is_baremetal(context.current):
                    # Baremetal db entries are created here instead
                    # of precommit since a get operation to
                    # nexus device is required but blocking
                    # operation should not be done in precommit.
                    self._init_baremetal_trunk_interfaces(
                        context.current, vlan_segment, 0)
                    host_id = ''
                    all_switches, active_switches = (
                        self._get_baremetal_switches(context.current))
                else:
                    host_id = context.current.get(portbindings.HOST_ID)
                    all_switches, active_switches = (
                        self._get_host_switches(host_id))
                # if switches not active but host_id is valid
                if not active_switches and all_switches:
                    raise excep.NexusConnectFailed(
                        nexus_host=all_switches[0], config="None",
                        exc="Update Port Failed: Nexus Switch "
                        "is down or replay in progress")
                vni = self._port_action_vxlan(context.current, vxlan_segment,
                            self._configure_nve_member) if vxlan_segment else 0
                self._port_action_vlan(context.current, vlan_segment,
                                       self._configure_port_entries, vni)

    @lockutils.synchronized('cisco-nexus-portlock')
    def delete_port_precommit(self, context):
        """Delete port pre-database commit event."""
        if self._is_supported_deviceowner(context.current):
            vlan_segment, vxlan_segment = self._get_segments(
                                                context.top_bound_segment,
                                                context.bottom_bound_segment)
            vni = self._port_action_vxlan(context.current, vxlan_segment,
                             self._delete_nve_db) if vxlan_segment else 0
            self._port_action_vlan(context.current, vlan_segment,
                                   self._delete_nxos_db, vni)

    @lockutils.synchronized('cisco-nexus-portlock')
    def delete_port_postcommit(self, context):
        """Delete port non-database commit event."""
        if self._is_supported_deviceowner(context.current):
            vlan_segment, vxlan_segment = self._get_segments(
                                                context.top_bound_segment,
                                                context.bottom_bound_segment)
            vni = self._port_action_vxlan(context.current, vxlan_segment,
                             self._delete_nve_member) if vxlan_segment else 0
            self._port_action_vlan(context.current, vlan_segment,
                                   self._delete_switch_entry, vni)

    def bind_port(self, context):
        LOG.debug("Attempting to bind port %(port)s on network %(network)s",
                  {'port': context.current['id'],
                   'network': context.network.current['id']})

        #
        # if is VNIC_TYPE baremetal and all required config is intact.
        #    accept this transaction
        # otherwise check if vxlan for us
        #
        if self._supported_baremetal_transaction(context):
            return

        for segment in context.segments_to_bind:
            if self._is_segment_nexus_vxlan(segment):

                # Find physical network setting for this host.
                host_id = context.current.get(portbindings.HOST_ID)
                host_connections = self._get_port_connections(
                                       context.current,
                                       host_id)
                if not host_connections:
                    return

                for switch_ip, attr2, attr3, attr4 in host_connections:
                    physnet = self._nexus_switches.get((switch_ip, 'physnet'))
                    if physnet:
                        break
                else:
                    raise excep.PhysnetNotConfigured(host_id=host_id,
                                             host_connections=host_connections)

                # Allocate dynamic vlan segment.
                vlan_segment = {api.NETWORK_TYPE: p_const.TYPE_VLAN,
                                api.PHYSICAL_NETWORK: physnet}
                context.allocate_dynamic_segment(vlan_segment)

                # Retrieve the dynamically allocated segment.
                # Database has provider_segment dictionary key.
                network_id = context.current['network_id']
                dynamic_segment = ml2_db.get_dynamic_segment(
                                    db_api.get_session(), network_id, physnet)

                # Have other drivers bind the VLAN dynamic segment.
                if dynamic_segment:
                    context.continue_binding(segment[api.ID],
                                             [dynamic_segment])
                else:
                    raise excep.NoDynamicSegmentAllocated(
                                        network_id=network_id, physnet=physnet)
            else:
                LOG.debug("No binding required for segment ID %(id)s, "
                          "segment %(seg)s, phys net %(physnet)s, and "
                          "network type %(nettype)s",
                          {'id': segment[api.ID],
                           'seg': segment[api.SEGMENTATION_ID],
                           'physnet': segment[api.PHYSICAL_NETWORK],
                           'nettype': segment[api.NETWORK_TYPE]})
