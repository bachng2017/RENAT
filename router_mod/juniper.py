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

# $Rev: 828 $
# $Ver: 1.7.1 $
# $Date: 2018-03-20 09:41:00 +0900 (火, 20  3月 2018) $
# $Author: $

""" Provides keywords for Juniper platform

*Notes:* Ignore the _self_ parameters when using those keywords.
"""

import os,re
import codecs
import json
import jinja2
import time
import netsnmp
import shutil
import Common
from datetime import datetime
from datetime import timedelta
import robot.libraries.DateTime as DateTime
from robot.libraries.BuiltIn import BuiltIn
import openpyxl
from openpyxl.styles import PatternFill
from openpyxl.styles import colors
from openpyxl.styles import Font, Color
from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.styles import Alignment


def get_version(self):
    """ Returns router version information
    """ 

    result = self._vchannel.cmd('show version | no-more')
    return result

def get_current_datetime(self,time_format='%H:%M:%S',delta_time='0s',dir='+',**kwargs):    
    """ Returns the current date time with vendor format
    ``delta_time`` will be added or subtracted to current time, default is ``0s``

    ``time_format`` decides the time part of the output.
    Example result are :
    | May 24 04:14:25 
    | May  4 04:14:25
    *Note:* The date part is padded by space, and the result is allways 15 characters
    """
 
    delta = DateTime.convert_time(delta_time)
    if dir == '-':
        current_time = datetime.now() - timedelta(seconds=delta)
    else:
        current_time = datetime.now() + timedelta(seconds=delta)
    padded_day = datetime.strftime(current_time,"%d").rjust(2)
    format = "%%b %s %s" % (padded_day,time_format)
    result  = datetime.strftime(current_time,format)
    
    BuiltIn().log("Got current datetime and convert to Juniper format")
    return result


def number_of_ospf_neighbor(self,state="Full"):
    """ Returns number of OPSF neighbors with status ``state``
    """
    output  = self._vchannel.cmd("show ospf neighbor").lower()
    count   = output.count(state.lower())

    BuiltIn().log("Number of OSPF neighbors in `%s` state is %d" % (state,count))
    return count


def number_of_ospf3_neighbor(self,state="Full"):
    """ Returns number of OPSFv3 neighbors with status ``state``
    """
    output  = self._vchannel.cmd("show ospf3 neighbor")
    count   = output.count(state)

    BuiltIn().log("Number of OSPF neighbors in `%s` state is %d" % (state,count))
    return count


def number_of_bgp_neighbor(self,state="Established"):
    """ Returns number of BGP neighbor in ``state`` state
    """
    output  = self._vchannel.cmd("show bgp neighbor").lower()
    count   = output.count(state.lower())

    BuiltIn().log("Number of BGP neighbors in `%s` state is %d" % (state,count))
    return count


def enable_interface(self,intf):
    """ Enables an interface ``intf``
    """
 
    self._vchannel.cmd("configure")
    self._vchannel.cmd("delete interface " + intf + " disable")
    self._vchannel.cmd("commit")
    self._vchannel.cmd("exit")

    BuiltIn().log("Enabled interface `%s`" % (intf))


def disable_interface(self,intf):
    """ Disables an interface ``intf``
    """
    
    self._vchannel.cmd("configure")
    self._vchannel.cmd("set interface " + intf + " disable")
    self._vchannel.cmd("commit")
    self._vchannel.cmd("exit")

    BuiltIn().log("Disabled interface `%s`" % (intf))


def flap_interface(self,intf,time_str='10s'):
    """ Simulates an interface flap for interface ``intf``

    Disables the interface and wait for a while before turning it up again
    """

    self._vchannel.cmd("configure")
    self._vchannel.cmd("set interface " + intf + " disable")
    self._vchannel.cmd("commit")

    time.sleep(DateTime.convert_time(time_str))

    self._vchannel.cmd("delete interface " + intf + " disable")
    self._vchannel.cmd("commit")
    self._vchannel.cmd("exit")

    BuiltIn().log("Flapped interface `%s`" % (intf))
    

