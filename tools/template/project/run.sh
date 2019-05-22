#!/bin/bash

# $Date: 2019-04-19 17:38:37 +0900 (金, 19  4月 2019) $
# $Rev: 1996 $
# $Ver: $
# $Author: $
# suite run script
# runs all test cases in sub folders if it has `run.sh` and does not has `.ignore` file
# returns 0 if all sub test cases were succeed otherwise return a non zero value

PROG=$(basename $0)

RETURN=0
SUCCEED=0
FAIL=0
FAIL_ITEM=""
COLLECT=""

usage() {
    echo "usage: $PROG [RF OPTIONS]"
    echo "  Project run script. Run all items inside this project"
    echo
    echo "See run.sh in item folder for more about useful options"
    echo "Some useful options:"
    echo "  -h/--help               print this usage"
    echo "  -p/--parallel           parallelly run the items"
    echo "  -r/--report             remake reports with existed results"
    echo "  -v CLEAN                ccleanup result folder before run the test"
    echo "  -X                      stop immediately if a step fails (default is not set)"
    echo "  -v VAR:VALUE            define a global RF variable ${VAR} with value VALUE"
    echo "  -v CLEAN                execute CleanUp Result keyword before in Setup step"
    echo "  -v RENAT_BATCH          do not wait for user input (useful for patch run)"
    echo
}

PIDS=""
declare -A ITEMS

# find all sub folders and execute run.sh if there is no .ignore in the same folder.
run() { 
    # $1: ITEM_PATH
    # $2: PREFIX

    local ITEM_PATH=$1
    local PREFIX=$2
    local PWD=""
    local NAME=""

    #
    cd $ITEM_PATH
    local PWD=$(pwd)
    echo "### Current folder is $PWD ###"

    if [ "$PREFIX" = "." ]; then
        NAME=$(basename $PWD)
    else
        NAME="$PREFIX/$(basename $PWD)"
    fi
    
    for folder in $(find . -mindepth 1 -maxdepth 1 -type d | sort); do
        if [ -f $folder/run.sh ]; then
            run $folder $NAME
        fi
    done    

    if [ "$REPORT" == "1" ]; then
        if [ -f $PWD/result/output.xml ]; then
            COLLECT="$COLLECT $PWD/result/output.xml"
        fi
    else
        if [ -f ./.ignore ]; then
            echo "   .ignore found, ignore this folder"
            cat .ignore 
        elif [ -f ./main.robot ]; then
            if [ "$PARALLEL" = "1" ]; then 
                ./run.sh $PARAM &
                PIDS="$PIDS $!" 
                ITEMS[$!]=$PWD
            else
                ./run.sh $PARAM
                CODE=$?
                RETURN=$(expr $RETURN + $CODE)
                if [ $CODE -eq 0 ]; then
                    SUCCEED=$(expr $SUCCEED + 1)
                else
                    FAIL=$(expr $FAIL + 1)
                    FAIL_ITEM="$PWD \n$FAIL_ITEM"
                fi
                # collect data after run
                COLLECT="$COLLECT $PWD/result/output.xml"
                echo "Finished with exit code $CODE"
            fi
        fi
        echo ""
        echo ""
        echo ""
    fi
    if [ "$ITEM_PATH" != "." ]; then
        cd ..
    fi
}

# main run
for OPT in "$@"; do
    case "$OPT" in
        '-h'|'--help' )
            usage
            exit 1
            ;;
        '-p'|'--parallel' )
            PARALLEL=1
            shift 1
            ;;
        '-r'|'--report' )
            REPORT=1
            shift 1
            ;;
        *)
            PARAM+=" $1"
            shift 1
            ;;
    esac
done

run . .

if [ "$REPORT" != "1" ]; then
    # collect result from parallel process
    if [ "$PARALLEL" = "1" ]; then 
        for item in $PIDS; do
            wait $item
            CODE=$?  
            if [ $CODE -eq 0 ]; then
                SUCCEED=$(expr $SUCCEED + 1)
            else
                FAIL=$(expr $FAIL + 1)
                FAIL_ITEM="${ITEMS[$item]} \n$FAIL_ITEM"
            fi
            # collect data after run
            COLLECT="$COLLECT ${ITEMS[$item]}/result/output.xml"
        done
    fi
    
    # summerize
    echo "---"
    echo "succeeded items: " $SUCCEED
    echo "failed items:    " $FAIL
    echo -e $FAIL_ITEM
    echo ""
fi
 
# rebot
PROJ_NAME=$(basename $PWD)
echo "make project report for $PROJ_NAME"
rebot --name $PROJ_NAME -L INFO $COLLECT
exit $RETURN

