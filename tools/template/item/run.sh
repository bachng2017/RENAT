#!/bin/bash

# $Date: 2018-11-15 10:05:47 +0900 (木, 15 11月 2018) $
# $Rev: 1590 $
# $Author: $
# usage: ./runsh [-n <num>] <other robot argument>

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
    echo "RF Options:"
    echo "  -d, --dir FOLDER        make default result forder to FOLDER"
    echo "  -X                      stop immediately if a step fails (default is not set)"
    echo "  -v VAR:VALUE            define a global RF variable ${VAR} with value VALUE"
    echo "  -e TAG                  ignore steps tagged with TAG"
    echo "  -i TAG                  execute only steps tagged with TAG"
    echo "  -B                      automatically backup result folder with current date information"
    echo "  -r, --dry-run           same meaning with the original --dryrun"
    echo ""
    echo "Predefinded global variables:"
    echo "  -v CLEAN                execute CleanUp Result keyword before in Setup step"
    echo "  -v FORCE                run case started by Run Explicit"
}

# apply the resource
if [ -f ../renat.rc ]; then
    source ../renat.rc
fi

if [ -f ./renat.rc ]; then
    source ./renat.rc
fi


for OPT in "$@"; do
    case "$OPT" in 
        '-h'|'--help' )
            usage
            exit 1
            ;;
        '-B'|'--Backup' )
            BACKUP=1
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


# check necessary environment
if [[ -z "$RENAT_PATH" ]]; then
    echo "RENAT_PATH environment variable is not defined. Please check your environment"
    exit 1
else
    echo "Current RENAT path: $RENAT_PATH"
    echo 
fi

# export display variable for Selenium
export DISPLAY=:1


RESULT=0

process() {

    if [ ! -z $RUN_ALL ]; then    
        for folder in $(find . -mindepth 1 -maxdepth 1 -type d | sort); do
            if [ -f $folder/run.sh ]; then
                cd $folder
                process
                cd ..
            fi
        done
    fi

    PWD=$(pwd)
    echo "### Entering $PWD ###"
    if [ -f ./.ignore ] && [ -z $FORCE ]; then
        echo "   .ignore found, ignore this folder"
        cat .ignore
    elif [ -f ./main.robot ]; then
        if [ "$NUM" == "1" ]; then
            echo "Run only once"
        else
            echo "Run $NUM times"
        fi 
        echo 
        for INDEX in $(seq -f "%03g" 1 $NUM); do
            echo "Run: $INDEX"
            if [ -z $RESULT_FOLDER ]; then
                    RESULT_FOLDER="result"
            fi
            if [ $INDEX -gt 1 ]; then
                RESULT_FOLDER="result_$INDEX"
            fi

            # backup result folder if it exists
            if [ ! -z $BACKUP ] && [ -d $RESULT_FOLDER ]; then
                echo "Found result folder and make a backup of it"
                NAME=$(date '+%Y%m%d_%H%M%S')
                tar czf ${RESULT_FOLDER}_$NAME.tar.gz ${RESULT_FOLDER}
            fi

            OPTION=''
            if [ ! -z $DRYRUN ]; then
                OPTION="$OPTION --dryrun"
            fi

            robot $PARAM -d ${RESULT_FOLDER} -v MYID:$MYID -v RESULT_FOLDER:$RESULT_FOLDER -v RENAT_PATH:$RENAT_PATH $OPTION -K off main.robot
            CODE=$?
            RESULT=$(expr $RESULT + $CODE)
            echo
          done
    fi
}

process

TIME2=$(date +"%s")

### update run database
MSG="$PWD/$PROG $@"
# sqlite3 /home/robot/run.sqlite3 "UPDATE run_table SET count = count + 1 WHERE name='$USER'"
if [ -z ${RENAT_BATCH} ]; then
    logger -p local5.info -t "renat[$USER]" $TIME1 $TIME2 $RESULT "$MSG"
fi
exit $RESULT

