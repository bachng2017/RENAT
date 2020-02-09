#!/bin/sh

# script to add/remove job for this case to jenkins
JENKINS_URL=http://10.128.64.99:8082
PROG=$(basename $0)
TEMPLATE=$(dirname $0)/template/jenkins_job.xml

usage() {
  echo "usage: $PROG [OPTIONS] [JOB_NAME]"
  echo "add current item (folder) to Jenkins job"
  echo "note: a Jenkins API token of this user need tobe defined as \$JENKINS_TOKEN"
  echo "Jenkins API token could be created by clicking on top right username and choose Setting then API token"
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
  echo "Jenkins API token $JENKINS_TOKEN need to be defined"
  exit 1
fi


CRUMB=$(curl -m 5 --user $USER:$JENKINS_TOKEN -s "$JENKINS_URL/crumbIssuer/api/xml?xpath=concat(//crumbRequestField,\":\",//crumb)")
if [ "$ACTION" == "ADD" ]; then
  ERR=$(cat $TEMPLATE | sed "s/=\$USER/=$USER/g"  | sed "s|=\$CASE|=$PWD|g" | sed "s|<outputPath>\$CASE|<outputPath>$PWD|g" | \
        curl --user $USER:$JENKINS_TOKEN -vs -XPOST $JENKINS_URL/createItem?name=$JOB_NAME --data-binary @- -H "$CRUMB" -H "Content-Type:text/xml" 2>&1 | grep '400 Bad Request')
  if [ ! -z "$ERR" ]; then
    echo "ERROR: $ERR"
    echo "could not add job $JOB_NAME"
  else 
    echo "added job $JOB_NAME"
  fi
fi

if [ "$ACTION" == "DEL" ]; then
  ERR=$(curl --user $USER:$JENKINS_TOKEN -s -XPOST $JENKINS_URL/job/$JOB_NAME/doDelete -H "$CRUMB" 2>&1 | grep 'Error 404 Not Found')
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

