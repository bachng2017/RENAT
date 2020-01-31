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


""" Provides Spirent Avalance keywords

== Table of Contents ==
    - `Usage`
    - `Test Result`
    - `Keywords`

= Usage =
    The module need to be used with a AVA proxy server with topology looks like
this:

|    this module <=> AVA proxy server (32bit) <=> AVA 32bit library <=> AVA hardware

SPF test files should be exported from AVA GUI.

Sample ``local.yaml`` setting for AVA

| # tester information
| tester:
|     ava01:
|         device: ava01
|         config: config.spf
|         real-port:
|             -   chassis:    10.128.64.231
|                 card:       1
|                 port:       1
|             -   chassis:    10.128.64.232
|                 card:       1
|                 port:       1

The device `ava01` is define as below in global `device.yaml`:
|     ava01:
|         type: avaproxy
|         description: a AVA proxy (32bit)
|         license-server: 10.128.64.222
|         ip: 10.128.64.104
|         port: 5001
*Note*: the `license-server` field is optional.

and the account is define in `auth.yaml` under `avaproxy` section
|        avaproxy:
|            user: admin

= Test Result =
The AVA result is collected and save into the foler `ava` under current active
`result` folder. The merged resuls for client/server is a XML file as
`ava/result/merged/results.xml`.

Some predefined stylesheets are provided under `tools/xslt` folder and could be
use to reformat this result like belows samples:

| Common.`Convert XML` | ${RENAT_PATH}/tools/xslt/merged2html.xls | ${CURDIR}/${RESULT_FOLDER}/ava/merged/results.xml | ${CURDIR}/${RESULT_FOLDER}/ava_merged.html |
| Common.`Convert XML` | ${RENAT_PATH}/tools/xslt/merged2csv.xls | ${CURDIR}/${RESULT_FOLDER}/ava/merged/results.xml | ${CURDIR}/${RESULT_FOLDER}/ava_merged.csv |

*Note*: AVA proxy server is not a part of Spirent solutions.
"""

import sys,os,re,shutil
import Common
from robot.libraries.BuiltIn import BuiltIn
import robot.libraries.DateTime as DateTime

def close(self):
    """ Disconnect to the remote server
    """
    cli  = self._clients[self._cur_name]
    avaproxy = cli['connection']

    res = Common.send(avaproxy,'ava::logout')
    BuiltIn().log('Closed the AVA proxy connection')
    return res


def load_config(self,config_name=''):
    """ Loads the SPF config file and reseres necessary port
    """
    cli  = self._clients[self._cur_name]
    avaproxy = cli['connection']
    if config_name == '':
        config_name = Common.LOCAL['tester'][self._cur_name]['config']

    # load config
    config_path = Common.get_item_config_path() + '/' + config_name
    file_size = int(os.path.getsize(config_path))
    res = Common.send(avaproxy,'ava::send_file/%d/config.spf' % file_size)
    if res == 'ava::ok':
        with open(config_path,'rb') as f:
            data = f.read(1024)
            while data:
                avaproxy.send(data)
                data = f.read(1024)
    res = avaproxy.recv(1024)
    BuiltIn().log('Sent the config file `%s`' % config_name)

    res = Common.send(avaproxy,'ava::load_config/config.spf')
    BuiltIn().log('Loaded the SPF config, test handle is `%s`' % res)

    # reserve ports
    port_data = []
    if 'real-port' in Common.LOCAL['tester'][self._cur_name]:
        res = Common.send(avaproxy,'ava::release_all_ports')

        port_data = Common.LOCAL['tester'][self._cur_name]['real-port']
        interface = 0
        for item in port_data:
            res = Common.send(avaproxy,'ava::reserve_port/%d/%s/%s/%s' % (interface,item['chassis'],item['card'],item['port']))
            if res != 'ava::ok' :
                msg = "ERROR: could not reserve necessary ports\n%s" % res
                BuiltIn().log(msg)
                raise Exception(msg)
            interface += 1
            BuiltIn().log('    reserved port %s/%s/%s with result %s' % (item['chassis'],item['card'],item['port'],res))
    else:
        res = Common.send(avaproxy,'ava::reserve_all_ports')
        BuiltIn().log('    reserved all ports')

    BuiltIn().log('Reserved %d ports' % len(port_data))
    return res


def start_test(self,trial='0',timeout='5m'):
    """ Starts the test and wait until it finishes or timeout
    """
    cli  = self._clients[self._cur_name]
    avaproxy = cli['connection']
    res = Common.send(avaproxy,'ava::start_test/%s' % trial)
    BuiltIn().log('Started the test with trial mode is `%s`' % trial)

    res = Common.send(avaproxy,'ava::wait_until_finish/%d' % DateTime.convert_time(timeout))
    if res != 'ava::ok' :
        raise Exception('Error happened before the test finishes\n%s' % res)
    BuiltIn().log('Finished the test with result: %s' % res)
    return res


def get_test_result(self,name='ava'):
    """ Get test result folder

    The resuls will be saved under `current result` folder with the name `name`
    """
    cli  = self._clients[self._cur_name]
    avaproxy = cli['connection']

    res = Common.send(avaproxy,'ava::get_test_result');
    prefix = '%s/%s' % (Common.get_result_path(),name)
    # delele olf folder
    if name != '' and os.path.exists(prefix):
        shutil.rmtree(prefix)

    while res != 'ava::ok':
        if res.startswith('ava::dir'):
            m = re.match(r'ava::dir/(.+)', res)
            dir_path = '%s/%s' % (prefix,m.group(1))
            if not os.path.exists(dir_path):
                BuiltIn().log('    create folder %s' % dir_path)
                os.makedirs(dir_path)
            Common.send(avaproxy,'ava::ok',0)

        if res.startswith('ava::file'):
            m = re.match(r'ava::file/(.+?)/(.+)', res)
            file_size = int(m.group(1))
            file_path = '%s/%s' % (prefix,m.group(2))
            BuiltIn().log('    create file `%s`' % file_path)
            current_size = 0
            Common.send(avaproxy,'ava::ok',0)
            f = open(file_path,'wb')
            while current_size < file_size:
                data = avaproxy.recv(1024)
                if not data: break
                if len(data) + current_size > file_size:
                    data = data[:file_size - current_size]
                current_size += len(data)
                f.write(data)
            f.close()
            BuiltIn().log('    created file `%s` with size %d' % (file_path,current_size))
            Common.send(avaproxy,'ava::ok',0)
        if (sys.version_info > (3, 0)):
            res = avaproxy.recv(1024).decode('utf-8')
        else:
            res = avaproxy.recv(1024)

    BuiltIn().log('Got test result')

