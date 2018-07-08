# -*- coding: utf-8 -*-
#  Copyright 2018 NTT Communications
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

# $Date: 2018-07-01 13:11:50 +0900 (Sun, 01 Jul 2018) $
# $Rev: 1061 $
# $Ver: $
# $Author: $

import os
import subprocess,time,signal
import Common
from robot.libraries.BuiltIn import BuiltIn
import robot.libraries.DateTime as DateTime

class Tool(object):
    """  A collection of useful tools

    Contains some useful tools for packet capture, crafting and firewall testing ...

    *Note*: be careful about the argument of the command, it some cases they
    could block the test.

    Some commands need to sudo privileges to run. Below is sample sudo setting
    files that allows related commands run as `root` without password. *Note*:
    consider security risks carefully before using this setting.

    Sample sudoer setting in Centos system:
    | [root@walle renat]# cat /etc/sudoers.d/renat
    | Cmnd_Alias CMD_ROBOT_ALLOW  = /bin/kill,/usr/local/bin/nmap,/usr/sbin/hping3,/usr/sbin/tcpdump
    | %techno ALL=NOPASSWD: CMD_ROBOT_ALLOW
    | %jenkins ALL=NOPASSWD: CMD_ROBOT_ALLOW
    """

    ROBOT_LIBRARY_SCOPE = 'TEST SUITE'
    ROBOT_LIBRARY_VERSION = Common.version()

    def __init__(self):
        pass

    def merge_cap(sef,result_file,*args):
        """ Merges multi pcap files into one
        """
        BuiltIn().log("Merges pcap files")
        cmd_line = 'mergecap ' + ' '.join(args) + ' -w ' + result_file
        result =  subprocess.check_output(cmd_line,stderr=subprocess.STDOUT,shell=True)
         
        BuiltIn().log("Merged `%d` files to `%s`" % (len(args),result_file))
        BuiltIn().log(result)
        return result


    def hping(self,*args):
        """ Uses hping3 for multi purposes
        """
        BuiltIn().log('Execute hping')
        cmd_line = 'sudo -S hping3 ' + ' '.join(args)
        result = subprocess.check_output(cmd_line,stderr=subprocess.STDOUT,shell=True)
        BuiltIn().log(result)
        BuiltIn().log('Executed hping')
        return result


    def nmap(self,params):
        """ Uses nmap for multi purposes
        """
        BuiltIn().log('Execute Nmap')
        cmd_line = 'nmap ' + params
        result =  subprocess.check_output(cmd_line,stderr=subprocess.STDOUT,shell=True)
        BuiltIn().log(result)
        BuiltIn().log('Executed Nmap')
        return result


    def tcpdump(self,params,timeout=''):
        """ Uses tcpdump (for packet capture) and wait 
    
        The keyword ignores detail output of the command
        """
        BuiltIn().log('Run tcpdump command')
        cmd = 'sudo tcpdump ' + params
        proc1 = subprocess.Popen(cmd,stderr=subprocess.STDOUT,stdout=subprocess.PIPE,shell=True,preexec_fn=os.setpgrp)
        # proc1 = subprocess.Popen(cmd,shell=True,stderr=subprocess.STDOUT,preexec_fn=os.setpgrp)
        if timeout != '': 
            time.sleep(DateTime.convert_time(timeout))
        # output1 = proc1.stdout.readline()
        # output2 = subprocess.check_output('sudo kill %s' % proc1.pid,stderr=subprocess.STDOUT,shell=True)
        output2 = subprocess.check_output('sudo kill %s' % proc1.pid,shell=True)
        output1 = '\n'.join(proc1.stdout.readlines())

        time.sleep(1)
        BuiltIn().log(output1)
        # BuiltIn().log(output2)
        BuiltIn().log('Executed tcpdump command')
       
