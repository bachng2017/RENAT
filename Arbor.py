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


import os,time,traceback
import Common
from WebApp import WebApp,with_reconnect
from robot.libraries.BuiltIn import BuiltIn
from robot.libraries.BuiltIn import RobotNotRunningError
from selenium import webdriver
from selenium.webdriver.common.proxy import Proxy, ProxyType
import robot.libraries.DateTime as DateTime
from selenium.common.exceptions import WebDriverException


class Arbor(WebApp):
    """ A library provides functions to control Arbor application

    The library utilize `SeleniumLibrary` and adds more functions to control
    Arbor application easily.

    See [./WebApp.html|WebApp] for common keywords of web applications.

    `SeleniumLibrary` keywords still could be used along with this library.
    See [http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html|SeleniumLibrary] for more details.

    *Notes*: From 0.1.10, move from `Selenium2Library` to `SeleniumLibrary`
    """

    ROBOT_LIBRARY_SCOPE = 'TEST SUITE'
    ROBOT_LIBRARY_VERSION = Common.version()


    def __init__(self):
        super(Arbor,self).__init__()
        self.retry_num = 3
        self.auth = {}
        self._type = 'arbor'


#     def connect(self,app,name):
#         """ Opens a web browser and connects to application and assigns a
#         ``name``.
#
#         Extra information could be added to the ``webapp`` sections likes
#         ``login-url``, ``browser`` or ``profile-dir``. Default values are:
#         | browser     | firefox |
#         | login-url   | /         |
#         | profile-dir | ./config/samurai.profile |
#         """
#         self.open_ff_with_profile(app,name)
#         # login
#         auth = self._browsers[name]['auth']
#         self._selenium.input_text('name=username', auth['username'])
#         self._selenium.input_text('name=password', auth['password'])
#         self._selenium.click_button('name=Submit')
#         time.sleep(5)


    def reconnect(self):
        """ Reconnect to server if necessary
        """
        name = self._current_name
        auth            = self._browsers[name]['auth']
        url             = self._browsers[name]['url']
        self._selenium.go_to(url)
        self._selenium.wait_until_element_is_visible('name=username')

        # login
        self._selenium.input_text('name=username', auth['username'])
        self._selenium.input_text('name=password', auth['password'])
        self._selenium.click_button('name=Submit')
        time.sleep(5)
        BuiltIn().log("Reconnected to the Arbor application(%s)" % name)


    def login(self):
        """ Logs into the Arbor application
        """
        return self.reconnect()

    @with_reconnect
    def logout(self):
        """ Logs-out the current application, the browser remains
        """
        self.switch(self._current_name)
        self._selenium.click_link("xpath=//a[contains(.,'(Log Out)')]")

        if self._selenium.get_element_count('logout_confirm') > 0:
            self._selenium.click_button('logout_confirm')
        BuiltIn().log("Exited Arbor application")


    @with_reconnect
    def show_all_mitigations(self):
        """ Shows all mitigations
        """

        self.switch(self._current_name)
        self._selenium.mouse_over("xpath=//a[.='Mitigation']")
        self._selenium.wait_until_element_is_visible("xpath=//a[contains(.,'All Mitigations')]")
        self._selenium.click_link("xpath=//a[contains(.,'All Mitigations')]")
        self._selenium.wait_until_element_is_visible("//div[@class='sp_page_content']")
        self.verbose_capture()
        BuiltIn().log("Displayed all current mitigations")


    @with_reconnect
    def show_detail_mitigation(self,search_str):
        """ Shows detail information of a mitigation by its `search_str`

        *Note*: the result could include multi mitigations
        """
        self.show_all_mitigations()
        xpath = "//a[contains(.,'%s')]" %  search_str
        self._selenium.input_text("search_string_id",search_str)
        self._selenium.click_button("search_button")
        time.sleep(2)
        self._selenium.wait_until_page_contains_element("xpath=//div[@class='sp_page_content']")
        time.sleep(2)
        self._selenium.wait_until_element_is_visible("search_button")
        self._selenium.click_link(xpath)
        time.sleep(5)
        self.verbose_capture()
        BuiltIn().log("Showed details of a mitigation searched by `%s`" % search_str)


    @with_reconnect
    def show_detail_countermeasure(self,name,*method_list):
        """ Shows detail information about a countermeasure

        `name` is used to search the the mitigation and `method_list` is a list
        of countermeasures that are listed in Arbor Countermeasures panel

        Return the number of displayed methods

        Notes: the keyword will ignore if the method is not in its list and does not count for that

        Example:
        | ${NAME}  |   ${ID}=   |       `Show Detail First Mitigation` |
        | ${COUNT= |  Arbor.`Show Detail Countermeasure` | ${NAME} | DNS Malformed |
        | Arbor.`Capture Screenshot` |
        | Sleep  | 10s |
        | Arbor.`Show Detail Countermeasure` | ${NAME} |  Zombie Detection | HTTP Malformed |
        | Arbor.`Capture Screenshot` |
        """
        self.show_detail_mitigation(name)
        total_method = len(method_list)
        count_method = 0
        for item in method_list:
            xpath = '//table//td[(@class="borderright") and (. = "%s")]/../td[1]/a' % item
            if self._selenium.get_element_count(xpath) > 0:
                target = self._selenium.get_webelement(xpath)
                target.click()
                time.sleep(2)
                count_method += 1
        self.verbose_capture()
        BuiltIn().log('Showed detail information for %d/%d countermesure of mitigation `%s`' %(count_method,total_method,name))
        return count_method


    @with_reconnect
    def detail_first_mitigation(self):
        BuiltIn().log_to_console('WARN: This keyword is deprecated. Use `Show Detail First Mitigation` instead')
        return self.show_detail_first_mitigation()

    @with_reconnect
    def show_detail_first_mitigation(self):
        """ Shows details about the 1st mitigation on the list

        The keyword returns the `mitigation ID` and its name
        """
        name,id = self.show_detail_mitigation_with_order(1)
        return name,id


    @with_reconnect
    def show_detail_mitigation_with_order(self,order):
        """ Shows details about the `order`(th) mitigation in the current list

        `order` is counted from ``1``.
        The keyword returns the mitigation_id and its name

        Example:
        | ${NAME} |  ${ID}= | Arbor.`Show Detail Mitigation With Order` | 3 |
        | Log To Console  |   ${NAME}:${ID} |
        | Arbor.`Capture Screenshot` |
        """
        self.show_all_mitigations()
        # ignore the header line
        xpath = '//table[1]//tr[%s]/td[%s]//a[1]' % (int(order)+1,2)
        link = self._selenium.get_webelement(xpath)
        mitigation_name = link.get_attribute('innerText')
        href=link.get_attribute('href')
        mitigation_id = href.split('&')[1].split('=')[1]
        self._selenium.click_link(xpath)
        time.sleep(5)
        BuiltIn().log("Displayed detail of `%s`th mitigation in the list" % order)
        self.verbose_capture()
        return mitigation_name,mitigation_id


    @with_reconnect
    def get_status_msg(self):
        """ Get current status message

        Return null string if no message exists
        """
        msg = ''
        xpath = u"//ul[@id='statusmessage_content']//div"
        count = self._selenium.get_element_count(xpath)
        if count > 0:
            msg = self._selenium.get_webelement(xpath).text
        BuiltIn().log('Got current status message. Msg is `%s`' % msg)
        return msg


    @with_reconnect
    def clean_status_msg(self):
        """ Disposes any alert or status messgae at the top of the current page
        """
        BuiltIn().log('Cleans aler/status message')
        msg = ''
        # close any current open status message
        xpath = u"//a[@id='statusmessage_link' and @class='collapselink']"
        msg_count = self._selenium.get_element_count(xpath)
        if msg_count > 0:
            msg = self.get_status_msg()
            self._selenium.click_link(xpath)
        self._selenium.wait_until_page_does_not_contain_element(xpath)

        BuiltIn().log('Closed status message `%s`' % msg)


    @with_reconnect
    def menu(self,order,wait='2s',capture_all=False,prefix='menu_',suffix='.png',partial_match=False):
        """ Access to Arbor menu

        Parameters
        - ``order`` is the list of top menu items separated by '/'
        - ``wait`` is the wait time after the last item is clicked
        - if ``capture_all`` is ``True`` then a screenshot is captured for each
          menu item automtically. In this case, the image file is appended by
        ``prefix`` and ``suffix``.
        - by default, the system try to match the menu item in full, when
          ``partial_match`` is ``True``, partial match is applied.

        Examples:
        | Arbor.`Menu`               |          order=Alerts/Ongoing |
        | Arbor.`Capture Screenshot` |
        | Arbor.`Menu`               |          order=Alerts/All Alerts |
        | Arbor.`Capture Screenshot` |
        | Arbor.`Menu`               |          order=System/Status/Deployment Status |
        | Arbor.`Capture Screenshot` |
        | Arbor.`Menu`               |          order=System/Status/Signaling Status/Appliance Status | partial_match=${TRUE} |
        | Arbor.`Capture Screenshot` |
        """
        self.switch(self._current_name)

        self.clean_status_msg()

        index = 0
        items = order.split('/')
        for item in items:
            BuiltIn().log("    Access to menu item %s" % item)
            index +=1
            if index > 1:
                menu = '//li[not(contains(@class,\'top_level\'))]'
            else:
                menu = ''
            if partial_match:
                xpath = "xpath=%s//a[contains(.,'%s')]" % (menu,item)
            else:
                xpath = "xpath=%s//a[.='%s']" % (menu,item)
            self._selenium.mouse_over(xpath)
            # self._selenium.click_element(xpath)
            time.sleep(1)
            # self._selenium.wait_until_element_is_visible(xpath)
            if capture_all:
                capture_name='%s%s%s' % (prefix,item,suffix)
                self._selenium.capture_page_screenshot(capture_name)
            self.verbose_capture()
            if index == len(items):
                self._selenium.click_link(xpath)
                time.sleep(DateTime.convert_time(wait))


    def commit(self,strict=True):
        """ Commit the current changes

        If `strict` is ``${TRUE}`` then the keyword fails if there is not change
        to commit. Otherwise, it does nothing
        """
        xpath = u"//button[@name='open_commit' and not(starts-with(@class,'no'))]"
        count = self._selenium.get_element_count(xpath)
        BuiltIn().log('Found %d elements' % count)
        if strict and count == 0:
            raise Exception('ERROR: no changes to commit')

        if count > 0:
            self.verbose_capture()
            self._selenium.click_button(xpath)
            main_window = self._selenium.select_window('NEW')
            self.verbose_capture()
            self._selenium.click_button(u'commit')

            self._selenium.select_window(main_window)
            self._selenium.wait_until_element_is_not_visible(xpath,timeout='20s')
            self.verbose_capture()
            BuiltIn().log('Committed changes')
        else:
            BuiltIn().log('WARN:No changes to commit')


