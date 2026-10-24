# OpenGameArt browser pack

The two-map browser edition adds an explicit CC0 artwork pack under
`port/web/art-input/`. Both Apricot (Troopers Vs Zombies) and Peach (Capture the
Flag) use it. [Browser setup](browser.md) covers serving, WebGL and runtime
limitations; [two-map compatibility](two-map-compatibility.md) covers the authored
rules and existing engine gaps.

## Asset ownership and integration

`build-engine.py` calls `generate-basic-assets.py --art
port/web/art-input/catalog.json`. The generator creates its basic file set,
then overlays the catalog's native bytes before checking every target against
the prior `basic-assets-manifest.json`. Catalog entries contain relative source
paths and SHA-256 hashes. They may replace only generated missing resources or
add files under `OpenArt/`; maps, archives and unrelated loose files are outside
this contract. Every hash is checked before writing. Edited generated assets
and non-generated loose files still stop the build.

The renderer searches scoped map imports and archives before loose data. This
pack fills the known missing stock paths; it does not replace authored imports.
Neither map archive, JASS script, object stats, footprint nor gameplay rule is
modified. The generated FDF and command profiles keep the existing binding
names, positions, localized strings and command handlers. The same pack is
preloaded into both maps.

## Installed artwork

| Surface | Conversion and use |
| --- | --- |
| Terrain | DevEarley's Ancient Civ. grass, dirt, stone and concrete textures. Eighteen 256x256 native BLP2 atlases retain the existing 4x4 corner-mask topology: cell 0 transparent, cell 15 opaque. Source texture repeats in each 64px cell, so transition alpha and map tile UVs remain connected. |
| Trees and plants | Ten Kenney Nature Kit tree variants plus bush, rushes and lily. OBJ geometry/materials become MDX800 with native BLP2 textures. Tree Death flattens to a stump; Birth restores its original height through the existing root-scale track. |
| Camp buildings | Two Nature Kit tents replace the missing Graveyard, TombOfRelics, SpiritLodge and Marketplace proxies. They retain the original gameplay objects and footprints. |
| Characters | Quaternius warrior at Footman, Irondust soldier at Militia, and Kenney zombie at Ghoul. These aliases affect missing stock models; map-imported characters remain authored. |
| HUD and commands | Kenney Adventure and Sci-Fi UI sprites plus Game Icons. Disabled command art is desaturated/darkened. HUD backdrops are darkened to retain contrast with light labels. Border interiors stay transparent; black cinematic overlays remain the original solid textures. Human/Ancient ground decals use soft-alpha dirt/stone textures instead of missing-texture checkerboards. |
| Picker and loading | Full Kenney Nature Kit and Animated Characters 3 previews, resized as JPEG without cropping their creator footer. Preview captions identify source-pack artwork, rather than implying these are game screenshots. |

The warrior and soldier are static converted meshes: their sequence names are
aliases, not skeletal walk/attack animation. The zombie has sampled Idle/Run
motion at 30Hz, with MDX800 weights approximated in quarter increments. Stand
uses Idle and Walk uses Run; Attack/Portrait/Birth/Stand Work reuse Idle, and
Death uses an adapter-authored shrink. These are visual limitations, not new
combat rules. Models retain source colors; selection rings and UI still show
team ownership. The original team-colored capture-flag proxy is retained.

## Sources and licenses

`CREDITS.txt`, `licenses/`, `image-provenance.json`, `image-conversions.json` and
`model-provenance.json` record authors, source pages, download URLs, original
archive/member hashes where available, conversion details and runtime aliases.
Only the used converted assets and small web images are installed. Full ZIPs,
unused models, alternate skins and Blender scenes are omitted. These licenses
apply to the added art; they do not license the bundled Warcraft III data.

The native pack uses real MDLX version 800 models and uncompressed BLP2 BGRA
textures. Merely renaming OBJ/PNG files would not work: the renderer does not
load OBJ and an explicit BLP path does not try a PNG or TGA sibling. Conversion
was offline using Python/Pillow and Blender; the installed catalog can be
regenerated with Python's standard library and the existing font package.

The browser builder copies `art-input/web/`, credits and licenses beside the
engine as `art/`. It also preloads credits/licenses under `OpenArt/` with the
game data. No third-party request is required when playing locally.

## Verification and handoff

Baseline and final validation use `make -j4 test` with the local SDL development
include/library environment. `tests/test_web_opengameart.py` checks source hashes,
model texture dependency closure, native BLP layout and terrain corner masks,
production MDX loading, tree death/regrowth interpolation, and protection of
map files and edited assets during repeat generation. `test_web_engine_build.py`
checks both loading-art choices, status completion, and browser capability
failure handling. A successful loader check does not establish visual quality
or a complete gameplay playthrough.

The framebuffer gap is checked separately in bounded browser runs of both maps
after the WebAssembly build. Compatibility remains experimental; existing
missing effects/audio and other gaps are listed in the browser guide.

The cleaned handoff retains the `open-realm/` source repository, canonical
`port/web/data-input/`, this licensed pack, and the final `build/web/engine/`
runtime. Obsolete Windows executables/DLLs, duplicate maps/archives, the nested
original-game backup, old REA output, debug browser output and build
intermediates are removed. Git history and source fixtures remain available for
rebuilding. Launch from the parent folder with `./play.sh`, or run
`python3 port/web/serve.py` inside OpenRealm, then open
`http://127.0.0.1:8000/maps.html`.

### Completed local verification (2026-10-24)

The final `make -j4 test` passed all 32 printed native suite summaries and
66 Python tests (umbrella totals can include recursively repeated suites).
The optimized Emscripten build linked. Both final-package browser startup checks
used cross-origin isolation and rendered the new terrain/trees/UI with no
JavaScript exceptions, WASM traps or failed network requests. The loading
artwork hid when loading completed. Screenshots exposed light HUD backdrops
and missing Human/Ancient decals; the pack now has dark readable backdrops and
soft-alpha ground decals, covered by the art regression suite. Remaining
missing stock effects/models and incomplete audio are still the existing
partial-install limitations. These checks are not new full-match playthroughs.

All 283 preloaded data-file byte ranges in `index.data` were compared to their
canonical inputs. Both map hashes match the originals. The final browser
runtime is about 130 MiB including its small web artwork and license records.
