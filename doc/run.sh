#!/bin/sh

RENAT_DOC="/var/www/html/renat-doc/"
export PYTHONPATH=$PYTHONPATH:$RENAT_PATH

python -m robot.libdoc $RENAT_PATH/Common.py Common.html
python -m robot.libdoc $RENAT_PATH/Logger.py Logger.html
python -m robot.libdoc $RENAT_PATH/Router.py Router.html
python -m robot.libdoc $RENAT_PATH/Tester.py Tester.html
python -m robot.libdoc $RENAT_PATH/OpticalSwitch.py OpticalSwitch.html
python -m robot.libdoc $RENAT_PATH/VChannel.py VChannel.html
python -m robot.libdoc $RENAT_PATH/router_mod/juniper.py router_mod_juniper.html
python -m robot.libdoc $RENAT_PATH/router_mod/cisco.py router_mod_cisco.html
python -m robot.libdoc $RENAT_PATH/router_mod/gr.py router_mod_gr.html
python -m robot.libdoc $RENAT_PATH/tester_mod/ixnet.py tester_mod_ixnet.html
python -m robot.libdoc $RENAT_PATH/tester_mod/ixload.py tester_mod_ixload.html
python -m robot.libdoc $RENAT_PATH/WebApp.py WebApp.html
python -m robot.libdoc $RENAT_PATH/Samurai.py Samurai.html
python -m robot.libdoc $RENAT_PATH/Arbor.py Arbor.html
python -m robot.libdoc -F REST -n RENAT ./index.py index.html
python -m robot.libdoc $RENAT_PATH/Readme.py Readme.html

cp *.html $RENAT_DOC 


