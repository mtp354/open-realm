#ifdef BZ_TESTS
#include "test.h"
#include "../g_local.h"
#include "jass/jass.h"

bool run_test_jass(cstring_t src);
void setup_test_world(void);

static cstring_t peach_bots_cvar(cstring_t name, cstring_t fallback) {
    return !strcmp(name, "wc3_browser_bots") ? "1" : fallback;
}

static edict_t *peach_test_runner(uint32_t owner) {
    FILTER_EDICTS(unit, unit->inuse && unit->class_id == MAKEFOURCC('H','0','0','0') && unit->s.player == owner) return unit;
    return NULL;
}

static bool peach_bots_fixture(void) {
    static UnitWeapons_t const weapons = { .attacksEnabled = 1 };
    setup_test_world();
    strlcpy(level.map_path, "Maps/Download/peach.w3x", sizeof(level.map_path));
    gi.CvarString = peach_bots_cvar;
    FOR_LOOP(i, 7) {
        ((mapInfo_t *)level.mapinfo)->players[i].used = true;
        ((mapInfo_t *)level.mapinfo)->players[i].playerType = kPlayerTypeHuman;
        game.clients[i].connected = i == 0 || i == 2;
    }
    if (!run_test_jass(
        "globals\n"
        "  unit array udg_Unit_identifier_for_player_X\n"
        "  boolean array udg_Players_In_Jail\n"
        "  group udg_Main_Player_Units = null\n"
        "  unit udg_flag_1 = null\n"
        "  unit udg_flag_2 = null\n"
        "  integer udg_Number_Jailed_Team_1 = 0\n"
        "  integer udg_Number_Jailed_Team_2 = 0\n"
        "  integer peachPointOrders = 0\n"
        "  rect gg_rct_Team_1_side = null\n"
        "  rect gg_rct_Team_2_side = null\n"
        "  rect gg_rct_Team_1_Jail = null\n"
        "  rect gg_rct_Team_2_Jail = null\n"
        "endglobals\n"
        "function countPeachPointOrder takes nothing returns nothing\n"
        "  set peachPointOrders = peachPointOrders + 1\n"
        "endfunction\n"
        "function main takes nothing returns nothing\n"
        "  local integer i = 0\n"
        "  local integer ally = 0\n"
        "  local trigger orders = CreateTrigger()\n"
        "  call TriggerRegisterPlayerUnitEvent(orders, Player(1), EVENT_PLAYER_UNIT_ISSUED_POINT_ORDER, null)\n"
        "  call TriggerAddAction(orders, function countPeachPointOrder)\n"
        "  set udg_Main_Player_Units = CreateGroup()\n"
        "  set gg_rct_Team_1_side = Rect(-200.0, 20.0, 200.0, 200.0)\n"
        "  set gg_rct_Team_2_side = Rect(-200.0, -200.0, 200.0, -20.0)\n"
        "  set gg_rct_Team_1_Jail = Rect(100.0, 100.0, 140.0, 140.0)\n"
        "  set gg_rct_Team_2_Jail = Rect(100.0, -140.0, 140.0, -100.0)\n"
        "  set udg_flag_1 = CreateUnit(Player(14), 'hfoo', 80.0, 160.0, 0.0)\n"
        "  set udg_flag_2 = CreateUnit(Player(15), 'hfoo', 80.0, -160.0, 0.0)\n"
        "  loop\n"
        "    exitwhen i >= 7\n"
        "    set udg_Unit_identifier_for_player_X[i + 1] = CreateUnit(Player(i), 'Hpal', I2R(i) * 40.0 - 120.0, 80.0, 0.0)\n"
        "    call GroupAddUnit(udg_Main_Player_Units, udg_Unit_identifier_for_player_X[i + 1])\n"
        "    set ally = 0\n"
        "    loop\n"
        "      exitwhen i >= 6 or ally >= 6\n"
        "      call SetPlayerAlliance(Player(i), Player(ally), ALLIANCE_PASSIVE, true)\n"
        "      set ally = ally + 1\n"
        "    endloop\n"
        "    set i = i + 1\n"
        "  endloop\n"
        "  call SetPlayerAlliance(Player(6), Player(0), ALLIANCE_PASSIVE, false)\n"
        "  call SetUnitPosition(udg_Unit_identifier_for_player_X[7], -40.0, -80.0)\n"
        "  set udg_Players_In_Jail[5] = true\n"
        "endfunction\n"
        "function jailTeamOne takes nothing returns nothing\n"
        "  set udg_Number_Jailed_Team_1 = 1\n"
        "endfunction\n")) return false;
    /* H000 is a map-derived Hero. Keep the stock fixture's movement/inventory profile. */
    FILTER_EDICTS(unit, unit->inuse && unit->class_id == MAKEFOURCC('H','p','a','l')) {
        unit->class_id = MAKEFOURCC('H','0','0','0');
        /* The minimal MPQ omits UnitWeapons.slk; supply the runner's ordinary attack profile. */
        unit->data.UnitWeapons = &weapons;
        unit->attack1.type = ATK_NORMAL;
        unit->attack1.targetsAllowed = WC3_TARGET_FLAG_GROUND;
        unit->attack1.range = 100.0f;
        unit->attack1.cooldown = 1.0f;
        unit->attack1.damageBase = 10.0f;
        unit->targtype = TARG_GROUND;
    }
    if (!peach_test_runner(1) || !peach_test_runner(6)) return false;
    peach_test_runner(3)->paused = true;
    game.clients[5].jass.removed = true;
    return jass_dofile(level.vm, "warcraft-3\\Scripts\\BrowserPeach.j");
}

