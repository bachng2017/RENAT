#!/bin/sh

# $Date: 2018-03-20 02:58:07 +0900 (Tue, 20 Mar 2018) $
# $Rev: 822 $
# $Ver: 0.1.7 $
# $Author: bachng $
# usage: ./runsh [-n <num>] <other robot argument>

# read renat resource
# the RENAT_PATH variable is evaluated with this priority
# environment variable < suite renat.rc < case renat.rc


PROG=$(basename $0)
PWD=$(pwd)
MYID=$(echo $PWD | md5sum | cut -f1 -d' ')
NUM=1

usage () {
    echo "usage: $PROG [OPTIONS] [RF OPTIONS]"
    echo "  Item run script"
    echo
    echo "Options:"
    echo "  -h, --help              print usage"
    echo "  -n, --number NUM        repeat the test NUM times"
    echo "RF Options:"
    echo "  -X                      stop immediately if a step fails (default is not set)"
    echo "  -v VAR:VALUE            define a global RF variable ${VAR} with value VALUE"
    echo "  -v CLEAN                execute CleanUp Result keyword before in Setup step"
    echo "  -e TAG                  ignore steps tagged with TAG"
    echo "  -i TAG                  execute only steps tagged with TAG"
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
fi

# export display variable for Selenium
export DISPLAY=:1


RESULT=0
for INDEX in $(seq -f "%03g" 1 $NUM); do
    if [ "$NUM" == "1" ]; then
        echo "Run only once"
        RESULT_FOLDER="result"
    else
        echo "Run $NUM times"
        RESULT_FOLDER="result_$INDEX"
    fi
    robot $PARAM -d ${RESULT_FOLDER} -v MYID:$MYID -v RESULT_FOLDER:$RESULT_FOLDER -v RENAT_PATH:$RENAT_PATH main.robot
    CODE=$?
    RESULT=$(expr $RESULT + $CODE)
    echo
    echo
  done

### update run database
sqlite3 /home/robot/run.sqlite3 "UPDATE run_table SET count = count + 1 WHERE name='$USER'"

exit $RESULT

