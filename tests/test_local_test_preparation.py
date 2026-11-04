import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import prepare_local_test as preparation


class LocalTestPreparationTests(unittest.TestCase):
    def test_backup_preserves_history_layout_and_state_before_activation_without_launch(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name).resolve(); state = root / 'state'; data = root / 'data'
            (state / 'overlay/android').mkdir(parents=True)
            (data / 'files/ruby').mkdir(parents=True)
            for relative in preparation.PROTECTED:
                (data / 'files' / relative).write_bytes(relative.encode())
            old = {'status': 'prepared', 'apk_sha256': 'old', 'packages': [{'id': 'existing-code'}]}
            (state / 'local-test.json').write_text(json.dumps(old))
            receipt = b'{"pid":42,"apk":"old"}'
            (state / 'active.json').write_bytes(receipt)
            apk = root / 'new.apk'; apk.write_bytes(b'new engine')
            with patch.object(preparation.launcher.jailbreak, 'STATE', state), \
                 patch.object(preparation.launcher.jailbreak, 'DATA', data), \
                 patch.object(preparation.launcher, 'TEST_SHA', hashlib.sha256(apk.read_bytes()).hexdigest()), \
                 patch.object(preparation.bundle, 'inputs', return_value=[{'id': 'test'}]), \
                 patch.object(preparation.bundle, 'activate') as activate, \
                 patch.object(preparation.bundle, 'verify'), \
                 patch.object(preparation.launcher.control, 'spring_pids', return_value=[]), \
                 patch.object(preparation.launcher.control, 'start_overlay') as start, \
                 patch.object(preparation.launcher.control, 'stop_spring') as stop:
                plan = preparation.prepare(apk)
                self.assertEqual(plan['previous_test'], old)
                self.assertEqual(plan['layout_sha256'], preparation.hashes(data / 'files'))
                self.assertEqual(preparation.hashes(Path(plan['backup']) / 'files'), plan['layout_sha256'])
                self.assertEqual((state / 'active.json').read_bytes(), receipt)
                self.assertEqual((Path(plan['backup']) / 'active-before.json').read_bytes(), receipt)
                self.assertFalse(plan['engine_launched']); self.assertTrue(plan['draft_tweaks_installed'])
                activate.assert_called_once()
                start.assert_not_called(); stop.assert_not_called()

    def test_running_session_cannot_be_backed_up_or_reselected(self):
        with patch.object(preparation.launcher.control, 'spring_pids', return_value=[42]), \
             patch.object(preparation.launcher.control, 'snapshot_app_data') as backup, \
             patch.object(preparation.launcher.control, 'stop_spring') as stop:
            with self.assertRaises(RuntimeError): preparation.prepare(Path('not-read.apk'))
            backup.assert_not_called(); stop.assert_not_called()
