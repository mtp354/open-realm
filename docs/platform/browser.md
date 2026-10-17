# Browser platform — phase 1 foundation

This stage adds an opt-in Emscripten / SDL2 / WebGL 2 smoke-test target. It
**does not** compile or start OpenWarcraft III yet. The native build graph in
`Makefile` still produces ELF/dylib/DLL modules and must not be run under `emcc`
as if these were browser-loadable modules.

## Build

Activate an Emscripten SDK (`emsdk_env.sh`) and run:

```sh
make web-warcraft3-foundation
python3 port/web/serve.py
```

Open `http://127.0.0.1:8000/`. The server adds the COOP/COEP headers required
for Emscripten pthreads and shared memory. Do not open generated HTML from
`file://` or serve it with a plain static server that omits those headers.
A dark canvas and a status of "WebGL 2 probe running" indicate browser-side
SDL2, WASM and WebGL 2 initialization. This
is **not** proof that OpenRealm's actual GLES3 renderer is WebGL 2 compatible.
No Warcraft game files are used or distributed.

## Next integration stages

### On-screen browser controls

The browser launcher overlays **Esc** (send an Escape key press to the game,
including during cinematics) and **fullscreen** (toggle fullscreen for the
canvas and controls together) at the upper-right corner of the game view.
These are browser DOM controls, not game UI frames, and remain available after
the canvas transfers to the rendering pthread. Fullscreen requires a user
gesture and may be unavailable under restrictive embedding policies.

1. Inventory module entry points and shared-library dependencies in the
   `shared`, `client`, `server`, `renderer`, `games/warcraft-3` and `jass`
   modules. Introduce explicit static registration instead of native dynamic
   loading where required; retain the existing game/client ABI boundaries.
2. Port the native OpenRealm entry point and frame pump to browser scheduling.
3. Audit the existing GLES3 renderer and shader paths against WebGL 2.
4. Provide a WASM filesystem bridge with random-access archive reads and
   persistent local game data.
5. Add a launcher, installer, audio, save persistence and PWA support.

The source-only platform probe deliberately avoids browser-pthread requirements,
proprietary retail archives, new gameplay code and modifications to existing
native module ownership.

## Phase 2 — engine frame scheduling and module audit

`common/main.c` now provides `OpenRealm_Frame`, shared by the native busy loop
and the Emscripten callback (`emscripten_set_main_loop_arg`). It preserves the
online → server → client frame order, clock deltas, fast-forward behavior and
frame-limit shutdown. Native frame throttling remains native-only. Dedicated
stdin polling is excluded from Emscripten.

Run `make web-warcraft3-engine-check` for a **source-only** audit of this
integration and the existing module entry points. This is not an Emscripten
compiler test and does not produce a playable game.

The inspected modules already call `GetGameAPI`, `R_GetAPI` and `M_GetAPI`
through direct C symbols. They do not currently require `dlopen` shims for
these entry points. A subsequent patch must link the actual common, server,
client, game, renderer, menu, shared, JASS and sheet modules as a single wasm
program, resolving portability issues explicitly rather than weakening linker
checks. The `web-warcraft3-foundation` target remains a standalone graphics
probe in this phase. Browser file storage and installation are not yet present.

## Phase 3 — browser-local game data importer

The platform probe page now exposes a launcher-only file importer.
`site/installer.js` sends File objects to `site/install-worker.js`, which
reads them in 1 MiB chunks and stores them under OPFS
`openrealm/game-data/wc3/`. A versioned `installation.json` manifest is
written last, after copying completes. The worker supports cancellation and
removal. OPFS is origin-scoped and no data is sent to a server.

This is a *storage foundation*, not the game-data engine mount. The importer
does not claim that every MPQ is sufficient or valid for a playable Warcraft
installation. It currently supports flat selected MPQ/W3M/W3X files, and
does not extract CASC, ZIP archives or directories. Existing MPQ code has not
yet been connected to OPFS. Interrupted commits can leave orphan files,
and replacing an existing installation is not a fully atomic transaction;
the engine must not trust file presence without validating a manifest and
actual archive contents. Avoid importing over an active game session.

