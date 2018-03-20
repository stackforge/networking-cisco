# Copyright 2012 Red Hat, Inc.
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

import logging

from oslo_config import cfg


LOG = logging.getLogger(__name__)


class MultiConfigParser(object):
    """A ConfigParser which handles multi-opts.

    All methods in this class which accept config names should treat a section
    name of None as 'DEFAULT'.

    This class was moved here from oslo.config because it was removed from
    oslo.config and only networking-cisco was still using it.
    """

    _deprecated_opt_message = ('Option "%(dep_option)s" from group '
                               '"%(dep_group)s" is deprecated. Use option '
                               '"%(option)s" from group "%(group)s".')

    def __init__(self):
        self.parsed = []
        self._emitted_deprecations = set()

    def read(self, config_files):
        read_ok = []

        for filename in config_files:
            sections = {}
            parser = cfg.ConfigParser(filename, sections)

            try:
                parser.parse()
            except IOError:
                continue
            self._add_parsed_config_file(sections)
            read_ok.append(filename)

        return read_ok

    def _add_parsed_config_file(self, sections):
        """Add a parsed config file to the list of parsed files.

        :param sections: a mapping of section name to dicts of config values
        :raises: ConfigFileValueError
        """
        self.parsed.insert(0, sections)

    def get(self, names, multi=False):
        return self._get(names, multi=multi)

    def _get(self, names, multi=False, current_name=None):
        """Fetch a config file value from the parsed files.

        :param names: a list of (section, name) tuples
        :param multi: a boolean indicating whether to return multiple values
        :param current_name: current name in tuple being checked
        """
        rvalue = []

        for sections in self.parsed:
            for section, name in names:
                if section not in sections:
                    continue
                if name in sections[section]:
                    current_name = current_name or names[0]
                    self._check_deprecated((section, name), current_name,
                                           names[1:])
                    val = sections[section][name]
                    if multi:
                        rvalue = val + rvalue
                    else:
                        return val
        if multi and rvalue != []:
            return rvalue
        raise KeyError()

    def _check_deprecated(self, name, current, deprecated):
        """Check for usage of deprecated names.

        :param name: A tuple of the form (group, name) representing the group
                     and name where an opt value was found.
        :param current: A tuple of the form (group, name) representing the
                        current name for an option.
        :param deprecated: A list of tuples with the same format as the name
                    param which represent any deprecated names for an option.
                    If the name param matches any entries in this list a
                    deprecation warning will be logged.
        """
        if name in deprecated and name not in self._emitted_deprecations:
            self._emitted_deprecations.add(name)
            current = (current[0] or 'DEFAULT', current[1])
            # NOTE(bnemec): Not using versionutils for this to avoid a
            # circular dependency between oslo.config and whatever library
            # versionutils ends up in.
            LOG.warning(self._deprecated_opt_message,
                        {'dep_option': name[1], 'dep_group': name[0],
                         'option': current[1], 'group': current[0]})
