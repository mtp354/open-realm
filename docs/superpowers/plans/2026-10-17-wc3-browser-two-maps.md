# Warcraft III Browser Build: Two Maps Implementation Plan

**Goal:** Build the existing OpenRealm Warcraft III engine to WebAssembly, with a bare picker page that starts `apricot.w3x` or `peach.w3x`, and fix the runtime gaps those two maps hit until both reach normal play.

**Architecture:** Reuse the Emscripten route already in `port/web/`. `port/web/build-engine.py` compiles the engine units, `port/web/build.mk` exposes the make targets, and `port/web/site/` holds the page. Retail archives and the two maps are embedded into the virtual filesystem at build time. Gap fixes are made in the shared C source so the native build keeps its behavior.

**Tech stack:** C (C11), Emscripten (emsdk, pinned version), GNU make, Python 3, plain HTML/JS for the picker, the native test runner from `games/warcraft-3/game.mk`.

**Spec:** [2026-10-17-wc3-browser-two-maps-design.md](../specs/2026-10-17-wc3-browser-two-maps-design.md)

## Global constraints

- Work in `/home/matt/Projects/Game/open-realm`. Commit to its current branch with the Co-authored-by trailer.
- Never commit retail archives or the maps. `War3.mpq` is already ignored in `.gitignore`. Add ignore lines for `*.mpq` and `*.w3x` under `port/web/` build inputs if they are staged there, and keep staging outside tracked paths.
- Gap fixes are limited to what apricot and peach hit at runtime. No speculative features.
- Keep native behavior unchanged: after every gap fix, the native build and its tests must still pass.
- Comments only where a line needs clarification.
- Use REA evidence (`/home/matt/Projects/Game/REA/`) to confirm an original behavior before changing code that depends on it. Record the evidence name in the commit body.

## Review focus

- Spec coverage: picker shows exactly two maps, both start without manual steps, play reaches the win/loss condition, no console errors or wasm traps, native tests still pass, every gap commit names its map and behavior.
- The browser build reads data through the existing `+openrealm-data=` path. The picker must not require the installer flow.
- The `map` cvar and `SV_Map` start path must be the same one the native build uses.

## File map

| Path | Role |
|---|---|
| `port/web/build-engine.py` | Emscripten compile and link. Add embedded archive and map staging. |
| `port/web/build.mk` | Make targets. Add a target that stages data and builds. |
| `port/web/site/engine-shell.html` | Engine page. Replace the probe UI with the two-map picker. |
| `port/web/site/picker.js` | New. Picker logic: list two maps, start one by URL argument. |
| `docs/platform/browser.md` | Update build status and how to run. |
| `games/warcraft-3/menu/menu_map_data.c` | Read if the two-map list needs a filter. |
| `games/warcraft-3/game/g_spawn.c` | Map load path. Touched only for gap fixes. |
| `games/warcraft-3/jass-native-coverage.md` | Update placeholder counts for natives fixed. |

## Task 1: Commit the approved design spec

**Files:** `docs/superpowers/specs/2026-10-17-wc3-browser-two-maps-design.md`

- [ ] Stage only `docs/superpowers/`. Commit with message `Add two-map browser build design spec` and the trailer.
- [ ] Verify with `git status --short` that nothing else is staged.

## Task 2: Install and activate emsdk

**Files:** none in the repo. Install under `~/.local/src/emsdk`.

- [ ] Clone emsdk to `~/.local/src/emsdk` and install a pinned release (choose the latest stable tag at install time and record it in `docs/platform/browser.md`).
- [ ] Run `./emsdk install <tag>` and `./emsdk activate <tag>`.
- [ ] Verify with `source ~/.local/src/emsdk/emsdk_env.sh && emcc --version`. Expected: a version line.

## Task 3: Baseline the native build and tests

**Files:** none.

- [ ] Run `make build` in `open-realm`. Expected: success. If SDL2 or GL headers are missing, install them with apt and rerun.
- [ ] Find the test target name by reading `games/warcraft-3/game.mk` and the `test_schema` usages. Run the warcraft-3 test suite. Record pass/fail counts as the baseline.
- [ ] If any test fails before any change, record it in the browser docs as pre-existing and do not fix it.

## Task 4: Run preflight and the first browser compile

**Files:** none yet.

