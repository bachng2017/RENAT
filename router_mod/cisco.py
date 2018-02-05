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

# $Rev: 615 $
# $Date: 2018-01-20 16:44:55 +0900 (Sat, 20 Jan 2018) $
# $Author: $

####

""" Provides keywords for Cisco platform

"""

def get_version(self):
    """ return router version information
    """
    result = self._vchannel.cmd('show version')
    return result
