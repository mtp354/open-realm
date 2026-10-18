"""Validate generated browser assets through the production FDF parser."""
import importlib.util
import configparser
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("basic_assets", ROOT / "port/web/generate-basic-assets.py")
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)

PARSER = r'''
#include <stdlib.h>
#define STB_FDF_IMPLEMENTATION
#define STB_FDF_GLOBALS
#include "games/warcraft-3/common/stb_fdf.h"
handle_t UI_FdfAlloc(long size) { return calloc(1, size); }
void UI_FdfFree(handle_t data) { free(data); }
uint32_t UI_FdfFontIndex(cstring_t name, uint32_t size) { return 1; }
uint32_t UI_LoadTexture(cstring_t file, bool decorate) { return 1; }
uint32_t UI_LoadModel(cstring_t file, bool decorate) { return 1; }
cstring_t Theme_String(cstring_t key, cstring_t fallback) { return fallback; }
float Theme_Float(cstring_t key, cstring_t fallback) { return 0; }
void UI_WireFrameTypeFunctions(frameDef_t *frame) {}
void UI_ClearTheme(void) {}
int UI_FdfReadFile(cstring_t name, handle_t *out) { *out = NULL; return -1; }
void UI_FdfFreeFile(handle_t data) { free(data); }
static void check(int ok, cstring_t name) { if (!ok) { fprintf(stderr, "Invalid frame: %s\n", name); exit(1); } }
int main(int argc, char **argv) {
    for (int i = 1; i < argc; ++i) {
        FILE *file = fopen(argv[i], "rb"); check(file != NULL, argv[i]);
        fseek(file, 0, SEEK_END); long len = ftell(file); rewind(file);
        char *buffer = calloc(1, len + 1); check(fread(buffer, 1, len, file) == len, argv[i]); fclose(file);
        UI_ParseFDF_Buffer(argv[i], buffer); free(buffer);
    }
    frameDef_t *root = UI_FindFrame("ConsoleUI"); check(root != NULL, "ConsoleUI");
    frameDef_t *value = UI_FindFrame("ResourceBarLumberText");
    frameDef_t *heading = UI_FindFrame("BasicResourceLumberLabel");
    check(value && heading && heading->Parent == value, "resource heading follows value visibility");
    const char *buttons[] = { "UpperButtonBarMenuButton", "GameResultContinueButton", "ScriptDialogButton", "ReturnButton", "ConfirmQuitQuitButton", NULL };
    for (int i = 0; buttons[i]; ++i) {
        frameDef_t *b = UI_FindFrame(buttons[i]); check(b != NULL, buttons[i]);
        check(b->Type == FT_GLUETEXTBUTTON && b->Width > 0 && b->Height > 0 && !b->disabled, "interactive button geometry");
        check(UI_FindChildFrame(b, b->Control.Backdrop.Normal) != NULL, "button backdrop");
        check(UI_FindChildFrame(b, b->Text) != NULL, "button label binding");
    }
    frameDef_t *source = UI_FindFrame("ScriptDialog"); check(source != NULL, "ScriptDialog");
    frameDef_t *clone = UI_CloneFrameTree(source, NULL); check(clone != NULL, "ScriptDialog clone");
    check(UI_FindChildFrame(clone, "ScriptDialogText") != NULL, "ScriptDialogText");
    check(UI_FindChildFrame(clone, "ScriptDialogBackdrop") != NULL, "ScriptDialogBackdrop");
    UI_FreeFrameTree(clone);
    return 0;
}
'''

