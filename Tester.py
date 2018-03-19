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

# $Date: 2018-03-20 02:58:07 +0900 (Tue, 20 Mar 2018) $
# $Rev: 822 $
# $Ver: 0.1.7 $
# $Author: bachng $

import sys
import os
import re
import csv
import inspect
import yaml
import time
import Common
import IxNetwork
import SubIxLoad
from datetime import datetime
from robot.libraries.BuiltIn import BuiltIn
import robot.libraries.DateTime as DateTime
from importlib import import_module
from robot.libraries.BuiltIn import RobotNotRunningError
from types import MethodType
import multiprocessing

# expose following keywords
__all__ = ['switch','connect','connect_all','close_all']


class Tester(object):
    """ A class provides keywords for controlling testers and traffic
    generators.
    It could load predefined traffic file, manipulate traffic item, start and
    stop traffic flows. It also could generate traffic reports ...

    Tester information is stored in the active ``local.yaml`` likes this:

| tester:
|     tester01:
|         device: ixnet03_8009
|         config: vmx_20161129.ixncfg
|         real_port:
|            -   chassis: 10.128.32.71
|                card: 6
|                port: 11
|            -   chassis: 10.128.32.71
|                card: 6
|                port: 9

where ``device`` is the tester defined in the master ``device.yaml`` file.
If ``real_port`` does not exist, port remapping will not take place.
Otherwise, port remapping will use the ``real_port`` information to reassign
all existed ports and map to Ixia ports.

In this case, the order will be the order when user created the port in Ixia
GUI. *Note:* User can always confirm the created order by ``clear sorting`` in
Ixia GUI

    Examples:
    | Tester.`Connect All` |
    | Tester.`Switch` | tester01 |
    | Tester.`Load And Start Traffic` |
    | `Sleep` | 30s |
    | Tester.`Stop Traffic` |

Time format used in this module is same with ``time string`` format of Robot Framework. 
For more details about this, see [http://robotframework.org/robotframework/latest/libraries/DateTime.html|DateTime] 
library of Robot Framework.

*Note:* See [./tester_mod_ixnet.html|IxNet module],
[./tester_mod_ixload.html|IxLoad module] for details about keyword of each
module.

"""

    ROBOT_LIBRARY_SCOPE = 'TEST SUITE'
    ROBOT_LIBRARY_VERSION = Common.version()

    ### 
    def __init__(self):
        folder = os.path.dirname(__file__)
        sys.path.append(folder)

        self._clients   = {}
        self._cur_name  = ""

        try:
            BuiltIn().get_library_instance('VChannel')

            # using ixnet as a base mod for method name
            mod         = import_module('tester_mod.ixnet')
            cmd_list = inspect.getmembers(mod, inspect.isfunction)
    
            for cmd,data in cmd_list:
                if not cmd.startswith('_'):
                    def gen_xrun(cmd):
                        def _xrun(self,*args,**kwargs):
                            return self._xrun(cmd,*args,**kwargs)
                        return _xrun
                    setattr(self,cmd,MethodType(gen_xrun(cmd),self))

        except RobotNotRunningError as e:
            Common.err("RENAT is not running") 

    def switch(self,name):
        """ Switchs the current tester to ``name``
        """

        self._cur_name = name
        BuiltIn().log("Switched to tester " + name)


    def connect(self,name):
        """ Connect to the tester ``name``
        """

        dname   = Common.LOCAL['tester'][name]['device']
        ip      = Common.GLOBAL['device'][dname]['ip']
        desc    = Common.GLOBAL['device'][dname]['description']
        type    = Common.GLOBAL['device'][dname]['type']
        if 'port' in Common.GLOBAL['device'][dname]: port = Common.GLOBAL['device'][dname]['port']

    
        client = {}
        client['type']  = type
        client['ip']    = ip
        client['desc']  = desc
   
        if type == 'ixnet':
            ix = IxNetwork.IxNet()
            client['port']    = port
            ix.connect(ip,'-port',port,'-version','7.41')
            client['connection'] = ix
        elif type == 'ixload':
            tmp = os.getcwd().split('/')
            # win_folder = "D:/RENAT/RESULTS/%s_%s" % (tmp[-2],tmp[-1])
            win_case = "%s_%s" % (tmp[-2],tmp[-1])

            # start IxLoad in different process
            tasks   = multiprocessing.JoinableQueue()
            results = multiprocessing.Queue()
            ix_process = SubIxLoad.SubIxLoad(win_case, tasks, results)
            client['connection']    = ix_process
            client['tasks']         = tasks
            client['results']       = results

            BuiltIn().log_to_console("RENAT: created new process that run IxLoad client") 
            ix_process.start()
            tasks.put(['ixload::connect',ip])
            tasks.join()
            results.get()

        else:
            raise Execption("Error while connecting IxNetwork: wrong module type")
    
        self._clients[name] = client
        self._cur_name = name
    
        BuiltIn().log("Connected to tester `%s`(%s)" % (self._cur_name,ip))



    def connect_all(self):
        """ Connects to all testers
        """
        if 'tester' in Common.LOCAL and not Common.LOCAL['tester']: 
            BuiltIn().log("No valid tester configuration found")
            return True
        for entry in Common.LOCAL['tester']: 
            BuiltIn().log(entry)
            self.connect(entry) 

        BuiltIn().log("Connected to all %d testers" % len(self._clients))


    def close_all(self):
        """ Closes all connections
        """
        for entry in self._clients:
            self.switch(entry)
            self.close()
        self._cur_name = ""
        BuiltIn().log("Closed all connections") 


    def _xrun(self,cmd,*args,**kwargs):
        """ Local method for execute module command
        At this time, connection has been already made
        """
        BuiltIn().log("xrun for command %s" % cmd)

        client  = self._clients[self._cur_name]
        type    = client['type']
        mod     = import_module('tester_mod.'+ type)

        BuiltIn().log("    using `%s` module " %  type)

        mod_cmd = cmd.lower().replace(' ','_')

        # node is string and channel is Vchannel instance
        result = getattr(mod,mod_cmd)(self,*args,**kwargs)

        return result
