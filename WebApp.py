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

# $Date: 2019-03-26 07:28:16 +0900 (火, 26  3月 2019) $
# $Rev: 1924 $
# $Ver: $
# $Author: $

import os,time,re,traceback,shutil
from decorator import decorate
import Common
from robot.libraries.BuiltIn import BuiltIn
from robot.libraries.BuiltIn import RobotNotRunningError
from SeleniumLibrary import SeleniumLibrary
from SeleniumLibrary.errors import ElementNotFound
from selenium.common.exceptions import WebDriverException
import robot.libraries.DateTime as DateTime
from selenium import webdriver
from selenium.webdriver.common.proxy import Proxy, ProxyType


### module methods
def _with_reconnect(keyword, self, *args, **kwargs):
    count = 0
    max_count = int(Common.GLOBAL['default']['max-retry-for-connect'])
    while count <= max_count:
        try:
            return keyword(self,*args,**kwargs)
        except (AssertionError,ElementNotFound) as err:
            BuiltIn().log(err)
    
            logout_count = self._driver.get_matching_xpath_count("//h1[.='Timeout']")
            if logout_count == 0: # this is not time out
                raise

            count += 1
            if count < max_count:
                BuiltIn().log('WARN: Failed to execute the keyword `%s` %d time(s)'  % (keyword.__name__,count))
                safe_reconnect(self)
            else:
                BuiltIn().log('ERROR: Gave up retry for keyword `%s`' % keyword.__name__)
                BuiltIn().log(type(err))
                BuiltIn().log(traceback.format_exc())
                self.capture_screenshot(extra="_err") # save the last available screen
                raise
        except Exception as err:
            self.capture_screenshot(extra="_err") # save the last available screen
            raise 

def safe_reconnect(self):
    try:
        self.reconnect()
    except:
        self.capture_screenshot(extra="last") # save the last available screen
        raise 
        
def with_reconnect(f):
    return decorate(f, _with_reconnect)


###
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

    In order to download files from link, a `dowload-path` and MIME of that
    download need to be listed in `profile` section of the application setting.
    Default `download-path` is the current active result folder.

    Examples:
| ...
| webapp:
|     samurai-1:
|         device: samurai-b
          profile:
            auto-save-mime: application/octet-stream
|         proxy:
|             http:   10.128.8.210:8080
|             ssl:    10.128.8.210:8080
|     arbor-1:
|         device: arbor-sp-a
          profile:
            auto-save-mime: application/xml,application/octet-stream
