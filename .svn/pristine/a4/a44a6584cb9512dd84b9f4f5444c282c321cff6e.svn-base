# base information
FROM centos:7
LABEL maintainer="bachng@gmail.com"

# parameters
ARG NTP_SERVER=10.128.3.103
ARG RENAT_PASS=password!secret
ARG HTTP_PROXY=http://10.128.3.103:4713
ARG HTTPS_PROXY=http://10.128.3.103:4713
ARG SVN_URL=http://10.128.64.100/svn/automation/renat/trunk



# setting proxy
ENV http_proxy "$HTTP_PROXY"
ENV https_proxy "$HTTPS_PROXY"

# install packages
### update yum and install dev package
RUN yum update -y
RUN yum -y groupinstall "Development Tools"

### install Python 3.x env
RUN yum install -y https://centos7.iuscommunity.org/ius-release.rpm
RUN yum install -y python36u python36u-libs python36u-devel python36u-pip
RUN  pip3.6 install --upgrade pip

### add neccesary packages by yum
RUN yum install -y numpy net-snmp net-snmp-devel net-snmp-utils czmq czmq-devel python36u-tkinter xorg-x11-server-Xvfb  vim httpd xorg-x11-fonts-75dpi  nfs samba4 samba-client samba-winbind cifs-utils tcpdump hping3 telnet nmap wireshark java-1.8.0-openjdk firefox telnet ld-linux.so.2 ghostscript ImageMagick vlgothic-fonts vlgothic-p-fonts ntp openssl sudo openssh-server sshpass
RUN pip3.6 install pytest-runner numpy pyte PyYAML openpyxl Jinja2 pandas lxml requests netsnmp-py pdfkit robotframework robotframework-selenium2library robotframework-sshlibrary docutils pyvmomi PyVirtualDisplay pyscreenshot pillow decorator imgurscrot

### add more packages by rpm
RUN mkdir -p /root/work/download
WORKDIR /root/work/download
RUN wget https://downloads.wkhtmltopdf.org/0.12/0.12.5/wkhtmltox-0.12.5-1.centos7.x86_64.rpm
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.21.0/geckodriver-v0.21.0-linux64.tar.gz
RUN tar xzvf /root/work/download/geckodriver-v0.21.0-linux64.tar.gz -C /usr/local/bin
RUN rpm -Uvh wkhtmltox-0.12.5-1.centos7.x86_64.rpm

### install jenkins
RUN wget -O /etc/yum.repos.d/jenkins.repo http://pkg.jenkins-ci.org/redhat-stable/jenkins.repo
RUN rpm --import https://jenkins-ci.org/redhat/jenkins-ci.org.key

### change sudo setting
RUN echo $'\n\
Defaults    env_keep += "PATH PYTHONPATH LD_LIBRARY_PATH MANPATH XDG_DATA_DIRS PKG_CONFIG_PATH RENAT_PATH"\n\
Cmnd_Alias CMD_ROBOT_ALLOW  = /bin/kill,/usr/local/bin/nmap,/usr/sbin/hping3,/usr/sbin/tcpdump\n\
%renat ALL=NOPASSWD: CMD_ROBOT_ALLOW\n\
%jenkins ALL=NOPASSWD: CMD_ROBOT_ALLOW' > /etc/sudoers.d/renat
RUN chmod 0440 /etc/sudoers.d/renat
RUN sed -i 's/Defaults    secure_path/# &/' /etc/sudoers

### change skeleton setting
ADD files/skel/ /etc/skel/
RUN mkdir -p /etc/skel/work
RUN chmod 0775 /etc/skel/work
RUN sed -i 's/UMASK           077/UMASK           022/' /etc/login.defs

### add a robot account
RUN groupadd renat -o -g 1000
RUN useradd robot -g renat
RUN echo  "robot:$RENAT_PASS" | chpasswd


### httpd setting
RUN gpasswd -a apache renat
RUN sed -i -e 's/UserDir disabled/UserDir enabled/' \
           -e 's/\#UserDir public_html/UserDir work/' \
           -e 's/<Directory "\/home\/\*\/public_html">/<Directory "\/home\/\*\/work">/'  /etc/httpd/conf.d/userdir.conf
RUN sed -i 's/text\/plain            txt asc text pm el c h cc hh cxx hxx f90 conf log/text\/plain            txt asc text pm el c h cc hh cxx hxx f90 conf log robot/' /etc/mime.types
RUN mkdir -p /var/www/html/renat-doc
RUN chown apache:renat /var/www/html/renat-doc/
RUN chmod 0775 /var/www/html/renat-doc/
RUN systemctl enable httpd

### checkout RENAT and customize env
USER robot
WORKDIR /home/robot/work
RUN svn co $SVN_URL renat
ADD --chown=robot:renat files/renat/ /home/robot/work/renat/
RUN sed -i "s/robot-password: password/robot-password: $RENAT_PASS/" /home/robot/work/renat/config/config.yaml

# startup cmds
USER root
ENTRYPOINT ["/sbin/init"]
