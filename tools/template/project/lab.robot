# -*- coding: utf-8 -*-
# $Date: 2018-04-10 17:02:41 +0900 (火, 10  4月 2018) $
# $Rev: 900 $
# $Ver: $
# $Author: $

*** Variables ***
# folder and script for polling process on Apollo
${WORKING_FOLDER}           /mnt/fsv01/21_Users/${USER}/working
${POLLING_SCRIPT}           tools/Polling.rb -i 5

*** Setting ***
Resource                    ${RENAT_PATH}/config/extra.robot

*** Keywords ***

Collect Log From File Server
    [Documentation]         moves *.csv files to result folder
    Move Files              ${WORKING_FOLDER}/*.csv     ${RESULT_FOLDER} 

SNMP Polling Start For Host
    [Documentation]         starts polling for a specific host ``host``
    [Arguments]             ${host}         ${filename_prefix}=snmp_
    Set Test Variable       ${device}       ${LOCAL['node'][u'${host}']['device']}
    Set Test Variable       ${ip}           ${GLOBAL['device']['${device}']['ip']}
    ${mibfile} =            MIB For Node    ${host}
    VChannel.Cmd            ${POLLING_SCRIPT} -m ${mibfile} -t ${ip} > ${filename_prefix}${host}.csv &
    VChannel.Cmd            echo $! >> ${MYID}_Polling.txt


SNMP Polling Start
    [Documentation]         starts polling from ``host`` for all node that has ``snmp-polling`` tag
    [Arguments]             ${termname}         ${filename_prefix}=snmp_
    VChannel.Switch         ${termname}
    VChannel.Cmd            cd ${WORKING_FOLDER}
    VChannel.Cmd            [ -s ${WORKING_FOLDER}/${MYID}_Polling.txt ] && kill -9 $(cat ${WORKING_FOLDER}/${MYID}_Polling.txt)
    VChannel.Cmd            [ -f ${WORKING_FOLDER}/${MYID}_Polling.txt ] && rm -f ${WORKING_FOLDER}/${MYID}_Polling.txt
    :FOR    ${entry}   IN  @{NODE}
    \   Run Keyword If      ${NODE[u'${entry}']['snmp-polling']}        SNMP Polling Start For Host     ${entry}    ${filename_prefix}


SNMP Polling Stop
    [Documentation]         stop polling from ``host`` that started by `SNMP Polling Start`
    [Arguments]             ${termname}
    VChannel.Switch         ${termname}
    VChannel.Cmd            [ -s ${WORKING_FOLDER}/${MYID}_Polling.txt ] && kill -9 $(cat ${WORKING_FOLDER}/${MYID}_Polling.txt)
    VChannel.Cmd            [ -f ${WORKING_FOLDER}/${MYID}_Polling.txt ] && rm -f ${WORKING_FOLDER}/${MYID}_Polling.txt

Follow Remote Log Start
    [Documentation]         start remote log from `host` for nodes that has ``follow-remote-log`` flag 
    [Arguments]             ${termname}
    VChannel.Switch         ${termname}
    VChannel.Cmd            cd /var/log
    VChannel.Cmd            [ -s ${WORKING_FOLDER}/${MYID}_TAIL.txt ] && kill -9 $(cat ${WORKING_FOLDER}/${MYID}_TAIL.txt)
    VChannel.Cmd            [ -f ${WORKING_FOLDER}/${MYID}_TAIL.txt ] && rm -f ${WORKING_FOLDER}/${MYID}_TAIL.txt
    @{nodes}=               Common.Node With Attr  follow-remote-log  ${TRUE} 
    ${file_list}=           Set Variable    ${EMPTY}
    :FOR    ${node}  IN  @{nodes}
    \   ${dev}=         Set Variable    ${LOCAL['node'][u'${node}']['device']} 
    \   ${ip}=          Set Variable    ${GLOBAL['device']['${dev}']['ip']} 
    \   ${file_list}=   Set Variable    ${file_list} syslog-net/${ip}.log snmptrap-net/${ip}.log
    Run Keyword If	'${file_list}' != ''	VChannel.Write	tail -n 0 -F ${file_list} &
    Sleep               2s
    Run Keyword If	'${file_list}' != ''	VChannel.Cmd	echo $! > ${WORKING_FOLDER}/${MYID}_TAIL.txt

Follow Remote Log Stop
    [Documentation]         stop and clean up process started by `Follow Remote Log Start`
    [Arguments]             ${termname}
    VChannel.Switch         ${termname}
    VChannel.Write          [ -s ${WORKING_FOLDER}/${MYID}_TAIL.txt ] && kill -9 $(cat ${WORKING_FOLDER}/${MYID}_TAIL.txt)	2s
    VChannel.Write          [ -f ${WORKING_FOLDER}/${MYID}_TAIL.txt ] && rm -f ${WORKING_FOLDER}/${MYID}_TAIL.txt 		2s


Follow Syslog And Trap Start
    [Documentation]                 試験中に出力され、Apollo上に保存されているsyslog-netとsnmptrap-netを保存します。
    ...                             対象の装置はlocal.yamlの follow-remote-log が yes の装置のみです
    [Arguments]                     ${logserver}=apollo  ${logname}=syslog-trap.log  ${termname}=term_syslogtrap
    VChannel.Connect                ${logserver}  ${termname}  ${logname}
    Follow Remote Log Start         ${termname}
    [Return]                        ${termname}

Follow Syslog And Trap Stop
    [Documentation]                 stop and clear process started by `Follow Syslog and Trap Start`
    [Arguments]                     ${termname}=term_syslogtrap
    Follow Remote Log Stop          ${termname}


Lab Setup
    [Documentation]         initial setup for all test cases
    Create Directory        tmp 
    Change Mod              tmp                 0775
    Create Directory        ${WORKING_FOLDER}   

    Change Mod              ${RESULT_FOLDER}    0755

    ${renat_ver}=           RENAT Version
    Set Suite MetaData      RENAT Ver                   ${renat_ver}
    ${README}=              Get File Without Error     ./readme.txt
    Set Suite MetaData      README                      ${README} 
    BuiltIn.Log To Console  RENAT Ver:: ${renat_ver}
    BuiltIn.Log To Console  ------------------------------------------------------------------------------
    BuiltIn.Log To Console  README:
    BuiltIn.Log To Console  ${readme}
    BuiltIn.Log To Console  ------------------------------------------------------------------------------

    ${HAS_CLEAN}=           Get Variable Value  ${CLEAN}
    Run Keyword If          "${HAS_CLEAN}"!="None"             CleanUp Result

    VChannel.Connect All 

    # initialize extra libraries
    Extra.Connect All

    # load plugin
    Common.Load Plugin

    Logger.Log All          TESTING BEGIN   ${TRUE}     ===
    @{node_list}=           Node With Tag    init    juniper
    :FOR  ${node}  IN  @{node_list}
    \   Router.Switch       ${node}
    \   Router.Cmd          show system uptime | no-more
    \   Router.Cmd          show version invoke-on all-routing-engines | no-more
    \   Router.Cmd          show system alarms | no-more
    \   Router.Cmd          show chassis hardware | no-more

    BuiltIn.Log To Console  00. Lab Setup
    BuiltIn.Log To Console  ------------------------------------------------------------------------------


Lab Teardown
    [Documentation]         final teardown for all test cases
    Remove File             ${CURDIR}/tmp/*
    Logger.Log All          TESTING FINISH   ${TRUE}     ===
    Collect Log from File Server

    # Cleanup extra libraries    
    Extra.Close All

    VChannel.Close All 
    Close All Browsers 
    BuiltIn.Log To Console  99. Lab Teardown
    BuiltIn.Log To Console  ------------------------------------------------------------------------------

Chibalab Setup
    [Documentation]         initial setup for all test cases
    Lab Setup

Chibalab Teardown
    [Documentation]         final teardown for all test cases
    Lab Teardown