def get_cli_mode(self):
    """ Returns current mode of the CLI.

    Return value is ``config`` for configuration mode or ``command`` for command
    mode
    """
    result = ""
    output = self._vchannel.cmd('')
    if "#" in output: result = "config"
    if ">" in output: result = "command"

    BuiltIn().log("CLI mode is `%s`" % (result))
    return result



def load_config(self,mode='set',config_file='',confirm='0s',vars='',err_match='( syntax | error )'):
    """ Loads configuration to a router. 
    Usable ``mode`` is ``set``, ``override``, ``merge`` and ``replace``

    ``set`` mode uses configuration that contains ``set`` command.
    Mode ``override``, ``merge`` and ``replace`` use ordinary JunOS configuration file with appropriate mode.
    ``config_file`` is a configuration file inside the ``config`` folder of the
    current test case.
    
    Config file could includes jinja2 template. The template will be evalued
    with `LOCAL`, `GLOBAL` and varibles defined by `vars`. The `vars` has the
    format: var1=value1,var2=value2 ...
    
    If the loading has no error that match the ``error_match``, the
    configuration will be commited.

    The keywordl waits for ``confirm`` seconds before rollback the commited configuration. A
    zero value indicates an immediatly commit
    """

    # copy file, assuming current mode is command mode
    cli_mode = self.get_cli_mode()
    if cli_mode == "config": self._vchannel.cmd('exit')

    server      = Common.GLOBAL['default']['robot-server']
    password    = Common.GLOBAL['default']['robot-password']
    # the original config is in ./config folder
 
    folder              = os.getcwd() + '/config/'
    file_path           = os.getcwd() + '/config/' + config_file
    # file_path_replace = file_path + "_replace"
    file_path_replace   = os.getcwd() + '/tmp/' + config_file + '_tmp'

    # jinja2 process
    loader=jinja2.Environment(loader=jinja2.FileSystemLoader(folder)).get_template(config_file)
    render_var = {'LOCAL':Common.LOCAL,'GLOBAL':Common.GLOBAL}
    for pair in vars.split(','):
        info = pair.split("=")
        if len(info) == 2:
            render_var.update({info[0].strip():info[1].strip()})
    compiled_config = loader.render(render_var)

    with codecs.open(file_path_replace,'w','utf-8') as f: 
        f.write(compiled_config)
    cmd = "file copy robot@" + server + "://" + file_path_replace + ' /var/tmp/' + config_file

    output = self._vchannel.cmd(cmd,prompt="(yes/no|password:)")
    if "yes/no" in output:
        output = self._vchannel.cmd("yes")
    if "password:" in output:
        output = self._vchannel.cmd(password)

    confirm_time = int(DateTime.convert_time(confirm) / 60) # minute


    if not '100%' in output:
        raise Exception("ERROR: error while copying config file `%s`" % config_file)

    if mode in ['override','merge','replace']:
        self._vchannel.cmd('configure')
        output = self._vchannel.cmd("load " + mode + " /var/tmp/" + config_file)
    elif mode == 'set':
        self._vchannel.cmd('configure')
        output = self._vchannel.cmd("load set /var/tmp/" + config_file)
    else:
        raise Exception("Invalid ``mode``. ``mode`` should be ``set``,``override``,``merge``,``replace``")

    # check ouput
    if re.search(err_match, output):
        self._vchannel.cmd("rollback 0")
        raise Exception("ERROR: An error happened while loading the config. Output: `%s`" % output)
    
    if confirm_time == 0:
        output = self._vchannel.cmd("commit")
    else: 
        output = self._vchannel.cmd("commit confirmed %s" % (confirm_time))
   
    # check output 
    if re.search(err_match, output):
        self._vchannel.cmd("rollback 0")
        raise Exception("ERROR: An error happened while committing the change so I rolled it back")


    self._vchannel.cmd('exit')

    BuiltIn().log("commit result is: " + output)
    BuiltIn().log("Loaded config with ``%s`` mode and confirm time %s" % (mode,confirm_time))
    return True



