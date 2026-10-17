#ifdef BZ_TESTS
#include "test.h"
#include "../g_local.h"
#include "jass/jass.h"

void setup_test_world(void);
bool run_test_jass(cstring_t src);
slkTestData_t *parse_slk_string(char const *text);
void free_slk_rows(slkTestData_t *rows);

TEST(wc3_items, set_item_position_clears_carried_round_objective) {
    char const ability_data[] =
        "ID;PWXL;N;EBB;Y3;X8\n"
        "C;Y1;X1;K\"alias\"\nC;Y1;X2;K\"code\"\nC;Y1;X3;K\"DataA1\"\n"
        "C;Y1;X4;K\"DataB1\"\nC;Y1;X5;K\"DataC1\"\n"
        "C;Y1;X6;K\"DataD1\"\nC;Y1;X7;K\"DataE1\"\nC;Y1;X8;K\"levels\"\n"
        "C;Y2;X1;K\"AInv\"\nC;Y2;X2;K\"AInv\"\nC;Y2;X3;K\"6\"\n"
        "C;Y2;X4;K\"0\"\nC;Y2;X5;K\"1\"\nC;Y2;X6;K\"1\"\n"
        "C;Y2;X7;K\"1\"\nC;Y2;X8;K\"1\"\n"
        "C;Y3;X1;K\"AIat\"\nC;Y3;X2;K\"AIat\"\nC;Y3;X3;K\"6\"\nC;Y3;X8;K\"1\"\nE\n";
    slkTestData_t *rows = parse_slk_string(ability_data), *old = G_SetSLKRows("AbilityData", rows);
    edict_t *carrier = NULL, *item = NULL;
    setup_test_world();
    T_ASSERT(run_test_jass(
        "globals\nunit runner = null\nitem flag = null\nendglobals\n"
        "function reset_round takes nothing returns nothing\n"
        "call SetItemPosition(flag, -512.0, -256.0)\nendfunction\n"
        "function take_flag takes nothing returns nothing\n"
        "call UnitAddItem(runner, flag)\nendfunction\n"
        "function main takes nothing returns nothing\n"
        "set runner = CreateUnit(Player(0), 'Hpal', 0.0, 0.0, 0.0)\n"
        "set flag = CreateItem('ratf', 0.0, 0.0)\n"
        "call SetItemCharges(flag, 7)\n"
        "call UnitAddItem(runner, flag)\n"
        "call SetItemDroppable(flag, false)\nendfunction\n"));
    FOR_LOOP(i, globals.num_edicts) {
        edict_t *ent = g_edicts + i;
        if (!ent->inuse) continue;
        if (ent->class_id == MAKEFOURCC('H','p','a','l')) carrier = ent;
        if (G_IsItem(ent) && ent->class_id == MAKEFOURCC('r','a','t','f')) item = ent;
    }
    T_NOT_NULL(carrier);
    T_NOT_NULL(item);
    if (!carrier || !item) goto cleanup;
    T_ASSERT(item->item->carrier == carrier);
    T_ASSERT(!G_ItemDroppable(item));
    T_ASSERT(!G_DropItem(carrier, (uint32_t)item->item->inventory_slot));
    float const carried_bonus = carrier->attack1.temporaryDamageBonus;
    T_ASSERT(carried_bonus > 0);

    /* Peach resets its reusable flag item with SetItemPositionLoc. Exercise
     * two pickups/resets to catch stale inventory ownership and stat leakage. */
    FOR_LOOP(round, 2) {
        jass_callbyname(level.vm, "reset_round", true);
        jass_runevents(level.vm);
        T_ASSERT(!jass_rterror_pending(level.vm));
        T_NULL(item->item->carrier);
        T_EQ(item->item->inventory_slot, -1);
        T_ASSERT(item->item->in_world);
        T_ASSERT(!(item->s.renderfx & RF_HIDDEN));
        T_ASSERT(!(item->svflags & SVF_NOCLIENT));
        T_FEQ(item->s.origin.x, -512, 0.01f);
        T_FEQ(item->s.origin.y, -256, 0.01f);
        T_EQ(item->item->charges, 7);
        T_FEQ(carrier->attack1.temporaryDamageBonus, 0, 0.01f);
        FOR_LOOP(slot, MAX_INVENTORY) T_ASSERT(carrier->inventory[slot] != item);
        if (round == 0) {
            jass_callbyname(level.vm, "take_flag", true);
            jass_runevents(level.vm);
            T_ASSERT(item->item->carrier == carrier);
            T_FEQ(carrier->attack1.temporaryDamageBonus, carried_bonus, 0.01f);
        }
    }
cleanup:
    G_SetSLKRows("AbilityData", old);
    free_slk_rows(rows);
}

TEST(wc3_items, set_item_position_preserves_world_item_and_null_behavior) {
    setup_test_world();
    T_ASSERT(run_test_jass(
        "function main takes nothing returns nothing\n"
        "local item token = CreateItem('ratf', 0.0, 0.0)\n"
        "call SetItemPosition(token, 128.0, 64.0)\n"
        "call BJassAssert(GetItemX(token) == 128.0, \"world item x changed\")\n"
        "call BJassAssert(GetItemY(token) == 64.0, \"world item y changed\")\n"
        "call SetItemPosition(null, 32.0, 32.0)\nendfunction\n"));
}
#endif
