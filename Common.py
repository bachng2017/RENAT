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

# $Rev: 901 $
# $Ver: 0.1.8g $
# $Date: 2018-04-10 19:44:08 +0900 (Tue, 10 Apr 2018) $
# $Author: $

""" Common library for RENAT

It loads config files and create necessary varibles. The file should be the 1st
library  included from any test case.


== Table of Contents ==

- `Configuration file`
- `Variables`
- `Shortcuts`
- `Keywords`

= Configuration file =

== Global configuration ==
There are 2 kinds of configuration files. The global configuration files (aka
master files) include device information, authentication etc that are used for
all the test cases in the suite. The local configuration file ``local.yaml``
includes information about nodes, tester ports etc. that are used in a specific
test case.

At the beginning, the module makes a local copy the master files and initialize
necessary variables.

The master files folder is defined by ``renat-master-folder`` in
``$RENAT_PATH/config/config.yaml``. Usually, users do not need to modify the
master files. The most common case is when new device is deployed, the
``device.yaml`` need to be update so that device could be used in the test
cases.

- device.yaml: contains global device information

| device:
|     apollo:
|         type: ssh-host
|         description: main server
|         ip: 10.128.3.101
|     artermis:
|         type: ssh-host
|         description: second server
|         ip: 10.128.3.91
|     vmx11:
|         type: juniper
|         description: r1
|         ip: 10.128.64.11
|     vmx12:
|         type: juniper
|         description: r2
|         ip: 10.128.64.12
    


- auth.yaml: contains authentication information

| auth:
|     plain-text:
|         default:
|             user: user
|             pass: nttXXX
|         flets:
|             user: user
|             pass: IpcoXXXX
|         arbor:
|             user: admin
|             pass: nttXXX
| 
|     public-key: # for Public Key authentication
|         default:
|             user: robot
|             key: /home/user/.ssh/robot_id_rsa
|         test:
|             user: jenkins
|             key:  /var/lib/jenkins/.ssh/id_rsa


- template.yaml: contains devvice template information


| access-template:
|     ssh-host:
|         access: ssh
|         auth: public-key
|         profile: default
|         prompt: \$
|         append:
|         init: unalias -a
|     juniper:
|         access: telnet
|         auth: plain-text
|         profile: default
|         prompt: "(#|>) "
|         append: ' | no-more'
|         init:
|     cisco:
|         access: ssh
|         auth: plain-text
|         profile: default
|         prompt: "\@.*(#|>) "
|         append:
|         init:
| snmp-template:
|        juniper:
|             mib: ./mib-Juniper.json
|             community: public
|             poller: renat
|        cisco:
|             mib: ./mib-Cisco.json
|             community: public
|             poller: renat


== Local Configuration ==
Local configuration (aka ``local.yaml``) was used by a test case of its sub test
cases. Test cases could includes several test cases (the sub level is not
limited). The local configuration is defined by ``local.yaml`` in the ``config``
folder of each test case. If a test case does not has the ``local.yaml`` in its
``config`` folder, it will use the ``local.yaml`` file in its parent test case
and so on. This will help users to share the test information for related test
case without having the same ``local.yaml`` for each test case (*Note:* this
feature is enabled from RENAT 0.1.4). The ``local.yaml`` that is really used for
the test is called ``active local.yaml``.

When user used the wizard ``case.sh`` to create a new test case, they have the
ability to crete new ``local.yaml`` or not. ``local.yaml`` could be edited and
inserted new information later to hold more informations for the test case.

When a test is run, it will display its current active ``local.yaml``

    - <testcase>/config/local.yaml: contains local data for a test case

| node:
|     vmx11:
|         device: vmx11
|         snmp_polling: yes
|     vmx12:
|         device: vmx11
|         snmp_polling: yes
|     apollo:
|         device: vmx11
|         snmp_polling: yes
| 
| tester:
|     tester01:
|         type: ixnet
|         ip: 10.128.32.70
|         config: vmx_20161129.ixncfg
| 
| port-mapping:
|     uplink01:
|         device: vmx11
|         port: ge-0/0/0
|     downlink01:
|         device: vmx12
|         port: ge-0/0/2
| 
| default:
|     ignore_dead_node: yes
|     terminal:
|         width: 80
|         height: 32
|     result_folder: result


 
= Variables =
The module automatically create ``GLOBAL`` & ``LOCAL`` variable for other
libraries. It also creates global list variables `GLOBAL``,``LOCAL`` and
``NODE`` that could be accessed from `Robot Framework` test cases.


The GLOBAL variable holds all information defined by the master files and LOCAL
variable holds all variables defined by active ``local.yaml``. And ``NODE`` is a
list that hold all active nodes defined in the  ``local.yaml``.

Users could access to the information of a key in ``local.yaml`` by
``${LOCAL['key']}``, information of a node by ``${LOCAL['node']['vmx11']}`` or
simply ``$NODE['vmx']``. When a keyword need a list of current node, ``@{NODE}``
could be used.

*Notes:* By default, RENAT will stop and raise an exception if connection to a
node is failed. But if ``ignore_dead_node`` is defined as ``yes`` (default) is
the current active ``local.yaml``, RENAT will omit an warning but keep running
the test and remove the node from its active node list.

"""

