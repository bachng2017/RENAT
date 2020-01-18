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


import os,sys,shutil
import IxLoad
import Common
from robot.libraries.BuiltIn import BuiltIn
from datetime import datetime
from multiprocessing import Process,Queue

class SubIxLoad(Process):
    """ A multi process supported IxLoad wrapper

    A IxLoad test will automatically starts and runs this Ixload client in the
    background. The test item and this client communicates through predefined
    fortmat messages.

    The client will be terminated when the test finishes.
    """

    def __init__(self,log_name,task_queue, result_queue):
        Process.__init__(self)
        self.task_queue     = task_queue
        self.result_queue   = result_queue
        self.elapsed = None
        self.log_engine = None
        self.repository = None
        self.random = Common.random_name('_tmp%05d','0','99999')


    def connect(self,ip,verbose=False):
        self.ix = IxLoad.IxLoad()
        self.ix.connect(ip)

        # logger prepare
        self.logger      = self.ix.new("ixLogger","Ixload-RENAT",1)
        self.log_engine  = self.logger.getEngine()
        # 1st is File level and 2nd is console Level
        if verbose:
            self.log_engine.setLevels(self.ix.ixLogger.kLevelDebug,self.ix.ixLogger.kLevelInfo)
        else:
            self.log_engine.setLevels(self.ix.ixLogger.kLevelDebug,self.ix.ixLogger.kLevelError)
        self.log_engine.setFile(self._ixload_tmp_dir()+'/'+ self._ixload_tmp_dir(),1,256,1)

        self.result_queue.put(["ixload::ok"])
        self.task_queue.task_done()


    def _ixload_tmp_dir(self):
        """ Returns a temporary folder for this test
        """
        result_base = Common.GLOBAL['default']['ix-remote-tmp']

        tmp = os.getcwd().split('/')
        folder_name = "%s_%s" % (tmp[-2],tmp[-1])

        # create a temporary result directory
        result = "%s/%s" % (result_base,folder_name)
        result = result.replace('-','')
        result = result.replace(' ','_')
        result = result.replace('__','_')

        return result + self.random



    def load_config(self,config_name,port_list):
        """ Loads config file named ``config``

        ``config`` is the name of the confif file related to current active
        config path.
        """

        try:
            ixload_tmp_dir = self._ixload_tmp_dir()

            config_src = Common.get_item_config_path() + '/' + config_name
            config_dst = ixload_tmp_dir + '_' + config_name
            log = "IxLoad send file `%s` to `%s`" % (config_src,config_dst)

            IxLoad._TclEval("::IxLoad sendFileCopy %s %s" % (config_src,config_dst))


            self.controller = self.ix.new("ixTestController",outputDir=1)
            self.controller.setResultDir(ixload_tmp_dir)
            self.repository = self.ix.new("ixRepository",name=config_dst)

            test_name = self.repository.testList[0].cget('name')
            test = self.repository.testList.getItem(test_name)
            port_num = 0
            num = int(test.clientCommunityList.indexCount())
            for i in range(num):
                port_num = port_num + int(test.clientCommunityList[i].network.portList.indexCount())
            num = int(test.serverCommunityList.indexCount())
            for i in range(num):
                port_num = port_num + int(test.serverCommunityList[i].network.portList.indexCount())

            if len(port_list) == 0:
                self.result_queue.put(["ixload::ok"])
            elif port_num != len(port_list):
                self.result_queue.put(["ixload::err","Wrong port number"])
            else:
                num = int(test.clientCommunityList.indexCount())
                for i in range(num): test.clientCommunityList[i].network.portList.clear()

                num = int(test.serverCommunityList.indexCount())
                for i in range(num): test.serverCommunityList[i].network.portList.clear()

                test.setPorts(port_list)
                self.result_queue.put(["ixload::ok",ixload_tmp_dir,log])
        except Exception as err:
            self.result_queue.put([err])

        self.task_queue.task_done()


    def collect_data(self,prefix='',more_file='',ignore_not_found=True):
        """ Collect all data files

        Currently the follow data will be downloaded to the local machine
            - HTTP_Server.csv
            - HTTP Client.csv
            - HTTP Client - Per URL.csv
            - HTTP Server - Per URL.csv
            - L2-3 Stats for Client Ports.csv
            - L2-3 Stats for Server Ports.csv
            - L2-3 Throughput Stats.csv
            - Port CPU Statistics.csv

        Extra file could be add by ``more_file`` which is a comma separated
        filename string
        """

        ixload_tmp_dir = self._ixload_tmp_dir()

        result_folder = Common.get_result_path()
        file_list = [
            'HTTP_Server.csv',
            'HTTP_Client.csv',
            'HTTP Client - Per URL.csv',
            'HTTP Server - Per URL.csv',
            'L2-3 Stats for Client Ports.csv',
            'L2-3 Stats for Server Ports.csv',
            'L2-3 Throughput Stats.csv',
            'Port CPU Statistics.csv',
        ]

        # add more files
        file_list.extend(more_file.split(','))
        file_list.remove('')

        try:
            for item in file_list:
                dst = item.replace('-','')
                dst =  dst.replace(' ','_')
                dst =  dst.replace('__','_')
                try:
                    self.ix.retrieveFileCopy("%s/%s" % (ixload_tmp_dir,item), "%s/%s%s" % (result_folder,prefix,dst))
                except Exception as err:
                    if not ignore_not_found: raise err
            self.result_queue.put(["ixload::ok"])
        except Exception as err:
            self.result_queue.put([err])
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
        try:
            IxLoad._TclEval("set ::test_cont 0")

            self.controller.stopRun()
            if self.elapsed is None:
                stop = datetime.now()
                self.elapsed = (stop - self.run_start).total_seconds()
            self.result_queue.put(["ixload::ok",self.elapsed])
        except Exception as err:
            self.result_queue.put([err])
        self.task_queue.task_done()


    def get_test_report(self,prefix='',ignore_not_found=False):
        self.controller.generateReport(detailedReport=1, format="PDF")
        ixload_tmp_dir = self._ixload_tmp_dir()

        result_folder = Common.get_result_path()
        file_list = [
            'IxLoad Detailed Report.pdf'
        ]

        try:
            for item in file_list:
                dst = item.replace('-','')
                dst = dst.replace(' ','_')
                dst = dst.replace('__','_')
                try:
                    self.ix.retrieveFileCopy("%s/%s" % (ixload_tmp_dir,item), "%s/%s%s" % (result_folder,prefix,dst))
                except Exception as err:
                    if not ignore_not_found: raise err
            self.result_queue.put(["ixload::ok"])
        except Exception as err:
            self.result_queue.put([err])
        self.task_queue.task_done()


    def disconnect(self):
        # get log
        try:
            if self.log_engine:
                # self.log_engine.setFile(self._ixload_tmp_dir()+'/'+Common.get_myid(),4,2048,1)
                # remote_logfile = "C:/Progra~1/IxLoad/Client/tclext/remoteScriptingService/" + self.log_engine.getFileName()
                remote_logfile = self.log_engine.getFileName()
                local_logfile = Common.get_result_path() + '/ixload.log'
                self.ix.retrieveFileCopy(remote_logfile, local_logfile)

            self.ix.delete(self.repository)
            self.ix.delete(self.controller)
            self.ix.disconnect()
            self.result_queue.put(["ixload::ok",remote_logfile])
        except Exception as err:
            self.result_queue.put([err])
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
                elif next_task[0] == "ixload::load_config":
                    self.load_config(next_task[1],next_task[2])
                elif next_task[0] == "ixload::start_traffic":
                    self.start_traffic()
                elif next_task[0] == "ixload::stop_traffic":
                    self.stop_traffic()
                elif next_task[0] == "ixload::get_test_report":
                    self.get_test_report(next_task[1])
                elif next_task[0] == "ixload::collect_data":
                    self.collect_data(next_task[1],next_task[2],next_task[3])
                else:
                    raise Exception()

            except Exception as err:
                self.result_queue.put([err])
                self.task_queue.task_done()
        return



