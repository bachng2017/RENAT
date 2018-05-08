# -*- coding: utf-8 -*-
# $Date: 2018-03-20 00:33:18 +0900 (Tue, 20 Mar 2018) $
# $Rev: 822 $ 
# $Ver: 0.1.8g $
# $Author: $

# Basic setting
*** Setting ***
Documentation   item01: very simple sample
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
