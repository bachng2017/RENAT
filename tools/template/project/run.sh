#!/bin/sh

# $Date: 2018-03-20 02:58:07 +0900 (Tue, 20 Mar 2018) $
# $Rev: 822 $
# $Ver: 0.1.7 $
# $Author: bachng $
# suite run script
# runs all test cases in sub folders if it has `run.sh` and does not has `.ignore` file
# returns 0 if all sub test cases were succeed otherwise return a non zero value

PROG=$(basename $0)

RETURN=0
SUCCEED=0
FAIL=0
FAIL_ITEM=""

usage() {
    echo "usage: $PROG [RF OPTIONS]"
    echo "  Project run script. Run all items inside this project"
    echo
    echo "See run.sh in item folder for more about useful options"
    echo "Some useful options:"
    echo "  -h/--help               print this usage"
    echo "  -v CLEAN                ccleanup result folder before run the test"
    echo "  -X                      stop immediately if a step fails (default is not set)"
    echo "  -v VAR:VALUE            define a global RF variable ${VAR} with value VALUE"
    echo "  -v CLEAN                execute CleanUp Result keyword before in Setup step"
    echo "  -v BATCH                do not wait for user input (useful for patch process)
    echo
}

# find all sub folders and execute run.sh if there is no .ignore in the same folder.
process() { 
    for folder in $(find . -mindepth 1 -maxdepth 1 -type d | sort); do
        if [ -f $folder/run.sh ]; then
            cd $folder
            process $folder
            cd ..
        fi
    done    

    PWD=$(pwd)
    echo "### Entering $PWD ###"
    if [ -f ./.ignore ]; then
        echo "   .ignore found, ignore this folder"
        cat .ignore 
    elif [ -f ./main.robot ]; then
        ./run.sh $PARAM
        CODE=$?
        RETURN=$(expr $RETURN + $CODE)
        if [ $CODE -eq 0 ]; then
            SUCCEED=$(expr $SUCCEED + 1)
        else
            FAIL=$(expr $FAIL + 1)
            FAIL_ITEM="$FAIL_ITEM $entry"
        fi
        echo "Finished with exit code $CODE"
    fi
    echo ""
    echo ""
    echo ""
}

for OPT in "$@"; do
    case "$OPT" in
        '-h'|'--help' )
            usage
            exit 1
            ;;
        *)
            PARAM+=" $1"
            shift 1
            ;;
    esac
done

process .

# summerize
echo "---"
echo "succeeded items: " $SUCCEED
echo "failed items:    " $FAIL
echo "    $FAIL_ITEM"
echo ""
exit $RETURN


