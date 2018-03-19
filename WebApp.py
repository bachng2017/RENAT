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

# $Date: 2018-03-20 02:58:07 +0900 (Tue, 20 Mar 2018) $
# $Rev: 822 $
# $Ver: 0.1.7 $
# $Author: bachng $

import os,time,re
import Common
from robot.libraries.BuiltIn import BuiltIn
from robot.libraries.BuiltIn import RobotNotRunningError
from Selenium2Library import Selenium2Library


class WebApp(object):
    """ A library provides common keywords for web applications (aka Samurai,
    Arbor TMS)

    The library utilize `Selenium2Library` and adds more functions to control
    Samurai application easily.

    The `WebApp` uses the configuration in ``local.yaml`` in ``webapp`` section:
| ...
| webapp:
|     samurai-1:
|         device: samurai-b
|         profile: samurai.profile
|     arbor-1:
|         device: arbor-sp-a
|         profile: samurai.profile
| ...

    `Selenium2Library` keywords still could be used along with this library.
    See [http://robotframework.org/Selenium2Library/Selenium2Library.html|Selenium2Library] for more details.

    See [./Arbor.html|Arbor], [./Samurai.html|Samurai] for details about keywords of each application.
    """

    ROBOT_LIBRARY_SCOPE = 'TEST SUITE'
    ROBOT_LIBRARY_VERSION = Common.version()


    def __init__(self):
        self._browsers              = {}
        self._current_name          = None
        self._type                  = None
        try:
            self._driver = BuiltIn().get_library_instance('Selenium2Library')

        except RobotNotRunningError as e:
            Common.err("RENAT is not running")


    def connect_all(self):
        """ Connects to all applications defined in ``local.yaml``
    
        The name of the connection will be the same of the `webapp` name
        """
    
        num = 0
        if 'webapp' in Common.LOCAL and Common.LOCAL['webapp']:
            for entry in Common.LOCAL['webapp']: 
                device = Common.LOCAL['webapp'][entry]['device']
                device_info = Common.GLOBAL['device'][device]
                type = device_info['type']  # type is `samurai` or `arbor_sp`

                if type != self._type: continue
                num += 1 
                self.connect(entry,entry)
            BuiltIn().log("Connected to %d applications" % num)
        else:
            BuiltIn().log("No application to connect")
    
    
    def set_capture_format(self,format):
        """ Sets the format for the screen capture file

        The format does not include the default prefix ``.png``
        The default format is ``<mod>_%010d``. ``mod`` could be ``samurai`` or
        ``arbor``

        See https://docs.python.org/2/library/string.html#format-specification-mini-language
        for more details about the format string.

        Examples:
        | Samurai.`Set Capture Format`  | ${case}_%010d |  # ${case} is a predefined variable | 
        
        """
        name = self._current_name
        self._browsers[name]['capture_format'] = format
        BuiltIn().log("Changed the screenshot capture format to `%s`" % format)

    def set_capture_counter(self,value = 0):
        """ Sets the counter of the screen capture to ``value``
        """    
        name = self._current_name
        self._browsers[name]['capture_counter'] = value
        BuiltIn().log("Changed the screenshot capture counter to `%d`" % value)

    def reset_capture_counter(self):
        """ Resets the counter of the screen capture
        """    
        self.set_capture_counter(0)

    def capture_screenshot(self,filename=None,extra=''):
        """ Captures the current screen to file

        Using the internal counter for filename if ``filename`` is not
        specified. In this case, the filename is defined by a pre-set format. `Set Capture
        Format` could be used to change the current format.

        An extra information will be add to the filename if ``extra`` is defined 

        Examples:
        | Samurai.`Capture Screenshot`  |               | # samurai_0000000001.png |
        | Samurai.`Capture Screenshot`  |   extra=_list | # samurai_0000000002_`list`.png |
        | Arbor.`Capture Screenshot`    |               | # arbor_0000000001.png |
        | Arbor.`Capture Screenshot`    |   extra=_xxx  | # arbor_0000000001_`xxx`.png |
        | Samurai.`Capture Screenshot`  |   file_name=1111.png | # 1111.png |
        """
        self.switch(self._current_name) 
        name = self._current_name
        if not filename:
            current_counter = self._browsers[name]['capture_counter']
            new_counter = current_counter + 1
            format = self._browsers[name]['capture_format'] + extra + '.png'
            capture_name = format % (new_counter)
            self._browsers[name]['capture_counter'] = new_counter
        else:
            capture_name = filename
        self._driver.capture_page_screenshot(capture_name)
        BuiltIn().log("Captured the current screenshot to file `%s`" % capture_name) 

    
