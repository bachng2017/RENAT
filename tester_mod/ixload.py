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

""" provides functions for IxLoad

RENAT runs a virtual IxLoad client locally in the background that connects to a
Windows App server. Keywords from test case will send control messages to the
client, which in turn will control the test ports. 

Test resuls remain on the remote App server.

Different to IxNetwork, an IxLoad test case usually stops within predefined time
before ``Stop Traffic`` was called.

*Notes:* Ignore the _self_ parameters when using those keywords.
"""

from robot.libraries.BuiltIn import BuiltIn



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
    
    Returns the time in second that the test has really ran.
    """
    cli = self._clients[self._cur_name]
    tasks   = cli['tasks']
    results = cli['results']

    tasks.put(["ixload::stop_traffic"])
    tasks.join()
    result = _check_result(results,'ixload::stop_traffic')
    BuiltIn().log("Stopped the current test traffic")
    return result[1]
    

def load_traffic(self,file_path):
    """ Loads the test traffic defined by ``file_path``

    ``file_path`` is the path of the test file on the *remote* App server
    Result will be saved in remote machine under the folder
    ``D://RENAT/RESULS/<this case>``
    """

    cli = self._clients[self._cur_name]
    tasks   = cli['tasks']
    results = cli['results']
    
    tasks.put(["ixload::load_traffic",file_path])
    tasks.join()
    _check_result(results,'ixload::load_traffic')
    BuiltIn().log("Loaded repository file `%s` on remote machine" % file_path)
