#!/bin/sh

# script to add/remove job for this case to jenkins
JENKINS_URL=http://10.128.64.99:8082
PROG=$(basename $0)
TEMPLATE=$(dirname $0)/template/jenkins_job.xml

usage() {
  echo "usage: $PROG [OPTIONS] [JOB_NAME]"
  echo "add current item (folder) to Jenkins job"
  echo "note: a Jenkins API token of this user need tobe defined as \$JENKINS_TOKEN"
  echo "Jenkins API token could be created by clicking on top right username and choose Setting then API token."
  echo "Without Jenkins API, the command could still be used with password from user."
  echo "command options:"
  echo "  -h, --help              print usage"
  echo "  -a, --add               add a job"
  echo "  -d, --delete            delete a job"
}

OPT=$1
while  [ ! -z "$OPT" ]; do
  case "$OPT" in
    '-h'|'--help' )
      usage
      exit 1
    ;;
    '-d'|'--delete' )
      ACTION="DEL"
      shift 1
    ;;
    '-a'|'--add' )
      ACTION="ADD"
      shift 1
    ;;
    *) 
    JOB_NAME="$@"
    break
  esac
  OPT=$1 
done 

if [ -z $JOB_NAME ]; then
  usage
  exit 1
fi

if [ -z "$JENKINS_TOKEN" ]; then
  echo "Without \$JENKINS_TOKEN, user password will be requested twice."
  CREDENT="$USER"
else
  CREDENT="$USER:$JENKINS_TOKEN"
fi


CRUMB=$(curl -c ./.cookie -m 5 -u $CREDENT -s "$JENKINS_URL/crumbIssuer/api/xml?xpath=concat(//crumbRequestField,\":\",//crumb)")
ERR=$(echo $CRUMB | grep "Jenkins-Crumb:")
if [ -z "$ERR" ]; then
  echo "Login error. Check your password or token"
  exit 1
fi

if [ "$ACTION" == "ADD" ]; then
  ERR=$(cat $TEMPLATE | sed "s/=\$USER/=$USER/g"  | sed "s|=\$CASE|=$PWD|g" | sed "s|=\$RENAT_PATH|=$RENAT_PATH|g" | \
        sed "s|<outputPath>\$CASE|<outputPath>$PWD|g" | \
        curl -b ./.cookie -u $CREDENT -s -XPOST $JENKINS_URL/createItem?name=$JOB_NAME --data-binary @- -H "$CRUMB" -H "Content-Type:text/xml")
  if [ ! -z "$ERR" ]; then
    echo "could not add job $JOB_NAME"
  else 
    echo "added job $JOB_NAME"
  fi
fi

if [ "$ACTION" == "DEL" ]; then
  ERR=$(curl -b ./.cookie -u $CREDENT -s -H "$CRUMB" -XPOST $JENKINS_URL/job/$JOB_NAME/doDelete)
  if [ ! -z "$ERR" ]; then
    echo "ERROR: job not found"
  else 
    echo "deleted job $JOB_NAME"
  fi
fi

if [ -z  "$ACTION" ]; then
  echo "need an option"
  usage
  exit 1
fi

