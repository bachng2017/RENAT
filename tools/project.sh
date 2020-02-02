#!/bin/bash

. gettext.sh

TEXTDOMAIN=project_ja_JP
TEXTDOMAINDIR=$(dirname $0)/locale
export TEXTDOMAIN
export TEXTDOMAINDIR

CMD=$0
if [ ! "$#" -eq 1 ]; then
  echo "$(eval_gettext "usage: \$CMD [PROJECT]")"
  exit 1
fi 

PROJECT_PATH=$1
BASEDIR=$(dirname $0)


# check $RENAT_PATH environment variable
if [ -z "$RENAT_PATH" ]; then
  echo "$(eval_gettext "RENAT_PATH environment variable is not defined. Please check your environment")"
  exit 1
fi

if [ -d  "$PROJECT_PATH" ]; then 
  if [ -f $PROJECT_PATH/lab.robot ]; then
    echo "$(eval_gettext "Test project existed.")"
    exit 1
  else
    echo -n "$(eval_gettext "Folder seems not to be a RENAT project. Do you want to convert it? [y/n] ")"
    read ANS
  fi
else
  ANS="y"
fi

if [ "$ANS" == "y" ]; then
  TEMPLATE_PATH=$RENAT_PATH/tools/template
  cp -r $TEMPLATE_PATH/project/* $PROJECT_PATH
  find $PROJECT_PATH -name ".svn" -prune -name ".svn" -exec rm -rf {} \;
  echo "$(eval_gettext "created test project: ")" "$PROJECT_PATH"
  echo "$(eval_gettext "use item.sh to create test case")"
fi 
