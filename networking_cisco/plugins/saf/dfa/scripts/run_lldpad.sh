#!/bin/bash
# Copyright 2014 Cisco Systems, Inc.
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
# @author: Padmanabhan Krishnan, Cisco Systems, Inc.

SRC_DIR=$1
if [ "$SRC_DIR  " == "" ]
then
    logger -t SETUP_LLDPAD "Empty SRC DIR"
    exit
fi
flag=0
logger -t SETUP_LLDPAD "Copying lldpad files"
if [ -f /etc/lsb-release ]
then
    NAME=`cat /etc/lsb-release | grep DISTRIB_ID | awk -F "=" '{print $2}'`
    if [ "$NAME" == Ubuntu ]
    then
        if [ ! -f /etc/init/lldpad.conf ]
        then
            logger -t SETUP_LLDPAD "Copying lldpad upstart"
            sudo cp $SRC_DIR/dfa/scripts/lldpad.conf /etc/init/
            sleep 5
        fi
        LLDP_PATH=`which lldpad`
        if [ $? == 0 ]
        then
            LLDP_STAT=`sudo status lldpad | grep -i stop`
            if [ "$LLDP_STAT" == "" ]
            then
                logger -t SETUP_LLDPAD "lldpad is already running"
            else
                logger -t SETUP_LLDPAD "starting lldpad"
                sudo start lldpad
            fi
        else
            logger  -t SETUP_LLDPAD "Install and start lldpad service"
        fi
    else
        logger -t SETUP_LLDPAD "Please start Lldpad service manually"
    fi
fi
logger -t SETUP_LLDPAD "Done with lldpad"

