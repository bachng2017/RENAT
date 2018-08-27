#!/bin/bash

echo "item list:"
echo "----------"
COUNT=0
BASE="."
for item in $(find $BASE -depth -type f -name "run.sh" | sort); do
    if [ $item != './run.sh' ]; then
        ITEM=$(echo $item | sed "s/^$BASE\///g" | sed "s/\/run.sh//g")
        COMMENT="active"
        if [ -f $ITEM/main.robot ]; then
            INFO=$(cat $ITEM/main.robot | grep "^Documentation" | sed 's/^Documentation *//g')
        fi
        printf "%-64s %s %s\n" "$ITEM" "$INFO"
        COUNT=$(expr $COUNT + 1)
    fi
done
echo "---"
echo "total items: $COUNT"
echo ""
echo ""
echo "ignored list:"
echo "------------"
COUNT=0
BASE="."
for item in $(find $BASE -depth -type f -name ".ignore" | sort); do
    ITEM=$(echo $item | sed "s/^$BASE\///g" | sed "s/\/\.ignore//g")
    COMMENT=$(cat $item)
    printf "%-64s %s\n" $ITEM "$COMMENT"
    COUNT=$(expr $COUNT + 1)
done
echo "---"
echo "ignored items: $COUNT"



