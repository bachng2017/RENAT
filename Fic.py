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
#
# $Date: 2019-09-07 09:51:32 +0900 (土, 07  9月 2019) $
# $Rev: 2204 $
# $Ver: $
# $Author: $

import io,os,time,re,traceback,shutil,cv2,tempfile,json,base64
from PIL import Image
from difflib import SequenceMatcher
import lxml.html
import Common
import numpy as np
from decorator import decorate
from WebApp import WebApp,with_reconnect,session_check
from robot.libraries.BuiltIn import BuiltIn
import robot.libraries.DateTime as DateTime
from robot.libraries.BuiltIn import RobotNotRunningError
from SeleniumLibrary import SeleniumLibrary
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.common.action_chains import ActionChains


class Fic(WebApp):
    """ Provides FIC SDP GUI keywords
    """

    ROBOT_LIBRARY_SCOPE = 'TEST SUITE'
    ROBOT_LIBRARY_VERSION = Common.version()

    GET_SCREEN_TEXT_1 = 1    
    GET_SCREEN_TEXT_2 = 2   

    def __init__(self):
        super(Fic,self).__init__()
        self._type = 'fic'
        self.tenant_id = ''        


    def get_canvas_image(self,filename=None):
        """ Returns ndarray format of the image of canvas element

        The resut is an image in BGR format
        """
        canvas_base64 = self._selenium.execute_javascript("return document.getElementsByTagName(\"canvas\")[0].toDataURL('image/png').substring(21);")
        canvas_png = base64.b64decode(canvas_base64)
        if filename:
            with open(filename, 'wb') as f:
                f.write(canvas_png)
        img_bin_stream = io.BytesIO(canvas_png)
        img_numpy = np.asarray(Image.open(img_bin_stream))
        return img_numpy
    
    def shake(self):
        """ Simulates a shake of the screen

        By shaking, the current topology information will be updated in
        browser's localstorage
        """
        # shake the screen once to update localstorage
        action = ActionChains(self._selenium.driver)
        element = self._selenium.get_webelement('//body')
        action.move_to_element_with_offset(element,0, 0).perform()
        action.move_to_element_with_offset(element,200,200).perform()
        action.click_and_hold(element).perform()
        action.move_by_offset(1,0).perform()
        action.move_by_offset(-1,0).perform()
        action.release().perform()
        self.refresh_canvas()
        BuiltIn().log("Shaked the canvas once")


    def slide_canvas(self,x=u"0",y=u"0"):
        """ Slides the screen by x,y pixel offset
        """
        action = ActionChains(self._selenium.driver)
        element = self._selenium.get_webelement('//body')
        action.move_to_element_with_offset(element,0, 0).perform()
        action.move_to_element_with_offset(element,200,200).perform()
        action.click_and_hold(element).perform()
        action.move_by_offset(int(x),int(y)).perform()
        action.release().perform()
        self.refresh_canvas()
        self.wait_until_loaded()
        BuiltIn().log("Slided the canvas by (%s,%s)" % (x,y))


    def connect(self,app,name):
        """ Connects to FIC GUI
        """
        self.open_ff_with_profile(app,name)
        auth = self._browsers[name]['auth']
        time.sleep(5)
        self.capture_screenshot()
        self._selenium.page_should_not_contain('Internal Error')
        self._selenium.page_should_not_contain('Internal Server Error')
        self._selenium.page_should_not_contain('Temporarily Unavailable')

        try: 
            self._selenium.page_should_not_contain('Session Timeout')
        except:
            BuiltIn().log("WRN: Found Session Timeout")
            self._selenium.reload_page()
        

        self._selenium.wait_until_element_is_visible('username')
        self._selenium.input_text('//input[@id="username"]', auth['username'])
        self._selenium.input_text('//input[@id="password"]', auth['password'])
        # self.capture_screenshot(extra='_before_submit')
        self._selenium.click_element('//input[@type="submit"]')

        time.sleep(15)

        # reload page if session is timed out
        error = Common.get_config_value('session-error','web') or "Session Timeout"
        if self._selenium.get_element_count(error) > 0:
            self._selenium.reload_page()

        self.capture_screenshot()
        self._selenium.page_should_not_contain('Internal Error')
        self._selenium.page_should_not_contain('Internal Server Error')
        self._selenium.page_should_not_contain('Temporarily Unavailable')
        self._selenium.page_should_not_contain('Session Timeout')

        self._selenium.wait_until_element_is_visible('//iframe[@id="cusval-content-main"]')
        self._selenium.select_frame("cusval-content-main")
        # after selecting frame, capture screenshot only return this frame
        self.tenant_id = self._browsers[name]['login_url'].strip().split('=')[1]
    
        local_storage = self._browsers[name]['local-storage'] 
        if local_storage:
            self.restore_localstorage(os.getcwd() + '/' + local_storage)

        # shake the screen once to update localstorage
        self.shake()
        BuiltIn().log("Connected to the application `%s` by name `%s`" % (app,name))        

    
    def move_to(self,x=u'0',y=u'0',delay=u'1s',element=u'//canvas',mark_screen=False):
        """ Moves the pointer to screen coodinate of the element

        Default element is `canvas`
        """
        action = ActionChains(self._selenium.driver)
        action.move_to_element_with_offset(self._selenium.get_webelement(element), 0, 0).perform()
        time.sleep(5)
        action.move_to_element_with_offset(self._selenium.get_webelement(element), int(x),int(y)).perform()
        time.sleep(DateTime.convert_time(delay))
        if mark_screen:
            BuiltIn().log("Marked to screen on (%d,%d)" % (x,y))
            img_file = self.capture_screenshot(extra='_move')
            img = cv2.imread(Common.get_result_path() + '/' + img_file)
            cv2.drawMarker(img, (int(x),int(y)), color=(0,255,0), markerType=cv2.MARKER_CROSS, thickness=2)
            cv2.imwrite(Common.get_result_path() + '/' + img_file,img)
        BuiltIn().log('Moved the pointer to (%d,%d)' % (x,y))


    def get_canvas_info(self):
        """ Get text info from info area
        """
        result = self._selenium.get_text('//div[@class="console-left-bottom"]')
        BuiltIn().log("Got text in info area as `%s`" % result)
        return result


    def click_on(self,point,element=u'//canvas',mark_screen=False):
        """ Click on a screen coordinate of an element

        Default element is `//cannvas`
        """
        x,y = point
        el = self._selenium.get_webelement(element)
        action = ActionChains(self._selenium.driver)
        action.move_to_element_with_offset(el,0,0).perform()
        action.move_to_element_with_offset(el,x,y).perform()
        if mark_screen:
            BuiltIn().log("Marked to screen on (%d,%d)" % (x,y))
            img_file = self.capture_screenshot(extra='_click')
            img = cv2.imread(Common.get_result_path() + '/' + img_file)
            cv2.drawMarker(img, (int(x),int(y)), color=(0,255,0), markerType=cv2.MARKER_CROSS, thickness=2)
            cv2.imwrite(Common.get_result_path() + '/' + img_file,img)
        action.click().perform()
        self.wait_until_loaded()
        BuiltIn().log("Clicked on element %s at (%d,%d)" % (element,x,y))


    def match_template(self,img,template,threshold=u"0.8"):
        """  Matches a template in an image using TM_CCOEFF_NORMED method

        Both `img` and `tempalte` are BGR ndarray object.
        The result is in the the center and boundary of the match.
        """
        _method = cv2.TM_CCOEFF_NORMED
        gray_img = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
        gray_template = cv2.cvtColor(template,cv2.COLOR_BGR2GRAY)
        w,h = gray_template.shape[::-1]

        res = cv2.matchTemplate(gray_img,gray_template,_method)
        loc = np.where(res >= float(threshold))
        if len(loc[0]) != 0 and len(loc[1]) != 0:
            min_val,max_val,min_loc,max_loc = cv2.minMaxLoc(res)
            if _method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                top_left = min_loc
            else:
                top_left = max_loc
            bottom_right = (top_left[0] + w, top_left[1] + h)
            mx = int((top_left[0] + bottom_right[0])/2)
            my = int((top_left[1] + bottom_right[1])/2)
            result = ((mx,my),(top_left[0],top_left[1],bottom_right[0],bottom_right[1]))
            BuiltIn().log("Found image at %s" % str(result))
        else:
            result = (None,None)
            BuiltIn().log("WRN: Could not found the template")
        return result


    def click_on_matched_template(self,template_name,max_trial=u"3"):
        """ Clicks on the matched template insides the canvas

        ``template_name`` is the filename of the template under the local ``config``
        folder
        """
        BuiltIn().log("Find and click on the template")
        template_path = Common.get_item_config_path() + '/' + template_name
        template = cv2.imread(template_path)
        found_template = False
        max_count = int(max_trial)
        count = 0
        while not found_template and (count < max_count):
            canvas = self.get_canvas_image()
            cpoint,_ = self.match_template(canvas,template)

            if not cpoint:
                self.capture_screenshot(extra="_match")
                self.reset_positions()
                self.refresh_canvas()
                count +=1
                BuiltIn().log("    Try to match one more time")
            else:
                found_template = True
        if found_template:
            self.click_on(cpoint)
            BuiltIn().log("Clicked on the matched template at (%d,%d)" % cpoint)
        else:
            raise Exception("ERR: Could not find the template")


    @session_check
    def close_datacenter(self):
        """ Closes the opening datacenter by click at X template at the upper right
        """
        self.click_on_matched_template('cancel_button.png')
        BuiltIn().log("Closed the data center")


    def get_element_image(self,element=u'//body',filename=None):
        """ Get and opencv image object of the element and save it to file

        Returns a numpy array and temporarily filename
        """
        result_path = Common.get_result_path()
        tmp_file = '%s/screen_%s.png' % (Common.get_result_path(),next(tempfile._get_candidate_names()))
        self._selenium.capture_page_screenshot(tmp_file)
        _element = self._selenium.get_webelement(element)
        pos = _element.location
        size = _element.size
        screen = cv2.imread(tmp_file)
        img = screen[int(pos['y']):int(pos['y']+size['height']),int(pos['x']):int(pos['x']+size['width'])]

        if filename:
            cv2.imwrite('%s/%s' % (result_path,filename),img)
        BuiltIn().log('Save image of element to file `%s`' % filename)
        return img,tmp_file


    @session_check
    def choose_left_menu(self,menu,delay=u"10s"):
        """ Selects FIC left menu

        Usable menus are: `Port`, `Router`, `Connection`, `History`
        """
        xpath = '//button[normalize-space(.)="%s"]' % menu
        self._selenium.mouse_over(xpath)
        time.sleep(3)
        self._selenium.click_element(xpath)
        time.sleep(DateTime.convert_time(delay))
        BuiltIn().log("Selected left menu `%s`" % menu)


    def refresh_canvas(self):
        xpath = '//i[normalize-space(.)="cached"]'
        self._selenium.wait_until_page_contains_element(xpath)
        # self._selenium.mouse_over(xpath)
        # time.sleep(5)
        # self._selenium.click_element(xpath)
        self._selenium.click_element_at_coordinates(xpath,5,5)
        time.sleep(5)
        self.wait_until_loaded()
        BuiltIn().log("Refreshed network topology")


    def failure(self):
        """ Common failure keyword
        """
        self.capture_screenshot(extra="_failure")
        self.close()    
        BuiltIn().log("A failure has been occured, quit the browser")


    def close(self):
        """ Logout and close the browser
        """
        # save the localstorage
        self.save_localstorage()
        self._selenium.unselect_frame()
        self._selenium.click_element('//body')

        # self.capture_screenshot(extra="_last")
        
        self.wait_and_click('//a[@class="dropdown-toggle user-name" and normalize-space(.)="fic-sys-ns"]')
        self._selenium.select_frame("cusval-content-main")
        self.wait_until_loaded()
        self._selenium.unselect_frame()
        self.wait_and_click('//a[@id="sss-logout"]') 

        time.sleep(5)
        self.capture_screenshot(extra="_last")
        super(Fic,self).close()
        BuiltIn().log("Logged out of the system")


    def wait_until_loaded(self,interval=u"5s",timeout=u"60s"):
        """ Waits until the loading icon disappear
        """
        BuiltIn().log("Wait until the page is loaded")
        on_progress = True
        time_max= DateTime.convert_time(timeout)
        t =  DateTime.convert_time(interval)
        timer = 0
        progress_div = '//div[@id="ficComApiProgress"]'
        div_count = self._selenium.get_element_count(progress_div)
        on_progress = (div_count > 0) 
        while on_progress and timer < time_max:
            div_count = self._selenium.get_element_count(progress_div)
            on_progress = (div_count > 0) 
            BuiltIn().log("    Wait for more `%d` seconds" % t)
            time.sleep(t)
            timer += t
        if timer >= time_max:
            BuiltIn().log("WRN: timeout occurr while wating for loading finishes")
        # time.sleep(t)
        
        BuiltIn().log("Waited for '%d' seconds until loading finsihed" % timer)


    def save_localstorage(self,path=None):
        """ Saves current local storage data to `path`
        """
        script = "return JSON.stringify(localStorage);"
        result = self._selenium.execute_javascript(script)
        if not path:
            path = Common.get_result_path() + '/.localstorage'
        with open(path,'w') as f:
            # BuiltIn().log_to_console(result)
            f.write(result)
        BuiltIn().log("Saved localstorage to file `%s`" % path)


    def reset_positions(self):
        """ Resets the localstorage information
        """
        script = '''
            localStorage.setItem("positions","");
        '''
        self._selenium.execute_javascript(script)
        BuiltIn().log("Cleared the position information in localstorage")


    def restore_localstorage(self,path=None):
        """ Restores localstorage data from file
        """
        script = '''
            var w = JSON.parse(arguments[0]);
            for (var i=0; i < localStorage.length; i++) {
                key = localStorage.key(0); 
                localStorage.setItem(key,w[key]);
            }
        '''
        if path and os.path.exists(path):
            with open(path) as f:
                s = f.read()
                # BuiltIn().log_to_console(s)
                result = self._selenium.execute_javascript(script,'ARGUMENTS',s)
            self.refresh_canvas()
            BuiltIn().log("Restored localstorage from file `%s`" % path)
        else:
            BuiltIn().log("WRN: could not find data file `%s`" % path)


    @session_check
    def choose_node(self,name,max_try=u"5"):
        """ Choose a node from canvas by its `name`

        `name` could be a REGEX pattern.
        """
        found_node = False
        count = 0
        max_count = int(max_try)
        while not found_node and count < max_count:
            # get canvas size 
            self.capture_screenshot(extra='_choose_node')
            img = self.get_canvas_image('canvas_choose_node.png')
            gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
            # _,binary = cv2.threshold(gray,63, 255, cv2.THRESH_BINARY)
            binary = cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,11,2)
            kernel = np.ones((4,8), np.uint8) 
            binary = cv2.dilate(binary, kernel, iterations=2)  
            binary = cv2.erode(binary, kernel, iterations=2)  
    
            found_node = False
            # ctrs,hier = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) 
            ctrs, hier = cv2.findContours(binary, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
            sorted_ctrs = sorted(ctrs, key=lambda ctr: cv2.boundingRect(ctr)[0])
            BuiltIn().log("Found %d candidates" % len(sorted_ctrs))
            for i,ctr in enumerate(sorted_ctrs):
                x,y,w,h = cv2.boundingRect(ctr)
                mx,my = int(x+w/2),int(y+h/2)
                self.move_to(mx,my)
                info = self.get_canvas_info()
                if info == name:
                    found_node = True
                    BuiltIn().log("Found node with name `%s`" % info)
                    self.click_on((mx,my),mark_screen=True)
                    break
            if not found_node:
                BuiltIn().log("Could not found the node. Refresh the screen once")
                count += 1
                self.reset_positions()
                self.refresh_canvas()
            
        if not found_node:
            raise Exception("Could not found the node after %d trials" % count)
        else:
            BuiltIn().log("Chose the node")    


    @session_check
    def click_button_menu(self,menu,delay=u'10s'):
        """ Clicks the `menu` button
        """
        xpath = '//button[normalize-space(.)="%s"]' % menu
        self._selenium.click_element(xpath)
        time.sleep(DateTime.convert_time(delay))
        BuiltIn().log('Clicked on FIC menu button `%s`' % menu) 


    @session_check
    def wait_and_click_button(self,text):
        """ Waits and clicks a button by its text

        Sample:
        | Wait and Click Button | OK |
        """
        self.capture_screenshot()
        xpath = '//button[normalize-space(.)="%s"]' % text
        self._selenium.wait_until_element_is_visible(xpath)
        self._selenium.click_element(xpath)

