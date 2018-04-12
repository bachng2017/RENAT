#!/bin/sh
# sample for a slack trigger
# usage
if [ $# -ne 4 ]; then
    echo "usage: renat.sh [msg] <channel> <user> <proxy>"
    exit 1
fi

TOKEN=<your-token>
ICON=<your-avatar-link>

MSG=$1
CHANNEL=$2
if [ -z $CHANNEL ]; then
    CHANNEL="<default-channel>"
fi
USER=$3
if [ -z $USER ]; then
    USER=renat
fi
PROXY=$4
if [ -z $PROXY ]; then
    PROXY=<default-host-ip>
fi


# post to  channel
curl -s -x http://$PROXY -X POST https://slack.com/api/chat.postMessage \
    -d "token=$TOKEN" \
    -d "username=$USER" \
    -d "channel=$CHANNEL" \
    -d "icon_url=$ICON" \
    -d "text=$MSG" > /dev/null
