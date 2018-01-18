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

# $Date: 2018-01-17 20:51:29 +0900 (Wed, 17 Jan 2018) $
# $Rev: 0.1.6 $
# $Author: bachng $

import os,sys
import IxLoad
from datetime import datetime
from multiprocessing import Process,Queue

class SubIxLoad(Process):
    """ A multi process supported IxLoad wrapper
    """
    def __init__(self,log_name,task_queue, result_queue):
        Process.__init__(self)
        self.task_queue     = task_queue
        self.result_queue   = result_queue
        self.elapsed = None

    def connect(self,ip):
        self.ix = IxLoad.IxLoad()
        self.ix.connect(ip)
        # logger      = self.ix.new("ixLogger","Ixload-RENAT",1)
        # log_engine  = logger.getEngine()
        # log_engine.setLevels(self.ix.ixLogger.kLevelDebug,self.ix.ixLogger.kLevelInfo)
        self.result_queue.put(["ixload::ok"])
        self.task_queue.task_done()


    def load_traffic(self,file_path):
        """ Loads test defined by ``file_path``

        Result will be saved in remote machine under the folder
        ``D://RENAT/RESULS/<this case>``
        """

        tmp = os.getcwd().split('/')
        folder_name = "%s_%s" % (tmp[-2],tmp[-1])

        self.repository = self.ix.new("ixRepository",name=file_path)
        self.controller = self.ix.new("ixTestController",outputDir=1)
        self.controller.setResultDir("D:/RENAT/RESULTS/%s" % folder_name)
        self.result_queue.put(["ixload::ok"])
        self.task_queue.task_done()

    
    def start_traffic(self):
        test_name = self.repository.testList[0].cget("name")
        test = self.repository.testList.getItem(test_name)
        test.config(
            statsRequired = 1,
            enableResetPorts = 1,
            csvInterval = 2,
            enableForceOwnership = True
        ) 
        self.run_start = datetime.now()
        IxLoad._TclEval("set ::ixTestControllerMonitor \"\"")
        self.controller.run(test)

        self.task_queue.task_done()

        IxLoad._TclEval("""\
            set ::test_cont 1
            while {$::ixTestControllerMonitor == "" && $::test_cont == 1} {
                after 1000 set wakeup 1
                vwait wakeup
            }
        """)
        if self.elapsed is None:
            stop = datetime.now()
            self.elapsed = (stop - self.run_start).total_seconds()
        
        self.result_queue.put(["ixload::ok"])


    def stop_traffic(self):
        IxLoad._TclEval("set ::test_cont 0")
    
        self.controller.stopRun()
        if self.elapsed is None:
            stop = datetime.now()
            self.elapsed = (stop - self.run_start).total_seconds()
        self.result_queue.put(["ixload::ok",self.elapsed])
        self.task_queue.task_done()
        
    
    def disconnect(self):
        self.ix.disconnect()
        self.result_queue.put(["ixload::ok"])
        self.task_queue.task_done()

         
    def run(self):
        while True:
            next_task = self.task_queue.get()
            try:
                if next_task[0] == "ixload::connect":
                    ip = next_task[1]   
                    self.connect(ip)
                elif next_task[0] == "ixload::disconnect":
                    self.disconnect()
                    break
                elif next_task[0] == "ixload::load_traffic":
                    self.load_traffic(next_task[1])
                elif next_task[0] == "ixload::start_traffic":
                    self.start_traffic()
                elif next_task[0] == "ixload::stop_traffic":
                    self.stop_traffic()
                else:
                    raise Exception()

            except Exception, e:
                self.result_queue.put(e)
                self.task_queue.task_done()
        return


 
