# Two-map browser assets

The local archives omit terrain art, HUD definitions, fonts, pathing textures,
and some stock models. The user explicitly requested simple generated assets.
`generate-basic-assets.py` supplies that optional pack as loose game data; it
does not modify either map, their scripts, or any MPQ archive. The browser build
runs it before packaging `data-input/`.

```sh
python3 port/web/generate-basic-assets.py
make web-warcraft3-engine
python3 port/web/serve.py
```

Use `--output DIRECTORY` to generate a separate pack. Generation needs Python 3
and the DejaVu Sans package (`fonts-dejavu-core` on Debian/Ubuntu). `--font PATH`
can supply another local TrueType font. The default copies DejaVu Sans, plus its
copyright/license, to the existing `Fonts/FRIZQT__.TTF` alias because the
imported `MasterFont` skin already uses that path. DejaVu's internal font name
and bytes are preserved.

The pack contains:

- Sixteen original 64x64 terrain atlases at the paths named by `Terrain.slk`,
  plus the Dalaran Ruins and Lordaeron Blight atlases from `WorldEditData.txt`.
  Each atlas has 4x4 transition cells; mask 0 is transparent and mask 15 opaque.
- Plain FDF HUD, pause/end-game/save dialogs, game-result dialogs, quest/log
  windows, cinematic letterboxing and JASS choice dialogs. Named frame trees
  follow the checked-in game binding headers. Present retail FDF files,
  including `SimpleInfoPanel`, localization and options, remain in the archives.
- Original simple UI textures, selection rings, sixteen team colors and glows.
  `basic-ui-textures.txt` records UI paths confirmed absent during the two-map
  runtime checks. Missing command icons use distinct original category glyphs
  (book, ring, orb, shield, helmet, tower, ankh and wand), with muted colors for
  unavailable/disabled commands. Only paths reported missing are supplied.
- Static team-colored pyramids for missing stock units/buildings, and green
  pyramids for ten tree variants, a shrub, rushes and lily pads. These are
  visible proxies, with named static animation sequences; they do not reproduce
  the original models or animated poses. Map imports retain renderer precedence.
- Rectangular pathing TGAs for `2x2Default`, `4x4Default`, `12x12Simple` and
  `12x12TreeOfLife`. Dimensions are pixels, each spanning 32 world units. All
  block walking/construction; the Tree of Life also blocks flying. These simple
  footprints intentionally approximate the unavailable authored masks.

Textures use native uncompressed BLP2 BGRA. An explicit `.blp` reference never
tries a `.tga` sibling, so writing TGA art at a different extension does not fix
missing ground textures. Pathing uses native uncompressed 24-bit TGA.

Generated files and `basic-assets-manifest.json` live under ignored
`port/web/data-input/`. The manifest records hashes. A rerun can update its own
unchanged files and refuses to overwrite edited or non-generated loose assets;
it checks every target before writing. Existing loose fonts are preserved.
The pack does not supply every missing sound, effect, cliff or water asset.

Run the focused checks with the same native include environment used by the
project build:

```sh
python3 tests/test_web_basic_assets.py
```

They exercise the production FDF parser and all generated C frame bindings,
clone JASS dialogs, decode each primitive shape through the native MDX readers,
decode the footprints through `LoadTGA`, verify atlas masks and repeatability,
and confirm imported archives and edited loose files survive regeneration.
Native SDL/OpenGL development headers are required by the MDX-reader check.

The broader browser setup and limitations are documented in
[Browser platform](../../docs/platform/browser.md).