ROBOT_LIBRARY_VERSION = 'RENAT 0.1.8g'

import os
import glob,fnmatch
import re
import yaml
import glob
import time,datetime
import codecs
import numpy
import random
import shutil
import pdfkit
import string
import fileinput
import difflib
import hashlib
import pandas
import sys,select
import subprocess
from sets import Set
import robot.libraries.DateTime as DateTime
from robot.libraries.BuiltIn import BuiltIn
from collections import OrderedDict

# make sure the yaml dictionary is in its order
yaml.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    lambda loader, node: OrderedDict(loader.construct_pairs(node)))


# filter all warning
# done this for openpyxl, maybe we should not do this
import warnings
warnings.filterwarnings("ignore")


### global setting 
GLOBAL  = {}
LOCAL   = {}
NODE    = []
WEBAPP  = []
START_TIME = datetime.datetime.now()

def log(msg,level=1):
    """ Logs ``msg`` to the current log file (not console)
   
    The ``msg`` will logged only if the level is bigger than the global level
    ``${DEBUG}`` which could be defined at runtime.
    If ``${DEBUG}`` is not defined, it will be considered as the default
    ``level`` as 1.

    Examples:
    | Common.`Log` | XXX | # this always be logged |
    | Common.`Log` | AAA | level=2 | # this will not be logged with common run.sh |
    | Common.`Log` | BBB | level=2 | # ./run.sh -v ``DEBUG:2`` will log the message |

    *Notes*: For common use
    - level 1: is default
    - level 2: is debug mode
    - level 3: is very informative mode
    """
    _level = None
    try:
        _level = BuiltIn().get_variable_value('${DEBUG}') 
    except:
        pass 
    if _level is None: _level=1
    if int(_level) >= int(level): 
        BuiltIn().log(msg)

def log_to_console(msg,level=1):
    """ Logs a message to console

    See Common.`Print` for more details about debug level

    """
    _level = None
    try:
        _level = BuiltIn().get_variable_value('${DEBUG}') 
    except:
        pass 
    if _level is None: _level=1
    if int(_level) >= int(level): 
        BuiltIn().log_to_console(msg)


def err(msg):
    """ Prints error ``msg`` to console
    """
    BuiltIn().log_to_console(msg) 


###
try:
    _result_folder = os.path.basename(BuiltIn().get_variable_value('${OUTPUT DIR}'))
except:
    log("ERROR: Error happened while trying to get global RF variables")
    
    
_folder = os.path.dirname(__file__)
if _folder == '': _folder = '.'

### load global setting
with open(_folder + '/config/config.yaml') as f:
    GLOBAL.update(yaml.load(f))

### copy config file from maser to tmp
### overwrite the current files
_tmp_folder = _folder + '/tmp/'
_renat_master_folder    = GLOBAL['default']['renat-master-folder']
if _renat_master_folder:
    _renat_master_folder = os.path.expandvars(_renat_master_folder)
shutil.copy2(_renat_master_folder+'/device.yaml',_tmp_folder)
shutil.copy2(_renat_master_folder+'/auth.yaml',_tmp_folder)
shutil.copy2(_renat_master_folder+'/template.yaml',_tmp_folder)

_calient_master_path    = GLOBAL['default']['calient-master-path']
if _calient_master_path:
    _calient_master_path = os.path.expandvars(_calient_master_path)
if _calient_master_path:
    newest_calient = max(glob.iglob(_calient_master_path))
    shutil.copy2(newest_calient,_tmp_folder + "/calient.xlsm")

_ntm_master_path        = GLOBAL['default']['ntm-master-path']
if _ntm_master_path:
    _ntm_master_path = os.path.expandvars(_ntm_master_path)
if _ntm_master_path:
    newest_ntm = max(glob.iglob(_ntm_master_path))
    shutil.copy2(newest_ntm,_tmp_folder + "/g4ntm.xlsm")


