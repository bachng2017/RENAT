# RENAT installation instructions for Centos7 + Python3
date: 20180826



### base install
Install a typical Centos7 with following parameters:

    - memory: 16G (or more)
    - HDD: 64G (or more)
    - NIC: 2
    - package: minimum (+developer package)
    - ip address: 10.128.64.10/16 (sample)
    - gw: 10.128.1.1 (sample)
    - dns: 10.128.3.101 (sample)
    - hostname: renat.localhost (sample)

### post install configuration
- disable SE linux:
    - disable the feature

        ```
        set enforce 0
        ```

    - configure `SELINUX=disabled` in the `/etc/selinux/config` file:

- update install package and `reboot` the system

    ```
    yum update -y
    reboot
    ```
        
### library installation
- install python3 and related library

    ```
    yum install -y https://centos7.iuscommunity.org/ius-release.rpm
    yum install -y python36u python36u-libs python36u-devel python36u-pip
    pip3.6 install --upgrade pip 
    ```

- install extra libraries

    ```
    yum install -y numpy net-snmp net-snmp-devel net-snmp-utils czmq czmq-devel python35u-tkinter xorg-x11-server-Xvfb  vim httpd xorg-x11-fonts-75dpi  nfs samba4 samba-client samba-winbind cifs-utils tcpdump hping3 telnet nmap wireshark java-1.8.0-openjdk firefox-52.8.0-1.el7.centos.x86_64 telnet ld-linux.so.2 ghostscript ImageMagick vlgothic-fonts vlgothic-p-fonts ntp
    pip3.6 install pytest-runner
    pip3.6 install numpy pyte PyYAML openpyxl Jinja2 pandas lxml requests netsnmp-py pdfkit robotframework robotframework-selenium2library robotframework-sshlibrary docutils pyvmomi PyVirtualDisplay pyscreenshot pillow decorator
    ```
    
- add just selenium version

    ```
    pip3.6 uninstall selenium
    pip3.6 install selenium==2.53.6
    ```
    
- install libraries (besides yum)

    ```
    cd /root
    mkdir -p work/download
    cd work/download        

    sudo wget -O /etc/yum.repos.d/jenkins.repo http://pkg.jenkins-ci.org/redhat-stable/jenkins.repo
    
    sudo rpm --import https://jenkins-ci.org/redhat/jenkins-ci.org.key
    yum install -y jenkins
    
    cd /root/work/download
    wget https://github.com/mozilla/geckodriver/releases/download/v0.21.0/geckodriver-v0.21.0-linux64.tar.gz
    tar xzvf /root/work/download/geckodriver-v0.21.0-linux64.tar.gz -C /usr/local/bin

    cd /root/work/download
    wget https://downloads.wkhtmltopdf.org/0.12/0.12.5/wkhtmltox-0.12.5-1.centos7.x86_64.rpm
    rpm -Uvh wkhtmltox-0.12.5-1.centos7.x86_64.rpm
    ```
        
### configuration 
- modify NTP server
    - modify /etc/ntp.conf for favourite NTP server
    - activate and make the service auto start
       ```
       service ntpd start
       chkconfig ntpd on
       ```
    - check the current NTP
       ```
       ntpq -p
       ```


- sudo privilege
    - add a file named `renat` (persion 0440) to folder `/etc/sudoers.d`
    
        ```
        Defaults    env_keep += "PATH PYTHONPATH LD_LIBRARY_PATH MANPATH XDG_DATA_DIRS PKG_CONFIG_PATH RENAT_PATH"
        Cmnd_Alias CMD_ROBOT_ALLOW  = /bin/kill,/usr/local/bin/nmap,/usr/sbin/hping3,/usr/sbin/tcpdump
        %techno ALL=NOPASSWD: CMD_ROBOT_ALLOW
        %jenkins ALL=NOPASSWD: CMD_ROBOT_ALLOW        
        ```
        
    - comment out the line including `secure_path` in the file `/etc/sudoers`
    
        ```
        # Defaults    secure_path = /sbin:/bin:/usr/sbin:/usr/bin
        ```
        
- change some system default behaviours
    - create a folder name `work` under `/etc/skel` with permission `0775`
    - change `UMASK` to `022` in the file `/etc/login.defs`

        ```
        # UMASK           077
        UMASK           022
        ```
        
