"""Stopped-session core preparation/launch using disposable files and non-acting process controls."""
import hashlib
import itertools
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import mac_core


class MacCoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.base = self.root / 'platform'; self.state = self.root / 'host-state'; self.state.mkdir()
        self.data = self.base / 'data/data/com.guille.spring_0.8.1'
        (self.data / 'files/ruby').mkdir(parents=True); (self.data / 'shared_prefs').mkdir()
        (self.base / 'data/system').mkdir(); (self.base / 'sdcard').mkdir()
        (self.data / 'files/ios6_pages.json').write_bytes(b'current layout')
        (self.data / 'files/ruby/animaper.mode').write_bytes(b'orbit\n')
        (self.data / 'shared_prefs/fixture.xml').write_bytes(b'fixture preference')
        self.original = self.root / 'original.apk'; self.original.write_bytes(b'original fixture')
        self.apk = self.root / 'core.apk'; self.apk.write_bytes(b'core fixture')
        self.core = {'core': str(self.root), 'apk': str(self.apk), 'apk_sha256': hashlib.sha256(self.apk.read_bytes()).hexdigest(), 'runtimeAbi': mac_core.ABI}
        config = patch.multiple(mac_core.jailbreak, BASE=self.base, DATA=self.data, STATE=self.state,
                                ORIGINAL=self.original, ORIGINAL_SHA=hashlib.sha256(self.original.read_bytes()).hexdigest())
        config.start(); self.addCleanup(config.stop)
        self.checked = patch.object(mac_core, 'checked_core', return_value=self.core).start()
        self.addCleanup(patch.stopall)
        self.running = False
        self.pids = patch.object(mac_core.control, 'spring_pids', side_effect=lambda: [42] if self.running else []).start()
        self.start = patch.object(mac_core.control, 'start_overlay').start()
        patch.object(mac_core.control, 'stop_spring', side_effect=AssertionError('Must not stop an existing session')).start()
        patch.object(mac_core.control, 'start_original', side_effect=AssertionError('Must not start a competing session')).start()

    def test_prepare_keeps_all_data_history_and_installs_no_packages(self):
        previous = b'{"previous_test":"keep"}'
        (self.state / 'local-test.json').write_bytes(previous)
        before = mac_core.inventory(self.data)
        plan = mac_core.prepare(self.root)
        self.assertEqual(mac_core.inventory(self.data), before)
        self.assertEqual(mac_core.inventory(Path(plan['backup'])), before)
        self.assertEqual((self.state / 'local-test.json').read_bytes(), previous)
        self.assertEqual(plan['preinstalledTweaks'], [])
        self.assertFalse((self.data / 'files/winterx-tweaks').exists())
        self.start.assert_not_called()

    def test_running_session_is_refused_before_backup_or_selection(self):
        self.running = True
        with self.assertRaisesRegex(RuntimeError, 'Fully quit'): mac_core.prepare(self.root)
        self.checked.assert_not_called(); self.start.assert_not_called()
        self.assertFalse((self.state / 'core-plan.json').exists())
        self.assertFalse((self.state / 'backups').exists())

    def test_data_change_during_backup_never_restores_over_current_data(self):
        original = mac_core.control.snapshot_app_data
        def changed(data, backup):
            original(data, backup)
            (data / 'files/ios6_pages.json').write_bytes(b'newer external layout')
        with patch.object(mac_core.control, 'snapshot_app_data', side_effect=changed):
            with self.assertRaisesRegex(RuntimeError, 'changed during backup'): mac_core.prepare(self.root)
        self.assertEqual((self.data / 'files/ios6_pages.json').read_bytes(), b'newer external layout')
        self.assertFalse((self.state / 'core-plan.json').exists()); self.start.assert_not_called()

    def launched_fixture(self, duplicate=False):
        mac_core.prepare(self.root)
        child = Mock(pid=42); child.poll.return_value = None
        def start(*args):
            self.running = True
            (self.data / 'files/ruby/boot-ok-v1').write_bytes(b'fresh receipt')
            return child
        self.start.side_effect = start
        self.pids.side_effect = lambda: ([42, 43] if duplicate else [42]) if self.running else []
        ticks = itertools.count()
        with patch.object(mac_core.control, 'is_overlay_process', return_value=True), \
             patch.object(mac_core.time, 'monotonic', side_effect=lambda: float(next(ticks))), \
             patch.object(mac_core.time, 'sleep'):
            if duplicate:
                with self.assertRaisesRegex(RuntimeError, 'sole running core'): mac_core.launch()
                child.terminate.assert_called_once()
                self.assertFalse((self.state / 'active.json').exists())
            else:
                returned, record = mac_core.launch()
                self.assertIs(returned, child); self.assertTrue(record['coreOnly'])
                child.terminate.assert_not_called()
                self.assertEqual(json.loads((self.state / 'active.json').read_text())['apk_sha256'], self.core['apk_sha256'])
        self.start.assert_called_once()

    def test_launch_records_only_its_actual_fresh_core(self):
        self.launched_fixture()

    def test_duplicate_process_refuses_receipt_and_cleans_up_only_owned_child(self):
        self.launched_fixture(duplicate=True)


if __name__ == '__main__': unittest.main()
