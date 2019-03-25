# -*- coding: utf-8 -*-
# $Date: 2019-03-25 01:28:51 +0900 (月, 25  3月 2019) $
# $Rev: 1914 $
# $Ver: $
# $Author: $

*** Variables ***
# folder and script for polling process on Apollo
${WORKING_FOLDER}           ${HOME}/work
${POLLING_SCRIPT}           tools/Polling.rb -i 5

*** Setting ***
Resource                    ${RENAT_PATH}/config/extra.robot

*** Keywords ***

Collect Log From File Server
    [Documentation]         moves *.csv files to result folder on local operating system
    ...                     `SNMP Polling Start/Stop` で取得したCSVファイルをpollingサーバから収集します
    Run                     [ -f ${WORKING_FOLDER}/${MYID}_CSVList.txt ] && while read i; do mv $i; done < ${WORKING_FOLDER}/${MYID}_CSVList.txt
    Run                     [ -f ${WORKING_FOLDER}/${MYID}_CSVList.txt ] && rm -f ${WORKING_FOLDER}/${MYID}_CSVList.txt

SNMP Polling Start For Host
    [Documentation]         starts polling for a specific host ``host``
    [Arguments]             ${host}         ${filename_prefix}=snmp_
    Set Test Variable       ${device}       ${LOCAL['node'][u'${host}']['device']}
    Set Test Variable       ${ip}           ${GLOBAL['device']['${device}']['ip']}
    ${mibfile} =            MIB For Node    ${host}
    VChannel.Cmd            ${POLLING_SCRIPT} -m ${mibfile} -t ${ip} > ${MYID}_${filename_prefix}${host}.csv &
    VChannel.Cmd            echo $! >> ${MYID}_Polling.txt
    VChannel.Cmd            echo ${WORKING_FOLDER}/${MYID}_${filename_prefix}${host}.csv ${RESULT_FOLDER}/${filename_prefix}${host}.csv >> ${WORKING_FOLDER}/${MYID}_CSVList.txt

SNMP Polling Start
    [Documentation]         starts polling from ``host`` for all node that has ``snmp-polling`` tag
    ...                     local.yaml 内の node で `snmp-polling: yes` を設定された全装置のMIB値を定期的に取得開始します。
    ...                     本Keywordで開始したプロセスは `SNMP Polling Stop` で停止され、保存されたCSVファイルは `Collect Log From File Server` でresultフォルダに移動されます
    [Arguments]             ${logserver}=apollo     ${filename_prefix}=snmp_    ${logname}=term_snmppoller.log      ${term_name}=term_snmppoller
    VChannel.Connect        ${logserver}    ${term_name}     ${logname}
    VChannel.Switch         ${term_name}
    VChannel.Cmd            cd ${WORKING_FOLDER}
    VChannel.Cmd            [ -s ${WORKING_FOLDER}/${MYID}_Polling.txt ] && kill -9 $(cat ${WORKING_FOLDER}/${MYID}_Polling.txt)
    VChannel.Cmd            [ -f ${WORKING_FOLDER}/${MYID}_Polling.txt ] && rm -f ${WORKING_FOLDER}/${MYID}_Polling.txt
    VChannel.Cmd            [ -f ${WORKING_FOLDER}/${MYID}_CSVList.txt ] && rm -f ${WORKING_FOLDER}/${MYID}_CSVList.txt
    :FOR    ${entry}   IN  @{NODE}
    \   Run Keyword If      ${NODE[u'${entry}']['snmp-polling']}        SNMP Polling Start For Host     ${entry}    ${filename_prefix}

SNMP Polling Stop
    [Documentation]         stop polling from ``host`` that started by `SNMP Polling Start`
    ...                     `SNMP Polling Start` で起動されたプロセスを停止します。
    [Arguments]             ${term_name}=term_snmppoller
    VChannel.Switch         ${term_name}
    VChannel.Cmd            [ -s ${WORKING_FOLDER}/${MYID}_Polling.txt ] && kill -9 $(cat ${WORKING_FOLDER}/${MYID}_Polling.txt)
    VChannel.Cmd            [ -f ${WORKING_FOLDER}/${MYID}_Polling.txt ] && rm -f ${WORKING_FOLDER}/${MYID}_Polling.txt
    VChannel.Close

