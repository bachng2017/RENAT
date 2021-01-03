# -*- coding: utf-8 -*-

*** Variables ***
# folder and script for polling process on Apollo or Artemis
${POLLING_SCRIPT}           /ocn-gin/script/Polling/Polling.rb -i 5
# node name for polling process. e.g. apollo artemis
${POLLING_SERVER}           apollo
# node name for follow syslog,trap file. e.g. apollo artemis
${FOLLOWLOG_SERVER}         apollo

# Global Variable
# Follow Syslog And Trap Startの重複起動対策フラグ
${IS_RUNNING_FOLLOWLOG}     ${FALSE}

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
    [Arguments]             ${logserver}=${POLLING_SERVER}      ${filename_prefix}=snmp_    ${logname}=term_snmppoller.log      ${term_name}=term_snmppoller
    VChannel.Connect        ${logserver}    ${term_name}     ${logname}
    VChannel.Switch         ${term_name}
    VChannel.Cmd            shopt -s huponexit
    VChannel.Cmd            cd ${WORKING_FOLDER}
    VChannel.Cmd            [ -s ${WORKING_FOLDER}/${MYID}_Polling.txt ] && kill -9 $(cat ${WORKING_FOLDER}/${MYID}_Polling.txt)
    VChannel.Cmd            [ -f ${WORKING_FOLDER}/${MYID}_Polling.txt ] && rm -f ${WORKING_FOLDER}/${MYID}_Polling.txt
    VChannel.Cmd            [ -f ${WORKING_FOLDER}/${MYID}_CSVList.txt ] && rm -f ${WORKING_FOLDER}/${MYID}_CSVList.txt
    FOR     ${entry}    IN      @{NODE}
        Run Keyword If      ${NODE[u'${entry}']['snmp-polling']}        SNMP Polling Start For Host     ${entry}    ${filename_prefix}
    END

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
    ...                     デフォルトのログサーバは ${FOLLOWLOG_SERVER} のため、他サーバを使用する場合はlogserver変数を明示的に指定してください。
    ...                     保存対象装置は local.yaml の follow-remote-log が yes の装置のみです
    [Arguments]             ${logserver}=${FOLLOWLOG_SERVER}    ${logname}=syslog-trap.log      ${term_name}=term_syslogtrap
    # follow-remote-log対象が存在しない場合はそのまま終了する
    @{NODE_LIST}=               Common.Node With Attr  follow-remote-log  ${TRUE}
    ${length}=                  Get Length      ${NODE_LIST}
    Return From Keyword If      0 == ${length}

    # 重複起動対策
    Return From Keyword If      ${IS_RUNNING_FOLLOWLOG}
    ${IS_RUNNING_FOLLOWLOG}=    Set Variable    ${TRUE}
    Set Global Variable     ${IS_RUNNING_FOLLOWLOG}


    VChannel.Connect        ${logserver}  ${term_name}  ${term_name}.log
    VChannel.Cmd            shopt -s huponexit
    VChannel.Cmd            cd /var/log
    VChannel.Cmd            [ -s ${WORKING_FOLDER}/${MYID}_TAIL.txt ] && kill -9 $(cat ${WORKING_FOLDER}/${MYID}_TAIL.txt)
    VChannel.Cmd            [ -f ${WORKING_FOLDER}/${MYID}_TAIL.txt ] && rm -f ${WORKING_FOLDER}/${MYID}_TAIL.txt
    VChannel.Cmd            [ -f ${WORKING_FOLDER}/${MYID}_${logname} ] && rm -f ${WORKING_FOLDER}/${MYID}_${logname}
    ${file_list}=           Set Variable    ${EMPTY}
    FOR     ${ITEM}     IN      @{NODE_LIST}
        ${dev}=             Set Variable    ${LOCAL['node'][u'${ITEM}']['device']}
        ${ip}=              Set Variable    ${GLOBAL['device']['${dev}']['ip']}
        ${file_list}=       Set Variable    ${file_list} syslog-net/${ip}.log snmptrap-net/${ip}.log
    END
    Run Keyword If	'${file_list}' != ''	VChannel.Cmd	tail -n 0 -F ${file_list} >> ${WORKING_FOLDER}/${MYID}_${logname} &
    Sleep                   2s
    Run Keyword If	'${file_list}' != ''	VChannel.Cmd	echo $! > ${WORKING_FOLDER}/${MYID}_TAIL.txt
    [Return]                ${term_name}

