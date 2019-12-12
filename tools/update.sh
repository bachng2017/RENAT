#!/bin/bash
# WARN: this this should be run inside a RENAT project folder

if [[ "$1" == "-h" ]]; then
    echo "apply necessary changes to projects/items using current renat folder"
    echo "usage: $0 -h|-q"
    echo "   -h: print this help"
    echo "   -q: more quiet, do not print out diff information"
    exit 1
fi
if [[ "$1" == "-q" ]]; then
    QUIET=$1
fi

if [[ ! -f chibalab.robot ]] && [[ ! -f lab.robot ]]; then
  echo "ERROR: should be applied in a project folder which has chibalab.robot or lab.robot"
  exit 1
elif
  [[ -f main.robot ]]; then
  echo "ERROR: it looks like you are in a item folder. update.sh should be executed from insides a project folder."
  exit 1
else
  for i in $(find . -path $RENAT_PATH -prune -o -type f -name "chibalab.robot"); do
    LAB=$(echo $i | sed 's/chiba//')
    mv $i $LAB
    echo "moved chibalab.robot to lab.robot"
  done
  echo

  echo "ignore any changes in $RENAT_PATH"
  echo

  # update lab robot
  echo "try fixing lab.robot ..."
  FILE=$RENAT_PATH/tools/template/project/lab.robot
  if [[ -f ./lab.robot ]]; then
        diff $QUIET  $FILE lab.robot
        if [[ $? != 0 ]]; then
            cp -f $FILE .
            echo "updated $FILE"
        fi
  fi
  echo

  # update project/run.sh
  echo "try fixing project/run.sh ..."
  FILE=$RENAT_PATH/tools/template/project/run.sh
  diff $QUIET $FILE run.sh
  if [[ $? != 0 ]]; then
    cp -f $RENAT_PATH/tools/template/project/run.sh .
    echo "updated project $FILE"
    echo "---"
  fi
  echo

  # gitignore
  echo "try fixing gitignore ..."
  FILE=$RENAT_PATH/tools/template/project/.gitignore
  diff $QUIET $FILE .gitignore
  if [[ $? != 0 ]]; then
    cp -f $RENAT_PATH/tools/template/project/.gitignore .
    echo "updated item/.gitignore"
  fi
  echo

  # update lab.robot for items
  echo "try fixing items ..."
  RUN_FILE=$RENAT_PATH/tools/template/item/run.sh
  for entry in $(find . -path $RENAT_PATH -prune -o -type d -name config); do
    if [[ -f $entry/../main.robot ]] && [[ -f $entry/../lab.robot ]] ; then
       diff $QUIET $RUN_FILE  $entry/../run.sh
       if [[ $? != 0 ]]; then
         cp -f $RUN_FILE $entry/../run.sh
         echo "updated $entry/../run.sh"
         ln -sf ../lab.robot $entry/../lab.robot
         echo "updated lab.robot"
       fi
       diff $QUIET $RENAT_PATH/tools/template/item/.gitignore $entry/../.gitignore
       if [[ $? != 0 ]]; then
         cp -f $RENAT_PATH/tools/template/item/.gitignore $entry/../.gitignore
         echo "updated $entry/../.gitignore"
       fi
    else
       echo "ignore $entry because it does not look like an item folder"
    fi
  done
  echo

  echo "try fixing lab.robot symbolic ..."
  find . -path $RENAT_PATH -prune -o -name "main.robot" -exec sed --follow-symlinks -i 's/chibalab.robot/lab.robot/' {} \;
  find . -path $RENAT_PATH -prune -o -name "main.robot" -exec sed --follow-symlinks -i 's/\.\.\/lab\.robot/lab\.robot/' {} \;
  echo

  echo "try fixing local.yaml ..."
  find . -path $RENAT_PATH -prune -o -name "local.yaml" -exec sed --follow-symlinks -i '/^  *result_folder: result/d' {} \;
  echo

  # try to fix snmp polling issue
  echo "try fixing Follow Syslog Start issue ..."
  for entry in $(find . -path $RENAT_PATH -prune -o -type f -name local.yaml); do
    FLAG=$(grep 'Start Follow Syslog' $(dirname $entry)/../*.robot)
    if [ ! -z "$FLAG" ]; then
      grep -n 'snmp-polling: *yes\|follow-remote-log: *yes' $entry
      if [ $? == 0 ]; then
        sed -i '/snmp-polling: *yes/d' $entry
        sed -i '/follow-remote-log: *yes/d' $entry
        echo "updated $entry"
      fi
    fi
  done
  echo
fi


