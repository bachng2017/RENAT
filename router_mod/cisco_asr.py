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

# $Rev: 1038 $
# $Ver: $
# $Date: 2018-06-18 16:57:51 +0900 (月, 18  6月 2018) $
# $Author: $

####
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

    output = self._vchannel.cmd('show inventory rack | inc "^  0"')
    line = output.split('\n')[0]    # first line
    tmp = line.split()
    if len(tmp) > 2:
        result = tmp[2]
    else:
        result = ''
    BuiltIn().log("Got the serial number: %s" % (result))
    return result

def get_route_number(self,proto='ipv4'):
    """ Returns route number

    Parameters:
    - proto: `ipv4`(default) or `ipv6`
    """
    result = ""
    output = self._vchannel.cmd("show route %s summary" % proto)
    for line in output.split("\n"):
        match = re.match(r"^Total  *(\d*) ",line)
        if match:
            result = int(match.group(1))

    BuiltIn().log("Got %d routes from `%s`" % (result,proto))

    return result

def number_of_ospf_neighbor(self,state="Full"):
    """ Returns number of OPSF neighbors with status ``state``
    """
    output  = self._vchannel.cmd("show ospf neighbor").lower()
    count   = output.count(state.lower())

    BuiltIn().log("Number of OSPF neighbors in `%s` state is %d" % (state,count))
    return count


def number_of_bgp_neighbor(self,state="Established"):
    """ Returns number of BGP neighbor in ``state`` state
    """
    output  = self._vchannel.cmd("show bgp neighbor").lower()
    count   = output.count("bgp state = " + state.lower())

    BuiltIn().log("Number of BGP neighbors in `%s` state is %d" % (state,count))
    return count

# def get_user(self):
#     """ Return the current login user
#     """
#     result = []
#     output = self._vchannel.cmd('show users')
#     count = 0
#     for line in output.split("\n"):
#         if count < 2:
#             count += 1
#             continue
#         m=re.match(r"(\*)*\s+(\S+)\s+(\S+)",line)
#         if m and m.group(3):
#             user = m.group(3)
#             if user not in result:
#                 result.append(user)
#         count += 1
# 
#     BuiltIn().log("Got the login user information")
#     return result