Follow Syslog And Trap Stop
    [Documentation]         `Follow Syslog And Trap Start` で開始されたプロセスを終了させます。
    [Arguments]             ${term_name}=term_syslogtrap    ${logname}=syslog-trap.log
    # 重複起動対策
    Return From Keyword If      not ${IS_RUNNING_FOLLOWLOG}
    ${IS_RUNNING_FOLLOWLOG}=    Set Variable    ${FALSE}
    Set Global Variable     ${IS_RUNNING_FOLLOWLOG}
    VChannel.Switch         ${term_name}
    VChannel.Cmd            [ -s ${WORKING_FOLDER}/${MYID}_TAIL.txt ] && kill -9 $(cat ${WORKING_FOLDER}/${MYID}_TAIL.txt)
    VChannel.Cmd            [ -f ${WORKING_FOLDER}/${MYID}_TAIL.txt ] && rm -f ${WORKING_FOLDER}/${MYID}_TAIL.txt
    VChannel.Cmd            sync
    Sleep                   10s
    # RENAT local
    Run                     [ -f ${WORKING_FOLDER}/${MYID}_${logname} ] && mv ${WORKING_FOLDER}/${MYID}_${logname} ${RESULT_FOLDER}/${logname}
    Sleep                   5s
    VChannel.Close

Follow Syslog Start With Tag
    [Documentation]         指定したtagを持つnodeについて、試験中に出力されるsyslog-netを保存します。
    ...                     デフォルトのログサーバは ${FOLLOWLOG_SERVER} のため、他サーバを使用する場合はlogserver変数を明示的に指定してください。
    [Arguments]             ${tag}=syslog       ${logdir}=syslog-net        ${logserver}=${FOLLOWLOG_SERVER}
    ${term_name}=           Follow Remote Log Start With Tag    ${tag}      ${logdir}       ${logserver}
    [Return]                ${term_name}

Follow Trap Start With Tag
    [Documentation]         指定したtagを持つnodeについて、試験中に出力されるsnmptrap-netを保存します。
    ...                     デフォルトのログサーバは ${FOLLOWLOG_SERVER} のため、他サーバを使用する場合はlogserver変数を明示的に指定してください。
    [Arguments]             ${tag}=trap         ${logdir}=snmptrap-net      ${logserver}=${FOLLOWLOG_SERVER}
    ${term_name}=           Follow Remote Log Start With Tag    ${tag}      ${logdir}       ${logserver}
    [Return]                ${term_name}

Follow Remote Log Start With Tag
    [Documentation]         指定したtagを持つnodeについて、試験中に出力されるログを保存します。
    ...                     デフォルトのログサーバは ${FOLLOWLOG_SERVER} のため、他サーバを使用する場合はlogserver変数を明示的に指定してください。
    [Arguments]             ${tag}=syslog       ${logdir}=syslog-net    ${logserver}=${FOLLOWLOG_SERVER}
    ${logname}=             Set Variable    ${logdir}-${tag}.log
    ${term_name}=           Set Variable    term_${logdir}_${tag}
    VChannel.Connect        ${logserver}  ${term_name}  ${term_name}.log
    VChannel.Cmd            shopt -s huponexit
    VChannel.Cmd            cd /var/log
    VChannel.Cmd            [ -s ${WORKING_FOLDER}/${MYID}_TAIL_${logdir}_${tag}.txt ] && kill -9 $(cat ${WORKING_FOLDER}/${MYID}_TAIL_${logdir}_${tag}.txt)
    VChannel.Cmd            [ -f ${WORKING_FOLDER}/${MYID}_TAIL_${logdir}_${tag}.txt ] && rm -f ${WORKING_FOLDER}/${MYID}_TAIL_${logdir}_${tag}.txt
    VChannel.Cmd            [ -f ${WORKING_FOLDER}/${MYID}_${logname} ] && rm -f ${WORKING_FOLDER}/${MYID}_${logname}
    @{NODE_LIST}=           Common.Node With Tag  ${tag}
    ${file_list}=           Set Variable    ${EMPTY}
    FOR     ${ITEM}     IN      @{NODE_LIST}
        ${dev}=             Set Variable    ${LOCAL['node'][u'${ITEM}']['device']}
        ${ip}=              Set Variable    ${GLOBAL['device']['${dev}']['ip']}
        ${file_list}=       Set Variable    ${file_list} ${logdir}/${ip}.log
    END
    Run Keyword If	'${file_list}' != ''	VChannel.Cmd	tail -n 0 -F ${file_list} >> ${WORKING_FOLDER}/${MYID}_${logname} &
    Sleep                   2s
    Run Keyword If	'${file_list}' != ''	VChannel.Cmd	echo $! > ${WORKING_FOLDER}/${MYID}_TAIL_${logdir}_${tag}.txt
    [Return]                ${term_name}

