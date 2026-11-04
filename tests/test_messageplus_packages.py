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


class MessagePlusPackageTests(unittest.TestCase):
    def test_unlisted_hook_requires_running_native_calls_and_preserves_preferences(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); files = root / 'ruby'; imports = files / 'imports'; imports.mkdir(parents=True)
            meta = springys_tool.build(ROOT / 'builtin-repo/sources/messageplus', imports / 'messages.springys')
            self.assertEqual(meta['hook'], 'tweak.messageplus')
            catalogue = json.loads((ROOT / 'builtin-repo/index.json').read_text())
            ids = [springys_tool.springys.inspect(ROOT / 'builtin-repo' / item['url'])[0]['id'] for item in catalogue['packages']]
            self.assertNotIn(meta['id'], ids)
            data = root / 'spring'; ruby = data / 'files/ruby'; ruby.mkdir(parents=True)
            protected = {data / 'files/ios6_pages.json': b'saved home/folder/dock',
                         ruby / 'messageplus/photo-quality': b'95\n',
                         ruby / 'freeme-slots-v1.json': b'saved grid',
                         ruby / 'tweaks/me.example.code/data/value': b'user tweak data'}
            for path, content in protected.items(): path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(content)
            state = root / 'state'; state.mkdir(); apk = root / 'running.apk'
            def engine(native):
                with zipfile.ZipFile(apk, 'w') as archive:
                    archive.writestr('classes.dex', native)
                    archive.writestr('classes3.dex', b'messageplus-settings-photo-v1 winterx/messages/MessagePlus')
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
                engine(b'old native engine')
                self.assertFalse(request(1, 'install_package', filename='messages.springys')['ok'])
                self.assertFalse((ruby / 'messageplus.enabled').exists())
                engine(b'winterx/messages/MessagePlus')
                reply = request(2, 'install_package', filename='messages.springys')
                self.assertTrue(reply['ok'], reply); self.assertFalse(reply['restartRequired'])
                self.assertTrue((ruby / 'messageplus.enabled').is_file())
                reply = request(3, 'remove_package', packageId=meta['id'])
                self.assertTrue(reply['ok'], reply); self.assertFalse((ruby / 'messageplus.enabled').exists())
                with patch.object(safe_mode.control, 'spring_pids', return_value=[42, 43]):
                    self.assertFalse(request(4, 'install_package', filename='messages.springys')['ok'])
                with patch.object(safe_mode.control, 'is_overlay_process', return_value=False):
                    self.assertFalse(request(5, 'install_package', filename='messages.springys')['ok'])
                stop.assert_not_called(); start.assert_not_called()
            for path, content in protected.items(): self.assertEqual(path.read_bytes(), content)
