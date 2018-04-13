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

# $Rev: 898 $
# $Ver: 0.1.8 $
# $Date: 2018-04-10 15:33:53 +0900 (火, 10  4月 2018) $
# $Author: $

""" A library provides control for Telescent Network Topology Management (NTM)
robot patch.
"""
import requests
import openpyxl

import sys,os,re
import jinja2
import Common
from datetime import datetime
from robot.libraries.BuiltIn import BuiltIn


def _read_map(self):
    """
    """
    ### create the master port-map
    BuiltIn().log("        Use `%s` for cable x-connect" % Common.newest_ntm)

    _folder = os.path.dirname(__file__)
    _ntm_file = _folder + "/../tmp/g4ntm.xlsm"

    wb = openpyxl.load_workbook(_ntm_file,data_only=True)
    for sheet in wb.worksheets:
        switch_name = sheet.title

        if switch_name not in self._port_map: self._port_map[switch_name] = {}

        cells = sheet['B3': 'D1058']
        for c1,c2,c3 in cells:
            if any(x is None for x in [c1.value,c2.value,c3.value]): continue
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

            # BuiltIn().log_to_console("%s:%s:%s:%s" % (device,intf,switch_name,port))

    BuiltIn().log("        Read %d sheets of data" % len(wb.worksheets))

    # create session to all optical switch
    for entry in Common.GLOBAL['device']:
        dev_type  = Common.GLOBAL['device'][entry]['type']

        if dev_type != 'g4ntm': continue  # only deal with ntm type
        ip = Common.GLOBAL['device'][entry]['ip']
        conn_port = Common.GLOBAL['device'][entry]['port']

        session = requests.Session()
        credentials = Common.GLOBAL['auth']['plain-text']['ntm']
        session.auth = (credentials['user'],credentials['pass'])

        self._clients[entry] = {}
        self._clients[entry]['ip']          = ip
        self._clients[entry]['port']        = conn_port
        self._clients[entry]['session']     = session
        self._clients[entry]["cookies"]     = ""


def get_connection_info(self,dev,intf):
    """ Returns information about the connection by router/interface
    """
    sport   = self._intf_map[dev.lower()][intf.lower()]['switch-port']
    switch  = self._intf_map[dev.lower()][intf.lower()]['switch-name']
    cli     = self._clients[switch]
    ip      = cli['ip']
    conn_port = cli['port']
    session = cli['session']

    rest_result = session.get("http://%s:%s/rest/v1/port/%s" % (ip,conn_port,sport))
    if rest_result.status_code == requests.codes.ok:
        data = rest_result.json()
        if type(data) == list:
            BuiltIn().log("result = %s" % rest_result.json()[0])
            return rest_result.json()[0]
        else:
            BuiltIn().log("port is unavailable")
    else:
        msg = "ERROR: Error happened when collecting port"
        raise Exception(msg)


def _delete_conn_info(self, switch, port, dir):
    """ Deletes existed connection between ``port1`` and ``port2`` an the switch

    ``dir`` could be ``bi``,``in`` or ``out``
    """
    cli     = self._clients[switch]
    ip      = cli["ip"]
    conn_port  = cli["port"]
    session = cli["session"]

    if dir == 'bi':     direction = 'DUPLEX'
    if dir == 'in':     direction = 'INPUT'
    if dir == 'out':    direction = 'OUTPUT'

    rest_result = session.delete('http://%s:%s/rest/v1/connect/' % (ip,conn_port,port))
    if rest_result.status_code != requests.codes.ok:
        BuiltIn().log("Failed to delete the x-connection")
        return False
    else:
        BuiltIn().log("Deleted x-connection of port `%s` on switch %s" % (port,switch))

    return True



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

        if dir == 'bi': connect = 'DUPLEX'
        if dir == '>' : connect = 'OUTPUT'
        if dir == '<' : connect = 'INPUT'

        return (sw1, s1+connect+s2, s1 ,s2, connect)


def add(self,dev1,intf1,dev2,intf2,direction='bi',force=False):
    """
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
        raise Exception("ERROR: wrong connection info")

    cli     = self._clients[switch]
    ip      = cli['ip']
    conn_port = cli['port']
    session = cli['session']

    if direction.lower() == 'bi':
        duplex = 'true'
    else:
        dupplex = 'false'

    if force:
        rest_result = session.put('http://%s:%s/rest/v1/unlock/%s/?direction=%s' % (ip,conn_port,port1,direction))
        rest_result = session.put('http://%s:%s/rest/v1/unlock/%s/?direction=%s' % (ip,conn_port,port2,direction))
    rest_result = session.post('http://%s:%s/rest/v1/connect/%s/%s?duplex=true&allocate=true' % (ip,conn_port,port1,port2))
    if rest_result.status_code == requests.codes.ok:
        result = rest_result.json()
        BuiltIn().log('Added the connection with result:')
        BuiltIn().log(result)
    else:
        err = "ERROR: error while adding connection"
        raise Exception(err)

def delete(self,dev1,intf1,dev2,intf2,direction='bi',force=False):
    """ Deletes the connection between ``dev1:intf1 - dev2:intf2``
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
        raise Exception("ERROR: wrong connection info")

    cli     = self._clients[switch]
    ip      = cli['ip']
    conn_port = cli['port']
    session = cli['session']

    ## make uniq list
    if direction.lower() == "bi":
        direction = 'DUPLEX'
    elif direction.lower() == '>':
        direction = 'OUTPUT'
    else:
        direction = 'INPUT'

    if force: 
        rest_result = session.put('http://%s:%s/rest/v1/unlock/%s/?direction=%s' % (ip,conn_port,port1,direction))
        rest_result = session.put('http://%s:%s/rest/v1/unlock/%s/?direction=%s' % (ip,conn_port,port2,direction))
    rest_result = session.delete('http://%s:%s/rest/v1/connect/%s/?direction=%s' % (ip,conn_port,port1,direction))
    if rest_result.status_code == requests.codes.ok:
        result = rest_result.json()
        BuiltIn().log('Deleteed the connection with result:')
        BuiltIn().log(result)
    else:
        err = "ERROR: error while deleting connection. Detail is " + str(rest_result.json())
        raise Exception(err)
        