Follow Syslog And Trap Start
    [Documentation]         試験中に出力されるsyslog-netとsnmptrap-netを保存します。
    ...                     デフォルトのログサーバはapolloのため、他サーバを使用する場合はlogserver変数を明示的に指定してください。
    ...                     保存対象装置は local.yaml の follow-remote-log が yes の装置のみです
    [Arguments]             ${logserver}=apollo  ${logname}=syslog-trap.log  ${term_name}=term_syslogtrap
    VChannel.Connect        ${logserver}  ${term_name}  ${logname}
    VChannel.Cmd            cd /var/log
    VChannel.Cmd            [ -s ${WORKING_FOLDER}/${MYID}_TAIL.txt ] && kill -9 $(cat ${WORKING_FOLDER}/${MYID}_TAIL.txt)
    VChannel.Cmd            [ -f ${WORKING_FOLDER}/${MYID}_TAIL.txt ] && rm -f ${WORKING_FOLDER}/${MYID}_TAIL.txt
    @{NODE_LIST}=           Common.Node With Attr  follow-remote-log  ${TRUE}
    ${file_list}=           Set Variable    ${EMPTY}
    :FOR    ${ITEM}  IN  @{NODE_LIST}
    \   ${dev}=             Set Variable    ${LOCAL['node'][u'${ITEM}']['device']}
    \   ${ip}=              Set Variable    ${GLOBAL['device']['${dev}']['ip']}
    \   ${file_list}=       Set Variable    ${file_list} syslog-net/${ip}.log snmptrap-net/${ip}.log
    Run Keyword If	'${file_list}' != ''	VChannel.Write	tail -n 0 -F ${file_list} &
    Sleep                   2s
    Run Keyword If	'${file_list}' != ''	VChannel.Cmd	echo $! > ${WORKING_FOLDER}/${MYID}_TAIL.txt
    [Return]                ${term_name}

Follow Syslog And Trap Stop
    [Documentation]             `Follow Syslog And Trap Start` で開始されたプロセスを終了させます。
    [Arguments]                 ${term_name}=term_syslogtrap
    VChannel.Switch             ${term_name}
    VChannel.Write              [ -s ${WORKING_FOLDER}/${MYID}_TAIL.txt ] && kill -9 $(cat ${WORKING_FOLDER}/${MYID}_TAIL.txt)  10s
    VChannel.Write              [ -f ${WORKING_FOLDER}/${MYID}_TAIL.txt ] && rm -f ${WORKING_FOLDER}/${MYID}_TAIL.txt   5s
    VChannel.Close

Lab Setup
    [Documentation]         initial setup for all test cases
    Create Directory        tmp
    Change Mod              tmp                 0775
    Create Directory        ${WORKING_FOLDER}

    Change Mod              ${RESULT_FOLDER}    0775

    Set Library Search Order    Common  Router

    Common.Start Display

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
    @{NODE_LIST}=           Node With Tag    init    juniper
    :FOR  ${ITEM}  IN  @{NODE_LIST}
    \   Router.Switch       ${ITEM}
    \   Router.Cmd          show system uptime | no-more
    \   Router.Cmd          show version invoke-on all-routing-engines | no-more
    \   Router.Cmd          show system alarms | no-more
    \   Router.Cmd          show chassis hardware | no-more

    :FOR  ${ITEM}   IN      @{NODE}
    \   Router.Switch       ${ITEM}
    \   Router.Cmd

    BuiltIn.Log To Console  00. Lab Setup
    BuiltIn.Log To Console  ------------------------------------------------------------------------------


Lab Teardown
    [Documentation]         final teardown for all test cases
    Remove Directory        ${CURDIR}/tmp   recursive=${TRUE}
    # Logger.Log All          TESTING FINISH   ${TRUE}     ===
    Collect Log from File Server

    # Cleanup extra libraries
    Extra.Close All

    VChannel.Close All      TESTING FINISH  ${TRUE}     ===
    Close All Browsers
    Common.Close Display
    BuiltIn.Log To Console  99. Lab Teardown
    BuiltIn.Log To Console  ------------------------------------------------------------------------------

Chibalab Setup
    [Documentation]         initial setup for all test cases
    Lab Setup

Chibalab Teardown
    [Documentation]         final teardown for all test cases
    Lab Teardown
