import networking_cisco.plugins.ml2.drivers.cisco.nexus.config

def list_ml2_cisco_conf_opts():
    return [('ml2_cisco', networking_cisco.plugins.ml2.drivers.cisco.nexus.config.ml2_cisco_opts),
            ('ml2_mech_cisco_nexus:<ip>', networking_cisco.plugins.ml2.drivers.cisco.nexus.config.nexus_sub_opts)]
