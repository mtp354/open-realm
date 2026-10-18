// Companion policy for the authored CTF rules. Only ordinary unit orders;
// map triggers own pickups, tags, jail, round transitions and scoring.
native BrowserBotPlayerEligible takes player whichPlayer returns boolean

globals
    timer browserPeachTimer = null
    unit array browserPeachDefenseTarget
    unit array browserPeachRunner
    real array browserPeachGoalX
    real array browserPeachGoalY
    real array browserPeachLastX
    real array browserPeachLastY
    integer array browserPeachStalled
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

function BrowserPeachAvailable takes integer index returns boolean
    local unit runner = udg_Unit_identifier_for_player_X[index]
    return runner != null and GetUnitTypeId(runner) == 'H000' and GetWidgetLife(runner) > 0.0 and not IsUnitPaused(runner) and not IsUnitHidden(runner) and not udg_Players_In_Jail[index] and IsUnitInGroup(runner, udg_Main_Player_Units) and BrowserBotPlayerEligible(GetOwningPlayer(runner))
endfunction

function BrowserPeachMove takes unit runner, real x, real y returns nothing
    local integer id = GetPlayerId(GetOwningPlayer(runner))
    local real dx = GetUnitX(runner) - browserPeachLastX[id]
    local real dy = GetUnitY(runner) - browserPeachLastY[id]
    local real gx = x - browserPeachGoalX[id]
    local real gy = y - browserPeachGoalY[id]
    local boolean same = browserPeachRunner[id] == runner and gx * gx + gy * gy < 1024.0 and browserPeachDefenseTarget[id] == null
    set browserPeachLastX[id] = GetUnitX(runner)
    set browserPeachLastY[id] = GetUnitY(runner)
    if same then
        if dx * dx + dy * dy >= 64.0 then
            set browserPeachStalled[id] = 0
        else
            set browserPeachStalled[id] = browserPeachStalled[id] + 1
        endif
        set gx = GetUnitX(runner) - x
        set gy = GetUnitY(runner) - y
        if gx * gx + gy * gy < 4096.0 then
            return
        endif
        // A persistent order ID alone does not prove that its path is active.
        if GetUnitCurrentOrder(runner) == OrderId("move") and browserPeachStalled[id] < 4 then
            return
        endif
    endif
    set browserPeachRunner[id] = runner
    set browserPeachDefenseTarget[id] = null
    set browserPeachGoalX[id] = x
    set browserPeachGoalY[id] = y
    set browserPeachStalled[id] = 0
    call IssuePointOrder(runner, "move", x, y)
endfunction

function BrowserPeachOrder takes unit runner returns nothing
    local player owner = GetOwningPlayer(runner)
    local integer id = GetPlayerId(owner)
    local boolean teamOne = IsPlayerAlly(owner, Player(0))
    local rect home = gg_rct_Team_2_side
    local rect away = gg_rct_Team_1_side
    local rect jail = gg_rct_Team_1_Jail
    local unit flag = udg_flag_1
    local unit ownFlag = udg_flag_2
    local integer flagItem = 'I001'
    local integer jailed = udg_Number_Jailed_Team_2
    local unit candidate = null
    local unit closest = null
    local unit rescuer = null
    local unit defender = null
    local unit carrier = null
    local integer count = 0
    local integer index = 1
    local real distance = 25600.0
    local real dx = 0.0
    local real dy = 0.0
    local real mid = 0.0
    local real lane = 0.0
    local real direction = 1.0
    if teamOne then
        set home = gg_rct_Team_1_side
        set away = gg_rct_Team_2_side
        set jail = gg_rct_Team_2_Jail
        set flag = udg_flag_2
        set ownFlag = udg_flag_1
        set flagItem = 'I000'
        set jailed = udg_Number_Jailed_Team_1
        set direction = -1.0
    endif
    if home == null or away == null then
        return
    endif
    if BrowserPeachCarries(runner, flagItem) then
        call BrowserPeachMove(runner, GetRectCenterX(home), GetRectCenterY(home))
        return
    endif
    // Elect jobs from the live roster. Human and jailed runners never take a job.
    loop
        exitwhen index > 12
        set candidate = udg_Unit_identifier_for_player_X[index]
        if candidate != null and IsPlayerAlly(GetOwningPlayer(candidate), Player(0)) == teamOne then
            if BrowserPeachCarries(candidate, flagItem) then
                set carrier = candidate
            elseif BrowserPeachAvailable(index) then
                if count == 0 then
                    set rescuer = candidate
                elseif count == 1 then
                    set defender = candidate
                endif
                set count = count + 1
            endif
        endif
        set index = index + 1
    endloop
    if jailed > 0 and runner == rescuer and jail != null then
        call BrowserPeachMove(runner, GetRectCenterX(jail), GetRectCenterY(jail))
        return
    endif
    if count >= 3 and runner == defender then
        set distance = 262144.0
    endif
    // Raiders only interrupt for an immediate tag. One defender covers a wider radius.
    if BrowserPeachInside(runner, home) then
        set index = 1
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
            if GetUnitCurrentOrder(runner) == OrderId("attack") and browserPeachDefenseTarget[id] == closest then
                return
            endif
            if IssueTargetOrder(runner, "attack", closest) then
                set browserPeachDefenseTarget[id] = closest
                return
            endif
        endif
    endif
    if count >= 3 and runner == defender and ownFlag != null then
        call BrowserPeachMove(runner, GetUnitX(ownFlag), GetUnitY(ownFlag) + direction * 350.0)
    elseif carrier != null and carrier != runner then
        call BrowserPeachMove(runner, GetUnitX(carrier) + I2R(id - (id / 3) * 3 - 1) * 128.0, GetUnitY(carrier) - direction * 128.0)
    elseif flag != null and GetWidgetLife(flag) > 0.0 and not IsUnitHidden(flag) then
        set mid = (GetRectCenterY(home) + GetRectCenterY(away)) * 0.5
        if count > 1 and (GetUnitY(runner) - mid) * direction < 0.0 then
            set lane = (GetRectMaxX(home) - GetRectMinX(home)) * 0.18
            if lane > 512.0 then
                set lane = 512.0
            endif
            call BrowserPeachMove(runner, GetRectCenterX(home) + I2R(id - (id / 3) * 3 - 1) * lane, mid + direction * 128.0)
        else
            call BrowserPeachMove(runner, GetUnitX(flag), GetUnitY(flag))
        endif
    else
        call BrowserPeachMove(runner, GetRectCenterX(home), GetRectCenterY(home))
    endif
endfunction

function BrowserPeachTick takes nothing returns nothing
    local integer index = 1
    loop
        exitwhen index > 12
        if BrowserPeachAvailable(index) then
            call BrowserPeachOrder(udg_Unit_identifier_for_player_X[index])
        else
            // Respawns, tutorial pauses and round teleports need a fresh path.
            set browserPeachRunner[index - 1] = null
            set browserPeachDefenseTarget[index - 1] = null
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
