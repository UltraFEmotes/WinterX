import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'patches'))
import macapk_jailbreak
import ruby_bridge
import safe_mode
import springys_tool


class SnowyPackageTests(unittest.TestCase):
    def test_unlisted_live_install_remove_preserve_packs_preferences_and_layout_with_capability_gate(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); files = root / 'ruby'; imports = files / 'imports'; imports.mkdir(parents=True)
            meta = springys_tool.build(ROOT / 'builtin-repo/sources/snowyhome', imports / 'snowy.springys')
            self.assertEqual(meta['hook'], 'tweak.snowyhome')
            catalogue = json.loads((ROOT / 'builtin-repo/index.json').read_text())
            ids = [springys_tool.springys.inspect(ROOT / 'builtin-repo' / item['url'])[0]['id'] for item in catalogue['packages']]
            self.assertNotIn(meta['id'], ids)
            data = root / 'spring'; ruby = data / 'files/ruby'; ruby.mkdir(parents=True)
            protected = {data / 'files/ios6_pages.json': b'saved home/folder/dock memberships',
                ruby / 'snowyhome/preferences.json': b'{"pack":"stock","hideLabels":true}',
                ruby / 'snowyhome/packs/fixture/icons/mail.png': b'preserved icon bytes',
                ruby / 'freeme-slots-v1.json': b'saved cells', ruby / 'icon-positions-v1.json': b'legacy positions'}
            for path, content in protected.items(): path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(content)
            state = root / 'state'; state.mkdir(); apk = root / 'running.apk'
            def engine(primary):
                with zipfile.ZipFile(apk, 'w') as archive:
                    archive.writestr('classes.dex', primary); archive.writestr('classes3.dex', b'snowyhome-render-v1 winterx/snowy/SnowySettings')
                (state / 'active.json').write_text(json.dumps({'pid': 42, 'apk': str(apk), 'apk_sha256': hashlib.sha256(apk.read_bytes()).hexdigest()}))
            def request(n, action, **values):
                path = files / f'requests/{n}-0.json'; path.parent.mkdir(exist_ok=True)
                path.write_text(json.dumps({'id': f'{n}-0', 'action': action, **values}))
                ruby_bridge.process(path, files, root / 'inbox')
                return json.loads((files / f'results/{n}-0.json').read_text())
            with patch.object(macapk_jailbreak, 'DATA', data), patch.object(macapk_jailbreak, 'STATE', state), \
                 patch.object(safe_mode.control, 'spring_pids', return_value=[42]), \
                 patch.object(safe_mode.control, 'is_overlay_process', return_value=True), \
                 patch.object(safe_mode.control, 'stop_spring') as stop, patch.object(safe_mode.control, 'start_overlay') as start:
                engine(b'winterx/layout/DockIn winterx/layout/SpringHooks')
                self.assertFalse(request(1, 'install_package', filename='snowy.springys')['ok'])
                self.assertFalse((ruby / 'snowyhome.enabled').exists())
                engine(b'winterx/snowy/SnowyHome winterxStockIcon hiddenLabels artwork')
                reply = request(2, 'install_package', filename='snowy.springys')
                self.assertTrue(reply['ok'], reply); self.assertFalse(reply['restartRequired'])
                self.assertTrue((ruby / 'snowyhome.enabled').is_file())
                reply = request(3, 'remove_package', packageId=meta['id'])
                self.assertTrue(reply['ok'], reply); self.assertFalse((ruby / 'snowyhome.enabled').exists())
                with patch.object(safe_mode.control, 'spring_pids', return_value=[42, 43]):
                    self.assertFalse(request(4, 'install_package', filename='snowy.springys')['ok'])
                stop.assert_not_called(); start.assert_not_called()
            for path, content in protected.items(): self.assertEqual(path.read_bytes(), content)
