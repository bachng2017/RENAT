# -*- coding: utf-8 -*-
#  Copyright 2017-2020 NTT Communications
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


""" provides functions for IxNetwork

To use IxNetwork module, a IxNetwork TCL server should be started properly.

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
import time,traceback
import pandas as pd
import Common
import IxNetwork
from datetime import datetime,timedelta
from robot.libraries.BuiltIn import BuiltIn
import robot.libraries.DateTime as DateTime
import xml.etree.ElementTree as ET

def update_chassis(self):
    """ updates chassis info by information in device.yaml
    """
    cli     = self._clients[self._cur_name]
    ix      = cli['connection']

    # prepare chassis
    device =  Common.LOCAL['tester'][self._cur_name]['device']
    device_info = Common.GLOBAL['device'][device]
    cur_chassis = map(lambda x: ix.getAttribute(x,'-hostname'),ix.getList(ix.getRoot()+'availableHardware','chassis'))

    if 'chassis' in device_info:
        BuiltIn().log("    found chassis setting")
        for item in device_info['chassis']:
            item = item.strip()
            if item in cur_chassis: continue
            ix.add(ix.getRoot()+'availableHardware', 'chassis', '-hostname',item)
            BuiltIn().log('    added chassis `%s`' % item)
        ix.commit()

        chassis = ix.getList(ix.getRoot()+'availableHardware', 'chassis')
        # wait until all chassis is ready
        interval = 5
        ready = False
        while not ready:
            BuiltIn().log('    wait %d seconds until all chassis are ready' % interval)
            time.sleep(interval)
            ready = True
            for item in chassis:
                ready = ready and (ix.getAttribute(item,'-state') == u"ready")

        # set chassis master
        master = ''
        for item in chassis:
            BuiltIn().log('    checking %s:%s' % (ix.getAttribute(item,'-hostname'),ix.getAttribute(item,'-isMaster')))
            if ix.getAttribute(item,'-isMaster') == u'false': continue
            master = ix.getAttribute(item,'-hostname')
            BuiltIn().log('    found master `%s`' % master)
        if master != '' :
            for item in chassis:
                if ix.getAttribute(item,'-isMaster') == 'true': continue
                BuiltIn().log('    set cluster master to `%s`' % master)
                ix.setAttribute(item,'-masterChassis',master)
        ix.commit()
        time.sleep(5)
    BuiltIn().log('Updated chassis information')

def reset_config(self):
    """ Clears current config and creates new blank config
    """
    cli     = self._clients[self._cur_name]
    ix      = cli['connection']

    ix.execute('newConfig')
    self.update_chassis()
    BuiltIn().log("Created a new blank config")


def wait_until_connected(self,timeout_str='5m'):
    """ Waits until ports become enabled and connected
    """

    BuiltIn().log("Waiting for all ports become enable ...")

    timeout = DateTime.convert_time(timeout_str)
    cli = self._clients[self._cur_name]
    ix  = cli['connection']
    count = 0
    port_ok = False
    vport_list  = ix.getList(ix.getRoot(),'vport')

    if len(vport_list) == 0:
        port_ok = True
        BuiltIn().log("WARN: no port is configured")
    else:
        while (not port_ok) and (count < timeout):
            try :
                port_ok = True
                BuiltIn().log("    checking %d port status ..." % len(vport_list))
                for port in vport_list:
                    state   = ix.getAttribute(port,'-isConnected')
                    port_ok = port_ok and (state == 'true')

            except IxNetwork.IxNetError as err:
                port_ok = False
                BuiltIn().log("err type %s" % type(err))
                BuiltIn().log(err)
                raise Exception("ERROR: errors found on ixnetwork ports")
            time.sleep(5)
            count = count + 5
        if (count >= timeout):
            raise Exception("ERROR: errors found on ixnetwork ports")

    BuiltIn().log("Finished checking ports, state is %s (%d seconds elapsed)" % (port_ok,count))
    return port_ok

def load_traffic(self,wait_time='2m',wait_time2='2m',apply=True,protocol=True,force=True,tx_mode=u'interleaved'):
    str = "***WARNING: `Load Traffic` is deprecated. Use `Load Config` instead ***"
    BuiltIn().log(str)
    BuiltIn().log_to_console(str)
    self.load_config(wait_time='2m',wait_time2='2m',apply=True,protocol=True,force=True)


def load_config(self,config_name='',wait_time='2m',wait_time2='2m',apply=True,protocol=True,force=True,wait_time3='30s'):
    """ loads traffic configuration, applies and start protocol if necessary.

    The config file name was defined in the ``local.yaml` which is a Ixia
    Network configuration file and located in the `config` folder of the test.

    The keyword remap the vports to real port when data is specified in the
    local configuration file. For some reasons, the txMode is cleared when
    remapping happens. Use ``tx_mode`` to set the TxMode of the remapped ports.

    Parameters:
    - ``apply``: applies traffic when ``True`` otherwise
    - ``protocol``: starts all protocols when ``True`` otherwise
    - ``force``: force to reclaim the ports when ``True`` otherwise
    - ``wait_time``: wait time after applying protocols
    - ``wait_time2``: maximum wait time befor all ports become available. In
    common case, this is calculated automatically so user does not need to
    change this value.
    - ``wait_time3``: default waiting time after config file is loaded (30s)

    More information about ports could be define in ``real_port`` section like
    this:
| # tester information
| tester:
|
|     tester:
|         device: ixnet03_8009
|         config: bgp.ixncfg
|         real-port:
|             -   chassis:    10.128.4.41
|                 card:       4
|                 port:       7
|                 media:      fiber
|                 tx_mode:    interleaved

    Configurable port parameters ares:
    - ``tx_mode``: `sequential` or `interleaved`(default)
    - ``media`` : `copper` or `fiber` ( *Note*: no default value)

    See [./Common.html|Common] for more details about the yaml configuration files.
    """

    wait    = DateTime.convert_time(wait_time)
    wait2   = DateTime.convert_time(wait_time2)
    wait3   = DateTime.convert_time(wait_time3)

    cli     = self._clients[self._cur_name]
    ix      = cli['connection']
    if config_name == '':
        config_name = Common.LOCAL['tester'][self._cur_name]['config']

    # load config
    config_path = Common.get_item_config_path() + '/' + config_name
    ix.execute('loadConfig',ix.readFrom(config_path))
    BuiltIn().log("Loaded config file `%s`" % config_path)

    self.update_chassis()

    real_port_data = []
    if 'real-port' in Common.LOCAL['tester'][self._cur_name]:
        real_port_data = Common.LOCAL['tester'][self._cur_name]['real-port']
        BuiltIn().log("    found port setting")
        if real_port_data and len(real_port_data) != 0: # no need to remap ports
            # remap ports
            vports = ix.getList(ix.getRoot(),'vport')
            real_ports = []
            for item in real_port_data:
                chassis = item['chassis'].strip()
                card    = int(item['card'])
                port    = int(item['port'])
                real_ports.append((chassis,card,port))

            BuiltIn().log("    assigning %d ports to %d vports" % (len(real_ports),len(vports)))

            # assign ports
            result_id = ix.setAsync().execute('assignPorts',real_ports,[],vports,force)
            interval = 5
            is_done = u"false"
            count = 0
            while is_done == u"false" and count < wait2:
                count = count + interval
                BuiltIn().log_to_console('.','STDOUT',True)
                time.sleep(interval)
                is_done = ix.isDone(result_id)
                BuiltIn().log("    assigning status was `%s`, wait for more %d seconds ..." % (is_done,interval))

            if is_done != u"true" :
                raise Exception("ERROR: Error while remapping ports. The chassis IP might be wrong")

            # extra setting for port
            for data,port in zip(real_port_data,vports):
                if 'media' in data:
                    media = data['media']
                    ix.setAttribute(port + '/l1Config/ethernet','-media',media)
                if 'tx_mode' in real_port_data:
                    tx_mode = data['tx_mode']
                else:
                    tx_mode = 'interleaved'
                ix.setAttribute(port,'-txMode',tx_mode)
            result = ix.commit()
            if result != u'::ixNet::OK' :
                raise Exception("ERROR: Error while remapping ports: " + result)
            BuiltIn().log("Loaded config and reassigned %d ports in %d seconds" % (len(vports),count))

    # check port status again
    self.wait_until_connected(wait_time2)

    # start protocol
    if protocol :
        BuiltIn().log("Starting all protocols...")
        result = ix.execute('startAllProtocols')
        if result != u'::ixNet::OK' :
            raise Exception("ERROR: Error while starting protocols: "+result)
        time.sleep(wait) # wait enough for protocol to start
        BuiltIn().log("Started all protocols")
    # apply traffic
    if apply :
        BuiltIn().log("Applying traffic ...")
        result = ix.execute('apply',ix.getRoot()+'traffic')
        if result != u'::ixNet::OK' :
            raise Exception("ERROR: Error while applying traffic: " + result)
        BuiltIn().log("Applied traffic")
    #
    time.sleep(wait3)


def start_protocol(self,wait_time='1m'):
    """ Starts all protocols and wait for ``wait_time``

    Default ``wait_time`` is 1 minute. Make sure ``wait_time`` is big engouh to
    start all protocols.
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    result = ix.execute('startAllProtocols')
    if result != '::ixNet::OK' :
        raise Exception("Error while starting protocols: " + result)

    wait    = DateTime.convert_time(wait_time)
    time.sleep(wait) # wait enough for protocol to start
    BuiltIn().log("Started all protocols")


def apply_traffic(self,refresh=True):
    """ Applies the current traffic configuration

    ``refresh``: Refreshed the learned information before apply the traffic or not
    *Note:* This is a blocking command
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    #
    ix.setAttribute(ix.getRoot()+'traffic','-refreshLearnedInfoBeforeApply',refresh)

    # apply traffic
    ix.execute('apply',ix.getRoot()+'traffic')

    BuiltIn().log("Applied traffic")


def _rate_to_val_type(rate_str):
    if type(rate_str) is not str:
        rate_str = str(rate_str)

    m = re.match(r'^\s*([\d\.,]+)\s*([KMG])?(pcnt|%|fps|bps|pps)?\s*$', rate_str)
    if not m:
        raise Exception("ERROR: invalid rate format '%s'" % rate_str)

    rate_value, rate_si, rate_type = m.groups()
    rate_value = float(rate_value)
    
    rate_type = {
        None: None,
        'pcnt': 'percentLineRate',
        '%': 'percentLineRate',
        'fps': 'framesPerSecond',
        'pps': 'framesPerSecond',
        'bps': 'bitsPerSecond',
    }[rate_type]

    if rate_type == 'percentLineRate' and rate_si:
        raise Exception("ERROR: invalid rate format '%s'" % rate_str)

    rate_value *= {
        None: 1,
        'K': 1000,
        'M': 10**6,
        'G': 10**9
    }[rate_si]

    return (rate_value, rate_type)


def change_frame_rate_dynamic(self,value,pattern='.*'):
    """ Changes the traffic flow rate on-fly

    No need to stop the running traffic to change the rate

    Parameter:
        - ``value``: value to set. Depend on the current configuration, this
          could be ``percent line rate`` or ``bit per second`` etc.

        - ``pattern``: a regular expression to identify traffic item
          name, default is everything ``.*``
    """

    rate_value, rate_type = _rate_to_val_type(value)
    BuiltIn().log('setting rate for "{}" to {} {}'.format(pattern, rate_value, rate_type))

    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    traffic_item_list = ix.getList(ix.getRoot() + 'traffic', 'trafficItem')
    target_idx_list = []
    for idx, item in enumerate(traffic_item_list):
        name = ix.getAttribute(item, '-name')
        if re.match(pattern, name):
            target_idx_list.append(idx)

    if not target_idx_list:
        raise Exception("ERROR: no traffic items matching pattern")

    traffic_group_list = ix.getList(ix.getRoot() + 'traffic', 'dynamicRate')
    target_group_list = [traffic_group_list[i] for i in target_idx_list]

    for item in target_group_list:
        BuiltIn().log('found traffic group: {}'.format(item))
        if rate_type:
            ix.setAttribute(item, '-rateType', rate_type)
        ix.setAttribute(item, '-rate', rate_value)

    result = ix.commit()
    if result != '::ixNet::OK':
        return False

    BuiltIn().log("Changed traffic rate to %s" % (value))

    return True


def get_root(self):
    cli = self._clients[self._cur_name]
    return cli['connection'].getRoot()

def get_list(self, container, item):
    cli = self._clients[self._cur_name]
    return cli['connection'].getList(container, item)


def change_frame_rate(self,value,pattern='.*',flow_pattern='.*'):
    """ Changes the frame rate

    Parameter:
        - ``value``: value to set. Depends on the current configuration, this
          could be ``percent line rate`` or ``bit per second`` etc.
        - ``pattern`: a regular expression to identify ``traffic item``
          name, default is everything ``.*``
        - ``flow_pattern``: a regular expression to identify ``flow group``
          inside the item
    """

    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    traffic_item_list = ix.getList(ix.getRoot() + 'traffic', 'trafficItem')
    item_list = []
    for item in traffic_item_list:
        name = ix.getAttribute(item,'-name')
        if re.match(pattern,name): item_list.append(item)

    count = 0
    for item in item_list:
        flow_list   = ix.getList(item, 'highLevelStream')
        for flow in flow_list:
            name = ix.getAttribute(flow,'-name')
            if re.match(flow_pattern,name):
                count += 1
                BuiltIn().log('    Modify flow `%s`' % name)
                frame_rate  = ix.getList(flow, 'frameRate')[0]
                ix.setAttribute(frame_rate,'-rate',value)

    result1 = ix.commit()
    result2 = ix.execute('apply', ix.getRoot() + 'traffic')
    if result1 != '::ixNet::OK' or result2 != '::ixNet::OK' :
        raise Exception("Failed to change frame rate: (%s)(%s)" % (result1,result2))
        return False

    BuiltIn().log("Changed frame rate of %d items" % count)
    return True


def change_frame_size(self,type,value,pattern='.*',flow_pattern='.*'):
    """ Changes the frame size

    Parameter:
        - ``type``: could be ``fixed size``, ``increment_from``,``increment_step`` or
        ``increment_to``
        - ``value``: value to set
        - ``pattern``: a regular expression to identify traffic item
          name, default is everything ``.*``
        - ``flow_pattern``: a regular expression to identify ``flow group``
          inside the item
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    traffic_item_list = ix.getList(ix.getRoot() + 'traffic', 'trafficItem')
    item_list = []
    for item in traffic_item_list:
        name = ix.getAttribute(item,'-name')
        if re.match(pattern,name): item_list.append(item)

    count = 0
    for item in item_list:
        flow_list = ix.getList(item, 'highLevelStream')
        for flow in flow_list:
            name = ix.getAttribute(flow,'-name')
            if re.match(flow_pattern,name):
                BuiltIn().log('    Modify flow `%s`' % name)
                count += 1
                frame_size_list  = ix.getList(flow, 'frameSize')
                for frame_size in frame_size_list:
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

    BuiltIn().log("Changed frame size of %d items" % count)
    return True




