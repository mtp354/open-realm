# Warcraft III Allies Menu

## Ownership

The in-game Allies dialog is a server-authored `svc_window` built from the stock
`AllianceDialog.fdf` and `AllianceSlot` templates. F11 and the upper Allies
button both route through `cmd allies`. The window is modal for input capture but
uses `UI_WINDOW_NO_PAUSE`, so opening it does not freeze the single-player
simulation.

## Alliance editing

Each visible player row uses the existing directional alliance matrix. The Ally,
Share Vision, and Share Units checkboxes edit a per-player draft. Share Units
requires both passive alliance and shared vision. Accept commits changed
`ALLIANCE_PASSIVE`, `ALLIANCE_SHARED_VISION`, and `ALLIANCE_SHARED_CONTROL`
values plus the Allied Victory player state; Cancel discards the draft. Map flags
that lock or hide alliance changes are applied before controls are serialized.

Shared vision and shared control are not reimplemented by the dialog: accepted
changes feed the existing fog and command-authority paths. Gold/lumber transfer
fields remain presentation-only until there is an authoritative resource-transfer
operation with map-flag and balance validation.

### JASS relationships and team forces

`IsPlayerAlly`, `IsPlayerEnemy`, `ForceEnumAllies` and `ForceEnumEnemies`
use `G_PlayerTreatsPlayerAsAlly(source, other)`: a player is always allied to
itself; other relations read the directional `ALLIANCE_PASSIVE` matrix bit.
The low-level `GetPlayerAlliance` query still reports the stored bit. Do not
require a diagonal passive-alliance bit or make one-way alliances mutual.

Retail Blizzard.j's `GetPlayersAllies` / `GetPlayersEnemies` create a force and
invoke those enumeration natives. Peach's `Trig_game_win_one_Actions` awards
victory to the first force and defeat to the second. Reading the raw matrix
for self put local player 0 into its own enemy force, awarding defeat when its
team won. The relationship helper fixes both native predicates and force
construction without changing result or network state.

`tests/t_alliance_forces.c` covers self with an unset diagonal bit, asymmetric
alliances (0 -> 2, 1 -> 0), stock force membership, `ForForce` enumeration and
force-bit edits, then the Peach-shaped result pipeline: players 0/2 receive
victory and player 1 receives defeat. The original failure reproduces through
JASS and the ordinary `RemovePlayer` result events.

## Layout and scrolling

`AllianceBackdrop` is pinned to both corners of `AllianceDialog` because the
server-authored flattening path otherwise receives a zero-sized stock backdrop.
Stock Esc-menu button and checkbox state art is resolved for the receiving
player's race at serialization time.

The retail FDF also contains `AllianceDialogScrollBar`. OpenRealm currently has
at most eleven other regular players and all eleven `AllianceSlot` rows fit in
the authored dialog above Allied Victory, so that optional scrollbar is hidden.
Its child arrow/thumb buttons must not be serialized as independent controls.
Generic TextArea scrollbars (including the Message Log) are implemented by the
shared server-authored scrollbar path instead.

## Remaining gaps

- Resource trading is not yet authoritative.
- Allied Victory is stored through `PLAYERSTATE_ALLIED_VICTORY`; victory-condition
  consumers still need to honor it where retail semantics require it.
- Retail filtering/visibility details for unusual custom-map player-slot setups
  may need further compatibility work.
