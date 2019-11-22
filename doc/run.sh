#!/bin/bash

PUBLISH_DOC=/var/www/html/renat-doc/
export PYTHONPATH=$PYTHONPATH:$RENAT_PATH
PYTHON_CMD=$(head -n 1 `which robot` | sed 's/#!//')

$PYTHON_CMD -m robot.libdoc $RENAT_PATH/Common.py html/Common.html
$PYTHON_CMD -m robot.libdoc $RENAT_PATH/Logger.py html/Logger.html
$PYTHON_CMD -m robot.libdoc $RENAT_PATH/Router.py html/Router.html
$PYTHON_CMD -m robot.libdoc $RENAT_PATH/Tester.py html/Tester.html
$PYTHON_CMD -m robot.libdoc $RENAT_PATH/OpticalSwitch.py html/OpticalSwitch.html
$PYTHON_CMD -m robot.libdoc $RENAT_PATH/VChannel.py html/VChannel.html
$PYTHON_CMD -m robot.libdoc $RENAT_PATH/router_mod/juniper.py html/router_mod_juniper.html
$PYTHON_CMD -m robot.libdoc $RENAT_PATH/router_mod/cisco.py html/router_mod_cisco.html
$PYTHON_CMD -m robot.libdoc $RENAT_PATH/router_mod/gr.py html/router_mod_gr.html
$PYTHON_CMD -m robot.libdoc $RENAT_PATH/tester_mod/ixnet.py html/tester_mod_ixnet.html
$PYTHON_CMD -m robot.libdoc $RENAT_PATH/tester_mod/ixload.py html/tester_mod_ixload.html
$PYTHON_CMD -m robot.libdoc $RENAT_PATH/tester_mod/ixbps.py html/tester_mod_ixbps.html
$PYTHON_CMD -m robot.libdoc $RENAT_PATH/tester_mod/avaproxy.py html/tester_mod_avaproxy.html
$PYTHON_CMD -m robot.libdoc $RENAT_PATH/optic_mod/calient.py html/optic_mod_calient.html
$PYTHON_CMD -m robot.libdoc $RENAT_PATH/optic_mod/g4ntm.py html/optic_mod_g4ntm.html
$PYTHON_CMD -m robot.libdoc $RENAT_PATH/WebApp.py html/WebApp.html
$PYTHON_CMD -m robot.libdoc $RENAT_PATH/Samurai.py html/Samurai.html
$PYTHON_CMD -m robot.libdoc $RENAT_PATH/Arbor.py html/Arbor.html
$PYTHON_CMD -m robot.libdoc $RENAT_PATH/Hypervisor.py html/Hypervisor.html
$PYTHON_CMD -m robot.libdoc $RENAT_PATH/hypervisor_mod/vmware.py html/hpv_mod_vmware.html
$PYTHON_CMD -m robot.libdoc -F REST -n RENAT ./index.py html/index.html
$PYTHON_CMD -m robot.libdoc ./lab_robot.py html/lab_robot.html
# $PYTHON_CMD -m robot.libdoc $RENAT_PATH/CHANGES.txt html/Changes.html

chmod -R 0664 html/*.html
rm -f $PUBLISH_DOC/*.html
cp html/*.html $PUBLISH_DOC 
cp $RENAT_PATH/CHANGES.txt $PUBLISH_DOC 


# html to pdf
for i in $(cat list.txt); do 
    echo $i
    /usr/local/bin/wkhtmltopdf -q html/$i.html pdf/$i.pdf
done

# merge to all-in-one pdf
JOIN_CMD="gs -q -dPDFSETTINGS=/prepress -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -sOutputFile=renat.pdf "
LIST=$(cat list.txt | sed 's/$/.pdf/'|  paste -s -d' ')
cd pdf
$JOIN_CMD $LIST 
rm -f $PUBLISH_DOC/*.pdf
cp renat.pdf $PUBLISH_DOC