def set_traffic_item(self, *items, **kwargs):
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
        name = ix.getAttribute(item, '-name')
        traffic_data[name] = item

    for item in items:
        # acess traffic item by index if the item has format ::<num>
        indexes = re.findall(r'^::(\d+)$', item)
        if len(indexes) == 1:
            _index = int(indexes[0])
            if _index < len(traffic_items):
                target = traffic_items[_index]
            else:
                raise Exception("Error while setting traffic item")
        else:
            target = traffic_data[item]

        if target:
            ix.setAttribute(target, '-enabled', enabled)
        else:
            raise Exception("Error while setting traffic item")

    result = ix.commit()
    if result != '::ixNet::OK':
        raise Exception("Error while setting traffic item")

    BuiltIn().log("Set %d traffic items to `%s` state" % (len(items), enabled))

    return True


def set_all_traffic_item(self,enabled=True):
    """ Enables/Disables *all* traffic items at once
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

    *Note:* This is a asynchronus action. After called, the keyword finishes
    immediatly but it will take a while before traffic starts

    By default the keyword will wait for 30 seconds.
    """
    wait = DateTime.convert_time(wait_time)

    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    ix.execute('start',ix.getRoot()+'traffic')

    interval = 5
    elapsed_time = 0
    started = False
    while not started:
        BuiltIn().log('    wait %d seconds until traffic is started' % wait)
        time.sleep(interval)
        started = ix.getAttribute(ix.getRoot()+'traffic','-state') == u"started"
        elapsed_time += interval
        if elapsed_time >= wait and not started:
            raise Exception("ERROR: start traffic timed out")



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
    BuiltIn().log("Stopped the traffic")

    if stop_protocol :
        ix.execute('stopAllProtocols')
        BuiltIn().log("Stopped all protocols")
    time.sleep(wait)