A later patch must mount this storage into Emscripten FS using efficient
random-access reads, validate complete installations, and integrate the
actual OpenRealm WASM engine. The probe remains only a probe.

## Phase 4 — experimental static engine link

Run `make web-warcraft3-engine` with an activated Emscripten SDK. This new
target invokes `port/web/build-engine.py`, which compiles the real native
module source groups into separate WASM objects and attempts a single link.
The existing C entry points (`GetGameAPI`, `R_GetAPI`, `M_GetAPI`) are retained.
The normal native Makefile outputs are not replaced.

This is an **experimental compile/link target**, not a claim of a successful
build or a working game. The first compiler diagnostics should be resolved in
follow-up browser-port patches. In particular, browser networking, audio,
OpenGL ES/WebGL API compatibility, filesystem persistence, generated font
header production and startup asset mounts require additional integration.

The output `build/web/engine/` includes the launcher helper scripts. The page
validates its active OPFS installation before loading Emscripten's generated
script, then passes the active archive directory to native startup. Existing
MPQ/game file loading and full runtime compatibility still require browser
verification. Do not upload or ship retail data with this target.


## Phase 10 — engine build source preflight

The engine build script generates per-module unity compilation units beneath
`build/web/engine`. Quoted include paths are relative to **that generated file**,
not to the repository working directory. The generator therefore writes
relative paths back to each original source file.

Run `make web-warcraft3-preflight` to validate the source groups and generate
unity inputs without invoking Emscripten. Then run `make web-warcraft3-engine`
with an activated SDK and capture the **first** compiler or linker failure.
The preflight checks file existence and include layout only; it cannot prove
that the browser code links, renders or boots. Do not redistribute game data.

### Browser build compatibility (wasm32)

The experimental engine build excludes `g_save.c` and links browser-only
`web_save_unsupported.c` functions returning failure. WC3 save/load is therefore
**unsupported** in this build: `g_save.c` encodes 64 bits of relocation data into
a pointer-sized slot, and wasm32 pointer slots are only 32 bits wide. The native
save format and its assertions remain unchanged. A browser save implementation
must use explicitly sized on-disk relocation records and regression coverage
before enabling this feature.

Browser builds also exclude `BZ_CLIENT_WORLD` from the combined game/engine
compilation flags; server/game routing owns the WC3 pathing implementation,
while client-world helpers must not be compiled into the game unity module.
`-sWASMFS=1` is a final-link setting, not a compile-only setting.

### Static WASM module symbol ownership

The native `libgame` and `libmenu` each compile their own
`stb_fdf.h` implementation, `frames` registry and host callbacks. These
must remain distinct in the browser's single linked executable. The
browser-only `web_fdf_namespace.h` provides module-scoped link names when
compiling game and menu; `GetGameAPI` and `M_GetAPI` are not renamed.

`games/warcraft-3/common/campaign_progress.c` is pure shared functionality:
it is now compiled exactly once as `wc3_common.o`, rather than being
repeated in both game and menu objects. `world_w3.c` remains owned by
the engine object. These decisions do not change native shared libraries.

### WASM FDF parser symbol ownership

The Warcraft III game and menu are separately linked native modules and
independently instantiate `stb_fdf.h` with `STB_FDF_IMPLEMENTATION` and
`STB_FDF_GLOBALS`. The parser uses module-specific `UI_*` callbacks and
separate `frames` and `strings` registries. Both instances must remain
independent in the static WASM binary. `port/web/src/web_fdf_namespace.h`
renames the parser functions, enum tables and state together with the UI
helpers for the game/menu unity objects. It is deliberately not applied to
the universal engine or native builds. Sharing one complete FDF parser between
game and menu would incorrectly bind its state and host callbacks to one
module.

### Text batching and the browser thread stack