### expand environment variable and update GLOBAL config
for entry in ['auth.yaml', 'device.yaml','template.yaml']:
    with open(_tmp_folder + '/' + entry) as f:
        file_content = f.read()
        GLOBAL.update(yaml.load(os.path.expandvars(file_content)))

# with open(_tmp_folder + '/auth.yaml') as f:
#    str_auth = f.read()
#    GLOBAL.update(yaml.load(os.path.expandvars(str_auth)))


### local setting
### trace all config folder in the path
access_path = ""
check_path  = ""
local_config_path = ""
for entry in os.getcwd().split('/'):
    if entry == "": continue
    access_path = access_path + '/' + entry
    check_path  = access_path + '/config/local.yaml'
    if os.path.exists(check_path):
        local_config_path = check_path   
BuiltIn().log_to_console("Current local.yaml: " + local_config_path)
with open(local_config_path) as f:
    LOCAL.update(yaml.load(f))

USER = os.path.expandvars("$USER")
if 'node' in LOCAL:     NODE    = LOCAL['node']
if 'webaapp' in LOCAL:  WEBAPP = LOCAL['webapp']

newline = GLOBAL['default']['newline']




def renat_version():
    """ Returns RENAT version string
    """ 
    BuiltIn().log("RENAT version is : `%s`" % ROBOT_LIBRARY_VERSION)
    return ROBOT_LIBRARY_VERSION

def get_renat_path():
    """ Returns the absolute path of RENAT folder
    """
    return _folder

def get_item_name():
    """ Returns the name of the running item
    """
    return os.path.basename(os.getcwd())

def get_config_path():
    """ Returns absolute path of RENAT config folder path
    """
    return _folder + "/config" 

def get_item_config_path():
    """ Returns absolute path of current item config folder
    """
    return os.getcwd() + '/config'
    

def get_result_path():
    """ Returns absolute path of the current result folder
    """
    return os.getcwd() + '/' + _result_folder

def get_result_folder():
    """ Returns current result folder name. Default is ``result`` in current
    test case.

    *Note*: the keyword only returns the ``name`` of the result folder not its
    absolue path.
    """
    return _result_folder

def set_result_folder(folder):
    """ Sets the result folder to ``folder`` and return the old result folder.
    The result folder contains all output files from the test likes tester
    ouput, config file ...

    ``folder`` is a folder name that under current test case folder

    The system will create a new folder if it does not exist and set its mode to
    `0775` 

    *Note:* Result folder should be set at the begining of the test. Changing
    result folder only has effect on up comming connection
    """ 

    global _result_folder
    old_folder = _result_folder
    _result_folder = folder

    folder_path = os.getcwd() + '/' + folder
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        os.chmod(folder_path,int('0775',8))
        
    except Exception as e:
        BuiltIn().log("ERROR:" + str(e.args))
   
    # set ROBOT variable 
    # BuiltIn().set_variable('${OUTPUT DIR}', folder_path)
    # BuiltIn().set_variable('${OUTPUT DIR}', folder_path)
    # BuiltIn().set_variable('${LOG_FODER}', folder)
    BuiltIn().set_global_variable('${RESULT_FOLDER}', folder)
    BuiltIn().set_global_variable('${LOG_FODER}', folder)
    BuiltIn().set_global_variable('${RESULT_FOLDER}', folder)

    BuiltIn().log("Changed current result folder to `%s`" % (folder_path))
    return old_folder


def version():
    """ Returns the current version of RENAT
    """
    return ROBOT_LIBRARY_VERSION


def node_with_attr(attr_name,value):
    """ Returns a list of nodes which have attribute ``attr_name`` with value ``value``
    """
    result = [ node for node in NODE if attr_name in NODE[node] and NODE[node][attr_name] == value ]
    BuiltIn().log("Found %d nodes with condition `%s`=`%s`" % (len(result),attr_name,value))
    return result


def node_with_tag(*tag_list):
    """ Returns list of ``node`` from ``local.yaml`` that has *ALL* tags defined by ``tag_list``
    
    Tag was defined like this in local.yaml
|    vmx11:
|        device: vmx11
|        snmp_polling: yes
|        tag:
|            - tag1
|            - tag2
    
    Examples:
    | ${test3}=  | Common.`Node With Tag`  |  tag1 |  tag3 |  
    """

    result  = []
    s0 = Set(tag_list)
    if not LOCAL['node']: return result
    for node in LOCAL['node']:
        if 'tag' in LOCAL['node'][node]:
            s1 = Set(LOCAL['node'][node]['tag'])
            if s0.issubset(s1): result.append(node)
        else:
            BuiltIn().log("    Node `%s` has no `tag` key, check your `local.yaml`" % node) 
    BuiltIn().log("Found %d nodes have the tags(%s)" % (len(result),str(tag_list)))       
    return result

