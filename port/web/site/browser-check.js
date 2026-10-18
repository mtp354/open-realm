/* Probe the worker environment before downloading/starting the pthread engine. */
(function () {
  'use strict';
  window.openrealmCheckBrowser = function () {
    return new Promise(function (resolve) {
      var worker, timer, finished = false;
      function finish(result) {
        if (finished) return;
        finished = true;
        clearTimeout(timer);
        if (worker) worker.terminate();
        resolve(result);
      }
      try {
        worker = new Worker('browser-check-worker.js');
        worker.onmessage = function (event) {
          var result = event.data;
          finish(result && typeof result.ok === 'boolean' ? result : {
            ok: false, message: 'The browser could not complete its graphics check.'
          });
        };
        worker.onerror = function (event) {
          event.preventDefault();
          finish({ ok: false, message: 'This browser could not start the game graphics worker.' });
        };
        timer = setTimeout(function () {
          finish({ ok: false, message: 'The browser graphics check timed out.' });
        }, 20000);
        var canvas = document.createElement('canvas');
        canvas.width = canvas.height = 8;
        var transferred = canvas.transferControlToOffscreen();
        worker.postMessage({ canvas: transferred }, [transferred]);
      } catch (error) {
        finish({ ok: false, message: 'This browser does not allow the game graphics worker.' });
      }
    });
  };
})();
