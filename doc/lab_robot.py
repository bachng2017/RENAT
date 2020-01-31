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

""" A collection of user keywords that is commonly used by the lab.

== Common variables ==
Predefined variables:
- `${WORKING_FOLDER}`: is the `working` folder for each user on file server

"""
import Common
ROBOT_LIBRARY_VERSION = Common.version()

def collect_log_from_file_server():
    """  Moves all csv files defined in `${MY_ID}_CSVList.txt` to the current
    result folder.

    The `${MY_ID}` is a hashed specific for each test item.
    """
    pass

def snmp_polling_start_for_host(host,filename_prefix='snmp_'):
    """ Starts a predefined polling script for a ``host``

    The MIB file used for the polling process is defined in the local yaml
    config for each node.  The results file is appended by prefix
    ``filename_prefix``.
    """
    pass

def snmp_polling_start(termname='apollo',filename_prefix='_snmp'):
    """ Start the SNMP polling for all hosts that have ``snmp-polling`` tag

    ``tername`` is the host that the polling process is run (default is
    `apollo`).  The results file is appended by prefix ``filename_prefix``.
    """
    pass

def snmp_polling_stop(termname='apollo'):
    """ Stops the process started by `SNMP Polling Start` on ``termname``
    """
    pass

def follow_remote_log_start(termname):
    """ Starts monitoring the syslog for nodes that has ``follow-remote-log``
    flag from ``termname``
    """
    pass

def follow_remote_log_stop(termname):
    """ Stops the monitoring process started by `Follow Remote Log Start` on
    ``termname``
    """
    pass

def lab_setup():
    """ Setup common procedures for a test. This will be called for each test
    item.
    """
    pass

def lab_teardown():
    """ Clean up everything necessary after finishing a test.
    """
    pass
