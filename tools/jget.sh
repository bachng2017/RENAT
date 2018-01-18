#!/bin/sh

if [ $# -lt 3 ];  then
  echo "usage: $0 [set|def] <routername> <configname>"
  echo "ex: $0 set vmx11 vmx11.config"
  exit 1
fi
 

CMD=/usr/libexec/rancid/jlogin
ROUTER=$2
CONFIG=$3


if [ "$1" = "def" ]; then
  echo "get config for $ROUTER, mode = $1"
  $CMD -c "show config" $ROUTER | grep '.*[;\{\}] *#*.*$' > $CONFIG 
fi

if [ "$1" = "set" ]; then
  echo "get config for $ROUTER, mode = $1"
  $CMD -c "show config | display set | no-more" $ROUTER | grep "^set" > $CONFIG
fi

