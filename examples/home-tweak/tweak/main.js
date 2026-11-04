'use strict';
WinterX.on('settingsTap', function (page, row) {
  if (row !== 'inspect' && row !== 'move') return;
  WinterX.home.snapshot().then(function (home) {
    if (row === 'inspect') {
      return WinterX.alert({title: 'Native Home Snapshot', message: home.pages.length + ' pages; ' + home.dock.length + ' dock icons. Revision: ' + home.revision.slice(0, 12)});
    }
    var icons = home.pages[0] || [];
    var first = icons.find(function (icon) { return icon.id.indexOf('folder:') !== 0 && icon.id !== 'folder-utilities'; });
    var occupied = icons.map(function (icon) { return icon.slot; }), gap = -1;
    for (var slot = 0; slot < home.capacity; slot++) if (occupied.indexOf(slot) === -1) { gap = slot; break; }
    if (!first || gap < 0 || !home.gridEnabled) throw new Error('Enable FreeMe and leave a gap on page 1 first.');
    return WinterX.alert({title: 'Change This Grid Cell?', message: 'Move ' + first.id + ' to cell ' + gap + ' on page 1? Native dock and folder contents stay unchanged.', buttons: ['Cancel', 'Move']}).then(function (choice) {
      if (choice === 1) return WinterX.home.move({id: first.id, page: 0, slot: gap, revision: home.revision});
    });
  }).catch(function (error) { WinterX.alert({title: 'Home Unchanged', message: String(error.message)}); });
});
