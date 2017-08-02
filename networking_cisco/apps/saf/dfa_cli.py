# Copyright 2014 Cisco Systems, Inc.
# All Rights Reserved.
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

"""CLI module for fabric enabler."""
import argparse
import platform
import re
import sys
import time

from oslo_serialization import jsonutils
from oslo_utils import encodeutils

from cliff import app
from cliff import commandmanager
from cliff.lister import Lister
from cliff.show import ShowOne

from dfa.common import config
from dfa.common import constants
from dfa.common import rpc

try:
    from neutronclient._i18n import _
except ImportError:
    from neutronclient.i18n import _

DFA_API_VERSION = '2.0'


class ListNetwork(Lister):
    """List all the networks from Fabric Enabler. """

    sorting_support = True

    def get_parser(self, prog_name):
        parser = super(ListNetwork, self).get_parser(prog_name)
        parser.add_argument('--name',
                            help=_('Filter networks based on Network Name.'))
        parser.add_argument('--tenant_id',
                            help=_('Filter networks based on Tenant ID.'))
        parser.add_argument('--tenant_name',
                            help=_('Filter networks based on Tenant Name.'))
        parser.add_argument('-D', '--show-details',
                            help=argparse.SUPPRESS,
                            action='store_true',
                            default=False, )
        return parser

    def cli_get_networks(self, parsed_args):
        """Get all networks for a tenant from the Fabric Enabler. """

        context = {}
        msg = self.app.clnt.make_msg('cli_get_networks',
                                     context, msg=parsed_args)
        try:
            return self.app.clnt.call(msg)
        except (rpc.MessagingTimeout, rpc.RPCException, rpc.RemoteError) as e:
            print("RPC: Request to Enabler failed. Reason: %s" % e.message)

    def take_action(self, parsed_args):
        resp = self.cli_get_networks({'id': None,
                                      'name': parsed_args.name,
                                      'tenant_name': parsed_args.tenant_name,
                                      'tenant_id': parsed_args.tenant_id})
        if parsed_args.show_details:
            columns = ['Name', 'Segment ID', 'Vlan', 'Mobility-Domain',
                       'Config Profile', 'Tenant ID', 'Result',
                       'Failure Reason']
            data = [(r.get('name'), r.get('seg'), r.get('vlan'), r.get('md'),
                     r.get('cfgp'), r.get('tenant_id'), r.get('result'),
                     r.get('reason')) for r in resp]
        else:
            columns = ['ID', 'Name', 'Segment ID', 'Vlan', 'Mobility-Domain',
                       'Result', 'Failure Reason']
            data = [(r.get('net_id'), r.get('name'), r.get('seg'),
                     r.get('vlan'), r.get('md'),
                     r.get('result'), r.get('reason')) for r in resp]

        return (columns, data)


class ListProfile(Lister):
    """List all the profiles from Fabric Enabler. """

    sorting_support = True

    def get_parser(self, prog_name):
        parser = super(ListProfile, self).get_parser(prog_name)
        parser.add_argument('--name',
                            help=_('Filter profiles based on Profile Name.'))
        return parser

    def get_config_profiles_detail(self):
        """Get all config Profiles details from the Fabric Enabler. """

        context = {}
        args = jsonutils.dumps({})
        msg = self.app.clnt.make_msg('get_config_profiles_detail',
                                     context, msg=args)
        try:
            resp = self.app.clnt.call(msg)
            return resp
        except (rpc.MessagingTimeout, rpc.RPCException, rpc.RemoteError) as e:
            print("RPC: Request to Enabler failed. Reason: %s" % e.message)

    def take_action(self, parsed_args):
        columns = ['Profile Name', 'Profile Type']

        resp = self.get_config_profiles_detail()

        if parsed_args.name:
            data = [(p.get('profileName'), p.get('profileType')) for p in resp
                    if p.get('profileName') == parsed_args.name]
        else:
            data = [(p.get('profileName'), p.get('profileType')) for p in resp]

        return (columns, data)


