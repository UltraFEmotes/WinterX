import json
import hashlib
import shutil
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
import ruby_theme


class BridgePackageTests(unittest.TestCase):
    def test_free_icon_request_uses_its_own_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); files = root / 'ruby'; (files / 'requests').mkdir(parents=True)
            request = files / 'requests/10-0.json'
            request.write_text(json.dumps({'id': '10-0', 'action': 'enable_icons'}))
            with patch.object(safe_mode, 'set_marker_and_respring', return_value={'ok': True, 'message': 'enabled'}) as apply:
                ruby_bridge.process(request, files, root / 'inbox')
            self.assertEqual(apply.call_args.args[-3:], (True, 'free-icons.enabled', 'Icon placement test'))
            reply = json.loads((files / 'results/10-0.json').read_text())
            self.assertTrue(reply['ok']); self.assertEqual(reply['action'], 'enable_icons')

    def test_color_tweak_request_uses_expected_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = root / 'ruby'
            (files / 'requests').mkdir(parents=True)
            request = files / 'requests/9-0.json'
            request.write_text(json.dumps({'id': '9-0', 'action': 'enable_colors'}))
            with patch.object(ruby_theme, 'stage'), patch.object(safe_mode, 'set_marker_and_respring', return_value={'ok': True, 'message': 'enabled'}) as apply:
                ruby_bridge.process(request, files, root / 'inbox')
            self.assertEqual(apply.call_args.args[-3:], (True, 'ui-colors.enabled', 'Color test'))
            reply = json.loads((files / 'results/9-0.json').read_text())
            self.assertTrue(reply['ok'])
            self.assertEqual(reply['action'], 'enable_colors')

    def test_install_update_remove_through_bridge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = root / 'ruby'
            imports = files / 'imports'
            imports.mkdir(parents=True)
            marker = root / 'spring/files/ruby/settings-test.enabled'
            actions = []
            def apply(data, state, apk, sha, enabled, name, label):
                actions.append(enabled)
                marker.parent.mkdir(parents=True, exist_ok=True)
                if enabled: marker.touch()
                else: marker.unlink(missing_ok=True)
                return {'ok': True}
            def package(version):
                manifest = {'format':'winterx.springys/1', 'id':'me.example.test', 'name':'Test',
                            'version':version, 'description':'Example', 'author':'Example', 'hook':'test.settings'}
                with zipfile.ZipFile(imports / 'test.springys', 'w') as z:
                    z.writestr('manifest.json', json.dumps(manifest))
            def request(number, action, **values):
                path = files / ('requests/' + number + '-0.json')
                path.parent.mkdir(exist_ok=True)
                path.write_text(json.dumps({'id':number+'-0', 'action':action, **values}))
                ruby_bridge.process(path, files, root / 'inbox')
                result = json.loads((files / ('results/' + number + '-0.json')).read_text())
                self.assertTrue(result['ok'], result)
            with patch.object(macapk_jailbreak, 'DATA', root / 'spring'), patch.object(macapk_jailbreak, 'STATE', root / 'state'), patch.object(safe_mode, 'set_marker_and_respring', side_effect=apply):
                package('1.0')
                request('1', 'install_package', filename='test.springys')
                self.assertTrue(marker.exists())
                package('2.0')
                request('2', 'install_package', filename='test.springys')
                catalog = json.loads((files / 'packages.json').read_text())
                self.assertEqual(catalog['installed'][0]['version'], '2.0')
                request('3', 'remove_package', packageId='me.example.test')
                self.assertFalse(marker.exists())
                self.assertEqual(json.loads((files / 'packages.json').read_text())['installed'], [])
            self.assertEqual(actions, [True, False])

    def test_animaper_package_install_and_remove_do_not_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); files = root / 'ruby'; imports = files / 'imports'
            imports.mkdir(parents=True)
            shutil.copy2(ROOT / 'builtin-repo/packages/animaper.springys', imports / 'animaper.springys')
            apk = root / 'engine.apk'; apk.write_bytes(b'test engine')
            sha = hashlib.sha256(apk.read_bytes()).hexdigest()
            state = root / 'state'; state.mkdir()
            (state / 'active.json').write_text(json.dumps({'pid': 42, 'apk': str(apk), 'apk_sha256': sha}))
            data = root / 'spring'; marker = data / 'files/ruby/animaper.enabled'
            def request(number, action, **values):
                path = files / ('requests/' + number + '-0.json')
                path.parent.mkdir(exist_ok=True)
                path.write_text(json.dumps({'id': number + '-0', 'action': action, **values}))
                ruby_bridge.process(path, files, root / 'inbox')
                reply = json.loads((files / ('results/' + number + '-0.json')).read_text())
                self.assertTrue(reply['ok'], reply)
            import animaper
            with patch.object(macapk_jailbreak, 'DATA', data), patch.object(macapk_jailbreak, 'STATE', state), \
                 patch.object(macapk_jailbreak, 'PATCHED', apk), patch.object(macapk_jailbreak, 'PATCH_SHA', sha), \
                 patch.object(animaper, 'supported_by', return_value=True), \
                 patch.object(safe_mode.control, 'spring_pids', return_value=[42]), \
                 patch.object(safe_mode.control, 'is_overlay_process', return_value=True), \
                 patch.object(safe_mode.control, 'stop_spring') as stop, \
                 patch.object(safe_mode.control, 'start_overlay') as start:
                request('1', 'install_package', filename='animaper.springys')
                self.assertTrue(marker.is_file())
                request('2', 'remove_package', packageId='me.weirdmm.animaper')
                self.assertFalse(marker.exists())
                stop.assert_not_called(); start.assert_not_called()

    def test_scan_writes_catalogue_and_reply(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = root / 'ruby'
            (files / 'requests').mkdir(parents=True)
            request = files / 'requests/123-456.json'
            request.write_text(json.dumps({'id': '123-456', 'action': 'scan_packages'}))
            with patch.object(macapk_jailbreak, 'DATA', root / 'spring'):
                ruby_bridge.process(request, files, root / 'inbox')
            reply = json.loads((files / 'results/123-456.json').read_text())
            self.assertTrue(reply['ok'])
            self.assertEqual(reply['action'], 'scan_packages')
            self.assertEqual(json.loads((files / 'packages.json').read_text()), {'available': [], 'installed': []})

    def test_code_install_uses_running_engine_and_reports_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); files = root / 'ruby'; imports = files / 'imports'
            imports.mkdir(parents=True)
            manifest = json.loads((ROOT / 'examples/code-tweak/manifest.json').read_text())
            with zipfile.ZipFile(imports / 'code.springys', 'w') as archive:
                archive.writestr('manifest.json', json.dumps(manifest))
                archive.writestr('tweak/main.js', 'WinterX.log("my own code");')
            apk = root / 'running.apk'
            with zipfile.ZipFile(apk, 'w') as archive:
                archive.writestr('classes.dex', b'winterxCreate')
                archive.writestr('classes3.dex', b'winterx/tweaks/TweakHost winterx/tweaks/TweakSettings')
            state = root / 'state'; state.mkdir()
            (state / 'active.json').write_text(json.dumps({'pid': 42, 'apk': str(apk),
                'apk_sha256': hashlib.sha256(apk.read_bytes()).hexdigest()}))
            data = root / 'spring'; pages = data / 'files/ios6_pages.json'
            pages.parent.mkdir(parents=True); pages.write_text('saved icon positions')
            target = data / 'files/winterx-tweaks' / manifest['id']
            def request(number):
                path = files / ('requests/' + number + '-0.json'); path.parent.mkdir(exist_ok=True)
                path.write_text(json.dumps({'id': number + '-0', 'action': 'install_package', 'filename': 'code.springys'}))
                ruby_bridge.process(path, files, root / 'inbox')
                return json.loads((files / ('results/' + number + '-0.json')).read_text())
            with patch.object(macapk_jailbreak, 'DATA', data), patch.object(macapk_jailbreak, 'STATE', state), \
                 patch.object(macapk_jailbreak, 'PATCHED', root / 'older-selected.apk'), \
                 patch.object(safe_mode.control, 'is_overlay_process', return_value=False):
                self.assertFalse(request('1')['ok'])
                self.assertFalse((target / 'enabled').exists())
            with patch.object(macapk_jailbreak, 'DATA', data), patch.object(macapk_jailbreak, 'STATE', state), \
                 patch.object(macapk_jailbreak, 'PATCHED', root / 'older-selected.apk'), \
                 patch.object(safe_mode.control, 'spring_pids', return_value=[42]), \
                 patch.object(safe_mode.control, 'is_overlay_process', return_value=True), \
                 patch.object(safe_mode.control, 'stop_spring') as stop, \
                 patch.object(safe_mode.control, 'start_overlay') as start:
                reply = request('2')
                self.assertTrue(reply['ok'], reply); self.assertTrue(reply['restartRequired'])
                self.assertTrue((target / 'enabled').is_file())
                self.assertEqual(pages.read_text(), 'saved icon positions')
                stop.assert_not_called(); start.assert_not_called()

    def test_unknown_package_reports_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = root / 'ruby'
            (files / 'requests').mkdir(parents=True)
            request = files / 'requests/123-456.json'
            request.write_text(json.dumps({'id': '123-456', 'action': 'remove_package', 'packageId': 'me.example.missing'}))
            with patch.object(macapk_jailbreak, 'DATA', root / 'spring'):
                ruby_bridge.process(request, files, root / 'inbox')
            reply = json.loads((files / 'results/123-456.json').read_text())
            self.assertFalse(reply['ok'])
            self.assertEqual(reply['action'], 'remove_package')


if __name__ == '__main__':
    unittest.main()
