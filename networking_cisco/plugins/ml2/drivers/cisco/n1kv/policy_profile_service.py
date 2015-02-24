# Copyright 2015 Cisco Systems, Inc.
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

import eventlet
from oslo_config import cfg
from sqlalchemy.orm import exc
from sqlalchemy import sql

from networking_cisco.plugins.ml2.drivers.cisco.n1kv import (
    constants as n1kv_const)
from networking_cisco.plugins.ml2.drivers.cisco.n1kv import (
    exceptions as n1kv_exc)
from networking_cisco.plugins.ml2.drivers.cisco.n1kv import (
    n1kv_client)
from networking_cisco.plugins.ml2.drivers.cisco.n1kv import (
    n1kv_db)
from networking_cisco.plugins.ml2.drivers.cisco.n1kv import config  # noqa

from neutron.api import extensions as api_extensions
import neutron.db.api as db
from neutron.db import common_db_mixin as base_db
from neutron.openstack.common import excutils
from neutron.openstack.common.gettextutils import _LW
from neutron.openstack.common import log as logging
from neutron.plugins.ml2.drivers.cisco.n1kv import extensions
from neutron.plugins.ml2.drivers.cisco.n1kv.extensions import policy_profile
from neutron.plugins.ml2.drivers.cisco.n1kv import n1kv_models

LOG = logging.getLogger(__name__)


