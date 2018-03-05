# Copyright 2015 Cisco Systems, Inc.  All rights reserved.
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

from functools import wraps
import imp
import time

from oslo_log import log as logging

from neutron_lib import exceptions as nexception

from networking_cisco._i18n import _

LOG = logging.getLogger(__name__)


class DriverNotFound(nexception.NotFound):
    message = _("Driver %(driver)s does not exist")


def retry(ExceptionToCheck, tries=4, delay=3, backoff=2):
    """Retry calling the decorated function using an exponential backoff.

    Reference: http://www.saltycrane.com/blog/2009/11/trying-out-retry
    -decorator-python/

    :param ExceptionToCheck: the exception to check. may be a tuple of
        exceptions to check
    :param tries: number of times to try (not retry) before giving up
    :param delay: initial delay between retries in seconds
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    """
    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck as e:
                    LOG.debug("%(err_mess)s. Retry calling function "
                              "'%(f_name)s' in %(delta)d seconds.",
                              {'err_mess': str(e), 'f_name': f.__name__,
                               'delta': mdelay})
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            LOG.debug("Last retry calling function '%s'.", f.__name__)
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry


def import_module(module_path, parent_path=None):
    if not isinstance(module_path, list):
        module_path = module_path.split(".")
    info = imp.find_module(module_path[0], parent_path)
    m = imp.load_module(module_path[0], *info)
    if len(module_path) == 1:
        return m
    else:
        return import_module(module_path[1:], parent_path=m.__path__)


def convert_validate_driver_class(driver_class_name):
    # Verify that import_obj is a loadable class
    if driver_class_name is None or driver_class_name == '':
        return driver_class_name
    else:
        try:
            parts = driver_class_name.split(".")
            mod = import_module(parts[:-1])
            if parts[-1] in dir(mod):
                return driver_class_name
        except ImportError as e:
            LOG.error('Failed to verify driver module %(name)s: %(err)s',
                      {'name': driver_class_name, 'err': e})
    raise DriverNotFound(driver=driver_class_name)
