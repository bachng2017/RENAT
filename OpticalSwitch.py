# -*- coding: utf-8 -*-
#  Copyright 2017 NTT Communications
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

# $Rev: 898 $
# $Ver: $
# $Date: 2018-04-10 15:33:53 +0900 (火, 10  4月 2018) $
# $Author: $

import requests
import openpyxl
import sys,os,re,glob
import jinja2
import Common
from importlib import import_module
from datetime import datetime
from pprint import pprint
from robot.libraries.BuiltIn import BuiltIn

# expose following keywords
__all__ = ['connect_all','load_from_file','save_to_file','clear_by_file']

class OpticalSwitch(object):
    """ A library provides  control for L1 Optical Switch

    Unlike other device, there is no `Switch` keywork with optical switch.
    Usually user only need to care about the interfaces not the ports of the
    switches.
    """

    ROBOT_LIBRARY_SCOPE = 'TEST SUITE'
    ROBOT_LIBRARY_VERSION = Common.version()

    def __init__(self):
        self._clients   = {}
        self._intf_map  = {} # mapping interface to optical switch port
        self._port_map  = {} # mapping optical switch port to interface


    def connect_all(self):
        """ Connect to all L1 switch and read all neccesary information
        """

        # scan all optic modules
        for item in glob.glob(Common.get_renat_path() + '/optic_mod/[a-zA-Z0-9]*.py'):
            mod_name = os.path.basename(item).replace('.py','')
            BuiltIn().log("    Loaded optic module `%s`" % mod_name)
            mod = import_module('optic_mod.'+mod_name)
            getattr(mod,'_read_map')(self)

        if 'optic' in Common.LOCAL: self._connection = Common.LOCAL['optic']['connection']


        BuiltIn().log("Connected to all L1 switches")


    def close_all(self):
        """ Close all connections
        """
        BuiltIn().log("Closed all switch connections")


    def _mod_by_dev_intf(self,dev,intf):
        """
        """

        # get device type, should be `calient` or `ntm`
        switch_name = self._intf_map[dev][intf]['switch-name']
        type = Common.GLOBAL['device'][switch_name]['type']
        try:
            mod  = import_module('optic_mod.'+ type)
        except ImportError as err:
            msg = "ERROR: Could not find `%s`, try another one" % type
            BuiltIn().log(msg)

        return mod


        
    def get_connection_info(self,dev,intf):
        """ Returns connection information. See details in each module help.
        """

        mod = self._mod_by_dev_intf(dev,intf)
        cmd = sys._getframe(  ).f_code.co_name

        result = getattr(mod,cmd)(self,dev,intf)
        return result


    def add(self,dev1,intf1,dev2,intf2,direction='bi',force=False):
        """ Adds a connection. See details in each module help
        """ 

        mod = self._mod_by_dev_intf(dev1,intf1)
        cmd = sys._getframe(  ).f_code.co_name

        result = getattr(mod,cmd)(self,dev1,intf1,dev2,intf2,direction,force)



    def delete(self,dev1,intf1,dev2,intf2,direction='bi',force=False):
        """ Deletes a connection. See details in each module help
        """

        mod = self._mod_by_dev_intf(dev1,intf1)
        cmd = sys._getframe(  ).f_code.co_name

        result = getattr(mod,cmd)(self,dev1,intf1,dev2,intf2,direction,force)



    def save_to_file(self, file_name):
        """ Saves the current connection of all devices in this test. 

        By default, all interfaces of the devices are save. If a connection
        file is given, only interfaces specified in the connection file are
        saved

        Examples:
        | OpticalSwitch.`Save To File` | save1.conn |
        """

        save_file = open(Common.get_result_path() + '/' + file_name, "w")
        save_file.write("# %s x-connection information saved at %s\n" % (Common.ROBOT_LIBRARY_VERSION, datetime.now()))

        devices = Common.get_test_device() 

        for device in devices:
            if not device in self._intf_map: continue
            for intf,info in self._intf_map[device].iteritems():
                switch_name     = info["switch-name"]
                switch_port     = info["switch-port"]
            
                type = Common.GLOBAL['device'][switch_name]['type']
                mod  = import_module('optic_mod.' + type)
                
                # circuits        = self._get_circuit_from_port(switch_name, switch_port,["incircuit"])
                circuits = getattr(mod,'_get_circuit_from_port')(self,switch_name,switch_port,["incircuit"])
                if len(circuits) < 1: continue
                match  = re.match(r"(.+)(-|>)(.+)", circuits[0]) 
                if match is None: continue
                port1   = match.group(1)
                dir     = match.group(2)
                port2   = match.group(3)
                dev1    = self._port_map[switch_name][port1]["device"]
                intf1   = self._port_map[switch_name][port1]["interface"]
                dev2    = self._port_map[switch_name][port2]["device"]
                intf2   = self._port_map[switch_name][port2]["interface"]
               
                # write the information to file 
                save_file.write("%s,%s,%s,%s,%s\n" % (dev1,intf1,dir,dev2,intf2))

                if dir == '>':   ### need to take care of the other end
                    # more_circuits = self._get_circuit_from_port(switch_name, port2, ["incircuit"]) 
                    more_circuits = getattr(mod,'_get_circuit_from_port')(self,switch_name,port2,["incircuit"])
                    if len(more_circuits) < 1: continue
                    match  = re.match(r"(.+)(-|>)(.+)", more_circuits[0]) 
                    if match is None: continue
                    port1   = match.group(1)
                    dir     = match.group(2)
                    port2   = match.group(3)
                    dev1    = self._port_map[switch_name][port1]["device"]
                    intf1   = self._port_map[switch_name][port1]["interface"]
                    dev2    = self._port_map[switch_name][port2]["device"]
                    intf2   = self._port_map[switch_name][port2]["interface"]
                    save_file.write("%s,%s,%s,%s,%s\n" % (dev1,intf1,dir,dev2,intf2))


        save_file.close()
        BuiltIn().log("Saved x-connection information to `%s`" % file_name)             


    def load_from_file(self,file_name = "", force=True, comment="#"):
        """ Loads the connection file and set the connections
       
        ``filename`` is the name of the connection file under the current config
        folder.  If ``filename`` is empty, the value of ``optic/connection``
        from ``config/local.yaml`` will be used.

        The ``connection file`` supports ``jinja2`` template language. Besides,
        ``#`` is the default comment char which could be changed

        The format of ``connection file`` follows:
        - each connection is described by 1 line 
        - ``source`` and ``destination`` are separated by `` - `` or `` > ``,
          which mean ``bidirection`` or ``unidirection`` (unidirection connects
        ``source tx`` to ``dest rx``

        Connection file sample: 
|       device1:port1 - device2:port2
|       device1:port3 > device2:port

        Examples:
        | OpticalSwitch.`Load From File` |
        | OpticalSwitch.`Load From File` | save1.conn | 
        """

        if file_name == "":
            _file_name = Common.LOCAL['optic']['connection']
        else:
            _file_name = file_name
            
        # load and evaluate jinja2 template
        loader=jinja2.Environment(loader=jinja2.FileSystemLoader(os.getcwd() + '/config/')).get_template(_file_name)
        conn_str = loader.render({'LOCAL':Common.LOCAL,'GLOBAL':Common.GLOBAL})

        # process line by line
        for line in conn_str.split("\n"):
            str = line.partition(comment)[0].strip().lower()
            if str == "": continue
            match = re.match(r"(.+)(:|,)(.+)( |,)(-|>)( |,)(.+)(:|,)(.+)", str)
            if match is None:
                raise Exception("ERROR: Error happened while loading x-connection file: %s -> Format error" % str)
            else:
                dev1    = match.group(1)
                dev2    = match.group(7)
                port1   = match.group(3)
                port2   = match.group(9)
                dir     = match.group(5)

            if dir == "-":
                self.add(dev1,port1,dev2,port2,"bi",force)
            if dir == ">":
                self.add(dev1,port1,dev2,port2,"uni",force)
        BuiltIn().log("Loaded x-connection file ``%s``" % _file_name)

    
    def clear_by_file(self, file_name = "", comment = "#"):
        """ Clears all x-connections defined in the `connection file`

            Default `connection file` is defined in ``optic/connection`` of ``config/local.yaml``
        """

        if file_name == "":
            _file_name = Common.LOCAL['optic']['connection']
        else:
            _file_name = file_name

        # load and evaluate jinja3 template
        loader=jinja2.Environment(loader=jinja2.FileSystemLoader(os.getcwd() + '/config/')).get_template(_file_name)
        conn_str = loader.render({'LOCAL':Common.LOCAL,'GLOBAL':Common.GLOBAL})
        
        # process line by line
        for line in conn_str.split("\n"):
            str = line.partition(comment)[0].strip().lower()
            match = re.match(r"(.+)(:|,)(.+)( |,)(-|>)( |,)(.+)(:|,)(.+)", str)
            if match is None: continue
            dev1    = match.group(1)
            dev2    = match.group(7)
            intf1   = match.group(3)
            intf2   = match.group(9)
            dir     = match.group(5)

            switch1     = self._intf_map[dev1][intf1]["switch-name"]
            switch2     = self._intf_map[dev2][intf2]["switch-name"]
            port1       = self._intf_map[dev1][intf1]["switch-port"]
            port2       = self._intf_map[dev2][intf2]["switch-port"]

            if switch1 != switch2:
                raise Exception("ERROR: Error happened while clear the x-connection from file %s" % file_name)
            
            type = Common.GLOBAL['device'][switch1]['type']
            mod  = import_module('optic_mod.' + type)
            getattr(mod,'_delete_conn_info')(self,switch1,port1,port2,'bi')

        BuiltIn().log("Cleared all x-connections defined in file `%s`" % _file_name)
 