A symbolized main-menu frame crash reached `process_text` through
`R_DrawText` and `R_GetTextSize` after the renderer and UI had initialized.
The previous `textBatch_t` included 1,020 vertices as a local variable even
while measuring text (when no drawing or batching occurs). Nested alignment
measurement therefore placed unnecessarily large vertex arrays on the limited
WebAssembly engine pthread stack. The renderer now allocates the batch through
`ri.MemAlloc` only for drawing, flushes it, and frees it before returning.
Measurement still uses the same positioning and glyph-advance logic without
allocating a batch. Native rendering and text output should remain unchanged.

### Renderer on the browser engine worker

The browser build uses `PROXY_TO_PTHREAD` for OPFS, but SDL creates its GL
context through EGL. Emscripten proxies EGL context creation to the main
thread, so the HTML canvas must stay there. Browser builds use the
`OFFSCREEN_FRAMEBUFFER` rendering path instead of transferring the canvas to
the worker. Emscripten owns frame timing; native swap-interval behavior is
unchanged. COOP/COEP cross-origin isolation is required for pthreads.

### SDL/EGL context ownership on browser pthreads

The engine uses `PROXY_TO_PTHREAD` for WasmFS OPFS. SDL creates the renderer
context through EGL, and Emscripten's EGL context operations are proxied to
the browser main thread. Do **not** combine this SDL/EGL path with transferring
`#canvas` to the pthread: the main-thread EGL implementation then attempts
`getContext()` on an already-transferred HTML canvas and throws
`InvalidStateError`. The browser link deliberately uses
`-sOFFSCREEN_FRAMEBUFFER=1` without `OFFSCREENCANVAS_SUPPORT` or
`OFFSCREENCANVASES_TO_PTHREAD`, leaving the canvas on the main thread while
allowing the worker to submit WebGL operations through Emscripten's proxy.
COOP/COEP isolation is still necessary for pthreads. This resolves the
canvas-ownership conflict in configuration; WebGL rendering remains to be
validated on the target Emscripten SDK and browser.

### Direct WebGL context for browser renderer

The browser renderer uses Emscripten's HTML5 WebGL API directly instead of
creating and swapping a context through SDL/EGL on the proxied game pthread.
SDL still owns the window and input. WebGL 2 uses
`EMSCRIPTEN_WEBGL_CONTEXT_PROXY_ALWAYS` and explicit swap control; the
`-sOFFSCREEN_FRAMEBUFFER=1` link setting supplies the presentation buffer.
Native rendering remains unchanged. This is an experimental interoperability
fix requiring runtime verification of GL initialization, frame presentation,
resize and input handling.

### Worker-owned WebGL context (follow-up)

Direct WebGL context creation in the browser renderer still deadlocked with
`EMSCRIPTEN_WEBGL_CONTEXT_PROXY_ALWAYS` after shader loading: a synchronous GL
proxy on the engine pthread can enter a recursive pthread mutex lock. The
browser build now transfers `#canvas` to the engine pthread with
`OFFSCREENCANVAS_SUPPORT`/`OFFSCREENCANVASES_TO_PTHREAD`, and the renderer
requests `EMSCRIPTEN_WEBGL_CONTEXT_PROXY_DISALLOW`. The renderer continues to
create the context directly via Emscripten, **not** via SDL/EGL; this distinction
avoids the earlier transferred-canvas EGL error. No native build changes.

Requires a cross-origin-isolated page and OffscreenCanvas support. Test worker
context creation, shader/resource initialization, frame presentation, resize,
input and shutdown in the browser; a successful C link alone is insufficient.

### Diagnosing browser worker traps

The normal optimized build omits useful names from WASM stack traces. When
startup reaches `Loading shaders succeeded` but a worker fails with
`memory access out of bounds`, `operation does not support unaligned accesses`,
or an Emscripten pthread/proxy-queue assertion, **do not** assume the renderer
or OPFS is the original cause from the last successful log line alone. A
secondary worker failure can follow a primary engine-thread failure.