MODEL_PARSER = r'''
#include "games/warcraft-3/renderer/mdx/r_mdx_load.c"
#include "games/warcraft-3/renderer/mdx/r_mdx_interpolation.c"
#include "games/warcraft-3/renderer/mdx/r_mdx_anim.c"
#include "shared/source/vector3.c"
#include "shared/source/quaternion.c"
refImport_t ri;
struct render_globals tr;
uint32_t SDL_GetTicks(void) { return 0; }
static handle_t allocate(long size) { return calloc(1, size); }
int main(int argc, char **argv) {
    ri.MemAlloc = allocate; ri.MemFree = free;
    FILE *file = fopen(argv[1], "rb"); if (!file) return 1;
    fseek(file, 0, SEEK_END); long len = ftell(file); rewind(file);
    uint8_t *data = calloc(1, len); if (fread(data, 1, len, file) != len) return 2; fclose(file);
    sizeBuf_t input = { .data = data, .cursize = len, .readcount = 4 };
    mdxModel_t model = {0};
    while (input.readcount < input.cursize) {
        uint32_t tag = MSG_ReadLong(&input), length = MSG_ReadLong(&input);
        sizeBuf_t body = { .data = input.data + input.readcount, .cursize = length };
        if (tag == ID_GEOS) MDLX_ReadGEOS(&body, &model);
        if (tag == ID_MTLS) MDLX_ReadMTLS(&body, &model);
        if (tag == ID_SEQS) MDLX_ReadSEQS(&body, &model);
        if (tag == ID_BONE) MDLX_ReadBONE(&body, &model);
        input.readcount += length;
    }
    bool flag = argc > 2 && !strcmp(argv[2], "flag");
    if (!model.geosets || model.geosets->num_vertices != (flag ? 12 : 5) || model.geosets->num_triangles != (flag ? 42 : 18) ||
        model.geosets->num_texcoord != (flag ? 12 : 5) || model.geosets->default_bounds.box.max.z <= 0 ||
        !model.materials || model.materials->num_layers != 1 || model.materials->layers[0].staticAlpha != 1 ||
        model.num_sequences != 7 || !model.bones) return 3;
    if (argc > 2 && !strcmp(argv[2], "tree")) {
        vec3_t alive = {0}, dead = {0}, regrown = {0};
        if (!model.bones->node.scale) return 4;
        MDLX_GetModelKeytrackValue(&model, model.bones->node.scale, 0, &alive);
        MDLX_GetModelKeytrackValue(&model, model.bones->node.scale, 4998, &dead);
        MDLX_GetModelKeytrackValue(&model, model.bones->node.scale, 3000, &regrown);
        if (alive.z < 0.99f || dead.z > 0.05f || regrown.z < 0.99f) return 5;
    }
    return 0;
}
'''

PATH_PARSER = r'''
#include <stdlib.h>
#include "common/shared.h"
#define g_local_h
static struct { handle_t (*MemAlloc)(long); void (*MemFree)(handle_t); } gi;
#include "games/warcraft-3/game/g_pathing.c"
static handle_t allocate(long size) { return calloc(1, size); }
int main(int argc, char **argv) {
    gi.MemAlloc = allocate; gi.MemFree = free;
    FILE *file = fopen(argv[1], "rb"); if (!file) return 1;
    uint8_t data[4096]; long len = fread(data, 1, sizeof(data), file); fclose(file);
    pathTex_t *texture = LoadTGA(data, len);
    if (!texture || texture->width != atoi(argv[2]) || texture->height != atoi(argv[2])) return 2;
    for (int i = 0; i < texture->width * texture->height; i++)
        if (!texture->map[i].r || !texture->map[i].b || !!texture->map[i].g != atoi(argv[3])) return 3;
    free(texture);
    return 0;
}
'''


