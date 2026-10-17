// Original, opt-in orders for otherwise unattended Apricot player slots.
// The original map owns spawning, resources, alliances and victory/defeat.
native BrowserBotPlayerEligible takes player whichPlayer returns boolean

globals
    group BrowserApricotScan = null
    group BrowserApricotActors = null
    group BrowserApricotHumans = null
    group BrowserApricotZombies = null
    unit BrowserApricotSeeker = null
    unit BrowserApricotNearest = null
    real BrowserApricotNearestDistance = 0.0
    real array BrowserApricotHomeX
    real array BrowserApricotHomeY
    integer array BrowserApricotHomes
    integer array BrowserApricotTowers
    integer array BrowserApricotBuildSpot
    integer array BrowserApricotBuildAfter
    integer array BrowserApricotPatrol
    integer BrowserApricotTick = 0
    integer BrowserApricotMoveOrder = 0
    integer BrowserApricotAttackOrder = 0
    boolean BrowserApricotRunning = false
endglobals

function BrowserApricotModulo takes integer value, integer divisor returns integer
    return value - (value/divisor)*divisor
endfunction

function BrowserApricotClamp takes real value, real low, real high returns real
    if value < low then
        return low
    elseif value > high then
        return high
    endif
    return value
endfunction

function BrowserApricotCorner takes integer index returns rect
    if index == 0 then
        return gg_rct_NW_Corner
    elseif index == 1 then
        return gg_rct_NE_Corner
    elseif index == 2 then
        return gg_rct_SW_Corner
    endif
    return gg_rct_SE_Corner
endfunction

function BrowserApricotDistance takes unit a, unit b returns real
    local real dx = GetUnitX(a) - GetUnitX(b)
    local real dy = GetUnitY(a) - GetUnitY(b)
    return dx*dx + dy*dy
endfunction

function BrowserApricotAlive takes unit whichUnit returns boolean
    return whichUnit != null and GetUnitTypeId(whichUnit) != 0 and GetWidgetLife(whichUnit) > 0.405 and not IsUnitPaused(whichUnit)
endfunction

function BrowserApricotPickNearest takes nothing returns nothing
    local unit candidate = GetEnumUnit()
    local real distance
    if BrowserApricotAlive(candidate) and IsUnitEnemy(candidate, GetOwningPlayer(BrowserApricotSeeker)) and IsUnitVisible(candidate, GetOwningPlayer(BrowserApricotSeeker)) then
        set distance = BrowserApricotDistance(BrowserApricotSeeker, candidate)
        if distance < BrowserApricotNearestDistance then
            set BrowserApricotNearest = candidate
            set BrowserApricotNearestDistance = distance
        endif
    endif
    set candidate = null
endfunction

function BrowserApricotFindNearest takes unit seeker, group candidates, real range returns unit
    set BrowserApricotSeeker = seeker
    set BrowserApricotNearest = null
    set BrowserApricotNearestDistance = range*range
    call ForGroup(candidates, function BrowserApricotPickNearest)
    set BrowserApricotSeeker = null
    return BrowserApricotNearest
endfunction

function BrowserApricotCollect takes nothing returns nothing
    local integer slot = 0
    local unit whichUnit
    local integer kind
    call GroupClear(BrowserApricotActors)
    call GroupClear(BrowserApricotHumans)
    call GroupClear(BrowserApricotZombies)
    loop
        exitwhen slot >= 12
        set BrowserApricotHomes[slot] = 0
        set BrowserApricotTowers[slot] = 0
        call GroupClear(BrowserApricotScan)
        if GetPlayerSlotState(Player(slot)) == PLAYER_SLOT_STATE_PLAYING then
            call GroupEnumUnitsOfPlayer(BrowserApricotScan, Player(slot), null)
        endif
        loop
            set whichUnit = FirstOfGroup(BrowserApricotScan)
            exitwhen whichUnit == null
            call GroupRemoveUnit(BrowserApricotScan, whichUnit)
            if BrowserApricotAlive(whichUnit) then
                set kind = GetUnitTypeId(whichUnit)
                if slot >= 3 then
                    if kind == 'h00F' then
                        set BrowserApricotHomes[slot] = BrowserApricotHomes[slot] + 1
                    elseif kind == 'o004' then
                        set BrowserApricotTowers[slot] = BrowserApricotTowers[slot] + 1
                    elseif kind == 'h00Q' then
                        call GroupAddUnit(BrowserApricotHumans, whichUnit)
                    endif
                elseif not IsUnitType(whichUnit, UNIT_TYPE_STRUCTURE) and GetUnitDefaultMoveSpeed(whichUnit) > 0.0 then
                    call GroupAddUnit(BrowserApricotZombies, whichUnit)
                endif
                if slot > 0 and BrowserBotPlayerEligible(Player(slot)) and not IsUnitType(whichUnit, UNIT_TYPE_STRUCTURE) then
                    if slot <= 2 or kind == 'h00Q' then
                        call GroupAddUnit(BrowserApricotActors, whichUnit)
                    endif
                endif
            endif
        endloop
        set slot = slot + 1
    endloop
    set whichUnit = null
