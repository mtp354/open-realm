/* Standalone two-map build: the retail archives and maps are preloaded under
 * /data/warcraft-3, so the page only needs a map id from the picker. */
(function () {
  'use strict';
  const BUNDLED_MAPS = {
    apricot: 'Maps/Download/apricot.w3x',
    peach: 'Maps/Download/peach.w3x'
  };
  const BUNDLED_DATA = '/data/warcraft-3';
  const map = new URLSearchParams(location.search).get('map');
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
    '+map', BUNDLED_MAPS[map]
  ]);
})();
