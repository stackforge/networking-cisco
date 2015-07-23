#!/usr/bin/python

PROJECT = 'openstack_fabric_enabler'

VERSION = '1.0'

from setuptools import setup, find_packages

try:
    long_description = open('README.txt', 'rt').read()
except IOError:
    long_description = ''


with open('requirements.txt', 'r') as f:
    requires = [x.strip() for x in f if not x.startswith('#') and x.strip()]

setup(
    name=PROJECT,
    version=VERSION,
    description='Fabric enabler for openstack',
    long_description=long_description,
    platforms=['Any'],
    scripts=[],
    provides=[],
    namespace_packages=[],
    packages=find_packages(exclude=['tests']),
    include_package_data=True,
    install_requires=requires,
    entry_points={
        'console_scripts': [
            'fabric_enabler_server = dfa.dfa_enabler_server:dfa_server',
            'fabric_enabler_agent = dfa.dfa_enabler_agent:dfa_agent',
            'fabric_enabler_cli = dfa.dfa_cli:dfa_cli',
        ],
    },
    zip_safe=False,
)
