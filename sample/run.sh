#!/bin/sh

# $Date: 2018-01-17 20:51:29 +0900 (Wed, 17 Jan 2018) $
# $Rev: 0.1.6 $
# $Ver: 0.1.8g1 $
# $Author: bachng $
# suite run script
# runs all test cases in sub folders if it has `run.sh` and does not has `.ignore` file
# returns 0 if all sub test cases were succeed otherwise return a non zero value

CURRENT=`pwd`

echo "run all test cases in $PWD"
RETURN=0

# find all sub folders and execute run.sh if there is no .ignore in the same folder.
for entry in $(find * -type d); do  
    if [ -f $CURRENT/$entry/run.sh ]; then
        echo "*** Entering $entry ***"
        if [ -f $CURRENT/$entry/.ignore ]; then
            echo "   .ignore found, ignore this folder"
            echo ""
        else
            cd $CURRENT/$entry
            ./run.sh $@ 
            TMP=$?
            RETURN=`expr $RETURN + $TMP`
            echo "Finished with exit code $RETURN"
            echo ""
        fi
    fi
done
exit $RETURN


