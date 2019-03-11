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

# $Date: 2019-03-02 10:16:09 +0900 (土, 02  3月 2019) $
# $Rev: 1865 $
# $Ver: $
# $Author: $

from pyVim.connect import SmartConnect, Disconnect
import ssl,atexit,codecs
import Common
import SSHLibrary
import sys,os,glob,inspect
from importlib import import_module
from types import MethodType
from robot.libraries.BuiltIn import BuiltIn
from robot.libraries.BuiltIn import RobotNotRunningError

class Hypervisor(object):
    """ A module controls Hypervisors

    A hypervisor is declared in ``local.yaml`` like this:
| # esxi information
| hypervisor:
|    esxi-server:
|        device: esxi-3-15
 
 
    *Notes:* Currently support VMWare(Esxi) only
    """

    ROBOT_LIBRARY_SCOPE = 'TEST SUITE'
    ROBOT_LIBRARY_VERSION = Common.version()


    def __init__(self): 
        self._current_name = None
        self._current_id = None
        self._channels = {}
        self._max_id = 0
        self._ssh_prompt = '\[.*@.*\] ' 
        self._ssh_lib = SSHLibrary.SSHLibrary()

        # ignore SSL verify
        self._ssl_context = ssl._create_unverified_context()

        try:
            mod_list = glob.glob(Common.get_renat_path() + '/hypervisor_mod/*.py')
            keyword_list = []
            for item in mod_list:
                if item.startswith('_'): continue
                mod_name = os.path.basename(item).replace('.py','')
                mod  = import_module('hypervisor_mod.' + mod_name)
            
                cmd_list    = inspect.getmembers(mod, inspect.isfunction)
                for cmd,data in cmd_list:
                    if not cmd.startswith('_') and cmd not in keyword_list:
                        keyword_list.append(cmd)
                        def gen_xrun(cmd):
                            def _xrun(self,*args,**kwargs):
                                return self.xrun(cmd,*args,**kwargs)
                            return _xrun
                        setattr(self,cmd,MethodType(gen_xrun(cmd),self))
        except RobotNotRunningError as e:
            Common.err("WARN: RENAT is not running")
     
   
    def connect(self,hyper,name):
        """ Connects to a Hypervisor
        """
        ignore_dead_node = Common.get_config_value('ignore-dead-node')
        _hyper          = Common.LOCAL['hypervisor'][hyper]['device']
        _ip             = Common.GLOBAL['device'][_hyper]['ip']
        _type           = Common.GLOBAL['device'][_hyper]['type']
        _access_tmpl    = Common.GLOBAL['access-template'][_type]
        _access         = _access_tmpl['access']
        _auth_type      = _access_tmpl['auth'] 
        _profile        = _access_tmpl['profile']
        _auth           = Common.GLOBAL['auth'][_auth_type][_profile]
        _driver         = None

        try:
            channel_info = {}
            if _access == 'vmware':
                # register information
                id = self._max_id + 1
            
                conn = SmartConnect(host=_ip,user=_auth['user'],pwd=_auth['pass'],sslContext=self._ssl_context) 

                ssh_id = self._ssh_lib.open_connection(_ip,alias=name+'_ssh',term_type='vt100')
                output = self._ssh_lib.login(_auth['user'],_auth['pass'])
                self._ssh_lib.write('unalias -a')
                self._ssh_lib.read_until_regexp(self._ssh_prompt)
                result_folder = Common.get_result_path()
                log_file = name + '_ssh.log'
                _logger = codecs.open(result_folder + "/" + log_file,'w','utf-8') 
                _logger.write(output)
                # atexit.register(Disconnect,conn) 
                #
                channel_info['id'] = id
                channel_info['ip'] = _ip
                channel_info['type'] = _type
                channel_info['access-type'] = 'vmware-esxi'
                channel_info['connection'] = conn
                channel_info['ssh'] = self._ssh_lib
                channel_info['ssh_logger'] = _logger
                channel_info['capture_counter'] = 0
                channel_info['capture_format'] = 'vmware_%010d'
            
            self._max_id = id
            self._current_id = id
            self._current_name = name    

            self._channels[name]   = channel_info
            self._current_channel_info = channel_info
        except Exception as err:
            if ignore_dead_node:
                msg = 'WARN: Error when connecting to `%s(%s)` bug ignored' % (name,_ip)
                BuiltIn().log(msg)
            else:
                msg = 'ERROR: Error when connecting to `%s(%s)` bug ignored' % (name,_ip)
                BuiltIn().log(msg)
                raise
        BuiltIn().log('Connected to `%s(%s)`' % (name,_ip))
        return id


    def switch(self,name):
        """ Switch the current hypervisor to a new one
        """
        if name in self._channels:
            channel = self._channels[name]
            self._current_channel_info = channel
            self._current_id = channel['id']
            BuiltIn().log('Switched current hypervisor to `%s(%s)`' % (name,channel['ip'])) 
        else:
            msg = "ERROR: Could not find `%s` in current hypervisors" % name
            BuiltIn().log(msg)
            raise Exception(msg)            


    def connect_all(self,prefix=''):
        """ Connect to *all* hypervisor listed in local config yaml
        """
        num = 0
        if not 'hypervisor' in Common.LOCAL or not Common.LOCAL['hypervisor']:
            BuiltIn().log('WARNING: No hypervisors included')
            return True
        else: 
            for term in Common.LOCAL['hypervisor']:
                alias = prefix + term
                self.connect(term,alias)
                num += 1
        BuiltIn().log('Connected to all %d hypervisors' % num)


    def close(self):
        """ Closes and disconnects from a hypervisor
        """
        # self._channels[self._current_name]['connection'].Disconnect()
        channel = self._channels[self._current_name]
        Disconnect(channel['connection'])
        channel['ssh'].switch_connection(self._current_name+'_ssh')
        channel['ssh'].close_connection()
        channel['ssh_logger'].flush()
        channel['ssh_logger'].close()
        del(self._channels[self._current_name])

        # choose another active channel
        if len(self._channels) == 0:
            self._current_name = ''
            self._current_id = 0
            self._max_id = 0
        else:
            first = list(self._channels.keys())[0]
            self._current_name = self._channels[first]['name']
            self._current_id = self._channel[first]['id']

        return self._current_name


    def close_all(self):
        """ Closes all current opend hypervisor connection
        """ 
        while len(self._channels) > 0:
            self.close()

        self._current_id = 0
        self._max_id = 0
        self._current_name = None
        self._channels = {}
        BuiltIn().log('Closed all hypervision connections')


    def xrun(self,cmd,*args,**kwargs):
        """
        """
        channel     = self._channels[self._current_name]
        type_list   = channel['type'].split('_')
        type_list_length = len(type_list)

        mod_name = ''
        mod_cmd = cmd.lower().replace(' ','_')

        # go from detail mod to common mode
        for i in range(0,type_list_length):
            mod_name = '_'.join(type_list[0:type_list_length-i])
            try:
                mod  = import_module('hypervisor_mod.'+ mod_name)
                if hasattr(mod,mod_cmd):
                    break
            except ImportError:
                BuiltIn().log("   Could not find `%s`, try another one" % mod_name)

        BuiltIn().log("    using `%s` mod for command `%s`" %  (mod_name,cmd))
        result = getattr(mod,mod_cmd)(self,*args,**kwargs)

        return result        
