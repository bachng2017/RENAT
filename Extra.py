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

# $Date: 2018-08-28 10:52:25 +0900 (Tue, 28 Aug 2018) $
# $Rev: 1250 $
# $Ver: $
# $Author: $

import os
import traceback
import Common
from robot.libraries.BuiltIn import BuiltIn

class Extra():
    """ Handles extra work
    """
    ROBOT_LIBRARY_SCOPE = 'GLOBAL'
    
    def __init__(self):
        try:
            # load extra libraries
            if Common.GLOBAL['extra-lib']:
                for lib in Common.GLOBAL['extra-lib']:
                    lib_name = lib + '.py'
                    BuiltIn().import_library(os.environ['RENAT_PATH'] + '/'+ lib_name)
                    BuiltIn().log_to_console("Loaded extra library `%s`" % lib)
        
        except Exception as e:
            Common.err("ERROR: error while loading extra libraries")
            Common.err(e)

    def connect_all(self):
        if Common.GLOBAL['extra-lib']:
            for lib in Common.GLOBAL['extra-lib']:
                BuiltIn().run_keyword(lib+'.Connect All')
    
    def close_all(self):
        if Common.GLOBAL['extra-lib']:
            for lib in Common.GLOBAL['extra-lib']:
                BuiltIn().run_keyword(lib+'.Close All')
    
