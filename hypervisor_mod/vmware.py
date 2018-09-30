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

# $Date: 2018-09-23 07:15:11 +0900 (Sun, 23 Sep 2018) $
# $Rev: 1348 $
# $Ver: $
# $Author: $

""" provides function for VMware ESXI

    Athough this module provides some keywords for interact with the console
    (WebConsole), they only suppport very primitive actions. Do not use this to
    accomplish complex tasks. Instead, using VChannel through a SSH/Telnet channel.
"""
import os,time,shutil,jinja2
import Common
import SSHLibrary
from pyVmomi import vim
from selenium import webdriver
from robot.libraries.BuiltIn import BuiltIn
import robot.libraries.DateTime as DateTime
from selenium.webdriver.common.keys import Keys

def _ssh_cmd(self,cmd):
    channel = self._channels[self._current_name]
    ssh = channel['ssh']
    logger = channel['ssh_logger']
    ssh.write(cmd)
    logger.write(cmd)
     
    result  = ssh.read_until_regexp(self._ssh_prompt)
    logger.write(result)
    logger.flush()

    if 'Invalid' in result:
        raise Exception('ERROR: %s' % result)
    BuiltIn().log('Run cmd `%s` on SSH channel of hypervisor `%s`' % (cmd,self._current_name))
    return result


def _get_vm(self,vm_name):
    """
    """
    conn = self._channels[self._current_name]['connection']
    content = conn.content
    vm_list = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    result = []
    target_vm = None
    for vm in vm_list.view:
        if (vm.name == vm_name):
            target_vm = vm
            break
    return target_vm

def get_vm_list(self):
    """ Returns current VM name list of the hypervisor
    """
    conn = self._channels[self._current_name]['connection']
    content = conn.content
    vm_list = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    result = []
    for vm in vm_list.view:
            result.append(vm.name)
    BuiltIn().log('Got VM list(%d)' % len(result))
    return result


def get_mks_ticket(self,vm_name):
    """ Returns a MSK ticket for WebConsole
    """
    target_vm = _get_vm(self,vm_name)
    ticket = target_vm.AcquireTicket('webmks').ticket
    BuiltIn().log('Got WebMKS ticket for `%s`' % vm_name)
    return ticket


def get_vm_id(self,vm_name):
    """ Returns a VMID of a VM
    """
    target_vm = _get_vm(self,vm_name)
    return target_vm._moId


def get_vm_power_state(self,vm_name):
    """ Get vm power status
    
    Return ``on`` of ``off``
    """
    state = 'on'
    target_vm = _get_vm(self,vm_name)
    cmd = 'vim-cmd vmsvc/power.getstate %s' % target_vm._moId
    output = _ssh_cmd(self,cmd)
    if 'Powered off' in output:
        state = 'off'
    return state

def power_on(self,vm_name):
    """ Power on a VM
    """
    target_vm = _get_vm(self,vm_name)
    cmd = 'vim-cmd vmsvc/power.on %s' % target_vm._moId
    output = _ssh_cmd(self,cmd)
    BuiltIn().log('Power on the VM `%s`' % vm_name) 

def power_off(self,vm_name,graceful=True):
    """ Shutdowns a VM

    If `graceful` is True, a graceful shutdown is tried before a power off.
    
    *Note*: if VMware tools is not install on the VM, graceful shutdown is not
    available
    """
    target_vm = _get_vm(self,vm_name)
    if graceful:
        cmd = 'vim-cmd vmsvc/power.shutdown %s' % target_vm._moId
        output = _ssh_cmd(self,cmd)
    
    if 'VMware Tools is not running' in output:
        cmd = 'vim-cmd vmsvc/power.off %s' % target_vm._moId
        output = _ssh_cmd(self,cmd)
   
    BuiltIn().log('Shutdown the VM `%s`' % vm_name) 

def send_mks_key(self,key,wait='1s'):
    """ Sends key strokes to current web console
   
    Special Ctrl char could be used as ``${CTRL_A}`` to ``${CTRL_Z}``

    Examples:
    | `Send MKS Key`   |     ${CTRL_L} |
    """ 
    driver = BuiltIn().get_library_instance('SeleniumLibrary')
    canvas = driver.get_webelement('mainCanvas')
    if len(key) == 1 and ord(key) < ord('@'):
        canvas.send_keys(Keys.CONTROL + chr(ord(key)+ord('@')))
    else:
        canvas.send_keys(key)
    time.sleep(DateTime.convert_time(wait))
    BuiltIn().log('Sent keystrokes to the web console')

def click_mks(self,xoffset,yoffset):
    """ Click on the MKS console at `xoffset`,`yoffset` coordinate
    
    *Notes*: The coordinate (0,0) is at the left corner of the console screen
    """
    driver = BuiltIn().get_library_instance('SeleniumLibrary')
    canvas = driver.get_webelement('mainCanvas')
    size = canvas.size
    x = int(xoffset) - int(size['width']/2) + 1
    y = int(yoffset) - int(size['height']/2) + 1
    driver.click_element_at_coordinates(canvas,x,y)
    BuiltIn().log('Clicked on the MKS console at (%s,%s)' % (xoffset,yoffset))


