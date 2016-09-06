# Copyright (c) 2016 Cisco Systems
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

from oslo_config import cfg


class RemainderOpt(cfg.DictOpt):

    def _get_from_namespace(self, namespace, group_name):
        existing_opts = list(cfg.CONF.get(group_name))
        result = {}
        for section in namespace._parsed:
            gk = section.get(group_name)
            if not gk:
                continue
            for key in gk:
                if key not in existing_opts:
                    names = [(group_name, key)]
                    value = namespace._get_value(
                        names, positional=self.positional)
                    result[key] = value
        return result


class SubsectionOpt(cfg.DictOpt):

    def __init__(self, name, subopts=None, **kwargs):
        super(SubsectionOpt, self).__init__(name, **kwargs)
        self.subopts = subopts or []

    def _get_from_namespace(self, namespace, group_name):
        identities = {}
        sections = cfg.CONF.list_all_sections()
        for section in sections:
            subsection, sep, ident = section.partition(':')
            if subsection.lower() != self.name.lower():
                continue
            cfg.CONF.register_opts(self.subopts, group=section)
            identities[ident] = cfg.CONF.get(section)
        return identities
