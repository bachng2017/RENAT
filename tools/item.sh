#! /opt/rh/python27/root/usr/bin/python
# -*- coding: utf-8 -*-
# $Rev: 0.1.6 $
# $Ver: 1.7.1 $
# $Date: 2018-01-17 20:51:29 +0900 (Wed, 17 Jan 2018) $
# $Author: bachng $

import os,re
import sys
import jinja2
import shutil
import gettext
from distutils.dir_util import copy_tree

#
folder = os.path.dirname(__file__) 
language = gettext.translation('item',folder+'/locale',fallback=True)
language.install()


### checking
if len(sys.argv) != 2:
    print "usage: %s <item_name>" % (sys.argv[0])
    exit(1)
    
if 'RENAT_PATH' not in os.environ:
    print "RENAT_PATH is not defined"
    exit(1)

CASE        = sys.argv[1]
TEMPLATE    = os.environ['RENAT_PATH'] + "/tools/template/item" 
CURDIR      = os.path.dirname(os.path.abspath(__file__))

if os.path.exists(CASE):
    print _('Error: %s already exists') % (CASE)
    exit(1)

## base copy 
shutil.copytree(TEMPLATE, CASE)

## making necessary symbolic
os.system("ln -sf ../lab.robot %s/lab.robot" % CASE)

create_local = raw_input(_('Create local configuration file (local.yaml) or not [yes,no=default]:'))
if create_local == '': create_local = 'no'

if create_local.lower() in ['yes','y']:
    str_tester  = raw_input(_('Use tester [ex:ixnet03_8009]:'))
    traffic     = raw_input(_('Use tester config file [ex:traffic.ixncfg]:'))
    str_node    = raw_input(_('Use node list (comma separated) [ex:vmx11]:'))
    str_app     = raw_input(_('Use web app list (comma separated)[ex:samurai1]:'))

    ## customize local.yaml
    node_list   = re.split(r'[, ]+',str_node)
    if '' in node_list: node_list.remove('')
    app_list    = re.split(r'[, ]+',str_app)
    if '' in app_list: app_list.remove('')

    ## create null config file for nodes:
    for item in node_list: os.system("touch %s/config/%s.conf" % (CASE,item))
    
    if str_tester == "":    tester_list = []
    else:                   
        tester_list = re.split(r'[, ]+',str_tester)
        if '' in tester_list: tester_list.remove('')

    # create traffic file 
    os.system("touch %s/config/%s" % (CASE,traffic))

    loader = jinja2.Environment(loader=jinja2.FileSystemLoader(CURDIR)).get_template('local.yaml.tmpl')
    content = loader.render({'node_list':node_list,'app_list':app_list,'tester_list':tester_list,'traffic':traffic})
    
    with open(CASE + '/config/local.yaml','w') as f: f.write(content)

    print "\n"
    print _('=== Created `%s` test item ===') % (CASE)
    print _('Case scenario:     %s/%s/main.robot') % (CURDIR,CASE)
    print _('Case run file:     %s/%s/run.sh') % (CURDIR,CASE)
    print _('Local config file: %s/%s/config/local.yaml') % (CURDIR,CASE)
    print _('Tester config file:%s/%s/config/%s') % (CURDIR,CASE,traffic)
    print _('Check and change the `local.yaml` local config file if necessary')
else:
    print "\n"
    print _('Created test item `%s`')  % (CASE)
    print _('Test scenario: %s/%s/main.robot') % (CURDIR,CASE)
    print _('Test run file: %s/%s/run.sh') % (CURDIR,CASE)
    
# delete unused folders
for item in ['.svn', 'tmp/.svn', 'result/.svn', 'config/.svn', 'config/internet.profile/.svn', 'config/samurai.profile/.svn']:
    path = CASE + '/' + item
    if os.path.exists(path): shutil.rmtree(path)

