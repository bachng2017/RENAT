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
  for i in $(find . -type f -name "chibalab.robot"); do
    LAB=$(echo $i | sed 's/chiba//')
    mv $i $LAB
  done
  echo "moved chibalab.robot to lab.robot"

  # update lab robot
  FILE=$RENAT_PATH/tools/template/project/lab.robot
  if [[ -f ./lab.robot ]]; then
        diff $QUIET  $FILE lab.robot
        if [[ $? != 0 ]]; then
            cp -f $FILE .
            echo "updated lab.robot"
            echo "---"
        fi
  fi

  # update project/run.sh
  FILE=$RENAT_PATH/tools/template/project/run.sh
  diff $QUIET $FILE run.sh
  if [[ $? != 0 ]]; then
    cp -f $RENAT_PATH/tools/template/project/run.sh .
    echo "updated project run.sh"
    echo "---"
  fi

  # gitignore
  FILE=$RENAT_PATH/tools/template/project/.gitignore
  diff $QUIET $FILE .gitignore
  if [[ $? != 0 ]]; then
    cp -f $RENAT_PATH/tools/template/project/.gitignore .
    echo "updated item/.gitignore"
    echo "---"
  fi

  # update lab.robot for items
  RUN_FILE=$RENAT_PATH/tools/template/item/run.sh
  for entry in $(find . -type d -name config); do
    if [[ -f $entry/../main.robot ]] && [[ -f $entry/../lab.robot ]] ; then
       diff $QUIET $RUN_FILE  $entry/../run.sh
       cp -f $RUN_FILE $entry/../run.sh
       echo "updated $entry/../run.sh"
       ln -sf ../lab.robot $entry/../lab.robot
       echo "updated lab.robot"
       diff $QUIET $RENAT_PATH/tools/template/item/.gitignore $entry/../.gitignore
       cp -f $RENAT_PATH/tools/template/item/.gitignore $entry/../.gitignore
       echo "updated $entry/../.gitignore"
       echo "---"
    else
       echo "ignore $entry because it does not look like an item folder"
    fi
  done

  find . -name "main.robot" -exec sed --follow-symlinks -i 's/chibalab.robot/lab.robot/' {} \;
  find . -name "main.robot" -exec sed --follow-symlinks -i 's/\.\.\/lab\.robot/lab\.robot/' {} \;
  echo "updated main.robot"

  find . -name "local.yaml" -exec sed --follow-symlinks -i '/^  *result_folder: result/d' {} \;
  echo "updated local.yaml"
fi


