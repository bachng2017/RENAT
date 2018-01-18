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

# $Date: 2018-01-17 20:51:29 +0900 (Wed, 17 Jan 2018) $
# $Rev: 0.1.6 $
# $Author: bachng $

""" provides functions for IxNetwork

RENAT will connect to the App server and control the test ports. Test files and
result will be insde the RENAT server.

In order to run RENAT test case with `IxLoad`, the `TCLServer` must be activated
with `Administrator` privileges on the Ixia App server.

*Notes:* Ignore the _self_ parameters when using those keywords.
"""

import sys
import os
import re
import csv
import yaml
import time
import Common
import IxNetwork
from datetime import datetime
from robot.libraries.BuiltIn import BuiltIn
import robot.libraries.DateTime as DateTime

def wait_for_port(self,timeout_str='5m'):
    """ Waits until ports become enabled
    """

    BuiltIn().log("Waiting for all ports become enable ...")

    timeout = DateTime.convert_time(timeout_str)
    cli = self._clients[self._cur_name]
    ix  = cli['connection']
    count = 0
    port_ok = False

    while not port_ok and count < timeout:
        try :
            BuiltIn().log("Checking...")
            vport_list  = ix.getList(ix.getRoot(),'vport')
            port_ok     = len(vport_list) > 0

            for port in vport_list:
                state   = ix.getAttribute(port,'-isConnected')
                port_ok = port_ok and (state == 'true')

        except IxNetwork.IxNetError as err:
            port_ok = False
            BuiltIn().log("err type %s" % type(err))
            BuiltIn().log(err)
        time.sleep(5)
        count = count + 5 

    BuiltIn().log("Finished checking ports, state is %s (%d seconds elapsed)" % (port_ok,count))        
    return port_ok


def load_traffic(self,wait_time='2m',wait_time2='1m',apply=True,protocol=True):
    """ loads traffic configuration, applies and start protocol if necessary.

    The config file name was defined in the ``local.yaml` which is a Ixia
    Network configuration file and located in the `config` folder of the test.

    Parameter:
    - ``apply``: applies traffic when ``True`` otherwise 
    - ``protocol``: starts all protocols when ``True`` otherwise 

    See [./Common.html|Common] for more details about the yaml configuration files.
    """

    wait    = DateTime.convert_time(wait_time)
    wait2   = DateTime.convert_time(wait_time2)

    cli     = self._clients[self._cur_name]
    ix      = cli['connection']
    config_file = Common.LOCAL['tester'][self._cur_name]['config']
    
    # reset config
    ix.execute('newConfig')

    # load config
    ix.execute('loadConfig',ix.readFrom(os.getcwd() + '/config/' + config_file))
    
    BuiltIn().log("Loaded config:" + config_file)

    real_port_data = []
    if 'real_port' in Common.LOCAL['tester'][self._cur_name]:
        real_port_data = Common.LOCAL['tester'][self._cur_name]['real_port']

        if real_port_data and len(real_port_data) != 0: # no need to remap orts
            # remap ports 
            vports = ix.getList(ix.getRoot(),'vport')
            real_ports = []
            for item in real_port_data:
                chassis = item['chassis']
                card    = item['card']
                port    = item['port']
                real_ports.append((chassis,card,port)) 

            # assign ports without force to reclaim them
            result_id = ix.setAsync().execute('assignPorts',real_ports,[],vports,False) 
        
            interval = 5
            is_done = "false"
            count = 0
            while is_done == "false" and count < wait2:  
                count = count + 5
                time.sleep(5)
                is_done = ix.isDone(result_id)
                BuiltIn().log("is_done = %s, wait for more %d seconds ..." % (is_done,interval))

            if is_done != "true" :
                raise Exception("Error while remapping ports. The chassis IP might be wrong")

            result = ix.commit()
            if result != '::ixNet::OK' :
                raise Exception("Error while remapping ports: " + result)    
            BuiltIn().log("Remapped %s ports in % seconds" % (len(vports),count))

    self.wait_for_port(wait_time2)

    # start protocol
    if protocol :
        result = ix.execute('startAllProtocols')
        if result != '::ixNet::OK' :
            raise Exception("Error while starting protocols: " + result)    
        time.sleep(wait) # wait enough for protocol to start
        BuiltIn().log("Started all protocols")

    # apply traffic
    if apply :
        result = ix.execute('apply',ix.getRoot()+'traffic')
        if result != '::ixNet::OK' :
            raise Exception("Error while applying traffic: " + result)    
        BuiltIn().log("Applied traffic")