Build a separate, unoptimized DWARF-symbolized version with:

```sh
source ~/emsdk/emsdk_env.sh
python3 port/web/build-engine.py --debug
```

The result is in `build/web/engine-debug/`; it leaves the standard
`build/web/engine/` untouched. Serve the debug directory using the same
cross-origin isolation headers as the normal pthread build. In Chrome DevTools
(Sources), use WebAssembly DWARF debugging to inspect the **first** failing
thread, its C call stack and source line. Include the failing assertion and
first symbolic stack in the issue report. If needed, use the DWARF-capable
`llvm-addr2line` shipped with the Emscripten SDK against the exact matching
`index.wasm` and the `index.wasm:0x...` offsets; offsets from optimized builds
cannot be looked up in a different debug binary.

Keep pthread checks enabled. Do not mask WebAssembly traps by relaxing
alignment, disabling mutex assertions or suppressing errors in proxy queues.

### Procedural textures and the browser thread stack

The symbolized startup trace identified a stack overflow in
`R_MakeLoadingIndicatorTexture` immediately after shader initialization. Its
128×128 RGBA scratch image previously occupied 64 KiB of the engine thread
stack. The selection-circle generator had the same allocation shape, and the
blob-shadow generator used another stack-allocated RGBA buffer. These buffers
now use the renderer's existing `ri.MemAlloc`/`ri.MemFree` lifetime around
`R_LoadTextureMipLevel`, matching normal texture upload ownership. The pixels,
texture formats, and non-browser rendering behavior are unchanged.

The change avoids needing to increase the default pthread stack solely for
these temporary images. Recheck browser startup after shader loading; other
large local buffers might still need their own targeted fixes.

### Browser sound initialization (temporary limitation)

The browser executable uses `PROXY_TO_PTHREAD`, placing engine startup on a
worker. SDL 2's Emscripten audio device setup currently accesses JavaScript
`audioContext` state that is unavailable in that worker and throws before
client initialization completes. For now `S_Init` declines to initialize audio
on Emscripten and preserves the normal uninitialized-sound guards. The native
SDL audio path remains unchanged. Browser playback is intentionally silent.

Restore browser sound with a dedicated browser audio adapter or a verified
main-thread initialization and mixing bridge; do not call the standard SDL
Emscripten audio device opener from the engine worker. Verify the next browser
startup stage with both debug and release builds.

### Bundled Warcraft III defaults

The browser engine link embeds the open-source `games/warcraft-3/share/`
folder under the virtual filesystem path `/share/warcraft-3/`. In particular,
`/share/warcraft-3/config.cfg` must be present when `Com_Init` reads the
shipped input bindings (`MOUSE1` selection, `MOUSE2` smart orders, etc.).
`build-engine.py --check` checks that the source config exists; the normal
`emcc` link bundles it using `--preload-file`. Rebuild the browser engine after
changing shared defaults. These files are not copied to OPFS or uploaded by
users.

This built-in configuration is the read-only starting point; user config
loading and persistence are separate concerns. If HUD clicks work while
world selection/drag/orders do not, verify this bundle is included before
investigating mouse hit-testing.

### JASS callback stack usage

JASS filter, player-filter, AI integer callback, and trigger-condition evaluation
copy a full VM state to isolate callback context. These scratch VMs live on the
engine heap, not its limited WebAssembly pthread stack. In particular,
`GroupEnumUnitsOfPlayer` may evaluate many filtered units during campaign map
initialization. Allocation failures reject the corresponding filter or condition
without modifying the parent VM state.

### Browser audio (AudioWorklet)

