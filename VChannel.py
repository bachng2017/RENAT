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

# $Rev: 1963 $
# $Ver: $
# $Date: 2019-04-01 09:28:05 +0900 (月, 01  4月 2019) $
# $Author: $

import os,re,sys
from decorator import decorate
import yaml
import jinja2,difflib
import pyte
import codecs
import time
import traceback
import telnetlib
import Common
import SSHLibrary
from robot.libraries.Telnet import Telnet
from robot.libraries.BuiltIn import BuiltIn
import robot.libraries.DateTime as DateTime
from paramiko import SSHException


### module methods
def _get_history(screen):
    return _get_history_screen(screen.history.top) + Common.newline


def _get_history_screen(deque):
    # the HistoryScreen.history.top is a StaticDefaultDict that contains
    # Char element.
    # The Char.data contains the real Unicode char
    return Common.newline.join(''.join(c.data for c in list(row.values())).rstrip() for row in deque)


def _get_screen(screen):
    return Common.newline.join(row.rstrip() for row in screen.display).rstrip(Common.newline)   


def _dump_screen(channel):
    if channel['screen']:
        return  _get_history(channel['screen']) + _get_screen(channel['screen'])
    return ''


def _log(channel,msg):
    """ log for a channel
    """
    # in case the channel has already has the logger
    if 'logger' in channel:
        logger      = channel['logger']
        separator   = channel['separator']
        if separator != "":
            if channel['screen']: logger.write(Common.newline)
            logger.write(Common.newline + separator + Common.newline)
        # remove some special control char before write to file
        escaped_msg = re.sub(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]','',msg) 
        logger.write(escaped_msg)
        logger.flush()


def _with_reconnect(keyword,self,*args,**kwargs):
    """ local method that provide a fail safe reconnect when read/write
    """
    max_count = int(Common.GLOBAL['default']['max-retry-for-connect'])
    interval  = DateTime.convert_time(Common.GLOBAL['default']['interval-between-retry'])
    count = 0
    while count < max_count:
        try:
            return keyword(self,*args,**kwargs)
        except (RuntimeError,EOFError,OSError,KeyError,SSHException) as err:
            BuiltIn().log('Error while trying keyword `%s`' % keyword.__name__)
            count = count + 1
            if count < max_count:
                BuiltIn().log('    Try reconnection %d(th) after %d seconds ' % (count,interval))
                BuiltIn().log_to_console('.','STDOUT',True)
                time.sleep(interval)
                self.reconnect(self._current_name)
            else:
                err_msg = "ERROR: error while processing command. Tunning ``terminal-timeout`` in RENAT config file or check your command"
                BuiltIn().log(err_msg)
                BuiltIn().log("ErrorType: %s" % type(err))
                BuiltIn().log("Detail error is:")
                BuiltIn().log(err)
                BuiltIn().log(traceback.format_exc())
                raise 

    
def with_reconnect(f):
    return decorate(f, _with_reconnect)