class BasicBrowserAssets(unittest.TestCase):
    def test_map_flag_model_is_generated(self):
        with tempfile.TemporaryDirectory() as directory:
            generated = assets.generate(Path(directory))
            self.assertIn('Objects/InventoryItems/OrcCaptureFlag/OrcCaptureFlag.mdx', sorted(generated))

    def test_peach_hero_skill_icons_include_disabled_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            generated = assets.generate(Path(directory))
            # Observed H000 heroAbilList AEer, AOwk, A000, AEev, AEbl; Evasion
            # uses distinct passive and research paths in the shipped profiles.
            for name in ("BTNEntanglingRoots", "BTNWindWalkOn", "BTNStaffOfSanctuary",
                         "BTNEvasion", "BTNBlink", "PASBTNEvasion"):
                prefix = "PassiveButtons" if name.startswith("PAS") else "CommandButtons"
                for path in (f"ReplaceableTextures/{prefix}/{name}.blp",
                             f"ReplaceableTextures/CommandButtonsDisabled/DIS{name}.blp"):
                    self.assertIn(path, sorted(generated))
                    data = generated[path]
                    self.assertEqual(len(data), 1172 + 32 * 32 * 4)
                    self.assertGreater(len(set(data[i:i+4] for i in range(1172, len(data), 4))), 2)

    def test_command_profiles_have_visible_distinct_icons_and_grid_positions(self):
        with tempfile.TemporaryDirectory() as directory:
            generated = assets.generate(Path(directory))
            self.assertIn("Units/CommandFunc.txt", sorted(generated))
            # Localized labels and Errors already exist in the imported MPQs.
            self.assertNotIn("Units/CommandStrings.txt", generated)
            profile = configparser.ConfigParser(interpolation=None, comment_prefixes=("//", ";", "#"))
            profile.read_string(generated["Units/CommandFunc.txt"].decode())
            expected = {
                "CmdMove": (0, 0), "CmdStop": (1, 0), "CmdHoldPos": (2, 0),
                "CmdAttack": (3, 0), "CmdPatrol": (0, 1), "CmdAttackGround": (1, 1),
                "CmdSelectSkill": (3, 1), "CmdRally": (3, 1), "CmdCancel": (3, 2),
            }
            icons = {}
            for command, position in expected.items():
                self.assertIn(command, profile)
                self.assertEqual(profile[command]["Buttonpos"], f"{position[0]},{position[1]}")
                art = profile[command]["Art"].replace("\\", "/")
                self.assertIn(art, sorted(generated))
                data = generated[art]
                self.assertEqual(struct.unpack_from("<4sI4B2I", data), (b"BLP2", 1, 3, 8, 0, 0, 32, 32))
                pixels = [data[i:i+4] for i in range(1172, len(data), 4)]
                self.assertTrue(all(pixel[3] == 255 for pixel in pixels))
                self.assertGreater(len(set(pixels)), 2)
                icons[command] = data
            self.assertEqual(len(set(icons.values())), len(expected))

    def test_command_icons_have_distinct_repeatable_category_glyphs(self):
        names = ("Ankh", "ArcaniteArmor", "HelmOfValor", "HumanWatchTower", "OrbOfVenom",
                 "RingGreen", "TomeBrown", "WandOfManaSteal")
        images = []
        for name in names:
            path = f"ReplaceableTextures/CommandButtonsDisabled/DISBTN{name}.blp"
            pixels = list(assets.ui_pixels(path))
            self.assertEqual(pixels, list(assets.ui_pixels(path)))
            self.assertEqual(len(pixels), 32 * 32)
            self.assertGreater(len(set(pixels)), 2)
            self.assertTrue(all(pixel[3] == 255 for pixel in pixels))
            self.assertNotIn((255, 0, 255, 255), pixels)
            images.append(assets.blp(32, 32, pixels))
        self.assertEqual(len(set(images)), len(names))

    def test_simple_footprints_decode_and_block_in_native_loader(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            generated = assets.generate(output)
            self.assertIn("PathTextures/4x4SimpleSolid.tga", sorted(generated))
            binary = output / "path-check"
            build = subprocess.run(["cc", "-I", str(ROOT), "-I", str(ROOT / "shared"),
                                    "-x", "c", "-", "-o", str(binary)], input=PATH_PARSER,
                                   text=True, capture_output=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            for dimension, no_fly in ((2, False), (4, False), (12, False), (12, True)):
                path = output / "footprint.tga"
                path.write_bytes(assets.pathing_texture(dimension, dimension, no_fly))
                result = subprocess.run([str(binary), str(path), str(dimension), str(int(no_fly))],
                                        text=True, capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_primitive_models_decode_in_native_mdx_parser(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            binary = output / "mdx-check"
            command = ["cc", "-I", str(ROOT), "-I", str(ROOT / "shared"), "-I", "/usr/include/SDL2",
                       "-I", str(ROOT / "games/warcraft-3/common"), "-ffunction-sections", "-fdata-sections",
                       "-Wl,--gc-sections", "-x", "c", "-", "-lm", "-o", str(binary)]
            build = subprocess.run(command, input=MODEL_PARSER, text=True, capture_output=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            for kind in ("unit", "building", "tree", "shrub", "lily", "flag"):
                model = output / "proxy.mdx"
                model.write_bytes(assets.primitive_model(kind=kind))
                result = subprocess.run([str(binary), str(model), kind], capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")

    def test_native_blp_layout_and_transition_masks(self):
        for name, color in assets.TERRAIN.items():
            data = assets.blp(64, 64, assets.terrain_pixels(color))
            self.assertEqual(struct.unpack_from("<4sI4B2I", data), (b"BLP2", 1, 3, 8, 0, 0, 64, 64))
            self.assertEqual(struct.unpack_from("<I", data, 20)[0], 1172)
            self.assertEqual(len(data), 1172 + 64 * 64 * 4)
            alpha = lambda x, y: data[1172 + (x + y * 64) * 4 + 3]
            self.assertEqual(alpha(1, 1), 0, name)
            self.assertEqual(alpha(63, 63), 255, name)
            self.assertEqual(alpha(16, 0), 255, name)
            self.assertEqual(alpha(31, 15), 0, name)

    def test_repeatable_generation_preserves_imported_files(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            archive = output / "war3.mpq"
            archive.write_bytes(b"imported archive")
            first = assets.generate(output)
            self.assertEqual(first, assets.generate(output))
            self.assertEqual(archive.read_bytes(), b"imported archive")
            path = output / "UI/FrameDef/UI/ConsoleUI.fdf"
            path.write_text("user edit")
            with self.assertRaisesRegex(ValueError, "Refusing to replace"):
                assets.generate(output)
            self.assertEqual(path.read_text(), "user edit")
            path.write_bytes(first["UI/FrameDef/UI/ConsoleUI.fdf"])
            icon = output / "ReplaceableTextures/CommandButtonsDisabled/DISBTNAnkh.blp"
            icon.write_bytes(b"user icon")
            with self.assertRaisesRegex(ValueError, "Refusing to replace"):
                assets.generate(output)
            self.assertEqual(icon.read_bytes(), b"user icon")
            self.assertEqual(archive.read_bytes(), b"imported archive")

    def test_original_ui_parses_and_dialogs_clone_with_production_parser(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            generated = assets.generate(output)
            # Invoke the actual generated C binding functions, so a valid FDF
            # cannot pass with a missing root, child or required parent scope.
            includes, binding_checks = ["#define g_local_h"], []
            stems = [*assets.SCREENS.values(), "console_ui", "resource_bar", "upper_button_bar", "script_dialog", "script_dialog_button"]
            for stem in stems:
                source = (assets.GENERATED / (stem + ".h")).read_text()
                prefix = re.search(r'typedef struct (\w+)_s', source)[1]
                includes.append(f'#include "games/warcraft-3/game/generated/{stem}.h"')
                for dependency in re.findall(r'UI_EnsureFDF\(("[^"]+")\)', source):
                    binding_checks.append(f"UI_MarkFDFLoaded({dependency});")
                if f"{prefix}_Bind(" in source:
                    name = re.search(r'_Bind\(out, UI_FindFrame\("([^"]+)"\)', source)[1]
                    call = f'{prefix}_Bind(&bound, UI_FindFrame("{name}"))'
                else:
                    call = f'{prefix}_Load(&bound)'
                binding_checks.append(f'{{ {prefix}_t bound; check({call}, "{stem} binding"); }}')
            parser = PARSER.replace("int main(", "\n".join(includes) + "\nint main(")
            parser = parser.replace('    frameDef_t *source = UI_FindFrame("ScriptDialog");',
                                    "\n".join(binding_checks) + '\n    frameDef_t *source = UI_FindFrame("ScriptDialog");')
            binary = output / "fdf-check"
            command = ["cc", "-I", str(ROOT), "-I", str(ROOT / "shared"),
                       "-I", str(ROOT / "games/warcraft-3/common"), "-ffunction-sections", "-fdata-sections",
                       "-Wl,--gc-sections", "-x", "c", "-", "-lm", "-o", str(binary)]
            build = subprocess.run(command, input=parser, text=True, capture_output=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            files = [str(output / name) for name in sorted(generated) if name.endswith(".fdf")]
            result = subprocess.run([str(binary), *files], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