static void peach_tick(void) {
    jass_callbyname(level.vm, "BrowserPeachTick", false);
    G_RunEvents();
    jass_runevents(level.vm);
    T_ASSERT(!jass_rterror_pending(level.vm));
}

TEST(wc3_browser_peach, progressing_moves_persist_and_stalled_moves_retry_after_delay) {
    cstring_t (*old_cvar)(cstring_t, cstring_t) = gi.CvarString;
    bool ready = peach_bots_fixture();
    T_ASSERT(ready);
    if (ready) {
        char check[] = "function checkPeachOrders takes nothing returns nothing\n"
                       "  call BJassAssert(peachPointOrders == 1, \"moving runner was repeatedly reordered\")\n"
                       "endfunction\n"
                       "function checkPeachRetry takes nothing returns nothing\n"
                       "  call BJassAssert(peachPointOrders == 2, \"stalled runner was never retried\")\n"
                       "endfunction\n";
        jass_dobuffer(level.vm, check);
        peach_tick(); jass_runevents(level.vm);
        peach_test_runner(1)->s.origin2.x += 12;
        peach_tick(); jass_runevents(level.vm);
        jass_callbyname(level.vm, "checkPeachOrders", false);
        T_ASSERT(!jass_rterror_pending(level.vm));
        FOR_LOOP(i, 4) { peach_tick(); jass_runevents(level.vm); }
        jass_callbyname(level.vm, "checkPeachRetry", false);
        T_ASSERT(!jass_rterror_pending(level.vm));
    }
    gi.CvarString = old_cvar;
}

TEST(wc3_browser_peach, one_rescuer_and_separate_raiding_lanes) {
    cstring_t (*old_cvar)(cstring_t, cstring_t) = gi.CvarString;
    bool ready = peach_bots_fixture();
    vec2_t rescue = {0}, raid_a = {0}, raid_b = {0};
    T_ASSERT(ready);
    if (ready) {
        game.clients[2].connected = false;
        peach_test_runner(3)->paused = false;
        game.clients[5].jass.removed = false;
        jass_callbyname(level.vm, "jailTeamOne", false);
        peach_tick();
        T_ASSERT(G_GetIssuedOrderPoint(peach_test_runner(1), &rescue));
        T_ASSERT(G_GetIssuedOrderPoint(peach_test_runner(3), &raid_a));
        T_ASSERT(G_GetIssuedOrderPoint(peach_test_runner(5), &raid_b));
        T_FEQ(rescue.x, 120, .001f); T_FEQ(rescue.y, -120, .001f);
        T_ASSERT(raid_a.x != rescue.x || raid_a.y != rescue.y);
        T_FEQ(raid_a.y, raid_b.y, .001f);
        T_ASSERT(raid_a.x != raid_b.x);
    }
    gi.CvarString = old_cvar;
}

static void peach_goal(edict_t *runner, float x, float y) {
    vec2_t requested = { 0 };
    T_NOT_NULL(runner);
    if (!runner) return;
    T_EQ(G_GetIssuedOrderId(runner), G_OrderId("move"));
    T_NOT_NULL(runner->goalentity);
    /* Move may snap an occupied flag position to a pathable cell. Check the authored order point. */
    T_ASSERT(G_GetIssuedOrderPoint(runner, &requested));
    T_FEQ(requested.x, x, 0.001f);
    T_FEQ(requested.y, y, 0.001f);
}