class ListInstance(Lister):
    """List all the instances from Fabric Enabler. """

    sorting_support = True

    def get_parser(self, prog_name):
        parser = super(ListInstance, self).get_parser(prog_name)
        parser.add_argument('--name',
                            help=_('Filter instances based on Instance Name.'))
        parser.add_argument('--network_name',
                            help=_('Filter instances based on Network Name.'))
        parser.add_argument('--tenant_id',
                            help=_('Filter instances based on Tenant Id.'))
        parser.add_argument('--tenant_name',
                            help=_('Filter instances based on Tenant Name.'))
        parser.add_argument('--host',
                            help=_('Filter instances based on Host Name.'))
        parser.add_argument('--seg_id', type=int,
                            help=_('Filter instances based on Segment id.'))
        parser.add_argument('--vdp_vlan', type=int,
                            help=_('Filter instances based on Link Local'
                                   'Vlan.'))
        parser.add_argument('--local_vlan', type=int,
                            help=_('Filter instances based on Server Local'
                                   'Vlan.'))
        parser.add_argument('--port_id',
                            help=argparse.SUPPRESS)
        parser.add_argument('-D', '--show-details',
                            help=argparse.SUPPRESS,
                            action='store_true',
                            default=False, )
        return parser

    def cli_get_instances(self, parsed_args):
        """Get all instances from the Fabric Enabler. """

        context = {}
        msg = self.app.clnt.make_msg('cli_get_instances',
                                     context, msg=parsed_args)
        try:
            resp = self.app.clnt.call(msg)
            return resp
        except (rpc.MessagingTimeout, rpc.RPCException, rpc.RemoteError) as e:
            print("RPC: Request to Enabler failed. Reason: %s" % e.message)

    def take_action(self, parsed_args):
        resp = self.cli_get_instances({'name': parsed_args.name,
                                       'network_name':
                                           parsed_args.network_name,
                                       'tenant_id': parsed_args.tenant_id,
                                       'tenant_name': parsed_args.tenant_name,
                                       'seg_id': parsed_args.seg_id,
                                       'vdp_vlan': parsed_args.vdp_vlan,
                                       'local_vlan': parsed_args.local_vlan,
                                       'host': parsed_args.host,
                                       'port': parsed_args.port_id,
                                       'detail': parsed_args.show_details})

        if parsed_args.show_details:
            columns = ['Name', 'Mac', 'IP', 'Host', 'Segmentation Id',
                       'Link Local Vlan', 'Local Vlan', 'Result',
                       'Failure Reason']
            data = [(r.get('name'), r.get('mac'), r.get('ip'),
                     r.get('host'), r.get('seg'), r.get('vdp'),
                     r.get('local'), r.get('result'),
                     r.get('reason')) for r in resp]
        else:
            columns = ['Port ID', 'Name', 'IP', 'Segmentation ID', 'VDP Vlan',
                       'Local Vlan', 'Result', 'Failure Reason']
            data = [(r.get('port'), r.get('name'), r.get('ip'), r.get('seg'),
                     r.get('vdp'), r.get('local'),
                     r.get('result'), r.get('reason')) for r in resp]

        return (columns, data)


class ListProject(Lister):
    """List all the projects from Fabric Enabler. """

    sorting_support = True

    def get_parser(self, prog_name):
        parser = super(ListProject, self).get_parser(prog_name)
        parser.add_argument('--tenant_name',
                            help=_('Filter projects based on Tenant Name.'))
        parser.add_argument('--tenant_id',
                            help=_('Filter projects based on Tenant ID.'))
        return parser

    def cli_get_projects(self, parsed_args):
        """Get all projects from the Fabric Enabler. """

        context = {}
        msg = self.app.clnt.make_msg('cli_get_projects',
                                     context, msg=parsed_args)
        try:
            resp = self.app.clnt.call(msg)
            return resp
        except (rpc.MessagingTimeout, rpc.RPCException, rpc.RemoteError) as e:
            print("RPC: Request to Enabler failed. Reason: %s" % e.message)

    def take_action(self, parsed_args):
        columns = ['Project ID', 'Name', 'DC ID', 'Result', 'Failure Reason']

        resp = self.cli_get_projects({'name': parsed_args.tenant_name,
                                      'tenant_id': parsed_args.tenant_id})
        return (columns, resp)


class ListAgent(Lister):
    """List all agents from the Fabric Enabler. """

    sorting_support = True

    def get_parser(self, prog_name):
        parser = super(ListAgent, self).get_parser(prog_name)
        parser.add_argument('--name',
                            help=_('Filter agents based on Host Name.'))
        return parser

    def get_agents_details(self, parsed_args):
        """Get all agents from the Fabric Enabler. """

        context = {}
        args = jsonutils.dumps({})
        msg = self.app.clnt.make_msg('get_agents_details',
                                     context, msg=args)
        try:
            resp = self.app.clnt.call(msg)
            return resp
        except (rpc.MessagingTimeout, rpc.RPCException, rpc.RemoteError) as e:
            print("RPC: Request to Enabler failed. Reason: %s" % e.message)

    def take_action(self, parsed_args):
        columns = ['Host', 'Uplink Interface', 'Created', 'HeartBeat',
                   'Status']

        resp = self.get_agents_details({'host': parsed_args.name})
        data = [(r.get('host'), jsonutils.loads(r.get('config')).get('uplink'),
                 r.get('created').replace('T', ' ')[:-7],
                 r.get('heartbeat').replace('T', ' ')[:-7],
                 r.get('agent_status')) for r in resp]
        return (columns, data)


