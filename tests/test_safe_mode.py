import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'patches'))
import safe_mode


class SafeModeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data, self.state = self.root / 'data', self.root / 'state'
        self.data.mkdir(); self.state.mkdir()
        self.apk = self.root / 'winterx.apk'
        self.apk.write_bytes(b'verified test build')
        self.sha = hashlib.sha256(self.apk.read_bytes()).hexdigest()
        (self.state / 'active.json').write_text(json.dumps({'pid': 42, 'apk': str(self.apk), 'apk_sha256': self.sha}))
        self.marker = self.data / 'files/ruby/safe-mode.enabled'

    def tearDown(self):
        self.temp.cleanup()

    def run_change(self, enabled, fail=False):
        class Child:
            pid = 43
            def poll(self): return None
        child = Child()
        def flow(marker, stop, start, stop_child, restore, **kwargs):
            kwargs['before_start']()
            start()
            if fail:
                restore()
                return {'ok': False, 'message': 'recovered'}
            return {'ok': True, 'message': 'ok'}
        with patch.object(safe_mode.control, 'spring_pids', return_value=[42]), \
             patch.object(safe_mode.control, 'is_overlay_process', return_value=True), \
             patch.object(safe_mode.control, 'snapshot_app_data'), \
             patch.object(safe_mode.control, 'start_overlay', return_value=child), \
             patch.object(safe_mode.overlay_flow, 'run', side_effect=flow):
            return safe_mode.set_safe_mode(self.data, self.state, self.apk, self.sha, enabled)

    def test_enable_and_disable(self):
        result = self.run_change(True)
        self.assertTrue(result['ok']); self.assertTrue(self.marker.exists())
        self.assertTrue(result['safeMode'])
        active = json.loads((self.state / 'active.json').read_text())
        self.assertEqual(active['pid'], 43)
        active['pid'] = 42
        (self.state / 'active.json').write_text(json.dumps(active))
        result = self.run_change(False)
        self.assertFalse(result['safeMode']); self.assertFalse(self.marker.exists())

    def test_failed_respring_restores_marker_and_pid(self):
        result = self.run_change(True, fail=True)
        self.assertFalse(result['ok']); self.assertFalse(self.marker.exists())
        self.assertEqual(json.loads((self.state / 'active.json').read_text())['pid'], 43)

    def test_modified_apk_is_rejected(self):
        self.apk.write_bytes(b'tampered')
        with self.assertRaises(ValueError):
            self.run_change(True)
        self.assertFalse(self.marker.exists())


if __name__ == '__main__':
    unittest.main()