### 
class VChannel(object):
    """ A basic library that provides Terminal connection to routers/hosts
   
    ``VChannel`` is a core RENAT library that maintains input/output to nodes
    with an attached virtual terminal. It encapsulates the SSH/Telnet
    connections behind and provides common usage of access and execute commands
    to the nodes. Each channel instance has its own log file and a virtual
    terminal.

    == Table of Contents ==
    
    - `Device, Node and Channel`    
    - `Connections`
    - `Shortcuts`
    - `Keywords`

    = Device, Node and Channel =

    RENAT has 3 types of connection target. ``Device``, ``Node`` and
    ``Channel``. 
    == Device ==
    Each device stands for a real physical box that has its own IP address and
    is defined in the master file ``device.yaml``. Users do not directly use
    ``device`` in keywords.  
  
    == Node ==
    Node is a logical instance of a ``device``. It could stand for a logical
    instance of a router or just a virtual terminal to the router. Nodes were
    defined in ``local.yaml`` of the test case. Several nodes could point to a
    same device.

    == Channel ==
    Each channel holds a session to a node. Each channel has its own log file and a
    virtual terminal. Any command used by `Cmd`,`Write` or `Read` will be logged
    to the log file. Each channel is identified by a name when it is created
    with `Connect` keyword and is released with `Close` keyword.

    *Notes:* multi sessions to a same device could be done with predefined multi
    nodes to same device in the ``local.yaml`` file or by using multi `Connect` with
    different `name`.


    = Connections =
 
    The library provides a channel to a target node. Each channel is attached
    with a virtual terminal. Input and output to the node are made through 
    this virtual terminal. This will help to provide the output looks like the 
    output when operator is using the real terminal.

    When keywords `Read`, `Write`, `Cmd` are used, if the connection
    is not available anymore, the system will try to reconnect to the host with
    the information provided in the 1st connect. It will try
    ``max_retry_for_connect`` times and wait for ``interval_between_retry``
    seconds between retries. The values of ``max_retry_for_connect`` and
    ``interval_between_retry`` are defined in ``./config/config.yaml``

    Usually when RENAT could not make the connections to the target, the system
    will raise an exception. But if the ``ignore_dead_node`` is defined as
    ``yes`` in the current active ``local.yaml``, the system will ignore the dead
    node, remove it from the global variable ``LOCAL['node']`` and ``NODE`` and keep
    running the test.  
 
    """

    ROBOT_LIBRARY_SCOPE = 'TEST SUITE'
    ROBOT_LIBRARY_VERSION = Common.version()

    def __init__(self):
        # initialize instance of Telnet and SSH lib
        self._telnet = Telnet(timeout='3m')
        self._ssh = SSHLibrary.SSHLibrary(timeout='3m')
        self._current_id = 0
        self._current_name = None
        self._max_id = 0
        self._snap_buffer = {}
        self._channels = {}
        self._backup_channels = {}

    @property
    def current_name(self):
        return self._current_name

    def get_current_name(self):
        """ Returns the current active channel's name
        """
        return self._current_name

    def get_current_channel(self):
        """ Returns the current active channel
        """
        return self._channels[self._current_name]

    def get_channel(self,name):
        """ Returns a channel by its ``name``
        """
        return self._channels[name]

    def get_channels(self):
        """ Returns all current vchannel instances
        """
        return self._channels


    def _update_all(self):
        """ silently update all channels and flush their logs
        """
        for name in self._channels:
            try:
                channel = self._channels[name]
                if channel['screen']: continue
                output = channel['connection'].read() 
                _log(channel,output)
                channel['logger'].flush()
            except Exception as err:
                # BuiltIn().log(err)
                BuiltIn().log("WARN: error happend while update channel `%s` but is ignored" % name)


    def log(self,msg):
        """ Writes the log message ``msg`` to current log file of the channel
        """

        channel = self._channels[self._current_name]
        _log(channel,msg) 


    def set_log_separator(self,sep=""):
        """ Set a separator between the log of ``read``, ``write`` or
        ``cmd`` keywords
        """

        channel = self._channels[self._current_name]
        channel['separator'] = sep
 
    
    def reconnect(self,name):
        """ Reconnects to the ``name`` node using existed information 

        The only difference is that the mode of the log file is set to ```a+``` by default
        """
        BuiltIn().log("Reconnect to `%s`" % name)

        # remember the current channel name
        backup_channel = self._backup_channels[name]
        _node       = backup_channel['node']
        _name       = backup_channel['name']
        _log_file   = backup_channel['log-file']
        _w          = backup_channel['w'] 
        _h          = backup_channel['h'] 
        _mode       = backup_channel['mode'] 
        _timeout    = backup_channel['timeout']

        # reconect to the node. Appending the log
        if name in self._channels: 
            self._channels.pop(name)
            BuiltIn().log("    Removed `%s` from current channel" % name)
        self.connect(_node, _name, _log_file, _timeout, _w, _h, 'a+')

        # restore the current channel name
        # self._current_name = _curr_name

        # flush anything remained
        # self._channels[name]['logger'].flush() 
        # self.read()

        BuiltIn().log("Reconnected successfully to `%s`" % (name))
        

    def connect(self,node,name,log_file,\
                timeout=Common.GLOBAL['default']['terminal-timeout'], \
                w=Common.LOCAL['default']['terminal']['width'],\
                h=Common.LOCAL['default']['terminal']['height'],mode='w'):
        """ Connects to the node and create a VChannel instance

        Login information is automatically extracted from yaml configuration. 
        By defaullt a virtual terminal (vty100) with size 80x64 is attachted 
        to this channel. 

        If a login was successful, VChannel will create a log file name
        ``log_file`` for the connection in the current result folder of the test
        case. This log file will contain any command input/output executed on
        this channel.

        Multi sessions to the same node could be open with different names.
        Use `Switch` to change the current active session by its name

        Examples:
        | `Connect` | vmx11 | vmx11 | vmx11.log |
        | `Connect` | vmx11 | vmx11 | vmx11.log | 80 | 64 |

        See ``Common`` for more detail about the yaml config files.
        """

        # ignore or raise alarm when the initial connection has errors
        ignore_dead_node = Common.get_config_value('ignore-dead-node')
        id = 0

        if name in self._channels: 
            raise Exception("Channel `%s` already existed. Use different name instead" % name)
    
        _device         = Common.LOCAL['node'][node]['device']
        _device_info    = Common.GLOBAL['device'][_device]
        _ip             = _device_info['ip']
        _type           = _device_info['type']    
        _access_tmpl    = Common.GLOBAL['access-template'][_type] 
        _access         = _access_tmpl['access']
        _auth_type      = _access_tmpl['auth']
        _profile        = _access_tmpl['profile']
        
        if 'negotiate' in _access_tmpl:
            _negotiate  = _access_tmpl['negotiate']
        else:
            _negotiate  = None

        if 'proxy-cmd' in _access_tmpl:
            _proxy_cmd  = _access_tmpl['proxy-cmd']
        else:
            _proxy_cmd  = None
        if 'port' in _access_tmpl:
            _port = _access_tmpl['port']
        else:
            if 'port' in _device_info:
                _port = _device_info['port']
            else:
                _port = None

        # _prompt  = _access_tmpl['prompt'] + '$' # automatically append <dollar> to the prompt from yaml config 
        if 'prompt' in _access_tmpl:
            _prompt  = _access_tmpl['prompt']
        else:
            _prompt  = '.*'    
        # using strict prompt or not
        if Common.get_config_value('vchannel','prompt-strict'):
            if _prompt[-1] != '$': _prompt += '$'

        _auth  = Common.GLOBAL['auth'][_auth_type][_profile]
        if 'init' in _access_tmpl:
            _init  = _access_tmpl['init'] # initial command 
        else:
            _init = None
        if 'finish' in _access_tmpl:
            _finish = _access_tmpl['finish'] #finish  command 
        else:
            _finish = None
        _timeout        = timeout
        if 'login-prompt' in _access_tmpl: 
            _login_prompt = _access_tmpl['login-prompt']
        else:
            _login_prompt = Common.get_config_value('default-login-prompt','vchannel')
        if 'password-prompt' in _access_tmpl: 
            _password_prompt = _access_tmpl['password-prompt']
        else:
            _password_prompt = Common.get_config_value('default-password-prompt','vchannel')
        
        BuiltIn().log("Opening connection to `%s(%s):%s` as name `%s` by `%s`" % (node,_ip,_port,name,_access))
        

        try:
            channel_info = {}

            ### TELNET section
            ### _login_prompt could be None but not the _password_prompt
            if _access == 'telnet':
                output = ""
                s = str(w) + "x" + str(h)
                if _port is None: _port = 23
                local_id = self._telnet.open_connection(_ip,
                                                        port=_port, 
                                                        alias=name,terminal_type='vt100', window_size=s,
                                                        prompt=_prompt,prompt_is_regexp=True,
                                                    #    default_log_level="INFO",
                                                    #    telnetlib_log_level="TRACE",
                                                        timeout=_timeout)
                if _login_prompt is not None:
                    BuiltIn().log("Trying to login by username/password as `%s/%s`" % (_auth['user'],_auth['pass']))
                    output = self._telnet.login(_auth['user'],_auth['pass'], login_prompt=_login_prompt,password_prompt=_password_prompt)
                else:
                    BuiltIn().log("Trying to login only by password as `%s`" % _auth['pass'])
                    output = self._telnet.read_until(_password_prompt)
                    BuiltIn().log(output)
                    self._telnet.write(_auth['pass'])
                    output += Common.newline
                    output += self._telnet.read()
                    BuiltIn().log(output)
                
                # allocate new channel id
                id = self._max_id + 1
                channel_info['id']          = id 
                channel_info['type']        = _type
                channel_info['access-type'] = 'telnet'
                channel_info['prompt']      = _prompt 
                channel_info['connection']  = self._telnet
                channel_info['local-id']    = local_id
    
            ### SSH
            if _access == 'ssh':
                output = ""
                if _port is None: _port = 22
                local_id = self._ssh.open_connection(_ip,
                                                    port=_port,
                                                    alias=name,term_type='vt100',width=w,height=h,
                                                    timeout=_timeout,prompt="REGEXP:%s" % _prompt)
                # SSH with plaintext
                if _auth_type == 'plain-text':
                    if _proxy_cmd:
                        user        = os.environ.get('USER')
                        home_folder = os.environ.get('HOME')
                        if _port is None: 
                            port = 22
                        else:
                            port = _port
                        _cmd = _proxy_cmd.replace('%h',_ip).replace('%p',str(port)).replace('%u',user).replace('~',home_folder)
                        output = self._ssh.login(_auth['user'],_auth['pass'],proxy_cmd=_cmd)
                    else:
                        _cmd = None
                        output = self._ssh.login(_auth['user'],_auth['pass'])

                # SSH with publick-key
                if _auth_type == 'public-key':
                    if 'pass' in _auth:
                        pass_phrase = _auth['pass']
                    else:
                        pass_phrase = None
                    output = self._ssh.login_with_public_key(_auth['user'],_auth['key'],pass_phrase)
    
                # allocate new channel id
                id = self._max_id + 1
                channel_info['id']          = id 
                channel_info['type']        = _type
                channel_info['access-type'] = 'ssh'
                channel_info['prompt']      = _prompt
                channel_info['connection']  = self._ssh
                channel_info['local-id']    = local_id

            ### JUMP session
            if _access == 'jump':
                output = ""
                _access_base = _access_tmpl['access-base']

                # jump on telnet
                if _access_base == 'telnet':
                    s = str(w) + "x" + str(h)
                    local_id = self._telnet.open_connection(_ip,
                                                        port=_port, 
                                                        alias=name,terminal_type='vt100', window_size=s,
                                                        prompt=_prompt,prompt_is_regexp=True,
                                                        default_log_level="INFO",
                                                        telnetlib_log_level="TRACE",
                                                        timeout=_timeout)

                    # negotiate telnet session manually
                    cmd_ser1 = '\xff\xfc\x25' # i wont't authenticate
                    cmd_ser2 = '\xff\xfb\x00' # i will binary
                    # i do binary
                    # i will suppress go ahead
                    # i do suppress go ahead
                    # i do echo
                    # i don't 
                    cmd_ser3 = '\xff\xfd\x00\xff\xfb\x03\xff\xfd\x03\xff\xfd\x01\xff\xfe\xe8'
                    cmd_ser4 = '\xff\xfe\x2c' # i don't Com Port Control Option

                    if _negotiate:
                        BuiltIn().log("Negotiate telnet specs for this session MANUALLY")
                        self._telnet.write_bare(cmd_ser1)
                        time.sleep(1)
                        self._telnet.write_bare("\r")
                        time.sleep(1)
                        self._telnet.write_bare("\r")
                        time.sleep(1)
                        output = self._telnet.read()
                        # BuiltIn().log("--buf(%d)------" % len(output))
                        # BuiltIn().log(output)
                        # BuiltIn().log("---------------")
                       
                        if len(output) == 0: 
                            self._telnet.write_bare(cmd_ser1)
                            time.sleep(1)
                            self._telnet.write_bare(cmd_ser2)
                            time.sleep(1)
                            self._telnet.write_bare(cmd_ser3)
                            time.sleep(1)
                            self._telnet.write_bare(cmd_ser4)
                            time.sleep(3)

                    if _login_prompt is not None:
                        BuiltIn().log("Trying to login by username/password as `%s/%s`" % (_auth['user'],_auth['pass']))
                        output = self._telnet.login(_auth['user'],_auth['pass'], login_prompt=_login_prompt,password_prompt=_password_prompt)
                    else:
                        if _password_prompt is not None:
                            BuiltIn().log("Trying to login only by password as `%s`" % (_auth['pass']))
                            output = self._telnet.read_until_regexp(_password_prompt)
                            self._telnet.write(_auth['pass'])
                        else:
                            BuiltIn().log("WARN: Access jump server withouth authentication")
                            # self._telnet.write_bare("\r")
                            # time.sleep(1)
                            # output = self._telnet.read()
                            # BuiltIn().log(output)
                            
                    # allocate new channel id
                    id = self._max_id + 1
                    channel_info['id']          = id 
                    channel_info['type']        = _type
                    channel_info['access-type'] = 'telnet'
                    channel_info['prompt']      = _prompt 
                    channel_info['connection']  = self._telnet
                    channel_info['local-id']    = local_id

                # jump on ssh
                if _access_base == 'ssh':
                    out = ""
                    local_id = self._ssh.open_connection(_ip,alias=name,term_type='vt100',width=w,
                                                        height=h,timeout=_timeout,
                                                        prompt="REGEXP:%s" % _prompt)
                    # SSH with plaintext
                    if _auth_type == 'plain-text':
                        if _proxy_cmd:
                            user        = os.environ.get('USER')
                            home_folder = os.environ.get('HOME')
                            if _port is None: 
                                port = 22
                            else:
                                port = _port
                            _cmd = _proxy_cmd.replace('%h',_ip).replace('%p',str(port)).replace('%u',user).replace('~',home_folder)
                            out = self._ssh.login(_auth['user'],_auth['pass'],proxy_cmd=_cmd)
                        else:
                            _cmd = None
                            output = self._ssh.login(_auth['user'],_auth['pass'])
    
                    # SSH with publick-key
                    if _auth_type == 'public-key':
                        if 'pass' in _auth:
                            pass_phrase = _auth['pass']
                        else:
                            pass_phrase = None
                        output = self._ssh.login_with_public_key(_auth['user'],_auth['key'],pass_phrase)

                    # allocate new channel id
                    id = self._max_id + 1
                    channel_info['id']          = id 
                    channel_info['type']        = _type
                    channel_info['access-type'] = 'jump'
                    channel_info['prompt']      = _prompt
                    channel_info['connection']  = self._ssh

                # execute JUMP cmd
                if 'jump-cmd' in _device_info:
                    for item in _device_info['jump-cmd']:
                        channel_info['connection'].write(str(item)+'\r')
                        time.sleep(2)
                        output = channel_info['connection'].read()

                # at this point, the system is waiting for the second login
                # phase. The status could be already login
                BuiltIn().log("Jump to other device")

                _target_name        = _access_tmpl['target']
                _target_tmpl        = Common.GLOBAL['access-template'][_target_name] 
                _target_auth_type   = _target_tmpl['auth']
                _target_profile     = _target_tmpl['profile']
                _target_auth        = Common.GLOBAL['auth'][_target_auth_type][_target_profile]

                _prompt = _target_tmpl['prompt']
                _login_prompt = Common.get_config_value('default-login-prompt','vchannel')
                _password_prompt = Common.get_config_value('default-password-prompt','vchannel')
 
                if 'login-prompt' in _target_tmpl:      _login_prompt       = _target_tmpl['login-prompt']
                if 'password-prompt' in _target_tmpl:   _password_prompt    = _target_tmpl['password-prompt']
                if 'init' in _target_tmpl:               _init              = _target_tmpl['init']
                if 'finish' in _target_tmpl:            _finish             = _target_tmpl['finish']
                if 'timeout' in _target_tmpl:           _timeout            = _target_tmpl['timeout']

                # update channel and authentication info
                channel_info['prompt']  = _prompt
                _auth = _target_auth

                # authentication to the target device
                BuiltIn().log("------------")
                BuiltIn().log("--%s--" % output)
                BuiltIn().log("------------")
                if re.search('Press RETURN to get started',output):
                    channel_info['connection'].write("\r")
                    time.sleep(3)
                    
                if _login_prompt and re.search(_login_prompt,output):
                    BuiltIn().log("Login to target device with username `%s`" % _auth['user'])
                    channel_info['connection'].write(_auth['user'])
                    time.sleep(3)
                    output = channel_info['connection'].read()
                    BuiltIn().log("------------")
                    BuiltIn().log("--%s--" % output)
                    BuiltIn().log("------------")
                
                if _password_prompt and re.search(_password_prompt,output):
                    BuiltIn().log("Login to target device with password `%s`" % _auth['pass'])
                    channel_info['connection'].write(_auth['pass'])
                    time.sleep(3)
                 
                BuiltIn().log("Wait for the 1st prompt")
                channel_info['connection'].write("\r")
                time.sleep(3)
                channel_info['connection'].write("\r")
                time.sleep(1)
                channel_info['connection'].read_until_regexp(_prompt)

            # common for all access type
            # open/create a log file for this connection in result_folder
            result_folder = Common.get_result_folder()
            if log_file == '':
                channel_info['logger']  = None
            else:
                channel_info['logger']  = codecs.open(result_folder + "/" + log_file,mode,'utf-8')
    
            # common channel info
            channel_info['node']        = node
            channel_info['name']        = name
            channel_info['log-file']    = log_file
            channel_info['w']           = w
            channel_info['h']           = h
            channel_info['mode']        = mode
            channel_info['timeout']     = _timeout
            channel_info['auth']        = _auth
            channel_info['ip']          = _ip
            channel_info['separator']   = ""
            channel_info['finish']      = _finish
            channel_info['timeout']     = timeout
       
            # extra 
            channel_info['screen']      = None
            channel_info['stream']      = None
            self._current_id            = id
            self._max_id                = id
            self._current_name          = name
        
            # remember this info by name(alias)
            self._channels[name]   = channel_info 
            self._backup_channels[name] = channel_info
    
            # by default switch to the connected device
            self.switch(name)

            # logging the authentication process until now
            BuiltIn().log(output)
            self.log(output)

            # activate ENABLE mode
            # the device might bi in ENABLE mode already
            if 'secret' in _auth:
                BuiltIn().log("Entering ENABLE mode")
                self.cmd()
                output = self.cmd('enable',prompt=r"Password:|%s" % _prompt)
                if "Password:" in output: self.cmd(_auth['secret'])

            ### execute 1st command after login
            flag = Common.get_config_value('ignore-init-finish','vchannel',False)
            if not flag and _init is not None: 
                for item in _init: 
                    BuiltIn().log("Executing init command: %s" % (item))
                    self.cmd(item)

            BuiltIn().log("Opened connection to `%s(%s)`" % (name,_ip))
        except Exception as err:
            if not ignore_dead_node: 
                err_msg = "ERROR: Error occured when connecting to `%s(%s)`" % (name,_ip)
                BuiltIn().log(err_msg)
                # BuiltIn().log_to_console(err_msg)
                raise 
            else:
                warn_msg = "WARN: Error occured when connect to `%s(%s)` but was ignored" % (name,_ip)
                
                BuiltIn().log(warn_msg)
                BuiltIn().log_to_console(warn_msg)
                del Common.LOCAL['node'][name]

        return id

    
    def connect_all(self,prefix=""):
        """ Connects to *all* nodes that are defined in active ``local.yaml``. 

        A prefix ``prefix`` was appended to the alias name of the connection. A
        new log file by ``<alias>.log`` was automatiocally created.

        See `Common` for more detail about active ``local.yaml``
        """

        if 'node' in Common.LOCAL and not Common.LOCAL['node']: 
            num = 0
        else:  
            num = len(Common.LOCAL['node'])
            for node in Common.LOCAL['node']:
                alias       = prefix + node
                log_file    = alias + '.log'
                self.connect(node,alias,log_file)   
        BuiltIn().log("Connected to all %s nodes defined in ``conf/local.yaml``" % (num))


    ###
    def start_screen_mode(self):
        """ Starts the ``screen mode``. 

        In the ``screen mode``, the output is just the same with the real terminal. It 
        means that any real-time application likes ``top`` will be captured as-is. 
        Consecutive `read` from this VChannel instance may produce redundancy ouput.
        """
        channel = self._channels[self._current_name]
        channel['screen'] = pyte.HistoryScreen(channel['w'], channel['h'],100000)
        channel['stream'] = pyte.Stream()
        channel['stream'].attach(channel['screen'])
        # handle different version of pyte
        try:
            channel['screen'].set_charset('B', '(')
        except:
            channel['screen'].define_charset('B', '(')

        BuiltIn().log("Started ``screen mode``")

  
    def stop_screen_mode(self):
        """ Stops the ``screen mode`` and returns to ``normal mode``
        
        In ``screen mode``, `Write` does not return any thing and no output is logged.
        In ``normal mode``, escape sequences are not processed by the virtual terminal.
        
        """
        channel = self._channels[self._current_name]
        if channel['screen']:
            channel['screen'] = None
            channel['stream'] = None 
        
        BuiltIn().log("Stopped ``screen mode`` of channel `%s`" % self._current_name)


    def _get_history(self, screen):
        # the HistoryScreen.history.top is a StaticDefaultDict that contains
        # Char element.
        # The Char.data contains the real Unicode char
        return Common.newline.join(''.join(c.data for c in list(row.values())).rstrip() for row in screen.history.top) + Common.newline


    def _get_screen(self, screen):
        return Common.newline.join(row.rstrip() for row in screen.display).rstrip(Common.newline)   


    def _dump_screen(self):
        channel = self._channels[self._current_name]
        if channel['screen']:
            return  self._get_history(channel['screen']) + self._get_screen(channel['screen'])
        return ''

    @with_reconnect 
    def switch(self,name):
        """ Switches the current active channel to ``name``. 
        There only one active channel at any time

        Returns the current `channel_id`, `local_channel_id` and the output of
        current terminal.

        *Notes:* There is no assurance that the output of previous `Write`
        command will be in the retur output because keywords like
        Logger.`Log All` will update every channels.
    
        Examples:
        | VChannel.`Switch` | vmx12 | 
        """
        BuiltIn().log('Switching current vchannel to `%s`' % name)
        old_name = self._current_name

        output = ""
        if name in self._channels: 
            self._current_name = name
            channel_info = self._channels[name]
            self._current_id = channel_info['id']

            channel_info['connection'].switch_connection(channel_info['local-id'])
            if channel_info['screen']:
                # read from the session and log the result
                channel_info['stream'].feed(channel_info['connection'].read())
                try:
                    output = _dump_screen(channel_info) + Common.newline
                except UnicodeDecodeError as err:
                    BuiltIn().log('ERROR: Unicode error in read output')
                    output = err.args[1].decode('utf-8','replace')
            else:
                try:
                    output = channel_info['connection'].read() 
                except UnicodeDecodeError as err:
                    output = err.args[1].decode('utf-8','replace')
            _log(channel_info,output)
            if 'logger' in channel_info: channel_info['logger'].flush()

            BuiltIn().log("Switched current channel to `%s(%s)`" % (name,channel_info['ip']))
            return channel_info['id'], channel_info['local-id'], output
        else:
            err_msg = "ERROR: Could not find `%s` in current channels" % name
            BuiltIn().log(err_msg)
            raise Exception(err_msg)


    def change_log(self,log_file,mode='w'):
        """ Stops current log file and create a new log file. 

        Default `mode` is `w` which overwrite the existed logs. Change to `a` or
        `a+` to append the current existed log files.
   
        Every log from that point will be saved to the new log file.

        Return old log filename
        """
        channel = self._channels[self._current_name]
        old_log_file = channel['log-file']

        # flush buffer before change the log file
        channel['logger'].flush()
        channel['logger'].close()
    
        result_path = Common.get_result_path() 
        channel['logger'] = codecs.open(result_path+'/'+log_file,mode,'utf-8') 
        channel['log-file'] = log_file

        BuiltIn().log("Changed current log file to %s" % log_file)
        return old_log_file


    @with_reconnect
    def write(self,str_cmd=u"",str_wait=u'0s',start_screen_mode=False):
        """ Sends ``str_cmd`` to the target node and return after ``str_wait`` time. 

        If ``start_screen_mode`` is ``True``, the channel will be shifted to ``Screen
        Mode``. Default value of ``screen_mode`` is False.

        In ``normal mode``, a ``new line`` char will be added automatically to
        the ``str_cmd`` and the command return the output it could get at that time from
        the terminal and also logs that to the log file. 

        In ``screen Mode``, if it is necessary you need to add the ``new line``
        char by your own and the ouput is not be logged or returned from the keyword.

        Parameters:
        - ``str_cmd``: the command
        - ``str_wait``: time to wait after apply the command
        - ``start_screen_mode``: whether start the ``screen mode`` right after
          writes the command

        Special input likes Ctrl-C etc. could be used with global variable ${CTRL-<char>}

        Returns the output after writing the command the the channel.

        When `str_wait` is not `0s`, the keyword ``read`` and ``return the
        output`` after waiting `str_wait`. Otherwise, the keyword return
        without any output.
   
        *Notes:*  This is a non-blocking command.

        Examples:
        | VChannel.`Write` | monitor interface traffic | start_screen_mode=${TRUE} |
        | VChannel.`Write` | ${CTRL_C} | # simulates Ctrl-C |
        
        """
        result = ""
        wait = DateTime.convert_time(str_wait)
        channel = self._channels[self._current_name]
        is_screen_mode = (channel['screen'] is not None)
        display_cmd = str(str_cmd).replace(Common.newline,'<Enter>')
        
        BuiltIn().log("Write '%s', screen_mode=`%s`" % (str_cmd,is_screen_mode))
        if start_screen_mode:
            # channel['screen'] becomes valid after
            self.start_screen_mode()
            # because we've just start the screen mode but the node has not yet
            # be in screen mode, a newline is necessary here

            # cmd = str_cmd + Common.newline
            # tricky hack assuming that the system only receive the 1st char in
            # defined by `newline` item in global/config.yaml
            # There are some systems do not allow 2 char likes `\r\n`
            cmd = str_cmd + Common.newline[0]
        else:
            cmd = str_cmd

        if channel['screen']:
            self.read()     # get if something remains in the buffer
            BuiltIn().log('Write directly to session: `%s`' % display_cmd)
            channel['connection'].write_bare(cmd)
            self.log(cmd)
            if wait > 0:
                time.sleep(wait)
                result = self.read()
        else:
            # by default, always add a `newline` to the cmd
            # channel['connection'].write_bare(cmd + Common.newline)
            channel['connection'].write_bare(cmd + "\r")
            if wait > 0:
                time.sleep(wait)
                result = self.read()
            else:
                # self.log(cmd + Common.newline)
                # pass
                time.sleep(1)
                result = self.read()

        BuiltIn().log("Wrote '%s', screen_mode=`%s`" % (str_cmd,is_screen_mode))
        return result


    def current_prompt(self):
        """ Return current prompt
        """
        prompt = self._channels[self._current_name]['prompt']
        BuiltIn().log('Got current prompt `%s`' % prompt)
        return prompt


    def change_prompt(self,str_prompt):
        """ Changes the current prompt of the channel

        Returns previous prompt. User should change the prompt ``before`` execute the new command that
        expects to see new prompt.

        Example:
        | Router.`Switch`           | vmx11 |
        | ${prompt}=                | VChannel.`Change Prompt`  |    % |
        | VChannel.`Cmd`            | start shell |
        | VChannel.`Cmd`            | ls |
        | VChannel.`Change Prompt`  | ${prompt} |
        | Vchannel.`Cmd`            | exit  |

        """
        current_channel = self._channels[self._current_name]
        old_prompt      = current_channel['prompt']
        current_channel['prompt'] = str_prompt

        BuiltIn().log("Changed current prompt to `%s`" % (str_prompt))
        return  old_prompt
        

