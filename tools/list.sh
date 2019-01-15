#!/bin/bash
#
# $Rev: $
# $Ver: $
# $Date: $
# $Author: $ 

if [ $# -lt 1 ];  then
  echo "List information about test items in a RENAT project"
  echo "usage: $0 <project>"
  exit 1
fi

BASE=$(basename $1)
if [ "$1" == "." ]; then
    CURPATH=$(pwd)
else
    CURPATH=$(pwd)"/"$1
fi

echo "### all item list in '$BASE' ###"
echo "----------"
COUNT=0
# find all run.sh script
for item in $(find $1 -depth -type f -name "run.sh" | sort); do
    ITEM=$(echo $item | sed "s/^$BASE\///g" | sed "s/\/run.sh//g")
    if [ "$ITEM" == "run.sh" ]; then
        ITEM='.'
    fi
    ROBOT=$(echo $item | sed "s/run.sh/main.robot/g")
    COMMENT="active"
    # and make sure there is a main.robot file in the same folder of the run.sh
    if [ -f $ROBOT ]; then
        INFO=$(cat $ROBOT | grep "^Documentation" | sed 's/^Documentation *//g')
        printf "%-64s %s %s\n" "$ITEM" "$INFO"
        COUNT=$(expr $COUNT + 1)
    fi
done
echo "---"
echo "total items: $COUNT"
echo ""
echo ""

echo "### ignored item list in '$BASE' ###"
echo "------------"
COUNT=0
for item in $(find $1 -depth -type f -name ".ignore" | sort); do
    ITEM=$(echo $item | sed "s/^$BASE\///g" | sed "s/\/\.ignore//g")
    if [ "$ITEM" == ".ignore" ]; then
        ITEM='.'
    fi
    COMMENT=$(cat $item)
    printf "%-64s %s\n" $ITEM "$COMMENT"
    COUNT=$(expr $COUNT + 1)
done
echo "---"
echo "ignored items: $COUNT"
echo ""
echo ""

echo "### item last run status in '$BASE' ###"
for item in $(find $1 -depth -type f -name "run.sh" | sort); do
    ITEM=$(echo $item | sed "s/^$BASE\///g" | sed "s/\/run.sh//g")
    if [ "$ITEM" == "run.sh" ]; then
        ITEM='.'
    fi
    LOG=$(echo $item | sed "s/run.sh/run.log/g")
    ROBOT=$(echo $item | sed "s/run.sh/main.robot/g")
    if [ -f $ROBOT ]; then
        if [ -f $LOG ]; then
            # echo "Output:.*$CURPATH/$ITEM/result"
            INFO=$(cat $LOG | grep -B3 "Output:.*$CURPATH/$ITEM/result" | grep total)
            IGNORE=$(cat $LOG | grep -A1 "Entering.*$CURPATH/$ITEM" | grep .ignore)
            if [ "$IGNORE" == "" ]; then
                if [ "$INFO" == "" ]; then
                    INFO='running...'
                fi
            else
                INFO='ignored'
            fi
            printf "%-64s %s %s\n" "$ITEM" "$INFO"
        else
            printf "%-64s %s %s\n" "$ITEM" "N/A"
        fi
    fi
done    