def get_file(self,src_file,dst_file=''):
    """ Gets a file from router

    - ``src_file`` is a absolute path insides the router
    - ``dst_file`` is a file name under ``result`` folder
    """
 
    cli_mode = self.get_cli_mode()
    if cli_mode == "config": self._vchannel.cmd('exit')
    self._vchannel.stop_screen_mode()
   
    server      = Common.GLOBAL['default']['robot-server']
    password    = Common.GLOBAL['default']['robot-password']


    if dst_file == '':
        tmp_path    = os.getcwd() + '/tmp/juniper.conf.gz'
        dest_path   = os.getcwd() + '/' + Common.get_result_folder() + '/juniper.conf.gz'
    else:    
        tmp_path    = os.getcwd() + '/tmp/' + dst_file
        dest_path   = os.getcwd() + '/' + Common.get_result_folder() + '/' + dst_file

    cmd = "file copy %s robot@%s://%s" % (src_file,server,tmp_path)
    # output = self._vchannel.write(cmd, str_timeout)
    # output = self._vchannel.read() 
    output = self._vchannel.cmd(cmd,prompt="(yes/no|password:)")

    if "yes/no" in output:
        output = self._vchannel.cmd("yes")
    if "password:" in output:
        output = self._vchannel.cmd(password)
    if "error" in output:
        raise Exception("ERROR:" + output) 

    # change config mod
    # os.chmod(dest_path,int('0775',8)) 
    shutil.copy(tmp_path,dest_path)
    
    BuiltIn().log("Get the file `%s` from node `%s`" % (src_file,self._vchannel.current_name))



def get_config(self,dst_name=''):
    """ Gets the current configuration file of the router to current ``result``
    folder. Wait for ``str_timeout`` to finish the download, default
    ``str_timeout`` is 10 seconds. Increases this value if the config file is large.   

    Default ``dst_name`` is ``juniper.conf.gz``
    """

    return self.get_file('/config/juniper.conf.gz',dst_name)


def link_status(self,if_name):
    """ Returns link physical status as string (aka: "up down", "up up")
    """
   
    result = "" 
    output = self._vchannel.cmd("show interface %s terse | grep \"%s \"" % (if_name,if_name))
    tmp = re.split('\s+',output.split("\n")[0].strip())
    if len(tmp) == 3:
        result = tmp[1] + " " + tmp[2]
        BuiltIn().log("Got link status of `%s`: %s %s" % (if_name,tmp[1],tmp[2]))
    else:
        raise Exception("Error while getting link status of `%s`" % if_name)

    return result


def get_route_number(self,table='inet.0'):
    """ Returns number of active route in the ``table``

    ``table`` could be ``inet.0`` or ``inet.6``
    """
    
    result = ""
    output = self._vchannel.cmd("show route summary table %s" % table)
    for line in output.split("\n"):
        match = re.match(r"%s: .* \((.+) active," % table, line)
        if match:
            result = int(match.group(1))
    BuiltIn().log("Got %d routes from `%s`" % (result,table)) 
    
    return result 


def get_intf_addr(self,intf_name,family='inet'):
    """ Returns the tuple of address and netmask of an interface

    ``family`` should be ``inet`` or ``inet6``
    If the address is not set, ``('','')`` will be returned.
    """
    
    output  = self._vchannel.cmd("show interface %s terse | match %s" % (intf_name,family))
    line = output.split('\n')[0]    # first line
    try:
        address = tuple(line.split()[-1].split('/'))
    except IndexError:
        address = ('','')
    BuiltIn().log("Interface address is `%s`, netmask is `%s`" % (address[0],address[1]))
    return address

def get_chassis_serial(self):
    """ Returns the serial number of the chassis
    """

    output = self._vchannel.cmd("show chassis hardware | match Chassis")
    line = output.split('\n')[0]    # first line
    tmp = line.split()
    if len(tmp) > 2:
        result = tmp[1]
    else:
        result = ''
    BuiltIn().log("Got the serial number: %s" % (result))
    return result


