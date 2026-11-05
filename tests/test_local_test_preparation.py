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

    def test_explicit_new_engines_cannot_be_selected_while_running_or_with_an_unpinned_hash(self):
        for apk, sha in ((preparation.bundle.UI_FIX_ENGINE, preparation.bundle.UI_FIX_SHA),
                         (preparation.bundle.FETCH_ENGINE, preparation.bundle.FETCH_SHA)):
            with self.subTest(apk=apk), patch.object(preparation.launcher.control, 'spring_pids', return_value=[42]), \
                 patch.object(preparation.launcher.control, 'snapshot_app_data') as backup:
                with self.assertRaises(RuntimeError): preparation.prepare(apk, sha)
                backup.assert_not_called()
        with patch.object(preparation.launcher.control, 'spring_pids', return_value=[]), \
             patch.object(preparation.launcher.control, 'snapshot_app_data') as backup:
            with self.assertRaisesRegex(ValueError, 'explicitly pinned'):
                preparation.prepare(Path('not-read.apk'), '0' * 64)
            backup.assert_not_called()

    def test_neofetch_preparation_preserves_private_keys_preferences_packs_and_previous_plan(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name).resolve(); state = root / 'state'; data = root / 'data'
            (state / 'overlay/android').mkdir(parents=True)
            for relative in (*preparation.PROTECTED, 'ruby/ssh/authorized_keys', 'ruby/ssh/host-key.ser',
                             'ruby/messageplus/photo-quality', 'ruby/snowyhome/preferences.json',
                             'ruby/snowyhome/inbox/existing.zip', 'ruby/snowyhome/packs/existing/manifest.json',
                             'ruby/tweaks/existing/state.json'):
                path = data / 'files' / relative; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(('keep ' + relative).encode())
            old = {'status': 'prepared', 'apk_sha256': preparation.bundle.UI_FIX_SHA, 'packages': [{'id': 'existing-code'}]}
            (state / 'local-test.json').write_text(json.dumps(old))
            receipt = b'{"pid":42,"apk":"previous engine"}'; (state / 'active.json').write_bytes(receipt)
            apk = root / 'neofetch.apk'; apk.write_bytes(b'isolated info-engine fixture')
            sha = hashlib.sha256(apk.read_bytes()).hexdigest(); before = preparation.inventory(data)
            with patch.object(preparation.launcher.jailbreak, 'STATE', state), \
                 patch.object(preparation.launcher.jailbreak, 'DATA', data), \
                 patch.object(preparation.bundle, 'FETCH_SHA', sha), \
                 patch.object(preparation.bundle, 'inputs', return_value=[{'id': 'pinned fixture'}]), \
                 patch.object(preparation.bundle, 'activate') as activate, patch.object(preparation.bundle, 'verify'), \
                 patch.object(preparation.launcher.control, 'spring_pids', return_value=[]), \
                 patch.object(preparation.launcher.control, 'start_overlay') as start, \
                 patch.object(preparation.launcher.control, 'stop_spring') as stop:
                plan = preparation.prepare(apk, sha)
                self.assertEqual(plan['apk_sha256'], sha); self.assertEqual(plan['previous_test'], old)
                self.assertEqual(preparation.inventory(data), before)
                self.assertEqual(preparation.inventory(Path(plan['backup'])), before)
                self.assertEqual((state / 'active.json').read_bytes(), receipt)
                self.assertTrue(plan['persisted_data_verified']); self.assertFalse(plan['engine_launched'])
                activate.assert_called_once(); start.assert_not_called(); stop.assert_not_called()

    def test_neofetch_does_not_select_or_restore_a_backup_if_existing_keys_change(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name).resolve(); state = root / 'state'; data = root / 'data'
            (state / 'overlay/android').mkdir(parents=True)
            keys = data / 'files/ruby/ssh/authorized_keys'; keys.parent.mkdir(parents=True)
            keys.write_bytes(b'original private configuration')
            previous = b'{"status":"prepared","apk_sha256":"previous"}'; (state / 'local-test.json').write_bytes(previous)
            apk = root / 'neofetch.apk'; apk.write_bytes(b'isolated info-engine fixture')
            sha = hashlib.sha256(apk.read_bytes()).hexdigest()
            with patch.object(preparation.launcher.jailbreak, 'STATE', state), \
                 patch.object(preparation.launcher.jailbreak, 'DATA', data), \
                 patch.object(preparation.bundle, 'FETCH_SHA', sha), \
                 patch.object(preparation.bundle, 'inputs', return_value=[{'id': 'pinned fixture'}]), \
                 patch.object(preparation.bundle, 'activate', side_effect=lambda *args: keys.write_bytes(b'external edit')), \
                 patch.object(preparation.bundle, 'verify'), \
                 patch.object(preparation.launcher.control, 'spring_pids', return_value=[]), \
                 patch.object(preparation.launcher.control, 'start_overlay') as start, \
                 patch.object(preparation.launcher.control, 'stop_spring') as stop:
                with self.assertRaisesRegex(RuntimeError, 'Persisted data changed outside'):
                    preparation.prepare(apk, sha)
                self.assertEqual((state / 'local-test.json').read_bytes(), previous)
                self.assertEqual(keys.read_bytes(), b'external edit', 'backup must not erase an external edit')
                backups = list((state / 'backups').iterdir()); self.assertEqual(len(backups), 1)
                self.assertEqual((backups[0] / 'files/ruby/ssh/authorized_keys').read_bytes(), b'original private configuration')
                start.assert_not_called(); stop.assert_not_called()
