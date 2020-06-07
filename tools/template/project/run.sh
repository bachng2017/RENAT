#!/bin/bash

# suite run script
# runs all test cases in sub folders if it has `run.sh` and does not has `.ignore` file
# returns 0 if all sub test cases were succeed otherwise return a non zero value

PROG=$(basename $0)

RETURN=0
SUCCEED=0
FAIL=0
FAIL_ITEM=""
REPORT_FOLDER=""

usage() {
    echo "usage: $PROG [RF OPTIONS]"
    echo "  Project run script. Run all items inside this project"
    echo
    echo "See run.sh in item folder for more about useful options"
    echo "Some useful options:"
    echo "  -h/--help               print this usage"
    echo "  -p/--parallel           parallelly run the items"
    echo "  -r/--report             remake reports with existed results (without run the test)"
    echo "  -v CLEAN                cleanup result folder before run the test"
    echo "  -X                      stop immediately if an item fails (default is not set)"
    echo "  -v VAR:VALUE            define a global RF variable ${VAR} with value VALUE"
    echo "  -v CLEAN                execute CleanUp Result keyword before in Setup step"
    echo "  -v RENAT_BATCH          do not wait for user input (useful for patch run)"
    echo
}


report() {
    PROJ_NAME=$(basename $PWD)
    if [ -z "$REPORT_FOLDER" ]; then
      for item in $(find . -name output.xml | sort); do
        REPORT_FOLDER+=" $item"
      done
    fi
    COUNT=$(echo "$REPORT_FOLDER" | wc -w)
    echo "Make reports for project $PROJ_NAME from $COUNT folders:"
    echo "$REPORT_FOLDER"
    rebot --name $PROJ_NAME -L INFO $REPORT_FOLDER
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
   
    # call run recursivily 
    for folder in $(find . -mindepth 1 -maxdepth 1 -type d | sort); do
        if [ -f $folder/run.sh ]; then
            run $folder $NAME
            if [ ! -z $XSTOP ] && [ $CODE -ne 0 ]; then
                echo "ERR: An error happened, no more items are exectuted"
                report
                exit $RETURN
            fi
        fi
    done

    if [ -f ./.ignore ]; then
        echo "   .ignore found, ignore this folder"
        cat .ignore 
    elif [ -f ./main.robot ]; then
        if [ "$PARALLEL" == "1" ]; then 
            ./run.sh $XSTOP $PARAM &
            PIDS="$PIDS $!" 
            ITEMS[$!]=$PWD
        else
            ./run.sh $XSTOP $PARAM
            CODE=$?
            RETURN=$(expr $RETURN + $CODE)
            if [ $CODE -eq 0 ]; then
                SUCCEED=$(expr $SUCCEED + 1)
            else
                FAIL=$(expr $FAIL + 1)
                FAIL_ITEM="$PWD \n$FAIL_ITEM"
            fi
            # collect data after run
            for item in $(find $PWD/$RESULT_FOLDER -name output.xml); do
                REPORT_FOLDER+=" $item"
            done
            echo "Finished with exit code $CODE"
        fi
    fi
    echo
    echo
    echo

    if [ "$ITEM_PATH" != "." ]; then
        cd ..
    fi
}

# main run
OPT=$1
while [ ! -z "$OPT" ]; do
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
        '-X' )
            XSTOP="-X"
            shift 1
            ;;
        '-d'|'--dir' )
            if [[ -z "$2" ]] || [[ "$2" =~ ^-+ ]]; then
                echo "$PROG: option -d requires an argument -- $1" 1>&2
                exit 1
            fi
            RESULT_FOLDER=$2
            shift 2
            ;;
        *)
            PARAM+=" $1"
            shift 1
            ;;
    esac
    OPT=$1
done
if [ -z "$RESULT_FOLDER" ]; then
    RESULT_FOLDER="result"
fi
PARAM+=" -d $RESULT_FOLDER"


if [ -z "$REPORT" ]; then
    #
    run . .
   
    # collect data in case tests are run parallelly 
    if [ "$PARALLEL" == "1" ]; then 
        for item in $PIDS; do
            wait $item
            CODE=$?  
            if [ $CODE -eq 0 ]; then
                SUCCEED=$(expr $SUCCEED + 1)
            else
                FAIL=$(expr $FAIL + 1)
                FAIL_ITEM="${ITEMS[$item]} \n$FAIL_ITEM"
            fi
            # collect data after the run
            for item in $(find ${ITEMS[$item]}/$RESULT_FOLDER -name output.xml); do
                REPORT_FOLDER+=" $item"
            done
        done
    fi
        
    # summarize
    echo "---"
    echo "succeeded items: " $SUCCEED
    echo "failed items:    " $FAIL
    echo -e $FAIL_ITEM
    echo
fi

# PROJ_NAME=$(basename $PWD)
# if [ -z "$REPORT_FOLDER" ]; then
#   for item in $(find . -name output.xml | sort); do
#     REPORT_FOLDER+=" $item"
#   done
# fi
# COUNT=$(echo "$REPORT_FOLDER" | wc -w)
# echo "Make reports for project $PROJ_NAME from $COUNT folders:"
# echo "$REPORT_FOLDER"
# rebot --name $PROJ_NAME -L INFO $REPORT_FOLDER
report

exit $RETURN