def send_mks_cmd(self,cmd,wait=u'2s'):
    """ Sends command to current web console and wait for a while

    By default, `wait` time is ``2s`` and the keyword will automaticall add a
    ``Newline`` char after sending the `cmd`
    """
    driver = BuiltIn().get_library_instance('SeleniumLibrary')
    driver.press_key('mainCanvas',cmd)
    driver.press_key('mainCanvas',"\\13")
    time.sleep(DateTime.convert_time(wait))
    BuiltIn().log('Sent command `%s` to web console' % cmd)


def capture_mks_screenshot(self,filename=None,extra=u''):
    """ Captures the current web console to `filename`
    
    If `filename` is ``None``, the captured filename will be decided by the
    current ``format`` with an auto-increment counter and a ``extra`` at the
    end.
    
    Example:
    | `Hypervisor`.Capture MKS Screenshot | # will create a file console_0000000001.png |
    | `Hypervisor`.Capture MKS Screenshot | xxx.png | # will create a file xxx.png |
    | `Hypervisor`.Capture MKS Screenshot | # will create a file console_0000000002.png |
    """
    channel = self._channels[self._current_name]
    if filename is None:
        counter = int(channel['capture_counter']) + 1
        format = channel['capture_format'] + extra + '.png'
        capture_name = format % counter
    else:
        capture_name = filename

    driver = BuiltIn().get_library_instance('SeleniumLibrary')
    driver.capture_page_screenshot(capture_name)
    channel['capture_counter'] = counter
    BuiltIn().log('Captured MKS screenshot by name `%s`' % capture_name)


def set_capture_format(self,format):
    """ Set console capture format

    Initialized format is ``'vmware_%010d'``
    """
    channel = self._channels[self._current_name]
    channel['capture_format'] = format
    BuiltIn().log('Set capture format str of `%s` to `%s`' % (self._current_name,format))
    

def reset_capture_counter(self):
    self._channels[self._current_name]['counter'] = 0
    BuiltIn().log('Reset capture counter of channel `%s` to 0' % self._current_name)


def _check_console_html(self):
    """ Check console in the current folder and create template
    """
    console_path = os.getcwd() + '/tmp/console'
    renat_path = os.environ['RENAT_PATH']
    if not os.path.exists(console_path):
        shutil.copytree(renat_path + '/tools/template/console', os.getcwd() + '/tmp/console')
        BuiltIn().log('Not found `console` folder, created it')
    else:
        BuiltIn().log('Found `console` folder, use it')


def open_console(self,vm_name,width=None,height=None):
    """ Opens a web console for a VM `vm_name`

    Returns the `width` and `height` of the console
    Examples:
    | Hypervisor.`Set Capture Format`  |  console_%010d |
    | `Open Console`    |    ${VM_NAME} |
    | Hypervisor.`Capture MKS Screenshot` |
    | `Send MKS Cmd`   |     root |
    | `Send MKS Cmd`   |     password |   wait=10s |
    | `Send MKS Cmd`   |     ls |
    | Hypervisor.`Capture MKS Screenshot` |
    | `Send MKS Key`   |     ${CTRL_L} |
    | `Send MKS Cmd`   |     whoami |
    | Hypervisor.Capture MKS Screenshot` |
    """
    server_ip = Common.GLOBAL['default']['robot-server']
    channel = self._channels[self._current_name]

    _check_console_html(self)

    current_folder = os.getcwd()
    ticket = self.get_mks_ticket(vm_name) 
    console_folder = '%s/tools/template/console' % os.environ['RENAT_PATH']

    render_var = {}
    loader=jinja2.Environment(loader=jinja2.FileSystemLoader(console_folder)).get_template('console.html')
    if width is None:
        render_var['WIDTH'] = Common.GLOBAL['default']['mks-console']['width']
    else:
        render_var['WIDTH'] = width
    if height is None:
        render_var['HEIGHT'] = Common.GLOBAL['default']['mks-console']['height']
    else:
        render_var['HEIGHT'] = height
        
    render_var['SERVER_IP'] = channel['ip']
    render_var['TICKET'] = ticket

    console_html = loader.render(render_var)
    console_file = '%s/tmp/console/console.html' % current_folder 
    
    with open(console_file,'w') as file:
        file.write(console_html)

    driver = BuiltIn().get_library_instance('SeleniumLibrary')
    driver.open_browser('file:///' + console_file)
    time.sleep(5)
    canvas = driver.get_webelement('mainCanvas')
    size = canvas.size
    width = size['width']
    height = size['height'] 
    BuiltIn().log('Opened a WebMSK console(%s,%s) to `%s`' % (width,height,vm_name))
    return width,height
