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

# $Rev: 1187 $
# $Ver: $
# $Date: 2018-08-19 01:04:35 +0900 (日, 19 8 2018) $
# $Author: $


""" A library provides control for Calient Optical Switch

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
    x-connection file. X-connection files are text files and have the following format:

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


import requests
import openpyxl

import sys,os,re
import jinja2
import Common
from datetime import datetime
from robot.libraries.BuiltIn import BuiltIn

def _read_map(self):
    """ Reads the master port map file

    Make lower for all informations.
    """

    ### create the master port-map
    BuiltIn().log("        Use `%s` for cable x-connect" % Common.newest_calient)

    _folder = os.path.dirname(__file__)
    _calient_file = _folder + "/../tmp/calient.xlsm"

    wb = openpyxl.load_workbook(_calient_file,data_only=True)
    for sheet in wb.worksheets:
        switch_name = sheet.title

        if switch_name not in self._port_map: self._port_map[switch_name] = {}

        cells = sheet['B3': 'D326']
        for c1,c2,c3 in cells:
            if any(x is None for x in [c1.value,c2.value,c3.value]): continue
            if sys.version_info[0] > 2:
                port    = str(c1.value).lower() 
                device  = str(c2.value).lower()
                intf    = str(c3.value).lower()
            else:
                port    = unicode(c1.value).lower() 
                device  = unicode(c2.value).lower()
                intf    = unicode(c3.value).lower()
            if device not in self._intf_map: self._intf_map[device] = {}

            # interface map
            self._intf_map[device][intf] = {}
            self._intf_map[device][intf]['switch-name'] = switch_name
            self._intf_map[device][intf]['switch-port'] = port
            self._intf_map[device][intf]['device']      = device

            # port map
            self._port_map[switch_name][port] = {}
            self._port_map[switch_name][port]['device']     = device
            self._port_map[switch_name][port]['interface']  = intf

    BuiltIn().log("        Read %d sheets of data" % len(wb.worksheets))

    # create session to all optical switch
    for entry in Common.GLOBAL['device']:
        dev_type  = Common.GLOBAL['device'][entry]['type']  

        if dev_type != 'calient': continue  # only deal with calient type
        ip = Common.GLOBAL['device'][entry]['ip']  

        session = requests.Session()
        credentials = Common.GLOBAL['auth']['plain-text']['calient']
        session.auth = (credentials['user'],credentials['pass'])
   
        self._clients[entry] = {} 
        self._clients[entry]['ip']          = ip
        self._clients[entry]['session']     = session
        self._clients[entry]["cookies"]     = ""


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
    sw1 = self._intf_map[dev1.lower()][port1.lower()]['switch-name']
    sw2 = self._intf_map[dev1.lower()][port1.lower()]['switch-name']

    if sw1 != sw2:
        return ()
    else:
        s1 = self._intf_map[dev1.lower()][port1.lower()]['switch-port'] 
        s2 = self._intf_map[dev2.lower()][port2.lower()]['switch-port'] 

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
    sport   = self._intf_map[dev.lower()][intf.lower()]['switch-port']
    switch  = self._intf_map[dev.lower()][intf.lower()]['switch-name']
    cli     = self._clients[switch]
    ip      = cli['ip']
    session = cli['session']

    rest_result = session.get("http://"+ip+"/rest/ports/?id=detail&port="+sport)
    if rest_result.status_code == requests.codes.ok:
        BuiltIn().log("result = %s" % rest_result.json()[0])
        return rest_result.json()[0]
    else:
        raise Exception("ERROR: Error happened when collecting port information")


def _delete_conn_info(self, switch, port1, port2, dir):
    """ Deletes existed connection between ``port1`` and ``port2`` an the switch
    """
    cli     = self._clients[switch]
    ip      = cli["ip"] 
    session = cli["session"]

    if dir == "bi":
        tmp1 = _get_circuit_from_port(self,switch,port1,['incircuit','outcircuit'])
        tmp2 = _get_circuit_from_port(self,switch,port2,['incircuit','outcircuit'])
        circuits = list(set(tmp1 + tmp2))
    else:
        tmp1 = _get_circuit_from_port(self,switch,port1,['incircuit'])
        tmp2 = _get_circuit_from_port(self,switch,port2,['outcircuit'])
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
    Without ``force`` mode, an existed connection will make the keyword fails

    Examples:
    | OpticalSwitch.`Add` | mx2008-31-33 | xe-3/0/0 | mx2008-31-33 | xe-3/0/1 | bi | ${TRUE} |

    *Note*: when ``force`` is ``False`` but the current ports is owned by
    the same connection endpoints, keyword will succeed.

    For a bidirection connection, 2 single uni-direction connection
    will be made instead of 1 bi-direction connection. This will make the link could
    be simulated tx/rx failure later.
    """

    BuiltIn().log("Adds %s connection %s:%s %s:%s" % (direction,dev1,intf1,dev2,intf2))

    switch  = ''
    conn_id = ''
    port1   = ''
    port2   = ''
    result  = False

    conn_info = _make_conn_info(self,dev1,intf1,dev2,intf2,direction)
    
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
        _delete_conn_info(self,switch, port1, port2, direction)
    else:
        tmp1 = _get_circuit_from_port(self,switch,port1,['incircuit','outcircuit'])
        tmp2 = _get_circuit_from_port(self,switch,port2,['incircuit','outcircuit'])
        # circuits = list(set(tmp1 + tmp2))
        used_port = []
        for item in (tmp1 + tmp2):
            for i in re.split(r'<|>',item):
                if not i in used_port: used_port.append(i)

        if used_port and (sorted([port1,port2]) != sorted(used_port)):
            raise Exception("Ports are being used: %s:%s by %s, %s:%s by %s" % (dev1,intf1,str(tmp1),dev2,intf2,str(tmp2))) 
        else:
            _delete_conn_info(self,switch, port1, port2, direction)
            BuiltIn().log("   deleted old circuits because same owner")

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
  

def delete(self,dev1,intf1,dev2,intf2,direction='bi',force=False):
    """ Deletes the connection between ``dev1:intf1 - dev2:intf2``

    Examples:
    | OpticalSwitch.`Delete` | mx2008-31-33 | xe-3/0/1 | mx2008-31-33 | xe-3/0/1 |  uni |

    """
    switch  = ''
    conn_id = ''
    port1   = ''
    port2   = ''

    conn_info = _make_conn_info(self,dev1,intf1,dev2,intf2)
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
        tmp1 = _get_circuit_from_port(self,switch,port1,['incircuit','outcircuit'])
        tmp2 = _get_circuit_from_port(self,switch,port2,['incircuit','outcircuit'])
        circuits = list(set(tmp1 + tmp2))
    else:
        tmp1 = _get_circuit_from_port(self,switch,port1,['incircuit'])
        tmp2 = _get_circuit_from_port(self,switch,port2,['outcircuit'])

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



