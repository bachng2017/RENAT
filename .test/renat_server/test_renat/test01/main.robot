# -*- coding: utf-8 -*-

# Basic setting
*** Setting ***
Documentation   This is a sample test item
Metadata        Log Folder    [../${RESULT_FOLDER}|${CURDIR}/${RESULT_FOLDER}] 
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

06. Show version
    Cmd     show version
