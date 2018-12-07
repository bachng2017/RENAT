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

echo "### all item list in '$BASE' ###"
echo "----------"
COUNT=0
# find all run.sh script
for item in $(find $1 -depth -type f -name "run.sh" | sort); do
    ITEM=$(echo $item | sed "s/^$BASE\///g" | sed "s/\/run.sh//g")
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
    RESULT=$(echo $item | sed "s/run.sh/run.log/g")
    ROBOT=$(echo $item | sed "s/run.sh/main.robot/g")
    if [ -f $ROBOT ]; then
        if [ -f $RESULT ]; then
            INFO=$(cat $RESULT | grep -B3 'Output: ' | grep total)
            if [ "$INFO" == "" ]; then
                INFO='running...'
            fi
            printf "%-64s %s %s\n" "$ITEM" "$INFO"
        else
            printf "%-64s %s %s\n" "$ITEM" "N/A"
        fi
    fi
done    


