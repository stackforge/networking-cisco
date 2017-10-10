#!/bin/sh
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

set -e

GEN_CMD=oslo-config-generator

if ! type "$GEN_CMD" > /dev/null; then
    echo "ERROR: $GEN_CMD not installed on the system."
    exit 1
fi

config_files="etc/oslo-config-generator/ml2_nexus.ini
              etc/oslo-config-generator/ml2_nexus_vxlan_type_driver.ini"

for config_file in $config_files; do
    $GEN_CMD --config-file=$config_file
done

set -x
