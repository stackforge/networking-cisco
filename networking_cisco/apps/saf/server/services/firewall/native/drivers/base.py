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
#

import abc
import six


@six.add_metaclass(abc.ABCMeta)
class BaseDrvr(object):

    '''Base Driver class for FW driver classes.'''

    # def __init__(self):
    #    Pass

    @abc.abstractmethod
    def initialize(self):
        '''Initialize method'''
        pass

    @abc.abstractmethod
    def pop_evnt_que(self):
        '''Pop Event Queue'''
        pass

    @abc.abstractmethod
    def pop_dcnm_obj(self):
        '''Pop DCNM Obj'''
        pass

    @abc.abstractmethod
    def nwk_create_notif(self, tenant_id, tenant_name, cidr):
        '''Nwk Create Notification'''
        pass

    @abc.abstractmethod
    def nwk_delete_notif(self, tenant_id, tenant_name, net_id):
        '''Nwk Delete Notification'''
        pass

    @abc.abstractmethod
    def is_device_virtual(self):
        '''Return False if device is physical, True otherwise'''
        pass

    @abc.abstractmethod
    def get_name(self):
        '''Return the name of the driver service'''
        pass

    @abc.abstractmethod
    def get_max_quota(self):
        '''Retrieves the maximumnumber of FW that could be created'''
        pass

    @abc.abstractmethod
    def create_fw(self, tenant_id, data):
        '''Create the Firewall'''
        pass

    @abc.abstractmethod
    def delete_fw(self, tenant_id, data):
        '''Create the Firewall'''
        pass

    @abc.abstractmethod
    def modify_fw(self, tenant_id, data):
        '''Create the Firewall'''
        pass
