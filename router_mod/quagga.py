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


""" Provides keywords for Juniper platform

*Notes:* Ignore the _self_ parameters when using those keywords.
"""

import Common
from robot.libraries.BuiltIn import BuiltIn

def number_of_bgp_neighbor(self,state="Established",cmd='show bgp summary'):
    """ Returns number of BGP neighbor in ``state`` state
    """
    output  = self._vchannel.cmd(cmd).lower()
    count   = output.count(state.lower())

    BuiltIn().log_to_console(output)
    BuiltIn().log("Number of BGP neighbors in `%s` state is %d" % (state,count))
    return count