endfunction

function BrowserApricotOffsetX takes integer index returns real
    if index == 0 or index == 1 or index == 7 then
        return 384.0
    elseif index == 3 or index == 4 or index == 5 then
        return -384.0
    endif
    return 0.0
endfunction

function BrowserApricotOffsetY takes integer index returns real
    if index >= 1 and index <= 3 then
        return 384.0
    elseif index >= 5 and index <= 7 then
        return -384.0
    endif
    return 0.0
endfunction

function BrowserApricotFlee takes unit builder, unit enemy returns nothing
    local real dx = GetUnitX(builder) - GetUnitX(enemy)
    local real dy = GetUnitY(builder) - GetUnitY(enemy)
    local real distance = SquareRoot(dx*dx + dy*dy)
    local real x
    local real y
    if distance < 1.0 then
        set dx = 1.0
        set dy = 0.0
        set distance = 1.0
    endif
    set x = GetUnitX(builder) + dx*640.0/distance
    set y = GetUnitY(builder) + dy*640.0/distance
    set x = BrowserApricotClamp(x, GetRectMinX(gg_rct_Full_map)+96.0, GetRectMaxX(gg_rct_Full_map)-96.0)
    set y = BrowserApricotClamp(y, GetRectMinY(gg_rct_Full_map)+96.0, GetRectMaxY(gg_rct_Full_map)-96.0)
    call IssuePointOrder(builder, "move", x, y)
endfunction

function BrowserApricotHumanThink takes unit builder, integer slot returns nothing
    local unit enemy = BrowserApricotFindNearest(builder, BrowserApricotZombies, 550.0)
    local real dx = GetUnitX(builder) - BrowserApricotHomeX[slot]
    local real dy = GetUnitY(builder) - BrowserApricotHomeY[slot]
    local integer building
    local integer spot
    local boolean accepted
    if enemy != null then
        if BrowserApricotTowers[slot] > 0 and BrowserApricotDistance(builder, enemy) < 25600.0 and GetWidgetLife(builder) > GetUnitState(builder, UNIT_STATE_MAX_LIFE)*0.75 then
            if GetUnitCurrentOrder(builder) != BrowserApricotAttackOrder or BrowserApricotModulo(BrowserApricotTick, 5) == 0 then
                call IssueTargetOrder(builder, "attack", enemy)
            endif
        else
            call BrowserApricotFlee(builder, enemy)
        endif
        set enemy = null
        return
    endif
    if dx*dx + dy*dy > 102400.0 then
        if GetUnitCurrentOrder(builder) != BrowserApricotMoveOrder or BrowserApricotModulo(BrowserApricotTick, 5) == 0 then
            call IssuePointOrder(builder, "move", BrowserApricotHomeX[slot], BrowserApricotHomeY[slot])
        endif
        return
    endif
    if BrowserApricotTick < BrowserApricotBuildAfter[slot] then
        return
    endif
    // h00Q's authored build list permits these. The normal build path checks
    // resources, prerequisites, placement and the builder's actual capability.
    if BrowserApricotHomes[slot] == 0 then
        set building = 'h00F'
    elseif BrowserApricotTowers[slot] < 3 then
        set building = 'o004'
    else
        return
    endif
    set spot = BrowserApricotModulo(BrowserApricotBuildSpot[slot], 8)
    set BrowserApricotBuildSpot[slot] = BrowserApricotBuildSpot[slot] + 1
    set accepted = IssueBuildOrderById(builder, building, BrowserApricotHomeX[slot] + BrowserApricotOffsetX(spot), BrowserApricotHomeY[slot] + BrowserApricotOffsetY(spot))
    if accepted then
        set BrowserApricotBuildAfter[slot] = BrowserApricotTick + 15
    else
        set BrowserApricotBuildAfter[slot] = BrowserApricotTick + 4
    endif
