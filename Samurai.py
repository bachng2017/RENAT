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

# $Date: 2019-09-20 09:42:03 +0900 (金, 20  9月 2019) $
# $Rev: 2252 $
# $Ver: $
# $Author: $

import os,time,re,traceback,shutil
import lxml.html
import Common
from decorator import decorate
from WebApp import WebApp,with_reconnect
from robot.libraries.BuiltIn import BuiltIn
import robot.libraries.DateTime as DateTime
from robot.libraries.BuiltIn import RobotNotRunningError
from SeleniumLibrary import SeleniumLibrary
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.proxy import Proxy, ProxyType



class Samurai(WebApp):
    """ A library provides functions to control Samurai application

    The library utilize `SeleniumLibrary` and adds more functions to control
    Samurai application easily. Without other furthur mentions, all of the concepts
    of ``user``, ``user group`` are Samurai concepts. By default, RENAT will try to
    connec to all Samurai nodes defined in active ``local.yaml`` at the beginning of
    the test and disconnect from them at the end of the test automatically. Usually
    user does not need to use ``Connect All`` and ``Close`` explicitly.

    Currently, this module supposed that Samurai is used in Japanese locale.
    When Samurai module has error, it tried to make the last snapshot in
    ``result/selenium-screenshot-x.png``. Checking this capture will help to
    understand the reason of the error.

    Currently the module support Samurai 09/14/16

    Some keywords of [./Samurai.html|Samurai] is using ``xpath`` to identify
    elements. See `Selenium2Library` for more details about xpath.

    See [./WebApp.html|WebApp] for common keywords of web applications and how
    to configure the ``local.yaml`` file.


    `SeleniumLibrary` keywords still could be used together within this library.
    See [http://robotframework.org/Selenium2Library/Selenium2Library.html|Selenium2Library] for more details.
    """

    ROBOT_LIBRARY_SCOPE = 'TEST SUITE'
    ROBOT_LIBRARY_VERSION = Common.version()


    def __init__(self):
        super(Samurai,self).__init__()
        self._type = 'samurai'


