// Browser companions for Peach's authored capture-the-flag rules.
// Observe map state and issue ordinary orders; map triggers own pickups, tags, jail and scoring.
native BrowserBotPlayerEligible takes player whichPlayer returns boolean

globals
    timer browserPeachTimer = null
    unit array browserPeachDefenseTarget
endglobals

function BrowserPeachInside takes unit runner, rect bounds returns boolean
    return bounds != null and GetUnitX(runner) >= GetRectMinX(bounds) and GetUnitX(runner) <= GetRectMaxX(bounds) and GetUnitY(runner) >= GetRectMinY(bounds) and GetUnitY(runner) <= GetRectMaxY(bounds)
endfunction

function BrowserPeachCarries takes unit runner, integer rawcode returns boolean
    local integer slot = 0
    loop
        exitwhen slot >= 6
        if GetItemTypeId(UnitItemInSlot(runner, slot)) == rawcode then
            return true
        endif
        set slot = slot + 1
    endloop
    return false
endfunction

function BrowserPeachOrder takes unit runner returns nothing
    local player owner = GetOwningPlayer(runner)
    local boolean teamOne = IsPlayerAlly(owner, Player(0))
    local rect home = gg_rct_Team_2_side
    local rect jail = gg_rct_Team_1_Jail
    local unit flag = udg_flag_1
    local integer flagItem = 'I001'
    local integer jailed = udg_Number_Jailed_Team_2
    local unit candidate = null
    local unit closest = null
    local real distance = 262144.0
    local real dx = 0.0
    local real dy = 0.0
    local integer index = 1
    if teamOne then
        set home = gg_rct_Team_1_side
        set jail = gg_rct_Team_2_Jail
        set flag = udg_flag_2
        set flagItem = 'I000'
        set jailed = udg_Number_Jailed_Team_1
    endif
    if BrowserPeachCarries(runner, flagItem) then
        set browserPeachDefenseTarget[GetPlayerId(owner)] = null
        call IssuePointOrder(runner, "move", GetRectCenterX(home), GetRectCenterY(home))
        return
    endif
    if BrowserPeachInside(runner, home) then
        loop
            exitwhen index > 12
            set candidate = udg_Unit_identifier_for_player_X[index]
            if candidate != null and candidate != runner and GetUnitTypeId(candidate) == 'H000' and GetWidgetLife(candidate) > 0.0 and not IsUnitPaused(candidate) and not IsUnitHidden(candidate) and IsUnitVisible(candidate, owner) and not udg_Players_In_Jail[index] and IsPlayerEnemy(owner, GetOwningPlayer(candidate)) and BrowserPeachInside(candidate, home) then
                set dx = GetUnitX(candidate) - GetUnitX(runner)
                set dy = GetUnitY(candidate) - GetUnitY(runner)
                if dx * dx + dy * dy < distance then
                    set closest = candidate
                    set distance = dx * dx + dy * dy
                endif
            endif
            set index = index + 1
        endloop
        if closest != null then
            if GetUnitCurrentOrder(runner) == OrderId("attack") and browserPeachDefenseTarget[GetPlayerId(owner)] == closest then
                return
            endif
            if IssueTargetOrder(runner, "attack", closest) then
                set browserPeachDefenseTarget[GetPlayerId(owner)] = closest
                return
            endif
        endif
    endif
    set browserPeachDefenseTarget[GetPlayerId(owner)] = null
    if jailed > 0 and jail != null then
        call IssuePointOrder(runner, "move", GetRectCenterX(jail), GetRectCenterY(jail))
    elseif flag != null and GetWidgetLife(flag) > 0.0 and not IsUnitHidden(flag) then
        call IssuePointOrder(runner, "move", GetUnitX(flag), GetUnitY(flag))
    elseif home != null then
        // A teammate carries the hidden flag; cover the home half until the next map transition.
        call IssuePointOrder(runner, "move", GetRectCenterX(home), GetRectCenterY(home))
    endif
endfunction

function BrowserPeachTick takes nothing returns nothing
    local integer index = 1
    local unit runner = null
    loop
        exitwhen index > 12
        set runner = udg_Unit_identifier_for_player_X[index]
        if runner != null and GetUnitTypeId(runner) == 'H000' and GetWidgetLife(runner) > 0.0 and not IsUnitPaused(runner) and not IsUnitHidden(runner) and not udg_Players_In_Jail[index] and IsUnitInGroup(runner, udg_Main_Player_Units) and BrowserBotPlayerEligible(GetOwningPlayer(runner)) then
            call BrowserPeachOrder(runner)
        endif
        set index = index + 1
    endloop
endfunction

function BrowserPeachBots takes nothing returns nothing
    if browserPeachTimer == null then
        set browserPeachTimer = CreateTimer()
        call TimerStart(browserPeachTimer, 0.75, true, function BrowserPeachTick)
    endif
endfunction