class ShowNetwork(ShowOne):
    """Prints details of one network from Fabric Enabler. """

    def get_parser(self, prog_name):
        parser = super(ShowNetwork, self).get_parser(prog_name)
        parser.add_argument('NETWORK',
                            help=_('ID or name of network to look up.'))
        return parser

    def cli_get_networks(self, parsed_args):
        """Get all networks for a tenant from the Fabric Enabler. """

        context = {}
        msg = self.app.clnt.make_msg('cli_get_networks',
                                     context, msg=parsed_args)
        try:
            resp = self.app.clnt.call(msg)
            return resp
        except (rpc.MessagingTimeout, rpc.RPCException, rpc.RemoteError) as e:
            print("RPC: Request to Enabler failed. Reason: %s" % e.message)

    def take_action(self, parsed_args):
        HEX_ELEM = '[0-9A-Fa-f]'
        UUID_PATTERN = '-'.join([HEX_ELEM + '{8}', HEX_ELEM + '{4}',
                                 HEX_ELEM + '{4}', HEX_ELEM + '{4}',
                                 HEX_ELEM + '{12}'])
        match = re.match(UUID_PATTERN, parsed_args.NETWORK)
        net_id = None
        name = None
        if match:
            net_id = parsed_args.NETWORK
        else:
            name = parsed_args.NETWORK
        resp = self.cli_get_networks({'id': net_id, 'name': name,
                                      'tenant_id': None})
        columns = ('Network ID', 'Name', 'Segment ID', 'Vlan',
                   'Mobility-Domain', 'Config Profile', 'Tenant ID',
                   'Tenant Name', 'Source', 'Result', 'Failure Reason')
        data = [(r.get('net_id'), r.get('name'), r.get('seg'), r.get('vlan'),
                r.get('md'), r.get('cfgp'), r.get('tenant_id'),
                r.get('tenant_name'), r.get('source'), r.get('result'),
                r.get('reason')) for r in resp]

        if len(data) > 1:
            print(("Multiple Records found with the name: ") +
                  parsed_args.NETWORK + (", displaying first record"))

        if data:
            return (columns, data[0])
        print("Unable to find network with name or id: " + parsed_args.NETWORK)
        return (columns, data)


class ShowProfile(ShowOne):
    """Prints details of one profile from Fabric Enabler. """

    def get_parser(self, prog_name):
        parser = super(ShowProfile, self).get_parser(prog_name)
        parser.add_argument('name',
                            help=_('Filter profiles based on Profile Name.'))
        parser.add_argument('type',
                            help=_('Filter profile based on Profile Type.'))
        return parser

    def get_per_config_profile_detail(self, parsed_args):
        """Get a config Profile details from the Fabric Enabler. """

        context = {}
        args = jsonutils.dumps(parsed_args)
        msg = self.app.clnt.make_msg('get_per_config_profile_detail',
                                     context, msg=args)
        try:
            resp = self.app.clnt.call(msg)
            return resp
        except (rpc.MessagingTimeout, rpc.RPCException, rpc.RemoteError) as e:
            print("RPC: Request to Enabler failed. Reason: %s" % e.message)

    def take_action(self, parsed_args):
        columns = ['Profile Name', 'Profile Type', 'Forwarding Mode',
                   'Description', 'Commands']

        resp = self.get_per_config_profile_detail({'profile': parsed_args.name,
                                                   'ftype': parsed_args.type})
        data = []
        if resp:
            data = [resp.get('profileName'), resp.get('profileType'),
                    resp.get('forwardingMode'), resp.get('description'),
                    resp.get('configCommands').replace('\r', '\n')]
        return (columns, data)


