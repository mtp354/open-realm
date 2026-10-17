#ifdef BZ_TESTS
#include "test.h"
#include "../g_local.h"

bool run_test_jass(cstring_t src);

/* Self is deliberately absent from the raw matrix. Ordinary alliances are directional. */
#define DIRECTIONAL_ALLIANCE_SETUP \
    "  call SetPlayerAlliance(Player(0), Player(0), ALLIANCE_PASSIVE, false)\n" \
    "  call SetPlayerAlliance(Player(0), Player(1), ALLIANCE_PASSIVE, false)\n" \
    "  call SetPlayerAlliance(Player(1), Player(0), ALLIANCE_PASSIVE, true)\n" \
    "  call SetPlayerAlliance(Player(0), Player(2), ALLIANCE_PASSIVE, true)\n" \
    "  call SetPlayerAlliance(Player(2), Player(0), ALLIANCE_PASSIVE, false)\n"

TEST(wc3_alliance, self_and_directional_jass_relationships) {
    T_ASSERT(run_test_jass(
        "function main takes nothing returns nothing\n"
        DIRECTIONAL_ALLIANCE_SETUP
        "  call BJassAssert(IsPlayerAlly(Player(0), Player(0)), \"self must be an ally without diagonal bit\")\n"
        "  call BJassAssert(not IsPlayerEnemy(Player(0), Player(0)), \"self cannot be an enemy\")\n"
        "  call BJassAssert(IsPlayerAlly(Player(0), Player(2)), \"outgoing ally was rejected\")\n"
        "  call BJassAssert(IsPlayerEnemy(Player(2), Player(0)), \"one-way alliance became mutual\")\n"
        "  call BJassAssert(IsPlayerEnemy(Player(0), Player(1)), \"outgoing enemy became an ally\")\n"
        "  call BJassAssert(IsPlayerAlly(Player(1), Player(0)), \"reverse alliance was lost\")\n"
        "  call BJassAssert(not IsPlayerAlly(null, Player(0)) and not IsPlayerEnemy(null, Player(0)), \"null player has a relationship\")\n"
        "endfunction\n"));
    T_EQ(level.alliances[0][0] & (1u << ALLIANCE_PASSIVE), 0);
}

TEST(wc3_alliance, stock_forces_partition_self_allies_and_enemies) {
    uint32_t max_clients = game.max_clients;
    game.max_clients = 3;
    T_ASSERT(run_test_jass(
        "globals\n"
        "  integer members = 0\n"
        "endglobals\n"
        "function visit takes nothing returns nothing\n"
        "  local integer id = GetPlayerId(GetEnumPlayer())\n"
        "  if id == 0 then\n"
        "    set members = members + 1\n"
        "  elseif id == 1 then\n"
        "    set members = members + 2\n"
        "  elseif id == 2 then\n"
        "    set members = members + 4\n"
        "  else\n"
        "    set members = members + 100\n"
        "  endif\n"
        "endfunction\n"
        "function main takes nothing returns nothing\n"
        "  local force allies = null\n"
        "  local force enemies = null\n"
        DIRECTIONAL_ALLIANCE_SETUP
        "  set allies = GetPlayersAllies(Player(0))\n"
        "  set enemies = GetPlayersEnemies(Player(0))\n"
        "  call BJassAssert(IsPlayerInForce(Player(0), allies) and not IsPlayerInForce(Player(0), enemies), \"self force membership is reversed\")\n"
        "  call BJassAssert(IsPlayerInForce(Player(2), allies) and not IsPlayerInForce(Player(2), enemies), \"ally force membership is reversed\")\n"
        "  call BJassAssert(IsPlayerInForce(Player(1), enemies) and not IsPlayerInForce(Player(1), allies), \"enemy force membership is reversed\")\n"
        "  call ForForce(allies, function visit)\n"
        "  call BJassAssert(members == 5, \"ForForce did not visit exactly self and ally\")\n"
        "  set members = 0\n"
        "  call ForForce(enemies, function visit)\n"
        "  call BJassAssert(members == 2, \"ForForce did not visit exactly enemy\")\n"
        "  call ForceRemovePlayer(allies, Player(0))\n"
        "  call ForceAddPlayer(allies, Player(1))\n"
        "  call BJassAssert(not IsPlayerInForce(Player(0), allies) and IsPlayerInForce(Player(1), allies), \"force bit membership did not track edits\")\n"
        "  set members = 0\n"
        "  call ForForce(allies, function visit)\n"
        "  call BJassAssert(members == 6, \"ForForce membership edits changed unrelated bits\")\n"
        "endfunction\n"));
    game.max_clients = max_clients;
}

TEST(wc3_alliance, peach_winner_force_gives_local_self_victory_and_enemy_defeat) {
    uint32_t max_clients = game.max_clients;
    uint32_t winners = 0, losers = 0;
    game.max_clients = 3;
    T_ASSERT(run_test_jass(
        "function winner takes nothing returns nothing\n"
        "  call RemovePlayer(GetEnumPlayer(), PLAYER_GAME_RESULT_VICTORY)\n"
        "endfunction\n"
        "function loser takes nothing returns nothing\n"
        "  call RemovePlayer(GetEnumPlayer(), PLAYER_GAME_RESULT_DEFEAT)\n"
        "endfunction\n"
        "function main takes nothing returns nothing\n"
        DIRECTIONAL_ALLIANCE_SETUP
        /* Same force/result calls as Peach's Trig_game_win_one_Actions. */
        "  call ForForce(GetPlayersAllies(Player(0)), function winner)\n"
        "  call ForForce(GetPlayersEnemies(Player(0)), function loser)\n"
        "  call BJassAssert(GetPlayerState(Player(0), PLAYER_STATE_GAME_RESULT) == 0, \"local winner was defeated\")\n"
        "  call BJassAssert(GetPlayerState(Player(2), PLAYER_STATE_GAME_RESULT) == 0, \"ally did not win\")\n"
        "  call BJassAssert(GetPlayerState(Player(1), PLAYER_STATE_GAME_RESULT) == 1, \"enemy did not lose\")\n"
        "endfunction\n"));
    for (uint32_t i = level.events.read; i < level.events.write; i++) {
        gameEvent_t const *event = &level.events.queue[i % MAX_EVENT_QUEUE];
        if (event->type == EVENT_PLAYER_VICTORY && event->edict) winners |= 1u << event->edict->s.number;
        if (event->type == EVENT_PLAYER_DEFEAT && event->edict) losers |= 1u << event->edict->s.number;
    }
    T_EQ(winners, 5);
    T_EQ(losers, 2);
    game.max_clients = max_clients;
}

#undef DIRECTIONAL_ALLIANCE_SETUP
#endif
