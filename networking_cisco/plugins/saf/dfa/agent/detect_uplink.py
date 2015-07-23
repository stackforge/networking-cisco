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
import os
import re
import subprocess
import sys
import time
from dfa.common import dfa_logger as logging
LOG = logging.getLogger(__name__)

uplink_file_path='/tmp/uplink'
detect_uplink_file_path='/tmp/uplink_detected'

def run_cmd_line(cmd_str, stderr=None, shell=False,
                 echo_cmd=True, check_result=True):
    if echo_cmd:
        print cmd_str
    if shell:
        cmd_args = cmd_str
    else:
        cmd_args = cmd_str.split()
    output = None
    returncode = 0
    try:
        output = subprocess.check_output(cmd_args, shell=shell, stderr=stderr)
    except subprocess.CalledProcessError as e:
        if check_result:
            print e
            sys.exit(e.returncode)
        else:
            returncode = e.returncode
    return output, returncode

def read_file(file_name):
    file_content = None
    if os.path.isfile(file_name):
      file=open(file_name, "r")
      file_content=file.read()
      file_content = file_content.replace("\n", "")
    return file_content

def detect_uplink_non_auto(input_string):
    file_str = "normal"
    if (input_string == None):
      file_str = read_file(uplink_file_path)
    return file_str  

def detect_uplink_auto(input_string):
    if (input_string == None):
      cmd_str = """/usr/local/bin/detect_uplink.sh %s""" %detect_uplink_file_path 
      output, returncode = run_cmd_line (cmd_str, shell=True,check_result=False)
      if (returncode == 1):
#         print "not found"
         return_str = None
      else:
         return_str = read_file(detect_uplink_file_path)
    else:
      cmd_str ="""/usr/sbin/lldptool -i %s -g "ncb" -t -n -V evb |grep 'mode:bridge'""" % input_string
      (output, returncode) = run_cmd_line(cmd_str, shell=True, check_result=False)
#      print "output from lldptool is %s, return is %s" % (output, returncode)
      if (returncode == 0):
         return_str = "normal"
      else:
         return_str = "down"
#    print "returning from detect_uplink_auto: %s" % return_str
    return return_str        
         

def detect_uplink(input_string):
   auto_detect = False
   if os.path.isfile(uplink_file_path):
      detected_uplink = detect_uplink_non_auto(input_string)
   else:
      detected_uplink = detect_uplink_auto(input_string)
      auto_detect = True
   log_str= "auto detect = %s, input string %s, detected uplink is %s " % ( auto_detect, input_string , detected_uplink)
   LOG.debug(log_str)
   return detected_uplink

if __name__ == '__main__':
   link=detect_uplink("lldp_loc_v_eth5")
   print "return from detect_uplink is %s" % link
    
