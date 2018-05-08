# -*- coding: utf-8 -*-
# $Date: 2018-03-20 00:33:18 +0900 (Tue, 20 Mar 2018) $
# $Rev: 822 $ 
# $Ver: 0.1.8g $
# $Author: $

# Basic setting
*** Setting ***
Documentation   item03: best path testing    
Metadata        Log File    [.|${CURDIR}/result] 
Suite Setup     Lab Setup
Suite Teardown  Lab Teardown

# Common setting
Resource        lab.robot

# Variable setting
*** Variables ***

*** Test Cases ***
01. Cabling
    No Operation

02. Load config to DUT 
    Router.Switch                   target
    Router.Load Config              set             target.conf     vars=INTERFACE=et-0/0/2
    
03. Load tester config
    Tester.Switch                   tester
    Tester.Load Traffic             apply=${FALSE}
    Sleep                           30s
    
04. Confirm the status
    ${num}=                         Router.Number Of BGP Neighbor
    Should Be Equal                 ${num}          ${10}
    Router.Cmd                      show bgp summary

05. Flap interface once
    Router.Flap Interface           et-0/0/2.2      30s
    Sleep                           120s 

06. Collect route information
    ${show4}=                       Router.Cmd      show route 1/8 detail
    ${show6}=                       Router.Cmd      show route 1::/16 detail
    Set Suite Variable              ${show4}
    Set Suite Variable              ${show6}

07. Get best path result
    Create Best Path Select Data    ${show4}        best4.xlsx
    Create Best Path Select Data    ${show6}        best6.xlsx




