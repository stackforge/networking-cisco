# Copyright 2014 Red Hat, Inc.
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


from oslotest import base

from networking_cisco.config import multi_config_parser


class MultiConfigParserTestCase(base.BaseTestCase):

    def test_parse_single_file(self):
        paths = self.create_tempfiles([('test',
                                        '[DEFAULT]\n'
                                        'foo = bar\n'
                                        '[BLAA]\n'
                                        'bar = foo\n')])

        parser = multi_config_parser.MultiConfigParser()
        read_ok = parser.read(paths)

        self.assertEqual(read_ok, paths)

        self.assertIn('DEFAULT', parser.parsed[0])
        self.assertEqual(parser.parsed[0]['DEFAULT']['foo'], ['bar'])
        self.assertEqual(parser.get([('DEFAULT', 'foo')]), ['bar'])
        self.assertEqual(parser.get([('DEFAULT', 'foo')], multi=True),
                         ['bar'])
        self.assertEqual(parser.get([('DEFAULT', 'foo')], multi=True),
                         ['bar'])
        self.assertEqual(parser.get([('DEFAULT', 'foo')], multi=True),
                         ['bar'])

        self.assertIn('BLAA', parser.parsed[0])
        self.assertEqual(parser.parsed[0]['BLAA']['bar'], ['foo'])
        self.assertEqual(parser.get([('BLAA', 'bar')]), ['foo'])
        self.assertEqual(parser.get([('BLAA', 'bar')], multi=True),
                         ['foo'])

    def test_parse_multiple_files(self):
        paths = self.create_tempfiles([('test1',
                                        '[DEFAULT]\n'
                                        'foo = bar\n'
                                        '[BLAA]\n'
                                        'bar = foo'),
                                       ('test2',
                                        '[DEFAULT]\n'
                                        'foo = barbar\n'
                                        '[BLAA]\n'
                                        'bar = foofoo\n'
                                        '[bLAa]\n'
                                        'bar = foofoofoo\n')])

        parser = multi_config_parser.MultiConfigParser()
        read_ok = parser.read(paths)

        self.assertEqual(read_ok, paths)

        self.assertIn('DEFAULT', parser.parsed[0])
        self.assertEqual(parser.parsed[0]['DEFAULT']['foo'], ['barbar'])
        self.assertIn('DEFAULT', parser.parsed[1])
        self.assertEqual(parser.parsed[1]['DEFAULT']['foo'], ['bar'])
        self.assertEqual(parser.get([('DEFAULT', 'foo')]), ['barbar'])
        self.assertEqual(parser.get([('DEFAULT', 'foo')], multi=True),
                         ['bar', 'barbar'])

        self.assertIn('BLAA', parser.parsed[0])
        self.assertIn('bLAa', parser.parsed[0])
        self.assertEqual(parser.parsed[0]['BLAA']['bar'], ['foofoo'])
        self.assertEqual(parser.parsed[0]['bLAa']['bar'], ['foofoofoo'])
        self.assertIn('BLAA', parser.parsed[1])
        self.assertEqual(parser.parsed[1]['BLAA']['bar'], ['foo'])
        self.assertEqual(parser.get([('BLAA', 'bar')]), ['foofoo'])
        self.assertEqual(parser.get([('bLAa', 'bar')]), ['foofoofoo'])
        self.assertEqual(parser.get([('BLAA', 'bar')], multi=True),
                         ['foo', 'foofoo'])
