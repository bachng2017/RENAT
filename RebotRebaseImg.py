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

# $Rev: 2168 $
# $Ver: $
# $Date: 2019-08-17 17:34:00 +0900 (土, 17  8月 2019) $
# $Author: $

import re
from robot.api import SuiteVisitor
from robot.result.model import TestSuite
from robot.result.model import TestCase
class RebotRebaseImg(SuiteVisitor):
    """ Rebases embeded img in output with new `base`

    Rebased folder is extract from `Log Folder` meta of the suite
    Sample
    $ rebot  --prerebotmodifier ./RebotRebaseImg.py -N xxx -L info -d result result_001/output.xml
    """
    def __init__(self):
        self.base = None
 
    def start_suite(self,suite):
        if 'Log Folder' in suite.metadata:
            log_folder=suite.metadata['Log Folder']
            self.base = log_folder.replace('[','').replace(']','').split('|')[0] 

    def end_message(self,msg):
        if msg.html and re.match(r'.*<img src=.*>.*',msg.message): 
            new_msg = re.sub(r'="([^"]*?.png)"','="%s/\\1"' % self.base, msg.message)
            # print(msg)
            # print(new_msg)
            # print("%s:%s" % (type(msg.parent.parent.parent),msg.parent.parent.parent.name))
            # print(new_msg)
            msg.message = new_msg