On Emscripten the existing 44.1 kHz stereo S16 mixer feeds a dedicated
producer pthread under a sound mutex (not SDL's browser audio device).
The producer publishes samples to a shared Wasm memory ring; an AudioWorklet
consumes them on the browser's real-time audio thread and resamples to the
AudioContext output rate. The first user gesture unlocks AudioContext.
The audio worklet script is copied alongside index.js by the browser build.
The native SDL backend is unchanged. Verify playback for UI sounds, positional
unit acknowledgements, dialogue and music; also verify tab suspend/resume,
loading stalls and output-device sample rates. Audio may underrun during stalls.

## Two-map standalone build (apricot and peach)

`make web-warcraft3-engine` builds a standalone page that plays only
`apricot.w3x` and `peach.w3x`. The page is `maps.html` (a picker) and launches
the engine through `filesystem-bridge.js`, which only accepts map names on its
`BUNDLED_MAPS` allowlist.

Setup:

- Stage the retail archives and the two maps in `port/web/data-input/`
  (gitignored). The current staged files are `war3.mpq` (a copy of
  `persimmon.mpq`), `War3x.mpq` (a copy of `tangerine.mpq`), `War3Patch.mpq`,
  `War3xLocal.mpq`, and `Maps/Download/{apricot,peach}.w3x`. SHA-256 checks
  match all four staged archives to their source files in the workspace.
  These copies do not establish that the original base archives are present;
  see the data audit below.
- The data is preloaded into `/data/warcraft-3` with `--preload-file`. The
  data package is about 130 MiB with the basic assets. Emscripten SDK 6.0.9 is
  installed locally at `~/.local/src/emsdk`; activate `emsdk_env.sh` before building.
- The build automatically runs `port/web/generate-basic-assets.py`. At the
  owner's request this supplies 227 original basic assets (terrain, UI, font,
  icons, primitive models and rectangular pathing masks). It preserves maps,
  archives, and edited/non-generated loose files. See [basic asset pack](../../port/web/README.md).
- Serve locally with `python3 port/web/serve.py`, then open
  `http://127.0.0.1:8000/maps.html`. The server sends required COOP/COEP headers.
  The launcher disables the desktop automatic-fullscreen default; the page
  fullscreen button explicitly controls that transition. The Maps link reloads
  the picker to switch maps or restart without entering the native main menu.
- The picker fills other slots with simple bots by default; **Leave empty**
  disables them. See [standalone map bots](browser-bots.md) for policies and
  the native opt-in setting. The original tutorial and match rules still apply.
- The launcher passes `-tft`. RoC hides the `War3x*` archives, and the Loading
  and StandardTemplates FDFs live there, so the engine cannot reach the map
  without TFT mode.

Browser requirement: WebGL 2. The VS Code integrated browser has no WebGL and
cannot run the engine. Use a current desktop Chrome or Firefox.

Current verification (2026-10-17): both maps render terrain and a basic HUD
in headless Chrome/WebGL 2, with no JavaScript exceptions or WASM traps in
startup/selection checks. Apricot vendor selection shows unit details and
command buttons. Peach reaches its scoreboard and both authored browser result
actions display the correct Victory/Defeat dialogs. These result-action checks
bypass objective predicates; native objective checks are described below.
Peach browser clicks dismiss the round dialog, open the hero skill menu and
move the selected runner through normal right-click orders.
The full `make test` suite and native WC3/WoW/SC2 builds pass. The browser link
retains the expected pthread/memory-growth performance warning.

The previous black-view report combined missing art with a client input bug:
zero-initialized mouse coordinates continuously scrolled toward the map corner.
The shared client now waits for a pointer sample and invalidates it on window
leave/focus loss. Both are covered by input regressions. A temporary native
renderer diagnostic also proved fog sampling affected the black scene; the old
`r_fogofwar 0` experiment did not disable an already-uploaded network fog
texture. Do not treat that earlier experiment as ruling out gameplay fog.
Apricot deliberately gives its starting buildings small sight patches; much of
the map remains black until explored. Its zombie hero spawns after 90 seconds.

Known limitations:

- The original install is partial; generated art makes it inspectable and
  usable as a basic demo, not a faithful retail presentation. Models are static
  proxies, some cliffs/water/effects remain absent, and audio is incomplete.
