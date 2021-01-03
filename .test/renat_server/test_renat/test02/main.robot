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
06. Show version
    ${VER}=     Cmd     show version
    Log To Console      ${VER}

