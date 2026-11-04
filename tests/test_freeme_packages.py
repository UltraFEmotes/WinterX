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
import ruby_bridge
import macapk_jailbreak
import safe_mode
import springys_tool
import tweak_runtime


class FreeMePackageTests(unittest.TestCase):
    def test_sparse_grid_abi_is_required_not_legacy_free_icons(self):
        with tempfile.TemporaryDirectory() as name:
            apk = Path(name) / 'engine.apk'
            for primary, helpers, expected in (
                (b'winterx/layout/SpringHooks', b'icon-positions-v1.json', False),
                (b'winterx/layout/FreeMe winterx/layout/SpringHooks', b'freeme-slots-v1.json', False),
                (b'winterx/layout/FreeMe winterx/layout/SpringHooks', b'freeme-grid-v1', True),
                (b'old', b'freeme-grid-v1', False),
            ):
                with zipfile.ZipFile(apk, 'w') as archive:
                    archive.writestr('classes.dex', primary)
                    archive.writestr('classes3.dex', helpers)
                self.assertEqual(tweak_runtime.freeme_supported_by(apk), expected)
            self.assertFalse(tweak_runtime.freeme_supported_by(Path(name) / 'missing.apk'))

    def test_source_package_is_valid_and_unlisted(self):
        with tempfile.TemporaryDirectory() as name:
            meta = springys_tool.build(ROOT / 'builtin-repo/sources/freeme', Path(name) / 'freeme.springys')
            self.assertEqual(meta['hook'], 'tweak.freeme')
            self.assertEqual(meta['id'], 'com.winterx.freeme')
            catalogue = json.loads((ROOT / 'builtin-repo/index.json').read_text())
            ids = [springys_tool.springys.inspect(ROOT / 'builtin-repo' / item['url'])[0]['id'] for item in catalogue['packages']]
            self.assertNotIn(meta['id'], ids)

    def test_install_remove_preserves_layout_state_and_never_restarts(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); files = root / 'ruby'; imports = files / 'imports'; imports.mkdir(parents=True)
            springys_tool.build(ROOT / 'builtin-repo/sources/freeme', imports / 'freeme.springys')
            data = root / 'spring'; ruby = data / 'files/ruby'; ruby.mkdir(parents=True)
            protected = {
                data / 'files/ios6_pages.json': b'saved pages',
                ruby / 'icon-positions-v1.json': b'legacy positions',
                ruby / 'freeme-slots-v1.json': b'saved sparse cells',
                ruby / 'freeme.disabled': b'user preference',
            }
            for path, content in protected.items(): path.write_bytes(content)
            apk = root / 'running.apk'
            with zipfile.ZipFile(apk, 'w') as archive:
                archive.writestr('classes.dex', b'winterx/layout/FreeMe winterx/layout/SpringHooks')
                archive.writestr('classes3.dex', b'freeme-grid-v1')
            state = root / 'state'; state.mkdir()
            (state / 'active.json').write_text(json.dumps({'pid': 42, 'apk': str(apk), 'apk_sha256': hashlib.sha256(apk.read_bytes()).hexdigest()}))
            def request(n, action, **values):
                path = files / f'requests/{n}-0.json'; path.parent.mkdir(exist_ok=True)
                path.write_text(json.dumps({'id': f'{n}-0', 'action': action, **values}))
                ruby_bridge.process(path, files, root / 'inbox')
                return json.loads((files / f'results/{n}-0.json').read_text())
            with patch.object(macapk_jailbreak, 'DATA', data), patch.object(macapk_jailbreak, 'STATE', state), \
                 patch.object(macapk_jailbreak, 'PATCHED', root / 'not-the-running-apk'), \
                 patch.object(safe_mode.control, 'spring_pids', return_value=[42]), \
                 patch.object(safe_mode.control, 'is_overlay_process', return_value=True), \
                 patch.object(safe_mode.control, 'stop_spring') as stop, patch.object(safe_mode.control, 'start_overlay') as start:
                reply = request(1, 'install_package', filename='freeme.springys')
                self.assertTrue(reply['ok'], reply); self.assertFalse(reply['restartRequired'])
                self.assertTrue((ruby / 'freeme.enabled').is_file())
                reply = request(2, 'remove_package', packageId='com.winterx.freeme')
                self.assertTrue(reply['ok'], reply); self.assertFalse((ruby / 'freeme.enabled').exists())
                stop.assert_not_called(); start.assert_not_called()
            for path, content in protected.items(): self.assertEqual(path.read_bytes(), content)

    def test_selected_but_not_running_engine_cannot_enable_freeme(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); files = root / 'ruby'; imports = files / 'imports'; imports.mkdir(parents=True)
            springys_tool.build(ROOT / 'builtin-repo/sources/freeme', imports / 'freeme.springys')
            request = files / 'requests/1-0.json'; request.parent.mkdir()
            request.write_text(json.dumps({'id': '1-0', 'action': 'install_package', 'filename': 'freeme.springys'}))
            with patch.object(macapk_jailbreak, 'DATA', root / 'spring'), \
                 patch.object(macapk_jailbreak, 'STATE', root / 'state'), \
                 patch.object(tweak_runtime, 'freeme_supported_by', return_value=True), \
                 patch.object(safe_mode, 'set_live_tweak') as apply:
                ruby_bridge.process(request, files, root / 'inbox')
                apply.assert_not_called()
            self.assertFalse(json.loads((files / 'results/1-0.json').read_text())['ok'])
            self.assertFalse((root / 'spring/files/ruby/freeme.enabled').exists())


if __name__ == '__main__':
    unittest.main()