def node_without_tag(*tag_list):
    """ Returns list of ``node`` from ``local.yaml`` that  *does not has ANY* tags defined by ``tag_list``
    
    Tag was defined like this in local.yaml
|    vmx11:
|        device: vmx11
|        snmp_polling: yes
|        tag:
|            - tag1
|            - tag2
    
    Examples:
    | ${test3}=  | Common.`Node Without Tag`  |  tag1 |  tag3 |  
    """

    result  = []
    s0 = Set(tag_list)
    if not LOCAL['node']: return result
    for node in LOCAL['node']:
        if 'tag' in LOCAL['node'][node]:
            s1 = Set(LOCAL['node'][node]['tag'])
            if len(s0 & s1) == 0: result.append(node)
        else:
            BuiltIn().log("    Node `%s` has no `tag` key, check your `local.yaml`" % node) 
    BuiltIn().log("Found %d nodes do not include any tags(%s)" % (len(result),str(tag_list)))       
    return result


def mib_for_node(node):
    """ Returns the mib file name for this ``node``
    mib file is define by ``mib`` keyword under the ``node`` in ``local.yaml``
|   ...
|   node:
|       vmx11:
|           device: vmx11
|           snmp_polling: yes
|           mib: mib11.txt
|   ...

    Default value is defined by ``mib`` keyword from global
    ``config/snmp-template.yaml`` for the ``type`` of the node

    Example:
    | ${mib}=    | Common.`MIB For Node` | vmx11 | 
    """
    mib_file = None
    if 'mib' in LOCAL['node'][node]: 
        mib_file  = LOCAL['node'][node]['mib']
    if mib_file is None:
        device      = LOCAL['node'][node]['device']
        type        = GLOBAL['device'][device]['type']
        mib_file    = GLOBAL['snmp-template'][type]['mib']
    
    return mib_file


def loop_for_node_tag(var,tags,*keywords):
    """ Repeatly executes RF ``keyword`` for nodes that has tag ``tags``
    
    multi tags are separated by `:`
    keywords has same meaning with ``keywords`` used by `Run Keywords` of
    RobotFramework ( keyword and its arguments are separated by ``AND`` with the
    others.

    Example:
    | `Loop For Node Tag` | \${node} | tag1 |
    | ...  |   `Switch` |  \${node} |  AND |
    | ...  |   `Cmd`    |  show system user | AND |
    | ...  |   `Cmd`    |  show system uptime |

    *Note:* ``$`` in variable name must be escaped
    """
    nodes = node_with_tag(*tags.split(':'))
    for node in nodes:
        BuiltIn().set_test_variable(var,node)
        BuiltIn().run_keywords(*keywords)


def is_stable(seq,threshold,percentile='90'):
    """ Checks if the value sequence is stable or not
    """
    check_value = numpy.percentile(seq,percentile)
    result = (check_value < threshold)
    BuiltIn().log("check_value = %s threshold = %s result=%s" % (check_value,threshold,result) )
    return result


def str2seq(str_index,size):
    """ Returns a sequence from string format

        Samples:
        | `Str2Seq` | ::    | 5 | # (0,1,2,3,4) |
        | `Str2Seq` | :2    | 5 | # (0,1)       |
        | `Str2Seq` | 1:3   | 5 | # (1,2) |
        | `Str2Seq` | 0:5:2 | 5 | # (0,2,4) |
    """
    if ':' in str_index:
        tmp = map(lambda x: 0 if x=='' else int(x),str_index.split(':'))
        if len(tmp) > 3:
            return None
        else:
            result = range(*tmp)
            if len(result) == 0: result = range(size)
            return result
    else:
        return map(int,str_index.split(','))
    return None