def stop_all_protocols(self,wait_time='30s'):
    """ Stop all running protocols
    """

    wait = DateTime.convert_time(wait_time)

    cli = self._clients[self._cur_name]
    ix  = cli['connection']
    ix.execute('stopAllProtocols')

    time.sleep(wait)
    BuiltIn().log("Stopped all protocols")


def close(self):
    """ Disconnects the current tester client
    """

    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    result = ix.disconnect()
    if result != "::ixNet::OK": 
        raise Exception("Error while closing the connection")

    BuiltIn().log("Closed connection to `%s`" % self._cur_name)


def _fix_data(data):
    """
    """
    result = [[]]
    rows = re.findall(r'{{(.+?)}}',data)
    for row in rows:
        result[0].append(map(lambda x:re.sub(r'{|}','',x), re.findall(r'{.*?}|[^ ]+',row)))
    if not result[0]:
        result = map(lambda x:re.sub(r'{|}','',x), re.findall(r'{.*?}|[^ ]+',data))

    return result


def collect_data(self,view,prefix=u"stat_"):
    """ Depricated. Use `Get Test Result`
    """
    BuiltIn().log_to_console("WARNING: `Collect Data` is deprecated. Use `Get Test Result instead")
    self.get_test_result(view,prefix)


def get_test_result(self,view,prefix=u"stat_"):
    """ Collects traffic data of a ``view`` and export to a CSV file in
    ``result`` folder

    Currently, supported views are:

    ``Port Statistics``,
    ``Global Protocol Statistics``, ``BGP Aggregated Statistics``,
    ``BGP Aggregated State Counts``, ``OSPF Aggregated Statistics``,
    ``OSPF Aggregated State Counts``, ``OSPFv3 Aggregated Statistics``,
    ``OSPFv3 Aggregated State Counts``, ``L2-L3 Test Summary Statistics``,
    ``Flow Statistics``, ``Flow Detective``, ``Data Plane Port Statistics``,
    ``User Defined Statistics``, ``Traffic Item Statistics``

    Result were store as CSV files in ``result`` folder.
    If there is no valid data, view will be silently ignored

    The prefix ``prefix`` is appended to the view name for the CSV file.

    *Note*: the name of the result files are modified so that `space` will
    become `underbar`, `hyphen` will be deleted.
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']
    BuiltIn().log("Collecting data for view `%s`" % view)

    if not "::ixNet::OBJ" in view:
        view = ix.getRoot()+'/statistics/view:"%s"' % view

    # underbar in view name will be converted to space
    view = view.replace('_',' ')

    result_path = os.getcwd() + '/' + Common.get_result_folder()
    # null page should be ignored
    result_id = ix.setAsync().getAttribute(view+'/page','-isReady')
    time.sleep(5) # wait for 5 second
    is_done = ix.isDone(result_id)
    if is_done == u"true":
        ready = ix.getResult(result_id)
        if ready == u'false':
            BuiltIn().log("No statistic data for view `%s`" % view)
            return

        # set page size to 500 rows(max)
        ix.setAttribute(view+'/page','-pageSize',500)
        ix.commit()

        cap = ix.getAttribute(view+'/page', '-columnCaptions')
        if type(cap) is not list: cap = _fix_data(cap)

        # prepare CSV file
        file_name = view.split(':')[-1].strip('"') + '.csv'
        file_name = file_name.replace('-','')
        file_name = file_name.replace(' ','_')
        file_name = file_name.replace('__','_')
        file_name = prefix + file_name

        total_page = int(ix.getAttribute(view+'/page','-totalPages'))

        # open result file for write and preparing cap titles
        file_path = result_path + '/' + file_name
        f = open(file_path,'w+')
        w  = csv.writer(f, lineterminator='\n')
        w.writerow(cap)

        for page in range(total_page):
            ix.setAttribute(view+'/page','-currentPage',page+1)
            ix.commit()

            row = ix.getAttribute(view+'/page', '-pageValues')
            if row == '::ixNet::OK':
                row = ix.getAttribute(view+'/page', '-rowValues')

            if type(row) is not list: row = _fix_data(row)

            for i in range(len(row)):
                for j in range(len(row[i])):
                    w.writerow(row[i][j])

        f.close()
    BuiltIn().log("Got statistic data for view `%s`" % view)


def collect_all_data(self,prefix="stat_"):
    """ Deprecated. Use
    """
    BuiltIn().log_to_console("WARNING: `Collect All Data` is deprecated. Use `Get All Test Result` instead")
    self.get_all_test_result(prefix)


def get_all_test_result(self,prefix=u"stat_"):
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
        self.get_test_result(view,prefix)

    BuiltIn().log("Got all available test data")


def loss_from_file(self,file_name='Flow_Statistics.csv',index='0'):
    """ Returns ``packet loss`` by miliseconds and `delta frame`.

    Parameters:
    - `file_name`: flow information (csv format). Default is
      ``Flow_Statistics.csv``
    - `index`: row index of the result(counted from zero)

    Samples:
    | ${LOSS} | ${DELTA}= | Tester.`Loss From File` | Flow_Statistics.csv |
    | ${LOSS} | ${DELTA}= | Tester.`Loss From File` | Flow_Statistics.csv | index=1 |

    *Note*: The calculation should be performed when traffic is stopped.
    The calculation supposed traffic is configured by frame per second.
    """
    index_int=int(index)
    result_path = os.getcwd() + '/' + Common.get_result_folder()
    file_path = result_path + '/'  + file_name
    data = pd.read_csv(file_path,header=0)
    # data = data[data['First TimeStamp'].notnull()] # ignore null rows
    BuiltIn().log("    Read data from %s" % (file_path))

    frame_delta = int(data.filter(like='Frames Delta').loc[index_int])
    tx_frame    = int(data['Tx Frames'].loc[index_int])
    BuiltIn().log('----------')
    BuiltIn().log(data['First TimeStamp'].loc[index_int])
    BuiltIn().log('----------')
    data1 = data['First TimeStamp'].loc[index_int]
    data2 = data['Last TimeStamp'].loc[index_int]
    if pd.isnull(data1) or pd.isnull(data2) or tx_frame == 0:
        msec_loss   = None
        BuiltIn().log("Loss was %d frames, N/A miliseconds" % (frame_delta))
    else:
        h,res = data['First TimeStamp'].loc[index_int].split(':',1)
        time1 = timedelta(hours=int(h)) + datetime.strptime(res,'%M:%S.%f')

        h,res = data['Last TimeStamp'].loc[index_int].split(':',1)
        time2 = timedelta(hours=int(h)) + datetime.strptime(res,'%M:%S.%f')

        # time1       = datetime.strptime(data['First TimeStamp'].loc[index_int],"%H:%M:%S.%f")
        # time2       = datetime.strptime(data['Last TimeStamp'].loc[index_int],"%H:%M:%S.%f")
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
    | Tester.`Set BGP Item` | 0 | 1 | vport_index=0 | enabled=${FALSE} |
    | Tester.`Set BGP Item` | 0 | 1 | vport_index=1 | enabled=${TRUE} |
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
    - ``neighbor_index``: index of the neighbor or ``*``
    - ``route_range_index``: index of the route range or ``*``
    - ``is_enable``: ${TRUE} or ${FALSE}

    Note

    Examples:
    | Tester.`Set BGP Items`  |   0  |  *  |   *  |   ${FALSE} |
    | Tester.`Set BGP Items`  |   0  |  *  |   *  |   ${TRUE}  |

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

def set_capture_port(self,data_mode=True,control_mode=True,port_index=0):
    """ Capture packets for follow ``port``

    ``port_index``:     is a index of current test port (start from 0)
    ``data_mode``:      capture data packets and save in <intf>_HW.cap file
    ``control_mode``:   capture controls packets and save in <intf>_SW.cap file

    *Note*: ``control_mode`` saves all control packets and ``data_mode`` only
    saves data packets.

    *Note*: ``control_mode`` saves all control packets and ``data_mode`` only