def create_best_path_select_data(self,route_content,output_excel='best.xlsx'):
    """ Creates the matrix of best path selection 
    
    Provides the test described in  `smb://10.128.3.91/SharePoint01/31_VerificationRoom/31_13_検証環境セット/BGP-Best-Path-SelectionのAll-in-One設定_20161118改良/`
    The test uses predefined Ixia config and follows predefined steps
    """

    wb = openpyxl.Workbook()
    wb.guess_types = True
    tmp = output_excel.split('.')
    sheet_name = tmp[0]
    ws = wb.create_sheet(sheet_name,0)

    # adding column name
    ws.append( ['INTF','Prefix','ProtoPref','LocalPref','AS_PATH','Origin','MED','Protocol','I/E','IGP','Age','RouterID','CLLength','Peer','Win/Loose','Reason'])
   
    # sparsing route information 
    route_info_list=re.findall(r"(\S+/.{1,3}) (?:.*?entr.*?announced.*?)\r\n(( {8}[ *](\S+) *Pref.*?\r\n( {16}.*?\r\n)+)+)\r\n",route_content,re.DOTALL)

    line = 1 # excel start at number 1
    for route_info in route_info_list:
        route = route_info[0]
        proto_list = re.findall(r" {8}([ *])(\S+) *Preference: (\S+?)(?:/\S+){0,1}\r\n(( {16}.*?\r\n)+)",route_info[1],re.DOTALL)
        for proto_info in proto_list:
            if proto_info[0] == '*':
                win = 'win'
                if line > 1:
                    ws.append( ['','','','','','','','','','','','','','','',''])
                    line = line + 1
            else:
                win = 'loose'
            proto   = proto_info[1]
            pp      = proto_info[2]
    
            match_intf = re.search(r" via (\S+),", proto_info[3],re.MULTILINE)
            if match_intf:
                intf_index  = int(match_intf.group(1).split('.')[1])
                via_intf = chr(ord('A')+intf_index-1)
            else:
                via_intf = '-'
    
            match_localpref = re.search(r"Localpref: (\S+)", proto_info[3],re.MULTILINE)
            if match_localpref: local_pref = match_localpref.group(1)
            else:               local_pref = '-'
    
            match_as_path = re.search(r"AS path: (.*?)\r\n", proto_info[3],re.MULTILINE)
            if match_as_path:
                as_list = match_as_path.group(1).split()
                as_path = len(as_list) - 1 # the last is the origin
                if as_list[-1] == 'E':
                    origin = 'EGP'
                else:
                    origin = 'IGP'
            else:
                as_path = '-'
                origin = '-'
    
            match_med = re.search(r"Metric: (\S+) ", proto_info[3],re.MULTILINE)
            if match_med:
                med = match_med.group(1)
            else:
                med = '-'
    
            match_type = re.search(r"Local AS:  (\S+) Peer AS: (\S+)",proto_info[3],re.MULTILINE)
            if match_type:
                if match_type.group(1) == match_type.group(2):
                    type = 'IBGP'
                else:
                    type = 'EBGP'
            else:
                type = '-'
    
    
            match_igp = re.search(r"Metric2: (\S+)",proto_info[3],re.MULTILINE)
            if match_igp:
                igp = match_igp.group(1)
            else:
                igp = '-'
    
            match_router_id = re.search(r"Router ID: (\S+)",proto_info[3],re.MULTILINE)
            if match_router_id:
                router_id = match_router_id.group(1)
            else:
                router_id = '-'
    
            match_cll = re.search(r"Cluster list:  (.*)\r\n",proto_info[3],re.MULTILINE)
            if match_cll:
                cll = len(match_cll.group(1).split())
            else:
                cll = '0'
    
            match_peer = re.search(r"Source: (\S+)",proto_info[3],re.MULTILINE)
            if match_peer:
                peer = match_peer.group(1)
            else:
                peer = '-'
    