def csv_select(src_file,dst_file,str_row=':',str_col=':',has_header=None):
    """ Select part of the CSV file and write it to other file
    ``str_row`` and ``str_col`` are used to specify necessary rows and columns.
    They are using the same format with slice for Python list. 
        - :  and : means all rows and columns
        - :2 and : means first 2 rows and all columns
        - :  and 1,2 means all rows and 2nd and 3rd columns
        - 0:3 and 1 means 3 rows from the 1st one(0,1,2) and second column
        - 0:5:2 and 1 means 3 rows(0,3,5) and second column
    *Notes:* 
        - Rows and columns are indexed from zero 
        - When ':' is used, the string has format: <start>:<stop> or <start>:<stop>:<step>
          For convenience, ':' means all the data, ':x' means first 'x' data

    Examples:
    | `CSV Select`  |    result/data05.csv |  result/result3.csv  | 0,1,2 |  0,1 |
    | `CSV Select`  |    result/data05.csv |  result/result4.csv  | :     |  0,1 |
    | `CSV Select`  |    result/data05.csv |  result/result5.csv  | :2    |  :   |
    | `CSV Select`  |    result/data05.csv |  result/result6.csv  | 0:3   |  :   |
    | `CSV Select`  |    result/data05.csv |  result/result7.csv  | 0:5:2 |  :   |
    
    """

    src_pd = pandas.read_csv(src_file,header=has_header)
    s = src_pd.shape

    result = src_pd.iloc[str2seq(str_row,s[0]),str2seq(str_col,s[1])]
    result.to_csv(dst_file,index=None,header=has_header)
    BuiltIn().log("Wrote to CSV file `%s`" % dst_file)


def csv_concat(src_pattern, dst_name,has_header=None):
    """ Concatinates CSV files vertically
    If the CSV files has header, set ``has_header`` to ``${TRUE}``
   
    Examples:
    | Commmon.`CSV Merge` | config/data0[3,4].csv |  result/result2.csv | |
    | Commmon.`CSV Merge` | config/data0[3,4].csv |  result/result2.csv | has_header=${TRUE} |
    """

    file_list = glob.glob(src_pattern)
    num = len(file_list)
    if num < 1:
        BuiltIn().log("Could not find any file to concatinate")
        return False
    file = file_list.pop(0) 
    pd   = pandas.read_csv(file,header=has_header)
    for file in file_list:
        pd_next = pandas.read_csv(file,header=has_header)
        pd = pandas.concat([pd, pd_next])  

    pd.to_csv(dst_name,index=None,header=has_header)
    BuiltIn().log("Concatinated %d files to %s" % (num,dst_name))
    return True

def csv_merge(src_pattern,dst_name,on_key='0',has_header=None):
    """ Merges all CSV files horizontally by ``on_key`` key from ``src_pattern``
 
    ``on_key`` is the order of key column that is used as key when merging the
    files. Default is zero.

    When ``has_header`` is not ``None`` (default value), it is the order of the
    row used to make the column name.
    Returns ``False`` if only one file was found, no merging happend

    Examples:
    | Common.`CSV Merge` | config/data0[3,4].csv | result/result2.csv |
    | Common.`CSV Merge` | config/data0[3,4].csv | result/result2.csv | has_header=${TRUE} |
    """

    file_list = glob.glob(src_pattern)
    num = len(file_list)
    int_key = int(on_key)
    
    if num < 1: 
        BuiltIn().log("File number is less than %d" % (num))
        return False
    elif num < 2:
        f1_name = file_list.pop(0)
        f1  = pandas.read_csv(f1_name,header=has_header)
        f1.to_csv(dst_name,index=None,header=has_header)
        BuiltIn().log("File number is less than %d, merged anyway" % (num))
        return True 
    else:
        f1_name = file_list.pop(0)
        f2_name = file_list.pop(0)

        f1  = pandas.read_csv(f1_name,header=has_header)
        f2  = pandas.read_csv(f2_name,header=has_header)
        m   = pandas.merge(f1,f2,on=int_key)
        for item in file_list:
            f = pandas.read_csv(item,header=has_header)
            m = pandas.merge(m,f,on=int_key)
       
        m.to_csv(dst_name,index=None,header=has_header)
        BuiltIn().log("Merged %d files to %s" % (num,dst_name))
   
    return True 

def merge_files(path_name,file_name):
    """ Merges all the text files defined by ``path_name`` to ``file_name``

    Example:
    | `Merge Files`  |  ./result/*.csv |  ./result/test.csv  |
    """
    file_list = glob.glob(path_name)
    with open(file_name,'w') as fout:
        fin = fileinput.input(file_list)
        for line in fin:
            fout.write(line)
        fin.close()
    BuiltIn().log("Merges %d files to %s" % (len(file_list),file_name))


def create_sequence(start,end,interval,option='float'):
    """ Creates a list with number from ``start`` to ``end`` with ``interval``
    
    Example:
    | @{list}= | `Create Sequence` | 10 | 15 | 0.5 |
    will create a list of ``[11.0, 11.5, 12.0, 12.5, 13.0, 13.5, 14.0, 14.5]``
    """
    result = []
    if option == 'float':
        result = numpy.arange(float(start),float(end),float(interval)).tolist()
    if option == 'int':
        result = numpy.arange(int(start),int(end),int(interval)).tolist()
    return result

