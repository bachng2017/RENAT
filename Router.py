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

# $Date: 2018-03-24 20:42:36 +0900 (土, 24  3月 2018) $
# $Rev: 861 $
# $Ver: 0.1.8 $
# $Author: $

import netsnmp
import time
import sys
import os
import re
import csv
import json
import inspect
import jinja2
import difflib
import Common
from importlib import import_module
import robot.libraries.DateTime as DateTime
from robot.libraries.BuiltIn import BuiltIn
from robot.libraries.BuiltIn import RobotNotRunningError
from types import MethodType

# expose following keywords
__all__ = ['switch','cmd','exec_file','snap','snap_diff','xrun','follow_mib']


class Router(object):
    """ A class provides keywords for router controll. Usual command could be executed via
    [./VChannel.html|VChannel]. This class provides the vendor independent commands

    Device's ``type`` is defined in master ``device.yaml``. The system will load
    appropriate modules for each device.
    
    Details about keywords provided by modules could be found in document of each
module likes:
    -  [./router_mod_juniper.html|Juniper module]
    -  [./router_mod_cisco.html|Cisco module]
    -  [./router_mod_gr.html|GR module]

    Keywords provides by above module could be executed through `Xrun` keyword
or directly called from ``Router``.
    Examples:
        | Router.`Xrun`      | Load Config |
        | Router.`Load Config` |      | 

    """


    ROBOT_LIBRARY_SCOPE = 'TEST SUITE'
    ROBOT_LIBRARY_VERSION = Common.version()

    _vchannel = None
    _cur_name = ""
    _snap_buffer = {}
    

    def __init__(self):
        folder = os.path.dirname(__file__)
        sys.path.append(folder)
        try:
            self._vchannel = BuiltIn().get_library_instance('VChannel') 

            if self._vchannel is None:
                raise Exception("Could not find an instance of VChannel. Need import VChannel first")

            # using juniper as a base mod for method name
            mod         = import_module('router_mod.juniper')
            cmd_list    = inspect.getmembers(mod, inspect.isfunction)
   
            # sync the nanme with current VChannel instance 
            self._cur_name = self._vchannel._current_name
          
            for cmd,data in cmd_list:
                if not cmd.startswith('_'):
                    def gen_xrun(cmd):
                        def _xrun(self,*args,**kwargs):
                            return self.xrun(cmd,*args,**kwargs)
                        return _xrun
                    setattr(self,cmd,MethodType(gen_xrun(cmd),self))
    
            
        except RobotNotRunningError as e:
            Common.err("RENAT is not running")

   
    def switch(self,name):
        """ Changes the current channel of this router to ``name``

        Rerturns old node name
    
        *Note:* This is identical to VChannel.Switch

        Examples:
        | Router.`Switch`    | vmx11 | 
        | Router.`Cmd`       | show version |
        """
        old_name    = self._cur_name

        self._cur_name = name
        self._vchannel.switch(name)

        return old_name


    def get_ip(self):
        """ Returns the IP address of current node
        Examples:
            | ${router_ip}= | Router.`Get IP` | 
        """
        name    = self._cur_name
        node    = Common.LOCAL['node'][name]
        dev     = node['device']
        ip      = Common.GLOBAL['device'][dev]['ip']

        BuiltIn().log("Got IP address of current node: %s" % (ip))
        return  ip


    def cmd(self,command='',prompt = ''):
        """ Runs the command ``command`` and waits until the prompt defined for this
        router.
        This keyword is identical to ``VChannel.Cmd``

        Examples:

        | Router.`Cmd`   |         set system login user testtest authentication plain-text-password  |  password: | # wait for `password:` |
        | Router.`Cmd`   |         Renat2017     |       password: |  # wait for `password:` |
        | Router.`Cmd`   |         Renat2017     |                 |  # wait for default prompt |
        
        The above sample creates an output likes this:
|   user@vmx11# set system login user testtest authentication plain-text-password
|   New password:Renat2017
|   Retype new password:Renat2017
|
|   [edit]

        """

        result = self._vchannel.cmd(command,prompt)
        return result


    def write(self,cmd_str, wait_str='1s', start_screen_mode=False):
        """ Executes command ``write`` for the current vchannel coressponded to
        this router
        """
        
        result = self._vchannel.write(cmd_str,wait_str,start_screen_mode)
        return result


    def read(self):
        """ Executes command ``read`` for the current vchannel coressponded to
        this router
        """
        
        result = self._vchannel.read()
        return result


    def snap(self, name, *cmd_list):
        """ Remembers the result of a list of command defined by ``cmd_list``

        Use this keyword with `Snap Diff` to get the difference between the
        command's result.
        The a new snapshot will overrride the previous result.
        
        Each snap is identified by its ``name``
        """
        buffer = ""
        for cmd in cmd_list:
            buffer += cmd + "\n"
            buffer += self.cmd(cmd) 
        self._snap_buffer[name] = {} 
        self._snap_buffer[name]['cmd_list'] = cmd_list
        self._snap_buffer[name]['buffer'] = buffer

        BuiltIn().log("Took snapshot `%s`" % name)


    def snap_diff(self,name):
        """ Executes the comman that have been executed before by ``name``
        snapshot and return the difference.

        Difference is in ``context diff`` format
        """

        if not self._snap_buffer[name]: return False
        cmd_list    = self._snap_buffer[name]['cmd_list']
        old_buffer  = self._snap_buffer[name]['buffer']

        buffer = ""
        for cmd in cmd_list:
            buffer += cmd + "\n"
            buffer += self.cmd(cmd) 

        diff = difflib.context_diff(old_buffer.split("\n"),buffer.split("\n"),fromfile=name+":before",tofile=name+":current") 
        result = "\n".join(diff)

        BuiltIn().log(result)
        BuiltIn().log("Took snapshot `%s` and showed the difference" % name)

        return result


    def exec_file(self,file_name,vars='',comment='# ',step=False,str_error='syntax,rror'):
        """ Executes commands listed in ``file_name``
        Lines started with ``comment`` character is considered as comments

        ``file_name`` is a file located inside the ``config`` folder of the
        test case.

        This command file could be written in Jinja2 format. Default usable
        variables are ``LOCAL`` and ``GLOBAL`` which are identical to ``Common.LOCAL`` and
        ``Common.GLOBAL``. More variables could be supplied to the template by ``vars``.

        ``vars`` has the format: ``var1=value1,var2=value2``

        If ``step`` is ``True``, after very command the output is check agains
        an error list. And if a match is found, execution will be stopped. Error
        list is define by ``str_err``, that contains multi regular expression separated
        by a comma. Default value of ``str_err`` is `error`

        A sample for command list with Jinja2 template:
        | show interface {{ LOCAL['extra']['line1'] }}
        | show interface {{ LOCAL['extra']['line2'] }}
        | 
        | {% for i in range(2) %}
        | show interface et-0/0/{{ i }}
        | {% endfor %}

        Examples:
        | Router.`Exec File`   | cmd.lst |
        | Router.`Exec File`   | step=${TRUE} | str_error=syntax,error |


        *Note:* Comment in the middle of the line is not supported
        For example if ``comment`` is "# "
        | # this is comment line <-- this line will be ignored
        | ## this is not an comment line, and will be enterd to the router cli, but the router might ignore this
        """
    
        # load and evaluate jinja2 template
        folder = os.getcwd() + "/config/"
        loader=jinja2.Environment(loader=jinja2.FileSystemLoader(folder)).get_template(file_name)
        render_var = {'LOCAL':Common.LOCAL,'GLOBAL':Common.GLOBAL}
        for pair in vars.split(','):
            info = pair.split("=")
            if len(info) == 2:
                render_var.update({info[0].strip():info[1].strip()})
        
        command_str = loader.render(render_var)
       
        # execute the commands 
        for line in command_str.split("\n"):
            if line.startswith(comment): continue
            str_cmd = line.rstrip()
            if str_cmd == '': continue # ignore null line
            output = self._vchannel.cmd(str_cmd)
   
            if not step: continue 
            for error in str_error.split(','):
                if re.search(error,output,re.MULTILINE):
                    raise Exception("Stopped because matched error after executing `%s`" % str_cmd) 

        BuiltIn().log("Executed commands in file %s" % file_name)

 
    def xrun(self,cmd,*args,**kwargs):
        """ Runs the vendor independent keywords.

        Parametes:
        - ``cmd``: a keyword 
        - ``args``: other argumemts
        
        Examples:
            | Router.`Xrun` | Flap Interface | ge-0/0/0 |
        This keyword will then actually calling the correspond keyword for the
        device type. 
        """ 

        channel = self._vchannel.get_channel(self._cur_name)
        node    = channel['node']
        type_list    = channel['type'].split('_')
        mod_name = ''
        type_list_length = len(type_list)
        for i in range(0,type_list_length):
            mod_name = '_'.join(type_list[0:type_list_length-i])
            try:
                mod  = import_module('router_mod.'+ mod_name)
                break
            except ImportError:
                BuiltIn().log("   Could not find `%s`, try another one" % mod_name)

        BuiltIn().log("    using `%s` mode for command %s" %  (mod_name,cmd))

        mod_cmd = cmd.lower().replace(' ','_')

        result = getattr(mod,mod_cmd)(self,*args,**kwargs)
    
        return result


    def follow_mib( self,node_list,wait_time='10s',interval_time='5s',\
                    len='12',percentile='80',threshold='75',max_len='300',factor = '1'):
        """ Waits until all the nodes defined in ``node_list`` become ``stable``. 

        Stableness is checked by SNMP polling result. The MIB list is define by
        ``mib`` in ``node`` section
        Parameter:
        - ``wait_time(1)``: the time before the evaluation starting
        - ``interval_time(2)``: interval between SNMP polling time
        - ``threshold``: below this value is evaluated as ``stable`` 
        - ``len(3)``: the size of the evaluation window (number of values that
          are used in each valuation)
        - ``percentile``: real useful percentage of data (ignore top
          ``100-percentile`` percent)
        - ``max_len(4)``: maximum waiting ``lend`` for this checking
    
        | time sequence: --(1)--|-(2)-|-----|-----|----|-----|-----|
        |                      <--------(3)---------->     poll  poll 
        |                            <--------(3)----------> 
        |                      <---------------------(4)---------->
        
        """
        time.sleep(DateTime.convert_time(wait_time))

        interval = DateTime.convert_time(interval_time)
        data = {}
        for node in node_list:
            device = Common.LOCAL['node'][node]['device']
            type   = Common.GLOBAL['device'][device]['type']
            data[node] = {}
            data[node]['ip']          = Common.GLOBAL['device'][device]['ip']
            data[node]['community']   = Common.GLOBAL['snmp-template'][type]['community'] 
            data[node]['mib_file']    = Common.mib_for_node(node)
            f = open(data[node]['mib_file'])
            data[node]['oid_list']    = json.load(f)['miblist']
            f.close()
            data[node]['poller'] = netsnmp.SNMPSession(data[node]['ip'], data[node]['community']) 
            data[node]['monitor'] = []

        for i in range(int(len)):
            for node in node_list:
                for oid in data[node]['oid_list']:
                    try:
                        value = float(data[node]['poller'].get(oid['oid'])[0][2])
                    except:
                        value = 0.0
                    data[node]['monitor'].insert(0,value)
            time.sleep(interval)

        stable  = False
        count   = 0 

        BuiltIn().log("Stable checking ...")

        while not stable and count < max_len:
            stable = True
            for node in node_list:
                for oid in data[node]['oid_list']:
                    try:
                        value = float(data[node]['poller'].get(oid['oid'][0][2]))
                    except:
                        value = 0.0
                    data[node]['monitor'].insert(0,value)
                    data[node]['monitor'].pop()
                stable = stable and Common.is_stable(data[node]['monitor'],float(threshold), int(percentile))
                BuiltIn().log("node = %s stable = %s" % (node,stable))
                BuiltIn().log(",".join(str(i) for i in data[node]['monitor']))
                
            count += 1   
            time.sleep(interval)

        if count < max_len:
            BuiltIn().log("Stable checking normaly finished")
        else:
            BuiltIn().log("Stable chekcing forcely finsined")
            
    
    def stop_screen_mode(self):
        """ Stop the screen mode
        """
        return self._vchannel.stop_screen_mode()


    def cmd_and_wait_for(self,command,keyword,interval='30s',max_num=10,error_with_max_num=True):
        """ Execute a command and expect ``keyword`` occurs in the output.
        If not wait for ``interval`` and repeat the process again
       
        After ``max_num``, if ``error_with_max_num`` is ``True`` then the
        keyword will fail. Ortherwise the test continues. 
        """
       
        num = 1 
        BuiltIn().log("Execute command `%s` and wait for `%s`" % (command,keyword))
        while num <= max_num:
            BuiltIn().log("    %d: command is `%s`" % (num,command))
            output = self.cmd(command)
            if keyword in output:
                BuiltIn().log("Found keyword `%s` and stopped the loop" % keyword)
                break;
            else:
                num = num + 1
                time.sleep(DateTime.convert_time(interval))
                BuiltIn().log_to_console('.','STDOUT',True)
        if error_with_max_num and num > max_num:
            msg = "ERROR: Could not found keyword `%s`" % keyword
            BuiltIn().log(msg)
            raise Exception(msg)

        BuiltIn().log("Executed command `%s` and waited for keyword `%s`" % (command,keyword))

    
    # @Common.run_async 
    # def async_cmd(self,cmd,*args):
    #    self.cmd(cmd,*args)
    #   BuiltIn().log("finished " + cmd)
    
###