saves data packet

    Examples:
    | Tester.`Set Capture Port` | 0 |
    | Tester.`Set Capture Port` | control_mode=${TRUE} | 0 | 1 |

    """

    cli = self._clients[self._cur_name]
    ix  = cli['connection']
    vports      = ix.getList(ix.getRoot(),'vport')

    ix.execute('closeAllTabs')
    port = vports[int(port_index)]
    desc = ix.getAttribute(port,'-name')
    # ix.setAttribute(port,'-rxMode','capture')
    ix.setAttribute(port,'-rxMode','captureAndMeasure')
    ix.setAttribute(port+'/capture', '-hardwareEnabled', data_mode)
    ix.setAttribute(port+'/capture', '-softwareEnabled', control_mode)
    ix.commit()

    BuiltIn().log("Set capture data=`%s` control=`%s` for port `%s`" % (data_mode,control_mode,desc))

def start_capture(self,wait_time='30s'):
    """ Start packet capture

    Target ports are set by the configuration file or by [Set Capture] keyword
    """

    wait = DateTime.convert_time(wait_time)
    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    ix.execute('startCapture')
    time.sleep(wait)

    BuiltIn().log("Started packet capture")


def stop_and_save_capture(self,prefix='',wait_until_finish=True,monitor_interval='5s'):
    """ Stop current capture and save the resuls to folder specified by ``path``

    Captured files will be saved in current ``result`` folder with ``prefix``
    appended in their names.

    Examples:
    | Tester.`Start Capture` |
    | Sleep                  | 10s |
    | Tester.`Stop And Save Capture` | ${RESULT_FOLDER}/capture.zip |

    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']
    vports      = ix.getList(ix.getRoot(),'vport')
    interval = DateTime.convert_time(monitor_interval)

    ix.execute('stopCapture')

    if wait_until_finish:
        all_ready = False
        while not all_ready:
            all_ready = True
            time.sleep(interval)
            BuiltIn().log("    wait for more %s ..." % monitor_interval)
            for port in vports:
                mode = ix.getAttribute(port,'-rxMode')
                data_mode       = ix.getAttribute(port + '/capture','-hardwareEnabled') == 'true'
                control_mode    = ix.getAttribute(port + '/capture','-softwareEnabled') == 'true'
                if mode == 'capture' or mode == 'captureAndMeasure':
                    if data_mode:
                        ready = ix.getAttribute(port + '/capture', '-dataCaptureState')
                        all_ready = all_ready and (ready == 'ready')
                    if control_mode:
                        ready = ix.getAttribute(port + '/capture', '-controlCaptureState')
                        all_ready = all_ready and (ready == 'ready')

    folder = ix.getAttribute(ix.getRoot()+'/testConfiguration','-resultPath')
    # temporary folder
    folder = Common.get_config_value('ix-remote-tmp') + '/' + cli['device'] + '_' + os.getcwd().replace('/','_')
    ix.execute('saveCapture', folder)

    count = 0
    for port in vports:
        mode = ix.getAttribute(port,'-rxMode')
        if mode == 'capture' or mode == 'captureAndMeasure':
            name = ix.getAttribute(port,'-name')
            src1 = folder + '/' + name + '_HW.cap'
            src2 = folder + '/' + name + '_SW.cap'
            name = name.replace('-','')
            name = name.replace(' ','_')
            name = name.replace('__','_')
            dst1 = Common.get_result_path() + '/' + prefix + name + '_HW.cap'
            dst2 = Common.get_result_path() + '/' + prefix + name + '_SW.cap'
            try:
                ix.execute('copyFile',ix.readFrom(src1,'-ixNetRelative'),ix.writeTo(str(dst1)))
            except:
                err_msg = (
                    'Tried to copy file {s}'
                    'because interface {p} was in mode {m}'
                    'This operation failed, please investigate'.format(
                        s=src1, p=port, m=mode
                    )
                )
                BuiltIn().log(err_msg)
            try:
                ix.execute('copyFile',ix.readFrom(src2,'-ixNetRelative'),ix.writeTo(str(dst2)))
            except:
                err_msg = (
                    'Tried to copy file {s}'
                    'because interface {p} was in mode {m}'
                    'This operation failed, please investigate'.format(
                        s=src2, p=port, m=mode
                    )
                )
                BuiltIn().log(err_msg)
                count = count + 2


    BuiltIn().log("Stopped packet capture and saved %d files" % count)


def get_quicktest_list(self):
    """ Returns current loaded Quicktest list
    """

    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    test_list = ix.getAttribute(ix.getRoot() + '/quickTest', '-testIds')
    BuiltIn().log("Get current loaded Quictest list: %d items" % (len(test_list)))

    return test_list


