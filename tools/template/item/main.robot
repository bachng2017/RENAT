# -*- coding: utf-8 -*-
# $Date: 2019-07-25 23:50:10 +0900 (木, 25 7 2019) $
# $Rev: 2101 $ 
# $Ver: $
# $Author: $

# Basic setting
*** Setting ***
Documentation   This is a sample test item
Metadata        Log File    [.|${CURDIR}/${RESULT_FOLDER}] 
Suite Setup     Lab Setup
Suite Teardown  Lab Teardown

# Common setting
Resource        lab.robot

# Variable setting
*** Variables ***


*** Test Cases ***
01. Cabling
    [Tags]  cabling
    No Operation

02. Load router config
    [Tags]  load-config
    No Operation

03. Start traffic
    [Tags]  traffic
    No Operation

04. Run test
    Sleep               10s
    No Operation

05. Collect information
    [Tags]  traffic
    No Operation


