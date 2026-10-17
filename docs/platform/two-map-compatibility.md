# Two-Map Warcraft III Compatibility

Scope: the standalone browser package's `Maps/Download/apricot.w3x` and
`Maps/Download/peach.w3x`. See [browser setup](browser.md) for packaging and
rendering status. Native registration coverage is tracked in
[JASS Native Coverage](../../games/warcraft-3/jass-native-coverage.md); registration
and a successful startup do not establish a complete playthrough.

## Authored Map Contracts

| Map | Identity and opening | Authored win/loss |
| --- | --- | --- |
| `apricot.w3x` | **Troopers Vs Zombies v6.5**, 4–12 players. Players 0–2 are zombies; 3–11 are humans. Humans receive `h00Q` builders immediately; zombies receive `O000` at 90 seconds. Default local player 0 begins by its `n005` building at `(2048, -2816)`. | `Trig_People_win_modifier_Actions` enables both result predicates after 92 seconds; each polls every 5 seconds. Zombies win when no living `h00Q` remains for players 3–11. Humans win when no living `O000`, `n00D`, or `O007` remains for players 0–2. Each side's force receives `CustomVictoryBJ` or `CustomDefeatBJ`. |
| `peach.w3x` | **Capture the Flag v1.66b**, jim109109, generated 2011-10-19. Default local player 0 controls `H000` near `(0, 448)`. A tutorial starts at 0.50 seconds, pauses units/disables control, then returns control and opens Red's round-count dialog (3/5/7/10/15; default 5). Escape votes to skip while the authored voting trigger is enabled. | Coming within 200 units of the enemy `e000` flag hides that flag and transfers `I000`/`I001` to the runner. Entering the runner's home-side rectangle with the opposing flag scores; jailing every opponent also scores. `Trig_Point_Scored_Actions` either resets the round or invokes `Trig_Check_winners_Actions`. The winning side's `Trig_game_win_one_Actions` / `Trig_game_win_two_Actions` waits 2 seconds, rotates the camera 720 degrees over 60 seconds, waits 60 seconds, then issues victories/defeats. |

Apricot's exact chat commands are `-spawn nw`, `-spawn ne`, `-spawn sw`, and
`-spawn se`. They teleport human `h00Q` builders to the named corner before
the zombie spawn. Only players 3–11 have registrations; they do not apply to
default local player 0. All four triggers are disabled at 90 seconds.

Both maps configure all twelve slots as user controlled. Neither script starts
a computer AI. A single browser client does not establish multiplayer opponents
or authored bot behavior. The engine's current `GetPlayerSlotState` uses map
slot metadata, so unconnected human map slots can still count as playing.

## Native Gaps And Fixes