def change_mod(name,mod,relative=False):
    """ Changes file mod, likes Unix chmod

    ``mod`` is a string specifying the privilege mode
    ``relative`` is ``False`` or ``True``

    Examples:
    | Common.`Change Mod` | tmp | 0775 |
    """
    if relative:
        path = os.getcwd() + "/" + name
    else:
        path = name
    os.chmod(path,int(mod,8))
    BuiltIn().log("Changed `%s` to mode %s" % (path,mod))

def get_test_device():
    """ Return a list of all test device that is used in this test

    *Notes:* Device number could less than node number
    """

    devices = []
    for node_name,node in LOCAL["node"].iteritems():
        device = node["device"]
        if device not in devices: devices.append(device)
    return devices

def md5(str):
    """ Returns MD5 hash of a string
    """
    return hashlib.md5(str).hexdigest()


def file_md5(path):
    """ Returns MD5 hash of a file
    
    ``path`` is an absolute path
    """
    hash_md5 = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""): hash_md5.update(chunk)

    result = hash_md5.hexdigest()
    BuiltIn().log("Hash of file `%s` is %s" % (path,result))
    return result


def pause(msg="",time_out='3h',error_on_timeout=True,default_input=''):
    """ Displays the message ``msg`` and pauses the test execution and wait for user input

    In case of ``error_on_timeout`` is True(default), the keyword will raise an
    error when timeout occurs. Otherwise, it will continue the test.

    *Notes:* If the variable ``${RENAT_BATCH}`` was defined, the keyword will print out
    the message and keeps running without pausing.

    Examples:
    | Common.`Pause` | Waiting... | 10s | error_on_timeout=${TRUE} | default input | 
    | Common.`Pause` | Waiting... | 10s | 
    """

    BuiltIn().log("Pause and wait `%s` for user input" % time_out)
    BuiltIn().log_to_console(msg)
    input = None
    wait = DateTime.convert_time(time_out)

    renat_batch = BuiltIn().get_variable_value('${RENAT_BATCH}')
    if renat_batch is None: 
        i, o, e = select.select( [sys.stdin], [], [], wait)
        if i:
            input = sys.stdin.readline().strip()
            BuiltIn().log("User input detected. Input was `%s`" % input)
        else:
            if not error_on_timeout:
                input = default_input
                BuiltIn().log("Pause finished with time out. Input was `%s`" % input)
            else:
                raise Exception("ERROR: timeout while waiting for user input")
    else:
        BuiltIn().log("Pausing is ignored in batch mode")
    return input


def diff_file(path1,path2,newline=True):
    """ Shows difference between files

    Returns the diff result (multi lines)
    ``path1``, ``path2`` are absolute paths.
    """
    result = ""
    with codecs.open(path1,'r','utf-8') as f: f1 = f.readlines()
    with codecs.open(path2,'r','utf-8') as f: f2 = f.readlines()

    if newline:
        f1[-1] = f1[-1]+'\n'
        f2[-1] = f2[-1]+'\n'
    

    d = difflib.context_diff(f1,f2,fromfile=path1,tofile=path2)
    result  = ''.join(d)

    BuiltIn().log("Compared `%s` and `%s`" % (path1,path2))
    return result


def ping_until_ok(node,wait_str='5s',extra='-c 3'):
    """ Ping a ``node`` until it gets response. Then wait for more ``wait_str``
    Default ``extra`` option is ``-c 3``
    """

    device  = LOCAL['node'][node]['device']
    ip      = GLOBAL['device'][device]['ip']
    result  = os.system("ping %s %s" % (extra,ip))

    wait = DateTime.convert_time(wait_str)
    time.sleep(wait)
    
    BuiltIn().log("Pinged to host `%s(%s)` with result = %d" % (node,ip,result))

    return result

def _run_async(func):
    from threading import Thread
    from functools import wraps

    @wraps(func)
    def async_func(*args, **kwargs):
        func_hl = Thread(target=func, args=args, kwargs=kwargs)
        func_hl.start()
        return func_hl
    return async_func


def _wait_thread(*stuff):
    for something in stuff: something.join()


def count_keyword_line(keyword,*pattern_list):
    """ Count the number of lines contains the ``keyword``

    *Notes:* Keyword is matched partially. For example, ``error`` or
    ``errorXXX`` will be matched by ``error`` keyword.
    """
    counter = 0
    for pattern in pattern_list:
        file_list = glob.glob(pattern)
        for file in file_list:
            with open(file,"r") as f:
                BuiltIn().log("Check keyword in file `%s`" % file)
                for i,line in enumerate(f.readlines()):
                    pattern = re.compile(keyword.lower())
                    if re.search(pattern,line.lower()): 
                        counter += 1
                        BuiltIn().log("    Found matched keyword in line number: %d" % (i))

    BuiltIn().log("Found %d lines contain keyword `%s`" % (counter,keyword))
    return counter
    


