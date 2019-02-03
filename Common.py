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

# $Rev: 1764 $
# $Ver: $
# $Date: 2019-02-04 08:52:38 +0900 (月, 04  2月 2019) $
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
There are 2 important configuration files. The global configuration files (aka
master files) include device information, authentication etc that are used for
all the test cases in the suite. The local configuration file ``local.yaml``
includes information about nodes, tester ports etc. that are used in a specific
test case.

At the beginning, the module makes a local copy the master files and initialize
necessary variables.

The RENAT framework utilized the YAML format for its configurations file.

The master files folder is defined by ``renat-master-folder`` in
``$RENAT_PATH/config/config.yaml``. Usually, users do not need to modify the
master files. The most common case is when new device is deployed, the
``device.yaml`` need to be update so that device could be used in the test
cases.

=== 1. device.yaml: contains global device information ===

Each device information is store under ``device`` block and has the following
format:

| <node_name>
|     type:             <device type>
|     description:      <any useful description>
|     ip:               <the IPv4 address of the device

Where <node_name> is the name of the device. It could be the name of a switch,
router or a web appliance box and should be uniq between the devices.
<description> is any useful information and <ip> is the IP that RENAT
uses to access the device.

<type> is important because it will be used as the ky of the ``access_template``
in template file. Usually users do not need to invent a new type but should use
the existed type. When a new platform need to be supported, a new type will be
introduced with the correspon template and authentication information.

Samples:
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
    

=== 2. template.yaml: contains device template information ===

The template file contains information about how to access to the device and how
it should polling information ( SNMP only for now). Each template has the
following format:

<type>:
    access:         <ssh or telnet>
    auth:           <plaint-text or public-key>
    profile:        <authentication profile name>
    prompt:         <a regular expression for the PROMPT of the CLI device> (optional)
    login_prompt:   <a login PROMPT for CLI device> (optional)
    password_prompt:<a PROMPT for asking password of CLI device> (optional)   
    append:         <a pharase to append automatically for every CLI command
