# Standalone map bots

The Apricot/Peach browser picker enables simple bots by default. Choose **Leave
empty** to use the original unattended player slots, or append `&bots=0` to a
map URL. Native launches keep bots disabled unless passed
`+set wc3_browser_bots 1`.

These are original companion policies for the two bundled maps, not stock
Warcraft computer AI. The maps retain their units, economy, alliances, tutorial,
capture/death triggers and victory conditions. The policies issue ordinary JASS
orders; they do not create units, grant resources, teleport runners or declare
results. Player 0 stays human. A connected human, unused slot, non-human slot or
removed player is never assigned bot orders. Every decision rechecks ownership,
so connecting a human stops subsequent bot orders for that player.

## Policies

Apricot's `BrowserApricot.j` coroutine wakes every two seconds. Human builders
spread toward the four authored corner regions, attempt a Woodsman Home and up
to three Vulcans using normal construction checks, and flee visible zombies.
The two unattended zombie slots attack visible builders or patrol corner
regions with attack-move orders. The map still spawns zombie heroes after 90
seconds. Construction is limited by the map's starting resources and the
engine's supported order APIs; this is a basic survival opponent, not a complete
economy or skill strategy.

Peach's `BrowserPeach.j` timer wakes every 0.75 seconds. Its runners return a
carried enemy flag to their own half, defend against nearby visible invaders,
rescue jailed teammates or approach the enemy flag. They observe the map's
runner group, player array, jail flags and rectangles. Paused tutorial units and
jailed runners receive no orders. The original tutorial and red player's round
selection remain in control; bots do not skip them or choose a match length.

## Runtime and persistence

`g_browser_bots.c` is a WC3-only adapter. It accepts only the normalized paths
`Maps/Download/apricot.w3x` and `Maps/Download/peach.w3x`, loads the matching
sidecar into the map VM after the map declarations, and starts its entry after
`main`. Sidecar declarations load even when bots are disabled so native save
program identities are independent of the launch setting. JASS globals,
groups, timer callbacks and suspended coroutines use the existing native save
machinery. Native restores require the same sidecar program identity; keep the
bot launch setting when restoring a bot session. Browser save/load remains
unsupported.

The custom `BrowserBotPlayerEligible(player)` native exposes the ownership gate.
Bots consume their own normal fog grids without becoming connected clients or
receiving network packets. `IsUnitVisible` uses active sight, invisibility and
hidden-unit state, including for buildings; explored scenery alone does not
reveal a target. Stock campaign AI and all network structures are unchanged.

Focused regressions live in `t_browser_bots.c`, `t_browser_apricot_bots.c` and
`t_browser_peach_bots.c`. They run the actual sidecars in the JASS VM and check
ordinary orders, timer/coroutine scheduling, ownership changes, visibility,
rescue and flag-carrier priorities. See [two-map compatibility](two-map-compatibility.md)
for actual-map validation and remaining engine limitations.
