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
interface_list=$(ip link |grep 'state UP' | awk '{print $2}'|sed 's/://'|grep ^[epb])
not_found=1
log_file=/tmp/uplink.log
logger  -t DFA_UPLINK_DET "Interface list is $interface_list" 
for interface in $interface_list
do
   logger -t DFA_UPLINK_DET $interface
   ifconfig $interface |grep 'inet addr' >/dev/null
   if [ $? -ne 0 ]
   then
      logger -t DFA_UPLINK_DET "checking if $interface is an uplink"
      /usr/sbin/lldptool -i $interface -g "ncb" -L adminStatus=rxtx
      sleep 40
      /usr/sbin/lldptool -i $interface -g "ncb" -t -n -V evb |grep 'mode:bridge'
      if [ $? -eq 0 ]
      then
         not_found=0
         logger  -t DFA_UPLINK_DET "interface $interface is an uplink"
      fi
        /usr/sbin/lldptool -i $interface -g "ncb" -L adminStatus=disabled
      if [ $not_found -eq 0 ]
      then
         echo $interface >$1
         logger  -t DFA_UPLINK_DET "uplink detection finished $interface"
         break
      fi
         
   fi
done
logger  -t DFA_UPLINK_DET "Not Found"
exit $not_found 
