#!/bin/sh


echo "+--------------------------------+"
echo "+ run all shell test cases       +"
echo "+--------------------------------+"

CODE=0

# Run the test as robot user
sudo -s -u robot
export RENAT_PATH=$HOME/work/renat

# default test folder. Need to be an absolute path
TEST_FOLDER=$HOME/work/test_shell
ENTRY_POINT=run.sh
for item in $(find $TEST_FOLDER -depth  -type f -name $ENTRY_POINT); do
    echo
    echo 
    export CURRENT_DIR=$(dirname $item)
    cd $CURRENT_DIR
    echo "Run test in $CURRENT_DIR"
    $item
    CODE=$(expr $RETURN + $?)
done
echo
echo
echo


echo "+--------------------------------+"
echo "+ run all RENAT test cases       +"
echo "+--------------------------------+"
cd $HOME/work/test_renat
echo "update projects"
$RENAT_PATH/tools/update.sh
./run.sh
CODE=$(expr $RETURN + $?)


echo "---------------------------------"
echo "Exit code is $RETURN"
exit $CODE

