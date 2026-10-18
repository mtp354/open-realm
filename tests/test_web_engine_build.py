#!/usr/bin/env python3
"""Check standalone packaging failures before invoking Emscripten."""
import importlib.util
from pathlib import Path
import tempfile
import json
import subprocess
import unittest
import re
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('web_engine_build', ROOT / 'port/web/build-engine.py')
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
FILES = ('war3.mpq', 'War3x.mpq', 'War3Patch.mpq', 'War3xLocal.mpq',
         'Maps/Download/apricot.w3x', 'Maps/Download/peach.w3x')

class BrowserStartupTests(unittest.TestCase):
    def test_worker_probe_reports_failures_and_always_releases_worker(self):
        script = r"""
const fs = require('fs'), vm = require('vm');
const mode = process.argv[2];
let terminated = 0, transferred = 0, errorHandled = false;
const context = {Promise, clearTimeout, setTimeout: cb => setTimeout(cb, 1),
  document:{createElement:()=>({transferControlToOffscreen:()=>({probe:true})})},
  Worker:class {
    constructor(){ if (mode === 'blocked') throw new Error('blocked'); }
    terminate(){ ++terminated; }
    postMessage(data, transfers){
      transferred = data.canvas.probe && transfers[0] === data.canvas;
      queueMicrotask(() => {
        if (mode === 'error') this.onerror({preventDefault(){errorHandled=true;}});
        else if (mode !== 'timeout') this.onmessage({data:{ok:mode==='ready',message:'WebGL unavailable'}});
      });
    }
  }
};
context.window = context;
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),context);
context.openrealmCheckBrowser().then(result=>process.stdout.write(
  JSON.stringify({result,terminated,transferred,errorHandled})));
"""
        for mode in ('ready', 'graphics', 'blocked', 'error', 'timeout'):
            with self.subTest(mode=mode):
                result = json.loads(subprocess.check_output(['node', '-e', script,
                    str(ROOT / 'port/web/site/browser-check.js'), mode]))
                self.assertEqual(result['result']['ok'], mode == 'ready')
                self.assertEqual(result['terminated'], int(mode != 'blocked'))
                if mode != 'blocked':
                    self.assertTrue(result['transferred'])
                if mode == 'error':
                    self.assertTrue(result['errorHandled'])

    def test_worker_checks_graphics_and_storage_before_engine_start(self):
        script = r"""
const fs = require('fs'), vm = require('vm');
const mode = process.argv[2];
let result, storageChecks=0;
const context = {
  self:{postMessage:r=>result=r},
  WebAssembly:{Memory:function(){if(mode==='memory')throw new Error('memory');}},
  navigator:{storage:{async getDirectory(){++storageChecks;if(mode==='storage')throw new Error('denied');}}}
};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),context);
const gl={COLOR_BUFFER_BIT:1,DEPTH_BUFFER_BIT:2,clear(){},flush(){}};
context.self.onmessage({data:{canvas:{getContext:()=>mode==='graphics'?null:gl}}})
  .then(()=>process.stdout.write(JSON.stringify({result,storageChecks})));
"""
        for mode in ('ready', 'graphics', 'memory', 'storage'):
            with self.subTest(mode=mode):
                result = json.loads(subprocess.check_output(['node', '-e', script,
                    str(ROOT / 'port/web/site/browser-check-worker.js'), mode]))
                self.assertEqual(result['result']['ok'], mode == 'ready')
                self.assertEqual(result['storageChecks'], int(mode in ('ready', 'storage')))

    def test_engine_waits_for_worker_capabilities_and_explains_failure(self):
        shell = (ROOT / 'port/web/site/engine-shell.html').read_text()
        inline = next(part for part in re.findall(r'<script>(.*?)</script>', shell, re.S)
                      if 'var Module' in part)
        script = r"""
const vm = require('vm');
const elements = new Map(), scripts = [];
let checks = 0, resolveCheck;
const pending = new Promise(resolve => resolveCheck = resolve);
const context = {
  document: {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, {textContent:'', hidden:id!=='game-container', value:'',
        addEventListener(){}, setAttribute(){}, focus(){}});
      return elements.get(id);
    },
    addEventListener(){}, createElement: () => ({}), body: {appendChild: s => scripts.push(s)}
  },
  location: {href:'http://127.0.0.1:8000/index.html?map=peach'},
  OffscreenCanvas: function(){}, HTMLCanvasElement: {prototype:{transferControlToOffscreen(){}}},
  console, KeyboardEvent:function(){}, crossOriginIsolated:true,
  addEventListener(){}, openrealmCheckBrowser(){ ++checks; return pending; }
};
context.window = context;
context.document.getElementById('status');
vm.runInNewContext(process.argv[1], context);
(async () => {
  const start = context.openrealmStartEngine(['+map','peach']);
  const before = scripts.length;
  const ok = process.argv[2] === 'true';
  resolveCheck({ok, message:'Worker WebGL 2 unavailable'});
  await start;
  process.stdout.write(JSON.stringify({checks, before, after:scripts.length,
    status:elements.get('status').textContent,
    help:elements.get('browser-help')?.hidden,
    url:elements.get('external-game-url')?.value, gameHidden:elements.get('game-container')?.hidden}));
})();
"""
        for supported in (True, False):
            with self.subTest(supported=supported):
                result = json.loads(subprocess.check_output(
                    ['node', '-e', script, inline, str(supported).lower()]))
                self.assertEqual(result['before'], 0, 'engine started before worker probe finished')
                self.assertEqual(result['checks'], 1)
                self.assertEqual(result['after'], int(supported))
                if not supported:
                    self.assertIn('WebGL 2', result['status'])
                    self.assertFalse(result['help'])
                    self.assertIn('?map=peach', result['url'])
                    self.assertTrue(result['gameHidden'])

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
