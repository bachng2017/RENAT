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

# $Date: 2018-09-15 11:15:16 +0900 (Sat, 15 Sep 2018) $
# $Rev: 1314 $
# $Ver: $
# $Author: $

""" provides functions for Ixia Breaking Point

Breaking Point testers setting is set by ``tester`` section in ``local.yaml``.
Users need to specify the physical ports used by the test by its card and port
number.

Setting example:
|    ixbps01:
|        device: ixbps01
|        config: test.bpt
|        real-port:
|            - card:   1
|              port:   0
|            - card:   1
|              port:   1

*Notes:* Ignore the _self_ parameters when using those keywords. The module
requires Breaking Point Python library installedd properly to work.
"""

import time
import requests,json,shutil
from robot.libraries.BuiltIn import BuiltIn
import Common
import robot.libraries.DateTime as DateTime
import xml.etree.ElementTree as xml_tree

def close(self):
    """ Closes the connection to the BP box
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection'] 
    result = ix.delete(self._base_url + '/auth/session',verify=False)
    if result.status_code != requests.codes.ok:
        BuiltIn().log(result)
        Exception('ERROR: could not logout') 
    BuiltIn().log("Closed the connection")


def load_config(self,config_name='',force=True):
    """ Loads test configuration
    config_name is defined in ``local.yaml`` or specific by user in the main
    scenario. 
    """
    BuiltIn().log("Load test configuration")
    cli = self._clients[self._cur_name]
    ix  = cli['connection'] 
    if config_name == '':
        config_name = Common.LOCAL['tester'][self._cur_name]['config']

    config_path = Common.get_item_config_path() + '/' + config_name

    service = self._base_url + '/bps/upload'
    files = {'file': (config_name,open(config_path,'rb'),'application/xml')}
    jdata = {'force':force}
    result = ix.post(service,files=files,data=jdata,verify=False)

    if result.status_code != requests.codes.ok:
        BuiltIn().log(result.text)
        raise Exception('ERROR: could not logout') 
    self._config_path = config_path
    BuiltIn().log("Loaded configuration file `%s`" % config_path)


def cleanup_tests(self):
    """ Cleans up running test and release their ports
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection'] 
    service = self._base_url + '/bps/tests/operations/getformattedrunningtestinfo'
    result = ix.post(service,verify=False)
    if result.status_code != requests.codes.ok:
        BuiltIn().log(result.text)
        raise Exception('ERROR: could not start the test') 
    jinfo = json.loads(json.loads(result.text)['result'])['info']
    for item in jinfo:
        test_id = item['testid']
        BuiltIn().log('    Found running test: `%s`' % test_id)
        service = self._base_url + '/bps/tests/operations/stop'
        payload = {'testid':test_id}
        result = ix.post(service,json=payload,verify=False)
        if result.status_code != requests.codes.ok:
            BuiltIn().log(result)
            BuiltIn().log(result.text)
            raise Exception('ERROR: could not stop a running test') 
        BuiltIn().log('    Stopped the test `%s`' % test_id) 
        ports = item['ports']

        time.sleep(10) 

        service = self._base_url + '/bps/ports/operations/unreserve'
        for term in ports:
            payload  = {'slot':term['slot'],'portList':[term['port']]}
            result = ix.post(service,json=payload,verify=False)
            if result.status_code != requests.codes.ok:
                BuiltIn().log(result)
                BuiltIn().log(result.text)
                raise Exception('ERROR: could not release a port') 
            BuiltIn().log('    Released port `%s:%s`' % (term['slot'],term['port']))


