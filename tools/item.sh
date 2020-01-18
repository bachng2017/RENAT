#!/bin/bash
# -*- coding: utf-8 -*-

""":"
for cmd in python3.6 python3.5 python3 python2 python; do
    command -v > /dev/null $cmd && exec $cmd $0 "$@"
done
exit 127
":"""

import os,re
import sys
import jinja2
import shutil
import gettext
import argparse
from distutils.dir_util import copy_tree

#
folder = os.path.dirname(__file__) 
language = gettext.translation('item_ja_JP',folder+'/locale',fallback=True)
language.install()

### checking
# if len(sys.argv) != 2:
#    print("usage: %s <item_name>" % (sys.argv[0]))
#    exit(0)
    
if 'RENAT_PATH' not in os.environ:
    print("RENAT_PATH is not defined")
    exit(1)

# arg parsing
parser = argparse.ArgumentParser(description='RENAT item create script',usage='%(prog)s [options]',
            formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=80))
#           formatter_class=argparse.RawTextHelpFormatter)
#            formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('name',help='item name')
parser.add_argument('-b','--batch',action='store_true',help='batch process')
parser.add_argument('-l','--local',action='store_true',help='create local configuration',default=False)
parser.add_argument('-n','--node',help='node list',default='')
parser.add_argument('-t','--tester',help='tester list',default='')
parser.add_argument('-r','--traffic',help='traffic file',default='')
parser.add_argument('-w','--web',help='web app list',default='')
parser.add_argument('-v','--hyper',help='hypervisor app list',default='')
args = parser.parse_args()

# global variables
NAME        = args.name
TEMPLATE    = os.environ['RENAT_PATH'] + "/tools/template/item" 
CURDIR      = os.path.dirname(os.path.abspath(__file__))

if os.path.exists(NAME):
    print(_('Error: %s already exists') % NAME)
    exit(1)

# initialize user input
str_node = ''
str_tester = ''
str_traffic = ''
str_web = ''
str_hyper = ''
create_local = False

# batch process, ignore if local is False
if args.batch:
    if args.local:
        str_node    = args.node
        str_tester  = args.tester
        str_traffic = args.traffic    
        str_web     = args.web
        str_hyper   = args.hyper
        create_local = True
# inter active
else:
    if sys.version_info[0] > 2:
        ans = input(_('Create local configuration file (local.yaml) or not [yes,no=default]:'))
    else:
        ans= raw_input(_('Create local configuration file (local.yaml) or not [yes,no=default]:'))

    if ans.lower() in ['','n','no']: 
        create_local = False
    else:
        create_local = True
    # 
    if create_local:
        if sys.version_info[0] > 2:
            str_node    = input(_('Use node list (comma separated) [ex:vmx11]:'))
            str_tester  = input(_('Use tester [ex:ixnet03_8009]:'))
            str_traffic = input(_('Use tester config file [ex:traffic.ixncfg]:'))
            str_web     = input(_('Use web app list (comma separated)[ex:samurai1]:'))
            str_hyper   = input(_('Use hypervisor list (comma separated)[ex:esxi-3-15]:'))
        else:
            str_node    = raw_input(_('Use node list (comma separated) [ex:vmx11]:'))
            str_tester  = raw_input(_('Use tester [ex:ixnet03_8009]:'))
            str_traffic = raw_input(_('Use tester config file [ex:traffic.ixncfg]:'))
            str_web     = raw_input(_('Use web app list (comma separated)[ex:samurai1]:'))
            str_hyper   = raw_input(_('Use hypervisor list (comma separated)[ex:esxi-3-15]:'))

# customize local.yaml
node_list   = re.split(r'[, ]+',str_node)
if '' in node_list: node_list.remove('')
web_list    = re.split(r'[, ]+',str_web)
if '' in web_list: web_list.remove('')
tester_list = re.split(r'[, ]+',str_tester)
if '' in tester_list: tester_list.remove('')
hyper_list  = re.split(r'[, ]+',str_hyper)
if '' in hyper_list: hyper_list.remove('')

# base copy and necessary symbolic
shutil.copytree(TEMPLATE, NAME)
os.system("ln -sf ../lab.robot %s/lab.robot" % NAME)

# create local.yaml from template
if create_local:
    os.system("touch %s/config/%s" % (NAME,str_traffic))
    for item in node_list: os.system("touch %s/config/%s.conf" % (NAME,item))
    loader = jinja2.Environment(loader=jinja2.FileSystemLoader(CURDIR + '/template')).get_template('local.yaml.tmpl')
    content = loader.render({'node_list':node_list,'web_list':web_list,'tester_list':tester_list,'traffic':str_traffic,'hyper_list':hyper_list})
    with open(NAME + '/config/local.yaml','w') as f: f.write(content)
    

# display information
print("\n")
print(_('=== Created `%s` test item ===') % (NAME))
print(_('Case scenario:     %s/%s/main.robot') % (CURDIR,NAME))
print(_('Case run file:     %s/%s/run.sh') % (CURDIR,NAME))
if create_local:
    print(_('Local config file: %s/%s/config/local.yaml') % (CURDIR,NAME))
    print(_('Tester config file:%s/%s/config/%s') % (CURDIR,NAME,str_traffic))
    print(_('Check and change the `local.yaml` local config file if necessary'))
    
# delete unused folders
for item in ['.svn', 'tmp/.svn', 'result/.svn', 'config/.svn', 'config/internet.profile/.svn', 'config/samurai.profile/.svn']:
    path = NAME + '/' + item
    if os.path.exists(path): shutil.rmtree(path)

