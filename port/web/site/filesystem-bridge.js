/* Standalone two-map build: the retail archives and maps are preloaded under
 * /data/warcraft-3, so the page only needs a map id from the picker. */
(function () {
  'use strict';
  const BUNDLED_MAPS = {
    apricot: 'Maps/Download/apricot.w3x',
    peach: 'Maps/Download/peach.w3x'
  };
  const BUNDLED_DATA = '/data/warcraft-3';
  const params = new URLSearchParams(location.search);
  const map = params.get('map');
  if (!Object.prototype.hasOwnProperty.call(BUNDLED_MAPS, map)) {
    location.replace('maps.html');
    return;
  }
  const status = document.getElementById('status');
  if (status) status.textContent = 'Starting ' + map + '…';
  // TFT mode is required: RoC hides the War3x archives that hold the
  // Loading and StandardTemplates FDFs, which the engine needs before the map.
  window.openrealmStartEngine([
    '+openrealm-data=' + BUNDLED_DATA,
    '-tft',
    // Native defaults request fullscreen on the next gesture; the page owns its explicit fullscreen button.
    '+set', 'vid_fullscreen', '0',
    '+set', 'wc3_browser_bots', params.get('bots') === '0' ? '0' : '1',
    '+map', BUNDLED_MAPS[map]
  ]);
})();
