#ifdef BZ_TESTS
#include "test.h"
#include "../g_local.h"
#include "jass/jass.h"

bool run_test_jass(cstring_t src);
void setup_test_world(void);

static bool browser_bots_enabled;
static cstring_t (*browser_bots_old_cvar)(cstring_t, cstring_t);
static cstring_t browser_bots_cvar(cstring_t name, cstring_t fallback) {
    return !strcmp(name, "wc3_browser_bots") ? (browser_bots_enabled ? "1" : "0") :
        browser_bots_old_cvar(name, fallback);
}

static void browser_bots_setup(void) {
    setup_test_world();
    strlcpy(level.map_path, "Maps/Download/peach.w3x", sizeof(level.map_path));
    mapPlayer_t *slot = ((mapInfo_t *)level.mapinfo)->players + 1;
    slot->used = true;
    slot->playerType = kPlayerTypeHuman;
    browser_bots_old_cvar = gi.CvarString;
    gi.CvarString = browser_bots_cvar;
    browser_bots_enabled = true;
}

TEST(wc3_browser_bots, ownership_is_opt_in_and_never_takes_connected_or_finished_slots) {
    browser_bots_setup();
    T_ASSERT(G_BrowserBotPlayerEligible(1));
    T_ASSERT(!G_BrowserBotPlayerEligible(0));
    T_ASSERT(!G_BrowserBotPlayerEligible(2));
    T_ASSERT(!G_BrowserBotPlayerEligible(12));
    browser_bots_enabled = false;
    T_ASSERT(!G_BrowserBotPlayerEligible(1));
    browser_bots_enabled = true;
    game.clients[1].connected = true;
    T_ASSERT(!G_BrowserBotPlayerEligible(1));
    game.clients[1].connected = false;
    game.clients[1].jass.removed = true;
    T_ASSERT(!G_BrowserBotPlayerEligible(1));
    game.clients[1].jass.removed = false;
    strlcpy(level.map_path, "Maps\\Download\\APRICOT.w3x", sizeof(level.map_path));
    T_ASSERT(G_BrowserBotPlayerEligible(1));
    strlcpy(level.map_path, "Maps/Download/peach.w3x.extra", sizeof(level.map_path));
    T_ASSERT(!G_BrowserBotPlayerEligible(1));
    gi.CvarString = browser_bots_old_cvar;
}

TEST(wc3_browser_bots, bots_consume_real_sight_without_becoming_network_clients) {
    browser_bots_setup();
    G_FowInit();
    T_ASSERT(run_test_jass(
        "native BrowserBotPlayerEligible takes player whichPlayer returns boolean\n"
        "globals\n"
        "  unit observed = null\n"
        "endglobals\n"
        "function verify takes nothing returns nothing\n"
        "  call BJassAssert(IsUnitVisible(observed, Player(1)), \"bot grid was not updated\")\n"
        "  call BJassAssert(BrowserBotPlayerEligible(Player(1)), \"bot native rejected slot\")\n"
        "  call BJassAssert(not BrowserBotPlayerEligible(null), \"bot native accepted null\")\n"
        "endfunction\n"
        "function main takes nothing returns nothing\n"
        "  call CreateUnit(Player(1), 'hfoo', 192.0, 192.0, 0.0)\n"
        "  set observed = CreateUnit(Player(2), 'hfoo', 224.0, 192.0, 0.0)\n"
        "endfunction\n"));
    /* Fixture UnitBalance rows omit sight; give this ordinary unit a sight
     * radius so the test measures viewer consumption, not missing test data. */
    FOR_LOOP(i, globals.num_edicts)
        if (g_edicts[i].inuse && g_edicts[i].class_id == MAKEFOURCC('h','f','o','o') &&
            g_edicts[i].s.player == 1)
            g_edicts[i].runtime.sight_radius.day = g_edicts[i].runtime.sight_radius.night = 128.0f;
    G_FowUpdate();
    jass_callbyname(level.vm, "verify", false);
    T_ASSERT(!jass_rterror_pending(level.vm));
    T_ASSERT(!game.clients[1].connected);
    T_ASSERT(!level.fow.players[1].client_connected);
    edict_t *observed = NULL;
    FOR_LOOP(i, globals.num_edicts)
        if (g_edicts[i].inuse && g_edicts[i].class_id == MAKEFOURCC('h','f','o','o') &&
            g_edicts[i].s.player == 2) observed = g_edicts + i;
    T_ASSERT(observed && G_FowPlayerCanHoverEntity(1, observed));
    G_FowShutdown();
    gi.CvarString = browser_bots_old_cvar;
}

TEST(wc3_browser_bots, visibility_native_observes_current_sight_and_hidden_units) {
    setup_test_world();
    G_FowInit();
    T_ASSERT(run_test_jass(
        "function main takes nothing returns nothing\n"
        "  local unit u = CreateUnit(Player(1), 'hfoo', 192.0, 192.0, 0.0)\n"
        "  call FogEnable(true)\n"
        "  call FogMaskEnable(true)\n"
        "  call SetFogStateRadius(Player(0), FOG_OF_WAR_MASKED, 192.0, 192.0, 128.0, false)\n"
        "  call BJassAssert(not IsUnitVisible(u, Player(0)), \"unseen enemy is visible\")\n"
        "  call SetFogStateRadius(Player(0), FOG_OF_WAR_VISIBLE, 192.0, 192.0, 128.0, false)\n"
        "  call BJassAssert(IsUnitVisible(u, Player(0)), \"visible enemy is hidden\")\n"
        "  call ShowUnit(u, false)\n"
        "  call BJassAssert(not IsUnitVisible(u, Player(0)), \"hidden unit is visible\")\n"
        "  call BJassAssert(not IsUnitVisible(null, Player(0)) and not IsUnitVisible(u, null), \"null visibility accepted\")\n"
        "endfunction\n"));
    G_FowShutdown();
}
#endif
