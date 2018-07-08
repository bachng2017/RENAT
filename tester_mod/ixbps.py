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

# $Date: 2018-06-29 13:43:17 +0900 (Fri, 29 Jun 2018) $
# $Rev: 1054 $
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
from robot.libraries.BuiltIn import BuiltIn
import Common
import robot.libraries.DateTime as DateTime

def close(self):
    """ Closes the connection to the BP box
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection'] 
    try:
        self.stop_test()
        BuiltIn().log("Stopped running test and released reserved ports") 
    except:
        BuiltIn().log("Have no reserved ports or running tests") 
    ix.logout()
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

    result = ix.upload_config(filename=config_path,force=force)
    BuiltIn().log("Loaded configuration file `%s`" % config_name)
    return result



def start_test(self,test_name,force=True):
    """ Starts a test by its name
    
    The system automatically reserve the ports defined in ``local.yaml``. The
    reserved ports are released when the test is stopped
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection'] 
    ports = []
    if 'real-port' in Common.LOCAL['tester'][self._cur_name]:
        ports = Common.LOCAL['tester'][self._cur_name]['real-port']
        for item in ports: 
            ix.reserve_ports(slot=item['card'],portlist=[item['port']],force=force)
    
        self._test_id = ix.run_test(testname=test_name)
        BuiltIn().log("Started the Breaking Point test `%s` with %d ports" % (test_name,len(ports)))
    else:
        self._test_id = None
        BuiltIn().log("No eserved ports. Check your local.yaml")
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
        while progress < 100 and count < wait_time:
            progress = ix.get_test_progress(testid=self._test_id)
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
    ix.stop_test(testid=self._test_id)
    time.sleep(DateTime.convert_time(wait))
    if 'real-port' in Common.LOCAL['tester'][self._cur_name]:
        ports = Common.LOCAL['tester'][self._cur_name]['real-port']
        for item in ports: 
            ix.unreserve_ports(slot=item['card'],portlist=[item['port']])
    BuiltIn().log("Stopped `%s` test" % self._test_id) 
   

def get_test_report(self,report_name='result'):
    """ Gets and saves the test report to local disk
    """
    cli = self._clients[self._cur_name]
    ix  = cli['connection'] 
    result_path = Common.get_result_path() 
    ix.download_report(testid=self._test_id,reportname=report_name+'.pdf',location=result_path)
    ix.BPSProxy.exportTestsCsv(csvName=report_name,location=result_path)
    BuiltIn().log("Got test reports in PDF and CSV `%s`" % report_name)

