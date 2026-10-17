# Multiboard And TextTag JASS Natives

Server-owned registries for DotA-style scoreboards and floating combat/gold text.
Parent tracking: [dota-map-playability.md](dota-map-playability.md) / GitHub #434.

## Contract

| Handle | Registry | Notes |
| --- | --- | --- |
| `multiboard` | `level.multiboards[]` | Title, rows/cols, cells, per-client display/minimize bits |
| `multiboarditem` | `level.multiboard_items[]` | Refcounted view into one cell; `ReleaseItem` frees the view |
| `texttag` | `level.texttags[]` | Text, color, unit/world anchor, velocity, lifespan, visibility |

`MultiboardDisplay` / `MultiboardMinimize` / `SetTextTagVisibility` follow the leaderboard local model: `currentplayer` (GetLocalPlayer context) updates one client slot; a global call updates every connected client mask.

Destroying a multiboard sets `item->board = -1` so outstanding item handles no longer mutate cells. Cell data lives on the board, not on the item view.

## Implemented DotA Surface

Multiboard: create/destroy, display, minimize/`IsMultiboardMinimized`, title, set/get row/column count, get/release item, per-item style/value/color/width/icon, broadcast style/width.

TextTag: create/destroy, text+height, color, `Pos`/`PosUnit`, velocity, visibility, permanent, lifespan, fadepoint.

`IsMultiboardDisplayed` and `MultiboardSuppressDisplay` are registered. Other `common.txt` natives, including `MultiboardClear`, remain outstanding.

`MultiboardGetRowCount` / `MultiboardGetColumnCount` return the registry's current dimensions, including a zero dimension after resizing; null or destroyed boards return zero. Retail `Blizzard.j` calls both getters even for a single-cell `MultiboardSetItem*BJ` update. `peach.w3x` (Capture the Flag v1.66b) initializes a 4-column, 13-row board at 0.10 seconds and uses `MultiboardSetItemWidthBJ(board, 1, 0, 10.00)` to update every row of the first column. Missing getters previously aborted those wrapper calls.

`SetTextTagPos` retains explicit X/Y and height offset, clears an earlier unit anchor, marks the position initialized, and publishes through the existing keyed texttag event. `SetTextTagPosUnit` can subsequently attach that same handle again. Null or destroyed tags do not publish updates. The existing world-anchor transport uses the stored height offset as world Z; exact retail terrain-relative height behavior is unverified. `common.txt` and the extracted retail `Blizzard.j` establish these signatures and the scoreboard wrapper's 1-based/broadcast traversal. The supplied `REA/` report contains metadata only, with no native body evidence for these three functions.

## Presentation Gaps

- **Multiboard HUD:** `hud_multiboard.c` now emits `svc_layout` for a displayed custom board (title, cell text/colors/icons, minimized title) or the automatic Team Resources display. Single-board ownership is per client; showing a custom board replaces the previous custom board. Suppression hides the presentation without changing requested visibility.
- **Retail parity gaps:** stock multiboard FDF skin/geometry, cell width, UI minimize interaction and leaderboard coexistence still need asset-driven verification. Custom boards take precedence over Team Resources, and suppression hides both; see [Team Resources and Advanced Shared Control](team-resources.md). The current panel uses a conservative provisional layout.
- **TextTag draw:** JASS texttags publish keyed `TE_TEXT_TAG` create/update/remove events with resolved text, colour, font, anchor, visibility, motion and lifetime. The generic client updates one active label per texttag handle, follows a unit anchor, and draws it with the same world-text renderer as one-shot `TE_FLOATING_TEXT`. Resource-gain labels remain independent one-shot events ([resource-gain-text.md](resource-gain-text.md)).

Do not widen `entityState_t` / `playerState_t` for either widget.

## Save/Load

Save format version 76 persists multiboards, item views, and texttags (including `texttag.unit` via `F_EDICT` and texttag presentation generations) and JASS handle identity through registry indexes, plus per-client suppression and Team Resources collapse flags.

## Verification

```bash
make test-wc3-engine WC3_PATTERN='wc3_api.multiboard*'
make test-wc3-engine WC3_PATTERN='wc3_api.texttag*'
make test-wc3-engine WC3_PATTERN='wc3_api.leaderboard*'
```

Tests live in `games/warcraft-3/game/tests/t_multiboard.c`.
`multiboard_dimension_queries_allow_stock_broadcast_widths` exercises the stock wrapper in the fixture `Scripts/Blizzard.j`, including the map's 4x13 shape and a selected last cell. `texttag_world_position_replaces_unit_anchor_and_publishes_updates` checks repeated attach/detach, coordinates, keyed update packets, and null/destroyed handles. Both regressions failed before their native registrations/implementations were added and pass in RoC and TFT.

Team Resources is a distinct engine-managed display on `LAYER_GAME_3` (`WC3_LAYER_MULTIBOARD`), separate from the `LAYER_GAME_2` command-error overlay; see [Team Resources and Advanced Shared Control](team-resources.md).