- [ ] Run `make web-warcraft3-preflight`. Expected: generated sources validate with no errors.
- [ ] Run `make web-warcraft3-engine` with emsdk active. Record the first compile or link error, verbatim, in a scratch note under the session files folder, not in the repo.
- [ ] Fix only build breakage needed to produce `index` / `.wasm` output. Commit each fix separately with a message that names the cause.

## Task 5: Stage the retail archives and the two maps into the virtual filesystem

**Files:** `port/web/build-engine.py`, `port/web/build.mk`.

The current build embeds only `games/warcraft-3/share` at `/share/warcraft-3`. The engine reads data from the directory given by `+openrealm-data=`. Keep the same interface.

- [ ] Add an input directory variable, default `port/web/data-input/`, that is ignored by git. Copy into it: `persimmon.mpq`, `tangerine.mpq`, `War3Patch.mpq`, `War3xlocal.mpq`, `apricot.w3x`, `peach.w3x`. Use the owner's copies from `/home/matt/Projects/Game`.
- [ ] Add `--embed-file <input-dir>@/data/warcraft-3` (or the exact layout the engine expects, found by reading `common/main.c` around line 430 and the archive lookup in `common/common.c`).
- [ ] Verify the staged layout: `emcc` links without `-sFORCE_FILESYSTEM` errors and the `.data` package lists the six files.
- [ ] Commit with message `Embed retail archives and two maps into the browser build`.

## Task 6: Two-map picker page

**Files:** `port/web/site/engine-shell.html`, `port/web/site/picker.js`.

- [ ] Replace the probe UI in `engine-shell.html` with a page that shows exactly two buttons: `apricot` and `peach`. Each button starts the engine with `+openrealm-data=/data/warcraft-3` and the map selection argument.
- [ ] Determine the exact argument that starts a map directly. Check `games/warcraft-3/menu/menu_main.c` (the `map` cvar near line 394) and `g_spawn.c` (the `map` cvar near line 842). If the engine only supports the menu path, add a `+map=<file>` handling in `common/main.c` next to the `+openrealm-data=` parse. This is a shared change, so run the native tests after it.
- [ ] Add `picker.js` only if the logic does not fit in the page. Keep it under 80 lines.
- [ ] Commit with message `Add two-map browser picker`.

## Task 7: Verify each map loads in the browser

**Files:** none.

- [ ] Serve the build directory with a static server (`python3 -m http.server` in the build output directory).
- [ ] Open the page with the browser tools. Click `apricot`. Record console errors and wasm traps. Take a screenshot.
- [ ] Repeat for `peach`.
- [ ] Each failure becomes one gap item for Task 8.

## Task 8: Gap loop, one item at a time

Repeat until both maps reach normal play.

- [ ] Identify the first failing item from the console or the first placeholder native a map calls. Use `games/warcraft-3/jass-native-coverage.md` to look up the native's status.
- [ ] Look up the original behavior in REA evidence (`REA/evidence/`, `REA/REPORT.txt`). Write the evidence name in the commit body.
- [ ] Write a failing native test under `games/warcraft-3/tests/` where the logic is testable on native. Run it and confirm it fails.
- [ ] Implement the minimal fix in the shared C source.
- [ ] Run the native test suite and confirm it passes, with no new failures compared to the Task 3 baseline.
- [ ] Rebuild the browser target and rerun the map in the browser.
- [ ] Commit with message `Fix <native or behavior> for <map>` and a body that names the map, the behavior, and the REA evidence.

## Task 9: Win and loss condition check

**Files:** none unless a gap is found.

- [ ] Play each map to its win or loss condition. For apricot and peach, read their `war3map.j` trigger conditions to know what that means. Treat a map that ends with a native placeholder as a gap and return to Task 8.
- [ ] Record the result for each map in `docs/platform/browser.md`.

## Task 10: Documentation

**Files:** `docs/platform/browser.md`, `games/warcraft-3/jass-native-coverage.md`.

- [ ] Update `docs/platform/browser.md` with: the emsdk version, the build command, how to serve the page, and the two-map status.
- [ ] Update the placeholder counts in `jass-native-coverage.md` for natives fixed in Task 8.
- [ ] Commit with message `Document two-map browser build`.

## Task 11: Final verification

- [ ] Run `make build` and the warcraft-3 test suite. Compare to the Task 3 baseline.
- [ ] Run `make web-warcraft3-engine` from a clean build directory.
- [ ] Open the picker in the browser. Both maps start without manual steps. No console errors. Screenshot both.
- [ ] Remove scratch files created outside the repo, and confirm `git status` shows no retail archives or maps staged.
