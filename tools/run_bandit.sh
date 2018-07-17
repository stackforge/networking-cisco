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

TMPDIR=`mktemp -d /tmp/bandit.XXXXXX` || exit 1
export TMPDIR
trap "rm -rf $TMPDIR" EXIT

RESULTS=$TMPDIR/output.txt
FAILURES=0

get_static_analysis_results () {
    # Currently only verifying ML2 drivers is successful
    bandit -r networking_cisco/ml2_drivers -n5 -f txt -o  $RESULTS
    # Use the following instead when ASR1K issues resolved
    #bandit -r networking_cisco -x apps/saf,tests,plugins/cisco/cpnr -n5 -f txt -o $RESULTS

    while read p; do

        if [[ "$p" = *"Total issues (by confidence)"* ]]; then
            break
        fi

        if [[ "$p" = *"Total issues (by severity)"* ]]; then
            severity_set=1
        elif [ $severity_set ]; then
            if [[ "$p" = *"Low"* ]] || [[ "$p" = *"Medium"* ]] || [[ "$p" = *"High"* ]]; then
                NUMBER=$(echo $p | grep -o -E '[0-9]+\.' | grep -o -E '[0-9]+')
                FAILURES=`expr $NUMBER + $FAILURES`
            fi
        fi

    done < $RESULTS
}

get_static_analysis_results

# Fail, if there are emitted failures
if [ $FAILURES -gt 0 ]; then
    cat $RESULTS
    exit 1
fi
