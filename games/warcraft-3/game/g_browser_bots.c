#include "g_local.h"
#include "jass/jass.h"

/* Optional standalone policies live in the map VM and use normal JASS orders.
 * Keep this adapter out of the shared engine and stock campaign AI. */
typedef struct {
    cstring_t map, script, entry;
} browserBotPolicy_t;

static browserBotPolicy_t const policies[] = {
    { "Maps/Download/apricot.w3x", "warcraft-3\\Scripts\\BrowserApricot.j", "BrowserApricotBots" },
    { "Maps/Download/peach.w3x", "warcraft-3\\Scripts\\BrowserPeach.j", "BrowserPeachBots" },
};

static browserBotPolicy_t const *G_BrowserBotPolicy(void) {
    char path[sizeof(level.map_path)];
    strlcpy(path, level.map_path, sizeof(path));
    for (char *p = path; *p; ++p) if (*p == '\\') *p = '/';
    FOR_LOOP(i, sizeof(policies) / sizeof(policies[0]))
        if (!strcasecmp(path, policies[i].map)) return policies + i;
    return NULL;
}

bool G_BrowserBotPlayerEligible(uint32_t player) {
    gameClient_t const *client;
    mapPlayer_t const *slot;
    if (!player || player >= 12 || player >= game.max_clients || !level.mapinfo ||
        !G_BrowserBotPolicy() || !atoi(gi.CvarString("wc3_browser_bots", "0"))) return false;
    slot = level.mapinfo->players + player;
    client = G_GetPlayerClientByNumber(player);
    return slot->used && slot->playerType == kPlayerTypeHuman && client &&
        !client->connected && !client->jass.removed;
}

void G_LoadBrowserBots(void) {
    browserBotPolicy_t const *policy = G_BrowserBotPolicy();
    /* Declarations are deterministic even with bots disabled, so save program
     * identities do not depend on a launch cvar. No map bytes are rewritten. */
    if (policy && !jass_dofile(level.vm, policy->script))
        fprintf(stderr, "WC3 browser bots: could not load %s\n", policy->script);
}

void G_StartBrowserBots(void) {
    browserBotPolicy_t const *policy = G_BrowserBotPolicy();
    if (policy && atoi(gi.CvarString("wc3_browser_bots", "0")))
        jass_startcoroutinebyname(level.vm, policy->entry);
}

uint32_t BrowserBotPlayerEligible(jass_t *j) {
    player_t const *player = jass_checkhandle(j, 1, "player");
    return jass_pushboolean(j, player && G_BrowserBotPlayerEligible(PLAYER_NUM(player)));
}