def stop_quicktest(self,test_index='0'):
    """ Stops a running test
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    index = int(test_index)
    test_list = ix.getAttribute(ix.getRoot() + '/quickTest', '-testIds')
    ix.execute('stop',test_list[index])

    BuiltIn().log("Stopped the Quicktest")


def add_port(self,force=True,time_out='2m',learn_time='2m'):
    """ Add ports using the ``real-port`` information from active local config

    - ``time_out`` is the wait time until port is connected (default is 2m)
    - ``learn_time`` is the time waiting for arp to be learned (default is 2m)

    Sample of local config
|tester:
|    tester:
|        device: ixnet03_8009
|        config: quicktest.ixncfg
|        real-port:
|            -   chassis: 10.128.4.41
|                card: 4
|                port: 3
|                ip: 10.100.11.2
|                mask: 24
|                gw: 10.100.11.1
|            -   chassis: 10.128.4.41
|                card: 4
                port: 4
|                ip: 10.100.14.2
|                mask: 24
|                gw: 10.100.14.1

    """

    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    wait_time = DateTime.convert_time(time_out)

    real_ports = []
    vports = []
    port_data = Common.LOCAL['tester'][self._cur_name]['real-port']
    for item in port_data:
        chassis = item['chassis']
        card    = item['card']
        port    = item['port']
        real_ports.append((chassis,card,port))

    # assign ports
    result_id = ix.setAsync().execute('assignPorts',real_ports,[],vports,force)

    interval = 5
    is_done = "false"
    count = 0
    while is_done == "false" and count < wait_time:
        count = count + 5
        BuiltIn().log_to_console('.','STDOUT',True)
        time.sleep(interval)
        is_done = ix.isDone(result_id)
        BuiltIn().log("    is_done = %s, wait for more %d seconds ..." % (is_done,interval))

    if is_done != "true":
        raise Exception("ERROR: Error while remapping ports: hardware failure or wrong chassis IP")

    # wait for ports become enable
    self.wait_until_connected(wait_time)

    vports = ix.getList(ix.getRoot(),'vport')

    # adding Ether protocol to port
    # how about other type ?
    for data,port in zip(port_data,vports):
        if 'tx_mode' in data: tx_mode = data['tx_mode']
        else: tx_mode = 'interleaved'
        ix.setAttribute(port,'-transmitMode',tx_mode)
        interface = ix.add(port,'interface')
        ix.setAttribute(interface,'-enabled','true')
        ip = ix.add(interface,'ipv4')
        ix.setAttribute(ip,'-ip',data['ip'])
        ix.setAttribute(ip,'-maskWidth',data['mask'])
        ix.setAttribute(ip,'-gateway',data['gw'])


    result = ix.commit()
    if result != '::ixNet::OK' :
        raise Exception("ERROR: " + result)

    # need time for the ARP learning
    time.sleep(DateTime.convert_time(learn_time))

    BuiltIn().log("Added %d Ixia ports" % len(port_data))



def add_quicktest(self,name,test_type=u'rfc2544throughput',tx_mode=u'interleaved',clear_all=True):
    """ Create a new Quicktest with default value

    Type could be one of following: ``rfc2544throughput``, ``rfc2544frameLoss``,
    ``rfc2544back2back``. Use Tester.`Load Config` to load a customized quicktest

    When ``clear_all`` is True, any existed quicktests will be cleared.

    Transmit mode ``tx_mode`` takes following values: ``interleaved`` (default)
    or ``sequential``. The mode should be identical with the transmit mod of the
    ports.

    *Notes*: The keyword *does not* create necessary ports. It should be used with a
    existed configuration by Tester.`Load Config` or Tester.`Add Port` keyword.
    """
    BuiltIn().log("Adding quicktest `%s`" % name)
    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    if clear_all:
        test_list = ix.getAttribute(ix.getRoot() + '/quickTest', '-testIds')
        for test in test_list:
            ix.remove(test)
        traffic_item_list = ix.getList(ix.getRoot() + 'traffic', 'trafficItem')
        for item in traffic_item_list:
            ix.remove(item)
        ix.commit()
        BuiltIn().log("    cleared all %d existed Quicktest items" % (len(test_list)))

    test = ix.add(ix.getRoot()+'/quickTest',str(test_type))
    ix.setMultiAttribute(test,'-name',str(name),'-mode','newMode')
    result = ix.commit()
    if result != '::ixNet::OK':
        raise Exception("ERROR: could not create new Quicktest")
    BuiltIn().log("    added and commited `%s` quicktest" % name)

    vports = ix.getList(ix.getRoot(),'vport')

    # apply traffic item
    result = ix.execute('apply',test) # apply will create traffic items
    if result != '::ixNet::OK':
        raise Exception("ERROR: could not applying the config of configured Quicktest")

    # customize more
    tx_mode='interleaved'
    for port in vports:
        ix.setAttribute(port,'-txMode',str(tx_mode))
    traffic_items = ix.getList(ix.getRoot()+'/traffic','trafficItem')

    ix.setAttribute(traffic_items[0],'-trafficType', 'ipv4')
    for item in traffic_items:
        ix.setAttribute(item,'-transmitMode',str(tx_mode))

    # 1st half will be TX and 2nd half will be RX
    end_point = ix.add(traffic_items[0],'endpointSet')
    half = int(len(vports) / 2)
    for i in range(0,half):
        ix.setMultiAttribute(end_point,'-sources',vports[i]+'/protocols','-destinations',vports[half+i]+'/protocols')

    # end_point = ix.add(traffic_items[0],'endpointSet','-sources',vports[0]+'/protocols','-destinations',vports[1]+'/protocols')
    result = ix.commit()
    if result != '::ixNet::OK':
        raise Exception("ERROR: could not create new Quicktest")

    BuiltIn().log("Created a new Quicktest with type `%s` for %d ports " % (test_type,len(vports)))


def get_quicktest_name(self,test_index='0'):
    """ Return quicktest name by its index
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']
    test_ids = ix.getAttribute(ix.getRoot() + '/quickTest', '-testIds')
    test = test_ids[int(test_index)]
    name = ix.getAttribute(test,'-name')
    BuiltIn().log('Get name for the test id `%d`' % int(test_index))
    return name


def get_quicktest_index(self,test_name):
    """ Return quicktest name by its name
    """
    result = None
    cli = self._clients[self._cur_name]
    ix  = cli['connection']
    test_ids = ix.getAttribute(ix.getRoot() + '/quickTest', '-testIds')
    count = 0
    for item in test_ids:
        name = ix.getAttribute(item,'-name')
        if name == test_name:
            result = count
            break
        count += 1
    BuiltIn().log('Got index for the test name `%s`' % test_name)
    return result


def run_quicktest_by_name(self,test_name,wait_until_finish=True):
    """ Runs a quicktest by its name
    """
    test_index = self.get_quicktest_index(test_name)
    return self.run_quicktest(test_index,wait_until_finish)


