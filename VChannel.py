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

# $Rev: 1010 $
# $Ver: 0.1.8g1 $
# $Date: 2018-05-31 11:30:17 +0900 (Thu, 31 May 2018) $
# $Author: $

import os,re,sys
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
        self._telnet = Telnet()
        self._ssh = SSHLibrary.SSHLibrary()
        self._current_id = 0
        self._current_name = None
        self._max_id = 0
        self._snap_buffer = {}
        self._channels = {}


    @property
    def current_name(self):
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


    def log(self,msg):
        """ Writes the log message ``msg`` to current log file of the channel
        """

        channel = self._channels[self._current_name]
 
       # in case the channel has already has the logger
        if 'logger' in channel:
            logger      = channel['logger']
            separator   = channel['separator']
            if separator != "":
                if channel['screen']: logger.write(Common.newline)
                logger.write(Common.newline + separator + Common.newline)
            # logger.write(msg)
            # remove some special control char before write to file
            logger.write(re.sub(r"[\x07]", "", msg))
            logger.flush()


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
        # _curr_name  = self._current_name
        _node       = self._current_channel_info['node']
        _name       = self._current_channel_info['name']
        _log_file   = self._current_channel_info['log_file']
        _w          = self._current_channel_info['w'] 
        _h          = self._current_channel_info['h'] 
        _mode       = self._current_channel_info['mode'] 
        _timeout    = self._current_channel_info['timeout']

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
        ignore_dead_node =  'ignore_dead_node' in Common.LOCAL['default'] and \
                            Common.LOCAL['default']['ignore_dead_node']
        id = 0

        if name in self._channels: 
            raise Exception("Channel `%s` already existed. Use different name instead" % name)
    
        _device         = Common.LOCAL['node'][node]['device']
        _ip             = Common.GLOBAL['device'][_device]['ip']
        _type           = Common.GLOBAL['device'][_device]['type']    
        _access_tmpl    = Common.GLOBAL['access-template'][_type] 
        _access         = _access_tmpl['access']
        _auth_type      = _access_tmpl['auth']
        if 'proxy_cmd' in _access_tmpl:
            _proxy_cmd      = _access_tmpl['proxy_cmd']
        else:
            _proxy_cmd      = None
        _profile        = _access_tmpl['profile']
        _prompt         = _access_tmpl['prompt'] + '$' # automatically append <dollar> to the prompt from yaml config 
        _auth           = Common.GLOBAL['auth'][_auth_type][_profile]
        if 'init' in _access_tmpl:
            _init           = _access_tmpl['init'] # initial command 
        else:
            _init = None
        _timeout        = timeout
        if 'login_prompt' in _access_tmpl: 
            _login_prompt = _access_tmpl['login_prompt']
        else:
            _login_prompt = 'login:'
        if 'password_prompt' in _access_tmpl: 
            _password_prompt = _access_tmpl['password_prompt']
        else:
            _password_prompt = 'Password:'
        
        BuiltIn().log("Opening connection to `%s(%s)`" % (name, _ip))
        

        try:
    
            channel_info = {}
            ### TELNET 
            ### _login_prompt could be None but not the _password_prompt
    	    if _access == 'telnet':
                s = str(w) + "x" + str(h)
                local_id = self._telnet.open_connection(_ip,
                                                        alias=name,terminal_type='vt100', window_size=s,
                                                        prompt=_prompt,prompt_is_regexp=True,timeout=_timeout)
                if _login_prompt is not None:
                    out = self._telnet.login(_auth['user'],_auth['pass'], login_prompt=_login_prompt,password_prompt=_password_prompt)
                else:
                    out = self._telnet.read_until(_password_prompt)
                    self._telnet.write(_auth['pass'])
    
                # allocate new channel id
                id = self._max_id + 1
                channel_info['id']          = id 
                channel_info['type']        = _type
                channel_info['access-type'] = 'telnet'
                channel_info['prompt']      = _prompt 
                channel_info['connection']  = self._telnet
                channel_info['local_id']    = local_id
    
    
            ### SSH plain-text
            if _access == 'ssh':
                out = ""
                local_id = self._ssh.open_connection(_ip,alias=name,term_type='vt100',width=w,height=h,timeout=_timeout)
                if _auth_type == 'plain-text':
                    if _proxy_cmd:
                        user        = os.environ.get('USER')
                        home_folder = os.environ.get('HOME')
                        port = 22
                        _cmd = _proxy_cmd.replace('%h',_ip).replace('%p',str(port)).replace('%u',user).replace('~',home_folder)
                    else:
                        _cmd = None
                    out = self._ssh.login(_auth['user'],_auth['pass'],proxy_cmd=_cmd)
                    # out = self._ssh.login(_auth['user'],_auth['pass'],False)
                if _auth_type == 'public-key':
                    out = self._ssh.login_with_public_key(_auth['user'],_auth['key'])
    
                # allocate new channel id
                id = self._max_id + 1
                channel_info['id']          = id 
                channel_info['type']        = _type
                channel_info['access-type'] = 'ssh'
                channel_info['prompt']      = _prompt
                channel_info['connection']  = self._ssh
                channel_info['local_id']    = local_id
    
    
            # open/create a log file for this connection in result_folder
            result_folder = Common.get_result_folder()
            if log_file == '':
                channel_info['logger']  = None
            else:
                channel_info['logger']  = codecs.open(result_folder + "/" + log_file,mode,'utf-8')
    
            # common channel info
            channel_info['node']        = node
            channel_info['name']        = name
            channel_info['log_file']    = log_file
            channel_info['w']           = w
            channel_info['h']           = h
            channel_info['mode']        = mode
            channel_info['timeout']     = _timeout
            channel_info['auth']        = _auth
            channel_info['ip']          = _ip
            channel_info['separator']   = ""
       
            # extra 
            channel_info['screen']      = None
            channel_info['stream']      = None
            self._current_id           = id
            self._max_id               = id
            self._current_name         = name
    
        
            # remember this info by name(alias)
            self._channels[name]   = channel_info 
            self._current_channel_info = channel_info
    
            # logging the ouput 
            self.log(out)


            # by default switch to the connected device
            self.switch(name)
        
            # enable
            if 'enable' in _auth:
                channel_info['connection'].write('enable')
                channel_info['connection'].read_until_regexp("Password:")
                self.cmd(_auth['enable'])
    
            ### execute 1st command after login
            if _init is not None: 
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
        
        if not channel['screen']:
            channel['screen'] = pyte.HistoryScreen(channel['w'], channel['h'],100000)
            # channel['screen'] = pyte.Screen(channel['w'], channel['h'])
            # channel['stream'] = pyte.ByteStream(encodings=[('UTF-8', 'ignore')])
            channel['stream'] = pyte.Stream()
            channel['stream'].attach(channel['screen'])
            channel['screen'].set_charset('B', '(')

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

        BuiltIn().log("Stopped ``screen mode``")


    def _get_history(self,screen):
        return self._get_history_screen(screen.history.top) + Common.newline

    def _get_history_screen(self, deque):
        return Common.newline.join(''.join(c.data for c in row).rstrip()
                                  for row in deque).rstrip(Common.newline)

    def _get_screen(self, screen):
        channel = self._channels[self._current_name]
        return Common.newline.join(row.rstrip() for row in screen.display).rstrip(Common.newline)   

    def _dump_screen(self):
        channel = self._channels[self._current_name]
        if channel['screen']:
            return  self._get_history(channel['screen']) + self._get_screen(channel['screen'])
            # return  self._get_screen(channel['screen'])
        return ''

 
    def switch(self,name):
        """ Switches the current active channel to ``name``. 
        There only one active channel at any time
    
        Examples:
        | VChannel.`Switch` | vmx12 | 
        """
        # clear buffer before switch 
        old_name = self._current_name
        self.read()
 
        if name in self._channels: 
            channel_info = self._channels[name]
            self._current_name = name
            self._current_channel_info = channel_info

            self._current_id = channel_info['id']

            channel_info['connection'].switch_connection(channel_info['local_id'])

            BuiltIn().log("Switched current channel to `%s(%s)`" % (name,channel_info['ip']))
            return channel_info['id'], channel_info['local_id']
        else:
            err_msg = "ERROR: Could not find `%s` in current channels" % name
            BuiltIn().log(err_msg)
            raise Exception(err_msg)


    def change_log(self,log_file,mode='w'):
        """ Stops current log file and create a new log file. 
   
        Every log from that point will be saved to the new log file
        Return old log filename
        """
        channel = self._channels[self._current_name]
        old_log_file = channel['log_file']

        # flush buffer before change the log file
        channel['logger'].flush()
        channel['logger'].close()
    
        result_path = Common.get_result_path() 
        channel['logger'] = codecs.open(result_path+'/'+log_file,mode,'utf-8') 
        channel['log_file'] = log_file

        BuiltIn().log("Changed current log file to %s" % log_file)
        return old_log_file


    def _with_reconnect(self,f,*args):
        """ local method that provide a fail safe reconnect when read/write
        """
        max_retry = Common.GLOBAL['default']['max-retry-for-connect']
        interval  = Common.GLOBAL['default']['interval-between-retry']

        # BuiltIn().log("Try maximum %s times with %s second interval" % (max_retry,interval))
        for i in range(max_retry):
            try:
                return f(*args)
            except (EOFError,KeyError) as e:
                BuiltIn().log("    Exception(%s): %s" % (str(type(e)),str(e)))
                # BuiltIn().log(traceback.format_exc())

                BuiltIn().log("    Try reconnection: " + str(i+1))
                try:
                    self.reconnect(self._current_name)
                    continue
                except Exception as e:
                    BuiltIn().log("    WARNING: %s: %s" % (str(type(e)),str(e)))
                    # BuiltIn().log(traceback.format_exc())
                    if i == max_retry - 1:
                        err_msg = "    ERROR: Failed to reconnect to node `%s`" % self._current_name
                        BuiltIn().log(err_msg)
                        raise Exception(err_msg)
                    else:
                        time.sleep(interval)
                        BuiltIn().log_to_console('.','STDOUT',True)
            except Exception as e:
                err_msg = "ERROR: timeout while processing command. Tunning ``terminal-timeout`` in RENAT config file or check your command"
                BuiltIn().log(err_msg)
                raise Exception(err_msg)

        err_msg = "    ERROR: failed to execute command `%s`" % f
        BuiltIn().log(err_msg)
        raise Exception(err_msg)


    def _write(self,cmd,wait):

        result = ""
        channel = self._channels[self._current_name]
    
        if channel['screen']:
            channel['connection'].write_bare(cmd)
            self.log(cmd)
            if wait > 0:
                time.sleep(wait)
                result = self.read()
            else:
                self.log(cmd)
        else:
            channel['connection'].write_bare(cmd + Common.newline)
            if wait > 0:
                time.sleep(wait)
                result = self.read()
            else:
                self.log(cmd + Common.newline)
           
        return result


    def write(self,str_cmd,str_wait='0s',start_screen_mode=False):
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

        When `str_wait` is not `0s`, the keyword read and return the output
        after waiting `str_wait`. Otherwise, the keyword return with no output.
   
        *Notes:*  This is a non-blocking command.

        Examples:
        | VChannel.`Write` | monitor interface traffic | start_screen_mode=${TRUE} |
        | VChannel.`Write` | ${CTRL_C} | # simulates Ctrl-C |
        
        """

        #
        # self.read()

        wait = DateTime.convert_time(str_wait)

        channel = self._channels[self._current_name]
        if channel['screen']: 
            screen_mode = True
        else: 
            screen_mode = False
        
        if start_screen_mode:
            self.start_screen_mode()
            # because we've just start the screen mode but the node has not yet
            # start the screen_mode, a newline is necessary here
            result = self._with_reconnect(self._write,str_cmd + Common.newline,wait)
        else:
            result = self._with_reconnect(self._write,str_cmd,wait)

        BuiltIn().log("Screen=%s, wrote '%s'" % (screen_mode,str_cmd))
        return result


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
        


    def _cmd(self,str_cmd,str_prompt):
        output = ""
        channel = self._channels[self._current_name]

        if channel['screen']: raise Exception("``Cmd`` keyword is prohibitted in ``screen  mode``")

        access      = channel['access-type']
        cur_prompt  = channel['prompt']


        # in case something left in the buffer
        output  = channel['connection'].read()
        self.log(output)
        
        channel['connection'].write(str_cmd)
        self.log(str_cmd + Common.newline)
       
        if str_prompt == '' :    
            output  = channel['connection'].read_until_regexp(cur_prompt)
        else:
            output  = channel['connection'].read_until_regexp('.*' + str_prompt)
        self.log(output)
        return output

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


    def cmd(self,command='',prompt='',match_err='\r\n(unknown command.|syntax error, expecting <command>.)\r\n'):
        """Executes a ``command`` and wait until for the prompt. 
  
        This is a blocking keyword. Execution of the test case will be postponed until the prompt appears.
        If ``prompt`` is a null string (default), its value is defined in the ``./config/template.yaml``

        Output will be automatically logged to the channel current log file.

        See [./Common.html|Common] for details about the config files.
        """

        BuiltIn().log("Execute command: `%s`" % (command))
        output = self._with_reconnect(self._cmd,command,prompt)

        # result checking
        if Common.GLOBAL['default']['cmd-auto-check'] and match_err != '' and re.search(match_err, output):
            err_msg = "ERROR: error while execute command `%s`" % command
            BuiltIn().log(err_msg)
            BuiltIn().log(output)
            raise Exception(err_msg)

            
        BuiltIn().log("Executed command `%s`" % (command))
        return output
    

    def cmd_yesno(self,cmd,ans='yes',question='? [yes,no] '):
        """ Executes a ``cmd``, waits for ``question`` and answers that by
        ``ans``
        """
        channel = self._channels[self._current_name]

        output = self.write(cmd,'5s')
        if not question in output:
            raise Exception("Unexpected output: %s" % output)

        output = self.write(ans)

        BuiltIn().log("Answered `%s` to command `%s`" % (ans,cmd))
        return True


    def _read(self):
        channel = self._channels[self._current_name]
        output = ""
  
        if channel['screen']:
            channel['stream'].feed(channel['connection'].read())
            try:
                output = self._dump_screen() + Common.newline
            except UnicodeDecodeError as err:
                output = err.args[1].decode('utf-8','replace')
        else:
            try:
                output = channel['connection'].read() 
            except UnicodeDecodeError as err:
                output = err.args[1].decode('utf-8','replace')

        self.log(output)
        return output


    def read(self,silence=False):
        """ Returns the current output of the virtual terminal and automatically
        logs to file. 
 
        In ``normal mode`` this will return the *unread* output only, not all the content of the screen.
        """

        output = self._with_reconnect(self._read)

        if not silence: BuiltIn().log("Read from channel buffer")
        return output
   
 

    @property
    def current_name(self):
        """ returns node name of the current channel
        """
        return self._current_name


    def close(self):
        """ Closes current connection and returns the active channel name 
        """
        channels = self.get_channels()
        old_name = self._current_name

        # close
        channels[self._current_name]['connection'].switch_connection(self._current_name)
        channels[self._current_name]['connection'].close_connection() 
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
            first_key = channels.keys()[0]
            self._current_name     = channels[first_key]['name'] 
            self._current_id       = channels[first_key]['id']

        BuiltIn().log("Closed the connection for channel '%s'" % (old_name))
        return self._current_name


    def close_all(self):
        """ Closes all current sessions and flush out all log files. 

        Current node name was reset to ``None``
        """
        # for name in self._channels:
        while len(self._channels) > 0:
            self.close()
            # output = self.read() 

        # self._telnet.close_all_connections()    
        # self._ssh.close_all_connections()    

        self._current_id = 0
        self._max_id = 0
        self._current_name = None
        self._channels = {}

 
    def flush_all(self):
        """
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
        name    = self._cur_name
        node    = Common.LOCAL['node'][name]
        dev     = node['device']
        ip      = Common.GLOBAL['device'][dev]['ip']

        BuiltIn().log("Got IP address of current node: %s" % (ip))
        return  ip  

    def exec_file(self,file_name,vars='',comment='# ',step=False,str_error='syntax,rror'):
        """ Executes commands listed in ``file_name``
        Lines started with ``comment`` character is considered as comments

        ``file_name`` is a file located inside the ``config`` folder of the
        test case.

        This command file could be written in Jinja2 format. Default usable
        variables are ``LOCAL`` and ``GLOBAL`` which are identical to
        ``Common.LOCAL`` and
        ``Common.GLOBAL``. More variables could be supplied to the template by
        ``vars``.

        ``vars`` has the format: ``var1=value1,var2=value2``

        If ``step`` is ``True``, after very command the output is check agains
        an error list. And if a match is found, execution will be stopped. Error
        list is define by ``str_err``, that contains multi regular expression
        separated by a comma. Default value of ``str_err`` is `error`

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
            output = self.cmd(str_cmd)

            if not step: continue
            for error in str_error.split(','):
                if re.search(error,output,re.MULTILINE):
                    raise Exception("Stopped because matched error after executing `%s`" % str_cmd)

        BuiltIn().log("Executed commands in file %s" % file_name)


    def cmd_and_wait_for(self,command,keyword,interval='30s',max_num=10,error_with_max_num=True):
        """ Execute a command and expect ``keyword`` occurs in the output.
        If not wait for ``interval`` and repeat the process again

        After ``max_num``, if ``error_with_max_num`` is ``True`` then the
        keyword will fail. Ortherwise the test continues.
        """

        num = 1
        BuiltIn().log("Execute command `%s` and wait for `%s`" % (command,keyword))
        while num <= max_num:
            BuiltIn().log("    %d: command is `%s`" % (num,command))
            output = self.cmd(command)
            if keyword in output:
                BuiltIn().log("Found keyword `%s` and stopped the loop" % keyword)
                break;
            else:
                num = num + 1
                time.sleep(DateTime.convert_time(interval))
                BuiltIn().log_to_console('.','STDOUT',True)
        if error_with_max_num and num > max_num:
            msg = "ERROR: Could not found keyword `%s`" % keyword
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
        self._snap_buffer[name]['cmd_list'] = cmd_list
        self._snap_buffer[name]['buffer'] = buffer

        BuiltIn().log("Took snapshot `%s`" % name)


    def snap_diff(self,name):
        """ Executes the comman that have been executed before by ``name``
        snapshot and return the difference.

        Difference is in ``context diff`` format
        """

        if not self._snap_buffer[name]: return False
        cmd_list    = self._snap_buffer[name]['cmd_list']
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
