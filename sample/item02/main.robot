# -*- coding: utf-8 -*-
# $Date: 2018-03-20 00:33:18 +0900 (Tue, 20 Mar 2018) $
# $Rev: 822 $ 
# $Ver: $
# $Author: $

# Basic setting
*** Setting ***
Documentation   item02: simple sample for Exec File keyword
Metadata        Log File    [.|${CURDIR}/result] 
Suite Setup     Lab Setup
Suite Teardown  Lab Teardown

# Common setting
Resource        lab.robot

# Variable setting
*** Variables ***


*** Test Cases ***
01. Run a command list (Jinja2 supported)
    Router.Switch           vmx11
    Router.Exec File        cmd.lst

02. Using test item specific data directly
    : FOR   ${INTF}     IN  @{LOCAL['interface-list']}
    \   Router.Cmd          show interface ${INTF}

03. Using command list with test item specific data
    Router.Exec File        cmd2.lst

