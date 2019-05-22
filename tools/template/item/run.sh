#!/bin/bash

# $Date: 2019-05-22 05:47:03 +0900 (水, 22  5月 2019) $
# $Rev: 2022 $
# $Author: $
# usage: ./run.sh [-n <num>] <other robot argument>
# ITEM run script
# read renat resource
# the RENAT_PATH variable is evaluated with this priority
# environment variable < suite renat.rc < case renat.rc


PROG=$(basename $0)
PWD=$(pwd)
MYID=$(echo $PWD | md5sum | cut -f1 -d' ')
NUM=1
TIME1=$(date +"%s")

usage () {
    echo "usage: $PROG [OPTIONS] [RF OPTIONS]"
    echo "  Item run script"
    echo
    echo "Options:"
    echo "  -h, --help              print usage"
    echo "  -n, --number NUM        repeat the test NUM times"
    echo "  -f, --force             force the test to run, does not care about .ignore files"
    echo "  -a, --all               run the item and all its sub items"
    echo "  -b, --rm-null-space     automatically remove the null space char (\u200b) in the scenario"
    echo "RF Options:"
    echo "  -d, --dir FOLDER        make default result forder to FOLDER"
    echo "  -X                      stop immediately if a step fails (default is not set)"
    echo "  -v VAR:VALUE            define a global RF variable ${VAR} with value VALUE"
    echo "  -e TAG                  ignore steps tagged with TAG"
    echo "  -i TAG                  execute only steps tagged with TAG"
    echo "  -B, --backup            automatically backup result folder with current date information"
    echo "  -r, --dry-run           same meaning with the original --dryrun"
    echo "Predefinded global variables:"
    echo "  -v CLEAN                execute CleanUp Result keyword before in Setup step"
    echo "  -v FORCE                run case started by Run Explicit"
    echo ""
}

for OPT in "$@"; do
    case "$OPT" in 
        '-h'|'--help' )
            usage
            exit 1
            ;;
        '-B'|'--backup' )
            BACKUP=1
            shift 1
            ;;
        '-b'|'--remove-null-space' )
            RM_NULL_SPACE=1
            shift 1
            ;;
        '-d'|'--dir' )
            if [[ -z "$2" ]] || [[ "$2" =~ ^-+ ]]; then
                echo "$PROG: option requires an number argument -- $1" 1>&2
                exit 1
            fi
            RESULT_FOLDER=$2
            shift 2
            ;;
        '-f'|'--force' )
            FORCE=1
            shift 1
            ;;
        '-a'|'--all' )
            RUN_ALL=1
            shift 1
            ;;
        '-r'|'--dry-run' )
            DRYRUN=1
            shift 1
            ;; 
        '-n'|'--number' )
            if [[ -z "$2" ]] || [[ "$2" =~ ^-+ ]]; then
                echo "$PROG: option requires an number argument -- $1" 1>&2
                exit 1
            fi
            NUM="$2"
            shift 2
            ;;
        '--'|'-' )
            shift 1
            PARAM+=( "$@" )
            break
            ;;
        *)
            PARAM+=" $1"
            shift 1
            ;;    
    esac
done


# check the anoyance \u200B code 
WARN=$(grep -Psrn '\x{200B}' *.{yaml,robot})
if [ "$WARN" != "" ]; then
    if [ -z $RM_NULL_SPACE ]; then
        echo -e "\e[31mWARNING: an unexpect ZERO WIDTH SPACE is found in your scenario. Check and remove them or use -b option\e[m"
        echo "$WARN"
        exit 1
    else
        echo "WARNING:zero width space is found and remove. Original file is backup to main.robot.org"
        cp main.robot main.robot.org
        sed -i -s 's/\xe2\x80\x8b//g' main.robot
    fi
fi


# check necessary environment
if [[ -z "$RENAT_PATH" ]]; then
    echo "RENAT_PATH environment variable is not defined. Please check your environment"
    exit 1
else
    echo "Current time:       $(env LC_ALL=c date)"
    echo "Current RENAT path: $RENAT_PATH"
    echo 
fi

# export display variable for Selenium
export DISPLAY=:1

RESULT=0

###  
run() {
    # $1: item path
    # $2: prefix
    local ITEM_PATH=$1
    local PREFIX=$2
    local PWD=""
    local NAME=""

    # change working folder
    cd $ITEM_PATH
    PWD=$(pwd)
    echo "### Current folder is $PWD ###"

    # name of the test
    if [ "$PREFIX" = '.' ]; then
        NAME="$(basename $PWD)"
    else
        NAME="$PREFIX/$(basename $PWD)"
    fi

    # run sub items if -a is defined
    if [ ! -z $RUN_ALL ]; then    
        for ITEM in $(find . -mindepth 1 -maxdepth 1 -type d | sort); do
            if [ -f $ITEM/run.sh ]; then
                > $ITEM/run.log 
                run $ITEM "$NAME" > >(tee -a $ITEM/run.log) 2>&1
            fi
        done
    fi

    if [ -f ./.ignore ] && [ -z $FORCE ]; then
        echo "   .ignore found, ignore this folder"
        cat .ignore
    elif [ -f ./main.robot ]; then
        if [ "$NUM" = "1" ]; then
            echo "Run only once"
        else
            echo "Run $NUM times"
        fi 
        echo 

        for RUN_INDEX in $(seq -f "%03g" 1 $NUM); do
            echo "Run: $RUN_INDEX"
            if [ -e ./.stop ]; then
                echo "This run was stopped with following reason:"
                cat ./.stop
                echo "---------------------------------"
                rm "./.stop"
                break    
            fi
            if [ -z $RESULT_FOLDER ]; then
                    RESULT_FOLDER="result"
            fi
            if [ $RUN_INDEX -gt 1 ]; then
                RESULT_FOLDER="result_$RUN_INDEX"
            fi

            # backup result folder if it exists
            if [ ! -z $BACKUP ] && [ -d $RESULT_FOLDER ]; then
                echo "Found result folder and make a backup of it"
                DATE=$(date '+%Y%m%d_%H%M%S')
                tar czf ${RESULT_FOLDER}_$DATE.tar.gz ${RESULT_FOLDER}
            fi

            OPTION=''
            if [ ! -z $DRYRUN ]; then
                OPTION="$OPTION --dryrun"
            fi

            robot --name $NAME $PARAM -d ${RESULT_FOLDER} \
                    -v MYID:$MYID -v RUN_INDEX:$RUN_INDEX -v RESULT_FOLDER:$RESULT_FOLDER \
                    -v RENAT_PATH:$RENAT_PATH $OPTION -K off main.robot
            CODE=$?
            RESULT=$(expr $RESULT + $CODE)
            echo
          done
    fi
    if [ "$ITEM_PATH" = "." ]; then
        cd .
    else
        cd ..
    fi
}

> ./run.log
run . . > >(tee -a ./run.log) 2>&1

TIME2=$(date +"%s")

### log run information
MSG="$PWD/$PROG $@"
if [ -z ${RENAT_BATCH} ]; then
    logger -p local5.info -t "renat[$USER]" $TIME1 $TIME2 $RESULT "$MSG"
fi
exit $RESULT