def keyword_line_should_not_be_bigger_than(num,keyword,*pattern_list):
    """ Checks whether the number of line containing the keyword be less than a number
    """ 
    counter = count_keyword_line(keyword, *pattern_list)

    if counter <= int(num):
        BuiltIn().log("Found %d lines `%s`" % (counter,keyword))
        return True
    else:
        raise Exception("Found %d lines that matched `%s`, bigger than %s" % (counter,keyword,num))
        return False   


def count_match_regexp(regexp,*pattern_list):
    """ Count the number of ``regex`` found in ``pattern_list``

    Examples:
    | ${err_num}= | `Count Match RegExp` | .*error.* | result/*.csv | result/*.txt |
    """
    counter = 0
    for pattern in pattern_list:
        file_list = glob.glob(pattern)
        for file in file_list:
            with open(file,"r") as f:
                BuiltIn().log("Find pattern `%s` in file `%s`" % (regexp,file))
                for i,line in enumerate(f.readlines()):
                    res = re.match(regexp, line)
                    if res is None: continue
                    counter += 1 
                    BuiltIn().log("    Found match in line number: %d" % (i))

    BuiltIn().log("Found %d matching of `%s`" % (counter,regexp))
    return counter


def count_keyword(keyword,*pattern_list):
    """ Count the keyword in files. Keyword is not case-sensitive
    """ 

    counter = 0
    for pattern in pattern_list:
        file_list = glob.glob(pattern)
        for file in file_list:
            with open(file,"r") as f:
                BuiltIn().log("Check keyword in file `%s`" % file)
                for word in [word for line in f for word in line.split()]:
                    if word.lower() == keyword.lower(): counter += 1

    BuiltIn().log("Found %d keyword `%s`" % (counter,keyword))
    return counter

    
def keyword_should_not_be_bigger_than(num,keyword,*pattern_list):
    """ Checks whether the number of keyword be less than a number
    """ 
    counter = count_keyword(keyword, *pattern_list)

    if counter <= int(num):
        BuiltIn().log("Found %d of keyword `%s`" % (counter,keyword))
        return True
    else:
        raise Exception("Number of `%s` is %d, bigger than %s" % (keyword,counter,num))
        return False   


def error_should_not_be_bigger_than(num,*pattern_list):
    """ Checks whether the number of ``error`` be less than a number
    """ 
    return keyword_should_not_be_bigger_than(num,'error',*pattern_list)


def error_line_should_not_be_bigger_than(num,*pattern_list):
    """ Checks whether the number of lines that contains ``error`` be less than a number
    """ 
    return keyword_line_should_not_be_bigger_than(num,'error',*pattern_list)


def get_file_without_error(file_path):
    """ Get content of the file and return null string if the file does not
    exist
    """
    result = ""
    if not os.path.exists(file_path): 
        BuiltIn().log("File `%s` does not exist but keep going" % file_path)
    else:
        with codecs.open(file_path,'r','utf-8') as f:
            result = f.read()
        BuiltIn().log("Read file `%s`" % file_path)
    return result


def fold_str(str):
    """ Folds a string by adding Non-Width-Space char (0x200b) at 6th char
    """
    s1 = str[:6]
    s2 = str[6:]
    if s2 != '' :
        result = s1 + u'\u200b' + s2
    else:
        result = s1
    return result


def follow_syslog_and_trap(pattern,log_file_name='syslog-trap.log',delay_str='1s'):
    """ Pauses the execution and wait for the pattern is matched if the file
    `log_file_name` located in the current result folder.

    By default the `log_file_name` is `./result/syslog-trap.log` which is
    created by `Follow Syslog and Trap` keyword.

    The keyword should be in tests between `Follow Syslog adn Trap Start` and
    `Follow Syslog and Trap Stop` keywords.
    """

    match_pattern = re.compile(pattern)
    log_file = open(os.getcwd() + '/' +  _result_folder + '/' + log_file_name)
    log_file.seek(0,os.SEEK_END)

    vchannel_instance = BuiltIn().get_library_instance('VChannel')

    wait_msg = "Waiting for `%s` in file `%s`" % (pattern,log_file_name)

    BuiltIn().log_to_console(wait_msg)
    BuiltIn().log(wait_msg)

    renat_batch = BuiltIn().get_variable_value('${RENAT_BATCH}')
    if renat_batch is None: 
        while True:
            line = log_file.readline()
            if not line or line == '':
                time.sleep(DateTime.convert_time(delay_str))
                vchannel_instance.flush_all() 
            else:
                if match_pattern.search(line): break
    else:
        BuiltIn().log("Pausing is ignored in batch mode")

    log_file.close()
    BuiltIn().log('Found pattern `%s` in log file `%s`' % (pattern,log_file_name))