#     def connect(self,app,name):
#         """ Opens a web browser and connects to application and assigns a
#         ``name``.
#
#         - `app` is the name of the application (e.g. samurai-1)
#         - `name` is the name of the browser
#
#         If not defined in ``local.yaml`` those following key will have defaut
#         values:
#         | browser     | firefox             | optional |
#         | login_url   | /                   | optiona  |
#         | proxy:      |                     | optional |
#         |     http:   10.128.8.210:8080     | optional |
#         |     ssl:    10.128.8.210:8080     | optional |
#         |     socks:  10.128.8.210:8080     | optional |
#
#         """
#         self.open_ff_with_profile(app,name)
#         # login
#         auth = self._browsers[name]['auth']
#         self._selenium.wait_until_element_is_visible('name=username')
#         self._selenium.input_text('name=username', auth['username'])
#         self._selenium.input_text('name=password', auth['password'])
#         self._selenium.click_button('name=Submit')
#         self._selenium.wait_until_page_contains_element("//div[@id='infoarea']")
#         BuiltIn().log("Connected to the application `%s` by name `%s`" % (app,name))


    def reconnect(self):
        """ Reconnects to the server
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
        self._selenium.wait_until_page_contains_element("//div[@id='infoarea']")
        BuiltIn().log("Reconnected to the Samurai application(%s)" % name)


    def wait_until_load_finish(self, timeout=u"2m"):
        """ Waits until the loading finishes
        """
        self._selenium.wait_until_page_does_not_contain_element('//img[@src="image/ajax-loader.gif"]',timeout)
        BuiltIn().log("Finished loading")


    def login(self):
        """ Logs-in into the application

        User and password is set by the template and authentication methods in
        the master files
        """
        self.switch(self._current_name)
        # login
        self._selenium.input_text('name=username', auth['username'])
        self._selenium.input_text('name=password', auth['password'])
        self._selenium.click_button('name=Submit')
        self._selenium.wait_until_page_contains_element("//div[@id='infoarea']")
        BuiltIn().log("Logged-in the application")

    @with_reconnect
    def logout(self):
        """ Logs-out the current application, the browser remains
        """

        self.switch(self._current_name)
        self._selenium.click_link('logout')
        self._selenium.page_should_contain_image('image/logout_10.gif')

        BuiltIn().log("Exited samurai application")


    @with_reconnect
    def left_menu(self,menu,locator=None, ignore_first_element=True):
        """ Chooses the left panel menu by its displayed name

        When ``locater`` is not null, the keyword will return a list of text
        attribute of all elements specified by the ``locator``. ``locator``
        could be a xpath or a predefined string.

        ``locator`` predefined strings are: ``MITIGATE_REALTIME``,
        ``MITIGATE_LIST``, ``DETECT_LIST``

        For example, a xpath ``//div[@id='infoareain2']/*//td[1]/a`` means the list of
        `link` of all elements in a 1st column of a table insides a ``div`` with
        id ``infoareain2``.

        Examples:
        | Samurai.`Left Menu` | Traffic |
        | Samurai.`Left Menu` | Detection |
        | Samurai.`Left Menu` | ポリシー管理 |
        | @{LIST}= | Samurai.`Left Menu` | Active Mitigation | //div[@id='infoareain2']/*//td[1]/a |
        """

        self.switch(self._current_name)
        self._selenium.select_window('MAIN')

        target = self._selenium.get_webelement(u'//div[@class="submenu" and contains(.,"%s")]' % menu)
        id = target.get_attribute('id')
        if not target.is_displayed():
            self._selenium.execute_javascript("toggle_disp('%s','mitigation')" % id)
        self._selenium.click_link(menu)
        self._selenium.wait_until_element_is_visible("id=my_contents")

        item_list = []
        if locator:
            if locator == 'MITIGATE_LIST':
                xpath = "//div[@id='infoareain2']/*//td[1]/a"
            elif locator == 'MITIGATE_REALTIME':
                xpath = "//div[@id='infoareain']/*//td[1]/a"
            elif locator == 'DETECT_LIST':
                xpath = "//div[@id='infoareain']/*//td[1]/a"
            else:
                xpath = locator
            try:
                item_list = [ x.text for x in self._selenium.get_webelements(xpath) ]
            except Exception:
                pass

            if ignore_first_element and len(item_list) > 0:
                BuiltIn().log("    Removed the 1st element in the list")
                item_list = item_list[1:]
            else:
                BuiltIn().log("    Found zero elements")

        self.wait_until_load_finish()

        BuiltIn().log("Chose left menu `%s`" % menu)
        return item_list


    @with_reconnect
    def start_mitigation(self,policy,prefix,comment="mitigation started by RENAT",device=None,force=False):
        """ Starts a mitigation with specific ``prefix``

        ``device`` is used for matching real device name configured by Samurai
        If ``force`` is ``TRUE`` then the keyword will fail if selected device
        does not contain ``device``

        Returns mitigation ``id`` and selected ``arbor device``

        Example:
        | ${id} |  ${device}=  |  Samurai.`Start Mitigation` | 211.1.12.1/32 | mitigation by RENAT | SP-A | ${TRUE} |
        """
        self.switch(self._current_name)

        menu = self._selenium.get_webelement(u'//div[@id="submenu3"]')
        if not menu.is_displayed():
            BuiltIn().log('Executing the javascript to expand the left menu')
            self._selenium.execute_javascript("toggle_disp('submenu3','mitigation')")
            BuiltIn().log('Executed the javascript to expand the left menu')
        # self.capture_screenshot()
        self._selenium.wait_until_page_contains_element(u"//a[contains(.,'Active Mitigation')]")
        self._selenium.click_link("Active Mitigation")
        self._selenium.wait_until_page_contains_element(u"//input[@value='Guard実行']")
        self._selenium.click_button(u"//input[@value='Guard実行']")
        time.sleep(5)

        # IP input
        self._selenium.select_window(u"title=Mitigation登録 IPアドレスの決定")
        self._selenium.select_from_list_by_label("gui_policy",policy)
        self._selenium.input_text("name=address",prefix)
        self._selenium.click_button(u"//input[@value='追加']")

        # device check
        self._selenium.element_should_not_be_visible(u"//span[contains(.,'有効な mitigation デバイスがありません')]")

        # device selection
        title = self._selenium.get_title()
        if title == u"Mitigation 登録 Mitigation Device決定" :
            if device:
                value = self._selenium.get_value("//tr[contains(.,'%s')]/td[1]/input" % device)
                self._selenium.select_radio_button("device_id",value)
            BuiltIn().log("Chose device `%s`" % device)
            self._selenium.click_button(u"Mitigation Device 決定")

        # comment input
        applied_device = self._selenium.get_text(u"//td[.='Mitigation デバイス']/../td[2]")
        if force and device not in applied_device:
            raise("Selected device is `%s` which does not contain `%s`" % (applied_device,device))

        self._selenium.input_text("name=comment",comment)

        # execute
        self._selenium.click_button(u"//input[@value='Mitigation 実行']")
        id = self._selenium.get_text("xpath=//*[text()[contains(.,'Mitigation ID')]]")
        search = re.search(".*:(.+) .*$", id)
        result = search.group(1)

        self._selenium.click_button(u"//input[@value='閉じる']")
        self._selenium.select_window("title= Active Mitigation")
        self._selenium.reload_page()
        time.sleep(5)

        BuiltIn().log("Started a new mitigation id=`%s` by device `%s`" % (result,applied_device))
        return (result,applied_device)


    @with_reconnect
    def stop_mitigation(self,id,raise_error=True):
        """ Stops a mitigation by its ID

        The keyword will raise an error if `raise_error` is ``True``. Otherwise
        it will ignore any errors.

            Example:
            | Samurai.`Stop Mitigation` | 700 |
        """

        self.switch(self._current_name)
        self.left_menu(u"Active Mitigation")
        self._selenium.wait_until_page_contains(u"Active Mitigation")

        try:
            self._selenium.select_window("title= Active Mitigation")
            self._selenium.reload_page()
            self._selenium.wait_until_element_is_visible("infoarea")
            self._selenium.click_button(u"//input[@onclick='delete_confirm(%s);']" % id)
            self._selenium.confirm_action()
            self._selenium.wait_until_element_is_visible(u"//span[contains(.,'削除を開始しました')]")
            BuiltIn().log("Stopped the mitigation id=%s" % id)
        except Exception as err:
            if raise_error:
                raise err
            else:
                BuiltIn().log_to_console("WARN: failed to stop mitgation %s but continue" % id)


    @with_reconnect
    def add_user(self,group,**user_info):
        """ Adds user to the current group
        ``user_info`` is a dictionary contains user information that has
        following keys: ``name``, ``password``, ``privilege`` and ``policy``

        ``privilege`` is existed privilege that has been created (e.g: _system_admin_.

        ``policy`` could be ``*`` for all current policies or a list of policy
        names that are binded to this user.

        ``group`` is the user group. ``Dot(.)`` means current group

        Examples:
        | Samurai.`Add User` |  OCNDDoS | name=user000   |  password=Test12345678 |
        | ...                |  privilege=system_admin |  policy=*  |
        | Samurai.`Add User` |  OCNDDoS | username=user001   |  password=Test12345678 |
        | ...                |  privilege=system_admin |  policy=OCN11,OCN12  |

        """
        ### choose menu
        if group == '.':
            self.left_menu(u"ユーザ管理(自グループ)")
        else:
            self.left_menu(u"ユーザ管理(他グループ)")
            self._selenium.select_from_list_by_label("policy_group_id", group)

        self._selenium.wait_until_page_contains_element(u"//input[@value='ユーザの追加']")
        self._selenium.click_button(u"//input[@value='ユーザの追加']")
        self._selenium.input_text("user_name",user_info['name'])
        self._selenium.input_text("password1",user_info['password'])
        self._selenium.input_text("password2",user_info['password'])
        self._selenium.select_from_list("privilege_group_id",user_info["privilege"])
        policy = ''
        if 'policy' in user_info:
            policy = user_info['policy']
            if policy == '*':
                self._selenium.execute_javascript("change_all_check_box(document.FORM1.policy_id, true)")
            else:
                for entry in [x.strip() for x in policy.split(',')] :
                    self._selenium.select_checkbox(u"//label[contains(.,'%s')]/../input" % entry)
        #
        self._selenium.click_button(u"//button[contains(.,'追加')]")
        self._selenium.wait_until_page_contains_element(u"//span[contains(.,'ユーザを追加しました')]")
        BuiltIn().log("Added user `%s`" % user_info['name'])


    @with_reconnect
    def delete_user(self,group,*user_list):
        """ Deletes user from the user group

        ``group`` is the user group. And ``.`` means current group
        Returns the number of deleted users

        Examples:
        | Samurai.`Delete User` | SuperGroup | user001 | user002 |
        | Samurai.`Delete User` | .          | user002 |
        """
        ### choose menu
        if group == '.':
            self.left_menu(u"ユーザ管理(自グループ)")
        else:
            self.left_menu(u"ユーザ管理(他グループ)")
            self._selenium.select_from_list_by_label("policy_group_id", group)

        self._selenium.wait_until_page_contains(u"ユーザ管理")
        items,selected_items = self.select_items_in_table("//tr/td[3]","../td[1]",*user_list)
        if len(selected_items) > 0:
            self._selenium.click_button(u"//input[@value='削除']")
            self._selenium.confirm_action()
            self._selenium.wait_until_page_contains_element(u"//span[contains(.,'ユーザを削除しました')]")

        BuiltIn().log("Deleted %d user" % len(selected_items))
        return len(selected_items)


    @with_reconnect
    def make_item_map(self,xpath):
        """ Makes a item/webelement defined `xpath`

        The map is a dictionary from `item` to the `WebElement`
        Items name found by ``xpath`` are used as keys
        """
        BuiltIn().log("Making item map by xpath `%s`" % xpath)
        self._selenium.wait_until_page_contains_element(xpath)
        items = self._selenium.get_webelements(xpath)
        item_map = {}
        for item in items:
            html = item.get_attribute('outerHTML')
            element = lxml.html.fromstring(html)
            text = element.text
            # using text_content in case of nothing found from text
            if not text: text = element.text_content()
            key = text.replace(u'\u200b','').strip()
            item_map[key] = item

        BuiltIn().log("Made a map of %d items of from a table" % (len(items)))
        return item_map


    @with_reconnect
    def select_items_in_table(self,xpath,xpath2,*item_list):
        """ Checks items in Samurai table by xpath

        ``xpath`` points to the column that used as key and ``xpath2`` is the
        relative xpath contains the target column.

        ``item_list`` is a list of item and its action that need to check.
        Item in the list could be a regular expresion with the format ``re:<regular expression>|action``.

        The default action for the item could be ``click``(default),``check`` or ``uncheck``

        The keyword is called with assuming that the table is already visible.

        Returns the tupple of all items and selected items


        *Note:* Non-width-space (\u200b) will be take care by the keyword.

        *Note:* if the first item_list is `*` then the keywork will try to click
        a link named `すべてを選択`.
        """

        BuiltIn().log("Trying to select %d items from table" % len(item_list))

        # prepare
        count = 0
        result_map = {}
        action_map = {}
        item_map  = self.make_item_map(xpath)

        tmp = item_list[0].split(',')
        if tmp[0] == '*':
            self._selenium.click_link(u"すべてを選択")
            count = len(item_map)
            result_map = item_map
            for key in result_map:
                action_map[key] = tmp[1]
        else:
            key_list = []
            action_list = []
            for item in item_list:
                tmp = item.split('|')
                if len(tmp) < 2:
                    action = 'click'
                else:
                    action = tmp[1]
                if tmp[0].startswith('re:'):
                    pattern = tmp[0].split(':')[1]
                    re_match = re.compile(pattern)
                    for k in item_map:
                        if re_match.match(k):
                            key_list.append(k)
                            action_list.append(action)
                else:
                    key_list.append(tmp[0])
                    action_list.append(action)

            for k,action in zip(key_list,action_list):
                if k in item_map:
                    BuiltIn().log("    Found item %s:%s" % (k,action))
                    result_map[k] = item_map[k]
                    action_map[k] = action

        count = len(result_map)

        #
        for item in result_map:
            target = result_map[item].find_element_by_xpath(xpath2)
            action = action_map[item]
            if action == 'click':
                self._selenium.click_element(target)
                BuiltIn().log("    Clicked the item")
            if action == 'check':
                if not target.is_selected():
                    self._selenium.click_element(target)
                    BuiltIn().log("    Checked the item")
                else:
                    BuiltIn().log("    Item is already checked")
            if action == 'uncheck':
                if target.is_selected():
                    self._selenium.click_element(target)
                    BuiltIn().log("    Unchecked the item")
                else:
                    BuiltIn().log("    Item is already unchecked")

        BuiltIn().log("Set %d/%d items in the table" % (len(result_map),len(item_map)))
        return (item_map,result_map)

#    @with_reconnect
#    def show_policy_edit_panel(self,policy_name,panel_name,strict=False):
#        """ Show edit panel `panel_name` for policy `policy_name`
#
#        *Notes*: When `strict` is ``True`` then the keword raises error if no
#        panel is found.
#        """
#        self.left_menu(u"ポリシー管理")
#        self._selenium.wait_until_page_contains_element("//input[@id='filter']")
#        self._selenium.input_text("filter",policy_name)
#        time.sleep(self._ajax_timeout)
#        item_map = self.make_item_map("//tr/td[3]/div")
#        item = item_map[policy_name]
#        button = item.find_element_by_xpath(u"../../td/div/input[@title='編集']")
#        self._selenium.wait_until_page_contains_element(button)
#        self._selenium.click_element(button)
#        self._selenium.wait_until_page_contains_element(u"//button[.='変更']")
#
#        if panel_name == u'基本設定':
#            panel_xpath = u"//span[starts-with(@class,'submenu_')]//span[normalize-space(.)='%s']" % panel_name
#        else:
#            panel_xpath = u"//a[starts-with(@class,'submenu_')]//span[normalize-space(.)='%s']" % panel_name
#
#        if strict:
#            self._selenium.wait_until_page_contains_element(xpath)
#        if panel_name != u'基本設定':
#            count = self._selenium.get_element_count(panel_xpath)
#            if count > 0:
#                self.verbose_capture()
#                self._selenium.click_element(panel_xpath)
#                time.sleep(1)
#                self._selenium.wait_until_page_contains_element(u"//div[@id='operationarea2']")
#                self.verbose_capture()
#        BuiltIn().log('Showed policy edit panel `%s`' % panel_name)


    @with_reconnect
    def show_policy_basic(self,policy_name):
        """ Makes the virtual browser show basic setting of the policy `name`.

        A following Samurai.`Capture Screenshot` is necessary to capture  the
        result.
        """
        self.left_menu(u"ポリシー管理")
        self._selenium.wait_until_page_contains_element("//input[@id='filter']")
        self._selenium.input_text("filter",policy_name)
        time.sleep(self._ajax_timeout)
        item_map = self.make_item_map("//tr/td[3]/div")
        item = item_map[policy_name]
        button = item.find_element_by_xpath(u"../../td/div/input[@title='編集']")
        self._selenium.wait_until_page_contains_element(button)
        self._selenium.click_element(button)
        time.sleep(1)
        self._selenium.wait_until_page_contains_element(u"//button[.='キャンセル']")
        self.verbose_capture()
        BuiltIn().log("Showed `basic setting` panel of the policy `%s`" % policy_name)


    @with_reconnect
    def show_policy_traffic(self,policy_name):
        """ Makes the virtual browser show the traffic setting of the policy `name`.

        A following Samurai.`Capture Screenshot` is necessary to capture  the
        result.
        """
        self.show_policy_basic(policy_name)
        panel_xpath = u"//a[starts-with(@class,'submenu_')]//span[normalize-space(.)='%s']" % u"Traffic設定"
        self._selenium.wait_until_page_contains_element(panel_xpath)
        self._selenium.click_element(panel_xpath)
        time.sleep(1)
        self._selenium.wait_until_page_contains_element(u"//button[.='キャンセル']")
        self.verbose_capture()
        BuiltIn().log("Showed `traffic setting` panel of the policy `%s`" % policy_name)


    @with_reconnect
    def show_policy_detection(self,policy_name):
        """Shows the detction pannel of `policy_name` policy
        """
        self.show_policy_basic(policy_name)
        panel_xpath = u"//a[starts-with(@class,'submenu_')]//span[normalize-space(.)='%s']" % u"Detection設定"
        self._selenium.wait_until_page_contains_element(panel_xpath)
        self._selenium.click_element(panel_xpath)
        time.sleep(1)
        self._selenium.wait_until_page_contains_element(u"//button[.='キャンセル']")
        self.verbose_capture()
        BuiltIn().log("Showed `detection setting` panel of the policy `%s`" % policy_name)


    @with_reconnect
    def show_policy_mitigation(self,policy_name):
        """ Make the virtual browser show the mitigation setting of a policy

        """
        self.show_policy_basic(policy_name)
        panel_xpath = u"//a[starts-with(@class,'submenu_')]//span[normalize-space(.)='%s']" % u"Mitigation設定"
        self._selenium.wait_until_page_contains_element(panel_xpath)
        self._selenium.click_element(panel_xpath)
        time.sleep(1)
        self._selenium.wait_until_page_contains_element(u"//button[.='キャンセル']")
        self.verbose_capture()
        BuiltIn().log("Showed mitigation setting of the policy `%s`" % policy_name)


    @with_reconnect
    def show_policy_mo(self,policy_name,strict=False):
        """ Make the virtual browser show the MO setting of a policy

        Automatically expand the MO section of other devices.
        *Notes*: Depending on the setting of the policy, MO panel may not be
        existed. In this case, if `strict` is ``True``, then the keyword will
        fail.
        """
        self.show_policy_basic(policy_name)
        panel_xpath = u"//a[starts-with(@class,'submenu_')]//span[normalize-space(.)='%s']" % u"TMS MO設定"
        if strict:
            self._selenium.wait_until_page_contains_element(panel_xpath)
        count = self._selenium.get_element_count(panel_xpath)
        if count > 0:
            self._selenium.click_element(panel_xpath)
            time.sleep(1)
            self._selenium.wait_until_page_contains_element(u"//button[.='キャンセル']")
            # self._selenium.wait_until_page_contains(u"TMS Managed Object設定")
            # not all device information is expanded yet
            mo_info = self._selenium.get_webelements(u"//div[starts-with(@id,'mo_')]")
            for item in mo_info:
                id = item.get_attribute('id')
                if not item.is_displayed():
                    self._selenium.execute_javascript("toggle_disp('%s','%s_img')" % (id,id))
            self.verbose_capture()
            BuiltIn().log("Showed mitigation setting of the policy `%s`" % policy_name)
        else:
            BuiltIn().log("WARN: no MO setting is found")


    @with_reconnect
    def show_policy_notify(self,policy_name):
        """ Make a virtual browser show the mitigation setting of a policy
        """
        self.show_policy_basic(policy_name)
        panel_xpath = u"//a[starts-with(@class,'submenu_')]//span[normalize-space(.)='%s']" % u"イベント通知設定"
        self._selenium.wait_until_page_contains_element(panel_xpath)
        self._selenium.click_element(panel_xpath)
        time.sleep(1)
        self._selenium.wait_until_page_contains_element(u"//input[@value='キャンセル']")
        self.verbose_capture()
        BuiltIn().log("Showed NW monitoring setting of the policy `%s`" % policy_name)


    def show_policy_monitor(self,policy_name):
        BuiltIn().log_to_console("WARN: `Show Policy Monitor` is deprecated. Use `Show Policy NW Monitor` keywod instead")
        return self.show_policy_nw_monitor(policy_name)


    @with_reconnect
    def show_policy_nw_monitor(self,policy_name,strict=False):
        """ Make a virtual browser show the NW monitor setting of a policy

        *Notes*: Depending on the setting of the policy, MO panel may not be
        existed. In this case, if `strict` is ``True``, then the keyword will
        fail.
        """
        self.show_policy_basic(policy_name)
        panel_xpath = u"//a[starts-with(@class,'submenu_')]//span[normalize-space(.)='%s']" % u"NW 監視設定"
        if strict:
            self._selenium.wait_until_page_contains_element(panel_xpath)
        count = self._selenium.get_element_count(panel_xpath)
        if count > 0:
            self._selenium.wait_until_page_contains_element(panel_xpath)
            self._selenium.click_element(panel_xpath)
            time.sleep(1)
            self._selenium.wait_until_page_contains_element(u"//button[.='キャンセル']")
            self.verbose_capture()
            BuiltIn().log("Showed NW monitoring setting of the policy `%s`" % policy_name)
        else:
            BuiltIn().log("WARN: no NW monitor setting is found")


    @with_reconnect
    def show_policy_display(self,policy_name):
        """ Make a virtual browser show the display setting of a policy

        *Notes*: Depending on the setting of the policy, MO panel may not be
        existed. In this case, if `strict` is ``True``, then the keyword will
        fail.
        """
        self.show_policy_basic(policy_name)
        panel_xpath = u"//a[starts-with(@class,'submenu_')]//span[normalize-space(.)='%s']" % u"閲覧設定"
        self._selenium.wait_until_page_contains_element(panel_xpath)
        self._selenium.click_element(panel_xpath)
        time.sleep(1)
        self._selenium.wait_until_page_contains_element(u"//button[.='キャンセル']")
        self.verbose_capture()
        BuiltIn().log("Showed NW monitoring setting of the policy `%s`" % policy_name)


    @with_reconnect
    def edit_policy(self,**policy):
        """ Edits a Samurai policy

        ``policy`` contains information about the policy. See `Add Policy` for
        more details about ``policy`` format
        """
        policy_name = policy['name']

        # basic
        changing = False
        self.show_policy_basic(policy_name)
        if 'basic_alias' in policy:
            changing = True
            self._selenium.input_text("alias_name1", policy['basic_alias'])
        if 'basic_cidr_list' in policy:
            changing = True
            cidr_list = [x.strip() for x in policy['basic_cidr_list'].split(',')]
            self._selenium.input_text("detection_cidr", '\n'.join(cidr_list))
        if 'basic_option_filter' in policy:
            changing = True
            self._selenium.input_text("option_filter", policy['basic_option_filter'])
            time.sleep(self._ajax_timeout)
        if 'basic_direction' in policy:
            changing = True
            if policy['basic_direction'].lower() in ['incoming', 'in'] :
                basic_direction = 'Incoming'
            else:
                basic_direction = 'Outgoing'
            self._selenium.select_from_list_by_label("direction",basic_direction)
        if changing:
            self.verbose_capture()
            self._selenium.click_button("submitbutton")
            self._selenium.wait_until_page_contains_element(u"//input[@value='戻る']")
            self._selenium.click_button(u'戻る')

        # traffic setting
        changing = False
        self.show_policy_traffic(policy_name)
        if 'traffic_enabled' in policy:
            changing = True
            if policy['traffic_enabled']:
                traffic_enabled = 'true'
            else:
                traffic_enabled = 'false'
            self._selenium.select_radio_button("traffic_enabled",traffic_enabled)
        if changing:
            changing = True
            self._selenium.click_button("submitbutton")
            self._selenium.wait_until_page_contains_element(u"//input[@value='戻る']")
            self._selenium.click_button(u'戻る')

        # detection setting
        changing = False
        self.show_policy_detection(policy_name)
        if 'detection_enabled' in policy:
            changing = True
            if policy['detection_enabled']:
                detection_enabled = 'true'
            else:
                detection_enabled = 'false'
            self._selenium.select_radio_button("misuse_enabled_flag",detection_enabled)
        if changing:
            self.verbose_capture()
            self._selenium.click_button("submitbutton")
            self._selenium.wait_until_page_contains_element(u"//input[@value='戻る']")
            self._selenium.click_button(u'戻る')

        # mitigation
        changing = False
        self.show_policy_mitigation(policy_name)
        if 'mitigation_auto_enabled' in policy:
            changing = True
            if policy['mitigation_auto_enabled']:
                mitigation_auto_enabled = "true"
            else:
                mitigation_auto_enabled = "false"
            self._selenium.select_radio_button("auto_enable",mitigation_auto_enabled)
        if 'mitigation_auto_stop_enabled' in policy:
            changing = True
            if policy['mitigation_auto_stop_enabled']:
                mitigation_auto_stop_enabled = "true"
            else:
                mitigation_auto_stop_enabled = "false"
            self._selenium.select_radio_button("auto_stop",mitigation_auto_enabled)
        if 'mitigation_zone_prefix' in policy:
            changing = True
            self._selenium.input_text("prefix0",policy['mitigation_zone_prefix'])
        if 'mitigation_thr_bps' in policy:
            changing = True
            self._selenium.input_text("thr_bps",policy['mitigation_thr_bps'])
        if 'mitigation_thr_pps' in policy:
            changing = True
            self._selenium.input_text("thr_pps",policy['mitigation_thr_pps'])
        if 'mitigation_mo_enabled' in policy:
            changing = True
            if policy['mitigation_mo_enabled']:
                mitigation_mo_enabled = 'true'
            else:
                mitigation_mo_enabled = 'false'
            self._selenium.select_radio_button("arbor_mo_enable",mitigation_mo_enabled)
        if 'mitigation_device_list' in policy:
            changing = True
            device_list = [x.strip() for x in policy['mitigation_device_list'].split(',')]
            table_map,selected_table_map = self.select_items_in_table('//tr/td[2]','../td[1]', *device_list)
        if changing:
            self.verbose_capture()
            self._selenium.click_button("submitbutton")
            self._selenium.wait_until_page_contains_element(u"//input[@value='戻る']")
            self._selenium.click_button(u'戻る')

        # TMS MO
        changing = False
        self.show_policy_mo(policy_name)
        if 'mitigation_mo_name' in policy:
            changing = True
            mo_name = policy['mitigation_mo_name']
            # not all device information is expanded yet
            mo_info = self._selenium.get_webelements(u"//div[starts-with(@id, 'mo_')]")
            for item in mo_info:
                id = item.get_attribute('id')
                if not item.is_displayed():
                    self._selenium.execute_javascript("toggle_disp('%s','%s_img')" % (id,id))
            items = self._selenium.get_webelements(u"//tr/td[2][.='%s']/../td[1]" % mo_name)
            for k in items: self._selenium.click_element(k)
        if changing:
            self.verbose_capture()
            self._selenium.click_button("submitbutton")
            self._selenium.wait_until_page_contains_element(u"//input[@value='戻る']")
            self._selenium.click_button(u'戻る')

        # NW monitoring
        # only Samurai > 16 has this panel
        # this panel not always be there
        changing = False
        self.show_policy_nw_monitor(policy_name)
        if ('nw_monitor_gre1' in policy) or ('nw_monitor_gre2' in policy):
            changing = True
            gre_elements = self._selenium.get_webelements('//input[contains(@id,"gre_addr")]')
            if 'nw_monitor_gre1' in policy:
                self._selenium.input_text(gre_elements[0],policy['nw_monitor_gre1'])
            if 'nw_monitor_gre2' in policy:
                self._selenium.input_text(gre_elements[1],policy['nw_monitor_gre2'])
        if ('nw_monitor_pe1' in policy) or ('nw_monitor_ce1' in policy):
            changing = True
            pe_elements = self._selenium.get_webelements('//select[contains(@name,"pe_id")]')
            if 'nw_monitor_pe1' in policy:
                self._selenium.select_from_list_by_label(pe_elements[0],policy['nw_monitor_pe1'])
            if 'nw_monitor_pe2' in policy:
                self._selenium.select_from_list_by_label(pe_elements[1],policy['nw_monitor_pe2'])
        if ('nw_monitor_ce1' in policy) or ('nw_monitor_ce2' in policy):
            changing = True
            ce_elements = self._selenium.get_webelements('//input[contains(@id,"ce_addr")]')
            if 'nw_monitor_ce1' in policy:
                self._selenium.input_text(ce_elements[0],policy['nw_monitor_ce1'])
            if 'nw_monitor_ce2' in policy:
                self._selenium.input_text(ce_elements[1],policy['nw_monitor_ce2'])
        if changing:
            self.verbose_capture()
            self._selenium.click_button("submitbutton")
            self._selenium.wait_until_page_contains_element(u"//input[@value='戻る']")
            self._selenium.click_button(u'戻る')

        BuiltIn().log("Changed setting for the policy `%s`" % policy_name)


    @with_reconnect
    def add_policy(self,**policy):
        """ Adds a new Samurai policy

        ``policy`` is a map containing the below information to create the new policy.
        | *key*     | *meaning*             | *mandatory* | *sample* |
        | name      | name of the policy    | yes | _test001_  |
        | basic_alias     | alias name of the policy |   | _test001_  |
        | basic_port_id   | another alias |  | |
        | basic_facing   | ``customer`` or ``backbone`` | | _customer_ |
        | basic_intf_list | list of router and interface pair, separated by comma | yes | _10.128.18.31:xe-0/0/0.1_ |
        | basic_cidr_list | list of CIDR separate by comma | | |
        | basic_option_filter | optinal filter | | |
        | basic_direction | direction of the traffic (``incoming`` or ``outgoing``) | | _incoming_ |
        | traffic_enabled | Enable traffic monitoring or not | yes | _${TRUE}_ or _${FALSE}_ |
        | detection_enabled | Enable detection or not | yes | _${TRUE}_ or _${FALSE}_ |
        | detection_direction | change detect direction fo all attack type | ``incomming`,``outgoing``,``both`` | _both:check_ |
        | mitigation_enabled | Enable Mitigation or not | yes | _${TRUE}_ or _${FALSE}_ |
        | mitigation_zone_name | Name of the zone for mitigation | | _zone001_ |
        | mitigation_zone_prefix | Prefixes that could mitigate | | _1.1.1.1/32_ |
        | mitigation_thr_bps | Upper limit (bps) | | _800,000,000_ |
        | mitigation_thr_pps | Upper limit (pps) | | _54,000,000_ |
        | mitigation_auto_enabled | Enable automitgation or not | | _${TRUE}_ or _${FALSE}_ |
        | mitigation_auto_level | Automitgation level  | | 0:overLow 1:overMedium 2:High |
        | mitigation_auto_time | Automitigation detect attack time (min) | | default is 15 |
        | mitigation_mo_enabled | Using Arbor TMS MO or not | yes | _${TRUE}_ or _${FALSE}_ |
        | mitigation_auto_stop_enabled | Enable automitgation stop or not | | _${TRUE}_ or _${FALSE}_ |
        | mitigation_auto_stop_level | Automitgation level  | | 0:overLow  2:High |
        | mitigation_auto_stop_time | Automitigation stop detect attack time (min) | | default is 15 |
        | mitigation_device_list | Devices used for TMS, separated by comma | | _ArborSP-A_ |
        | mitigation_mo_name     | MO name, separated by comma | | _OCN12(ALU)_LOOSE_ |
        | mitigation_comm_list   | commna separated peer/community list |   | _1.10(180.0.1.10)/2914:666,1.11(180.0.1.11)/2914:777_ |
        | nw_monitor_gre1 | 1st GRE address for NW monitor |  | _210.0.1.1_ |
        | nw_monitor_gre2 | 2nd GRE address for NW monitor |  | _210.0.1.1_ |
        | nw_monitor_ce1  | 1st CE address for NW monitor  |  | _210.0.1.2_ |
        | nw_monitor_ce2  | 2nd CE address for NW monitor  |  | _210.0.1.2_ |
        | nw_monitor_pe1  | 1st PE for NW monitor (list)   |  | _edge01hige-MX2020-15(118.23.176.244)_ |
        | nw_monitor_pe2  | 2nd PE for NW monitor (list)   |  | _edge01hige-MX2020-15(118.23.176.244)_ |
        | event_name  | name of the message event to make |  | _info1_ |
        | event_addr  | address to send the events      |  |  _user@mail.com_ |
        | view_group  | user group that could view this policy, separated by comma | yes | _SuperGroup,test_group_007_ |

        Example:
        | Samurai.`Switch`      | samurai-1 | |
        | Samurai.`Add Policy`  | name=${POLICY_NAME}        | basic_alias=${POLICY_NAME} |
        | ...                   | basic_facing=customer      | basic_intf_list=10.128.18.31:xe-0/0/0.1 |
        | ...                   | basic_cidr_list=1.1.1.0/24 | basic_direction=incoming |
        | ...                   | traffic_enabled=${TRUE} |
        | ...                   | detection_enabled=${TRUE} |
        | ...                   | mitigation_zone_name=test_zone001 | mitigation_zone_prefix=1.1.1.1/32 |
        | ...                   | mitigation_device_list=ArborSP-A,ArborSP-B |
        | ...                   | mitigation_mo_enabled=${TRUE} |
        | ...                   | mitigation_mo_name=N000000012_LOOSE |
        | ...                   | mitigation_comm_list=1.10(180.0.1.10)/2914:666,1.11(180.0.1.11)/2914:777 |
        | ...                   | event_name=test |        event_addr=user@mail.com |
        | ...                   | view_group=SuperGroup |

        *Note*: when there is no setting, `default values` (depending on the application) will be used.
        """

        # menu
        self.left_menu(u"ポリシー管理")

        traffic_enabled         = 'false'
        detection_enabled       = 'false'
        mitigation_enabled      = 'false'
        mitigation_mo_enabled   = 'false'

        # basic
        BuiltIn().log("### Basic setting ###")
        self._selenium.click_button(u"//input[@value='ポリシーの追加']")
        # if the policy number reached its limit, no more policy is addable

        self._selenium.wait_until_element_is_visible("policy_name")
        self._selenium.input_text("policy_name", policy['name'])
        if 'basic_alias' in policy:
            self._selenium.input_text("alias_name1", policy['basic_alias'])
        else:
            self._selenium.input_text("alias_name1", policy['name'])
        if 'basic_port_id' in policy:
            self._selenium.input_text("alias_name2", policy['basic_port_id'])
        if 'basic_facing' in policy:
            if policy['basic_facing'] == 'customer':
                customer_flag = 'true'
            else:
                customer_flag = 'false'
            self._selenium.select_from_list_by_value("customer_flag",customer_flag)
        intf_list = [x.strip() for x in policy['basic_intf_list'].split(',')]
        self._selenium.input_text("detection_interface", '\n'.join(intf_list))
        if 'basic_cidr_list' in policy:
            cidr_list = [x.strip() for x in policy['basic_cidr_list'].split(',')]
            self._selenium.input_text("detection_cidr", '\n'.join(cidr_list))
        if 'basic_option_filter' in policy:
            self._selenium.input_text("option_filter", policy['basic_option_filter'])
            time.sleep(self._ajax_timeout)

        basic_direction = 'Outgoing'
        if 'basic_direction' in policy and policy['basic_direction'].lower() in ['incoming', 'in'] :
                basic_direction = 'Incoming'
        self._selenium.select_from_list_by_label("direction", basic_direction)

        self.verbose_capture()
        self._selenium.click_button("submitbutton")
        self._selenium.wait_until_page_contains(u"ポリシーを追加しました。")
        self.verbose_capture()
        self._selenium.click_button(u"//button[.='進む']")

        # traffic setting
        BuiltIn().log("### Traffic setting ###")
        if policy['traffic_enabled']:   traffic_enabled = 'true'
        if traffic_enabled == 'true':
            self._selenium.select_radio_button("traffic_enabled",traffic_enabled)
        self.verbose_capture()
        self._selenium.click_button(u"//button[.='次へ']")

        # detection setting
        BuiltIn().log("### Detection setting ###")
        detection_enabled = 'false'
        if 'detection_enabled' in policy and policy['detection_enabled']:
            detection_enabled = 'true'
        self._selenium.select_radio_button("misuse_enabled_flag",detection_enabled)

        # clear all items by default
        # only check necessary
        if 'detection_direction' in policy and policy['detection_direction']:
            items = self._selenium.get_webelements("//td/input[contains(@id,'available')]")
            for item in items: self._selenium.unselect_checkbox(item)
            direction_config = policy['detection_direction'].lower()
            for config in direction_config.split(','):
                tmp = config.strip().split(':')
                direction = tmp[0]
                check = tmp[1]
                if direction == 'incoming':
                    items = self._selenium.get_webelements("//td[contains(.,'Incoming')]/input[contains(@id,'available')]")
                    for item in items:
                        if check == "check": self._selenium.select_checkbox(item)
                if direction == 'outgoing':
                    items = self._selenium.get_webelements("//td[contains(.,'Outgoing')]/input[contains(@id,'available')]")
                    for item in items:
                        if check == "check": self._selenium.select_checkbox(item)
                if direction == "both":
                    for item in items:
                        if check == "check": self._selenium.select_checkbox(item)
        self.verbose_capture()
        self._selenium.click_button(u"//button[.='次へ']")

        # mitigation
        mitigation_enabled =  'mitigation_enabled' in policy and policy['mitigation_enabled']
        if mitigation_enabled == 'true':
            BuiltIn().log("### Mitigation setting ###")
            self.verbose_capture()
            self._selenium.click_button("zoneaddbutton")
            self._selenium.input_text("zonename0",policy['mitigation_zone_name'])
            self._selenium.input_text("prefix0",policy['mitigation_zone_prefix'])
            if policy['mitigation_mo_enabled']:         mitigation_mo_enabled = 'true'
            self._selenium.select_radio_button("arbor_mo_enable",mitigation_mo_enabled)

            device_list = [x.strip() for x in policy['mitigation_device_list'].split(',')]
            table_map,selected_table_map = self.select_items_in_table("//tr/td[2]","../td[1]", *device_list)
            if 'mitigation_thr_bps' in policy:
                self._selenium.input_text("thr_bps",policy['mitigation_thr_bps'])
            if 'mitigation_thr_pps' in policy :
                self._selenium.input_text("thr_pps",policy['mitigation_thr_pps'])

            mitigation_auto_enabled = 'false'
            if 'mitigation_auto_enabled' in policy and policy['mitigation_auto_enabled']:
                    mitigation_auto_enabled = 'true'
            self._selenium.select_radio_button("auto_enable",mitigation_auto_enabled)

            mitigation_auto_level = "1" # default
            if 'mitigation_auto_level' in policy:
                if policy['mitigation_auto_level'].lower() in ['0','low']:
                    mitigation_auto_level = '0'
                if policy['mitigation_auto_level'].lower() in ['2','high']:
                    mitigation_auto_level = '2'
            self._selenium.select_radio_button("attack_lv",mitigation_auto_level)

            mitigation_auto_time = "15"
            if "mitigation_auto_time" in policy:
                mitigation_auto_time = policy['mitigation_auto_time']
            self._selenium.input_text("attack_ln",mitigation_auto_time)

            mitigation_auto_stop_enabled = 'false'
            if 'mitigation_auto_stop_enabled' in policy and policy['mitigation_auto_stop_enabled']:
                    mitigation_auto_stop_enabled = 'true'
            self._selenium.select_radio_button("auto_stop",mitigation_auto_stop_enabled)

            mitigation_auto_stop_level = "2" # default
            if 'mitigation_auto_stop_level' in policy:
                if policy['mitigation_auto_stop_level'].lower() in ['0','low']:
                    mitigation_auto_stop_level = '0'
            self._selenium.select_radio_button("stop_lv",mitigation_auto_stop_level)

            mitigation_auto_stop_time = "15"
            if "mitigation_auto_stop_time" in policy:
                mitigation_auto_stop_time = policy['mitigation_auto_stop_time']
            self._selenium.input_text("stop_ln",mitigation_auto_stop_time)


            if 'mitigation_comm_list' in policy:
                BuiltIn().log("### Diversion Community setting ###")
                for entry in [x.strip() for x in policy['mitigation_comm_list'].split(',')]:
                    tmp = entry.split('/')
                    peer = tmp[0].strip()
                    comm = tmp[1].strip()
                    if len(tmp) > 2:
                        check = tmp[2].strip()
                    else:
                        check = 'check'
                    if peer in table_map:
                        item = table_map[peer]
                        check_input = item.find_element_by_xpath("../td[1]/input")
                        comm_input =    item.find_element_by_xpath("../td[3]/input")
                        if check == 'check':
                            self._selenium.select_checkbox(check_input)
                        self._selenium.input_text(comm_input,comm)
        self.verbose_capture()
        self._selenium.click_button(u"//button[.='次へ']")

        # MO
        # When peers have been configured, there are no places to set community
        if mitigation_mo_enabled == 'true':
            BuiltIn().log("### MO setting ###")
            self._selenium.wait_until_page_contains_element(u"//b[.='TMS Managed Object設定']")
            mo_name = policy['mitigation_mo_name']
            # not all device information is expanded yet
            mo_info = self._selenium.get_webelements(u"//div[starts-with(@id, 'mo_')]")
            for item in mo_info:
                id = item.get_attribute('id')
                if not item.is_displayed():
                    self._selenium.execute_javascript("toggle_disp('%s','%s_img')" % (id,id))

            items = self._selenium.get_webelements(u"//tr/td[2][.='%s']/../td[1]" % mo_name)
            for k in items: self._selenium.click_element(k)
            self.verbose_capture()
            self._selenium.click_button(u"//button[.='次へ']")

        # Add more setting for Samurai16
        BuiltIn().log("### Monitoring setting ###")
        nw_monitor = self._selenium.get_element_count(u"//div[contains(.,'NW 監視設定')]")
        if nw_monitor > 0:
            if ('nw_monitor_gre1' in policy) or ('nw_monitor_gre2' in policy):
                gre_elements = self._selenium.get_webelements('//input[contains(@id,"gre_addr")]')
                self._selenium.input_text(gre_elements[0],policy['nw_monitor_gre1'])
                self._selenium.input_text(gre_elements[1],policy['nw_monitor_gre2'])
            if ('nw_monitor_pe1' in policy) or ('nw_monitor_ce1' in policy):
                pe_elements = self._selenium.get_webelements('//select[contains(@name,"pe_id")]')
                self._selenium.select_from_list_by_label(pe_elements[0],policy['nw_monitor_pe1'])
                self._selenium.select_from_list_by_label(pe_elements[1],policy['nw_monitor_pe2'])
            if ('nw_monitor_ce1' in policy) or ('nw_monitor_ce2' in policy):
                ce_elements = self._selenium.get_webelements('//input[contains(@id,"ce_addr")]')
                self._selenium.input_text(ce_elements[0],policy['nw_monitor_ce1'])
                self._selenium.input_text(ce_elements[1],policy['nw_monitor_ce2'])

            self.verbose_capture()
            self._selenium.click_button(u"//button[.='次へ']")

        # Notify
        BuiltIn().log("### Event setting ###")
        if 'event_name' in policy:
            self._selenium.wait_until_page_contains_element(u"//input[@value='メール通知の追加']")
            self.verbose_capture()
            self._selenium.click_button(u"//input[@value='メール通知の追加']")
            self._selenium.input_text("user_name",policy['event_name'])
            self._selenium.input_text("mail_address",policy['event_addr'])
            self.verbose_capture()
            self._selenium.click_button(u"//button[.='追加']")
            self._selenium.wait_until_page_contains(u"メール通知設定を追加しました")

        # View setting
        BuiltIn().log("### View setting ###")
        view_group_list = [x.strip() for x in policy['view_group'].split(',')]
        self.change_policy_view_group(policy['name'],*view_group_list)

        self.verbose_capture()
        BuiltIn().log("Added a Samurai policy named `%s`" % policy['name'])



    @with_reconnect
    def change_policy_view_group(self,name,*group_name):
        """ Changes the groups that could see this policy

        ``name`` is the policy name. ``group_name`` is a list of policies

        Example:
        | Samurai.`Change Policy View Group` | super_admin | test_group001 |
        """

        BuiltIn().log("Changing Policy View Group of the policy `%s`" % name)

        self.left_menu(u"ポリシー管理")
        self._selenium.input_text("filter",name)
        time.sleep(self._ajax_timeout)
        item_map = self.make_item_map("//tr/td[3]/div")
        item = item_map[name]
        button = item.find_element_by_xpath("../../td/div/input[@title='編集']")
        self._selenium.click_element(button)

        # view ( not check the case when there are multi groups over 1 page)
        self._selenium.click_element(u"//span[normalize-space(.)='閲覧設定']")
        #
        self._selenium.wait_until_page_contains_element("//tr/td[2]")

        item_map,result_map = self.select_items_in_table("//tr/td[2]","../td[1]",*group_name)
        for item in result_map:
            link = result_map[item].find_element_by_xpath(u"..//a[text()='すべてを選択']")
            self._selenium.click_element(link)

        self._selenium.click_button(u"//button[.='変更']")
        self._selenium.click_element(u"//span[contains(.,'閲覧設定を変更しました')]")

        # list current policies
        self.left_menu(u"ポリシー管理")
        BuiltIn().log("Changed the groups that could see this policy")


    @with_reconnect
    def delete_policy(self,*policy_names):
        """ Deletes poilcies by their names

        Returned the number of deleted users

        *Notes:* If the policy does not exists, the system will not report any error.

        Examples:
        | Samurai.`Delete Policy` | test001 | test002 |
        """
        # menu
        BuiltIn().log("Deleting policies")
        self.left_menu(u"ポリシー管理")

        all_items,selected_items = self.select_items_in_table('//tr/td[3]/div','../../td[1]',*policy_names)
        if len(selected_items) > 0:
            self._selenium.click_button(u"//input[@value='削除']")
            self._selenium.confirm_action()
            self._selenium.wait_until_page_contains_element(u"//span[contains(.,'ポリシーを削除しました')]")

        BuiltIn().log("Deleted %d/%d policies" % (len(selected_items),len(policy_names)))
        return len(selected_items)


    @with_reconnect
    def add_policy_group(self,group_name,policy_list="*",limit_bps="4000000000",limit_pps="2700000"):
        """ Add a new policy group

        ``group_name`` is the name of the new group. ``policy_list`` is a comma
        separated of existed policy that should be bound to this policy. An
        asterisk for this parameter (``*``) means `all of the existed policy`.
        ``limit_bps`` and ``limit_pps`` are the mitigation capacity threshold of
        this group.
        """
        # menu
        self.left_menu(u"ポリシーグループ管理")

        self._selenium.click_button(u"//input[@value='ポリシーグループの追加']")
        self._selenium.input_text("policy_group_name",group_name)

        count = 0
        if policy_list:
            if policy_list == "*" :
                item_list = self._selenium.get_webelements("xpath=//*[starts-with(@for,'label')]")
                count = len(item_list)
                self._selenium.click_link(u"すべてを選択")
            else :
                item_list = [x.strip() for x in policy_list.split(',')]
                for item in item_list:
                    self._selenium.click_element(u"//input[@id=//label[.='%s']/@for]" % item)
                count = len(item_list)

            self._selenium.click_button(u"//input[@value='追加']")
            self._selenium.page_should_contain_element(u"//span[contains(.,'ポリシーグループを追加しました')]")

        self.left_menu(u"ポリシーグループ管理")
        BuiltIn().log("Added policy group '%s' and bound it to %d policies" % (group_name,count))


    @with_reconnect
    def delete_policy_group(self,*group_list):
        """ Deletes policy groups

        See `Select Items In Table` for more detail about how to choose `group_list`

        Returns the number of deleted policy groups
        Example:
        | Samurai.`Delete Policy Group` | test_group001 | test_group002 |
        """
        # menu
        self.left_menu(u"ポリシーグループ管理")
        all_items,selected_items = self.select_items_in_table("//tr/td[3]","../td[1]",*group_list)
        if len(selected_items) > 0:
            self._selenium.click_button(u"//input[contains(@value,'削除')]")
            self._selenium.confirm_action()
            self._selenium.wait_until_page_contains_element(u"//span[contains(.,'ポリシーグループを削除しました')]")

        BuiltIn().log("Deleted %d policy groups" % len(selected_items))
        return len(selected_items)


    @with_reconnect
    def click_all_elements(self,xpath):
        """ Click all element in current page defined by ``xpath``

        Returns the number of elements that have been clicked
        """
        items = self._selenium.get_webelements(xpath)
        for item in items: self._selenium.click_element(item)

        BuiltIn().logs("Clicked %d items defined by xpath=`%s`" % (len(items),xpath))
        return len(items)


    @with_reconnect
    def show_detail_mitigation(self,id):
        """ Shows detail information of a mitigation
        """
        self.left_menu(u"Active Mitigation")
        self._selenium.wait_until_page_contains(u"Active Mitigation")
        self._selenium.click_link('%s' % id)
        time.sleep(5)
        self._selenium.select_window(u"title=リアルタイム詳細")
        self._selenium.wait_until_page_contains(u"適用フィルタ情報")

        BuiltIn().log("Showed detail of mitigation id `%s`" % id)


    def close_window():
        """ Closes the current window
        """
        self._selenium.close_window()
        time.sleep(2)
        BuiltIn().log("Closed the current window")


    @with_reconnect
    def select_window(self,title):
        """ Selects a window by its title
        """
        # self.switch(self._current_name)
        self._selenium.select_window(u"title=%s" % title)
        self._selenium.wait_until_page_contains(title)

        BuiltIn().log("Selected window `%s`" % title)


    @with_reconnect
    def get_mitigation_list(self,status=u'実行中'):
        """ Gets current mitigation list

        Return current active mitgation name, ID and the number of them

        Example:
        | ${MITI}  ${IDS}  ${NUM}=   |     Samurai.`Get Mitigation List` |
        """
        result = []
        result_ids = []
        self.left_menu(u"Active Mitigation")
        time.sleep(2)
        try:
            item_list = self._selenium.get_webelements("//div[@id='infoareain']//tr/td[2]")
            for item in item_list:
                item_status = item.find_element_by_xpath(u'../td[5]').text
                # BuiltIn().log_to_console(item_status)
                if item.text != u'ポリシー' and item_status == status:
                    result.append(item.text)
                    result_ids.append(item.find_element_by_xpath(u'../td[1]').text)

            BuiltIn().log("Got %d active mitigations has status %s" % (len(result),status))
        except Exception as err:
            BuiltIn().log("No active mitigations found")
        return result,result_ids,len(result)


    @with_reconnect
    def edit_mitigation_controller(self,controller,**config):
        """ Change the setting of the mitigation control

        - ``control``: name of the mitigation controller
        - ``config``: configuration need to be changed. Currently only
          ``tms_group`` is configurable with the following format:
            ``groupname1:action1,groupname2:action2``. ``groupname`` is
            currently set TMS group name and action could be `click`,`check` or `uncheck`.

        Example:
        | Samurai.`Edit Mitigation Controller` |  controller=vSP-A | tms_group=Logical0_SOCN_IPv4:uncheck |

        """
        self.left_menu(u"Mitigation Device管理")
        self._selenium.wait_until_page_contains_element("//div[@id='dataTable']")
        edit_button = self._selenium.get_webelement(u"//tr/td/div[translate(.,'\u200B','')='%s']/../../td[2]/div/input[@name='change']" % controller)
        self._selenium.click_button(edit_button)
        time.sleep(2)
        self._selenium.wait_until_page_contains_element("//button[@id='submitbutton']")
        if 'tms_group' in config:
            tmp = config['tms_group'].split(':')
            checkbox1 = u"//tr/td[.='%s']/../td[1]//input" % tmp[0]
            checkbox2 = u"//tr/td[.='%s']/../td[2]//input" % tmp[0]
            count1 = int(self._selenium.get_matching_xpath_count(checkbox1))
            if count1 > 0:
                check_box = self._selenium.get_webelement(checkbox1)
            else:
                check_box = self._selenium.get_webelement(checkbox2)
            if (tmp[1] == 'check' and not check_box.is_selected()) or (tmp[1] == 'uncheck' and check_box.is_selected()):
                self._selenium.click_element(check_box)


        self._selenium.click_button("submitbutton")
        self._selenium.wait_until_page_contains(u"Mitigationデバイス情報を変更しました")
        BuiltIn().log("Update mitigation controller setting")


    @with_reconnect
    def update_mitigation_controller_info(self,controller,wait=u'10s'):
        """ Updates information of `controller`
        """
        self.left_menu(u"Mitigation Device管理")
        self._selenium.wait_until_page_contains_element("//div[@id='dataTable']")
        # self.capture_screenshot()
        edit_button = self._selenium.get_webelement(u"//tr/td/div[translate(.,'\u200B','')='%s']/../../td[2]/div/input[@name='change']" % controller)
        self._selenium.click_button(edit_button)
        time.sleep(2)
        self._selenium.wait_until_page_contains_element("//button[@id='submitbutton']")
        self.mark_element("//form[@name='FORM_TMS']")
        self._selenium.click_button(u'TMS情報取得')
        time.sleep(DateTime.convert_time(wait))
        self._selenium.handle_alert()
        time.sleep(10)
        self.wait_until_element_changes()
        BuiltIn().log("Updated mitigation controller information")


