@echo off
rem script to start a remoteserver on Windows machine

python -c "from robotremoteserver import RobotRemoteServer;from WhiteLibrary import WhiteLibrary;RobotRemoteServer(WhiteLibrary(),host='10.128.64.52')"




