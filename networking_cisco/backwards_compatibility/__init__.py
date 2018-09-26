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

from neutron.plugins.ml2.drivers import type_tunnel

from networking_cisco.backwards_compatibility import neutron_version as nv

# FIXME(sambetts) We should remove cases where people are using bc.<neutron
# version> so that we don't need to do this.
from networking_cisco.backwards_compatibility.neutron_version import *  # noqa

# FIXME(sambetts) We should remove cases where people are using bc.constants
# instead of importing constants properly so we don't need to do this.
from networking_cisco.backwards_compatibility import constants  # noqa

# Some constants and verifier functions have been deprecated but are still
# used by earlier releases of neutron. In order to maintain
# backwards-compatibility with stable/mitaka this will act as a translator
# that passes constants and functions according to version number.


if nv.NEUTRON_VERSION >= nv.NEUTRON_NEWTON_VERSION:
    from neutron.conf import common as base_config
    from neutron_lib.api import validators
    from neutron_lib.db import model_base
    is_attr_set = validators.is_attr_set
    validators = validators.validators
    HasProject = model_base.HasProject
else:
    from neutron.api.v2 import attributes as _attributes
    from neutron.common import config as base_config
    is_attr_set = _attributes.is_attr_set
    validators = _attributes.validators


if nv.NEUTRON_VERSION >= nv.NEUTRON_OCATA_VERSION:
    from neutron.agent.common import utils as agent_utils
    from neutron.db import api as db_api
    from neutron.db.models import agent as agent_model
    from neutron.db.models import l3 as l3_models
    from neutron.db.models import l3agent as rb_model
    from neutron.db import segments_db
    from neutron.objects import trunk as trunk_objects
    from neutron.services.trunk import constants as trunk_consts
    from neutron.services.trunk.drivers import base as trunk_base
    from neutron_lib.api.definitions import portbindings
    from neutron_lib.api.definitions import provider_net as providernet
    from neutron_lib.api import extensions
    from neutron_lib.plugins import directory
    from neutron_lib.services import base as service_base
    from neutron_lib.utils import helpers as common_utils

    try:
        from neutron import context
    except ImportError:
        from neutron_lib import context

    get_plugin = directory.get_plugin
    VXLAN_TUNNEL_TYPE = type_tunnel.ML2TunnelTypeDriver
    Agent = agent_model.Agent
    RouterPort = l3_models.RouterPort
    Router = l3_models.Router

    def get_context():
        return context.Context()

    def get_db_ref(context):
        return context

    def get_tunnel_session(context):
        return context.session

    def get_novaclient_images(nclient):
        return nclient.glance

    def get_reader_session():
        return lib_db_api.get_reader_session()

    def get_writer_session():
        return lib_db_api.get_writer_session()

    is_agent_down = agent_utils.is_agent_down

else:
    from networking_cisco.services.trunk import (  # noqa
        trunkstubs as trunk_objects)  # noqa
    from networking_cisco.services.trunk import (  # noqa
        trunkstubs as trunk_consts)  # noqa
    from networking_cisco.services.trunk import (  # noqa
        trunkstubs as trunk_base)  # noqa

    from neutron.api import extensions  # noqa
    from neutron.api.v2 import attributes as attr
    from neutron.common import utils as common_utils  # noqa
    from neutron import context
    from neutron.db import agents_db
    from neutron.db import api as db_api
    from neutron.db import l3_agentschedulers_db as rb_model  # noqa
    from neutron.db import l3_db
    from neutron.db import model_base  # noqa
    from neutron.extensions import portbindings  # noqa
    from neutron.extensions import providernet  # noqa
    from neutron import manager
    from neutron.plugins.ml2 import db as segments_db  # noqa
    from neutron.services import service_base  # noqa
    import sqlalchemy as sa
    from sqlalchemy.ext import declarative
    from sqlalchemy import orm

    class HasTenant(object):

        project_id = sa.Column(sa.String(attr.TENANT_ID_MAX_LEN), index=True)

        def get_tenant_id(self):
            return self.project_id

        def set_tenant_id(self, value):
            self.project_id = value

        @declarative.declared_attr
        def tenant_id(cls):
            return orm.synonym(
                'project_id',
                descriptor=property(cls.get_tenant_id, cls.set_tenant_id))

    def get_plugin(service=None):
        if service is None:
            return manager.NeutronManager.get_plugin()
        else:
            return manager.NeutronManager.get_service_plugins().get(service)

    HasProject = HasTenant
    VXLAN_TUNNEL_TYPE = type_tunnel.TunnelTypeDriver
    Agent = agents_db.Agent
    RouterPort = l3_db.RouterPort
    Router = l3_db.Router

    def get_context():
        return context.Context(user_id=None, tenant_id=None)

    def get_db_ref(context):
        return db_api.get_session()

    def get_tunnel_session(context):
        return context

    def get_novaclient_images(nclient):
        return nclient.images

    def get_reader_session():
        return lib_db_api.get_session()

    def get_writer_session():
        return lib_db_api.get_session()

    is_agent_down = agents_db.AgentDbMixin.is_agent_down

