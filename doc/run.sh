#!/bin/sh

PUBLISH_DOC=/var/www/html/renat-doc/
export PYTHONPATH=$PYTHONPATH:$RENAT_PATH

python -m robot.libdoc $RENAT_PATH/Common.py html/Common.html
python -m robot.libdoc $RENAT_PATH/Logger.py html/Logger.html
python -m robot.libdoc $RENAT_PATH/Router.py html/Router.html
python -m robot.libdoc $RENAT_PATH/Tester.py html/Tester.html
python -m robot.libdoc $RENAT_PATH/OpticalSwitch.py html/OpticalSwitch.html
python -m robot.libdoc $RENAT_PATH/VChannel.py html/VChannel.html
python -m robot.libdoc $RENAT_PATH/router_mod/juniper.py html/router_mod_juniper.html
python -m robot.libdoc $RENAT_PATH/router_mod/cisco.py html/router_mod_cisco.html
python -m robot.libdoc $RENAT_PATH/router_mod/gr.py html/router_mod_gr.html
python -m robot.libdoc $RENAT_PATH/tester_mod/ixnet.py html/tester_mod_ixnet.html
python -m robot.libdoc $RENAT_PATH/tester_mod/ixload.py html/tester_mod_ixload.html
python -m robot.libdoc $RENAT_PATH/tester_mod/ixbps.py html/tester_mod_ixbps.html
python -m robot.libdoc $RENAT_PATH/optic_mod/calient.py html/optic_mod_calient.html
python -m robot.libdoc $RENAT_PATH/optic_mod/g4ntm.py html/optic_mod_g4ntm.html
python -m robot.libdoc $RENAT_PATH/WebApp.py html/WebApp.html
python -m robot.libdoc $RENAT_PATH/Samurai.py html/Samurai.html
python -m robot.libdoc $RENAT_PATH/Arbor.py html/Arbor.html
python -m robot.libdoc -F REST -n RENAT ./index.py html/index.html
# python -m robot.libdoc $RENAT_PATH/CHANGES.txt html/Changes.html

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
LIST=$(cat list.txt | sed 's/$/.pdf/'|  paste -s -d' ')
cd pdf
/usr/bin/pdfjoin -o renat.pdf $LIST 
rm -f $PUBLISH_DOC/*.pdf
cp renat.pdf $PUBLISH_DOC

