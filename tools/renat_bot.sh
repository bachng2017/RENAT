#!/bin/bash
# sample slack script to publish a message to a channel
# the reason to use the script is to keep supporty for both Python 2 & 3

i# usage
if [ $# -ne 4 ]; then
    echo "usage: $0 [msg] <channel> <user> <host>"
    exit 1
fi

MSG=$1
CHANNEL=$2
if [ -z $CHANNEL ]; then
    CHANNEL="<your channel with #>"
fi
USER=$3
if [ -z $USER ]; then
    USER=renat
fi
HOST=$4
if [ -z $HOST ]; then
    HOST=<your proxy server IP:port_number>
fi
TOKEN=<put your token here>
ICON=<url of your avatar here>


# post to  channel
curl -s -x http://$HOST -X POST https://slack.com/api/chat.postMessage \
    -d "token=$TOKEN" \
    -d "username=$USER" \
    -d "channel=$CHANNEL" \
    -d "icon_url=$ICON" \
    -d "text=$MSG" > /dev/null

