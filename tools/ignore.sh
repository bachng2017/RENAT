#!/bin/bash
# -*- coding: utf-8 -*-
# 
#
#
BASE=$(basename $0)
if [ $# -lt 2 ];  then
  echo "Mark an item with ignore flag that would be ignored by run.sh. Option -r will mark the item and all its sub items"
  echo "Usage: "
  echo "  $BASE -l base:             show the ignore list of the base folder"
  echo "  $BASE -d [-r] item:        remove ignore flag of an item"
  echo "  $BASE [-r] item comment:   mark an item as ignore with comment"
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
  if [ "$2" == "-r" ]; then
    RECUR=""
    ITEM=$3
  else
    RECUR="-maxdepth=0"
    ITEM=$2 
  fi 
  for TARGET in $(find $ITEM $RECUR -type d); do
    if [ -f $TARGET/.ignore ]; then
      rm -f $TARGET/.ignore
      echo "removed .ignore in '$TARGET'"
    fi
  done
else
  if [ "$1" == "-r" ]; then
    ITEM=$2
    COMMENT=$3
    RECUR=""
  else
    ITEM=$1
    COMMENT=$2
    RECUR="-maxdepth 0"
  fi

  for TARGET in $(find $ITEM $RECUR -type d); do
    if [ -f $TARGET/main.robot ]; then
      if [ -f $TARGET/.ignore ];  then
          OLD_COMMENT=$(cat $TARGET/.ignore)
      fi
      echo "$COMMENT" > $TARGET/.ignore
      echo "ignored item '$TARGET'"
    fi
  done
fi
