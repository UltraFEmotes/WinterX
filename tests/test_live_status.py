import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'patches'))
import macapk_controls
import macapk_jailbreak
import ruby_bridge
import safe_mode


class LiveStatusTests(unittest.TestCase):
    def test_alpha8_status_and_requested_safe_mode_follow_running_engine_not_default(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); state = root / 'state'; state.mkdir()
            data = root / 'spring'; (data / 'files/ruby').mkdir(parents=True)
            (data / 'files/ruby/safe-mode.enabled').touch()
            (data / 'files/ruby/animaper.enabled').touch()
            apk = root / 'alpha8.apk'; apk.write_bytes(b'fixture engine')
            sha = hashlib.sha256(apk.read_bytes()).hexdigest()
            record = {'pid': 42, 'apk': str(apk), 'apk_sha256': sha}
            (state / 'active.json').write_text(json.dumps(record))
            app = root / 'app'; (app / 'requests').mkdir(parents=True)
            with patch.object(macapk_jailbreak, 'STATE', state), patch.object(macapk_jailbreak, 'DATA', data), \
                 patch.object(macapk_jailbreak, 'LOCAL_ALPHA8_SHA', sha), \
                 patch.object(macapk_jailbreak, 'PATCHED', root / 'default.apk'), \
                 patch.object(macapk_controls, 'spring_pids', return_value=[42]), \
                 patch.object(macapk_controls, 'is_overlay_process', return_value=True), \
                 patch.object(safe_mode, 'set_safe_mode', return_value={'ok': True, 'message': 'fixture only'}) as apply:
                ruby_bridge.update_live_status(app)
                live = json.loads((app / 'live.json').read_text())
                self.assertTrue(live['active']); self.assertTrue(live['safeModeSupported']); self.assertTrue(live['safeMode'])
                self.assertTrue(live['animaperInstalled'])
                request = app / 'requests/1-0.json'; request.write_text(json.dumps({'id':'1-0', 'action':'set_safe_mode', 'enabled':False}))
                ruby_bridge.process(request, app, root / 'inbox')
                self.assertTrue(json.loads((app / 'results/1-0.json').read_text())['ok'])
                self.assertEqual(apply.call_args.args[2:4], (apk, sha))
                for pids, digest in (([42, 43], sha), ([42], 'incorrect')):
                    (state / 'active.json').write_text(json.dumps({**record, 'apk_sha256': digest}))
                    with patch.object(macapk_controls, 'spring_pids', return_value=pids):
                        ruby_bridge.update_live_status(app)
                        live = json.loads((app / 'live.json').read_text())
                        self.assertFalse(live['active']); self.assertFalse(live['safeModeSupported']); self.assertFalse(live['safeMode'])