def apply_traffic(self):
    """ Applies the current traffic configuration

    *Note:* This is a blocking command
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']
    
    # apply traffic
    ix.execute('apply',ix.getRoot()+'traffic')
    
    BuiltIn().log("Applied traffic")



def change_frame_rate_dynamic(self,value,pattern='.*'):
    """ Changes the traffic flow rate on-fly

    No need to stop the running traffic to change the rate

    Parameter:
        - ``value``: value to set. Depend on the current configuration, this
          could be ``percent line rate`` or ``bit per second`` etc.

        - ``pattern`: a regular expression to identify traffic item
          name, default is everything ``.*``
    """

    cli = self._clients[self._cur_name]
    ix  = cli['connection']
   
    traffic_group_list = ix.getList(ix.getRoot() + 'traffic', 'dynamicRate')
    target_list = []
    for item in traffic_group_list:
        name = ix.getAttribute(item,'-name')
        if re.match(pattern,name): target_list.append(item)
    # target_list = [ item for item in traffic_group_list if re.match(pattern,item) ]

    for  item in target_list: ix.setAttribute(item,'-rate',value)

    result = ix.commit()
    if result != '::ixNet::OK': return False 

    BuiltIn().log("Changed traffic rate to %s" % (value))
        
    return True 



def change_frame_rate(self,value,pattern='.*'):
    """ Changes the frame rate 

    Parameter:
        - ``value``: value to set. Depends on the current configuration, this
          could be ``percent line rate`` or ``bit per second`` etc.
        - ``traffic_pattern`: a regular expression to identify traffic item
          name, default is everything ``.*``
    """

    cli = self._clients[self._cur_name]
    ix  = cli['connection']
   
    traffic_item_list = ix.getList(ix.getRoot() + 'traffic', 'trafficItem')
    target_list = []
    for item in traffic_item_list:
        name = ix.getAttribute(item,'-name')
        if re.match(pattern,name): target_list.append(item)
    # target_list = [ item for item in traffic_item_list if re.match(pattern,item) ]

    for  item in target_list:
        stream      = ix.getList(item, 'highLevelStream')[0]
        frame_rate  = ix.getList(stream, 'frameRate')[0] 
        ix.setAttribute(frame_rate,'-rate',value)

    result1 = ix.commit()
    result2 = ix.execute('apply', ix.getRoot() + 'traffic')
    if result1 != '::ixNet::OK' or result2 != '::ixNet::OK' :
        raise Exception("Failed to change frame rate: (%s)(%s)" % (result1,result2))
        return False 

    BuiltIn().log("Changed frame rate of %d items" % (len(target_list)))
    return True


def change_frame_size(self,type,value,pattern='.*'):
    """ Changes the frame size

    Parameter:
        - ``type``: could be ``fixed size``, ``increment_from``,``increment_step`` or
        ``increment_to`` 
        - ``value``: value to set
        - ``traffic_pattern`: a regular expression to identify traffic item
          name, default is everything ``.*``
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']
   
    traffic_item_list = ix.getList(ix.getRoot() + 'traffic', 'trafficItem')
    target_list = []
    for item in traffic_item_list:
        name = ix.getAttribute(item,'-name')
        if re.match(pattern,name): target_list.append(item)
    # target_list = [ item for item in traffic_item_list if re.match(pattern,item) ]

    for  item in target_list:
        stream      = ix.getList(item, 'highLevelStream')[0]
        frame_size  = ix.getList(stream, 'frameSize')[0] 
        if type == 'increment_from' :
            ix.setAttribute(frame_size,'-incrementFrom',value)
        elif type == 'increment_step' :
            ix.setAttribute(frame_size,'-incrementStep',value)
        elif type == 'increment_to' :
            ix.setAttribute(frame_size,'-incrementTo',value)
        else:
            ix.setAttribute(frame_size,'-fixedSize',value)
            

    result1 = ix.commit()
    result2 = ix.execute('apply', ix.getRoot() + 'traffic')
    if result1 != '::ixNet::OK' or result2 != '::ixNet::OK' :
        raise Exception("Failed to change frame sizce: (%s)(%s)" % (result1,result2))
        return False 

    BuiltIn().log("Changed frame size of %d items" % (len(target_list)))
    return True




def set_traffic_item(self,*items,**kwargs):
    """ Enables/Disables some traffic items ``items``
        
        Parameters:
        - ``items``: a list of Ixia traffic item name
        - ``enabled``: False or True ,the mode to set traffic item to, default is
          ``True`` (``enabled``)

        *Note*:  traffic item could be specified by ::<num> format. In this
        case the ``num`` is the order of traffic item count from zero.

        Returns ``True`` if all items are set coordinately or otherwise

        Examples:
        | Set Traffic Item | Traffic Item 1 | Traffic Item 2 |
        | Set Traffic Item | @{item_list}   | 
        | Set Traffic Item | Traffic Item 1 | enabled = ${FALSE} |

    """

    cli = self._clients[self._cur_name]
    ix  = cli['connection']
    if kwargs: 
        enabled = kwargs['enabled']
    else:
        enabled = True

    # create traffic data
    traffic_data = {}
    traffic_items = ix.getList(ix.getRoot()+'traffic','trafficItem')
    for item in traffic_items:  
        name = ix.getAttribute(item,'-name')
        traffic_data[name] = item
    
    for item in items:
        # acess traffic item by index if the item has format ::<num>
        indexes = re.findall('^::(%d)$',item)
        if len(indexes) == 1 :
            if indexes[0] < len(traffic_items):
               _item = traffic_items[indexes[0]]
            else:
                raise Exception("Error while setting traffic item")
        else:
            _item = item

        if traffic_data[_item]:
            ix.setAttribute(traffic_data[item],'-enabled',enabled)
        else:
            raise Exception("Error while setting traffic item") 

    result = ix.commit()
    if result != '::ixNet::OK': 
        raise Exception("Error while setting traffic item")

    BuiltIn().log("Set %d traffic items to `%s` state" % (len(items),enabled))

    return True 
    
   
def set_all_traffic_item(self,enabled=True):
    """ Enables/Disables all traffic items at once
    """

    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    traffic_items = ix.getList(ix.getRoot()+'traffic','trafficItem')
    for item in traffic_items:
        result = ix.setAttribute(item,'-enabled',enabled)
        if result != '::ixNet::OK': return False
    ix.commit()
 
    return True 


def start_traffic(self,wait_time='30s'):
    """ Starts the current traffic settiing and wait for ``wait_time``.

    *Note:* This is a asynchronus action. After called, traffic will take a while
    before start to come out, the the keyword will finish immediatly.
    """
    wait = DateTime.convert_time(wait_time)
    
    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    ix.execute('start',ix.getRoot()+'traffic')
    time.sleep(wait)


def load_and_start_traffic(self,wait_time1='10s',wait_time2='10s'):
    """ Combines `Load Traffic` and `Start Traffic` to one keyword.
    """ 
    self.load_traffic(wait_time1)
    self.start_traffic(wait_time2)


def stop_traffic(self,stop_protocol=False,wait_time='10s'):
    """ Stops the current traffic and wait for ``wait_time``
    
    Parameters:
    - stop_protocol: if ``True`` also stops all running protocols
    - wait_time: time to wait after apply the command
    """

    wait = DateTime.convert_time(wait_time)
    
    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    ix.execute('stop',ix.getRoot()+'traffic')
    BuiltIn().log("stopped the traffic")

    if stop_protocol :
        ix.execute('stopAllProtocols')
        BuiltIn().log("stopped all protocols")
    time.sleep(wait)


def close(self):
    """ Disconnects the current tester client
    """

    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    result = ix.disconnect()
    if result != "::ixNet::OK": raise Execption("Error while closing the connection")
    
    BuiltIn().log("Closed connection to `%s`" % self._cur_name)


def _fix_data(data):
    result = [[]]
    rows = re.findall(r'{{(.+?)}}',data)
    for row in rows:
        result[0].append(map(lambda x:re.sub(r'{|}','',x), re.findall(r'{.*?}|[^ ]+',row)))
    if not result[0]:
        result = map(lambda x:re.sub(r'{|}','',x), re.findall(r'{.*?}|[^ ]+',data))

    return result



def collect_data(self,view,prefix="stat_"):
    """ Collects traffic data of a ``view`` and export to a CSV file in
    ``result`` folder 

    Currently, supported views are: 

    ``Port_Statistics``, 
    ``Global_Protocol_Statistics``, ``BGP_Aggregated_Statistics``,
    ``BGP_Aggregated_State_Counts``, ``OSPF_Aggregated_Statistics``, 
    ``OSPF_Aggregated_State_Counts``, ``OSPFv3_Aggregated_Statistics``,
    ``OSPFv3_Aggregated_State_Counts``, ``L2-L3_Test_Summary_Statistics``,
    ``Flow_Statistics``, ``Flow_Detective``, ``Data_Plane_Port_Statistics``,
    ``User_Defined_Statistics``, ``Traffic_Item_Statistics``

    Result were store as CSV files in ``result`` folder.
    If there is no valid data, view will be silently ignored

    The prefix ``prefix`` is appended to the view name for the CSV file.
    """

    cli = self._clients[self._cur_name]
    ix  = cli['connection']
    BuiltIn().log("Collecting data for view `%s`" % view)
    result_path = os.getcwd() + '/' + Common.get_result_folder()
    result_id = ix.setAsync().getAttribute(view+'/page','-isReady')
    time.sleep(5) # wait for 5 second
    is_done = ix.isDone(result_id) 
    if is_done == "true": 
        # set page size to 2048(max)
        ix.setAttribute(view+'/page','-pageSize',500)
        ix.commit()

        # still this only support 1 page result
        # use below the get the total pages and moving b/t pages
        # ix.getAttribute(view+'/page','-totalRows')
        # ix.setAttribute(view+'/page','-currentPage', 2)
        # ix.commit()


        cap = ix.getAttribute(view+'/page', '-columnCaptions')
        if type(cap) is not list: cap = _fix_data(cap)
        # row = ix.getAttribute(view+'/page', '-rowValues')
        row = ix.getAttribute(view+'/page', '-pageValues')
        if row == '::ixNet::OK':
            row = ix.getAttribute(view+'/page', '-rowValues')
            
        if type(row) is not list: row = _fix_data(row)
        file_name = result_path + "/" + prefix + view.split(':')[-1].strip('"').replace(" ","_") + '.csv'
        f = open(file_name,'w+')
        w  = csv.writer(f, lineterminator='\n')
        w.writerow(cap)
        for i in range(len(row)):
            for j in range(len(row[i])):
                w.writerow(row[i][j])
        f.close()
    BuiltIn().log("Collected data for view `%s`" % view) 

def collect_all_data(self,prefix="stat_"):
    """ Collects all Ixia traffic data after traffic is stopped. 

    Results are CSV files that are stored in ``result`` folder. The prefix ``prefix`` is appended
    to the original view name
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    views = ix.getList(ix.getRoot()+'statistics','view')
    ### work-around for IxNet older than 7.4 which return a string not list for
    ### this
    if type(views) is not list: 
        BulitIn().log("    Fix data for  some old version of  Ixia NW (<7.4)")
        # views = filter(None,re.split("} {|{|}",views))
        views = _fix_data(views)

    for view in views:
        self.collect_data(view,prefix)    

    BuiltIn().log("Collected all available data")
   

def loss_from_file(self,file_name='Flow_Statistics.csv',tx_frame_i=3,frame_delta_i=5,time1_i=23,time2_i=24):
    """ Returns ``packet loss`` by miliseconds and delta frame.

    The calculation should be performed when traffic is stopped.
    The calculation supposed traffic is configured by frame per second
    """

    result_path = os.getcwd() + '/' + Common.get_result_folder()
    file_path = result_path + '/'  + file_name
    with open(file_path,'r') as file: lines = file.readlines()
    BuiltIn().log("    Read data from %s" % (file_path))
  
    data = lines[1].split(',') # read 2nd line
    frame_delta = int(data[frame_delta_i])
    tx_frame    = int(data[tx_frame_i])
    time_str1   = data[time1_i].strip()
    time_str2   = data[time2_i].strip()
    time1       = datetime.strptime(time_str1,"%H:%M:%S.%f")
    time2       = datetime.strptime(time_str2,"%H:%M:%S.%f")

    msec_delta  = (time2-time1).total_seconds()*1000
    BuiltIn().log("    Delta sec   = %d" % msec_delta) 
    BuiltIn().log("    Delta frame = %d" % frame_delta)
    msec_loss   = int(frame_delta * msec_delta / tx_frame)

    BuiltIn().log("Loss was %d frames, %d miliseconds" % (frame_delta,msec_loss))
    return msec_loss,frame_delta


def set_bgp_neighbor(self,*indexes,**kwargs):
    """ Enables/Disables BGP entry by neighbor index

    ``kwargs`` contains following parameters:
    - indexes: is a list of index of BGP neighbor (index is started from zero)
    - vport_index: is the target vport index
    - enabled: TRUE or FALSE 

    Examples:
    | Tester.`Set BGP Item` | 0 | 1 | vport_index=0 | enabled=${FALSE}
    | Tester.`Set BGP Item` | 0 | 1 | vport_index=1 | enabled=${TRUE}
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    if 'vport_index' in kwargs:
        vport_index = int(kwargs['vport_index'])
    else:
        vport_index = 0
    if 'enabled' in kwargs:
        enabled = kwargs['enabled']
    else:
        enabled = True

    vports      = ix.getList(ix.getRoot(),'vport')
    protocols   = ix.getList(ix.getRoot()+vports[vport_index],'protocols')
    bgps        = ix.getList(ix.getRoot()+protocols[0],'bgp')
    neighbors   = ix.getList(ix.getRoot()+bgps[0],'neighborRange') 
    for index in indexes:
        ix.setAttribute(ix.getRoot()+neighbors[int(index)],'-enabled',enabled)

    ix.commit()
    BuiltIn().log("Set %d BGP entries to value `%s`" % (len(indexes), enabled))


def set_bgp_items(self,port_index,neighbor_index,route_range_index,is_enable):
    """ Enables/Disables BGP entry by a set of port,neighbor,route_range index

    Parameters:
    - ``port_index``: index of the port 
    - ``neighbor_index``: index of the neighbor or `*` 
    - ``route_range_index``: index of the route range or `*'
    - ``is_enable``: ${TRUE} or ${FALSE}

    Note

    Examples:
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    vports      = ix.getList(ix.getRoot(),'vport')
    try:
        protocols       = ix.getList(ix.getRoot()+vports[int(port_index)],'protocols')
        bgps            = ix.getList(ix.getRoot()+protocols[0],'bgp')
        neighbor_list   = ix.getList(ix.getRoot()+bgps[0],'neighborRange') 
        if neighbor_index == '*':
            for neighbor in neighbor_list:
                ix.setAttribute(ix.getRoot()+neighbor,'-enabled',is_enable)
        else:
            route_range_list = ix.getList(ix.getRoot()+neighbor_list[int(neighbor_index)],'routeRange')
            if route_range_index == '*':
                for route in route_range_list:
                    ix.setAttribute(ix.getRoot()+route,'-enabled',is_enable)
            else:
                ix.setAttribute(ix.getRoot()+route_range_list[int(route_range_index)],'-enabled',is_enable)
    except IndexError as err:
        raise Exception("Index error while trying to access BGP items")  

    ix.commit()
    BuiltIn().log("Set BGP items to value `%s`" % (is_enable))


