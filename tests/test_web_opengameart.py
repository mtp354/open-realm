"""Exercise the installed art pack and generated-file ownership contract."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

from test_web_basic_assets import assets, MODEL_PARSER, ROOT

CATALOG = ROOT / "port/web/art-input/catalog.json"


class OpenGameArtTests(unittest.TestCase):
    def test_explicit_overlay_is_repeatable_and_preserves_maps_and_user_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "game"
            output.mkdir()
            pack = Path(directory) / "pack"
            pack.mkdir()
            image = assets.blp(2, 2, [(20, 60, 90, 255)] * 4)
            (pack / "panel.blp").write_bytes(image)
            entry = {"source": "panel.blp", "sha256": hashlib.sha256(image).hexdigest()}
            catalog = pack / "catalog.json"
            catalog.write_text(json.dumps({"version": 1, "files": {"UI/BrowserBasic/panel.blp": entry}}))
            archive = output / "peach.w3x"
            archive.write_bytes(b"authored map")
            assets.generate(output)
            first = assets.generate(output, art=catalog)
            self.assertEqual(first["UI/BrowserBasic/panel.blp"], image)
            self.assertEqual(first, assets.generate(output, art=catalog))
            self.assertEqual(archive.read_bytes(), b"authored map")
            (output / "UI/BrowserBasic/panel.blp").write_bytes(b"user edit")
            before = (output / assets.MANIFEST).read_bytes()
            with self.assertRaisesRegex(ValueError, "Refusing to replace"):
                assets.generate(output, art=catalog)
            self.assertEqual((output / "UI/BrowserBasic/panel.blp").read_bytes(), b"user edit")
            self.assertEqual((output / assets.MANIFEST).read_bytes(), before)

    def test_pack_rejects_corruption_and_out_of_scope_paths_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            pack = Path(directory)
            (pack / "art.blp").write_bytes(b"corrupted")
            catalog = pack / "catalog.json"
            entry = {"source": "art.blp", "sha256": "0" * 64}
            for target, source, error in (("UI/BrowserBasic/panel.blp", "art.blp", "hash"),
                    ("Maps/Download/peach.w3x", "art.blp", "target"),
                    ("OpenArt/../war3.mpq", "art.blp", "target"),
                    ("UI/BrowserBasic/panel.blp", "../outside.blp", "source")):
                with self.subTest(target=target, source=source):
                    entry["source"] = source
                    catalog.write_text(json.dumps({"version": 1, "files": {target: entry}}))
                    output = pack / "output"
                    with self.assertRaisesRegex(ValueError, error):
                        assets.generate(output, art=catalog)
                    self.assertFalse(output.exists(), "invalid pack wrote partial output")

    def test_installed_pack_has_native_art_and_complete_texture_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            files = assets.generate(Path(directory), art=CATALOG)
            catalog = json.loads(CATALOG.read_text())
            self.assertGreater(len(catalog["files"]), 60)
            for name in catalog["files"]:
                data = files[name]
                if name.endswith(".mdx"):
                    self.assertEqual(data[:4], b"MDLX", name)
                    cursor = 4
                    while cursor < len(data):
                        tag, size = struct.unpack_from("<4sI", data, cursor)
                        if tag == b"TEXS":
                            for offset in range(cursor + 8, cursor + 8 + size, 268):
                                path = data[offset+4:offset+264].split(b"\0")[0].decode().replace("\\", "/")
                                if path:
                                    self.assertIn(path, files, name + " texture " + path)
                        cursor += size + 8
                elif name.endswith(".blp"):
                    self.assertEqual(data[:4], b"BLP2", name)
                    width, height = struct.unpack_from("<2I", data, 12)
                    self.assertEqual(len(data), 1172 + width * height * 4, name)
                    if name.startswith("TerrainArt/"):
                        self.assertEqual((width, height), (256, 256))
                        alpha = lambda x, y: data[1172 + (x + y * width) * 4 + 3]
                        self.assertEqual(alpha(0, 0), 0)
                        self.assertEqual(alpha(255, 255), 255)
                        self.assertEqual(alpha(64, 0), 255)
                        self.assertEqual(alpha(127, 63), 0)
                        self.assertGreater(len(set(data[i:i+3] for i in range(1172, len(data), 4))), 16)

    def test_hud_backdrops_keep_light_labels_readable_and_ground_decals_have_alpha(self):
        with tempfile.TemporaryDirectory() as directory:
            files = assets.generate(Path(directory), art=CATALOG)
            for name in ("panel", "button", "pressed"):
                data = files[f"UI/BrowserBasic/{name}.blp"]
                width, height = struct.unpack_from("<2I", data, 12)
                offset = 1172 + (width // 2 + height // 2 * width) * 4
                self.assertLess(max(data[offset:offset+3]), 110, name)
            for name in ("Human", "Ancient"):
                data = files[f"ReplaceableTextures/Splats/{name}UberSplat.blp"]
                self.assertEqual(data[1175], 0, "decal corner must be transparent")
                center = 1172 + (64 + 64 * 128) * 4 + 3
                self.assertGreater(data[center], 160, "decal center must be visible")

    def test_converted_models_decode_and_trees_keep_death_and_regrowth(self):
        # Use the production reader/interpolator, allowing actual multi-geoset
        # meshes instead of the basic pack's fixed five-vertex pyramid.
        parser = MODEL_PARSER.replace("model.geosets->num_vertices != (flag ? 12 : 5)", "model.geosets->num_vertices < 12")
        parser = parser.replace("model.geosets->num_triangles != (flag ? 42 : 18)", "model.geosets->num_triangles < 12")
        parser = parser.replace("model.geosets->num_texcoord != (flag ? 12 : 5)", "model.geosets->num_texcoord != model.geosets->num_vertices")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            files = assets.generate(output, art=CATALOG)
            binary = output / "mdx-check"
            build = subprocess.run(["cc", "-I", str(ROOT), "-I", str(ROOT / "shared"),
                "-I", str(ROOT / "games/warcraft-3/common"), "-ffunction-sections", "-fdata-sections",
                "-Wl,--gc-sections", "-x", "c", "-", "-lm", "-o", str(binary)],
                input=parser, text=True, capture_output=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            for name in json.loads(CATALOG.read_text())["files"]:
                if name.endswith(".mdx"):
                    result = subprocess.run([str(binary), str(output / name),
                        "tree" if "LordaeronTree" in name else "model"], capture_output=True, timeout=5)
                    self.assertEqual(result.returncode, 0, name + str(result.stderr))


if __name__ == "__main__":
    unittest.main()