class PolicyProfile_db_mixin(policy_profile.PolicyProfilePluginBase,
                             base_db.CommonDbMixin):
    """Policy Profile Mixin class."""

    def _make_policy_profile_dict(self, policy_profile, fields=None):
        res = {"id": policy_profile["id"], "name": policy_profile["name"]}
        return self._fields(res, fields)

    def _make_profile_bindings_dict(self, profile_binding, fields=None):
        res = {"profile_id": profile_binding["profile_id"],
               "tenant_id": profile_binding["tenant_id"]}
        return self._fields(res, fields)

    def _policy_profile_exists(self, id, vsm_ip=None):
        db_session = db.get_session()
        if vsm_ip is None:
            return self._check_policy_profile_on_all_vsm(id, db_session)
        else:
            return (db_session.query(n1kv_models.PolicyProfile).
                    filter_by(id=id, vsm_ip=vsm_ip).first())

    def _create_policy_profile(self, id, pprofile_name, vsm_ip):
        """Create a policy profile."""
        db_session = db.get_session()
        pprofile = n1kv_models.PolicyProfile(id=id, name=pprofile_name,
                                             vsm_ip=vsm_ip)
        db_session.add(pprofile)
        db_session.flush()
        return pprofile

    def _add_policy_profile(self, policy_profile_id, name, vsm_ip,
                            tenant_id=None):
        """
        Add Policy profile and tenant binding.

        :param policy_profile_id: UUID representing the policy profile
        :param name: string representing the name for the
                     policy profile
        :param vsm_ip: VSM IP from which policy profile is retrieved
        :param tenant_id: UUID representing the tenant
        """
        tenant_id = tenant_id or n1kv_const.TENANT_ID_NOT_SET
        if not self._policy_profile_exists(policy_profile_id, vsm_ip):
            self._create_policy_profile(policy_profile_id, name, vsm_ip)

    def _get_policy_profiles(self):
        """Retrieve all policy profiles."""
        db_session = db.get_session()
        return db_session.query(n1kv_models.PolicyProfile)

    def _get_policy_profile(self, session, id):
        return n1kv_db.get_policy_profile_by_uuid(session, id)

    def _get_policy_collection_for_tenant(self, db_session, model, tenant_id):
        profile_ids = (db_session.query(n1kv_models.
                       ProfileBinding.profile_id)
                       .filter_by(tenant_id=tenant_id).
                       filter_by(profile_type=n1kv_const.POLICY).all())
        profiles = db_session.query(model).filter(model.id.in_(
            pid[0] for pid in profile_ids))
        return [self._make_policy_profile_dict(p) for p in profiles]

    def _get_policy_profiles_by_host(self, vsm_ip):
        """Retrieve policy profiles by vsm_ip."""
        return n1kv_db.get_policy_profiles_by_host(vsm_ip)

    def _remove_policy_profile(self, pprofile_id, vsm_ip):
        """Delete a policy profile."""
        db_session = db.get_session()
        pprofile = (db_session.query(n1kv_models.PolicyProfile).
                    filter_by(id=pprofile_id, vsm_ip=vsm_ip).first())
        if pprofile:
            db_session.delete(pprofile)
            db_session.flush()
        if not self._check_policy_profile_on_any_vsm(pprofile_id, db_session):
            self._delete_profile_binding(db_session, pprofile_id)

    def _create_profile_binding(self, db_session, tenant_id, profile_id):
        """Create Policy Profile association with a tenant."""
        db_session = db_session or db.get_session()
        if self._profile_binding_exists(db_session,
                                        tenant_id,
                                        profile_id):
            return self._get_profile_binding(db_session, tenant_id, profile_id)

        with db_session.begin(subtransactions=True):
            binding = n1kv_models.ProfileBinding(profile_type=n1kv_const.
                                                 POLICY,
                                                 profile_id=profile_id,
                                                 tenant_id=tenant_id)
            db_session.add(binding)
            return binding

    def _profile_binding_exists(self, db_session, tenant_id, profile_id):
        """Check if the profile-tenant binding exists."""
        db_session = db_session or db.get_session()
        return (db_session.query(n1kv_models.ProfileBinding).
                filter_by(tenant_id=tenant_id, profile_id=profile_id,
                          profile_type=n1kv_const.POLICY).first())

    def _get_profile_binding(self, db_session, tenant_id, profile_id):
        """Get Policy Profile - Tenant binding."""
        try:
            return (db_session.query(n1kv_models.ProfileBinding).filter_by(
                tenant_id=tenant_id, profile_id=profile_id).one())
        except exc.NoResultFound:
            raise n1kv_exc.ProfileTenantBindingNotFound(profile_id=profile_id)

    def _get_profile_bindings(self, db_session):
        """Get all Policy Profile - Tenant bindings."""
        return (db_session.query(n1kv_models.ProfileBinding).
                filter_by(profile_type=n1kv_const.POLICY))

    def _delete_profile_binding(self, db_session, profile_id, tenant_id=None):
        """Delete Profile Binding."""
        db_session = db_session or db.get_session()
        try:
            with db_session.begin(subtransactions=True):
                if tenant_id:
                    bindings = self._get_profile_binding(db_session, tenant_id,
                                                         profile_id)
                else:
                    bindings = (db_session.query(n1kv_models.ProfileBinding).
                                filter_by(profile_id=profile_id).all())
                if bindings:
                    db_session.delete(bindings)
        except exc.NoResultFound:
            raise n1kv_exc.ProfileTenantBindingNotFound(profile_id=profile_id)

    def _remove_all_fake_policy_profiles(self):
        """
        Remove all policy profiles associated with fake tenant id.

        This will find all Profile ID where tenant is not set yet - set A
        and profiles where tenant was already set - set B
        and remove what is in both and no tenant id set
        """
        db_session = db.get_session()
        with db_session.begin(subtransactions=True):
            a_set_q = (db_session.query(n1kv_models.ProfileBinding).
                       filter_by(tenant_id=n1kv_const.TENANT_ID_NOT_SET,
                                 profile_type=n1kv_const.POLICY))
            a_set = set(i.profile_id for i in a_set_q)
            b_set_q = (db_session.query(n1kv_models.ProfileBinding).
                       filter(sql.and_(n1kv_models.ProfileBinding.
                                       tenant_id != n1kv_const.
                                       TENANT_ID_NOT_SET,
                                       n1kv_models.ProfileBinding.
                                       profile_type == n1kv_const.POLICY)))
            b_set = set(i.profile_id for i in b_set_q)
            (db_session.query(n1kv_models.ProfileBinding).
             filter(sql.and_(n1kv_models.ProfileBinding.profile_id.
                             in_(a_set & b_set),
                             n1kv_models.ProfileBinding.tenant_id ==
                             n1kv_const.TENANT_ID_NOT_SET)).
             delete(synchronize_session="fetch"))

    def _replace_fake_tenant_id_with_real(self, context):
        """
        Replace default tenant-id with admin tenant-ids.

        Default tenant-ids are populated in profile bindings when plugin is
        initialized. Replace these tenant-ids with admin's tenant-id.
        :param context: neutron api request context
        """
        if context.is_admin and context.tenant_id:
            tenant_id = context.tenant_id
            db_session = context.session
            with db_session.begin(subtransactions=True):
                (db_session.query(n1kv_models.ProfileBinding).
                 filter_by(tenant_id=n1kv_const.TENANT_ID_NOT_SET).
                 update({'tenant_id': tenant_id}))

    def get_policy_profile(self, context, id, fields=None):
        """
        Retrieve a policy profile for the given UUID.

        :param context: neutron api request context
        :param id: UUID representing policy profile to fetch
        :params fields: a list of strings that are valid keys in a policy
                        profile dictionary. Only these fields will be returned
        :returns: policy profile dictionary
        """
        profile = self._get_policy_profile(context.session, id)
        return self._make_policy_profile_dict(profile, fields)

    def get_policy_profiles(self, context, filters=None, fields=None):
        """
        Retrieve a list of policy profiles.

        Retrieve all policy profiles if tenant is admin. For a non-admin
        tenant, retrieve all policy profiles belonging to this tenant only.
        :param context: neutron api request context
        :param filters: a dictionary with keys that are valid keys for a
                        policy profile object. Values in this dictiontary are
                        an iterable containing values that will be used for an
                        exact match comparison for that value. Each result
                        returned by this function will have matched one of the
                        values for each key in filters
        :params fields: a list of strings that are valid keys in a policy
                        profile dictionary. Only these fields will be returned
        :returns: list of all policy profiles
        """
        db_session = db.get_session()

        if (context.is_admin or
            not cfg.CONF.ml2_cisco_n1kv.restrict_policy_profiles):
            pp_list = self._get_collection(context, n1kv_models.PolicyProfile,
                                        self._make_policy_profile_dict,
                                        filters=filters, fields=fields)
        else:
            pp_list = self._get_policy_collection_for_tenant(context.session,
                                                          n1kv_models.
                                                          PolicyProfile,
                                                          context.tenant_id)

        #uniquify the port profile ids
        pp_ids = set(pp['id'] for pp in pp_list)

        return [self._make_policy_profile_dict(self._get_policy_profile(
                db_session, id)) for id in pp_ids
                if (self._check_policy_profile_on_all_vsm(id, db_session))]

    def _check_policy_profile_on_all_vsm(self, id, db_session=None):
        """Checks if port profile is present on all VSM"""
        db_session = db_session or db.get_session()
        vsm_count = len(self.n1kvclient.get_vsm_hosts())
        return (db_session.query(n1kv_models.PolicyProfile).
                filter_by(id=id).count() == vsm_count)

    def _check_policy_profile_on_any_vsm(self, profile_id, db_session=None):
        """Checks if policy profile is present on any VSM"""
        db_session = db_session or db.get_session()
        return (db_session.query(n1kv_models.PolicyProfile).
                filter_by(id=profile_id).count())

    def get_policy_profile_bindings(self, context, filters=None, fields=None):
        """
        Retrieve a list of profile bindings for policy profiles.

        :param context: neutron api request context
        :param filters: a dictionary with keys that are valid keys for a
                        profile bindings object. Values in this dictiontary are
                        an iterable containing values that will be used for an
                        exact match comparison for that value. Each result
                        returned by this function will have matched one of the
                        values for each key in filters
        :params fields: a list of strings that are valid keys in a profile
                        bindings dictionary. Only these fields will be returned
        :returns: list of profile bindings
        """
        if context.is_admin:
            profile_bindings = self._get_profile_bindings(context.session)
            return [self._make_profile_bindings_dict(pb)
                    for pb in profile_bindings]


