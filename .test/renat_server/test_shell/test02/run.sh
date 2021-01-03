#!/bin/sh

echo "------------------------------"
echo "Test02"
echo "This is a simple RENAT test case"
echo "------------------------------"

echo "Create and run project"
cd $HOME/work
$RENAT_PATH/tools/project.sh sample01
cd sample01
$RENAT_PATH/tools/item.sh -b -l test01
./run.sh

