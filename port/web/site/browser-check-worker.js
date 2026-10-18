/* A separate canvas leaves the engine's transferable canvas untouched. */
self.onmessage = async function (event) {
  try {
    new WebAssembly.Memory({ initial: 1, maximum: 1, shared: true });
  } catch (error) {
    self.postMessage({ ok: false, message: 'This browser does not allow shared WebAssembly memory.' });
    return;
  }
  try {
    var canvas = event.data.canvas;
    var gl = canvas.getContext('webgl2', { depth: true, stencil: false, antialias: false });
    if (!gl) throw new Error('No WebGL 2 context');
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.flush();
  } catch (error) {
    self.postMessage({ ok: false, message: 'WebGL 2 graphics are unavailable in this browser worker.' });
    return;
  }
  try {
    // WasmFS initializes its OPFS backend in a worker, even with preloaded maps.
    await navigator.storage.getDirectory();
  } catch (error) {
    self.postMessage({ ok: false, message: 'This browser does not allow the game to access local browser storage.' });
    return;
  }
  self.postMessage({ ok: true });
};