def run_quicktest(self,test_index='0',wait_until_finish=True):
    """ Runs a quicktest and wait until it finishes

    *Warning*: it could take a long time to finish a quicktest
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    index = int(test_index)

    test_list = ix.getAttribute(ix.getRoot() + '/quickTest', '-testIds')
    result = ix.execute('start',test_list[index])
    # BuiltIn().log_to_console(result)

    # interval for recheck the proress
    interval = 30

    if not wait_until_finish:
        BuiltIn().log("Started the Quicktest. Test is still running")
    else:
        elapsed_time = 0
        is_running = ix.getAttribute(test_list[index]+'/results','-isRunning')
        while is_running == 'true':
            BuiltIn().log_to_console('.','STDOUT',True)
            time.sleep(interval)
            elapsed_time = elapsed_time + interval
            is_running = ix.getAttribute(test_list[index]+'/results','-isRunning')

        result = ix.getAttribute(test_list[index]+'/results','-result')
        if result == 'fail':
            str = "ERROR: Quicktest failed"
            BuiltIn().log(str)
            raise Exception(str)
        else:
            BuiltIn().log("Ran and finished the Quicktest with result `%s` in %d seconds" % (result,elapsed_time))




def get_test_report(self,name='ixnet_report.pdf',enable_all=True):
    """ Generates and get report of the current active test in PDF format

    ``name``: name of the report on local machine. Default is ``ixnet_report.pdf``
    """
    BuiltIn().log("Get report of the current test")

    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    ix.setMultiAttribute(
        ix.getRoot()+'/reporter/testParameters',
        '-testCategory','RENAT item',
        '-testDUTName','DUT',
        '-testerName',cli['desc'],
        '-testName',Common.get_item_name())

    result_path = ix.getAttribute(ix.getRoot()+'/testConfiguration','-resultPath')
    BuiltIn().log("    current result path is `%s`" % result_path)

    # prepare report using default template
    report_file = result_path + '/report.pdf'
    ix.setMultiAttribute(ix.getRoot()+'/reporter/generate',
        '-outputFormat','pdf',
        '-outputPath',str(report_file))
    ix.commit()

    # enable all statistics
    if enable_all:
        ix.setAttribute(ix.getRoot()+'/reporter/saveResults','-enableAllResult','true')
        ix.commit()
    # save result in details
    ix.execute('saveDetailedResults',ix.getRoot()+'/reporter/saveResults')
    state = ix.getAttribute(ix.getRoot()+'/reporter/saveResults','-state')
    while state != 'done':
        state = ix.getAttribute(ix.getRoot()+'/reporter/saveResults','-state')
        BuiltIn().log_to_console('.','STDOUT',True)
        time.sleep(5)

    # generate report
    ix.execute('generateReport',ix.getRoot()+'/reporter/generate')
    state = ix.getAttribute(ix.getRoot()+'/reporter/generate','-state')
    BuiltIn().log("init state = %s" % state)
    while state != 'done':
        state = ix.getAttribute(ix.getRoot()+'/reporter/generate','-state')
        BuiltIn().log_to_console('.','STDOUT',True)
        time.sleep(5)

    # copy to local folder (renat server)
    dst_file = Common.get_result_path() + '/' + name
    ix.execute('copyFile',ix.readFrom(report_file,'-ixNetRelative'),ix.writeTo(dst_file,'-overwrite'))
    BuiltIn().log("Got the report file `%s`" % name)


def get_quicktest_result_path(self,test_index=u'-1'):
    """ Returns the path of the newest run of a Quicktest

    ``test_index`` is a index of the current  Quicktest. ``-1`` means that last one.
    """
    BuiltIn().log("Get Quicktest result path")
    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    index = int(test_index)
    # get quicktest list
    index = int(test_index)
    test_list = ix.getAttribute(ix.getRoot() + '/quickTest', '-testIds')
    BuiltIn().log("    Got %d tests" % len(test_list))
    # get the result path
    result_path = ix.getAttribute(test_list[index]+'/results','-resultPath')
    if result_path == "":
        raise Exception("ERROR: did not found a result of this test. Run it first")

    BuiltIn().log("Got the path of the newest run: %s" % result_path)
    return result_path


def get_quicktest_result_by_name(self,name=None,prefix='',enable_all=True):
    """ Get quicktest results by its name

    Default(None) is the last one
    """
    if name:
        index = self.get_quicktest_index(name)
    else:
        index = -1
    BuiltIn().log('Got result for quicktest `%s`' % name)
    return self.get_quicktest_result(index,prefix,enable_all)



def get_quicktest_result(self,test_index=u'-1',prefix='',enable_all=True):
    """ Get the result.csv file from the latest Quicktests

    ``test_index`` is a index of the current  Quicktest. ``-1`` means that last one.
    """

    BuiltIn().log("Get result of the `%s` Quicktest" % test_index)

    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    index = int(test_index)

    # get quicktest list
    index = int(test_index)
    test_list = ix.getAttribute(ix.getRoot() + '/quickTest', '-testIds')

    # get the result path
    result_path = ix.getAttribute(test_list[index]+'/results','-resultPath')
    if result_path == "":
        raise Exception("ERROR: did not found a result of this test. Run it first")

    # enable all statistics
    if enable_all:
        ix.setAttribute(ix.getRoot()+'/reporter/saveResults','-enableAllResult','true')
        ix.commit()
    # save result in details
    ix.execute('saveDetailedResults',ix.getRoot()+'/reporter/saveResults')
    state = ix.getAttribute(ix.getRoot()+'/reporter/saveResults','-state')
    while state != 'done':
        state = ix.getAttribute(ix.getRoot()+'/reporter/saveResults','-state')
        BuiltIn().log_to_console('.','STDOUT',True)
        time.sleep(5)

    file_list = [
        'results.csv',
        'AggregateResults.csv',
        'BGP Aggregated Statistics.csv',
        'Data Plane Port Statistics.csv',
        'Flow Statistics.csv',
        'Flow View.csv',
        'Global Protocol Statistics.csv',
        'L2-L3 Test Summary Statistics.csv',
        'Port CPU Statistics.csv',
        'Port Statistics.csv',
        'Traffic Item Statistics.csv',
        'PortMap.csv',
        'Real Time Stats.csv',
        'User Defined Statistics.csv' ]

    count = 0
    for item in file_list:
        src_file = result_path + '/' + item
        dst_file = Common.get_result_path() + '/' + prefix + item.replace(' ','_')
        try:
            ix.execute('copyFile',ix.readFrom(src_file,'-ixNetRelative'),ix.writeTo(dst_file,'-overwrite'))
            count = count + 1
        except IxNetwork.IxNetError as err:
            BuiltIn().log("   Could not found `%s`, but ignore that" % item)

    BuiltIn().log("Got %d result files for the Quicktest" % count)


def should_be_pingable(self,dst_ip,src_port_index=0,src_intf_index=0):
    """ Ping from Ixia and raise an error if ping fails

        The keyword return `True` if succeeds
    """
    output = self.ping(dst_ip,src_port_index,src_intf_index)
    if 'failed' in output or 'Error' in output:
        BuiltIn().log("ERROR: ping to `%s` failed with result `%s`" % (dst_ip,output))
        raise Exception(output)
    else:
        BuiltIn().log("Pinged successful to `%s` with output `%s`" % (dst_ip,output))
        return True


def ping(self,dst_ip,src_port_index=0,src_intf_index=0):
    """ Ping from Ixia to ``dst_ip``

    The keyword return the output string as it is. The return could be
    | - Port <portName>: ping failed: port not assigned
    | - Response received from <sourceIp>/unknown . Sequence Number <sequenceNumber>
    | - Ping request to <destinationIp>/unknown ip failed: <GenericPingError>/<error>: <genericError>unknown reason
    | - Error: Couldn't find any source interface for Send Ping to <destinationIp> on <portName> Id <id>
    | - Error: Couldn't find any source IP for Send Ping to <destinationIp> on <portName> Id <id>

    Parameters:
    - src_port_index: index of Ixia port (starts from 0)
    - src_intf_index: index of interface insides the port (starts from 0)

    Examples:
    | Tester.`Ping`  | 1.1.1.1 | 0 | 0 |
    | Tester.`Ping`  | 1.1.1.1 |
    """

    BuiltIn().log("Ping IP address `%s`" % dst_ip)

    cli = self._clients[self._cur_name]
    ix  = cli['connection']
    vports = ix.getList(ix.getRoot(),'vport')

    port = vports[int(src_port_index)]
    interfaces = ix.getList(port,'interface')
    intf = interfaces[int(src_intf_index)]

    output = ix.execute("sendPing",intf,dst_ip)
    BuiltIn().log("Pinged `%s` with result `%s`" % (dst_ip,output))
    return output


def regenerate(self):
    """ Regenerates *all* flow of current traffic items
    """

    BuiltIn().log("Regenerate flows for current traffic items")
    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    traffic_items = ix.getList(ix.getRoot()+'traffic','trafficItem')

    for item in traffic_items:
        ix.execute('generate', item)

    BuiltIn().log("RegenerFinishedate flows for %d traffic items" % len(traffic_items))



def start_test_composer(self,script_name=u'Main_Procedure',run_num=u'1',wait_for_test=True,parameter=u'',wait=u'10s'):
    """ Run a test composer script.

    The test composer script should be included in an Ixia Network configuration
    file and loaded properly with `Load Config`

    Parameters:
    - ``script_name`` is the name of the script to run. Default value is ``Main_Procedure``.
    - ``wait_for_test``: if ``${TRUE}`` then wait until the script finishes.
    - ``parameter``: parameter that is passed to the script. Parameter could be
      in 2 formats: ``{{VAR1 VALUE1} {VAR2 VALUE2}}`` or simply as ``VALUE1 VALUE2``.
    The script must prepare `VAR1` and `VAR2` properly by `Test
    parameter`. See Ixia Network anout composer script for more details.
    - ``wait``: wait time before go to next keyword

    Examples:
    | Tester.`Start Test Composer` | parameter=XXX YYY |
    | Tester.`Get Test Composer Result` | result_file=script1.log |
    | Tester.`Start Test Composer` | parameter={{VAR1 AAA} {VAR2 BBB}} |
    | Tester.`Get Test Composer Result` | result_file=script1.log |

    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    composer_runner = None
    sched = None

    BuiltIn().log("Start a test composer script")
    quicktest_list = ix.getList(ix.getRoot() + 'quickTest','eventScheduler')

    if len(quicktest_list) > 0:
        for item in quicktest_list:
            name = ix.getAttribute(item,'-name')
            if name == 'composer_runner':
                BuiltIn().log("    Found an existed composer_runner test")
                composer_runner = item
                sched = ix.getList(composer_runner,'eventScheduler')[0]
                break

    # create new quicktest item if it is neccessary
    if composer_runner is None:
        composer_runner = ix.add(ix.getRoot() + '/quickTest','eventScheduler')
        ix.setAttribute(composer_runner,'-name','composer_runner')
        sched = ix.add(composer_runner,'eventScheduler')
        name = str(script_name)
        ix.setMultiAttribute(sched,'-enabled','true','-itemId',name,'-itemName',name)

    # setting parameter
    ix.setAttribute(sched,'-parameters',str(parameter))

    config = ix.getList(composer_runner,'testConfig')
    ix.setAttribute(config[0],'-numTrials',int(run_num))
    ix.setAttribute(config[0],'-protocolItem',[])
    ix.commit()
    composer_runner = ix.remapIds(composer_runner)[0]

    # start the script
    ix.execute('start', composer_runner)
    if wait_for_test:
        BuiltIn().log("    Wait until the script finishes")
        ix.execute('waitForTest', composer_runner)

    time.sleep(DateTime.convert_time(wait))
    BuiltIn().log("Finished a test compose script")