#            match_age = re.search(r"Age: (\S+)",proto_info[3],re.MULTILINE)
#            if match_age:
#                age = reduce(lambda x, y: x*60+y, [int(i) for i in match_age.group(1).split(':')])
#            else:
#                age = '-'
            match_age = re.search(r"Age: (.*?) (?:\r\n|    )", proto_info[3],re.MULTILINE)
            if match_age:
                m = re.match(r"(\d+w){0,1}(\d+d){0,1} {0,1}(\S+)",match_age.group(1))
                age = 0
                if m.group(1): age = age + int(m.group(1)[:-1])*7*24*60*60
                if m.group(2): age = age + int(m.group(2)[:-1])*24*60*60
                age = age + sum(int(x) * 60 ** i for i,x in enumerate(reversed(m.group(3).split(":"))))
            else:
                age = '-'
    
            match_reason = re.search(r"Inactive reason: (.+)\r\n",proto_info[3],re.MULTILINE)
            if match_reason:
                reason = match_reason.group(1)
            else:
                reason = '-'
    
    
            BuiltIn().log("    Added row: \
            (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)" %
            (via_intf,route,pp,local_pref,as_path,origin,med,proto,type,igp,age,router_id,cll,peer,win,reason))
    
            row = [via_intf,route,pp,local_pref,as_path,origin,med,proto,type,igp,age,router_id,cll,peer,win,reason]
            ws.append(row)
            line = line + 1
   
    # coloring style
    # HeaderFill  = PatternFill(start_color='ffff00',end_color='ffff00',fill_type='solid')
    RedFont     = Font(color=colors.RED)
    BlueFont    = Font(color=colors.BLUE)
    #for cell in ws[1]:
    #    cell.fill = HeaderFill
    #for cell in ws['O']:
    #    if cell.value=='win': cell.font = RedFont
    
    for cell in reversed(ws['P']):
        row = int(cell.row)
        if cell.value == 'Update source':
            ws['N%d' % row].font = BlueFont
            ws['N%d' % (row - 1)].font = RedFont
        if cell.value == 'Cluster list length':
            ws['M%d' % row].font = BlueFont
            ws['M%d' % (row - 1)].font = RedFont
        if cell.value == 'Router ID':
            ws['L%d' % row].font = BlueFont
            ws['L%d' % (row - 1)].font = RedFont
        if cell.value == 'Active preferred':
            ws['K%d' % row].font = BlueFont
            ws['K%d' % (row - 1)].font = RedFont
        if cell.value == 'IGP metric':
            ws['J%d' % row].font = BlueFont
            ws['J%d' % (row - 1)].font = RedFont
        if cell.value == 'Interior > Exterior > Exterior via Interior':
            ws['I%d' % row].font = BlueFont
            ws['I%d' % (row - 1)].font = RedFont
        if cell.value == 'Route Metric or MED comparison':
            ws['H%d' % row].font = BlueFont
            ws['H%d' % (row - 1)].font = RedFont
        if cell.value == 'Always Compare MED':
            ws['G%d' % row].font = BlueFont
            ws['G%d' % (row - 1)].font = RedFont
        if cell.value == 'Origin':
            ws['F%d' % row].font = BlueFont
            ws['F%d' % (row - 1)].font = RedFont
        if cell.value == 'AS path':
            ws['E%d' % row].font = BlueFont
            ws['E%d' % (row - 1)].font = RedFont
        if cell.value == 'Local Preference':
            ws['D%d' % row].font = BlueFont
            ws['D%d' % (row - 1)].font = RedFont
        if cell.value == 'Route Preference':
            ws['C%d' % row].font = BlueFont
            ws['C%d' % (row - 1)].font = RedFont
    
    # adjust column width
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 12
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['H'].width = 12
    ws.column_dimensions['L'].width = 12
    ws.column_dimensions['M'].width = 12
    ws.column_dimensions['O'].width = 12
    ws.column_dimensions['P'].width = 32
    
    tab = Table(displayName="Table1",ref="A1:P%d" % line)
    style = TableStyleInfo(name="TableStyleMedium9",showFirstColumn=False,showLastColumn=False,showRowStripes=False,showColumnStripes=False)
    tab.tableStyleInfo = style
    ws.add_table(tab)

    # top = Border(top=border.top)
    rows = ws["A1:P%d" % line]
    for row in rows:
        for cell in row:
            cell.alignment = Alignment(horizontal="right")
    
    ws.append([])
    ws.append(['※1 Protocol Preference の値はルータの import policy で変更'])
    ws.append(['※2 ここでは Always Compare MED 有りの試験のみ実施。'])
    ws.append(['※3 1.6.0.0/staticの場合、ルータにて PP 170 の static経路を設定。ただし、正常に試験できているか不明。'])
    ws.append(['※4 全経路配信後、IF-B から配信しているこの経路(1.9.0.0) だけ一回フラップさせるた。'])

    save_path = os.getcwd() + '/' + Common.get_result_folder() + '/' + output_excel
    wb.save(save_path) 
    BuiltIn().log("Created the best path select matrix")