if nv.NEUTRON_VERSION >= nv.NEUTRON_PIKE_VERSION:
    from neutron.conf.agent import common as config
    from neutron.db._resource_extend import extends
    from neutron.db._resource_extend import get_funcs  # noqa
    from neutron.db._resource_extend import has_resource_extenders  # noqa
    from neutron_lib.api.definitions import dns
    from neutron_lib.api.definitions import provider_net

    def auto_schedule_routers(self, hosts, r_ids):
        self.l3_plugin.auto_schedule_routers(self.adminContext, hosts)
else:
    from neutron.agent.common import config  # noqa
    from neutron.extensions import dns  # noqa
    from neutron.extensions import providernet as provider_net  # noqa

    def auto_schedule_routers(self, hosts, r_ids):
        self.l3_plugin.auto_schedule_routers(self.adminContext, hosts, r_ids)

    def has_resource_extenders(klass):
        return klass

    def extends(resources):
        def decorator(method):
            return method

        return decorator

if nv.NEUTRON_VERSION >= nv.NEUTRON_QUEENS_VERSION:
    # Newer than queens
    from neutron.conf.agent import common as neutron_agent_conf
    from neutron.conf.plugins.ml2 import config as ml2_config
    from neutron_lib.api.definitions import dns as dns_const
    from neutron_lib.api.definitions import external_net as exnet_const
    from neutron_lib.api.definitions import extraroute as extraroute_const
    from neutron_lib.api.definitions import l3 as l3_const
    from neutron_lib.api import faults as cb_faults
    from neutron_lib.callbacks import events as cb_events
    from neutron_lib.callbacks import registry as cb_registry
    from neutron_lib.callbacks import resources as cb_resources
    from neutron_lib.exceptions import agent as agent_exceptions
    from neutron_lib.exceptions import l3 as l3_exceptions
    from neutron_lib.plugins.ml2 import api as ml2_api
    from neutron_lib.utils import runtime as runtime_utils
    extraroute_const.EXTENDED_ATTRIBUTES_2_0 = (
            extraroute_const.RESOURCE_ATTRIBUTE_MAP)
    dns_const.EXTENDED_ATTRIBUTES_2_0 = dns_const.RESOURCE_ATTRIBUTE_MAP

    # Return the database object rather than oslo versioned object
    def get_agent_db_obj(agent):
        return agent.db_obj
else:
    # Pre-queens
    from neutron.agent.linux import external_process  # noqa
    from neutron.agent.linux import interface as neutron_agent_conf  # noqa
    from neutron.api.v2 import base as cb_faults  # noqa
    from neutron.callbacks import events as cb_events  # noqa
    from neutron.callbacks import registry as cb_registry  # noqa
    from neutron.callbacks import resources as cb_resources  # noqa
    from neutron.common import utils as runtime_utils  # noqa
    from neutron.extensions import agent as agent_exceptions  # noqa
    from neutron.extensions import dns as dns_const  # noqa
    from neutron.extensions import external_net as exnet_const  # noqa
    from neutron.extensions import extraroute as extraroute_const  # noqa
    from neutron.extensions import l3 as l3_const  # noqa
    from neutron.plugins.ml2 import config as ml2_config  # noqa
    from neutron.plugins.ml2 import driver_api as ml2_api  # noqa
    l3_exceptions = l3_const
    neutron_agent_conf.INTERFACE_OPTS = neutron_agent_conf.OPTS
    neutron_agent_conf.EXTERNAL_PROCESS_OPTS = external_process.OPTS

    def get_agent_db_obj(agent):
        return agent

if nv.NEUTRON_VERSION >= nv.NEUTRON_ROCKY_VERSION:
    from neutron_lib.agent import topics  # noqa
    from neutron_lib.db import api as lib_db_api
else:
    from neutron.common import topics  # noqa
    from neutron.db import api as lib_db_api

core_opts = base_config.core_opts