| Surface | Evidence and scope |
| --- | --- |
| Event registrations | Peach has 61 `TriggerRegisterAnyUnitEventBJ` sites, each expanding over 16 players, plus timers, regions and direct registrations. The baseline dedicated run crashed after `event slot limit 1024 reached`. Capacity is now 2048 with matching handle/token bits and save version 90; exhaustion must return a safe null event. See [trigger events](../games/warcraft-3/trigger-events.md). |
| `MultiboardGetRowCount`, `MultiboardGetColumnCount` | Implemented against existing registry state. Peach's 0.10-second 4x13 scoreboard uses stock `MultiboardSetItem*BJ` wrappers, which call both missing getters before touching cells. Regression uses the stock broadcast-width wrapper. |
| `SetTextTagPos` | Registered explicit world-anchor updates and unit-anchor replacement. Null/destroyed tags and wire updates are covered. Exact retail terrain-relative height remains unverified; see [multiboards/texttags](../games/warcraft-3/multiboard-and-texttag.md). |
| `SetCameraRotateMode` | Implemented full signed sweep and pivot-based orbit in the game scheduler, preserving 360/720-degree requests instead of shortest-arc collapse. Supports stop/replacement and save/load. This native occurs before Peach's terminal result calls. See [camera contract and native evidence](../games/warcraft-3/cinematics.md). |
| `UnitDamagePoint` | Implemented Apricot's immediate `UnitDamagePointLoc` call with radius 900 and damage 80, including footprint distance and damage-source events. Positive delays are explicitly rejected and typed flags retain the existing scripted-damage limitation; see [attack damage](../games/warcraft-3/attack-damage.md). |
| `TriggerRegisterPlayerChatEvent` | Registered placeholder in the baseline. Breaks the four Apricot corner commands and Peach's chat-driven settings/cosmetics. Browser text submission alone cannot fix the missing game-event dispatch. |
| `IsItemIdSellable`, `GroupEnumUnitsOfType` | The first is unregistered and the second is a placeholder in the baseline. They occur in the stock marketplace initialization closure; direct map scripts do not call them. Static reachability does not prove this dormant branch executed. |
| Item ownership | `SetItemPlayer` remains a placeholder. Peach sets each hidden flag item's owner, but capture predicates use runner alliance/group membership and item type; ownership is not the capture gate. |
| Carried item positioning | `SetItemPosition` previously ignored carried items, so Peach's round-reset and dropped-flag storage calls left flags attached to runners. It now uses the existing scripted drop lifecycle to release the slot/passive effects and place the same item in the world. Two pickup/reset cycles are regression-tested; see [inventory contract and retail binary evidence](../games/warcraft-3/inventory-and-items.md#drop-and-script-paths). |
| Null-player text | Normal Apricot combat killed a builder at 138.8 seconds and crashed in `DisplayTimedTextFromPlayer`: the map's `Trig_Defeat_Func002A` calls `CustomDefeatBJ(GetEnumPlayer(), ...)` from `ForGroup`, which supplies no force-enumeration player. `DisplayTextToPlayer`, `DisplayTimedTextToPlayer`, and `DisplayTimedTextFromPlayer` now safely ignore a null recipient. This does not repair or reinterpret the map's malformed defeat callback. A focused group-callback regression confirms no broadcast or message overwrite. |
| Audio | `NewSoundEnvironment`, `StopSound`, `CreateMIDISound`, and `VolumeGroupSetVolume` remain placeholders in the baseline; Peach also calls placeholder `SetSoundPitch` / `SetSoundChannel`. Missing staged audio is tracked separately in browser setup. |

## Command Card Data

The partial installation has `Units\CommandStrings.txt` in its imported MPQs,
but no `Units\CommandFunc.txt`. `InitUnitData` loads both; `FindConfigValue`
prefers these tables for `Cmd*` sections. Without the function profile,
`G_BuildCommandButton` logs `skipping missing art` and omits Move, Stop, Hold,
Patrol, Attack and Hero Abilities even though their command handlers exist.

The explicit basic asset generator now provides `Units/CommandFunc.txt` with
art paths and grid positions, plus eleven original geometric glyphs under
`UI/BrowserBasic/command-*.blp`. It covers ordinary movement/combat commands,
skill menu, rally, build and cancellation commands. Labels, hotkeys and errors
continue to resolve from imported `CommandStrings`; no engine HUD fallback or
map modification is involved.

Peach's custom `H000` has hero abilities `AEer,AOwk,A000,AEev,AEbl` (the custom
`A000` uses the Staff of Sanctuary art). Their function profiles exist, but
the imported archives lack the Entangling Roots, Wind Walk, Staff, Evasion,
Blink and passive Evasion icon files. The basic catalog supplies original
glyphs at those twelve enabled/disabled paths. Disabled icons use the normal
`CommandButtonDisabledArtPath` plus `DIS` and the source basename, including
`DISPASBTNEvasion.blp`. Browser clicks dismiss the authored round dialog and open the skill menu with
the generated icons. The map places both Roots and Wind Walk at research cell
(0,0); that authored overlap remains. A normal browser right-click also moved the selected runner to the requested
area. Individual skill learning remains unverified; menu art and input checks
do not prove every map ability works.

```sh
python3 port/web/generate-basic-assets.py
python3 -m unittest tests.test_web_basic_assets
```

## Extraction And Bounded Checks

Apricot's protected listfile is not an inventory. Its script is stored under
`scripts/war3map.j`; Peach uses the root member:

```sh
build/bin/mpqtool -mpq port/web/data-input/Maps/Download/apricot.w3x cat scripts/war3map.j
build/bin/mpqtool -mpq port/web/data-input/Maps/Download/peach.w3x cat war3map.j
build/bin/mpqtool -mpq port/web/data-input/Maps/Download/apricot.w3x cat war3map.wts
```

Bounded simulation audit (120 seconds of simulation; no framebuffer or player
input validation):

```sh
python3 tools/wc3_map_audit.py --data port/web/data-input \
  --binary build/bin/openwarcraft3 --mpqtool build/bin/mpqtool \
  --jobs 1 --frames 1200 --timeout 45 --port-base 29571 \
  --output-dir build/two-map-audit \
  --loose-map port/web/data-input/Maps/Download/apricot.w3x \
  --loose-map port/web/data-input/Maps/Download/peach.w3x
```

The pre-fix audit reached the frame limit for Apricot and crashed on Peach's
event capacity. The final audit reached 2,000 bounded simulation frames for
both maps without a JASS runtime error, missing-native abort, event-limit error
or process crash. This covers scheduler execution, not framebuffer/input or
complete objective-driven playthroughs; dedicated slots can gate player spawns.

With `sv_cheats 1`, these commands exercise map-authored terminal action paths:

```text
jass Trig_infected_win_Actions       # Apricot: local player 0 victory
jass Trig_humans_win_Actions         # Apricot: local player 0 defeat
jass Trig_Skip_tutorial_Copy_Actions # Peach: authored tutorial cleanup
jass Trig_game_win_one_Actions      # Peach: team 1/local player 0 victory
jass Trig_game_win_two_Actions      # Peach: team 2/local player 0 defeat
```

They bypass objective predicates and are result-path checks, not playthroughs.
Allow at least 62.05 simulated seconds after Peach's game-win actions before
expecting results. A complete gameplay check must additionally move a unit,
capture/return flags or kill the authored target units, exercise round reset,
and verify the result dialog and exit actions.


## Objective and bot checks (2026-10-17)

The native Apricot check selected player 0's spawned zombie hero at 95 seconds
and sent a normal `smartpoint 1008 1936` order. By 360 simulated seconds all
nine authored human builders were dead, three zombie heroes remained, and
player 0 had the authored victory result. This also passes the former
138.8-second null-player text crash. The map leaves its repeating win trigger
enabled; if the result is ignored, repeated stock dialog creation eventually
reaches the safe 64-dialog limit. Restart or leave the result screen.

With the optional [bots](browser-bots.md), native Peach progressed from 1–0 at
600 seconds to 5–0 at 2,200 seconds and removed player 0 through the original
terminal result. No results, resources, unit positions or scores were injected;
player 0 was idle. This exercises a complete match and multiple authored round
resets, rather than directly invoking a result action. It is a native simulation
check; browser framebuffer, input and result checks remain separate evidence.

Apricot bot checks reached the authored corner regions, issued normal combat
orders and constructed starter buildings. This exposed the missing
`PathTextures/4x4SimpleSolid.tga` used by the Woodsman Home. The basic generator
now supplies this footprint as well; native construction then proceeds through
normal placement and costs. The complete basic pack contains 227 assets.

## Review and validation

The change makes the two bundled maps load with original basic assets, repairs
map-reached native contracts, and adds optional unattended-player policies.
Network layouts are unchanged. Native save version 90 rejects older saves;
browser save/load remains unsupported.

The final full suite passed (32 suite summaries), all three native game targets
built, the WebAssembly build linked, and both boundary audits were clean.
Browser startup/result checks were cross-origin isolated and recorded no
JavaScript exceptions or WASM traps.

Validation commands (activate the local SDL environment and Emscripten SDK as
needed):

```sh
make -j8 test
make -j8 build openwow opensc2
make web-warcraft3-engine
python3 tools/engine_boundary_audit.py
python3 tools/menu_boundary_audit.py
python3 port/web/serve.py
```

Suggested review split, in dependency order: (1) client pointer lifecycle;
(2) WC3 native contracts, event capacity, save version and regression tests;
(3) explicit basic asset generation, packaging, launcher and server;
(4) map bot sidecars, ownership/visibility adapter and policy tests. This is a
review proposal, not a rewritten or split history.