def set_multi_item_variable(*vars):
    """ Set multiple varibles to be `suite variable` at the same time

    Suite variables (or item variable) could be access anywhere in all the item
    scenario.
    """
    for var in vars:
        BuiltIn().set_suite_variable(var)
    BuiltIn().log('Set %d variables to suite(item) scope' % len(vars))

def random_number(a='0',b='99'):
    """ Returns a random number between [a,b]
    """
    result = random.randint(int(a),int(b))
    BuiltIn().log("Created a random number as `%d`" % result)
    return result

def random_name(base,a='0',b='99'):
    """ Returns a random name by a `base` and a random number between [a,b]

    Example:
    | ${FOLDER}= |   `Random Name` | capture_%05d | 0 | 99 | 
    """

    number = random.randint(int(a),int(b))
    result = base % number
    BuiltIn().log("Created a random name  as `%s`" % result)
    return result

def convert_html_to_pdf(html_file,pdf_file):
    """ Converts html file to pdf file
    """
    options = {
        'page-size': 'A4',
        'margin-top': '0.1in',
        'margin-right': '0.1in',
        'margin-bottom': '0.1in',
        'margin-left': '0.1in',
        'encoding': "UTF-8",
        'no-outline': None
    }
    pdfkit.from_file(html_file,pdf_file,options)
    BuiltIn().log("Converted `%s` to `%s`" % (html_file,pdf_file))


def cleanup_result(ignore=u'^(log.html|output.xml|report.html)$'):
    """ Cleans up the result folder 

    Deletes all files in current active folder that does not match the
    ``ignore`` expression and are older than the time the test has started.

    *Note*: The keyword only removes files but not folders
    """
  
    BuiltIn().log("Delete files in result folder `%s`" % _result_folder) 
    candidates=[] 
    for root, dirs, files in os.walk(_result_folder):
        for basename in files:
            if not re.search(ignore,basename) and not '/.svn' in root:
                file_path = os.path.join(root,basename)
                modified_time = os.path.getmtime(file_path)
                if modified_time < int(START_TIME.strftime('%s')):
                    candidates.append(file_path)

    for x in candidates:
        os.remove(x)
        BuiltIn().log("    Deleted `%s`" % x)
    BuiltIn().log("Deleted %d files in current result folder" % len(candidates))


def slack(msg,channel='#automation_dev',user='renat',host=GLOBAL['default']['slack-host']):
    """ Post a message to Slack
    """

    BuiltIn().log("Post message to Slack")
    renat_batch = BuiltIn().get_variable_value('${RENAT_BATCH}')
    if renat_batch is None:
        cmd = GLOBAL['default']['slack-cmd']
        subprocess.call([cmd, msg, channel, user, host])
        BuiltIn().log("Posted message `%s` to Slack channel `%s`" % (msg,channel))
    else:
        BuiltIn().log("Ignored Slack msg in batch mode")


def load_plugin():
    """ Load plugin in renat/plugin folder
    """
    for item in glob.glob(get_renat_path() + '/plugin/*.robot'):
        plugin_name = os.path.basename(item)
        BuiltIn().import_resource('./plugin/' + plugin_name)
        BuiltIn().log("Loaded plugin `%s`" % plugin_name)
    

# set RF global variables and load libraries
try:
    

    BuiltIn().set_global_variable('${GLOBAL}',GLOBAL)
    BuiltIn().set_global_variable('${LOCAL}',LOCAL)
    BuiltIn().set_global_variable('${USER}',USER)
    BuiltIn().set_global_variable('${NODE}', NODE)
    BuiltIn().set_global_variable('${WEBAPP}', WEBAPP)
    BuiltIn().set_global_variable('${START_TIME}', START_TIME)

    # define Ctrl A-Z
    for i,char in enumerate(list(string.ascii_uppercase)):
        BuiltIn().set_global_variable('${CTRL_%s}' % char,chr(int(1+i)))

    # set log level
    BuiltIn().set_log_level(self.GLOBAL['default']['log-level'])

except:
    log("ERROR: Error happened  while setting global configuration")

