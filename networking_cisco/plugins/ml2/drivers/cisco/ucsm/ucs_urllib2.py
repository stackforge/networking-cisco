# Copyright 2018 Cisco Systems, Inc.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import urllib2
from urllib2 import *  # noqa

from networking_cisco.plugins.ml2.drivers.cisco.ucsm import config


def build_opener(*handlers):
    if not config.get_ucsm_https_verify():
        LOG.debug("Inside Monkey patch code")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return urllib2.build_opener(urllib2.HTTPSHandler(context=ctx),
            *handlers)
    else:
        return urllib2.build_opener(*handlers)