class ShowInstance(ShowOne):
    """Prints details of one instance from Fabric Enabler. """

    def get_parser(self, prog_name):
        parser = super(ShowInstance, self).get_parser(prog_name)
        parser.add_argument('INSTANCE',
                            help=_('Port ID or Name of instance to look up.'))
        return parser

    def cli_get_instances(self, parsed_args):
        """Get an instances for a name from the Fabric Enabler. """

        context = {}
        msg = self.app.clnt.make_msg('cli_get_instances',
                                     context, msg=parsed_args)
        try:
            resp = self.app.clnt.call(msg)
            return resp
        except (rpc.MessagingTimeout, rpc.RPCException, rpc.RemoteError) as e:
            print("RPC: Request to Enabler failed. Reason: %s" % e.message)

    def take_action(self, parsed_args):
        HEX_ELEM = '[0-9A-Fa-f]'
        UUID_PATTERN = '-'.join([HEX_ELEM + '{8}', HEX_ELEM + '{4}',
                                 HEX_ELEM + '{4}', HEX_ELEM + '{4}',
                                 HEX_ELEM + '{12}'])
        match = re.match(UUID_PATTERN, parsed_args.INSTANCE)
        port_id = None
        name = None
        if match:
            port_id = parsed_args.INSTANCE
        else:
            name = parsed_args.INSTANCE

        resp = self.cli_get_instances({'name': name,
                                       'port': port_id})
        columns = ['ID', 'Name', 'Mac', 'IP', 'Host', 'Segmentation Id',
                   'Port ID', 'Network ID', 'Network Name', 'Link Local Vlan',
                   'Local Vlan', 'Tenant Name', 'Result', 'Failure Reason']
        data = [(r.get('id'), r.get('name'), r.get('mac'),
                 r.get('ip'), r.get('host'), r.get('seg'),
                 r.get('port'), r.get('net_id'), r.get('net_name'),
                 r.get('vdp'), r.get('local'), r.get('tenant_name'),
                 r.get('result'), r.get('reason')) for r in resp]

        if len(data) > 1:
            print(("Multiple Records found with the name: ") +
                  parsed_args.INSTANCE + (", displaying first record"))

        if data:
            return (columns, data[0])
        print(("Unable to find instance with name or portid: ") +
              parsed_args.INSTANCE)
        return (columns, data)


class ShowAgent(ShowOne):
    """Prints details of one agent from Fabric Enabler. """

    def get_parser(self, prog_name):
        parser = super(ShowAgent, self).get_parser(prog_name)
        parser.add_argument('host',
                            help=_('Filter agents based on Host Name.'))
        return parser

    def get_agent_details_per_host(self, parsed_args):
        """Get all agents from the Fabric Enabler. """

        context = {}
        args = jsonutils.dumps(parsed_args)
        msg = self.app.clnt.make_msg('get_agent_details_per_host',
                                     context, msg=args)
        try:
            resp = self.app.clnt.call(msg)
            return resp
        except (rpc.MessagingTimeout, rpc.RPCException, rpc.RemoteError) as e:
            print("RPC: Request to Enabler failed. Reason: %s" % e.message)

    def take_action(self, parsed_args):
        columns = ['Name', 'Created At', 'Heartbeat', 'veth Interface',
                   'Member Ports', 'Uplink Port', 'Remote Port',
                   'Bond Interface', 'Remote Chassis Mac', 'Remote Mgmt IP',
                   'Remote EVB Mode', 'Remote System Name', 'Remote System']

        r = self.get_agent_details_per_host({'host': parsed_args.host})

        data = []
        if not r:
            return (columns, data)

        r = r[0]
        cfg = jsonutils.loads(r.get('config'))
        topo = cfg.get('topo')
        data = [r.get('host'), r.get('created').replace('T', ' ')[:-7],
                r.get('heartbeat').replace('T', ' ')[:-7],
                cfg.get('veth_intf'), cfg.get('memb_ports'),
                cfg.get('uplink')]

        topology = []
        for key in topo.keys():
            intf = topo.get(key)
            if not intf.get('remote_evb_cfgd'):
                continue
            topology = [intf.get('remote_port'), intf.get('bond_intf'),
                        intf.get('remote_chassis_id_mac'),
                        intf.get('remote_mgmt_addr'),
                        intf.get('remote_evb_mode'),
                        intf.get('remote_system_name'),
                        intf.get('remote_system_desc')]

        data = data + topology
        return (columns, data)


class FabricSummary(ShowOne):
    """Prints details of the fabric. """

    def get_fabric_summary(self):
        """Get fabric details from the Fabric Enabler. """

        context = {}
        msg = self.app.clnt.make_msg('get_fabric_summary', context, msg={})
        try:
            resp = self.app.clnt.call(msg)
            return resp
        except (rpc.MessagingTimeout, rpc.RPCException, rpc.RemoteError) as e:
            print("RPC: Request to Enabler failed. Reason: %s" % e.message)

    def take_action(self, parsed_args):
        columns = ['Fabric Enabler Version', 'DCNM Version', 'DCNM IP',
                   'Switch Type', 'Fabric Type', 'Fabric ID',
                   'Segment ID Range']

        resp = self.get_fabric_summary()
        data = [r.get('value') for r in resp]
        return (columns, data)


