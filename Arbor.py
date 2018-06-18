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

# $Date: 2018-05-31 12:59:24 +0900 (Thu, 31 May 2018) $
# $Rev: 1012 $
# $Ver: $
# $Author: $

import os,time
import Common
from WebApp import WebApp
from robot.libraries.BuiltIn import BuiltIn
from robot.libraries.BuiltIn import RobotNotRunningError
from Selenium2Library import Selenium2Library
from selenium import webdriver
from selenium.webdriver.common.proxy import Proxy, ProxyType

class Arbor(WebApp):
    """ A library provides functions to control Arbor application

    The library utilize `Selenium2Library` and adds more functions to control
    Arbor application easily.

    See [./WebApp.html|WebApp] for common keywords of web applications.

    `Selenium2Library` keywords still could be used along with this library.
    See [http://robotframework.org/Selenium2Library/Selenium2Library.html|Selenium2Library] for more details.
    """

    ROBOT_LIBRARY_SCOPE = 'TEST SUITE'
    ROBOT_LIBRARY_VERSION = Common.version()


    def __init__(self):
        super(Arbor,self).__init__()


    def connect_all(self):
        """ Connects to all applications defined in ``local.yaml``

        The name of the connection will be the same of the `webapp` name
        """

        num = 0
        if 'webapp' in Common.LOCAL and Common.LOCAL['webapp']:
            for entry in Common.LOCAL['webapp']:
                device = Common.LOCAL['webapp'][entry]['device']
                type = Common.GLOBAL['device'][device]['type']
                if type.startswith('arbor'):
                    num += 1
                    self.connect(entry,entry)
                    BuiltIn().log("Connected to %d applications" % num)
        else:
            BuiltIn().log("WARNING: No application to connect")


    def connect(self,app,name):
        """ Opens a web browser and connects to application and assigns a
        ``name``.

        Extra information could be added to the ``webapp`` sections likes
        ``login_url``, ``browser`` or ``profile_dir``. Default values are:
        | browser     | firefox |
        | login_url   | /         |
        | profile_dir | ./config/samurai.profile |
        """
        if name in self._browsers:
            BuiltIn().log("Browser `%s` already existed. Reconnect to it" % name)
            self.close()
            # return

        login_url   = '/'
        browser     = 'firefox'
        profile_dir = None

        # collect information about the application
        app_info = Common.LOCAL['webapp'][app]
        if 'login_url' in app_info and app_info['login_url']:    
            login_url = app_info['login_url']
        if 'browser'  in app_info and app_info['browser']:    
            browser  = app_info['browser']
        if 'profile_dir' in app_info and app_info['profile_dir']:    
            ff_profile_dir  = os.getcwd() + 'config/' + app_info['profile_dir']
        if 'proxy' in app_info and app_info['proxy']:
            proxy = Proxy()
            proxy.proxy_type = ProxyType.MANUAL
            if 'http' in app_info['proxy']:
                proxy.http_proxy    = app_info['proxy']['http']
            if 'socks' in app_info['proxy']:
                proxy.socks_proxy   = app_info['proxy']['socks']
            if 'ssl' in app_info['proxy']:
                proxy.ssl_proxy     = app_info['proxy']['ssl']
            capabilities = webdriver.DesiredCapabilities.FIREFOX
            proxy.add_to_capabilities(capabilities)

        device = app_info['device']
        device_info = Common.GLOBAL['device'][device]
        ip = device_info['ip']
        type = device_info['type']

        template = Common.GLOBAL['access-template'][type]
        profile = template['profile']   

        # currently, only plain-text authentication is supported
        auth = {}
        auth['username']    = Common.GLOBAL['auth']['plain-text'][profile]['user']
        auth['password']    = Common.GLOBAL['auth']['plain-text'][profile]['pass']
        url = 'https://%s/%s' %  (ip,login_url)

        # open a browser
        self._driver.open_browser(url,browser,'_arbor_' + name,False,None,profile_dir)
        self._driver.wait_until_element_is_visible('name=username')
        
        # login
        self._driver.input_text('name=username', auth['username'])
        self._driver.input_text('name=password', auth['password'])
        self._driver.click_button('name=Submit')
        time.sleep(5)
    
        self._current_name = name
        self._current_app  = app
        browser_info = {}
        browser_info['capture_counter'] = 0
        browser_info['capture_format']  = 'arbor_%010d'
        browser_info['browser']         = browser
        self._browsers[name] = browser_info

        BuiltIn().log("Connected to `%s` with name `%s`" % (app,name))


    def reconnect(self):
        """ Reconnect if necessary
        """
        # self._driver.reload_page()
        login_element_count = 0
        
        self._driver.reload_page()
        login_element_count = int(self._driver.get_matching_xpath_count("//button[@value='Log In']"))

        if login_element_count > 0: 
            BuiltIn().log("Try to reconnect to the system")
            self.connect(self._current_app, self._current_name)
            BuiltIn().log("Reconnected to the system by `%s`" % self._current_name)

        
    def login(self):
        """ Logged-into the Arbor application
        """
        self.switch(self._current_name) 
        self._driver.input_text('name=username', auth['username'])
        self._driver.input_text('name=password', auth['password'])
        self._driver.click_button('name=Submit')
        time.sleep(5)

    
    def logout(self):
        """ Logs-out the current application, the browser remains
        """
    
        self.switch(self._current_name) 
        self._driver.click_link("xpath=//a[contains(.,'(Log Out)')]")
        BuiltIn().log("Exited Arbor application")
    
    
    def switch(self,name):
        """ Switches the current browser to ``name``
        """
        self._driver.switch_browser('_arbor_' + name)
        self._current_name = name
        self.reconnect()
        BuiltIn().log("Switched the current browser to `%s`" % name)

    
    def set_count(self,counter=0):
        """ Sets current counter to ``counter``
        """
        pass
    
    def close(self):
        """ Closes the current active browser
        """
    
        # self.switch(self._current_name) 

        old_name = self._current_name
        self._driver.close_browser()
        del(self._browsers[old_name])
        if len(self._browsers) > 0:
            self._current_name = self._browsers.keys()[-1]
        else:
            self._current_name = None
    
        BuiltIn().log("Closed the browser '%s', current acttive browser is `%s`" % (old_name,self._current_name))
        return old_name
    
    
    def close_all(self):
        """ Closes all current opened applications
        """
        for entry in self._browsers:
            self.switch(entry)
            self._driver.close_browser()
        BuiltIn().log("Closed all Arbor applications")
    
    
    def show_all_mitigations(self):
        """ Shows all mitigations
        """
        
        self.switch(self._current_name)
        self._driver.mouse_over("xpath=//a[.='Mitigation']")
        self._driver.wait_until_element_is_visible("xpath=//a[contains(.,'All Mitigations')]")
        self._driver.click_link("xpath=//a[contains(.,'All Mitigations')]")
        self._driver.wait_until_element_is_visible("//div[@class='sp_page_content']")
        # time.sleep(5) 
        # self._driver.reload_page()
        # time.sleep(5) 
        BuiltIn().log("Displayed all current mitigations")



    def show_detail_mitigation(self,id):
        """ Shows detail information for a mitigation 
        """
        self.switch(self._current_name)

        xpath = "//a[contains(.,'%010d')]" % int(id)
        miti_id = "samurai%010d" % int(id)
        self._driver.input_text("search_string_id",miti_id)
        self._driver.click_button("search_button")
        self._driver.wait_until_page_contains_element("xpath=//div[@class='sp_page_content']") 

        self._driver.wait_until_element_is_visible(xpath)
        self._driver.click_link(xpath)
        time.sleep(5)
        BuiltIn().log("Showed details of a mitigation")    
  
 
    def detail_first_mitigation(self):
        """ Shows details about the 1st mitigation on the list
        """

        self.switch(self._current_name)
        miti_name = self._driver.get_table_cell("xpath=//table[@class='sptable']",2,2)
        # self._driver.click_link("xpath=//a[.=' %s']" % miti_name)
        self._driver.click_link(miti_name)
        time.sleep(5)
        BuiltIn().log("Displayed detail of 1st mitigation in the list")
