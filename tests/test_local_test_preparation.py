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
                         (preparation.bundle.FETCH_ENGINE, preparation.bundle.FETCH_SHA),
                         (preparation.bundle.RENDER_ACTIONS_ENGINE, preparation.bundle.RENDER_ACTIONS_SHA),
                         (preparation.bundle.SSH_TERMINAL_ENGINE, preparation.bundle.SSH_TERMINAL_SHA)):
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

    def test_render_actions_upgrade_preserves_every_persisted_entry_and_never_launches_apps(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name).resolve(); state = root / 'state'; data = root / 'data'
            (state / 'overlay/android').mkdir(parents=True)
            for relative in (*preparation.PROTECTED, 'ruby/animaper.mode', 'ruby/ssh/authorized_keys', 'ruby/ssh/host-key.ser',
                             'ruby/ssh/inbox/user-upload.sapp', 'ruby/snowyhome/preferences.json', 'sapps-data/example/files/current',
                             'ruby/safe-mode.enabled'):
                file = data / 'files' / relative; file.parent.mkdir(parents=True, exist_ok=True); file.write_bytes(('keep ' + relative).encode())
            before = preparation.inventory(data)
            previous = {'status': 'prepared', 'apk_sha256': preparation.bundle.UI_FIX_SHA}
            (state / 'local-test.json').write_text(json.dumps(previous)); (state / 'active.json').write_text('{"pid":42}')
            apk = root / 'combined.apk'; apk.write_bytes(b'fixture combined engine'); sha = hashlib.sha256(apk.read_bytes()).hexdigest()
            with patch.object(preparation.launcher.jailbreak, 'STATE', state), patch.object(preparation.launcher.jailbreak, 'DATA', data), \
                 patch.object(preparation.bundle, 'RENDER_ACTIONS_SHA', sha), patch.object(preparation.bundle, 'inputs', return_value=[]), \
                 patch.object(preparation.bundle, 'activate'), patch.object(preparation.bundle, 'verify'), \
                 patch.object(preparation.launcher.control, 'spring_pids', return_value=[]), \
                 patch.object(preparation.launcher.control, 'start_overlay') as start, patch.object(preparation.launcher.control, 'stop_spring') as stop:
                plan = preparation.prepare(apk, sha)
            self.assertEqual(preparation.inventory(data), before)
            self.assertEqual(preparation.inventory(Path(plan['backup'])), before)
            self.assertEqual(plan['previous_test'], previous); self.assertEqual(plan['apk_sha256'], sha)
            self.assertTrue(plan['safe_mode_preserved']); self.assertFalse(plan['engine_launched'])
            start.assert_not_called(); stop.assert_not_called()

    def test_explicit_engine_flags_are_mutually_exclusive(self):
        import subprocess
        import itertools
        script = Path(preparation.__file__)
        for first, other in itertools.combinations(('--ui-fix', '--neofetch', '--render-actions', '--ssh-terminal'), 2):
            result = subprocess.run([sys.executable, str(script), first, other], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('not allowed with argument', result.stderr)

    def test_retargeted_platform_alias_refuses_selection_and_retains_both_data_roots(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name).resolve(); state = root / 'state'; data = root / 'native'; replacement = root / 'new-native'; alias = root / 'platform.data'
            (state / 'overlay/android').mkdir(parents=True)
            for folder, content in ((data, 'old data'), (replacement, 'new data')):
                (folder / 'files/ruby').mkdir(parents=True); (folder / 'files/ios6_pages.json').write_text(content)
            alias.symlink_to(data, target_is_directory=True)
            previous = b'{"status":"prepared","apk_sha256":"previous"}'; (state / 'local-test.json').write_bytes(previous)
            apk = root / 'combined.apk'; apk.write_bytes(b'fixture'); sha = hashlib.sha256(apk.read_bytes()).hexdigest()
            snapshot = preparation.launcher.control.snapshot_app_data
            def retarget(source, backup):
                snapshot(source, backup); alias.unlink(); alias.symlink_to(replacement, target_is_directory=True)
            with patch.object(preparation.launcher.jailbreak, 'STATE', state), patch.object(preparation.launcher.jailbreak, 'DATA', alias), \
                 patch.object(preparation.bundle, 'RENDER_ACTIONS_SHA', sha), patch.object(preparation.bundle, 'inputs', return_value=[]), \
                 patch.object(preparation.bundle, 'activate') as activate, patch.object(preparation.bundle, 'verify'), \
                 patch.object(preparation.launcher.control, 'snapshot_app_data', side_effect=retarget), \
                 patch.object(preparation.launcher.control, 'spring_pids', return_value=[]):
                with self.assertRaisesRegex(RuntimeError, 'data-root alias changed'):
                    preparation.prepare(apk, sha)
                activate.assert_not_called()
            self.assertEqual((state / 'local-test.json').read_bytes(), previous)
            self.assertEqual((data / 'files/ios6_pages.json').read_text(), 'old data')
            self.assertEqual((replacement / 'files/ios6_pages.json').read_text(), 'new data')
