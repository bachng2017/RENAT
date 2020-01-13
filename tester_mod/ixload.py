# -*- coding: utf-8 -*-
#  Copyright 2017-2019 NTT Communications
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

# $Date: 2018-07-03 22:39:21 +0900 (火, 03  7月 2018) $
# $Rev: 1074 $
# $Ver: $
# $Author: $

""" provides functions for IxLoad

To use IxLoad module, a IxLoad TCL server should be started properly.

RENAT runs a virtual IxLoad client locally in the background that connects to a
Windows App server. Keywords from test case will send control messages to the
client, which in turn will control the test ports.

Different to IxNetwork, an IxLoad test case usually stops within predefined time
before ``Stop Traffic`` was called.

*Notes:* Ignore the _self_ parameters when using those keywords.
"""

from robot.libraries.BuiltIn import BuiltIn
import Common


def _check_result(results,keyword,extra="unknown"):
    result = results.get()
    if result[0] != "ixload::ok":
        raise Exception("RENAT error in `%s` keyword: %s" % (keyword,result))
    return result


def close(self):
    """ Disconnects the current tester client
    """
    cli = self._clients[self._cur_name]
    tasks   = cli['tasks']
    results = cli['results']

    tasks.put(["ixload::disconnect"])
    tasks.join()
    _check_result(results,'ixload::close')
    BuiltIn().log("Closed the connection and finished IxLoad subprocess")


def start_traffic(self):
    """ Starts the test traffic
    """
    cli = self._clients[self._cur_name]
    tasks   = cli['tasks']
    results = cli['results']

    tasks.put(["ixload::start_traffic"])
    # tasks.join()
    _check_result(results,'ixload::start_traffic')
    BuiltIn().log("Started the test traffic")


def stop_traffic(self):
    """ Stops the current running test

    Returns the  elapsed time in seconds
    """
    cli = self._clients[self._cur_name]
    tasks   = cli['tasks']
    results = cli['results']

    tasks.put(["ixload::stop_traffic"])
    tasks.join()
    msg = _check_result(results,'ixload::stop_traffic')
    BuiltIn().log("Stopped the current test traffic, elasped time is %s" % msg[1])
    return msg[1]


def load_traffic(self,file_path):
    BuiltIn().log_to_console('WARNING: `Load Traffic` is deprecated. Using `Load Config` instead')
    self.load_config(file_path)


def load_config(self,config_name=""):
    """ Loads the test traffic defined by ``config_name``

    ``file_path`` is the path of the test file on the *remote* App server
    A path to a remote network drive could be use to load a config file on Renat
    server.
    """

    cli = self._clients[self._cur_name]
    tasks   = cli['tasks']
    results = cli['results']

    # prepare port data
    if 'real-port' in Common.LOCAL['tester'][self._cur_name]:
        port_data = Common.LOCAL['tester'][self._cur_name]['real-port']
    set_port = []
    for item in port_data:
        set_port.append("%s;%s;%s" % (item['chassis'],item['card'],item['port']))

    # prepare config file
    if config_name == '':
        config_name = Common.LOCAL['tester'][self._cur_name]['config']

    tasks.put(["ixload::load_config",config_name,set_port])
    tasks.join()
    msg = _check_result(results,'ixload::load_config')
    BuiltIn().log("Loaded config file `%s`, set result folder to `%s` and reassigned %d ports" % (config_name,msg[1],len(set_port)))



def collect_data(self,prefix='',more_file='',ignore_not_found=True):
    """ Collects all result data and save them to the current active ``result``
    folder

    A ``prefix`` will be automatically added to the file names.

    Currently the follow data will be downloaded to the local machine
        - HTTP_Server.csv
        - HTTP Client.csv
        - HTTP Client - Per URL.csv
        - HTTP Server - Per URL.csv
        - L2-3 Stats for Client Ports.csv
        - L2-3 Stats for Server Ports.csv
        - L2-3 Throughput Stats.csv
        - Port CPU Statistics.csv

    Extra files could be add by ``more_file`` which is a comma separated
    filename string

    When ``ignore_not_found`` is True, the keyword will not terminate even when
    the expected file is not found.
    """

    cli = self._clients[self._cur_name]
    tasks   = cli['tasks']
    results = cli['results']

    tasks.put(["ixload::collect_data",prefix,more_file,ignore_not_found])
    tasks.join()
    _check_result(results,'ixload::collect_data')
    BuiltIn().log("Copied result data to local result folder")


def get_test_report(self,prefix=''):
    """ Get the test report(PDF) and put it into the active result folder
    """
    cli = self._clients[self._cur_name]
    tasks   = cli['tasks']
    results = cli['results']

    tasks.put(["ixload::get_test_report",prefix])
    tasks.join()
    _check_result(results,'ixload::get_test_report')
    BuiltIn().log("Copied report files to local result folder")

