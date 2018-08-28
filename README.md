# RENAT

A Robotframework Extension for Network Automation Testing

---

## Disclaimer

The Authors assume no responsibility for damage or loss of system
performance as a direct or indirect result of the use of this
software.  This software is provided "as is" without express or
implied warranty.

All product names and trademarks are the property of their respective owners, which are in no way associated or affiliated with this software. Use of these names does not imply any co-operation or endorsement.
- Ixia, IxiaNetwork, IxiaLoad are trademarks of IXIA 
- Calient is a trademark of CALIENT NETWORKS, INC.
- Junos, Juniper are trademarks of Junipter Networks.
- Cisco is a trademark of Cisco Systems, Inc.

For details about Robot Framework see [RobotFramework](http://www.robotframework.org/)

--- 

## Table of contents

- [Disclaimer](#disclaimer)
- [Table Of Contents](#table-of-contents)
- [Features](#features)
- [Installation](#installation)
- [Usages](#usages)
- [More Examples](#more-examples)
- [Manual](#manual)
- [Copying And Copyrights](#copying-and-copyrights)
- [Thanks](#thanks)

## Features
The framework provides an simple way to conduct Network Automation Testing by using simple scenario

![Renat scenario sample](doc/renat_sample.png)

Feature includes: 
- An extension of widely used RobotFramework that add more supports for Network Automation Testing
- Easy to write and read testing scenario
- Separate testing data and logic
- Easy to collect logs and activities on testing devices
- Easy to add vendor-independent keywords for new platforms
- Support traffic generator (IxNetwork/IxLoad) and L1 Switch (Calient)
- Extend Selenium library for simple web appliance testing

## Installation
The following instructions is aimed for Centos 6.x systems. Other system could use the equivalent commands to install necessary packages

### Python
The current version of RENAT is using Python 2.x (support Python 3.x is in experimental phase)
```
yum -y install centos-release-scl-rh
yum -y install python27
python --version
```

### Other necessary packages
```
yum install -y epel-release
yum install -y gettext gcc net-snmp net-snmp-devel net-snmp-utils czmq czmq-devel python27-tkinter xorg-x11-server-Xvfb ghostscript firefox-52.8.0-1.el6.centos.x86_64 httpd vimjj
pip install numpy pyte PyYAML openpyxl Jinja2 pandas paramiko lxml requests pdfkit
pip install netsnmp-py==0.3 
```

### Robot Framwork packages
```
pip install robotframework robotframework-seleniumlibrary robotframework-selenium2library robotframework-sshlibrary docutils
```
For more information about Robotframework and installation, check http://robotframework.org/

The newest selenium pakage could not capture the whole page (but only current view). In other to utilize the fullpage capture, make sure the correcnt `selenium` package and `gecko-driver` is install

```
pip uninstall selenium
pip install selenium==2.53.6
```

### Other system configuration
##### RENAT account
Create a common `robot` account on the RENAT server. This account will be used for collect and set configuration between the test routers and the RENAT server. Following are sample configuration
```
groupadd techno -o -g 1000
useradd robot -g tech
passwd  robot
```
Edit the global configuration of RENAT `config/config.yaml` to suite your environment.
Usually only the `robot-server` and `robot-password` are need to be modified.

#### Patch the RF SSHLibrary
By default the Robotframework SSHLibrary does not support SSH proxy command. Using the information in th patch file `$RENAT_PATH/patch/SSHLibrary.patch` to patch `SSHLibrary` located in the Python package folder.


### Web server (optional)
It is more convinence to access the test result from a web browser. Configure your favorite web server to display to access the test project and test item folder.
The following is a snipset of Apache config file `httpd.conf` to show the user `work` directory. Any RENAT test project or test item could be access easily from browser with following URL like: `http://<renat server url>/~user/work/renat/sample/item01/log.html`
```
<IfModule mod_userdir.c>
    #
    # UserDir is disabled by default since it can confirm the presence
    # of a username on the system (depending on home directory
    # permissions).
    #
    # UserDir disabled
    # UserDir enabled *
    #
    # To enable requests to /~user/ to serve the user's public_html
    # directory, remove the "UserDir disabled" line above, and uncomment
    # the following line instead:
    #
    UserDir work

</IfModule>
<Directory /home/*/work>
    Options MultiViews Indexes SymLinksIfOwnerMatch IncludesNoExec
</Directory>
```

### Selenium related libraries
In order to capture the screen, Selenium and related drivers need to be installed and prepared correclty.

#### Gecko driver
Download and install gecko driver from https://github.com/mozilla/geckodriver/releases

```
cd /tmp
wget https://github.com/mozilla/geckodriver/releases/download/v0.21.0/geckodriver-v0.21.0-linux64.tar.gz
cd /usr/local/bin
tar xzvf /root/work/download/geckodriver-v0.21.0-linux64.tar.gz
chown root:root geckodriver
```

#### Xvfb start script
Depending on your system, a virtual screen (Xvfb) must be started before using scree ncapture function.

For example on CentOS 6.x, prepare a service startup file `xvfb` in folder `/etc/rc.d/init.d` likes this:

```
#!/bin/bash
#
# /etc/rc.d/init.d/xvfbd
#
# chkconfig: 345 95 28
# description: Starts/Stops X Virtual Framebuffer server
# processname: Xvfb
#

. /etc/init.d/functions

[ "${NETWORKING}" = "no" ] && exit 0

PROG="/usr/bin/Xvfb"
PROG_OPTIONS=":1 -screen 0 640x480x24"
PROG_OUTPUT="/tmp/Xvfb.out"

case "$1" in
    start)
        echo -n "Starting : X Virtual Frame Buffer "
        $PROG $PROG_OPTIONS>>$PROG_OUTPUT 2>&1 &
        disown -ar
        /bin/usleep 500000
        status Xvfb & >/dev/null && echo_success || echo_failure
        RETVAL=$?
        if [ $RETVAL -eq 0 ]; then
            /bin/touch /var/lock/subsys/Xvfb
            /sbin/pidof -o  %PPID -x Xvfb > /var/run/Xvfb.pid
        fi
        echo
        ;;
    stop)
        echo -n "Shutting down : X Virtual Frame Buffer"
        killproc $PROG
        RETVAL=$?
        [ $RETVAL -eq 0 ] && /bin/rm -f /var/lock/subsys/Xvfb /var/run/Xvfb.pid
        echo
        ;;
    restart|reload)
        $0 stop
        $0 start
        RETVAL=$?
        ;;
    status)
        status Xvfb
        RETVAL=$?
        ;;
    *)
     echo $"Usage: $0 (start|stop|restart|reload|status)"
     exit 1
esac

exit $RETVAL
```

Then make it starts automatically 
```
service xvfb start
chkconfig xvfb on
```

### Ixia Network and Ixia Load modules (optional)
You need to access to proper Ixia softwares by your own and following its instruction correctly. The following instructions are just examples.You could by pass this part if you are not intending to use Ixia control modules.
```
yum install -y java-1.8.0-openjdk java-1.8.0-openjdk-devel ld-linux.so.2
```

Use Ixia install files to install necessary application. For example:

- add `./IxOS6.80.1100.9Linux64.bin` (default install folder is: /opt/ixia/ixos/6.80-EA-SP1)
- add `./IxNetworkTclClient7.41.945.9Linux.bin` (default install folder is: /opt/ixia/ixnet/7.41-EA)
- add `./IxLoadTclApi8.01.99.14Linux_x64.bin` (default install folder is: /opt/ixia/ixload/8.01.99.14)

Add a startup file `ixia.sh` to `/etc/profile.d/` using proper destination
```
IXIA_HOME=/opt/ixia
IXIA_VERSION=8.01.0.2

IXL_libs=$IXIA_HOME/ixload/8.01.99.14
IXN_libs=$IXIA_HOME/ixnet/7.41-EA
IXOS_libs=$IXIA_HOME/ixload/8.01.99.14/../../ixos-api/8.01.0.2
BPS_libs=/opt/ixia/bps

PYTHONPATH=.:$IXN_libs/lib/PythonApi:$IXL_libs/lib:$IXOS_libs:$BPS_libs:$PYTHONPATH
for LIBS in "$IXL_libs $IXOS_libs"
do
    for FOLDER in `find $LIBS -type f -name pkgIndex.tcl | rev | cut -d/ -f2- | rev`
    do
        TCLLIBPATH="$TCLLIBPATH $FOLDER"
        PYTHONPATH="$PYTHONPATH:.:$FOLDER"
    done
done

export TCLLIBPATH
export IXIA_VERSION
export IXL_libs
export PYTHONPATH
```

Depending on your install order, sometims following lines are inserted at the end of `etc/profile`.
These will override the TCCLLIBPATH configured in the above ixia.sh.
Remember to comment them out if not IxLoad module will not work correctly.
```
TCLLIBPATH=/opt/ixia/ixos/6.80-EA-SP1/lib
export TCLLIBPATH
```

The concept of ``Tester module`` is that the configuration should be created using Tester GUI (like Ixia Network or Ixia Load). RENAT framework supports controling the test items, stop/run the tests etc. but does not support traffic generating itself.

### Installation check
Make sure you have right Python (2.x) and runnable Ixia module (if `Tester` module is necessary)
```
$ python --version
Python 2.7.13
$ python
Python 2.7.13 (default, Apr 12 2017, 06:53:51)
[GCC 4.4.7 20120313 (Red Hat 4.4.7-18)] on linux2
Type "help", "copyright", "credits" or "license" for more information.
>>> import IxNetwork
>>> import IxLoad
```


### RENAT checkout and preparation
#### 1. Checkout
Prepare a RENAT folder in user working folder and check out the source

```
cd
mkdir work
cd work
git clone https://github.com/bachng2017/RENAT.git renat
```

#### 2. RENAT  configuration
- make $RENAT_PATH

Make an environment varible `$RENAT_PATH` pointing the correct RENAT folder.
If you have multi renat (different version) checked out, modify this varible to use the correct RENAT version.
```
export RENAT_PATH=~/work/renat
```

Or edit your startup script
```
echo "export RENAT_PATH=~/work/renat" >> ~/.bashrc
```

- configure device and authencation information in `$RENAT_PATH/config/device.yaml` and `$RENAT_PATH/config/auth.yaml` to suite to lab environment.

## Create test scenario and run
Below example assumes that you've already have a test router running JunOS.

### 1. Create a sample project
```
$ cd ~/work
$ $RENAT_PATH/tools/project.sh sample
created test project:  sample
use item.sh to create test case
tree sample
sample
├── lab.robot
├── renat.rc
├── run.sh
└── setpath.bashrc
``` 

### 2. Create a sample test item
```
$ cd sample
$ $RENAT_PATH/tools/item.sh item01
Create local configuration file (local.yaml) or not [yes,no=default]:y
Use tester [ex:ixnet03_8009]:
Use tester config file [ex:traffic.ixncfg]:
Use node list (comma separated) [ex:vmx11]:vmx11
Use web app list (comma separated)[ex:samurai1]:


=== Created `item01` test item ===
Case scenario:     /home/user/work/renat/tools/item01/main.robot
Case run file:     /home/user/work/renat/tools/item01/run.sh
Local config file: /home/user/work/renat/tools/item01/config/local.yaml
Tester config file:/home/user/work/renat/tools/item01/config/
Check and change the `local.yaml` local config file if necessary
$ tree item01
item01
├── config
│   ├── local.yaml
│   └── vmx11.conf
├── lab.robot -> ../lab.robot
├── main.robot
├── readme.txt
├── renat.rc
├── result
├── run.sh
└── tmp

4 directories, 10 files
```

### 3.Edit scenario file
The `config/local.yaml` file includes local information for each test item. Edit this file to add more test devices, tester or other item specific information.

Edit `main.robot` file in test item folder to look like this

```
# Basic setting 
*** Setting ***
Documentation   This is a sample test item
Metadata        Log File    [.|${CURDIR}/result]
Suite Setup     Lab Setup
Suite Teardown  Lab Teardown

# Common setting
Resource        lab.robot

# Variable setting
*** Variables ***


*** Test Cases ***
01. First item:
    Router.Switch               vmx11
    Router.Cmd                  show version
```

### 4.Check to scenario
Using `--dryrun` option to check the current scenario
```
$ ./run.sh --dryrun
Current RENAT path: /home/user/work/renat
Run only once
Current local.yaml: /home/user/work/renat/sample/item01/config/local.yaml
Loaded extra library `Tester`
Loaded extra library `Arbor`
==============================================================================
Main :: Testing item01
==============================================================================
01. First item:                                                       | PASS |
------------------------------------------------------------------------------
Main :: Testing item01                                                | PASS |
1 critical test, 1 passed, 0 failed
1 test total, 1 passed, 0 failed
==============================================================================
Output:  /home/user/work/renat/sample/item01/result/output.xml
Log:     /home/user/work/renat/sample/item01/result/log.html
Report:  /home/user/work/renat/sample/item01/result/report.html
```


### 5. Run the test
Execute `./run.sh` to run the test. Test result and log files are in the `./result` folder.

```
$ ./run.sh
Current RENAT path: /home/user/work/renat
Run only once
Current local.yaml: /home/user/work/renat/sample/item01/config/local.yaml
Loaded extra library `Tester`
Loaded extra library `Arbor`
Loaded extra library `OpticalSwitch`
==============================================================================
Main :: item01: very simple sample
==============================================================================
RENAT Ver:: RENAT 0.1.6
------------------------------------------------------------------------------
README:
The sample requires a running Juniper router

------------------------------------------------------------------------------
00. Lab Setup
------------------------------------------------------------------------------
01. First item:                                                       | PASS |
------------------------------------------------------------------------------
99. Lab Teardown
------------------------------------------------------------------------------
Main :: item01: very simple sample                                    | PASS |
1 critical test, 1 passed, 0 failed
1 test total, 1 passed, 0 failed
==============================================================================
Output:  /home/user/work/renat/sample/item01/result/output.xml
Log:     /home/user/work/renat/sample/item01/result/log.html
Report:  /home/user/work/renat/sample/item01/result/report.html
```

In case you has configured a web server, access `http://<server-ip>/~<username>/tes01/result/log.html` or `http://<server-ip>/~<username>/result/report.html` for more details about the result.

When running with `--debug` options likes `./run.sh --debug debug.txt`, the system creates detail debug information in the file `result/debug.txt`. Use this to see in details or bug report. Please make sure your passwords are removed before submit the files.

## More Examples
- See [item02](./sample/item02/main.robot) for sample about `Exec File` keyword
- See [item03](./sample/item03/main.robot) for sample about `BGP Best Path Selection` testing for a JunOS router

## Manual
See [manual](https://bachng2017.github.io/RENAT/doc/index.html) for more details about RENAT keywords and its modules. Or checking the `doc` folder in your `renat` (html/pdf)

## Copying And Copyrights
Copyright 2018 NTT Communications

This project is licensed under the Apache v2.0 license. For more detail see [license](./LICENSE)

## Thanks
Thanks to everybody has encouraged, tested and supported this project. All comments, advices and co-operation are appreciated.

