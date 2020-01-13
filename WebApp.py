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

# $Date: 2019-09-24 18:27:05 +0900 (火, 24  9月 2019) $
# $Rev: 2253 $
# $Ver: $
# $Author: $

import cv2,tempfile
import pytesseract
from difflib import SequenceMatcher
import numpy as np
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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.firefox.options import Options

### module methods

def _session_check(f, self, *args, **kwargs):
    BuiltIn().log("Check session timeout ...")
    error = Common.get_config_value('session-error','web') or "Session Timeout"
    if self._selenium.get_element_count(error) > 0:
        self._selenium.reload_page()
    return f(self, *args, **kwargs)

def session_check(f):
    return decorate(f, _session_check)

# reconnect methods currenlty focus on Samurai only
# need to enhance this
def _with_reconnect(keyword, self, *args, **kwargs):
    count = 0
    max_count = int(Common.get_config_value('max-retry','web'))
    reconnect = Common.get_config_value('reconnect','web',True)
    while count <= max_count:
        try:
            return keyword(self,*args,**kwargs)
        except (AssertionError,ElementNotFound) as err:
            self.capture_screenshot(extra="_warn") # save the last available screen
            BuiltIn().log("WRN: Save last available screen")
            BuiltIn().log(err)

            logout_count = int(self._selenium.get_matching_xpath_count("//h1[.='Timeout']"))
            BuiltIn().log("Found `%d` match for Timeout" % logout_count)
            # raise error if not a timeout or reconnect is not expected
            if logout_count == 0 or (not reconnect):
                BuiltIn().log("ERR: An unexpected error occurs. Not a timeout event",console=True)
                BuiltIn().log(err, console=True)
                raise
            count += 1
            if count < max_count:
                BuiltIn().log('WRN: Failed to execute the keyword `%s` %d time(s)'  % (keyword.__name__,count))
                BuiltIn().log('WRN: Will try the keyword again')
                safe_reconnect(self)
            else:
                BuiltIn().log('ERR: Gave up retry for keyword `%s`' % keyword.__name__)
                BuiltIn().log(type(err))
                BuiltIn().log(traceback.format_exc())
                # self.capture_screenshot(extra="_err") # save the last available screen
                raise
        except Exception as err:
            BuiltIn().log("ERR: An unexpected error occured", console=True)
            BuiltIn().log("Save last available screen", console=True)
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
        self._ajax_timeout          = int(Common.get_config_value('ajax-timeout','web','5'))
        self._type                  = 'webapp'
        self._selenium              = None  # SeleniumLibrary instance
        try:
            self._selenium = BuiltIn().get_library_instance('SeleniumLibrary')
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


    def set_ajax_timeout(self,wait_time='2s'):
        """ Set the ajax wait time
        """
        old_value = self._ajax_timeout
        self._ajax_timeout = DateTime.convert_time(wait_time)
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

        Returns the captured filename.

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
        total_width     = int(self._selenium.execute_javascript("return document.body.offsetWidth;"))
        # total_height    = int(self._selenium.execute_javascript("return document.body.parentNode.scrollHeight;"))

        script_text=""" return Math.max(document.body.scrollHeight, \
document.documentElement.scrollHeight, \
document.body.offsetHeight, \
document.documentElement.offsetHeight, \
document.body.clientHeight, \
document.documentElement.clientHeight); """
        total_height = int(self._selenium.execute_javascript(script_text))

        display_info = Common.get_config_value('display')

        if total_width < int(display_info['width']):
           total_width = int(display_info['width'])
        if total_height < int(display_info['height']):
           total_height = int(display_info['height'])
        # store old  window size
        (old_width, old_height) = self._selenium.get_window_size()

        # only update windows height
        self._selenium.set_window_size(old_width, total_height)
        time.sleep(2)
        self._selenium.set_screenshot_directory(Common.get_result_path())
        self._selenium.capture_page_screenshot(capture_name)
        # restore old window size
        self._selenium.set_window_size(old_width, old_height)
        # self._selenium.maximize_browser_window()
        time.sleep(2)
        BuiltIn().log("Captured the current screenshot(%dx%d) to file `%s`" % (total_width,total_height,capture_name))
        return capture_name


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

            self._selenium.close_browser()
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
        ignore_dead_node = Common.get_config_value('ignore-dead-node')

        app_info = Common.LOCAL['webapp'][app]
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
        if 'login-url' in app_info and app_info['login-url']:
            login_url = app_info['login-url']
        if 'browser' in app_info and app_info['browser']:
            browser  = app_info['browser']
        if 'local-storage' in app_info and app_info['local-storage']:
            local_storage = app_info['local-storage']
        else:
            local_storage = None
        if 'login-xpath' in template:
            login_xpath = template['login-xpath']

        # firefox options
        profile_dir = Common.get_result_path() + '/.%s_%s_profile' % (profile,name)

        if not os.path.exists(profile_dir): os.mkdir(profile_dir)
        os.chmod(profile_dir, 0o777)
        ff_opt = Options()
        # ff_opt.log.level = "TRACE"
        ff_opt.log.level = "INFO"
        # ff_opt.add_argument("--lang=en_US")
        # ff_opt.add_argument("-profile")
        # ff_opt.add_argument(profile_dir)

        # firefox profiles
        # ff_pf = webdriver.FirefoxProfile()
        ff_pf = webdriver.FirefoxProfile(profile_dir)
        BuiltIn().log("Open FF with profile `%s`" % ff_pf.path)
        if 'profile' in app_info and 'download-dir' in app_info['profile']:
            download_path = app_info['profile']['download-path']
        else:
            download_path = Common.get_result_path()
        if 'profile' in app_info and 'auto-save-mime' in app_info['profile']:
            auto_save_mime = app_info['profile']['auto-save-mime']
            ff_pf.set_preference("browser.helperApps.neverAsk.saveToDisk", app_info['profile']['auto-save-mime'])
        ff_pf.set_preference("browser.download.folderList",2)
        ff_pf.set_preference("browser.download.dir",download_path)
        ff_pf.set_preference("browser.download.manager.showWhenStarting",False);
        ff_pf.set_preference("browser.download.useDownloadDir",True);
        ff_pf.set_preference("browser.download.panel.shown",False);
        ff_pf.set_preference("gfx.canvas.azure.backends","skia");
        ff_pf.set_preference("gfx.content.azure.backends","skia");
        ff_pf.set_preference("general.warnOnAboutConfig", False)
        ff_pf.set_preference("javascript.enabled",True)
        # lang = Common.get_config_value('web','lang','ja, en-US, en')
        lang = Common.get_config_value('web','lang','en-US, en')
        ff_pf.set_preference("intl.accept_languages", lang)
        # ff_pf.set_preference("font.language.group","x-western");
        # ff_pf.set_preference("font.language.group","ja");
        # ff_pf.set_preference("browser.cache.disk.enable",False)
        # ff_pf.set_preference("browser.cache.memory.enable",False)
        # ff_pf.set_preference("browser.cache.offline.enable",False)
        # ff_pf.set_preference("network.http.use-cache",False)
        ff_pf.native_events_enabled = True
        ff_pf.update_preferences()

        # firefox capabilities
        ff_cap = webdriver.DesiredCapabilities.FIREFOX
        ff_cap['javascriptEnabled'] = True
        ff_cap['webStorageEnabled'] = True
        if 'proxy' in app_info and app_info['proxy']:
            proxy = Proxy()
            proxy.proxy_type = ProxyType.MANUAL
            if 'http' in app_info['proxy']:     proxy.http_proxy  = app_info['proxy']['http']
            if 'ssl' in app_info['proxy']:      proxy.ssl_proxy   = app_info['proxy']['ssl']
            if 'https' in app_info['proxy']:    proxy.ssl_proxy   = app_info['proxy']['https']
            if 'ftp' in app_info['proxy']:      proxy.ftp_proxy   = app_info['proxy']['ftp']
            proxy.add_to_capabilities(ff_cap)

        # create webdriver
        alias = '_%s_%s' % (profile,name)
        self._selenium.create_webdriver('Firefox',
            alias = alias,
            options = ff_opt,
            firefox_profile=ff_pf,
            desired_capabilities=ff_cap,
            service_log_path=Common.get_result_path()+'/selenium.log'
            )
        BuiltIn().log('Create a webdriver with alias `%s`' % alias)

        # open a browser and retry 3 times if it is necessary
        try:
            retry = 0
            while retry <= 3:
                try:
                    url = 'https://' + ip + '/' + login_url
                    self._selenium.go_to(url)
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
        browser_info['ff_cap'] = ff_cap
        browser_info['ff_profile_dir'] = ff_pf.path
        browser_info['capture_counter'] = 0
        browser_info['capture_format']  = "%s_%%010d" % app
        browser_info['browser']  = browser
        browser_info['profile']  = profile
        browser_info['login_url']  = login_url
        browser_info['local_storage'] = local_storage
        browser_info['login_xpath'] = login_xpath
        self._browsers[name] = browser_info
        display_info = Common.get_config_value('display')
        self._selenium.set_window_size(display_info['width'],display_info['height'])

        BuiltIn().log("Opened browser(%s) for %s app with profile `%s`" % (browser,app,ff_pf.path))


    def switch(self,name):
        """ Switches the current browser to ``name``
        """
        self._selenium.switch_browser('_%s_%s' % (self._browsers[self._current_name]['profile'],name))
        self._current_name = name
        BuiltIn().log("Switched the current browser to `%s`" % name)


    def close_all(self):
        """ Closes all current opened applications
        """
        num = len(self._browsers)
        while len(self._browsers) > 0:
            self.close()
        BuiltIn().log("Closed all %d the browsers for %s application" % (num,self.__class__.__name__))


    def connect(self,app,name,delay=u'5s'):
        """ Connect to the application using login information in the template

        Sample template:
        ```
            samurai:
                access: webapp
                auth: plain-text
                login-xpath:
                    user: name=username
                    pass: name=password
                    button: name=Submit
                    check: //div[@id='infoarea']
                profile: samurai
        ```
        `check` is optional which indicates item that need to be existed after a sucessful login.
        """
        self.open_ff_with_profile(app,name)
        # login
        auth = self._browsers[name]['auth']
        login_xpath = self._browsers[name]['login_xpath']

        user_xpath = login_xpath['user']
        pass_xpath = login_xpath['pass']
        login_button_xpath = login_xpath['button']
        if 'check' in login_xpath:
            login_check_xpath = login_xpath['check']
        else:
            login_check_xpath = None

        self._selenium.wait_until_element_is_visible(user_xpath)
        self._selenium.input_text(user_xpath, auth['username'])
        self._selenium.input_text(pass_xpath, auth['password'])

        self._selenium.click_button(login_button_xpath)
        if login_check_xpath:
            self._selenium.wait_until_page_contains_element(login_check_xpath)
        time.sleep(DateTime.convert_time(delay))
        BuiltIn().log("Connected to the application(%s) `%s` by name `%s`" % (self._type,app,name))


    def connect_all(self):
        """ Connects to all applications defined in ``local.yaml``

        The name of the connection will be the same of the `webapp` name
        """
        num = 0
        if 'webapp' in Common.LOCAL and Common.LOCAL['webapp']:
            for entry in Common.LOCAL['webapp']:
                device = Common.LOCAL['webapp'][entry]['device']
                type = Common.GLOBAL['device'][device]['type']
                if type.startswith(self._type):
                    num += 1
                    self.connect(entry,entry)
                    BuiltIn().log("Connected to %d applications" % num)
        else:
            BuiltIn().log("WARNING: No application to connect")


    def mark_element(self,xpath):
        """ Marking an element to check its stattus later
        """
        element = self._selenium.get_webelement(xpath)
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
        element = self._selenium.get_webelement(xpath)
        element_id = element.id
        while count < timeout_sec and element_id == id:
            BuiltIn().log_to_console('.','STDOUT',True)
            delta = DateTime.convert_time(interval)
            time.sleep(delta)
            count += delta
            element_count = self._selenium.get_element_count(xpath)
            if element_count > 0:
                element = self._selenium.get_webelement(xpath)
                element_id = element.id
            else:
                element_id = -1

        if count >= timeout_sec:
            BuiltIn().log('Timeout happened but element is still not changed')
            if error_on_timeout:
                raise Exception('ERR: Timeout while waiting for element status changed')

        BuiltIn().log('Waited for element status changed')


    def wait_and_click(self,xpath):
        """ Waits and clicks an element by its xpath

        Sample:
        | Wait and Click | //button[normalize-space(.)="OK"] |
        """
        self.capture_screenshot()
        self._selenium.wait_until_element_is_visible(xpath)
        self._selenium.click_element(xpath)