- Save/load remains unsupported on wasm32. Native save format is now version
  90, covering event-capacity/token and camera-rotation state changes; older
  native saves are explicitly rejected. Network formats are unchanged.
- Native objective checks reached Apricot victory through ordinary commands
  and a five-round Peach bot match through its original scoring rules. Browser
  end-to-end objective playthroughs remain unverified. Remaining map-script gaps
  are recorded in [two-map compatibility](two-map-compatibility.md), including
  chat-event placeholders and partial scripted damage semantics.
- Apricot has no `war3mapUnits.doo`; its units come from `scripts/war3map.j`.
  Peach contains `war3mapUnits.doo` and its root script is `war3map.j`.

### Staged-data audit (2026-10-17)

`FS_AddDataDirectory` (`common/common.c`) recursively mounts every staged MPQ;
`-tft` makes both `War3x*` archives visible. The extra patch/local archives
are already staged and cannot be recovered merely by mounting them again.
Direct `mpqtool cat` probes across all four archives found 7 of the 29 FDF
dependencies referenced by `games/warcraft-3/game/generated/*.h`. Missing
dependencies include `ConsoleUI.fdf`, `ResourceBar.fdf`, `UpperButtonBar.fdf`,
`EscMenuTemplates.fdf`, `EscMenuMainPanel.fdf` and `GameResultDialog.fdf`.
`GlobalStrings.fdf` and several localized panels are present, but do not
provide those missing frame definitions.

Reading each map's W3E tile IDs and resolving them through the staged
`TerrainArt\Terrain.slk` confirms that all nine Apricot ground BLPs
(`TerrainArt\DalaranRuins\DRuins_*.blp`, tileset J) and all seven Peach
ground BLPs (six `TerrainArt\LordaeronSummer\Lords_*.blp` plus
`TerrainArt\Cityscape\City_WhiteMarble.blp`, tileset L) are absent from the
four staged archives. `TerrainArt\CliffTypes.slk`, `TerrainArt\Water.slk`,
`PathTextures\xDefault.tga`, and nested `J.mpq`/`L.mpq` are also absent.
These findings describe the original archives before the owner-approved
basic pack was generated. Loose generated assets now supply selected missing
paths; the original archives are unchanged.

Reproduce representative checks from the repository root; each command
searches each original archive explicitly, excluding the generated loose files:

```sh
for archive in port/web/data-input/*.mpq; do
  build/bin/mpqtool -mpq "$archive" cat UI/FrameDef/UI/ConsoleUI.fdf > /dev/null
  build/bin/mpqtool -mpq "$archive" cat TerrainArt/Water.slk > /dev/null
done
```

`../REA/lime-filename-findings.json` and `../REA/REPORT.txt` record retail
`lime.dll` strings referencing **both** `persimmon.mpq`/`tangerine.mpq` and
`War3.mpq`/`War3X.mpq` (Evidence
`ev_f064a80a3cc067fe3c9debae5a77ee9342d2c81a848f854692a7726db4a5bdbd`).
This supports treating the renamed files as supplemental archives, rather
than assuming they replace the base data. Static strings do not establish
retail mount order. No original base `War3.mpq`/`War3X.mpq` exists in the
workspace or its `Warcraft III/` install folder; the latter's patch/local
archives match the staged copies. Complete base archives would restore retail presentation. The owner instead
requested original basic terrain and UI, so the browser generator supplies
explicit substitute assets. Archive and map-import precedence remain intact;
the substitutions and gameplay limitations are documented in the basic pack README.

Load-time fix: `common/mpq.c` used to re-inflate an entire compressed sector
or single-unit file on every small `SFileReadFile` call. Map readers issue many
small reads, so a map load took roughly 90 seconds per load, and the
120-second loading plaque timed out before the first frame. Each file handle
now caches its last decoded sector (`sector_cache`) and single-unit payload
(`unit_cache`). Apricot now reaches `G_ClientBegin` normally.