def stop_test_composer(self,wait='10s'):
    """ Stop a running composer

    Do nothing when a test composer has already stopped or no composer has been
    prepared.
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    composer_runner = None

    BuiltIn().log("Stop a test composer script")
    quicktest_list = ix.getList(ix.getRoot() + 'quickTest','eventScheduler')

    if len(quicktest_list) > 0:
        for item in quicktest_list:
            name = ix.getAttribute(item,'-name')
            if name == 'composer_runner':
                composer_runner = item
                break

    if composer_runner:
        ix.execute('stop', composer_runner)
        time.sleep(DateTime.convert_time(wait))
        BuiltIn().log("Stopped the current composer script")
    else:
        BuiltIn().log("No running composer is found")


def get_test_composer_result(self,result_file=u'composer.log'):
    """ Get the result of test composer script
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']

    BuiltIn().log("Get test composer result")
    composer_runner = None

    quicktest_list = ix.getList(ix.getRoot() + 'quickTest','eventScheduler')
    if len(quicktest_list) > 0:
        for item in quicktest_list:
            name = ix.getAttribute(item,'-name')
            if name == 'composer_runner':
                composer_runner = item
                break

    if composer_runner:
        result_path = ix.getAttribute(composer_runner+'/results','-resultPath')
        src_path = result_path + '/logFile.txt'
        dst_path = Common.get_result_path() + '/' + str(result_file)
        BuiltIn().log("    result src: %s" % src_path)
        BuiltIn().log("    result dst: %s" % dst_path)
        ix.execute('copyFile',ix.readFrom(src_path,'-ixNetRelative'),ix.writeTo(dst_path))

        BuiltIn().log("Got log file from %s" % result_path)
    else:
        BuiltIn().log("No composer runner found")


