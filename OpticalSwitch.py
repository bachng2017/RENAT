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

# $Rev: 621 $
# $Date: 2018-01-21 16:19:12 +0900 (Sun, 21 Jan 2018) $
# $Author: $

import requests
import openpyxl

import sys,os,re
import jinja2
import Common
from datetime import datetime
from pprint import pprint
from robot.libraries.BuiltIn import BuiltIn

class OpticalSwitch(object):
    """ A library provides  control for L1 Optical Switch (currently Calient)

    ``OpticalSwitch`` is a RENAT library that provides control for L1 optical
    switch. Currently the library only supports Calient.

    == Table of Contents ==

    - `Master file`
    - `Connection file Format`
    - `Shortcuts`
    - `Keywords`

= Master file =
    The L1 switch provides a mechanism to remotely connect device interface.
    Each device interface has been wired to L1 switch already. The connection
    was described in the master file located specific by `calient-master-path`
    in the configuration file `renat/config/config.yaml`. 

    The master file includes several Calients in each tab. The column meaning
    and order is trivial.

= Connection file Format =
    Keywords `Load From File`, `Clear By File` and `Save To File` use the
    x-connection file. The connection has following rules:

    Connection files are text files and have the following format:

|   # this is the comment
|   device1,interface1,-,device2,interface2
|   device1,interface1,>,device2,interface2
    
    The separator ``-`` means a bidirection connection and ``>`` means a unidirection
    connection. For a unidirection connection, ``device1/interface1`` TX will be
    connected to ``device2/interface2`` RX. 
    
    *Note:* The separator character must be surrounded by spaces or commas.

    The connection file also support jinja2 template format. After the template
    is evaluated, comment could be used by ``comment char``

    There is no need to specify which L1 switch for the x-connection. The system
    will automatically find the appropriate switch. 

    """

    ROBOT_LIBRARY_SCOPE = 'TEST SUITE'
    ROBOT_LIBRARY_VERSION = Common.version()

    def __init__(self):
        self._clients = {}
        self._intf_map = {} # mapping interface to optical switch port
        self._port_map = {} # mapping optical switch port to interface
        self._connection = ""

    def connect_all(self):
        self.read_map()
        BuiltIn().log("Connected to all switches")

    def close_all(self):
        BuiltIn().log("Closed all switch connections")

    def read_map(self):
        """ Reads the master port map file
        """

        ### create the master port-map
        _folder = os.path.dirname(__file__)
        _calient_file = _folder + "/tmp/calient.xlsx"
        # print _calient_file
        wb = openpyxl.load_workbook(_calient_file,data_only=True)
        for sheet in wb.worksheets:
            switch_name = sheet.title

            if switch_name not in self._port_map: self._port_map[switch_name] = {}

            cells = sheet['B3': 'D326']
            for c1,c2,c3 in cells:
                if any(x is None for x in [c1.value,c2.value,c3.value]): continue
                port    = unicode(c1.value).lower() 
                device  = unicode(c2.value).lower()
                intf    = unicode(c3.value).lower()
                if device not in self._intf_map: self._intf_map[device] = {}

                self._intf_map[device][intf] = {}
                self._intf_map[device][intf]["switch-name"] = switch_name
                self._intf_map[device][intf]["switch-port"] = port

                self._port_map[switch_name][port] = {}
                self._port_map[switch_name][port]["device"] = device
                self._port_map[switch_name][port]["interface"] = intf

        # create session to all optical switch
        for entry in Common.GLOBAL['device']:
            dev_type  = Common.GLOBAL['device'][entry]['type']  

            if dev_type != 'calient': continue  # only deal with calient type
            ip      = Common.GLOBAL['device'][entry]['ip']  

            session = requests.Session()
            credentials = Common.GLOBAL['auth']['plain-text']['calient']
            session.auth = (credentials['user'],credentials['pass'])
   
            self._clients[entry] = {} 
            self._clients[entry]['ip']          = ip
            self._clients[entry]['session']     = session
            self._clients[entry]["cookies"]     = ""

        # load local physical connection file
        if 'optic' in Common.LOCAL: 
            self._connection = Common.LOCAL['optic']['connection']
        


    def _get_circuit_from_port(self,switch,switch_port_id,circuit_types):
        """ Returns a list of circuit that this `switch-port-id` belongs to

        The `circuit_types` includes ``incircuit`` , ``outcircuit`` or ``empty`` if there
        is no cicicuit at all
        """
        cli = self._clients[switch]
        session = cli['session']
        ip = cli['ip']
        result = []
        rest_result = session.get("http://%s/rest/ports/?id=detail&port=%s" % (ip,switch_port_id))
        if rest_result.status_code == requests.codes.ok:
            for entry in circuit_types:
                tmp = rest_result.json()[0][entry]
                if tmp != "": result.append(tmp)
        return result


    def _make_conn_info(self,dev1,port1,dev2,port2,dir='bi'):
        """ Returns `switch_name` and ``conn_id`` if available.
        and returns ``None`` if the connection stretches over multi optic
        switches  
        """
        sw1 = self._intf_map[dev1][port1]['switch-name']
        sw2 = self._intf_map[dev1][port1]['switch-name']

        if sw1 != sw2:
            return ()
        else:
            s1 = self._intf_map[dev1][port1]['switch-port'] 
            s2 = self._intf_map[dev2][port2]['switch-port'] 

            if dir == 'bi':
                connect = '-'
            else:
                connect = '>'
            return (sw1, s1+connect+s2, s1 ,s2, connect)


    def get_connection_info(self,dev,intf):
        """ Returns information of the optic switch port that connected to
        ``dev:intf``. The information is in jason format.

        Examples:

        | OpticalSwitch.`Get Connection Info` |  mx2008-31-33 | xe-3/0/1 |
        return information looks like below:
| result = {u'outoc': u'NOHW', u'outopwdh': u'-20.0', u'inos': u'OOS',
| u'outalias': u'', u'inowner': u'TRANSIT', u'outopwct': u'-23.0', u'inpower':
| u'-3.4', u'inas': u'IS', u'outpower': u'-4.8', u'outas': u'OOS-NP', u'inopt':
| u'-17.0', u'inopth': u'13.0', u'incircuit': u'3.3.1>3.3.2', u'inalias': u'',
| u'inoc': u'NOHW', u'inoptc': u'-20.0', u'outos': u'OOS', u'port': u'3.3.1',
| u'outowner': u'NONE', u'outcircuit': u''}

        """
        sport   = self._intf_map[dev][intf]['switch-port']
        switch  = self._intf_map[dev][intf]['switch-name']
        cli     = self._clients[switch]
        ip      = cli['ip']
        session = cli['session']

        rest_result = session.get("http://"+ip+"/rest/ports/?id=detail&port="+sport)
        if rest_result.status_code == requests.codes.ok:
            BuiltIn().log("result = %s" % rest_result.json()[0])
            return rest_result.json()[0]
        else:
            raise Exception("Error when collect port information")


    def _delete_conn_info(self, switch, port1, port2, dir):
        """ Deletes existed connection between ``port1`` and ``port2`` an the switch
        """
        cli     = self._clients[switch]
        ip      = cli["ip"] 
        session = cli["session"]

        if dir == "bi":
            tmp1 = self._get_circuit_from_port(switch,port1,['incircuit','outcircuit'])
            tmp2 = self._get_circuit_from_port(switch,port2,['incircuit','outcircuit'])
            circuits = list(set(tmp1 + tmp2))
        else:
            tmp1 = self._get_circuit_from_port(switch,port1,['incircuit'])
            tmp2 = self._get_circuit_from_port(switch,port2,['outcircuit'])
            circuits = list(set(tmp1 + tmp2))
                
        for item in circuits:
            rest_result = session.delete('http://'+ip+'/rest/crossconnects/?conn=' + item)
            if rest_result.status_code != requests.codes.ok:
                BuiltIn().log("Failed to delete the x-connection")
                return False
            else:
                BuiltIn().log("Deleted x-connection `%s` on switch %s" % (item,switch))

        return True


    def add(self,dev1,intf1,dev2,intf2,direction='bi',force=False):
        """ Adds x-connection between ``dev1:intf1`` and ``dev2:intf2``

        ``direction`` is ``bi`` for bi-direction or ``uni`` for uni-direction.
        If ``direction`` is ``uni``, the tx of ``dev 1:port 1`` will be connected
        to ``dev 2:port 2``.

        With ``force`` mode, existed connection that use those ports will be deleted. 
        Without ``force`` mode, an existed connection will make the keyword
        fails

        Examples:

        | OpticalSwitch.`Add` | mx2008-31-33 | xe-3/0/0 | mx2008-31-33 | xe-3/0/1 | bi | ${TRUE} |

        *Note:* For a bidirection connection, 2 single uni-direction connection
        will be made instead of 1 bi-direction connection. This will make the link could
        be simulated tx/rx failure later.
        """

        BuiltIn().log("Adds %s connection %s:%s %s:%s" % (direction,dev1,intf1,dev2,intf2))

        switch  = ''
        conn_id = ''
        port1   = ''
        port2   = ''
        result  = False

        conn_info = self._make_conn_info(dev1,intf1,dev2,intf2,direction)
        
        if conn_info:
            switch  = conn_info[0]
            conn_id = conn_info[1]
            port1   = conn_info[2]
            port2   = conn_info[3]
        else:
            return False

        cli     = self._clients[switch]
        ip      = cli['ip']
        session = cli['session']
    
        # delete existed connection in Force mode    
        if force: 
            self._delete_conn_info(switch, port1, port2, direction)
        else:
            tmp1 = self._get_circuit_from_port(switch,port1,['incircuit','outcircuit'])
            tmp2 = self._get_circuit_from_port(switch,port2,['incircuit','outcircuit'])
            circuits = list(set(tmp1 + tmp2))

            if circuits:
                raise Exception("Ports are being used: %s:%s by %s, %s:%s by %s" % (dev1,intf1,str(tmp1),dev2,intf2,str(tmp2))) 

        if direction.lower() == 'bi':
            rest_result1 = session.post('http://'+ip+'/rest/crossconnects/',data={'id':'add','in':port1,'out':port2,'dir':'uni'})
            rest_result2 = session.post('http://'+ip+'/rest/crossconnects/',data={'id':'add','in':port2,'out':port1,'dir':'uni'})

            if rest_result1.status_code == requests.codes.ok and rest_result2.status_code == requests.codes.ok:  
                result = True
                msg1    = rest_result1.json()[0]['msg']
                desc1   = rest_result1.json()[0]['description']
                msg2    = rest_result2.json()[0]['msg']
                desc2   = rest_result2.json()[0]['description']
                # BuiltIn().log("Result: msg1 = %s, desc1 = %s" % (msg1,desc1))
                # BuiltIn().log("Result: msg2 = %s, desc2 = %s" % (msg2,desc2))
                if rest_result1.json()[0]['status'] == "1" and rest_result2.json()[0]['status'] == "1":
                    result = True
                    BuiltIn().log("Added connection %s on switch %s, connects %s:%s - %s:%s" % (conn_id,switch,dev1,intf1,dev2,intf2))
                else:
                    result = False
                    raise Exception("Failed to add a binary x-connection (%s,%s)(%s,%s)" % (msg1,desc1,msg2,desc2))
            else:
                result = False
                raise Exception("REST API failed (%d,%d) while trying to add a binary x-connection" % (rest_result1.status_code, rest_result2.status_code))
        else:
            rest_result = session.post('http://'+ip+'/rest/crossconnects/',data={'id':'add','in':port1,'out':port2,'dir':'uni'})
            if  rest_result.status_code == requests.codes.ok:
                result = True
                msg = rest_result.json()[0]['msg']
                desc = rest_result.json()[0]['description']
                BuiltIn().log("Result: msg = %s, desc = %s" % (msg,desc))
                if rest_result.json()[0]['status'] == "1":
                    result = True
                    BuiltIn().log("Added connection %s on switch %s, connects %s:%s > %s:%s" % (conn_id,switch,dev1,port1,dev2,port2))
                else:
                    result = False
                    raise Exception("Failed to add a uni x-connection (%s,%s)" % (msg,desc))
            else:
                result = False
                raise Exception("REST API failed (%d) while truing to an uni add x-connction" % (rest_result.status_code))
        return result
  

    def delete(self,dev1,intf1,dev2,intf2,direction='bi'):
        """ Deletes the connection between ``dev1:intf1 - dev2:intf2``

        Examples:
        | OpticalSwitch.`Delete` | mx2008-31-33 | xe-3/0/1 | mx2008-31-33 | xe-3/0/1 |  uni |

        """
        switch  = ''
        conn_id = ''
        port1   = ''
        port2   = ''

        conn_info = self._make_conn_info(dev1,intf1,dev2,intf2)
        if conn_info:
            switch  = conn_info[0]
            conn_id = conn_info[1]
            port1   = conn_info[2]
            port2   = conn_info[3]
        else:
            return False

        cli     = self._clients[switch]
        ip      = cli['ip']
        session = cli['session']
        result  = False
        ## make uniq list
        if direction.lower() == "bi":
            tmp1 = self._get_circuit_from_port(switch,port1,['incircuit','outcircuit'])
            tmp2 = self._get_circuit_from_port(switch,port2,['incircuit','outcircuit'])
            circuits = list(set(tmp1 + tmp2))
        else:
            tmp1 = self._get_circuit_from_port(switch,port1,['incircuit'])
            tmp2 = self._get_circuit_from_port(switch,port2,['outcircuit'])

            circuits = list(set(tmp1 + tmp2))

        if len(circuits) == 0:
            BuiltIn().log("The connection is not valid")
        
        for item in circuits:
            rest_result = session.delete('http://' + ip+ '/rest/crossconnects/?conn=' + item)
            if rest_result.status_code == requests.codes.ok:
                stat = rest_result.json()[0]['status']
                msg = rest_result.json()[0]['msg']
                desc = rest_result.json()[0]['description']
                BuiltIn().log("Result: status = %s, msg = %s, desc = %s" % (stat,msg,desc))
                if stat == "1":
                    result = True
                    BuiltIn().log("Deleted connection %s on switch %s" % (item,switch))
                else:
                    result = False
                    raise Exception("Failed to make the connection(%d,%s,%s)" % (rest_result.status_code,msg,desc))
                    break
            else:
                result = False
                raise Exception("Failed to delete the connection %s (%d)" % (item,rest_result.status_code))
                break 
 
        return result

    
    def save_to_file(self, file_name):
        """ Saves the current connection of all devices in this test. 

        By default, all interfaces of the devices are save. If a connection
        file is given, only interfaces specified in the connection file are saved

        Examples:
        | OpticalSwitch.`Save To File` | save1.conn |
        """

        save_file = open(os.getcwd() + "/config/" + file_name, "w")
        save_file.write("# RENAT x-connection information saved at %s\n" % datetime.now())

        devices = Common.get_test_device() 

        for device in devices:
            if not device in self._intf_map: continue
            for intf,info in self._intf_map[device].iteritems():
                switch_name     = info["switch-name"]
                switch_port     = info["switch-port"]
                
                circuits        = self._get_circuit_from_port(switch_name, switch_port,["incircuit"])
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

                save_file.write("%s,%s,%s,%s,%s\n" % (dev1,intf1,dir,dev2,intf2))

                if dir == '>':   ### need to take care of the other end
                    more_circuits = self._get_circuit_from_port(switch_name, port2, ["incircuit"]) 
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
        folder.  If ``filename`` is empty, the value of ``optic/connection`` from
        ``config/local.yaml`` will be used.

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
                raise Exception("Error while loading x-connection file: %s -> Format error" % str)
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
                raise Exception("Error while clear the x-connection from file %s" % file_name)

            self._delete_conn_info(switch1, port1,port2, 'bi')

        BuiltIn().log("Cleared all x-connections defined in file `%s`" % _file_name)



