#ifdef BZ_TESTS
#include "test.h"
#include "../g_local.h"
#include "jass/jass.h"

void setup_test_world(void);
edict_t *alloc_test_unit(uint32_t class_id, float x, float y);
bool run_test_jass(cstring_t source);
static void G_RunFrame(void);

static cstring_t (*apricot_bot_saved_cvar)(cstring_t, cstring_t);
static cstring_t apricot_bot_cvar(cstring_t name, cstring_t fallback) {
    return !strcmp(name, "wc3_browser_bots") ? "1" : apricot_bot_saved_cvar(name, fallback);
}

static void apricot_bot_test_world(void) {
    setup_test_world();
    strlcpy(level.map_path, "Maps/Download/apricot.w3x", sizeof(level.map_path));
    FOR_LOOP(i, 12) {
        mapPlayer_t *slot = ((mapInfo_t *)level.mapinfo)->players + i;
        slot->used = true;
        slot->playerType = kPlayerTypeHuman;
        game.clients[i].mapplayer = slot;
        game.clients[i].ps.number = i;
    }
    G_InitPlayerAlliances(level.mapinfo);
    apricot_bot_saved_cvar = gi.CvarString;
    gi.CvarString = apricot_bot_cvar;
}

static edict_t *apricot_bot_test_unit(uint32_t owner, uint32_t type, float x, float y) {
    edict_t *unit = alloc_test_unit(MAKEFOURCC('h','f','o','o'), x, y);
    unit->class_id = type;
    unit->s.player = owner;
    unit->svflags |= SVF_MONSTER;
    unit->movetype = MOVETYPE_STEP;
    unit->unitinfo.MoveSpeed = 300;
    unit->runtime.acquisition_range = 0;
    unit->health.value = unit->health.max_value = 500;
    unit->attack1.damageBase = 5;
    unit->attack1.range = 32;
    unit->attack1.type = ATK_NORMAL;
    unit->attack1.cooldown = 1;
    unit->attack1.targetsAllowed = WC3_TARGET_FLAG_GROUND | WC3_TARGET_FLAG_STRUCTURE;
    unit->targtype = TARG_GROUND;
    unit->stand = unit_stand;
    unit_stand(unit);
    gi.LinkEntity(unit);
    return unit;
}

static bool apricot_bot_start_policy(void) {
    if (!run_test_jass(
        "type unitstate extends handle\n"
        "native ConvertUnitState takes integer i returns unitstate\n"
        "globals\n"
        // The deliberately small test common.j omits these retail constants.
        "constant playerslotstate PLAYER_SLOT_STATE_PLAYING = ConvertPlayerSlotState(1)\n"
        "constant unitstate UNIT_STATE_MAX_LIFE = ConvertUnitState(1)\n"
        "rect gg_rct_NW_Corner = null\nrect gg_rct_NE_Corner = null\n"
        "rect gg_rct_SW_Corner = null\nrect gg_rct_SE_Corner = null\n"
        "rect gg_rct_Full_map = null\nendglobals\n"
        "function main takes nothing returns nothing\n"
        "call FogEnable(false)\ncall FogMaskEnable(false)\n"
        "set gg_rct_NW_Corner = Rect(-640.0, 560.0, -560.0, 640.0)\n"
        "set gg_rct_NE_Corner = Rect(560.0, 560.0, 640.0, 640.0)\n"
        "set gg_rct_SW_Corner = Rect(-640.0, -640.0, -560.0, -560.0)\n"
        "set gg_rct_SE_Corner = Rect(560.0, -640.0, 640.0, -560.0)\n"
        "set gg_rct_Full_map = Rect(-1024.0, -1024.0, 1024.0, 1024.0)\n"
        "endfunction\n")) return false;
    G_LoadBrowserBots();
    if (!jass_functionbyname(level.vm, "BrowserApricotBots")) return false;
    level.started = level.scriptsStarted = true;
    G_StartBrowserBots();
    jass_runevents(level.vm);
    return !jass_rterror_pending(level.vm);
}