- add a default group and user and set its password

    ```
    groupadd techno -o -g 1000
    useradd robot -g techno
    passwd robot
    ```

        
    *Note*: the password of this `robot` account is set in the RENAT config file `${RENAT_PATH}/config/config.yaml`
    

- configure jenkins:
    - Change jenkins listen port `JENNKINS_PORT` to `8002` in file `/etc/sysconfig/jenkins`
    
        ```
        # JENKINS_PORT="8080"
        JENKINS_PORT="8082"
        ```
        
    - enable the service
    
        ```
        systemctl enable jenkins
        systemctl start jenkins
        ```

- configure iptables:
    By default, Centos7 does not support saving iptables from `service` command. 
    ```
    systemctl stop firewalld
    systemctl disable firewalld
    yum install -y iptables-services
    systemctl enable iptables.service
    systemctl start iptables.service
    ```
    
    Then configure `iptables` to allow necessary ports like `80`,`8082`,`22` and traffic from IxiaAppServer.
    Or allow access for your whole local network:
    ```
    -A INPUT -s 10.128.0.0/16 -j ACCEPT
    ```

- configure httpd service
    - add `apache` to `techno` group
    - modify `userdir.conf` under folder `/etc/httpd/conf.d` to show list the `work` folder of each user
    
        ```
        # UserDir disabled
        UserDir enabled

        # UserDir public_html
        UserDir work

        # <Directory "/home/*/public_html">
         <Directory "/home/*/work">
           IndexOptions +NameWidth=*
        ```
        
        *Note*: Do not for get the `<Directory>` section
            
    - add robot to mime type in file `/etc/mime.types`
        ```
        # text/plain            txt asc text pm el c h cc hh cxx hxx f90 conf log
        text/plain              txt asc text pm el c h cc hh cxx hxx f90 conf log robot
        ```
    - prepare the document folder
    
        ```  
        mkdir -p /var/www/html/renat-doc
        chown apache:techno /var/www/html/renat-doc/
        chmod 0775 /var/www/html/renat-doc/
        ```
            
    - enable and restart the service
    
        ```
        systemctl restart httpd
        systemctl enable httpd
        ```

- make skeleton for users
    - create a folder call `work` under `/etc/skel` with mode `0750`

### add a renat user
- add a user to the group `techno`

    ```
    useradd user -g techno
    passwd user
    ```

- login as the new user
    
- create a key for the account `robot` that would be used for using with SSH proxy. Enter when asked for password (2 times)

    ```
    mkdir ~/.ssh
    cd ~/.ssh
    ssh-keygen -C for_robot_`whoami` -f robot_id_rsa
    
- push to key to proxy server using `robot` password
    ```
    ssh-copy-id -i robot_id_rsa.pub robot@<proxy server IP>
    ```

### install Ixia related (optional)
- download necessary files (below are samples. Use the correct install files in your environment)

    ```
    BPSRobotLibrary.tgz
    IxNetworkTclClient7.41.945.9Linux.bin.tgz
    IxOS6.80.1100.9Linux64.bin.tar.gz
    ```
- install IxOS. Choose `Tcl8.5` and default destination folder `/opt/ixia/ixos/6.80-EA-SP1`

    ```
    tar xzvf IxOS6.80.1100.9Linux64.bin.tar.gz
    ./IxOS6.80.1100.9Linux64.bin -i console
    ```
    
- install IxNetwork. Choose `/opt/ixia/ixnet/7.41-EA` for default destination folder and `1-Yes` for `HTLAPI` when asked (let other option as default)

    ```
    tar xzvf IxNetworkTclClient7.41.945.9Linux.bin.tgz
    ./IxNetworkTclClient7.41.945.9Linux.bin -i console
    
- install IOxLoad. Choose `/opt/ixia/ixload/8.01.99.14` for default destination folder.

    ```
    tar xzvf IxLoadTclApi8.01.99.14Linux_x64.bin.tgz
    ./IxLoadTclApi8.01.99.14Linux_x64.bin -i console
    ```
*Note*: if it is necessary remove the folder if you chose wrong destination folder and reinstall

### install Avalanche related (optional)
- install avalanch api
    
    ```
    pip3.6 install avalancheapi
    ```

-
