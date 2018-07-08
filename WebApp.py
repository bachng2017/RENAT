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

# $Date: 2018-07-02 21:30:24 +0900 (Mon, 02 Jul 2018) $
# $Rev: 1067 $
# $Ver: $
# $Author: $

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

    The `WebApp` uses the configuration in ``local.yaml`` in ``webapp`` section.
    The webapp device has following format:
| <test node name>:
|     device:     <device name>
|     proxy:
|         http:       <proxy for http>    
|         https:      <proxy for http>    
|         ssl:        <proxy for http>    
    Where ``<device name>`` is defined in master ``device.yaml``, ``proxy``
    section could be optional.

    Samples:
| ...
| webapp:
|     samurai-1:
|         device: samurai-b
|         proxy:
|             http:   10.128.8.210:8080
|             ssl:    10.128.8.210:8080
|             socks:  10.128.8.210:8080
|     arbor-1:
|         device: arbor-sp-a
|         proxy:
|             http:   10.128.8.210:8080
|             ssl:    10.128.8.210:8080
|             socks:  10.128.8.210:8080
| ...

    `Selenium2Library` keywords still could be used along with this library like
    this:
    | Click Link |                         //a[contains(.,'ユーザ設定')] |
    | Sleep      |                         2s |
    | Click Link |                        Home設定 |
    | Sleep |                             2s |
    | Samurai.Capture Screenshot |

    See [http://robotframework.org/Selenium2Library/Selenium2Library.html|Selenium2Library] for more details.


    The module `Samurai` and `Arbor` based on this module.
    See [./Arbor.html|Arbor], [./Samurai.html|Samurai] for details about keywords of each application.
    """

    ROBOT_LIBRARY_SCOPE = 'TEST SUITE'
    ROBOT_LIBRARY_VERSION = Common.version()


    def __init__(self):
        self._browsers              = {}
        self._current_name          = None
        self._current_app           = None
        self._type                  = None
        self._ajax_wait             = 2
        try:
            self._driver = BuiltIn().get_library_instance('Selenium2Library')

        except RobotNotRunningError as e:
            Common.err("WARN: RENAT is not running")

    
    def set_ajax_wait(self,wait_time='2s'):
        """ Set the ajax wait time
        """
        old_value = self._ajax_wait
        self._ajax_wait = DateTime.convert_time(wait_time)
        BuiltIn().log("Set the ajax wait_time to `%d` seconds")
        return old_value


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
        | Samurai.`Capture Screenshot`  |   filename=1111.png | # 1111.png |
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

   
