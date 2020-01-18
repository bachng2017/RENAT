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


####
""" Provides keywords for Hitachi GR platform
"""

import re
from robot.libraries.BuiltIn import BuiltIn

def get_version(self):
    """ return router version information
    """
    result = self._vchannel.cmd('show version')
    return result

def get_chassis_serial(self):
    """ Returns the serial number of the chassis
    """

    output = self._vchannel.cmd("show version | grep Model")
    line = output.split('\n')[0]    # first line
    m = re.match(r".*\[.*, (.*)\]",line)
    if m:   result = m.group(1)
    else:   result = ''
    BuiltIn().log("Got the serial number: %s" % (result))
    return result
