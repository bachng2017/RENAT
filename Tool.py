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

# $Date: 2019-02-14 23:25:17 +0900 (木, 14  2月 2019) $
# $Rev: 1778 $
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
        cmd_line = '/usr/sbin/mergecap ' + ' '.join(args) + ' -w ' + result_file
        result =  subprocess.check_output(cmd_line,stderr=subprocess.STDOUT,shell=True)
         
        BuiltIn().log("Merged `%d` files to `%s`" % (len(args),result_file))
        BuiltIn().log(result)
        return result


    def hping(self,*args):
        """ Uses hping3 for multi purposes
        """
        BuiltIn().log('Execute hping')
        cmd_line = 'sudo -S /usr/sbin/hping3 ' + ' '.join(args)
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


    def tcpdump_to_file(self,filename='capture.pcap',params='', timeout='10s'):
        """ Uses tcpdump (for packet capture) and wait 
    
        The keyword ignores detail output of the command.
        By default, the keyword only captures 10s 
        """
        BuiltIn().log('Run tcpdump command')
        result_file = '%s/%s' % (Common.get_result_path(),filename)
        cmd = 'sudo /usr/sbin/tcpdump %s -w %s' % (params,result_file)
        proc1 = subprocess.Popen(cmd,stderr=subprocess.STDOUT,stdout=subprocess.PIPE,shell=True,preexec_fn=os.setpgrp)
        time.sleep(DateTime.convert_time(timeout))

        output2 = subprocess.check_output('sudo /bin/kill %s' % proc1.pid,shell=True)
        time.sleep(1)
        output1 = b'\n'.join(proc1.stdout.readlines())
        BuiltIn().log(output1)
        BuiltIn().log(output2)

        # change owner of the captured file
        username = Common.current_username()
        usergroup = Common.current_usergroup()
        output = subprocess.check_output('sudo /bin/chown %s:%s %s' % (username,usergroup,result_file),shell=True)

        BuiltIn().log('Executed tcpdump command `%s`' % cmd)
       