endfunction

function BrowserApricotZombieThink takes unit zombie, integer slot returns nothing
    local unit target = BrowserApricotFindNearest(zombie, BrowserApricotHumans, 2400.0)
    local rect destination
    local real dx
    local real dy
    if target != null then
        if GetUnitCurrentOrder(zombie) != BrowserApricotAttackOrder or BrowserApricotModulo(BrowserApricotTick, 5) == 0 then
            call IssueTargetOrder(zombie, "attack", target)
        endif
        set target = null
        return
    endif
    set destination = BrowserApricotCorner(BrowserApricotPatrol[slot])
    set dx = GetUnitX(zombie) - GetRectCenterX(destination)
    set dy = GetUnitY(zombie) - GetRectCenterY(destination)
    if dx*dx + dy*dy < 409600.0 then
        set BrowserApricotPatrol[slot] = BrowserApricotModulo(BrowserApricotPatrol[slot] + 1, 4)
        set destination = BrowserApricotCorner(BrowserApricotPatrol[slot])
        call IssuePointOrder(zombie, "attack", GetRectCenterX(destination), GetRectCenterY(destination))
    elseif GetUnitCurrentOrder(zombie) != BrowserApricotAttackOrder or BrowserApricotModulo(BrowserApricotTick, 15) == 0 then
        // Patrol authored corner regions; never target an unseen builder.
        call IssuePointOrder(zombie, "attack", GetRectCenterX(destination), GetRectCenterY(destination))
    endif
    set destination = null
endfunction

function BrowserApricotThinkUnit takes nothing returns nothing
    local unit whichUnit = GetEnumUnit()
    local integer slot = GetPlayerId(GetOwningPlayer(whichUnit))
    if BrowserApricotAlive(whichUnit) and BrowserBotPlayerEligible(Player(slot)) then
        if slot >= 3 then
            call BrowserApricotHumanThink(whichUnit, slot)
        elseif slot > 0 then
            call BrowserApricotZombieThink(whichUnit, slot)
        endif
    endif
    set whichUnit = null
endfunction

function BrowserApricotBots takes nothing returns nothing
    local integer slot = 1
    local integer corner
    local rect base
    if BrowserApricotRunning then
        return
    endif
    set BrowserApricotRunning = true
    set BrowserApricotScan = CreateGroup()
    set BrowserApricotActors = CreateGroup()
    set BrowserApricotHumans = CreateGroup()
    set BrowserApricotZombies = CreateGroup()
    set BrowserApricotMoveOrder = OrderId("move")
    set BrowserApricotAttackOrder = OrderId("attack")
    set BrowserApricotPatrol[1] = 0
    set BrowserApricotPatrol[2] = 3
    loop
        exitwhen slot >= 12
        if slot >= 3 then
            set corner = BrowserApricotModulo(slot - 3, 4)
            set base = BrowserApricotCorner(corner)
            set BrowserApricotHomeX[slot] = GetRectCenterX(base) + I2R((slot-3)/4 - 1)*192.0
            set BrowserApricotHomeY[slot] = GetRectCenterY(base)
        endif
        set slot = slot + 1
    endloop
    set base = null
    loop
        set BrowserApricotTick = BrowserApricotTick + 1
        call BrowserApricotCollect()
        call ForGroup(BrowserApricotActors, function BrowserApricotThinkUnit)
        call TriggerSleepAction(2.0)
    endloop
endfunction
