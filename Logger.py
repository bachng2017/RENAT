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

import datetime
import Common
from robot.libraries.BuiltIn import BuiltIn
from robot.libraries.BuiltIn import RobotNotRunningError

class Logger(object):
    """ Provides advanced logging functions. Every [./Logger.html|Logger] instance has one
    [./VChannel.html|VChannel] object and the is synchronized with the current active
    [./VChannel.html|VChannel].

    
    """

    ROBOT_LIBRARY_SCOPE = 'TEST SUITE'
    ROBOT_LIBRARY_VERSION = Common.version()

    _vchannel = None
   
    ### 
    def __init__(self):
        try:
            self._vchannel = BuiltIn().get_library_instance('VChannel')
            if self._vchannel is None:
                raise Exception("Could not find an instance of VChannel. Need import VChannel first")
        except RobotNotRunningError as e:
            Common.err("RENAT is not running")


    def switch(self,name):
        """ Switches the current [./VChannel.html|VChannel] instance to ``name``.
        ``name`` is the name of the [./VChannel.html|VChannel] (usually is the
        node name defined in the current active ``local.yaml``).

        Example:
        | Logger.`Switch` | vmx11 |
        """
        self._vchannel.switch(name) 


    def _log(self,channel,msg,with_time,mark):
        note = ""
        if with_time :
            note = datetime.datetime.now().strftime("%I:%M%p on %B %d, %Y: ") + msg
        else :
            note = msg
        note = mark + ' ' + note + ' ' + mark
        channel['logger'].write(Common.newline + Common.newline + note + Common.newline + Common.newline)
        channel['logger'].flush()
  

    def log(self,msg,with_time=False,mark="***"):
        """ Inserts a message ``msg`` to the current `VChannel` log file. 
        A default mark of ``***`` will be added at the beginning ant the end of 
        this message.

        Example:
        |  Logger.`Log` | START TRAFFIC FROM HERE  |   ${TRUE} |
        |  Logger.`Log` | START TRAFFIC FROM HERE  |   ${False} | ===== |

        """
        channel = self._vchannel.get_current_channel()
        self._log(channel,msg,with_time,mark)

    
    def log_all(self,msg,with_time=False,mark="***"):
        """ inserts a message ``msg`` to current *all* [./VChannel.html|VChannel] log files. 

        A default ``mark`` of ``***`` and newline will be added at the beggining and the end of this
        message.

        Example:
        |  Logger.`Log All` | START TRAFFIC FROM HERE  |   ${TRUE} |
        |  Logger.`Log All` | START TRAFFIC FROM HERE  |   ${TRUE} | ===== |

        The log file will look likes this:
| ipc0re@vmx12> 
|
| ***** 06:01PM on August 13, 2017: START TRAFFIC FROM HERE *****
|
| === 06:01PM on August 13, 2017: START TRAFFIC FROM HERE ===
|
| configure
        
        """
        clients = self._vchannel.get_channels()
        for name in clients:
            self._log(clients[name],msg,with_time,mark)
        BuiltIn().log("Wrote msg to `%d` clients" % (len(clients)))