#        # experimentally implement VChannel without using prompt
#        result = ''
#        old_output = ''
#        count = 0
#        output  = channel['connection'].read()
#        while count < 3:
#            # BuiltIn().log_to_console("***" + result + "***")
#            result = result + output
#            old_output = output
#            output  = channel['connection'].read()
#            if output == old_output: 
#                count = count + 1
#                time.sleep(1)
#            else:
#                count = 0
#        self.log(result)
#    
#        return result

    def cmd_more(self,cmd=u'',wait_prompt=u'.*---\(more.*\)---',press_key=u' ',prompt=None):
        """ Execute a command and press `press_key` when `wait_prompt` is
        displayed until the prompt
        """
        BuiltIn().log("Execute command: `%s` and wait until prompt" % cmd)
        output = ''
        channel = self._channels[self._current_name]
        if channel['screen']: raise Exception("``Cmd`` keyword is prohibitted in ``screen mode``")
        # in case something left in the buffer
        output  = channel['connection'].read()
        self.log(output)
        
        channel['connection'].write(cmd)
        self.log(cmd + Common.newline)

        default_prompt  = channel['prompt']
        if prompt is None :    
            last_prompt = default_prompt
            cur_prompt = '.*(%s|%s)' % (default_prompt,wait_prompt)
        else:
            last_prompt = '.*%s' % prompt
            cur_prompt = '.*(%s|%s)' % (prompt,wait_prompt)
        output = '' 
        BuiltIn().log('prompt = %s' % cur_prompt)
        while True:
            output = channel['connection'].read_until_regexp(cur_prompt)
            self.log(output)
            if re.match('.*' + last_prompt,output,re.DOTALL): break
            BuiltIn().log('Continue...')
            self.write(' ')
            time.sleep(1)
        
        BuiltIn().log("Executed command: `%s` and wait until prompt")


    
    def _set_conn_timeout(self,conn,timeout): 
        """ Set current connection timeout
        """
        if timeout is None: return
        if hasattr(conn,'set_timeout'): conn.set_timeout(timeout)
        if hasattr(conn,'set_client_configuration'): conn.set_client_configuration(timeout=timeout)


    @with_reconnect
    def cmd(self,command='',prompt=None,
            timeout=None,error_on_timeout=True,
            remove_prompt=False,
            match_err='\r\n(unknown command.|syntax error, expecting <command>.)\r\n'):
        """Executes a ``command`` and wait until for the prompt. 
  
        This is a blocking keyword. Execution of the test case will be postponed until the prompt appears.

        If ``prompt`` is a null string (default), its value is defined in the
        ``./config/template.yaml``.  Otherwise, it is a regular expression for a
        temporarily prompt for this command only.

        `timeout` is the timeout for this `Cmd`. If `timeout` is not define, the
        local `vchannel/cmd-timeout` or global `vchannel/cmd-timeout` will be
        used.

        The keyword returns error when the output matches the ``match_err`` and
        the default config value `cmd-auto-check` is ``True``

        When `remove_prompt` is ``${TRUE}``, the last line (usually the prompt
        line) will be remove from the return value. But still in this case, the log
        information is unchanged.

        Output will be automatically logged to the channel current log file.

        See [./Common.html|Common] for details about the config files.

        Sample:
        | Router.Cmd   | version |
        | Router.Cmd   | reload   | prompt=\\[yes/no\\]:${SPACE} | # reload a Cisco router |
        | Router.Cmd   | no       | prompt=\\[confirm\\] | [ is escaped twice |
        | Router.Write |

        """
        BuiltIn().log("Execute command: `%s`" % (command))
        output = ''
        channel = self._channels[self._current_name]
        if channel['screen']: raise Exception("``Cmd`` keyword is prohibitted in ``screen  mode``")
        # in case something left in the buffer
        output  = channel['connection'].read()
        self.log(output)
        
        channel['connection'].write(command)
        self.log(command + Common.newline)

        cur_prompt  =  channel['prompt']
        if prompt is not None :    
            cur_prompt = prompt

        # automatically append an END-OF-LINE char to prompt for strictly
        # matching
        # if cur_prompt[-1] != '$':
        #    cur_prompt = cur_prompt + '$'
       
        output = ''

        # only TelnetLib has set_timeout attr
        self._set_conn_timeout(channel['connection'],timeout)
        try:
            output = channel['connection'].read_until_regexp(cur_prompt)
            self.log(output)
        except:
            if error_on_timeout: raise
            else:
                BuiltIn().log("WARN: timeout occured but no error was raised")
        self._set_conn_timeout(channel['connection'],channel['timeout'])

        # result checking
        cmd_auto_check = Common.get_config_value('cmd-auto-check')
        if cmd_auto_check and match_err != '' and re.search(match_err, output):
            err_msg = "ERROR: error while execute command `%s`" % command
            BuiltIn().log(err_msg)
            BuiltIn().log(output)
            raise Exception(err_msg)

        # remove PROMPT from the result if necessary
        if remove_prompt:
            tmp = output.splitlines()
            output = "\r\n".join(tmp[:-1])
            
        BuiltIn().log("Executed command `%s`" % (command))
        return output
    

    def cmd_yesno(self,cmd,ans='yes',question='? [yes,no] ',timeout='5s'):
        """ Executes a ``cmd``, waits for ``question`` and answers that by
        ``ans``
        """
        channel = self._channels[self._current_name]

        output = self.write(cmd,timeout)
        if not question in output:
            raise Exception("Unexpected output: %s" % output)

        output = self.write(ans)

        BuiltIn().log("Answered `%s` to command `%s`" % (ans,cmd))


    @with_reconnect
    def read(self,silence=False):
        """ Returns the current output of the virtual terminal and automatically
        logs to file. 
 
        In ``normal mode`` this will return the *unread* output only, not all the content of the screen.
        """
        if not silence: BuiltIn().log("Read from channel buffer:")
        channel = self._channels[self._current_name]
        output = ""
        if channel['screen']:
            # read from the session and log the result
            channel['stream'].feed(channel['connection'].read())
            try:
                output = _dump_screen(channel) + Common.newline
            except UnicodeDecodeError as err:
                BuiltIn().log('ERROR: Unicode error in read output')
                output = err.args[1].decode('utf-8','replace')
        else:
            try:
                output = channel['connection'].read() 
            except UnicodeDecodeError as err:
                output = err.args[1].decode('utf-8','replace')
    
        self.log(output)
        return output


    @property
    def current_name(self):
        """ returns node name of the current channel
        """
        return self._current_name


    def close(self,msg='',with_time=False,mark="***"):
        """ Closes current connection and returns the active channel name 

        `msg` is the last message is written to each device's log 
        """
        channels = self.get_channels()
        old_name = self._current_name
        channel = channels[old_name]
        finish_cmd = channel['finish']

        # close
        channels[self._current_name]['connection'].switch_connection(self._current_name)

        ### execute command before close the connection
        BuiltIn().log("Closing the connection for channel `%s`" % old_name)
        flag = Common.get_config_value('ignore-init-finish','vchannel',False)
        if not flag and finish_cmd is not None: 
            for item in finish_cmd:
                BuiltIn().log("Execute finish command: %s" % (item))
                channel['connection'].write_bare(item + '\r')
                time.sleep(1)
        
        timeout = Common.get_config_value('wait-time-before-close','vchannel','10s')
        BuiltIn().log("Wait `%s` seconds before closing the connection `%s`" % (timeout,old_name))
        try: 
            channel['connection'].write_bare('' + '\r')
            time.sleep(DateTime.convert_time(timeout))
            output = channels[self._current_name]['connection'].close_connection() 
            if output is not None: self.log(output)
        except Exception as err:
            BuiltIn().log('WARN: ignored errors while closing channel')
            BuiltIn().log(err)
            BuiltIn().log(traceback.format_exc())
        
        # farewell message    
        logger = BuiltIn().get_library_instance('Logger')
        logger.log(msg,with_time,mark)
        del(channels[self._current_name])

        # choose another active channel
        if len(channels) == 0:
            self._current_name     = ""
            self._current_id       = 0
            self._max_id           = 0

            self._telnet.close_all_connections()    
            self._ssh.close_all_connections()    
            self._telnet           = None
            self._ssh              = None
        else:
            first_key = list(channels.keys())[0]  # make dict key compatible with Python3
            self._current_name     = channels[first_key]['name'] 
            self._current_id       = channels[first_key]['id']

        # we need some time to release the socket
        time.sleep(1)

        BuiltIn().log("Closed the connection for channel `%s`, current channel is `%s`" % (old_name,self._current_name))
        return self._current_name


    def close_all(self,msg='',with_time=False,mark="***"):
        """ Closes all current sessions and flush out all log files. 

        `msg` is the last message the is written to each device's log.

        Current node name was reset to ``None``
        """
        # for name in self._channels:
        while len(self._channels) > 0:
            self.close(msg,with_time,mark)

        self._current_id = 0
        self._max_id = 0
        self._current_name = None
        self._channels = {}

 
    def flush_all(self):
        """ Flushes all remain data into the logger
        """
        current_name = self._current_name
        for name in self._channels:
            channel = self._channels[name]
            self.switch(name)
            self.read()
            if 'logger' in channel:
                channel['logger'].flush()
  
        self.switch(current_name)

   
    def get_ip(self):
        """ Returns the IP address of current node
        Examples:
            | ${router_ip}= | Router.`Get IP` |
        """
        name    = self._current_name
        node    = Common.LOCAL['node'][name]
        dev     = node['device']
        ip      = Common.GLOBAL['device'][dev]['ip']

        BuiltIn().log("Got IP address of current node: %s" % (ip))
        return  ip  

    def exec_file(self,file_name,vars='',comment='# ',step=False,mode='cmd',str_error='syntax,rror'):
        """ Executes commands listed in ``file_name``
        Lines started with ``comment`` character is considered as comments

        Parameters: 
        - `file_name` is a file located inside the ``config`` folder of the
        test case
        - `mode`: could be ``cmd`` or ``write`` which define that if the cmd is
          exectued by VChannel.`Cmd` or VChannel.`Write`
        -  if `step` is ``True``, after very command the output is check agains
        an error list. And if a match is found, execution will be stopped. Error
        list is define by ``str_err``, that contains multi regular expression
        separated by a comma. Default value of ``str_err`` is `error`
        - `vars` are additional variables in format ``var1=value1,var2=value2``

        The command file could be written in Jinja2 format. Default usable
        variables are ``LOCAL`` and ``GLOBAL`` which are identical to
        ``Common.LOCAL`` and
        ``Common.GLOBAL``. More variables could be supplied to the template by
        ``vars``.

        A sample for command list with Jinja2 template:
        | show interface {{ LOCAL['extra']['line1'] }}
        | show interface {{ LOCAL['extra']['line2'] }}
        |
        | {% for i in range(2) %}
        | show interface et-0/0/{{ i }}
        | {% endfor %}

        Examples:
        | Router.`Exec File`   | cmd.lst |
        | Router.`Exec File`   | step=${TRUE} | str_error=syntax,error |


        *Note:* Comment in the middle of the line is not supported
        For example if ``comment`` is "# "
        | # this is comment line <-- this line will be ignored
        | ## this is not an comment line, and will be enterd to the router cli,
        but the router might ignore this

        `step` is ignored in `write` mode
        """

        # load and evaluate jinja2 template
        folder = os.getcwd() + "/config/"
        loader=jinja2.Environment(loader=jinja2.FileSystemLoader(folder)).get_template(file_name)
        render_var = {'LOCAL':Common.LOCAL,'GLOBAL':Common.GLOBAL}
        for pair in vars.split(','):
            info = pair.split("=")
            if len(info) == 2:
                render_var.update({info[0].strip():info[1].strip()})

        command_str = loader.render(render_var)

        # execute the commands
        for line in command_str.split("\n"):
            if line.startswith(comment): continue
            str_cmd = line.rstrip()
            if str_cmd == '': continue # ignore null line
            if mode.lower() == 'cmd': 
                output = self.cmd(str_cmd)
            else:
                output = self.write(str_cmd)

            if not (step and mode.lower() == 'cmd'): continue
            for error in str_error.split(','):
                if re.search(error,output,re.MULTILINE):
                    raise Exception("Stopped because matched error after executing `%s`" % str_cmd)

        BuiltIn().log("Executed commands in file `%s` with mode `%s`" % (file_name,mode))


    @with_reconnect
    def cmd_and_wait_for_regex(self,command,pattern,interval=u'30s',max_num=u'10',error_with_max_num=True):
        """ Execute a command and expect ``pattern`` occurs in the output.
        If not wait for ``interval`` and repeat the process again

        When the keyword contains ``not:`` at the beginning, the matching logic
        is revsersed.

        After ``max_num``, if ``error_with_max_num`` is ``True`` then the
        keyword will fail. Ortherwise the test continues.
        """

        num = 1
        BuiltIn().log("Execute command `%s` and wait for `%s`" % (command,pattern))
        while num <= int(max_num):
            BuiltIn().log("    %d: command is `%s`" % (num,command))
            output = self.cmd(command)
            if re.search(pattern,output):
                BuiltIn().log("Found pattern `%s` and stopped the loop" % pattern)
                break;
            else:
                num = num + 1
                time.sleep(DateTime.convert_time(interval))
                BuiltIn().log_to_console('.','STDOUT',True)
        if error_with_max_num and num > int(max_num):
            msg = "ERROR: Could not found pattern `%s`" % pattern
            BuiltIn().log(msg)
            raise Exception(msg)
        BuiltIn().log("Executed command `%s` and waited for pattern `%s`" % (command,pattern))


    def cmd_and_wait_for(self,command,keyword,interval='30s',max_num=10,error_with_max_num=True):
        """ Execute a command and expect ``keyword`` occurs in the output.
        If not wait for ``interval`` and repeat the process again

        After ``max_num``, if ``error_with_max_num`` is ``True`` then the
        keyword will fail. Ortherwise the test continues.
        """

        num = 1
        BuiltIn().log("Execute command `%s` and wait for `%s`" % (command,keyword))

        tmp = keyword.split('not:')
        if len(tmp)==2 and tmp[0]=='':
            logic = 'not'
            m_keyword = tmp[1]
        else:
            logic = ''
            m_keyword = keyword
        BuiltIn().log('    Using matching logic `%s`' % logic)
        
        while num <= int(max_num):
            BuiltIn().log("    %d: command is `%s`" % (num,command))
            output = self.cmd(command)
            matching = '%s(m_keyword in output)' % logic
            if eval(matching) :
                BuiltIn().log("    Matched keyword `%s` and stopped the loop" % keyword)
                break;
            else:
                num = num + 1
                time.sleep(DateTime.convert_time(interval))
                BuiltIn().log_to_console('.','STDOUT',True)
        if error_with_max_num and num > int(max_num):
            msg = "ERROR: Could not match keyword `%s`" % keyword
            BuiltIn().log(msg)
            raise Exception(msg)

        BuiltIn().log("Executed command `%s` and waited for keyword `%s`" % (command,keyword))



    def snap(self, name, *cmd_list):
        """ Remembers the result of a list of command defined by ``cmd_list``

        Use this keyword with `Snap Diff` to get the difference between the
        command's result.
        The a new snapshot will overrride the previous result.

        Each snap is identified by its ``name``
        """
        buffer = ""
        for cmd in cmd_list:
            buffer += cmd + "\n"
            buffer += self.cmd(cmd)
        self._snap_buffer[name] = {}
        self._snap_buffer[name]['cmd-list'] = cmd_list
        self._snap_buffer[name]['buffer'] = buffer

        BuiltIn().log("Took snapshot `%s`" % name)


    def snap_diff(self,name):
        """ Executes the comman that have been executed before by ``name``
        snapshot and return the difference.

        Difference is in ``context diff`` format
        """

        if not self._snap_buffer[name]: return False
        cmd_list    = self._snap_buffer[name]['cmd-list']
        old_buffer  = self._snap_buffer[name]['buffer']

        buffer = ""
        for cmd in cmd_list:
            buffer += cmd + "\n"
            buffer += self.cmd(cmd)

        diff = difflib.context_diff(old_buffer.split("\n"),buffer.split("\n"),fromfile=name+":before",tofile=name+":current")
        result = "\n".join(diff)

        BuiltIn().log(result)
        BuiltIn().log("Took snapshot `%s` and showed the difference" % name)

        return result

    
    def broadcast_write_with_tag(self,cmd,*tag_list):
        """ Broadcasts `cmd` to all channels
        """
        channels = Common.node_with_tag(*tag_list)
        channel_num = len(channels)
        _name = self._current_name
        for item in channels:
            self.switch(item) 
            self.write(cmd)
        self.switch(_name)
        BuiltIn().log('Broadcasted cmd `%s` to %d channels' % (cmd,channel_num))

