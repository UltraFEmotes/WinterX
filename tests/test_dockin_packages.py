import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'patches'))
import macapk_jailbreak
import ruby_bridge
import safe_mode
import springys_tool
import tweak_runtime


class DockInPackageTests(unittest.TestCase):
    def test_native_dock_abi_and_hooks_are_required(self):
        with tempfile.TemporaryDirectory() as name:
            apk = Path(name) / 'engine.apk'
            primary = b'winterx/layout/DockIn winterx/layout/SpringHooks launchSize'
            helpers = b'dockin-native-v1 winterx/layout/DockMotion'
            for main, extra, expected in ((primary, helpers, True), (primary, b'old', False),
                    (b'winterx/layout/DockIn', helpers, False), (primary, b'dockin-native-v1', False)):
                with zipfile.ZipFile(apk, 'w') as archive:
                    archive.writestr('classes.dex', main); archive.writestr('classes3.dex', extra)
                self.assertEqual(tweak_runtime.dockin_supported_by(apk), expected)
            self.assertFalse(tweak_runtime.dockin_supported_by(Path(name) / 'missing.apk'))

    def test_unlisted_package_and_live_install_remove_preserve_saved_data(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); files = root / 'ruby'; imports = files / 'imports'; imports.mkdir(parents=True)
            meta = springys_tool.build(ROOT / 'builtin-repo/sources/dockin', imports / 'dockin.springys')
            self.assertEqual(meta['hook'], 'tweak.dockin')
            catalogue = json.loads((ROOT / 'builtin-repo/index.json').read_text())
            ids = [springys_tool.springys.inspect(ROOT / 'builtin-repo' / item['url'])[0]['id'] for item in catalogue['packages']]
            self.assertNotIn(meta['id'], ids)
            data = root / 'spring'; ruby = data / 'files/ruby'; ruby.mkdir(parents=True)
            protected = {data / 'files/ios6_pages.json': b'saved six-icon dock and pages',
                ruby / 'dockin.capacity': b'6\n', ruby / 'freeme-slots-v1.json': b'saved cells',
                ruby / 'icon-positions-v1.json': b'legacy positions'}
            for path, content in protected.items(): path.write_bytes(content)
            apk = root / 'running.apk'
            with zipfile.ZipFile(apk, 'w') as archive:
                archive.writestr('classes.dex', b'winterx/layout/DockIn winterx/layout/SpringHooks launchSize')
                archive.writestr('classes3.dex', b'dockin-native-v1 winterx/layout/DockMotion')
            state = root / 'state'; state.mkdir()
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
                reply = request(1, 'install_package', filename='dockin.springys')
                self.assertTrue(reply['ok'], reply); self.assertFalse(reply['restartRequired'])
                self.assertTrue((ruby / 'dockin.enabled').is_file())
                reply = request(2, 'remove_package', packageId=meta['id'])
                self.assertTrue(reply['ok'], reply); self.assertFalse((ruby / 'dockin.enabled').exists())
                with patch.object(safe_mode.control, 'spring_pids', return_value=[42, 43]):
                    self.assertFalse(request(3, 'install_package', filename='dockin.springys')['ok'])
                stop.assert_not_called(); start.assert_not_called()
            for path, content in protected.items(): self.assertEqual(path.read_bytes(), content)