class AssociateProfile(ShowOne):
    """Associate configuration profile to a network. """

    def get_parser(self, prog_name):
        parser = super(AssociateProfile, self).get_parser(prog_name)
        parser.add_argument('profile',
                            help=_('Profile name to associate with network.'))
        parser.add_argument('network_id',
                            help=_('Network ID with which profile need to be \
                                    attached.'))
        return parser

    def associate_profile_with_network(self, network):
        context = {}
        args = jsonutils.dumps(network)
        msg = self.app.clnt.make_msg('associate_profile_with_network', context,
                                     msg=args)
        try:
            resp = self.app.clnt.call(msg)
            return resp
        except (rpc.MessagingTimeout, rpc.RPCException, rpc.RemoteError) as e:
            print("RPC: Associate request to Enabler failed. Reason: %s" %
                  e.message)

    def cli_get_networks(self, parsed_args):
        """Get all networks for a tenant from the Fabric Enabler. """

        context = {}
        msg = self.app.clnt.make_msg('cli_get_networks',
                                     context, msg=parsed_args)
        try:
            resp = self.app.clnt.call(msg)
            return resp
        except (rpc.MessagingTimeout, rpc.RPCException, rpc.RemoteError):
            print("RPC: Get request to Enabler failed.")

    def take_action(self, parsed_args):
        self.associate_profile_with_network({'id': parsed_args.network_id,
                                             'cfgp': parsed_args.profile,
                                             'name': None,
                                             'tenant_id': None})
        time.sleep(3)
        net_resp = self.cli_get_networks({'id': parsed_args.network_id,
                                          'name': None,
                                          'tenant_id': None})
        columns = ('Network ID', 'Name', 'Segment ID', 'Vlan',
                   'Mobility-Domain', 'Config Profile', 'Tenant ID',
                   'Result', 'Failure Reason')
        data = [(r.get('net_id'), r.get('name'), r.get('seg'), r.get('vlan'),
                r.get('md'), r.get('cfgp'), r.get('tenant_id'),
                r.get('result'), r.get('reason')) for r in net_resp
                if r.get('net_id') == parsed_args.network_id]
        if data:
            return (columns, data[0])
        return (columns, data)


class EnablerVersion(ShowOne):
    """Prints nexus fabric enabler version. """

    def take_action(self, parsed_args):
        return (['Fabric Enabler Version'], [constants.VERSION])


COMMAND_V2 = {
    'version': EnablerVersion,
    'fabric-summary': FabricSummary,
    'associate-profile': AssociateProfile,
    'network-list': ListNetwork,
    'network-show': ShowNetwork,
    'profile-list': ListProfile,
    'profile-show': ShowProfile,
    'instance-list': ListInstance,
    'instance-show': ShowInstance,
    'project-list': ListProject,
    'agent-list': ListAgent,
    'agent-show': ShowAgent,
}

COMMANDS = {'2.0': COMMAND_V2}


class DFAShell(app.App):

    def __init__(self):
        super(DFAShell, self).__init__(
            description=__doc__.strip(),
            version=DFA_API_VERSION,
            command_manager=commandmanager.CommandManager('dfa.cli'), )
        self.commands = COMMANDS
        for k, v in self.commands[DFA_API_VERSION].items():
            self.command_manager.add_command(k, v)

        # Pop the 'complete' to correct the outputs of 'help'.
        self.command_manager.commands.pop('complete')

    def initialize_app(self, argv):
        super(DFAShell, self).initialize_app(argv)
        sys.argv = sys.argv[:3]
        self.ctl_host = platform.node()
        self._cfg = config.CiscoDFAConfig().cfg
        url = self._cfg.dfa_rpc.transport_url % (
            {'ip': self.ctl_host})
        self.clnt = rpc.DfaRpcClient(url, constants.DFA_SERVER_QUEUE,
                                     exchange=constants.DFA_EXCHANGE)
        return self.clnt


def dfa_cli(argv=sys.argv[1:]):
    try:
        sys.argv.insert(1, '--config-file')
        sys.argv.insert(2, '/etc/saf/enabler_conf.ini')

        return DFAShell().run(
            list(map(encodeutils.safe_decode, argv)))
    except KeyboardInterrupt:
        print("... terminating Fabric Enabler client")
        return 130
    except Exception as e:
        print(e)
        return 1


if __name__ == "__main__":
    sys.exit(dfa_cli(sys.argv[1:]))
