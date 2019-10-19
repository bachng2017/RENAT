# AVAPROXY

A proxyserver to provide Avalance API from 32bit machine to RENAT system

---

## Install the base system

- Install a debian 32bit system with appropriate resource 
- sample iso: debian-9.6.0-i386-DVD-1.iso
- use default setting and suitable network information
- only need below 2 softwares option:
    - ssh server
    - system utilities

## Post install configureation

### Edit apt sources list /etc/apt/sources.list

```
# stretch-updates, previously known as 'volatile'
# deb http://ftp.jp.debian.org/debian/ stretch-updates main contrib
# deb-src http://ftp.jp.debian.org/debian/ stretch-updates main contrib
deb http://security.debian.org/debian-security jessie/updates main 
deb http://ftp.de.debian.org/debian jessie main
```

### Install necessary packages
Install following packages

```
$ apt install aptitude 
$ aptitude update
$ aptitude install libgif4 tzdata libxft2 libxss1 gcc make libxss-dev sudo net-tools x11-apps ntp ntpdate tcpdump python-pip python-tk libreadline-dev libbz2-dev zlib1g-dev libgdbm-dev sqlite3 libsqlite3-dev libncurses5-dev python-bsddb3 vim  curl libssl-dev

$ aptitude install openjdk-7-jdk
```
There will be some collisions when install `openjdk`. Choose the solution to downgrade current `tzdata`


### Install activeTCL by source
- download ActiveTCL from official page
- install it to `/usr`
```
$ tar xzvf ActiveTcl8.5.18.0.298892-linux-ix86-threaded.tar.gz
$ cd ActiveTcl8.5.18.0.298892-linux-ix86-threaded
$ ./install.sh 
```
choose /usr for Path, let other by default
```
Path [/opt/ActiveTcl-8.5]: /usr
```

### Install python 2.7.14  
- download python source file from the official page
- configure and build 

```
$ tar xzvf Python-2.7.14.tgz
$ cd  Python-2.7.14
$ ./configure --with-ensurepip --with-tcltk-includes="-I/usr/include" --with-tcltk-libs="-L/usr/lib -ltcl8.5 -L/usr/lib -ltk8.5"
$ make
```

- ignore following waring
```
Python build finished, but the necessary bits to build these modules were not found:
_bsddb             bsddb185           sunaudiodev     
```
- install python
```
$ make install
```

### Install more necessary packages
```
$ pip install --upgrade pip
$ pip install Flask decorator avalancheapi
```

### Install avalanche software
- get appropriate file from vendor.
- following below instructions to install and active

```
$ tar -xvzf Layer_4_7_Auto_Linux_4.46.tar.gz
$ mkdir /opt/spirent/
$ mkdir /opt/spirent/api
$ mv -f Layer_4_7_Auto_Linux_4.46/Layer_4_7_Application_Linux/ /opt/spirent/api/
$ mkdir /opt/spirent/licenses
$ cd /opt/spirent/api/Layer_4_7_Application_Linux/service/bin/
$ chmod +x ./*
$ ./installDaemon.sh
$ ./startDaemon.sh
``` 


### Configure Avalanche

- add a file `spirent.sh` to startup profile `/etc/profile.d` with following content:
```
AVA_PATH=/opt/spirent/api/Layer_4_7_Application_Linux/TclAPI
TCLLIBPATH="$AVA_PATH $TCLLIBPATH"
export TCLLIBPATH
export SPIRENT_TCLAPI_ROOT=/opt/spirent/api/Layer_4_7_Application_Linux/TclAPI
export SPIRENT_TCLAPI_LICENSEROOT=/opt/spirent/license/
export SPIRENTD_LICENSE_FILE=@10.128.64.222
export PYTHONPATH=$PYTHONPATH:/opt/spirent/api/Layer_4_7_Application_Linux/STC
```
- apply it once
```
source /etc/profile.d/spirent.sh
```

### Install avaproxy from renat/misc/avaproxy
- install avaproxy source
```
$ mkdir /root/work
$ cd /root/work
$ tar xzvf avaproxy.tar.gz
```

### Install avaproxy service
- copy `avaproxy` from $RENAT_PATH/misc/avaproxy` to /etc/init.d
- configure the service:
```
$ cd /etc/init.d
$ update-rc.d avaproxy defaults
$ systemctl daemon-reload
$ service avaproxy start
$ update-rc.d avaproxy enable
```
- reboot the server and avaproxy will automatically listen at the port defined in `avaproxy` service

