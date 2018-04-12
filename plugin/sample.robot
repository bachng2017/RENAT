*** Keywords ***
Sample
    [Documentation]     Sample plugin
    ...                 usage: Sample   arg
    ...                 The keyword does not use local.yaml
    [Arguments]         ${ARG}

    Log To Console      Sample keyword with a argument ${ARG}
