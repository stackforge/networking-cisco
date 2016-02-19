# Copyright 2014 Cisco Systems, Inc.  All rights reserved.
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

#######################################################
# Module that implements REST APIs for
# Cisco's CPNR (Cisco Prime Network Registrar) server
#######################################################

from neutron.common import exceptions
from oslo_log import log as logging
from oslo_serialization import jsonutils
import requests
from requests import exceptions as r_exc

LOG = logging.getLogger(__name__)
URL_BASE = "web-services/rest/resource"


class CpnrException(exceptions.NeutronException):
    message = _("CPNR exception occurred")


class ServerError(CpnrException):
    message = _("CPNR received error response: %(status)i %(msg)s")


class Timeout(CpnrException):
    message = _("CPNR callout to server timed out: %(msg)s")


class ConnectionError(CpnrException):
    message = _("CPNR failed to connect: %(msg)s")


class UnexpectedError(CpnrException):
    message = _("CPNR unexpected error: %(msg)s")


class CpnrClient(object):
    """Class implementing REST APIs for
    the CPNR (Cisco Prime Network Registrar) server
    """

    def __init__(self, scheme, address, port, username,
                 password, insecure, timeout=20):
        """Constructor for the CpnrClient class."""
        self.url = scheme + "://" + address + ":" + str(port)
        self.auth = requests.auth.HTTPBasicAuth(username, password)
        self.headers = {'Content-Type': 'application/json',
                        'Accept': 'application/json'}
        self.dhcp_reload_needed = False
        self.dns_reload_needed = False
        self.verify_ssl_certs = not insecure
        self.timeout = timeout

    def __repr__(self):
        return "<CpnrClient(url=%s)>" % (self.url,)

    def _build_url(self, tags, vpn='', view='', zone=''):
        """Builds and returns CPNR URL."""
        url = [self.url, URL_BASE]
        url.extend(tags)
        url = "/".join(url)
        if vpn:
            url += '?vpnId=' + vpn
        if view:
            url += '?viewId=' + view
        if zone:
            url += '&zoneOrigin=' + zone
        return url

    def _do_request(self, method, url, data=""):
        """Perform REST request and return response."""
        LOG.debug("%s %s %s", method, url, str(data))
        try:
            # Send request, receive response
            data = jsonutils.dumps(data) if data else None
            response = requests.request(method, url,
                                        data=data,
                                        auth=self.auth,
                                        headers=self.headers,
                                        timeout=self.timeout,
                                        verify=self.verify_ssl_certs)

            # Check for HTTP errors, raise exception
            if 400 <= response.status_code:
                raise ServerError(status=response.status_code,
                                  msg=response.text)

            # Check if CPNR reload is needed
            if 'AX_DHCP_RELOAD_REQUIRED' in response.content:
                self.dhcp_reload_needed = True

            # If incomplete response, fetch next set of data
            if 'next' in response.links:
                nexturl = response.links['next']['url']
                nextresp = self._do_request(method, nexturl)
                return response.json() + nextresp

            return response.json() if method == 'GET' else None

        except r_exc.Timeout as te:
            raise Timeout(msg=te.message)
        except r_exc.ConnectionError as ce:
            raise ConnectionError(msg=ce.message)
        except r_exc.RequestException as re:
            raise UnexpectedError(msg=re.message)

    def get_dhcp_server(self):
        """Returns a dictionary with all the objects of DHCPServer."""
        request_url = self._build_url(['DHCPServer'])
        return self._do_request('GET', request_url)

    def get_client_classes(self):
        """Returns a list of all the client classes from CPNR server."""
        request_url = self._build_url(['ClientClass'])
        return self._do_request('GET', request_url)

    def get_client_class(self, client_class_name):
        """Returns a dictionary with all the objects of a specific client
        class name from CPNR server.
        """
        request_url = self._build_url(['ClientClass', client_class_name])
        return self._do_request('GET', request_url)

    def get_vpns(self):
        """Returns a list of all the VPNs from CPNR server."""
        request_url = self._build_url(['VPN'])
        return self._do_request('GET', request_url)

    def get_vpn(self, vpn_name):
        """Returns a dictionary with all the objects of a specific VPN name
        from CPNR server.
        """
        request_url = self._build_url(['VPN', vpn_name])
        return self._do_request('GET', request_url)

    def get_scopes(self, vpnid='.*'):
        """Returns a list of all the scopes from CPNR server."""
        request_url = self._build_url(['Scope'], vpn=vpnid)
        return self._do_request('GET', request_url)

    def get_scope(self, scope_name):
        """Returns a dictionary with all the objects of a specific scope name
        from CPNR server.
        """
        request_url = self._build_url(['Scope', scope_name])
        return self._do_request('GET', request_url)

    def get_client_entries(self):
        """Returns a list of all the client entries from CPNR server."""
        request_url = self._build_url(['ClientEntry'])
        return self._do_request('GET', request_url)

    def get_client_entry(self, client_entry_name):
        """Returns a dictionary with all the objects of a specific client
        entry name from CPNR server.
        """
        request_url = self._build_url(['ClientEntry', client_entry_name])
        return self._do_request('GET', request_url)

    def get_leases(self, vpnid='.*'):
        """Returns a list of all the leases from CPNR server."""
        request_url = self._build_url(['Lease'], vpn=vpnid)
        return self._do_request('GET', request_url)

    def get_dns_server(self):
        request_url = self._build_url(['DNSServer'])
        return self._do_request('GET', request_url)

    def get_dns_forwarders(self):
        request_url = self._build_url(['DnsForwarder'])
        return self._do_request('GET', request_url)

    def get_dns_forwarder(self, name):
        request_url = self._build_url(['DnsForwarder', name])
        return self._do_request('GET', request_url)

    def get_dns_views(self):
        request_url = self._build_url(['DnsView'])
        return self._do_request('GET', request_url)

    def get_dns_view(self, name):
        request_url = self._build_url(['DnsView', name])
        return self._do_request('GET', request_url)

    def get_ccm_zones(self, viewid='.*'):
        request_url = self._build_url(['CCMZone'], view=viewid)
        return self._do_request('GET', request_url)

    def get_ccm_zone(self, name, viewid='.*'):
        request_url = self._build_url(['CCMZone', name], view=viewid)
        return self._do_request('GET', request_url)

    def get_ccm_reverse_zones(self, viewid='.*'):
        request_url = self._build_url(['CCMReverseZone'], view=viewid)
        return self._do_request('GET', request_url)

    def get_ccm_reverse_zone(self, name, viewid='.*'):
        request_url = self._build_url(['CCMReverseZone', name], view=viewid)
        return self._do_request('GET', request_url)

    def get_ccm_hosts(self, viewid='.*', zoneid='.*'):
        request_url = self._build_url(['CCMHost'], view=viewid, zone=zoneid)
        return self._do_request('GET', request_url)

    def get_ccm_host(self, name, viewid='.*', zoneid='.*'):
        request_url = self._build_url(['CCMHost', name],
                                      view=viewid, zone=zoneid)
        return self._do_request('GET', request_url)

    def create_scope(self, data):
        """Returns status code after creating a scope with data dictionary."""
        request_url = self._build_url(['Scope'])
        return self._do_request('POST', request_url, data)

    def create_client_class(self, data):
        """Returns status code after creating a client class with data
        dictionary.
        """
        self.dhcp_reload_needed = True
        request_url = self._build_url(['ClientClass'])
        return self._do_request('POST', request_url, data)

    def create_vpn(self, data):
        """Returns status code after creating a VPN with data dictionary."""
        self.dhcp_reload_needed = True
        request_url = self._build_url(['VPN'])
        return self._do_request('POST', request_url, data)

    def create_client_entry(self, data):
        """Returns status code after creating a client entry with data
        dictionary.
        """
        request_url = self._build_url(['ClientEntry'])
        return self._do_request('POST', request_url, data)

    def create_dns_forwarder(self, data):
        self.dns_reload_needed = True
        request_url = self._build_url(['DnsForwarder'])
        return self._do_request('POST', request_url, data)

    def create_dns_view(self, data):
        self.dns_reload_needed = True
        request_url = self._build_url(['DnsView'])
        return self._do_request('POST', request_url, data)

    def create_ccm_zone(self, data, viewid=None):
        self.dns_reload_needed = True
        request_url = self._build_url(['CCMZone'], view=viewid)
        return self._do_request('POST', request_url, data)

    def create_ccm_reverse_zone(self, data, viewid=None):
        self.dns_reload_needed = True
        request_url = self._build_url(['CCMReverseZone'], view=viewid)
        return self._do_request('POST', request_url, data)

    def create_ccm_host(self, data, viewid=None, zoneid=None):
        request_url = self._build_url(['CCMHost'], view=viewid, zone=zoneid)
        return self._do_request('POST', request_url, data)

    def update_dhcp_server(self, data):
        """Returns status code after updating dhcp server with data
        dictionary.
        """
        self.dhcp_reload_needed = True
        request_url = self._build_url(['DHCPServer'])
        return self._do_request('PUT', request_url, data)

    def update_client_class(self, client_class_name, data):
        """Returns status code after updating client class client_class_name
        with data dictionary.
        """
        self.dhcp_reload_needed = True
        request_url = self._build_url(['ClientClass', client_class_name])
        return self._do_request('PUT', request_url, data)

    def update_vpn(self, vpn_name, data):
        """Returns status code after updating VPN vpn_name with data
        dictionary.
        """
        self.dhcp_reload_needed = True
        request_url = self._build_url(['VPN', vpn_name])
        return self._do_request('PUT', request_url, data)

    def update_scope(self, scope_name, data):
        """Returns status code after updating scope scope_name with data
        dictionary.
        """
        request_url = self._build_url(['Scope', scope_name])
        return self._do_request('PUT', request_url, data)

    def update_client_entry(self, client_entry_name, data):
        """Returns status code after updating client entry client_entry_name
        with data dictionary.
        """
        request_url = self._build_url(['ClientEntry', client_entry_name])
        return self._do_request('PUT', request_url, data)

    def update_dns_server(self, data):
        """Updates DNS serer with supplied attributes."""
        self.dns_reload_needed = True
        request_url = self._build_url(['DNSServer'])
        return self._do_request('PUT', request_url, data)

    def update_dns_forwarder(self, name, data):
        self.dns_reload_needed = True
        request_url = self._build_url(['DnsForwarder', name])
        return self._do_request('PUT', request_url, data)

    def update_dns_view(self, name, data):
        self.dns_reload_needed = True
        request_url = self._build_url(['DnsView', name])
        return self._do_request('PUT', request_url, data)

    def update_ccm_zone(self, name, data, viewid=None):
        self.dns_reload_needed = True
        request_url = self._build_url(['CCMZone', name], view=viewid)
        return self._do_request('PUT', request_url, data)

    def update_ccm_reverse_zone(self, name, data, viewid=None):
        self.dns_reload_needed = True
        request_url = self._build_url(['CCMReverseZone', name], view=viewid)
        return self._do_request('PUT', request_url, data)

    def update_ccm_host(self, name, data, viewid=None, zoneid=None):
        request_url = self._build_url(['CCMHost', name],
                                      view=viewid, zone=zoneid)
        return self._do_request('PUT', request_url, data)

    def delete_client_class(self, client_class_name):
        """Returns status code after deleting client class
        client_class_name.
        """
        self.dhcp_reload_needed = True
        request_url = self._build_url(['ClientClass', client_class_name])
        return self._do_request('DELETE', request_url)

    def delete_vpn(self, vpn_name):
        """Returns status code after deleting VPN vpn_name
        delete_vpn must not be called before delete_client_entry.
        """
        self.dhcp_reload_needed = True
        request_url = self._build_url(['VPN', vpn_name])
        return self._do_request('DELETE', request_url)

    def delete_scope(self, scope_name):
        """Returns status code after deleting scope scope_name."""
        request_url = self._build_url(['Scope', scope_name])
        return self._do_request('DELETE', request_url)

    def delete_client_entry(self, client_entry_name):
        """Returns status code after deleting scope client_entry_name
        delete_vpn must not be called before delete_client_entry.
        """
        request_url = self._build_url(['ClientEntry', client_entry_name])
        return self._do_request('DELETE', request_url)

    def delete_dns_forwarder(self, name):
        self.dns_reload_needed = True
        request_url = self._build_url(['DnsForwarder', name])
        return self._do_request('DELETE', request_url)

    def delete_dns_view(self, name):
        self.dns_reload_needed = True
        request_url = self._build_url(['DnsView', name])
        return self._do_request('DELETE', request_url)

    def delete_ccm_zone(self, name, viewid=None):
        request_url = self._build_url(['CCMZone', name], view=viewid)
        return self._do_request('DELETE', request_url)

    def delete_ccm_reverse_zone(self, name, viewid=None):
        self.dns_reload_needed = True
        request_url = self._build_url(['CCMReverseZone', name], view=viewid)
        return self._do_request('DELETE', request_url)

    def delete_ccm_host(self, name, viewid=None, zoneid=None):
        request_url = self._build_url(['CCMHost', name],
                                      view=viewid, zone=zoneid)
        return self._do_request('DELETE', request_url)

    def release_address(self, address, vpnid):
        """Release a specific lease, called after delete_client_entry"""
        query = address + "?action=releaseAddress&vpnId=" + vpnid
        request_url = self._build_url(['Lease', query])
        return self._do_request('DELETE', request_url)

    def reload_dhcp_server(self):
        """Returns status code after reloading CPNR server."""
        try:
            request_url = self._build_url(['DHCPServer',
                                           '?action=reloadServer'])
            response = requests.request('PUT', request_url, auth=self.auth,
                                        verify=self.verify_ssl_certs)
            if 400 <= response.status_code:
                raise ServerError(status=response.status_code,
                                  msg=response.text)
            self.dhcp_reload_needed = False
        except r_exc.RequestException as e:
            raise UnexpectedError(msg=e.message)

    def reload_dns_server(self):
        """Returns status code after reloading CPNR server."""
        try:
            request_url = self._build_url(['DNSServer',
                                           '?action=reloadServer'])
            response = requests.request('PUT', request_url, auth=self.auth,
                                        verify=self.verify_ssl_certs)
            if 400 <= response.status_code:
                raise ServerError(status=response.status_code,
                                  msg=response.text)
            self.dns_reload_needed = False
        except r_exc.RequestException as e:
            raise UnexpectedError(msg=e.message)

    def reload_needed(self):
        """Return true if reload is required."""
        return self.dhcp_reload_needed or self.dns_reload_needed

    def reload_server(self, force=False):
        """Reload DHCP and DNS servers as needed."""
        if self.dhcp_reload_needed or force:
            self.reload_dhcp_server()
        if self.dns_reload_needed or force:
            self.reload_dns_server()

    def get_version(self):
        """Returns the CPNR version."""
        try:
            request_url = "/".join([self.url, "web-services/rest/session"])
            response = requests.request('GET', request_url,
                                        auth=self.auth, timeout=self.timeout,
                                        verify=self.verify_ssl_certs)
            return str(response.text)
        except r_exc.RequestException as e:
            raise UnexpectedError(msg=e.message)
