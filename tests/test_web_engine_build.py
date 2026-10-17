#!/usr/bin/env python3
"""Check standalone packaging failures before invoking Emscripten."""
import importlib.util
from pathlib import Path
import tempfile
import json
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('web_engine_build', ROOT / 'port/web/build-engine.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
FILES = ('war3.mpq', 'War3x.mpq', 'War3Patch.mpq', 'War3xLocal.mpq',
         'Maps/Download/apricot.w3x', 'Maps/Download/peach.w3x')

class BundledDataTests(unittest.TestCase):
    def test_browser_launcher_keeps_initial_click_windowed(self):
        script = """
const fs = require('fs'), vm = require('vm');
const result = { args: null, redirect: null };
const context = { URLSearchParams,
  location: { search: process.argv[2], replace: url => result.redirect = url },
  document: { getElementById: () => ({textContent:''}) },
  window: { openrealmStartEngine: args => result.args = args } };
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), context);
process.stdout.write(JSON.stringify(result));
"""
        bridge = ROOT / 'port/web/site/filesystem-bridge.js'
        for map_id in ('apricot', 'peach', '__proto__', 'other'):
            with self.subTest(map=map_id):
                result = json.loads(subprocess.check_output(['node', '-e', script, str(bridge), '?map=' + map_id]))
                if map_id in ('apricot', 'peach'):
                    args = result['args']
                    index = args.index('vid_fullscreen')
                    self.assertEqual(args[index - 1:index + 2], ['+set', 'vid_fullscreen', '0'])
                    index = args.index('wc3_browser_bots')
                    self.assertEqual(args[index - 1:index + 2], ['+set', 'wc3_browser_bots', '1'])
                    self.assertEqual(args[-2:], ['+map', 'Maps/Download/' + map_id + '.w3x'])
                    self.assertIsNone(result['redirect'])
                else:
                    self.assertIsNone(result['args'])
                    self.assertEqual(result['redirect'], 'maps.html')
        result = json.loads(subprocess.check_output(['node', '-e', script, str(bridge), '?map=peach&bots=0']))
        index = result['args'].index('wc3_browser_bots')
        self.assertEqual(result['args'][index + 1], '0')

    def test_missing_each_required_input_rejected_before_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / 'port/web/data-input'
            for name in FILES:
                path = data / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'fixture')
            with patch.object(builder, 'ROOT', root):
                for name in FILES:
                    with self.subTest(name=name):
                        path = data / name
                        path.unlink()
                        with self.assertRaisesRegex(SystemExit, name.replace('.', r'\.')):
                            builder.bundled_data_args()
                        path.write_bytes(b'fixture')
                self.assertEqual(builder.bundled_data_args(),
                                 ['--preload-file', str(data) + '@/data/warcraft-3'])

if __name__ == '__main__':
    unittest.main()
