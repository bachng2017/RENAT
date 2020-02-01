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


import threading,traceback,time,datetime
import Common,VChannel
from robot.libraries.BuiltIn import BuiltIn
import robot.libraries.DateTime as DateTime

def _thread_cmd(self,cmd):
    try:
        channel = self._channels[self._current_name]
        self._cmd(cmd)
    except Exception as err:
        BuiltIn().log("WARN: A running thread for channel `%s` is \
            terminated" % (channel['node']),console=False)
        BuiltIn().log(err,console=False)
        BuiltIn().log(traceback.format_exc(),console=False)

def _thread_repeat_cmd(stop,self,cmd,interval,with_time):
    try:
        channel = self._channels[self._current_name]
        if with_time:
            mark = datetime.datetime.now().strftime("%I:%M:%S%p on %B %d, %Y: ")
        else:
            mark = ""
        while not stop.is_set():
            self._cmd(cmd)
            self.log("\n---%s---\n" % mark,channel)
            time.sleep(DateTime.convert_time(interval))

    except Exception as err:
        BuiltIn().log("WARN: A running thread for channel `%s` is \
            terminated" % (channel['node']),console=False)
        BuiltIn().log(err,console=False)
        BuiltIn().log(traceback.format_exc(),console=False)


class AChannel(VChannel.VChannel):
    """ AChannel derives from VChannel and is used for parallel actions \
    besides the main scenario.

    Likes VChannel, AChannel handles a virtual terminal for each node.

    While `VChannel.Cmd` is a bloking keyword, `AChannel.Cmd` is a
    non-blocking keyword. When using `Cmd`, users need to control when the
    command finishes its work.
    """
    def __init__(self):
        super(AChannel,self).__init__(u"_")
        self._cmd_threads = {}
        self._cmd_thread_id = 0


    def cmd(self,cmd=''):
        """ Exececutes a command in background

        - `cmd`: a command
        Returns an id that could be used for `Cmd Wait`
        """
        self._cmd_thread_id += 1
        thread_id = self._cmd_thread_id
        self._cmd_threads[thread_id] = {}

        thread = threading.Thread(target=_thread_cmd,args=(self,cmd))
        thread.start()
        self._cmd_threads[thread_id]['thread'] = thread
        self._cmd_threads[thread_id]['stop'] = None
        BuiltIn().log("Started command `%s` in other thread" % cmd)
        return thread_id


    def wait_cmd(self,exec_id,timeout=u'0s'):
        """ Waits until a background command finishes or timeout
        """
        time_s = DateTime.convert_time(timeout)
        thread = self._cmd_threads[exec_id]['thread']
        thread.join(time_s)
        BuiltIn().log("Waited until cmd thread finished")


    def stop_repeat_cmd(self,exec_id,timeout=u'0s'):
        """ Stops a runnin Repeat Command by its `exec_id`

        - `exec_id`: an ID return when using Cmd
        """
        time_s = DateTime.convert_time(timeout)
        thread = self._cmd_threads[exec_id]['thread']
        stop = self._cmd_threads[exec_id]['stop']
        if stop:
            stop.set()
        thread.join(time_s)
        BuiltIn().log("Stopped a repeated command")


    def repeat_cmd(self,cmd='',interval='1',with_time=True):
        """ Repeat a command with `interval`

        When `with_time` is ${TRUE}, a time mark will be inserted between output
        of the command
        """
        stop = threading.Event()
        self._cmd_thread_id += 1
        thread_id = self._cmd_thread_id
        self._cmd_threads[thread_id] = {}
        thread = threading.Thread(target=_thread_repeat_cmd,args=(stop,self,cmd,interval,with_time))
        thread.start()
        self._cmd_threads[thread_id]['thread'] = thread
        self._cmd_threads[thread_id]['stop'] = stop
        BuiltIn().log("Started command `%s` in other thread" % cmd)
        return thread_id

