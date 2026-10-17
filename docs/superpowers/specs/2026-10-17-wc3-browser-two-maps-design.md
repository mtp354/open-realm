# Warcraft III browser build: apricot and peach

## Intent

The owner wants a standalone, browser-only build of the OpenRealm Warcraft III
engine that plays exactly two maps: `apricot.w3x` and `peach.w3x`. The purpose
is personal education. The owner wants to take the finished result apart to
learn game design, so the build must stay inspectable: map scripts and game
data should be readable, not hidden inside an opaque bundle.

Once the engine can run these maps, it should close the gaps those two maps
actually hit, using the REA analysis of the original Warcraft III binaries as
the reference for correct behavior.

## Goals

- A browser page with a bare-bones picker that lists exactly two maps. Picking
  one starts it directly, with no further setup.
- Full play once a map starts: units move and fight, the map's triggers and
  JASS scripts run, and the game can be won or lost as the map intends.
  (My call: "full play" includes reaching the win or loss condition the map
  defines, not just running until the first combat.)
- Game data (the Blizzard archives needed at runtime and the two maps) is
  bundled into the browser build. The build is for the owner's personal use.
- Gap-fixing is limited to what apricot and peach hit at runtime. Fixes are
  made in the open-realm C source so the native build behaves as before.
- Analysis of the original binaries in `/home/matt/Projects/Game/REA/` is used
  to confirm behavior where the open-source code is a guess.

## Non-goals

- Any other map, campaign, or the Melee/custom-map picker.
- Multiplayer, LAN, and the lobby. Networking stays out of the browser build.
- Save and load. `g_save.c` is already excluded on wasm32 and remains
  unsupported here.
- Closing the broader JASS placeholder list in
  `games/warcraft-3/jass-native-coverage.md`. Only natives these two maps call
  are in scope.
- World of Warcraft and StarCraft II targets.
- Rewriting the engine in JavaScript or TypeScript.

## Anti-goals

- Shipping or publicly hosting the built page with the Blizzard data inside.
  The personal-use constraint is part of the design, not an afterthought.
- Breaking or weakening the native build, its tests, or its linker checks to
  make the browser build pass.
- Patching around a missing behavior with a silent no-op that hides the gap.
  A gap that a map hits must be implemented or reported as a visible failure.

## Constraints

- The engine is C. The browser build compiles it to WebAssembly with
  Emscripten and renders through WebGL 2, following the existing foundation in
  `port/web/` (`build.mk`, `build-engine.py`, `site/`, `src/`).
- `port/web/` is documented as experimental, with full runtime compatibility
  unverified. Its existing targets are the starting point, not a finished
  build.
- wasm32 has 32-bit pointers. Any code that stores data in pointer-sized slots
  must be checked.
- Emscripten is not installed on this machine. Activating an emsdk
  installation is required before any browser build can run.
- The owner's Warcraft III files are in `/home/matt/Projects/Game`. The two
  maps are in `Maps/Download/`. The archives are `persimmon.mpq`,
  `tangerine.mpq`, `War3Patch.mpq`, and `War3xlocal.mpq`.
- The native build needs SDL2 and OpenGL, and is driven from the root
  `Makefile`.

## The how, as decided

- **Engine approach (my call):** compile the existing C engine to WebAssembly.
  The repo has a foundation for this, and the game logic is too large to
  reimplement reliably in JavaScript.
- **Page shape (my call):** a single static page that loads the engine and
  shows the two-map picker. The page has no other UI.
- **REA use (my call):** REA evidence (`REA/evidence/`, `REA/REPORT.txt`, and
  the Ghidra-derived procedure data for `kiwi.exe` and `lime.dll`) is consulted
  whenever a runtime gap needs a reference for what the original did. It is
  not used to generate code.
- **Gap procedure (my call):** run each map in the browser build, record the
  first JASS native that is a placeholder or the first engine path that fails,
  fix that item, and repeat until both maps reach full play.
- **Save and audio (my call):** save/load is out of scope. Audio is treated as
  best-effort and must not block play.

## Done means

- Both apricot and peach can be picked from the page and start without manual
  steps.
- Each map runs through its opening and into normal play: units move, combat
  resolves, and triggers fire. Verified by playing them in the browser.
- The browser build loads without console errors or wasm traps during that play.
- The native build still compiles and its existing tests still pass.
- Each gap-fix commit names the map and the behavior it unblocked.

## Left to the builder

- The exact Emscripten version and how the emsdk is activated.
- How the game data is packaged: preloaded files, embedded files, or a
  generated archive. Choose the one that keeps load time reasonable.
- Which retail archives are strictly required at runtime, and which can be
  left out.
- Picker layout and styling, as long as it is bare-bones and shows exactly
  two entries.
- Whether debug symbols or source maps are included, provided the default
  build is readable enough to study.
- How the REA evidence is queried for a given behavior.