Follow Syslog Stop With Tag
    [Documentation]         指定したtagを持つnodeについて、syslog-net取得を停止し、resultにファイル移動します。
    [Arguments]             ${tag}=syslog       ${logdir}=syslog-net
    Follow Remote Log Stop With Tag     ${tag}      ${logdir}

Follow Trap Stop With Tag
    [Documentation]         指定したtagを持つnodeについて、snmptrap-net取得を停止し、resultにファイル移動します。
    [Arguments]             ${tag}=trap         ${logdir}=snmptrap-net
    Follow Remote Log Stop With Tag     ${tag}      ${logdir}

Follow Remote Log Stop With Tag
    [Documentation]         `Follow Remote Log Start With Tag` で開始されたプロセスを終了させます。
    [Arguments]             ${tag}=syslog       ${logdir}=syslog-net
    ${logname}=             Set Variable    ${logdir}-${tag}.log
    ${term_name}=           Set Variable    term_${logdir}_${tag}
    VChannel.Switch         ${term_name}
    VChannel.Cmd            [ -s ${WORKING_FOLDER}/${MYID}_TAIL_${logdir}_${tag}.txt ] && kill -9 $(cat ${WORKING_FOLDER}/${MYID}_TAIL_${logdir}_${tag}.txt)
    VChannel.Cmd            [ -f ${WORKING_FOLDER}/${MYID}_TAIL_${logdir}_${tag}.txt ] && rm -f ${WORKING_FOLDER}/${MYID}_TAIL_${logdir}_${tag}.txt
    VChannel.Cmd            sync
    Sleep                   10s
    # RENAT local
    Run                     [ -f ${WORKING_FOLDER}/${MYID}_${logname} ] && mv ${WORKING_FOLDER}/${MYID}_${logname} ${RESULT_FOLDER}/${logname}
    Sleep                   5s
    VChannel.Close

Lab Setup
    [Documentation]         initial setup for all test cases
    Create Directory        tmp
    Change Mod              tmp                 0775
    Create Directory        ${WORKING_FOLDER}
    Change Mod              ${RESULT_FOLDER}    0775

    Remove File             ./.stop

    Set Library Search Order    Common  Router  WebApp

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

    # connect to all nodes
    VChannel.Connect All

    # initialize extra libraries
    Extra.Connect All

    # load plugin
    Common.Load Plugin

    Logger.Log All          TESTING BEGIN   ${TRUE}     ===
    @{NODE_LIST}=           Node With Tag    juniper    timestamp
    FOR     ${ITEM}     IN      @{NODE_LIST}
        Router.Switch       ${ITEM}
        Router.Cmd          set cli timestamp
    END

    @{NODE_LIST}=           Node With Tag    juniper    init
    FOR     ${ITEM}     IN      @{NODE_LIST}
        Router.Switch       ${ITEM}
        Router.Cmd          show system uptime | no-more
        Router.Cmd          show version invoke-on all-routing-engines | no-more
        Router.Cmd          show system alarms | no-more
        Router.Cmd          show chassis hardware | no-more
    END

    FOR     ${ITEM}     IN      @{NODE}
        Router.Switch       ${ITEM}
        Router.Cmd
    END

    # follow syslog and trap with attr follow-remote-log: yes
    Follow Syslog And Trap Start

    # run User Setup
    Run Keyword If Exist    User Setup

    BuiltIn.Log To Console  00. Lab Setup
    BuiltIn.Log To Console  ------------------------------------------------------------------------------


Lab Teardown
    [Documentation]         final teardown for all test cases
    # run User Teardown
    Run Keyword If Exist    User Teardown

    Remove Directory        ${CURDIR}/tmp   recursive=${TRUE}
    # Logger.Log All          TESTING FINISH   ${TRUE}     ===
    # stop follow syslog and trap with attr follow-remote-log: yes
    Follow Syslog And Trap Stop

    # Collect Remote SNMP Polling CSV
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
