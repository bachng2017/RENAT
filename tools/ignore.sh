#!/bin/bash
# 
#
#
BASE=$(basename $0)
if [ $# -lt 2 ];  then
  echo "usage: $BASE -l <base>"
  echo "       $BASE -d <item>"
  echo "       $BASE <item> <comment>"
  exit 1
fi

if [ "$1" == "-l" ]; then
    echo "ignored list:"
    echo ""
    BASE=$2
    for item in $(find $BASE -depth -type f -name ".ignore" | sort); do
        ITEM=$(echo $item | sed "s/^$BASE\///g" | sed "s/\/\.ignore//g")
        COMMENT=$(cat $item)
        printf "%-64s %s\n" "$ITEM" "$COMMENT"
    done
    echo ""
elif [ "$1" == "-d" ]; then
    ITEM=$2
    if [ -f ./$ITEM/.ignore ]; then
        rm -f ./$ITEM/.ignore
        echo "removed .ignore in '$ITEM'"
    else
        echo "could not find .ignore in '$2'"
        exit 1
    fi
else
    ITEM=$1
    COMMENT=$2
    if [ -d ./$ITEM ]; then
        if [ -f ./$ITEM/.ignore ];  then
            OLD_COMMENT=$(cat ./$ITEM/.ignore)
            echo "old comment was: $OLD_COMMENT"
        fi
        echo "$COMMENT" > ./$ITEM/.ignore
        echo "ignored item '$ITEM'"
    else
        echo "could not find '$1'"
        exit 1
    fi
fi