#
#    def restore(self,restore_file):
#        """ Restores the x-connection saved by keyword ``Backup``
#
#        *Note: * The ```restore_file``` has different format with the format used by
#        ```Load File```keyword
#        """
#
#        lines = []
#        with open(os.getcwd() + "/config/"+ restore_file) as file: lines = file.readlines()
#
#        result = False
#        for line in lines:
#            if line.startswith("#"): continue
#            match = re.match(r"(.+),(.+)(-|>)(.+)", line)
#            if match is None: continue
#            switch  = match.group(1)
#            p1      = match.group(2)
#            p2      = match.group(4)
#            dir     = match.group(3)
#            cli     = self._clients[switch]
#            session = cli["session"]
#            ip      = cli["ip"]
#
#            ### cleanup existed connections
#            self._delete_conn_info(switch, p1, p2)
#
#            ### restore the x-connections
#            if dir == "-":
#                direction = "Bi"
#            else:
#                direction = "Uni"
#            rest_result = session.post('http://'+ip+'/rest/crossconnects/',data={'id':'add','in':p1,'out':p2,'dir':direction})
#            if rest_result.status_code == requests.codes.ok:
#                msg     = rest_result.json()[0]["msg"]
#                desc    = rest_result.json()[0]["description"]
#                BuiltIn().log("Result: msg = %s, desc = %s" % (msg,desc))
#                if rest_result.json()[0]["status"] == "1":
#                    result = True
#                    BuiltIn().log("Restored: %s" % line)
#                else:
#                    result = False
#                    BuiltIn().log("Failed to restore: %s" % line)
#            else:
#                result = False
#                raise Exception("REST API failed (%d)" % (rest_result.status_code))
#
#        BuiltIn().log("Restored %d x-connections from file `%s`" % (len(lines),restore_file))
#        return result
#
#                
#
#    def backup(self,backup_file, xconnect_file = "", comment="#"):
#        """ Stores the current x-connection that related to ports defined by
#        x-connection ``file_name``
#        """
#        if xconnect_file  == "":
#            _file_name = Common.LOCAL['optic']['connection']
#        else:
#            _file_name = xconnect_file
#           
#        backup = open(os.getcwd() + "/config/" + backup_file, "w")
#        backup.write("# RENAT x-connection backup %s\n" % datetime.now())
#         
#            
#        # load and evaluate jinja2 template
#        loader=jinja2.Environment(loader=jinja2.FileSystemLoader(os.getcwd() + '/config/')).get_template(_file_name)
#        conn_str = loader.render({'LOCAL':Common.LOCAL,'GLOBAL':Common.GLOBAL})
#
#        # process line by line
#        for line in conn_str.split("\n"):
#            str = line.partition(comment)[0].strip().lower()
#            match = re.match(r"(.+)(:|,)(.+) (-|>) (.+)(:|,)(.+)", str)
#            if match is None: continue
#            dev1    = match.group(1)
#            dev2    = match.group(5)
#            port1   = match.group(3)
#            port2   = match.group(7)
#
#            conn_info = self._make_conn_info(dev1,port1,dev2,port2)
#            if not conn_info: continue
#            switch  = conn_info[0]
#            conn_id = conn_info[1]
#            s1      = conn_info[2]
#            s2      = conn_info[3]
#
#            cli     = self._clients[switch]
#            ip      = cli['ip']
#            session = cli['session']
#    
#            tmp1 = self._get_circuit_from_port(switch,s1,['incircuit','outcircuit'])
#            tmp2 = self._get_circuit_from_port(switch,s2,['incircuit','outcircuit'])
#            circuits = list(set(tmp1 + tmp2))
#            for entry in circuits:
#                backup.write("%s,%s\n" % (switch,entry))                
#
#        backup.close()
#        BuiltIn().log("Made backup information and wrote to file `%s`" % backup_file)
#