that executes> on this device (optional>
    init:           <an array of command that will be executed automatically
after a sucessful login of CLI device> (optional) 

*Note*: Becareful about the prompt field. Usually RENAT will wait until it could
see the prompt in its output. A wrong prompt will halt the system until it is
timed out.

Samples:

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


=== 3. auth.yaml: contains authentication information ===

The file contains authentication information that system uses when access to a
device. Each authencation type has follwing format:

| plain-text
|    <profile> 
|        user:       <user name>
|        password:   <password> 
or
| public-key:
|    <profile>:
|        user:       <user name>
|        key:        <public key path>

Where <profile> is the name of the authentication profile specificed in the
``access template`` of the device

Sample:
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

When user used the wizard ``item.sh`` to create a new test case, they have the
ability to crete new ``local.yaml`` or not. ``local.yaml`` could be edited and
inserted new information later to hold more informations for the test case.

When a test is run, it will display its current active ``local.yaml``

The local configuration file of each test item is stored in the ``config``
folder of the item as ``local.yaml`

Usually the ``local.yaml`` has following parts:
- CLI node information: started by ``node`` keyword
- WEB node information: started by ``webapp`` keyword
- Tester device information: started by ``tester`` keyword
- Default information: automatically created and started by ``default`` keyword
- And other neccessary information for the test by yaml format 



Sample:

| # CLI node
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
| # web application information
| webapp:
|     arbor-sp-a:
|         device: arbor-sp-a
|         proxy:
|             http:   10.128.8.210:8080
|             ssl:    10.128.8.210:8080
|             socks:  10.128.8.210:8080
|
| # Tester information
| tester:
|     tester01:
|         type: ixnet
|         ip: 10.128.32.70
|         config: vmx_20161129.ixncfg
|
| # Other user information| 
| port-mapping:
|     uplink01:
|         device: vmx11
|         port: ge-0/0/0
|     downlink01:
|         device: vmx12
|         port: ge-0/0/2
|
| # Default information 
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

ROBOT_LIBRARY_VERSION = 'RENAT 0.1.12'

import os,socket
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
import pyscreenshot as pyscreenshot
from pyvirtualdisplay import Display
from selenium.webdriver.common.keys import Keys
try:
    from sets import Set
except:
    pass
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
DISPLAY = None
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
    file_content = f.read()
    GLOBAL.update(yaml.load(os.path.expandvars(file_content)))

### copy config file from maser to tmp
### overwrite the current files
_tmp_folder = _folder + '/tmp/'
# _tmp_folder = os.getcwd() + '/tmp/'
_renat_master_folder    = GLOBAL['default']['renat-master-folder']

#lock_file = _renat_master_folder + '/tmp.lock'
#with open(lock_file,'r') as lock:
#    while True:
#        try:
#            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
#            shutil.copy2(_renat_master_folder+'/device.yaml',_tmp_folder)
#            shutil.copy2(_renat_master_folder+'/auth.yaml',_tmp_folder)
#            shutil.copy2(_renat_master_folder+'/template.yaml',_tmp_folder)
#            break
#        except IOError as e:
#            time.sleep(1)

_calient_master_path    = GLOBAL['default']['calient-master-path']
if _calient_master_path:
    newest_calient = max(glob.iglob(_calient_master_path))
    shutil.copy2(newest_calient,_tmp_folder + "/calient.xlsm")

_ntm_master_path        = GLOBAL['default']['ntm-master-path']
# if _ntm_master_path:
#    _ntm_master_path = os.path.expandvars(_ntm_master_path)
if _ntm_master_path:
    newest_ntm = max(glob.iglob(_ntm_master_path))
    shutil.copy2(newest_ntm,_tmp_folder + "/g4ntm.xlsm")


### expand environment variable and update GLOBAL config
for entry in ['auth.yaml', 'device.yaml','template.yaml']:
    with open(_renat_master_folder + '/' + entry) as f:
    # with open(_tmp_folder + '/' + entry) as f:
        file_content = f.read()
        retry = 0
        if len(file_content) == 0 and retry < 3:
            time.sleep(5) 
            BuiltIn().log_to_console("WARN: could not access file %s. Will retry" % entry)
            file_content = f.read()
            retry += 1
        if retry == 3: 
            BuiltIn().log_to_console("ERROR: could not get global config correctly")
        GLOBAL.update(yaml.load(os.path.expandvars(file_content)))


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

if local_config_path == '':
    BuiltIn().log_to_console("WARN: Could not find the local config file")
else:    
    with open(local_config_path) as f:
        LOCAL.update(yaml.load(f))
    BuiltIn().log_to_console("Current local.yaml: " + local_config_path)

USER = os.path.expandvars("$USER")
HOME = os.path.expandvars("$HOME")

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
    BuiltIn().set_global_variable('${LOG_FODER}', folder)
    BuiltIn().set_global_variable('${RESULT_FOLDER}', folder)
    BuiltIn().set_global_variable('${RESULT_PATH}', folder_path)

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
    """ Returns list of ``node`` or ``webapp`` from ``local.yaml`` that has *ALL* tags defined by ``tag_list``
    
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
   
    if sys.version_info[0] > 2:
        s0 = set(tag_list)
        if 'node' in LOCAL and LOCAL['node']:
            for item in LOCAL['node']:
                if 'tag' in LOCAL['node'][item]:
                    if LOCAL['node'][item]['tag']:
                        s1 = set(LOCAL['node'][item]['tag'])
                    else:
                        s1 = set()
                    if s0.issubset(s1): result.append(item)
        if 'webapp' in LOCAL and LOCAL['webapp']:
            for item in LOCAL['webapp']:
                if 'tag' in LOCAL['webapp'][item]:
                    if LOCAL['webapp'][item]['tag']:
                        s1 = set(LOCAL['webapp'][item]['tag'])
                    else:
                        s1 = set()
    else: 
        s0 = Set(tag_list)
        if 'node' in LOCAL and LOCAL['node']:
            for item in LOCAL['node']:
                if 'tag' in LOCAL['node'][item]:
                    s1 = Set(LOCAL['node'][item]['tag'])
                    if s0.issubset(s1): result.append(item)
        if 'webapp' in LOCAL and LOCAL['webapp']:
            for item in LOCAL['webapp']:
                if 'tag' in LOCAL['webapp'][item]:
                    s1 = Set(LOCAL['webapp'][item]['tag'])
                    if s0.issubset(s1): result.append(item)

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
    if sys.version_info[0] > 2:
        s0 = set(tag_list)
        if not LOCAL['node']: return result
        for node in LOCAL['node']:
            if 'tag' in LOCAL['node'][node]:
                if LOCAL['node'][node]['tag']:
                    s1 = set(LOCAL['node'][node]['tag'])
                else:
                    s1 = set()
                if len(s0 & s1) == 0: result.append(node)
            else:
                BuiltIn().log("    Node `%s` has no `tag` key, check your `local.yaml`" % node) 
    else:
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
        # tmp = map(lambda x: 0 if x=='' else int(x),str_index.split(':'))
        tmp = [ int(x) if x!='' else 0 for x in str_index.split(':') ]
        if len(tmp) > 3:
            return None
        else:
            result = range(*list(tmp))
            if len(result) == 0: result = range(size)
            return result
    else:
        # return list(map(int,str_index.split(',')))
        return [ int(x) for x in str_index.split(',') ]
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


def csv_concat(src_pattern, dst_name,input_header=None,result_header=True):
    """ Concatinates CSV files vertically
    If the CSV files has header, set ``has_header`` to ``${TRUE}``
   
    Examples:
    | Commmon.`CSV Concat` | config/data0[3,4].csv |  result/result2.csv | |
    | Commmon.`CSV Concat` | config/data0[3,4].csv |  result/result2.csv | has_header=${TRUE} |
    """

    file_list = sorted(glob.glob(src_pattern))
    num = len(file_list)
    if num < 1:
        BuiltIn().log("Could not find any file to concatinate")
        return False
    file = file_list.pop(0) 
    pd   = pandas.read_csv(file,header=input_header)
    for file in file_list:
        pd_next = pandas.read_csv(file,header=input_header)
        pd = pandas.concat([pd, pd_next])  

    pd.to_csv(dst_name,index=None,header=result_header)
    BuiltIn().log("Concatinated %d files to %s" % (num,dst_name))
    return True


def csv_merge(src_pattern,dst_name,input_header=None,key='0',select_column=':',result_header=True):
    """ Merges all CSV files ``horizontally`` by ``key`` key from ``src_pattern``
 
    ``input_header`` defines whether the input files has header row or not. If
    ``input_header`` is ``${NULL}``, the keyword assume that input files have no
    header and automatically define columns name. When ``input_header`` is not
    null (default is zero), the row define by ``input_header`` will be used as header
    and data is counted from the next row.

    ``select_column`` is a string that define the output columns and ``key`` is the
    column name that used to merge. When ``input_header`` is ``${NULL}``,
    ``select_column`` and `key` is the index of columns. Otherwise, they are
    `column name`.

    The result header (column names) is decided by ``result_header`` (`True` or `False`)

    The keyword returns ``False`` if no file is found by the pattern

    Examples:
    | Common.`CSV Merge` | config/data0[3,4].csv | result/result2.csv |
    | Common.`CSV Merge` | config/data0[3,4].csv | result/result2.csv | input_header=0 |
    | Common.`CSV Merge` | src_pattern=${RESULT_FOLDER}/balance*.csv  | input_header=0 |
    | ...                | dst_name=${RESULT_FOLDER}/result.csv | result_header=${FALSE} |
    | ...                | key=Stat Name      |      select_column=Valid Frames Rx. |
    | Common.`CSV Merge` | src_pattern=${RESULT_FOLDER}/balance*.csv  | input_header=${NULL} |
    | ...                | dst_name=${RESULT_FOLDER}/result.csv | result_header=${FALSE} |
    | ...                | key=0      |      select_column=5 |
    """

    file_list = sorted(glob.glob(src_pattern))
    num = len(file_list)

    if not select_column == ':':
        columns = '%s,%s' % (key,select_column)
    else:
        columns = select_column
    
    if num < 1: 
        BuiltIn().log("File number is less than %d" % (num))
        return False
    elif num < 2:
        f1_name = file_list.pop(0)
        if input_header is None:
            f1  = pandas.read_csv(f1_name,header=input_header)
            s = f1.shape
            result = f1.iloc[:,str2seq(columns,s[1])]
        else:
            f1  = pandas.read_csv(f1_name,header=int(input_header))
            result = f1[columns.split(',')]
        result.to_csv(dst_name,index=None,header=result_header)
        BuiltIn().log("File number is less than %d, merged anyway" % (num))
        return True 
    else:
        f1_name = file_list.pop(0)
        f2_name = file_list.pop(0)

        if input_header is None:
            f1  = pandas.read_csv(f1_name,header=input_header)
            f2  = pandas.read_csv(f2_name,header=input_header)
            s = f1.shape
            result1 = f1.loc[:,str2seq(columns,s[1])]
            s = f2.shape
            result2 = f2.loc[:,str2seq(columns,s[1])]
        else:
            f1 = pandas.read_csv(f1_name,header=int(input_header))
            f2 = pandas.read_csv(f2_name,header=int(input_header))
            result1 = f1[columns.split(',')]
            result2 = f2[columns.split(',')]

        if input_header is None:
            m  = pandas.merge(result1,result2,on=int(key))
        else:
            m  = pandas.merge(result1,result2,on=key)

        for item in file_list:
            if input_header is None:
                f = pandas.read_csv(item,header=input_header)
                s = f.shape
                result = f.iloc[:,str2seq(columns,s[1])]
            else:
                f = pandas.read_csv(item,header=int(input_header))
                result = f[columns.split(',')]
            
            if input_header is None:    
                m = pandas.merge(m,result,on=int(key))
            else:
                m = pandas.merge(m,result,on=key)
      
        # write to file without index 
        m.to_csv(dst_name,index=None,header=result_header)
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


def slack(msg,channel='#automation_dev',user='renat',host=GLOBAL['default']['slack-proxy']):
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

   
def explicit_run():
    """ skip the test case if global_variable RUN_ME is not defined

    Sample scenario:
    | 00. Cabling |
    | Common.`Explicit Run` |
    | Log To Console        |          cabling... |
    
    ``run.sh`` will bypass ``00. Cabling`` by default. In other to run this test
    case `${FORCE}` needs declared globally ``run.sh -X -v FORCE``
    
    """
    var = BuiltIn().get_variable_value('${FORCE}')
    if var != '':
        BuiltIn().pass_execution('Bypassed this step')
 

def get_myid():
    return BuiltIn().get_variable_value('${MYID}')


def get_config_value(key,base=u'default',default=None):
    """ Returns value of a key for renat configuration with this other
        LOCAL[base][key] > GLOBAL[base][key] > None
    """
    if base in LOCAL and key in LOCAL[base]:
        return LOCAL[base][key]
    if base in GLOBAL and key in GLOBAL[base]:
        return GLOBAL[base][key]
    else:
        return default
    return None


def log_csv(csv_file,index=False,border=0):
    """ Logs a content of ``csv_file`` into default log.html

    `index`, `border` are table attributes
    """
    df = pandas.read_csv(csv_file)
    BuiltIn().log(df.to_html(index=index,border=border),html=True)    


def wait(wait_time,size=10):
    """ Waits for `wait-time` and display the proress bar

    `wait_time` used RF `DateTime` format.
    
    Examples:
    | Common.`Wait` | wait_time=30s | size=10 |
    """
    wait_sec = DateTime.convert_time(wait_time)
    length = int(size)
    # if length > wait_sec: length = int(wait_sec)
    step = float(wait_sec/length)
    display = '%3.2fsecs [%%-%ds] %%02d%%%%' % (wait_sec,int(size))
    del_size = len(display % ('',0)) 
    BuiltIn().log_to_console(display % ('',0),'STDOUT',True)
    for i in range(length):
        BuiltIn().log_to_console('\010'*del_size + display % ('='*i,int(i*100/length)),'STDOUT',True)
        time.sleep(step)
    i = length
    BuiltIn().log_to_console('\010'*del_size + display % ('='*i,int(i*100/length)),'STDOUT',True)
    # BuiltIn().log_to_console('')
    BuiltIn().log('Slept `%d` seconds' % wait_sec)


def start_display():
    """ Starts a virtual display
    """
    global DISPLAY
    display_info = get_config_value('display')
    DISPLAY = Display(visible=0, size=(display_info['width'],display_info['height']))
    # DISPLAY = Display(visible=0, size=(display_info['width'],display_info['height']),fbdir=get_result_path())
    DISPLAY.start()
    time.sleep(2)
    BuiltIn().log('Started a virtual display as `%s`' % DISPLAY.new_display_var)


def close_display():
    """ Closes the opened display
    """
    global DISPLAY
    # tmpfile = '/tmp/xvfb.%s' % DISPLAY.new_display_var.replace(':','')
    # cmd = '/usr/bin/xwd -display %s -root -out %s' % (DISPLAY.new_display_var, tmpfile)
    # BuiltIn().log_to_console(cmd)
    # subprocess.Popen(cmd,shell=True)
    # screenshot.grab(childprocess=True).save('/tmp/test.png')
    DISPLAY.stop()
    DISPLAY.sendstop()
    BuiltIn().log('Closed the virtual display')


def screenshot(file_path):
    """ Capture whole display to a file specified by ``file_path``

    *Notes*: This keyword saves the whole virtual screen(monitor), while the
    familiar WebApp.`Screenshot Capture` only saves the portion of the web
    browser. But in contrast, the WebApp.`Screenshot Capture` could do `fullpage
    capture` depending on the content of the browser.
    """
    # pyscreenshot.grab(childprocess=True).save(file_path)
    pyscreenshot.grab().save(file_path)
    BuiltIn().log("Saved current display to file `%s`" % file_path)


def csv_create(pathname, *header):
    """ Create a CSV file with headers defined by a list `header`
    
    The CSV file is opend with `UTF-8` encoding mode
    """
    if sys.version_info[0] > 2:
        with open(pathname, 'w', encoding='utf-8') as f:
            f.write(','.join(header))
    else:
        with codecs.open(pathname, 'w', 'utf-8') as f:
            f.write(','.join(header))
    BuiltIn().log('Create an empty CSV file `%s`' % pathname)


def csv_add(pathname, *items):
    """ Add more data define by a list `items` to a existed CSV file

    *Note:*: do not check the consistency between item's number and header's
    number
    """
    if sys.version_info[0] > 2:
        with open(pathname, 'a', encoding='utf-8') as f:
            f.write("\r\n")
            f.write(','.join(items))
    else:
        with codecs.open(pathname, 'a', 'utf-8') as f:
            f.write("\r\n")
            f.write(','.join(items))
    BuiltIn().log('Added more data to CSV file `%s`' % pathname)
    

def send(sock,data,recv_buffer_size=1024,encode='utf-8'):
    """ Sends bytes of `data` by socket `sock` and reicve the response

    When `recv_buffer_size` is zero, the function does not execpt a response
    from the remote.
    """
    if (sys.version_info > (3, 0)):
        data_buffer = bytes(data,encode)
        sock.send(data_buffer)
        if recv_buffer_size != 0:
            recv_buffer = sock.recv(recv_buffer_size)
            return recv_buffer.decode(encode) 
    else:
        sock.send(data)
        if recv_buffer_size != 0:
            recv_buffer = sock.recv(recv_buffer_size)
            return recv_buffer 


def convert_xml(style,src,dst):
    """ Converts XML by using XLS stylesheet

    Predefined stylesheets are store in `tools/xls` under current active RENAT
    folder

    Parameters:
    - style: path to stylesheet
    - src: path to the XML source
    - dst: path to the output file
    """
    output = subprocess.check_output(['xsltproc',style,src])
    with open(dst,'w') as f:
        if (sys.version_info > (3, 0)):
            f.write(output.decode('utf-8').strip("\n"))
        else:
            f.write(output.strip("\n"))
    BuiltIn().log('Converted from `%s` to `%s` use stylesheet `%s`' % (src,dst,style)) 
    

def get_multi_lines(data,index):
    """ Returns multiple lines from text data using `index`
    
    `index` uses python rule.
    """
    tmp = data.splitlines()
    result = eval('\'\\n\'.join(tmp[%s])' % index)
    return result 


# set RF global variables and load libraries
# in doc create mode, there is not RF context, so we need to bypass the errors
try:
    

    BuiltIn().set_global_variable('${GLOBAL}',GLOBAL)
    BuiltIn().set_global_variable('${LOCAL}',LOCAL)
    BuiltIn().set_global_variable('${USER}',USER)
    BuiltIn().set_global_variable('${HOME}',HOME)
    BuiltIn().set_global_variable('${NODE}', NODE)
    BuiltIn().set_global_variable('${WEBAPP}', WEBAPP)
    BuiltIn().set_global_variable('${START_TIME}', START_TIME)

    # define Ctrl @A-Z[\]^_ string by ASCII code
    for i,char in enumerate(list('@'+string.ascii_uppercase+'[\]^_')):
        BuiltIn().set_global_variable('${CTRL_%s}' % char,chr(i))

    # other unicode keys from Selenium Key
    for key in filter(lambda x:x[0].isupper(),dir(Keys)):
        BuiltIn().set_global_variable('${Keys.%s}' % key, getattr(Keys,key))
    BuiltIn().set_global_variable('${Keys.WIN}', u'\u00FF')
    BuiltIn().set_global_variable('${Keys.WINDOWS}', u'\u00FF')
    BuiltIn().set_global_variable('${Keys.CTRL_ALT_DEL}',Keys.CONTROL + Keys.ALT + Keys.DELETE)
    BuiltIn().set_global_variable('${CTRL_ALT_DEL}',Keys.CONTROL + Keys.ALT + Keys.DELETE)

    # set log level
    BuiltIn().set_log_level(GLOBAL['default']['log-level'])

except Exception as e:
    # incase need to debug uncomment following
    # raise 
    log("ERROR: Error happened  while setting global configuration")
    