TEST(wc3_browser_peach, timer_orders_both_teams_and_skips_humans_paused_jailed_removed) {
    cstring_t (*old_cvar)(cstring_t, cstring_t) = gi.CvarString;
    uint32_t untouched[5], owners[] = { 0, 2, 3, 4, 5 };
    bool ready = peach_bots_fixture();
    T_ASSERT(ready);
    if (!ready) { gi.CvarString = old_cvar; return; }
    FOR_LOOP(i, 5) untouched[i] = G_GetIssuedOrderId(peach_test_runner(owners[i]));
    jass_callbyname(level.vm, "BrowserPeachBots", false);
    jass_callbyname(level.vm, "BrowserPeachBots", false);
    T_EQ(level.num_timers, 1);
    FOR_LOOP(i, 8) { G_RunTimers(); jass_runevents(level.vm); }
    T_ASSERT(!jass_rterror_pending(level.vm));
    peach_goal(peach_test_runner(1), 80.0f, -160.0f);
    peach_goal(peach_test_runner(6), 80.0f, 160.0f);
    FOR_LOOP(i, 5) T_EQ(G_GetIssuedOrderId(peach_test_runner(owners[i])), untouched[i]);
    gi.CvarString = old_cvar;
}

TEST(wc3_browser_peach, jailed_teammate_rescue_and_flag_carrier_home_use_authored_rectangles) {
    cstring_t (*old_cvar)(cstring_t, cstring_t) = gi.CvarString;
    edict_t *runner, *flag_item = NULL;
    char flag_script[] = "function giveFlag takes nothing returns nothing\n"
                         "  call CreateItem('ratf', 0.0, 0.0)\n"
                         "endfunction\n";
    bool ready = peach_bots_fixture();
    T_ASSERT(ready);
    if (!ready) { gi.CvarString = old_cvar; return; }
    runner = peach_test_runner(1);
    jass_callbyname(level.vm, "jailTeamOne", false);
    peach_tick();
    peach_goal(runner, 120.0f, -120.0f);
    jass_dobuffer(level.vm, flag_script);
    jass_callbyname(level.vm, "giveFlag", false);
    FILTER_EDICTS(item, item->inuse && G_IsItem(item)) { flag_item = item; break; }
    T_NOT_NULL(flag_item);
    if (flag_item) {
        flag_item->class_id = MAKEFOURCC('I','0','0','0');
        T_ASSERT(G_AddItemToSlotInternal(runner, flag_item, 0, false));
        peach_tick();
        peach_goal(runner, 0.0f, 110.0f);
    }
    gi.CvarString = old_cvar;
}

TEST(wc3_browser_peach, defending_runner_tags_nearby_enemy_with_ordinary_attack_order) {
    cstring_t (*old_cvar)(cstring_t, cstring_t) = gi.CvarString;
    edict_t *runner, *enemy, *replacement;
    bool ready = peach_bots_fixture();
    T_ASSERT(ready);
    if (!ready) { gi.CvarString = old_cvar; return; }
    runner = peach_test_runner(1); enemy = peach_test_runner(2);
    G_SetPlayerAlliance(&game.clients[1].ps, &game.clients[2].ps, ALLIANCE_PASSIVE, false);
    runner->s.origin2 = (vec2_t){ 0.0f, 80.0f };
    enemy->s.origin2 = (vec2_t){ 60.0f, 80.0f };
    gi.LinkEntity(runner); gi.LinkEntity(enemy);
    T_ASSERT(S_AttackCanTarget(runner, enemy));
    peach_tick();
    T_EQ(G_GetIssuedOrderId(runner), G_OrderId("attack"));
    T_EQ(runner->goalentity, enemy);
    T_EQ(G_GetIssuedOrderId(enemy), 0);
    /* The order ID can remain attack after its old victim dies; issue a fresh target. */
    G_SetHealth(enemy, 0);
    replacement = peach_test_runner(3);
    game.clients[3].connected = true;
    replacement->paused = false;
    replacement->s.origin2 = (vec2_t){ 80.0f, 80.0f };
    gi.LinkEntity(replacement);
    G_SetPlayerAlliance(&game.clients[1].ps, &game.clients[3].ps, ALLIANCE_PASSIVE, false);
    peach_tick();
    T_EQ(runner->goalentity, replacement);
    replacement->s.renderfx |= RF_HIDDEN;
    peach_tick();
    peach_goal(runner, 80.0f, -160.0f);
    replacement->s.renderfx &= ~RF_HIDDEN;
    G_FowInit();
    G_FowSetStateRadius(&(fogWrite_t){ .player = 1, .state = WC3_FOG_STATE_MASKED },
                        &replacement->s.origin2, 128.0f);
    peach_tick();
    peach_goal(runner, 80.0f, -160.0f);
    G_FowShutdown();
    gi.CvarString = old_cvar;
}
#endif
