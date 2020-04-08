#!/bin/bash
# -*- coding: utf-8 -*-

""":"
for cmd in python3.6 python3.5 python3 python2 python; do
    command -v > /dev/null $cmd && exec $cmd $0 "$@"
done
exit 127
":"""


import argparse
import os
import sys
import yaml

# arg parsing
parser = argparse.ArgumentParser(
  description='retrieve RENAT node information from configuration files',
  usage='%(prog)s [-h] [nodename]',
  formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=80))
parser.add_argument('node',help='node name')
args = parser.parse_args()
try:
  master_folder = yaml.load(open(os.environ['RENAT_PATH']+'/config/config.yaml'))['default']['renat-master-folder']
  info=yaml.load(open(master_folder + '/device.yaml'))['device'][args.node]
  print("information about node %s:" % args.node)
  print(yaml.dump(info,default_flow_style=False))
except:
  print("invalid nodename")

