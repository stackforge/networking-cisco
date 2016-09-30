# Copyright 2016 Cisco Systems, Inc.  All rights reserved.
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

# =============================================================================
# Set tenant network ip route with interface
# Syntax: ip route vrf <vrf-name> <tenant subnet> <mask> <interface> <next hop>
# eg:
#   $(config)ip route vrf nrouter-e7d4y5 40.0.0.0 255.255.255.0 pc.4 1.0.10.255
# =============================================================================
SET_TENANT_ROUTE_WITH_INTF = """
<config>
        <cli-config-data>
            <cmd>ip route vrf %s %s %s %s %s</cmd>
        </cli-config-data>
</config>
"""

# =============================================================================
# Remove tenant network ip route
# Syntax: ip route vrf <vrf-name> <tenant subnet> <mask> <interface> <next hop>
# eg:
#   $(config)ip route vrf nrouter-e7d4y5 40.0.0.0 255.255.255.0 pc.4 1.0.10.255
# =============================================================================
REMOVE_TENANT_ROUTE_WITH_INTF = """
<config>
        <cli-config-data>
            <cmd>no ip route vrf %s %s %s %s %s</cmd>
        </cli-config-data>
</config>
"""

# =============================================================================
# Set default ipv6 route with interface
# Syntax: ipv6 route vrf <vrf-name> ::/0 <interface> nexthop-vrf default
# eg:
# $(config)ipv6 route vrf nrouter-e7d4y5 ::/0 po10.304 nexthop-vrf default
# =============================================================================
# ToDo(Hareesh): Seems unused, remove commented below after testing
# DEFAULT_ROUTE_V6_WITH_INTF_CFG = 'ipv6 route vrf %s ::/0 %s %s'

SET_TENANT_ROUTE_V6_WITH_INTF = """
<config>
        <cli-config-data>
            <cmd>ipv6 route vrf %s ::/0 %s nexthop-vrf default</cmd>
        </cli-config-data>
</config>
"""

# ============================================================================
# Remove default ipv6 route
# Syntax: no ipv6 route vrf <vrf-name> ::/0 <interface> nexthop-vrf default
# eg:
# $(config)no ipv6 route vrf nrouter-e7d4y5 ::/0 po10.304 nexthop-vrf default
# ============================================================================
REMOVE_TENANT_ROUTE_V6_WITH_INTF = """
<config>
        <cli-config-data>
            <cmd>no ipv6 route vrf %s ::/0 %s nexthop-vrf default</cmd>
        </cli-config-data>
</config>
"""

# ===========================================================================
# Set Static source translation on an interface
# Syntax: ip nat inside source static <fixed_ip> <floating_ip>
# .......vrf <vrf_name>
# eg: $(config)ip nat inside source static 192.168.0.1 121.158.0.5
#    ..........vrf nrouter-e7d4y5
# ==========================================================================
SET_STATIC_SRC_TRL_NO_VRF_MATCH = """
<config>
        <cli-config-data>
            <cmd>ip nat inside source static %s %s vrf %s</cmd>
        </cli-config-data>
</config>
"""

# ===========================================================================
# Remove Static source translation on an interface
# Syntax: no ip nat inside source static <fixed_ip> <floating_ip>
# .......vrf <vrf_name>
# eg: $(config)no ip nat inside source static 192.168.0.1 121.158.0.5
#    ..........vrf nrouter-e7d4y5
# ==========================================================================
REMOVE_STATIC_SRC_TRL_NO_VRF_MATCH = """
<config>
        <cli-config-data>
            <cmd>no ip nat inside source static %s %s vrf %s</cmd>
        </cli-config-data>
</config>
"""

# =======================================================
# Add secondary IP
# $(config)interface GigabitEthernet 2.500
# $(config)ip address 192.168.0.1 255.255.255.0 secondary
# =======================================================
ADD_SECONDARY_IP = """
<config>
        <cli-config-data>
            <cmd>interface %s</cmd>
            <cmd>ip address %s %s secondary</cmd>
        </cli-config-data>
</config>
"""

# =======================================================
# Remove secondary IP
# $(config)interface GigabitEthernet 2.500
# $(config)no ip address 192.168.0.1 255.255.255.0 secondary
# =======================================================
REMOVE_SECONDARY_IP = """
<config>
        <cli-config-data>
            <cmd>interface %s</cmd>
            <cmd>no ip address %s %s secondary</cmd>
        </cli-config-data>
</config>
"""

# =============================================================================
# Generic interface configuration command
# Syntax: completely defined by parameter
# =============================================================================
SET_INTERFACE_CONFIG = """
<config>
        <cli-config-data>
            <cmd>interface %s</cmd>
            <cmd>%s</cmd>
        </cli-config-data>
</config>
"""

# =============================================================================
# Generic interface configuration remove command
# Syntax: completely defined by parameter
# =============================================================================
REMOVE_INTERFACE_CONFIG = """
<config>
        <cli-config-data>
            <cmd>interface %s</cmd>
            <cmd>no %s</cmd>
        </cli-config-data>
</config>
"""

GLOBAL_CONFIG_PREFIX = """
<config>
        <cli-config-data>
"""
GLOBAL_CONFIG_POSTFIX = """
        </cli-config-data>
</config>
"""
# =============================================================================
# Generic global configuration command
# Syntax: completely defined by parameter
# =============================================================================
SET_GLOBAL_CONFIG = """
            <cmd>%s</cmd>
"""

# =============================================================================
# Generic global configuration remove command
# Syntax: completely defined by parameter
# =============================================================================
REMOVE_GLOBAL_CONFIG = """
            <cmd>no %s</cmd>
"""

# =============================================================================
# VRF definition -- used only for checking existence in the
# running config (note absence of <config> and <cli-config-data> elements).
# Syntax: completely defined by parameter
# =============================================================================
VRF_CONFIG = """vrf definition %s"""
