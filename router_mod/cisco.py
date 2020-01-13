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

# $Rev: 1038 $
# $Ver: $
# $Date: 2018-06-18 16:57:51 +0900 (月, 18  6月 2018) $
# $Author: $

####
import re
from robot.libraries.BuiltIn import BuiltIn

""" Provides keywords for Cisco platform

"""

def get_version(self):
    """ return router version information
    """
    result = self._vchannel.cmd('show version')
    return result


def get_user(self):
    """ Return the current login user
    """
    result = []
    output = self._vchannel.cmd('show users')
    count = 0
    for line in output.split("\n"):
        if count < 2:
            count += 1
            continue
        m=re.match(r"(\*)*\s+(\S+)\s+(\S+)",line)
        if m and m.group(3):
            user = m.group(3)
            if user not in result:
                result.append(user)
        count += 1

    BuiltIn().log("Got the login user information")
    return result
