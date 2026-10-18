#include "g_local.h"
#include "jass/jass.h"

/* Standalone map presentation and controls share one exact-path profile.
 * Optional bot policies live in the map VM and use normal JASS orders. */
typedef struct {
    cstring_t map, script, entry;
    bool simple_hud, tree_smart_attack;
} browserMapProfile_t;

static browserMapProfile_t const profiles[] = {
    { "Maps/Download/apricot.w3x", "warcraft-3\\Scripts\\BrowserApricot.j", "BrowserApricotBots" },
    { "Maps/Download/peach.w3x", "warcraft-3\\Scripts\\BrowserPeach.j", "BrowserPeachBots", true, true },
};

static browserMapProfile_t const *G_BrowserMapProfile(void) {
    char path[sizeof(level.map_path)];
    strlcpy(path, level.map_path, sizeof(path));
    for (char *p = path; *p; ++p) if (*p == '\\') *p = '/';
    FOR_LOOP(i, sizeof(profiles) / sizeof(profiles[0]))
        if (!strcasecmp(path, profiles[i].map)) return profiles + i;
    return NULL;
}

bool G_BrowserMapUsesSimpleHud(void) {
    browserMapProfile_t const *policy = G_BrowserMapProfile();
    return policy && policy->simple_hud;
}

bool G_BrowserMapAllowsTreeSmartAttack(void) {
    browserMapProfile_t const *policy = G_BrowserMapProfile();
    return policy && policy->tree_smart_attack;
}

bool G_BrowserBotPlayerEligible(uint32_t player) {
    gameClient_t const *client;
    mapPlayer_t const *slot;
    if (!player || player >= 12 || player >= game.max_clients || !level.mapinfo ||
        !G_BrowserMapProfile() || !atoi(gi.CvarString("wc3_browser_bots", "0"))) return false;
    slot = level.mapinfo->players + player;
    client = G_GetPlayerClientByNumber(player);
    return slot->used && slot->playerType == kPlayerTypeHuman && client &&
        !client->connected && !client->jass.removed;
}

void G_LoadBrowserBots(void) {
    browserMapProfile_t const *policy = G_BrowserMapProfile();
    /* Declarations are deterministic even with bots disabled, so save program
     * identities do not depend on a launch cvar. No map bytes are rewritten. */
    if (policy && !jass_dofile(level.vm, policy->script))
        fprintf(stderr, "WC3 browser bots: could not load %s\n", policy->script);
}

void G_StartBrowserBots(void) {
    browserMapProfile_t const *policy = G_BrowserMapProfile();
    if (policy && atoi(gi.CvarString("wc3_browser_bots", "0")))
        jass_startcoroutinebyname(level.vm, policy->entry);
}

uint32_t BrowserBotPlayerEligible(jass_t *j) {
    player_t const *player = jass_checkhandle(j, 1, "player");
    return jass_pushboolean(j, player && G_BrowserBotPlayerEligible(PLAYER_NUM(player)));
}
