# -*- coding: utf-8 -*-
#  Copyright 2017-2019 NTT Communications
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


import netsnmp
import time
import sys,os,glob
import re
import csv
import json
import inspect
import Common
from VChannel import VChannel
from importlib import import_module
import robot.libraries.DateTime as DateTime
from robot.libraries.BuiltIn import BuiltIn
from robot.libraries.BuiltIn import RobotNotRunningError
from types import MethodType

# expose following keywords
# __all__ = ['switch','cmd','exec_file','snap','snap_diff','xrun','follow_mib']


class Router(object):
    """ A class provides keywords for router control. An instance of Router
    class automatically assigned methods of a VChannel class (*Note*: this is not
    an inheritance but rather 1-to-1 relation)

    See [./VChannel.html|VChannel] for more details about `VChannel`.

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
        | Router.`Switch`   | vmx12 |
        | Router.`Xrun`      | Load Config |
        | Router.`Load Config` |      |

    """


    ROBOT_LIBRARY_SCOPE = 'TEST SUITE'
    ROBOT_LIBRARY_VERSION = Common.version()


    def __init__(self):
        folder = os.path.dirname(__file__)
        sys.path.append(folder)
        try:
            self._vchannel = BuiltIn().get_library_instance('VChannel')

            if self._vchannel is None:
                raise Exception("Could not find an instance of VChannel. Need import VChannel first")
            else:
                keyword_list = inspect.getmembers(self._vchannel,inspect.ismethod)
                for keyword,body in keyword_list:
                    if not keyword.startswith('_'):
                        setattr(self,keyword,body)

            # sync the nanme with current VChannel instance
            self._cur_name = self._vchannel._current_name

            #
            mod_list = glob.glob(Common.get_renat_path() + '/router_mod/*.py')
            keyword_list = []
            for item in mod_list:
                # BuiltIn().log_to_console(item)
                if item.startswith('_'): continue
                mod_name = os.path.basename(item).replace('.py','')
                # BuiltIn().log_to_console(mod_name)
                mod  = import_module('router_mod.' + mod_name)

                cmd_list    = inspect.getmembers(mod, inspect.isfunction)
                for cmd,data in cmd_list:
                    if not cmd.startswith('_') and cmd not in keyword_list:
                        keyword_list.append(cmd)
                        # BuiltIn().log_to_console('   ' + cmd)
                        def gen_xrun(cmd):
                            def _xrun(self,*args,**kwargs):
                                return self.xrun(cmd,*args,**kwargs)
                            return _xrun
                        setattr(self,cmd,MethodType(gen_xrun(cmd),self))

        except RobotNotRunningError as e:
            Common.err("WARN: RENAT is not running")



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
        channel = self.get_current_channel()
        node    = channel['node']
        # type_list    = channel['type'].split('_')
        type_list = re.split(r'-|_', channel['type'])
        mod_name = ''
        type_list_length = len(type_list)

        mod_cmd = cmd.lower().replace(' ','_')

        # go from detail mod to common mode
        for i in range(0,type_list_length):
            mod_name = '_'.join(type_list[0:type_list_length-i])
            try:
                mod  = import_module('router_mod.'+ mod_name)
                if hasattr(mod,mod_cmd):
                    break
            except ImportError:
                BuiltIn().log("    Could not find `%s`, try another one" % mod_name)

        BuiltIn().log("    using `%s` mod for command `%s`" %  (mod_name,cmd))
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
            data[node]['mib-file']    = Common.mib_for_node(node)
            f = open(data[node]['mib-file'])
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

        max_len_value = int(max_len)
        while not stable and count < max_len_value:
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

        if count < max_len_value:
            BuiltIn().log("Stable checking normaly finished")
        else:
            BuiltIn().log("Stable chekcing forcely finsined")



