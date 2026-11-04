import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import tweak_runtime


class CapabilityTests(unittest.TestCase):
    def test_missing_or_old_engine_is_not_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            apk = Path(tmp) / 'engine.apk'
            self.assertFalse(tweak_runtime.supported_by(apk))
            with zipfile.ZipFile(apk, 'w') as archive:
                archive.writestr('classes.dex', b'old engine')
                archive.writestr('classes3.dex', b'winterx/tweaks/TweakHost winterx/tweaks/TweakSettings')
            self.assertFalse(tweak_runtime.supported_by(apk))
            self.assertFalse(tweak_runtime.coloredbar_supported_by(apk))

    def test_active_engine_requires_matching_checksum_and_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            apk = state / 'engine.apk'
            with zipfile.ZipFile(apk, 'w') as archive:
                archive.writestr('classes.dex', b'winterxCreate winterx/coloredbar/ColoredBar')
                archive.writestr('classes3.dex', b'winterx/tweaks/TweakHost winterx/tweaks/TweakSettings coloredbar.exclusions.json')
            sha = hashlib.sha256(apk.read_bytes()).hexdigest()
            self.assertTrue(tweak_runtime.supported_by(apk))
            self.assertTrue(tweak_runtime.coloredbar_supported_by(apk))
            (state / 'active.json').write_text(json.dumps({'apk': str(apk), 'apk_sha256': sha, 'pid': 123}))
            self.assertIsNone(tweak_runtime.active_engine(state, lambda *args: False))
            self.assertEqual(tweak_runtime.active_engine(state, lambda *args: True), apk)
            (state / 'active.json').write_text(json.dumps({'apk': str(apk), 'apk_sha256': 'bad', 'pid': 123}))
            self.assertIsNone(tweak_runtime.active_engine(state, lambda *args: True))


if __name__ == '__main__':
    unittest.main()