def start_test(self,test_name=None,force=True):
    """ Starts a test by its name
    
    The system automatically reserve the ports defined in ``local.yaml``. The
    reserved ports are released when the test is stopped

    ``test_name`` is the name of the testmodel saved in the configuration. If
    ``test_name`` is `None`, the 1st testmodel will be used.

    If ``force`` is `True` then all running tests and their reserved ports will
    be released.
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection'] 
    ports = []

    ### try to find the testmodel name
    if test_name:
        name = test_name
    else:
        root = xml_tree.parse(self._config_path)
        name = root.find(".//testmodel").get('name')

    if 'real-port' in Common.LOCAL['tester'][self._cur_name]:
        # check running test and stop it if necessary
        if force:
            BuiltIn().log('Cleans up all running tests')
            self.cleanup_tests()

        # reserve ports
        BuiltIn().log('Reserve necessary ports')
        ports = Common.LOCAL['tester'][self._cur_name]['real-port']
        service = self._base_url + '/bps/ports/operations/reserve'
        for item in ports: 
            payload     = {'slot':item['card'],'portList':[item['port']],'group':1,'force':force}
            result = ix.post(service,json=payload,verify=False)
            if result.status_code != requests.codes.ok:
                BuiltIn().log(result.text)
                raise Exception('ERROR: could not reserve ports `%s`' %json.dumps(payload)) 
            BuiltIn().log('    Reserved port `%s:%s`' % (item['card'],item['port']))

        # start the test 
        BuiltIn().log('Start the test')
        service = self._base_url + '/bps/tests/operations/start'
        data = {'modelname':name,'group':1}
        result = ix.post(service,json=data,verify=False)
        if result.status_code != requests.codes.ok:
            BuiltIn().log(result.text)
            raise Exception('ERROR: could not start the test') 

        self._test_id = result.json()['testid']
        BuiltIn().log("Started a BP test `%s(%s)` with %d ports" % (name,self._test_id,len(ports)))
    else:
        self._test_id = None
        BuiltIn().log("No reserved ports. Check your local.yaml")
    return self._test_id


def wait_until_finish(self,interval='30s',timeout=u'30m',verbose=False):
    """ Waits until the test finished or timeout

    *Notes*: This is a blocking keyword
    """
    step = DateTime.convert_time(interval)
    BuiltIn().log("Wait (max=%s) until the test finished" % timeout)
    if not self._test_id:
        BuiltIn().log("WARN: No running test")
    else:
        cli = self._clients[self._cur_name]
        ix  = cli['connection'] 
        count = 0
        wait_time = DateTime.convert_time(timeout)
        progress = 0
        service = self._base_url + '/bps/tests/operations/getrts'
        data = {'runid':self._test_id}
        while progress < 100.0 and count < wait_time:
            result = ix.post(service,json=data)
            if result.status_code != requests.codes.ok:
                BuiltIn().log(result.text)
                raise Exception('ERROR: could not get status of the test') 
            # BuiltIn().log(result.json())
            progress = int(result.json().get('progress'))
            time.sleep(step)
            count += step
            if verbose:
                BuiltIn().log("progress = %d%%" % progress)
                BuiltIn().log_to_console("progress = %d%%" % progress)
            else:
                BuiltIn().log_to_console('.','STDOUT',True)

    BuiltIn().log("The tested finished in %d second" % (count))


def stop_test(self,wait=u'5s'):
    """ Stops a running test
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection'] 
    if self._test_id:
        service = self._base_url + '/bps/tests/operations/stop'
        data = {'testid':self._test_id} 
        result = ix.post(service,json=data,verify=False)
        if result.status_code != requests.codes.ok:
            BuiltIn().log(result.text)
            raise Exception('ERROR: could not stop test `%s`' % self._test_id)
    else:
        BuiltIn().log('No runnning test')    
    time.sleep(DateTime.convert_time(wait))

    if 'real-port' in Common.LOCAL['tester'][self._cur_name]:
        ports = Common.LOCAL['tester'][self._cur_name]['real-port']
        service = self._base_url + '/bps/ports/operations/unreserve'
        for item in ports: 
            payload     = {'slot':item['card'],'portList':[item['port']]}
            result = ix.post(service,json=payload,verify=False)
            if result.status_code != requests.codes.ok:
                BuiltIn().log(result.text)
                raise Exception('ERROR: could not release ports `%s`' %json.dumps(payload)) 
            BuiltIn().log('    Unreserved port `%s:%s`' % (item['card'],item['port']))

    BuiltIn().log("Stopped `%s` test and released ports" % self._test_id) 
   

def get_test_report(self,report_name='result',format='csv'):
    """ Gets and saves the test report to local disk
    
    The report will be in PDF format. If ``export_csv`` is ``True`` then test
    results are also exported by CSV format.
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection'] 
    result_path = Common.get_result_path()
    report_path = result_path + '/' + report_name + '.' + format 
    service = self._base_url + '/bps/export/report/%s/%s'

    result = ix.get(service % (self._test_id,format),verify=False,stream=True)
    if result.status_code != requests.codes.ok:
        BuiltIn().log(result.text)
        raise Exception('ERROR: could not get test report')
    else:
        with open(report_path,'wb') as file:
            result.raw.decode_content = True
            shutil.copyfileobj(result.raw,file)
    
    BuiltIn().log("Got test reports by name `%s` with format `%s`" % (report_name,format))