def csv_snapshot(self,prefix='snapshot_',*views):
    """ Get current CSV snapshot

    Parameters:
    - `prefix`: prefix that be added to the filename. Default is ``snapshot_``
    - `views`: list of target views (eg: ``Port Statistics``, ``Flow Statistics``
      ...). If `view` is ``None``, all current available views will be target

    Samples:
    | Tester.`CSV Snapshot`  | snapshot03_  |  # collect all views |
    | Tester.`CSV Snapshot`  | snapshot03_  |  Port Statistics  | Flow Statistics | # collect specific views |

    *Note*: the name of result file will be modified so `space` will be replaced
    by `underbar`.

    Depending on the traffic status, the available views could be varied. For
    example, the view `Flow Statistics` is not available when there is no traffic.
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']
    setting_name='%s_%s' % (Common.get_myid(),time.strftime('%Y%m%d%H%M%S'))
    # remote path
    remote_path='%s/%s_%s' % (Common.get_config_value('ix-remote-tmp'),cli['device'],os.getcwd().replace('/','_'))
    # first get the default setting
    opt = ix.execute('GetDefaultSnapshotSettings')
    # then customize the setting
    opt[1]='Snapshot.View.Csv.Location: "%s"' % remote_path
    opt[2]='Snapshot.View.Csv.GeneratingMode: "kOverwriteCSVFile"'
    opt[8]='Snapshot.Settings.Name: "%s"' % setting_name
    if views:
        # in case user use under for space in view name
        current_views = list(map(lambda x: x.replace('_',' '),views))
    else:
        system_views=ix.getList(ix.getRoot() + 'statistics','view')
        current_views=list(map(lambda x: x.split(':')[-1].replace('"',''),system_views))
    result = ix.execute('TakeViewCSVSnapshot',current_views,opt)
    if result != '::ixNet::OK' :
        raise result

    for item in current_views:
        src_path = '%s/%s.csv' % (remote_path,item)
        dst_path = '%s/%s%s.csv' % (Common.get_result_path(),prefix,item.replace(' ','_'))
        BuiltIn().log(item)
        BuiltIn().log(src_path)
        BuiltIn().log(dst_path)
        result = ix.execute('copyFile',ix.readFrom(src_path,'-ixNetRelative'),ix.writeTo(dst_path,'-overwrite'))
        if result != '::ixNet::OK' :
            raise result

    BuiltIn().log('Took snapshots of %d views' % (len(current_views)))


def csv_logging(self, enabled=True, *views):
    """ Toggles enable/disable CSV loggin for a view

    Parameters:
    - `views`: is a list of views. `None` means all views.

    Result files will have format <View name>.index.csv, when index is
    automatically increased everytime the view is disable and re-enable again in the
    same test.

    Samples:
    | Tester.`CSV Logging`  | ${TRUE}  |  Flow Statistics |
    | Sleep    | 10s |
    | Tester.`CSV Logging`  | ${FALSE} |  Flow Statistics |

    *Note*:
       Long time enable fof CSV loggin could returns in very big file
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']
    count = 0

    if enabled:
        value = 'true'
    else:
        value = 'false'

    if views:
        current_views = list(map(lambda x: x.replace('_',' '),views))
    else:
        system_views=ix.getList(ix.getRoot() + 'statistics','view')
        current_views=list(map(lambda x: x.split(':')[-1].replace('"',''),system_views))

    for item in current_views:
        view = '%sstatistics/view:\"%s\"' % (ix.getRoot(),item.replace('_',' '))
        ix.setMultiAttribute(view,'-enabled',value,'-enableCsvLogging',value)
        BuiltIn().log('    set CSV logging for %s to %s' % (view,value))
        count += 1
    ix.commit()
    BuiltIn().log('Enabled CSV logging for %d views' % count)


def get_csv_log(self, prefix='', index=u'-1', *views):
    """ Gets all CSV log for a specific views or all from current test folder

    Parameters:
    - `views` is a list of views. `None` is all views.
    - `prefix` will be appended automatically to the beginning of the result
    - `range`: number of files from the newest data. `-1` for only 1 newest and
      `:` for all files.

    Samples:
    | Tester.`Get CSV Log` |  single_ | -1 | # get the newest CSV logging data for all views |
    | Tester.`Get CSV Log` |  all_  | : |  Flow Statistics | # get all CSV logging data for one view |

    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']
    src_folder = ix.getAttribute(ix.getRoot() + 'statistics','-csvFilePath')
    # collect target views by their name
    if views:
        # in case user use under for space in view name
        current_views = list(map(lambda x: x.replace('_',' '),views))
    else:
        system_views=ix.getList(ix.getRoot() + 'statistics','view')
        current_views=list(map(lambda x: x.split(':')[-1].replace('"',''),system_views))

    # get file list
    tmp_file = '%s/tmp/aptixia_reporter_xmd.xml' % (os.getcwd())
    filelist = '%s/aptixia_reporter_xmd.xml' % src_folder
    result = ix.execute('copyFile',ix.readFrom(filelist,'-ixNetRelative'),ix.writeTo(tmp_file,'-overwrite'))
    if result != '::ixNet::OK' : raise result

    #
    root = ET.parse(tmp_file).getroot()
    count = 0
    for view in current_views:
        # make file list
        csv_list = [x.attrib['scope'] for x in root.findall('.//Source[@entity_name="%s"]' % view) ]
        if index.lower() in [':','all']:
            for csv_file in csv_list:
                dst_file = '%s/%s%s' % (Common.get_result_path(),prefix,csv_file.replace(' ','_'))
                src_file = '%s/%s' % (src_folder,csv_file)
                BuiltIn().log('copy from %s to %s' % (src_file,dst_file))
                result = ix.execute('copyFile',ix.readFrom(src_file,'-ixNetRelative'),ix.writeTo(dst_file,'-overwrite'))
                if result != '::ixNet::OK' : raise result
                count += 1
        else:
            csv_file = csv_list[int(index)]
            dst_file = '%s/%s%s' % (Common.get_result_path(),prefix,csv_file.replace(' ','_'))
            src_file = '%s/%s' % (src_folder,csv_file)
            BuiltIn().log('copy from %s to %s' % (src_file,dst_file))
            result = ix.execute('copyFile',ix.readFrom(src_file,'-ixNetRelative'),ix.writeTo(dst_file,'-overwrite'))
            if result != '::ixNet::OK' : raise result
            count += 1
    BuiltIn().log('Got %d CSV log files' % count)


def get_view_csv_log(self,view,prefix=''):
    """ Gets the newest CSV log file of the specific view
    """
    self.get_csv_log(prefix,u'-1',view)


def get_view_all_csv_logs(self,view,prefix=''):
    """ Gets the newest CSV log file of *ALL* available views
    """
    self.get_csv_log(prefix,u':',view)


def get_all_views_csv_log(self,prefix=''):
    """ Gets the newest CSV log of all available views
    """
    self.get_csv_log(prefix,u'-1')


def get_all_views_all_csv_logs(self,prefix=''):
    """ Gets all CSV logs for all available views
    """
    self.get_csv_log(prefix,u':')


def link_up_down_by_index(self,port_index=u'0',state=u'up'):
    """ Simulates a LinkUpDown by port index

    Parameters:
        - `port_index`: zero-started port index
        - `state`: is `up` or `down`

    Samples:
    | Tester.`Link Up Down By Index` | 0 | down |
    | Sleep | 5s |
    | Tester.`Link Up Down By Index` | 0 | up |
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']
    vport_list  = ix.getList(ix.getRoot(),'vport')
    target_port = vport_list[int(port_index)]
    port_name = ix.getAttribute(target_port,'-name')
    result = ix.execute('linkUpDn',target_port,state.lower())
    if result != '::ixNet::OK' :
        raise result
    BuiltIn().log('Simulate a link `%s` on port `%s`' % (state.lower(),port_name))


def link_up_down_by_name(self,port_name,state=u'up'):
    """ Simulates a LinkUpDown by port name

    Parameters:
        - `port_index`: zero-started port index
        - `state`: is `up` or `down`

    Samples:
    | Tester.`Link Up Down By Name` | Ethernet - 001 | down |
    | Sleep | 5s |
    | Tester.`Link Up Down By Name` | Ethernet - 001 | up |
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection']
    vport_list  = ix.getList(ix.getRoot(),'vport')
    target_port_list = list(filter(lambda x: ix.getAttribute(x,'-name')==port_name, vport_list))
    if len(target_port_list) > 0 :
        result = ix.execute('linkUpDn',target_port_list[0],state.lower())
        if result != '::ixNet::OK' :
            raise result
    else:
        raise Exception('ERROR: could not found port name: `%s`' % port_name)
    BuiltIn().log('Simulate a link `%s` on port `%s`' % (state.lower(),port_name))


def clear_statistics(self):
    """
    Clear all statistics information
    """
    cli = self._clients[self._cur_name]
    ix = cli['connection']
    ix.execute('clearStats')
    BuiltIn().log("Cleared all statisctics information")


