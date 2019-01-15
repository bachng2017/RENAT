""" 
Document for RENAT framework

All in one pdf renat.pdf_

#########
Libraries
#########


RENAT includes following libraries:

Common_:
    Common library of RENAT

VChannel_:
    Library controls connection to targets (servers, routers, ...)

Logger_:
    Library provides enhanced loggging keywords
Optical_: 
    Library provides keywords to control L1 switches, includes mod_calient_ mod, mod_ntm_ mod
Router_:
    Library provides keywords to control routers, includes mod_juniper_ mod , mod_cisco_ mod and mod_gr_ mod
Tester_:
    Library provides keywords to control testers, includes mod_ixnet_ , mod_ixload_ , mod_ixbps_ and mod_avaproxy_
WebApp_:
    Common library for web application, includes 2 child libraries: Samurai_ and Arbor_
Hypervisor_:
    Library provides keywords to control Hypervisor, included mod_vmware_

LabKeyword_:
    Common lab keywords

######
Others
######


Changes_:
    Changes information

Choose each libraries for detail infomration and samples about keywords.

.. _renat.pdf:   ./renat.pdf
.. _Common:     ./Common.html
.. _VChannel:   ./VChannel.html
.. _Logger:     ./Logger.html
.. _Optical:    ./OpticalSwitch.html
.. _Router:     ./Router.html
.. _Tester:     ./Tester.html
.. _WebApp:     ./WebApp.html
.. _mod_juniper:    ./router_mod_juniper.html
.. _mod_cisco:      ./router_mod_cisco.html
.. _mod_gr:         ./router_mod_gr.html
.. _mod_ixnet:      ./tester_mod_ixnet.html
.. _mod_ixload:     ./tester_mod_ixload.html
.. _mod_ixbps:      ./tester_mod_ixbps.html
.. _mod_avaproxy:   ./tester_mod_avaproxy.html
.. _mod_calient:    ./optic_mod_calient.html
.. _mod_ntm:        ./optic_mod_ntm.html
.. _Samurai:        ./Samurai.html   
.. _Arbor:          ./Arbor.html   
.. _Changes:        ./CHANGES.txt  
.. _LabKeyword:     ./lab_robot.html
.. _Hypervisor:     ./Hypervisor.html
.. _mod_vmware:     ./hpv_mod_vmware.html

"""
ROBOT_LIBRARY_DOC_FORMAT = 'reST'
import Common

ROBOT_LIBRARY_VERSION = Common.version()