class PolicyProfilePlugin(PolicyProfile_db_mixin):
    """Implementation of the Cisco N1KV Policy Profile Service Plugin."""
    supported_extension_aliases = ["policy_profile"]

    def __init__(self):
        super(PolicyProfilePlugin, self).__init__()
        api_extensions.append_api_extensions_path(extensions.__path__)
        # Initialize N1KV client
        self.n1kvclient = n1kv_client.Client()
        eventlet.spawn(self._poll_policy_profiles)

    def _poll_policy_profiles(self):
        """Start a green thread to pull policy profiles from VSM."""
        while True:
            self._populate_policy_profiles()
            eventlet.sleep(cfg.CONF.ml2_cisco_n1kv.poll_duration)

    def _populate_policy_profiles(self):
        """Populate all the policy profiles from VSM."""
        hosts = self.n1kvclient.get_vsm_hosts()
        for vsm_ip in hosts:
            try:
                policy_profiles = self.n1kvclient.list_port_profiles(vsm_ip)
                vsm_profiles = {}
                plugin_profiles_set = set()
                # Fetch policy profiles from VSM
                for profile_name in policy_profiles:
                    profile_id = (policy_profiles[profile_name]
                                  [n1kv_const.PROPERTIES][n1kv_const.ID])
                    vsm_profiles[profile_id] = profile_name
                # Fetch policy profiles previously populated
                for profile in self._get_policy_profiles_by_host(vsm_ip):
                    plugin_profiles_set.add(profile.id)
                vsm_profiles_set = set(vsm_profiles)
                # Update database if the profile sets differ.
                if vsm_profiles_set.symmetric_difference(plugin_profiles_set):
                    # Add new profiles to database if they were created in VSM
                    for pid in vsm_profiles_set.difference(
                                                plugin_profiles_set):
                        self._add_policy_profile(pid, vsm_profiles[pid],
                                                 vsm_ip)
                    # Delete profiles from database if they were deleted in VSM
                    for pid in plugin_profiles_set.difference(
                                                   vsm_profiles_set):
                        if not n1kv_db.policy_profile_in_use(pid):
                            self._remove_policy_profile(pid, vsm_ip)
                        else:
                            LOG.warning(_LW('Policy profile %s in use'), pid)
            except (n1kv_exc.VSMError, n1kv_exc.VSMConnectionFailed):
                with excutils.save_and_reraise_exception(reraise=False):
                    LOG.warning(_LW('No policy profile populated from VSM'))

    def get_policy_profiles(self, context, filters=None, fields=None):
        """Return Cisco N1KV policy profiles."""
        self._replace_fake_tenant_id_with_real(context)
        return super(PolicyProfilePlugin, self).get_policy_profiles(context,
                                                                    filters,
                                                                    fields)

    def get_policy_profile(self, context, id, fields=None):
        """Return Cisco N1KV policy profile by its UUID."""
        return super(PolicyProfilePlugin, self).get_policy_profile(context,
                                                                   id,
                                                                   fields)

    def get_policy_profile_bindings(self, context, filters=None, fields=None):
        """Return Cisco N1KV policy profile - tenant bindings."""
        return super(PolicyProfilePlugin,
                     self).get_policy_profile_bindings(context, filters,
                                                       fields)