|         proxy:
|             http:   10.128.8.210:8080
|             ssl:    10.128.8.210:8080
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
        self._verbose               = False
        self._ajax_wait             = 2
        self._driver                = None
        try:
            self._driver = BuiltIn().get_library_instance('SeleniumLibrary')
        except RobotNotRunningError as e:
            Common.err("WARN: RENAT is not running")

    
    def set_verbose(self,verbose=False):
        """ Set current verbose mode to ``verbose``
        """
        self._verbose = verbose
        BuiltIn().log('Set verbose mode to `%s`' % self._verbose)


    def get_verbose(self):
        """ Get current verbose mode
        """
        BuiltIn().log('Got verbose mode: %s' % self._verbose)
        return self._verbose

    
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


    def capture_screenshot(self,filename=None,extra=u''):
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
        # self.switch(self._current_name) 
        name = self._current_name
        if not filename:
            current_counter = self._browsers[name]['capture_counter']
            new_counter = current_counter + 1
            format = self._browsers[name]['capture_format'] + str(extra) + '.png'
            capture_name = format % (new_counter)
            self._browsers[name]['capture_counter'] = new_counter
        else:
            capture_name = filename
        total_width     = int(self._driver.execute_javascript("return document.body.offsetWidth;"))
        total_height    = int(self._driver.execute_javascript("return document.body.parentNode.scrollHeight;"))

        display_info = Common.get_config_value('display')

        if total_width < int(display_info['width']):
           total_width = int(display_info['width'])
        if total_height < int(display_info['height']):
           total_height = int(display_info['height'])
        # store old  window size
        (old_width, old_height) = self._driver.get_window_size()

        # only update windows height
        self._driver.set_window_size(old_width, total_height)
        time.sleep(2)
        self._driver.capture_page_screenshot(capture_name)  
        # restore old window size
        self._driver.set_window_size(old_width, old_height)
        # self._driver.maximize_browser_window()
        time.sleep(2)
        BuiltIn().log("Captured the current screenshot(%dx%d) to file `%s`" % (total_width,total_height,capture_name))


    def verbose_capture(self,*args,**kwargs):
        """ Capture screenshot if verbose mode is ``True`` otherwise do nothing
        """
        if self._verbose:
            self.capture_screenshot(*args,**kwargs)
        BuiltIn().log('Captured screenshot with verbode mode `%s`' % self._verbose)


    def close(self):
        """ Close the web application
        """
        fp = self._browsers[self._current_name]['ff_profile_dir']
        ignore_dead_node = Common.get_config_value('ignore-dead-node')
        try: 
            old_name = self._current_name
            self._driver.close_browser()
            del(self._browsers[old_name])
            if len(self._browsers) > 0:
                self._current_name = list(self._browsers.keys())[-1]
            else:
                self._current_name = None
            shutil.rmtree(fp,ignore_errors=True)
            BuiltIn().log("Closed the browser '%s', current acttive browser is `%s`" % (old_name,self._current_name))
            return old_name
        except Exception as err:
            if not ignore_dead_node:
                err_msg = "ERROR: Error occured when connecting to `%s`" % (old_name)
                BuiltIn().log(err_msg)
                raise
            else:
                warn_msg = "WARN: Error occured when connect to `%s` but was ignored" % (old_name)
                BuiltIn().log_to_console(warn_msg)
                BuiltIn().log(warn_msg)
                BuiltIn().log(err) 


    def open_ff_with_profile(self,app,name):
        """
        """
        if name in self._browsers:
            BuiltIn().log("Browser `%s` already existed" % name)
            return
        browser         = 'firefox'
        login_url       = '/'
        proxy           = None
        fp              = None
        capabilities    = None

        ignore_dead_node = Common.get_config_value('ignore-dead-node')

        # collect information about the application that listed 
        app_info = Common.LOCAL['webapp'][app]
        if 'login-url' in app_info and app_info['login-url']:
            login_url = app_info['login-url']
        if 'browser' in app_info and app_info['browser']:
            browser  = app_info['browser']
        if 'proxy' in app_info and app_info['proxy']:
            proxy = Proxy()
            proxy.proxy_type = ProxyType.MANUAL
            if 'http' in app_info['proxy']:
                proxy.http_proxy    = app_info['proxy']['http']
            if 'ssl' in app_info['proxy']:
                proxy.ssl_proxy     = app_info['proxy']['ssl']
            if 'ftp' in app_info['proxy']:
                proxy.ftp_proxy     = app_info['proxy']['ftp']
            capabilities = webdriver.DesiredCapabilities.FIREFOX
            proxy.add_to_capabilities(capabilities)

        device = app_info['device']
        device_info = Common.GLOBAL['device'][device]
        ip = device_info['ip']
        type = device_info['type']
        template = Common.GLOBAL['access-template'][type]
        profile = template['profile'] 
        auth = {}
        BuiltIn().log('    Using profile `%s`' % profile)
        auth['username']    = Common.GLOBAL['auth']['plain-text'][profile]['user']
        auth['password']    = Common.GLOBAL['auth']['plain-text'][profile]['pass']
        url = 'https://' + ip + '/' + login_url

        # create a new profile and adjust it
        fp = webdriver.FirefoxProfile()
        if 'profile' in app_info and 'download-dir' in app_info['profile']:
            download_path = app_info['profile']['download-path']
        else:
            download_path = Common.get_result_path()
        if 'profile' in app_info and 'auto-save-mime' in app_info['profile']:
            auto_save_mime = app_info['profile']['auto-save-mime']
            fp.set_preference("browser.helperApps.neverAsk.saveToDisk", app_info['profile']['auto-save-mime'])
        fp.set_preference("browser.download.folderList",2)
        fp.set_preference("browser.download.dir",download_path)
        fp.set_preference("browser.download.manager.showWhenStarting",False);
        fp.set_preference("browser.download.useDownloadDir",True);
        fp.set_preference("browser.download.panel.shown",False);
        fp.set_preference("gfx.canvas.azure.backends","cairo");
        fp.set_preference("gfx.content.azure.backends","cairo");
        fp.update_preferences()

        # open a browser and retry 3 times if it is necessary
        try:
            retry = 0
            while retry <= 3:
                try:
                    url = 'https://' + ip + '/' + login_url
                    self._driver.open_browser(url,browser,'_%s_%s' % (profile,name),False,capabilities,fp.path)
                    time.sleep(5)
                    break
                except WebDriverException as err:
                    BuiltIn().log(err)
                    BuiltIn().log('Will retry one more time for browser session')
                    retry += 1
                    if retry == 3: raise
                # finally:
                    # shutil.rmtree(fp.path,ignore_errors=True)
        except Exception as err:
            if not ignore_dead_node:
                err_msg = "ERROR: Error occured when connecting to `%s`" % (name) 
                BuiltIn().log(err_msg)
                raise
            else:
                warn_msg = "WARN: Error occured when connect to `%s` but was ignored" % (name) 
                BuiltIn().log(warn_msg)
                BuiltIn().log_to_console(warn_msg)

        self._current_name = name
        browser_info = {}
        browser_info['url'] = url
        browser_info['auth'] = auth
        browser_info['capabilities'] = capabilities
        browser_info['ff_profile_dir'] = fp.path
        browser_info['capture_counter'] = 0
        browser_info['capture_format']  = "%s_%%010d" % app
        browser_info['browser']         = browser
        browser_info['profile']         = profile
        self._browsers[name] = browser_info

        BuiltIn().log("Opened browser(%s) for %s app with profile `%s`" % (browser,app,fp.path))


    def switch(self,name):
        """ Switches the current browser to ``name``
        """
        self._driver.switch_browser('_%s_%s' % (self._browsers[self._current_name]['profile'],name))
        self._current_name = name
        BuiltIn().log("Switched the current browser to `%s`" % name)


    def close_all(self):
        """ Closes all current opened applications
        """
        while len(self._browsers) > 0:
            self.close()
        BuiltIn().log("Closed all the browsers for %s" % self.__class__.__name__)


    def mark_element(self,xpath):
        """ Marking an element to check its stattus later
        """
        element = self._driver.get_webelement(xpath)
        name = self._current_name
        self._browsers[name]['mark_element_id'] = element.id
        self._browsers[name]['mark_element_xpath'] = xpath
        BuiltIn().log('Marked element with id `%s`' % element.id)


    def wait_until_element_changes(self,interval='5s',timeout='180s',error_on_timeout=False):
        """ Wait until the marked element has been changed
        """
        timeout_sec = DateTime.convert_time(timeout)
        name = self._current_name
        count = 0
        id      = self._browsers[name]['mark_element_id']
        xpath   = self._browsers[name]['mark_element_xpath']
        element = self._driver.get_webelement(xpath)
        element_id = element.id
        while count < timeout_sec and element_id == id:
            BuiltIn().log_to_console('.','STDOUT',True)
            delta = DateTime.convert_time(interval)
            time.sleep(delta)
            count += delta
            element = self._driver.get_webelement(xpath)
            element_id = element.id
           
        if count >= timeout_sec:
            BuiltIn().log('Timeout happened but element is still not changed')
            if error_on_timeout:
                raise Exception('ERR: Timeout while waiting for element status changed')

        BuiltIn().log('Waited for element status changed')
  
