#!/bin/bash
# sample slack script to publish a message to a channel
# the reason to use the script is to keep supporty for both Python 2 & 3

# usage
if [ $# -ne 5 ]; then
    echo "usage: $0 <file_path> <host> <channel> <title> <msg>"
    exit 1
fi

FILE_PATH=$1
if [ ! -f $FILE_PATH ]; then
    echo "need to specify a valid filepath"
    exit 1
fi

HOST=$2
if [ -z $HOST ]; then
    HOST=<YOUR HOST HERE>
fi

CHANNEL=$3
if [ -z $CHANNEL ]; then
    CHANNEL="<your channel with #>"
fi

TITLE=$4
if [ -z $TITLE ]; then
    TITLE="file upload"
fi

MSG=$5
if [ -z $MSG ]; then
    MSG="auto posted from webhook"
fi

TOKEN=<YOUR TOKEN HERE>


# post to  channel through a proxy defined by HOST
curl -s -x http://$HOST -X POST https://slack.com/api/files.upload \
-F file=@$FILE_PATH \
-F "title=$TITLE" \
-F "initial_comment=$MSG" \
-F "channels=$CHANNEL" \
-H "Authorization: Bearer $TOKEN"


