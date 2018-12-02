#!/bin/bash

. gettext.sh

TEXTDOMAIN=project_ja_JP
TEXTDOMAINDIR=$(dirname $0)/locale
export TEXTDOMAIN
export TEXTDOMAINDIR

if [ ! "$#" -eq 1 ]; then
  echo "usage: $0 <project_path>"
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
  echo "$(eval_gettext "Test project existed.")"
  exit 1
else
  TEMPLATE_PATH=$RENAT_PATH/tools/template
  cp -r $TEMPLATE_PATH/project $PROJECT_PATH
  find $PROJECT_PATH -name ".svn" -prune -name ".svn" -exec rm -rf {} \;
fi
echo "$(eval_gettext "created test project: ")" "$PROJECT_PATH"
echo "$(eval_gettext "entered project folder: ")" "$PROJECT_PATH"
echo "$(eval_gettext "use item.sh to create test case")"