TEST(wc3_browser_bots, apricot_sidecar_routes_builders_and_attacks_with_normal_orders) {
    vec2_t destination;
    apricot_bot_test_world();
    edict_t *local = apricot_bot_test_unit(0, MAKEFOURCC('O','0','0','0'), -700, -700);
    edict_t *zombie = apricot_bot_test_unit(1, MAKEFOURCC('O','0','0','0'), -700, -600);
    edict_t *builder = apricot_bot_test_unit(3, MAKEFOURCC('h','0','0','Q'), 0, 0);
    edict_t *connected = apricot_bot_test_unit(4, MAKEFOURCC('h','0','0','Q'), 100, 0);
    edict_t *paused = apricot_bot_test_unit(5, MAKEFOURCC('h','0','0','Q'), 0, 100);
    edict_t *removed = apricot_bot_test_unit(6, MAKEFOURCC('h','0','0','Q'), 0, 200);
    uint32_t const local_order = G_GetIssuedOrderId(local), connected_order = G_GetIssuedOrderId(connected);
    uint32_t const paused_order = G_GetIssuedOrderId(paused), removed_order = G_GetIssuedOrderId(removed);
    game.clients[0].connected = game.clients[4].connected = true;
    game.clients[6].jass.removed = true;
    paused->paused = true;
    game.clients[3].ps.stats[PLAYERSTATE_RESOURCE_GOLD] = 17;
    game.clients[3].ps.stats[PLAYERSTATE_RESOURCE_LUMBER] = 100;
    T_ASSERT(apricot_bot_start_policy());
    T_EQ(G_GetIssuedOrderId(builder), G_OrderId("move"));
    T_ASSERT(G_GetIssuedOrderPoint(builder, &destination));
    T_FEQ(destination.x, -792, 0.01f);
    T_FEQ(destination.y, 600, 0.01f);
    T_EQ(G_GetIssuedOrderId(zombie), G_OrderId("attack"));
    T_ASSERT(zombie->goalentity == builder);
    T_EQ(G_GetIssuedOrderId(local), local_order);
    T_EQ(G_GetIssuedOrderId(connected), connected_order);
    T_EQ(G_GetIssuedOrderId(paused), paused_order);
    T_EQ(G_GetIssuedOrderId(removed), removed_order);
    T_EQ(game.clients[3].ps.stats[PLAYERSTATE_RESOURCE_GOLD], 17);
    T_EQ(game.clients[3].ps.stats[PLAYERSTATE_RESOURCE_LUMBER], 100);
    gi.CvarString = apricot_bot_saved_cvar;
}

TEST(wc3_browser_bots, apricot_coroutine_rechecks_connections_pause_and_results) {
    apricot_bot_test_world();
    edict_t *first = apricot_bot_test_unit(3, MAKEFOURCC('h','0','0','Q'), 0, 0);
    edict_t *second = apricot_bot_test_unit(4, MAKEFOURCC('h','0','0','Q'), 100, 0);
    edict_t *third = apricot_bot_test_unit(5, MAKEFOURCC('h','0','0','Q'), 0, 100);
    game.clients[4].connected = true;
    T_ASSERT(apricot_bot_start_policy());
    T_EQ(G_GetIssuedOrderId(first), G_OrderId("move"));
    T_ASSERT(unit_issueimmediateorder(first, "stop"));
    T_ASSERT(unit_issueimmediateorder(third, "stop"));
    game.clients[3].connected = true;
    game.clients[4].connected = false;
    third->paused = true;
    level.time = 2100;
    G_RunFrame();
    T_ASSERT(!jass_rterror_pending(level.vm));
    T_EQ(G_GetIssuedOrderId(first), G_OrderId("stop"));
    T_EQ(G_GetIssuedOrderId(second), G_OrderId("move"));
    T_EQ(G_GetIssuedOrderId(third), G_OrderId("stop"));
    T_ASSERT(unit_issueimmediateorder(second, "stop"));
    game.clients[4].jass.removed = true;
    third->paused = false;
    level.time = 4200;
    G_RunFrame();
    T_ASSERT(!jass_rterror_pending(level.vm));
    T_EQ(G_GetIssuedOrderId(second), G_OrderId("stop"));
    T_EQ(G_GetIssuedOrderId(third), G_OrderId("move"));
    gi.CvarString = apricot_bot_saved_cvar;
}
#endif
