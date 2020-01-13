*** Keywords ***

Add Router
    [Documentation]     Add a router to selected area
    ...                 ${name}:        name of the router
    ...                 ${address}:     borrowed address
    ...                 ${redundancy}:  paired or single (default is single) 
    [Arguments]         ${name}     ${address}=192.168.0.0      ${redundancy}=${FALSE}

    Choose Left Menu                    Router
    Wait and Click Button               Create
    Wait and Click Button               Next 
    Wait Until Element is Visible       //div[@class="v-text-field__slot"]//input   
    Input Text                          (//div[@class="v-text-field__slot"]//input)[1]      ${name}
    Input Text                          (//div[@class="v-text-field__slot"]//input)[2]      ${address}
    Run Keyword Unless  ${redundancy}   Click Element   //label[normalize-space(.)="Redundant existence"]
    Wait and Click Button               Confirm
    Wait and Click Button               Create
    Wait and Click button               OK
    Log                                 Added router `${name}`


Delete Router
    [Documentation]     Remove a router from selected area by its name
    ...                 ${name}:        name of the router    
    [Arguments]         ${name}

    Choose Left Menu                    Router
    Wait and Click Button               Deletion
    Wait and Click Button               Next
    Fic.Capture Screenshot
    Choose Node                         ${name}
    Wait and Click Button               Deletion
    Wait and Click button               OK
    Log                                 Deleted router named `${name}`
    
