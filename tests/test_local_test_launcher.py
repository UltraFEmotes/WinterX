import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import launch_local_test as launcher


class LocalTestLauncherTests(unittest.TestCase):
    def test_combined_engine_is_pinned_and_old_alpha8_plan_is_rejected(self):
        self.assertEqual(launcher.TEST_SHA, '71fc52605f2d32294597dd9496956e72b3a02d485b4b233703087d6a75ae980d')
        self.assertEqual(launcher.bundle.UI_FIX_SHA, '3ca1213cf316081d958e2871caa367578595bfe5cb3de4cfd625972921c60169')
        self.assertEqual(launcher.bundle.FETCH_SHA, 'a1de2419994ccfa009e181af2d1ad7471332613de0af1e30c5d6464ca67e0987')
        with patch.object(launcher.control, 'spring_pids', return_value=[]), \
             patch.object(launcher.control, 'start_overlay') as start:
            with self.assertRaises(ValueError):
                launcher.launch({'status': 'prepared', 'apk_sha256': 'e1fc328e5cb794f8d8ebbac713e9cfaba6d7db08af14c5c13345c80137b6c6db'})
            start.assert_not_called()

    def test_running_spring_is_never_stopped_or_replaced(self):
        with patch.object(launcher.control, 'spring_pids', return_value=[42]), \
             patch.object(launcher.control, 'stop_spring') as stop, \
             patch.object(launcher.control, 'start_overlay') as start:
            with self.assertRaises(RuntimeError): launcher.launch({})
            stop.assert_not_called(); start.assert_not_called()

    def test_all_explicit_pins_verify_without_changing_current_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); apk = root / 'engine.apk'; apk.write_bytes(b'isolated fixture')
            for sha in (launcher.TEST_SHA, launcher.bundle.UI_FIX_SHA, launcher.bundle.FETCH_SHA):
                plan = {'status': 'prepared', 'apk': str(apk), 'apk_sha256': sha, 'backup': str(root), 'bundled_packages': []}
                with self.subTest(sha=sha), patch.object(launcher.control, 'spring_pids', return_value=[]), \
                     patch.object(launcher.jailbreak, 'digest', return_value=sha), \
                     patch.object(launcher.bundle, 'verify') as packages, \
                     patch.object(launcher.control, 'start_overlay') as start:
                    self.assertEqual(launcher.verify(plan), apk)
                    packages.assert_called_once(); start.assert_not_called()
            with patch.object(launcher.control, 'spring_pids', return_value=[]), \
                 patch.object(launcher.jailbreak, 'digest', return_value=launcher.TEST_SHA):
                with self.assertRaises(ValueError): launcher.verify(plan)

    def test_unprepared_or_changed_apk_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); apk = root / 'engine.apk'; apk.write_bytes(b'test')
            plan = {'status': 'prepared', 'apk': str(apk), 'apk_sha256': launcher.TEST_SHA, 'backup': str(root)}
            with patch.object(launcher.control, 'spring_pids', return_value=[]), \
                 patch.object(launcher.control, 'start_overlay') as start:
                with self.assertRaises(ValueError): launcher.launch({})
                with self.assertRaises(ValueError): launcher.launch(plan)
                start.assert_not_called()

    def test_receipt_records_the_actual_engine_without_restarting(self):
        for sha in (launcher.TEST_SHA, launcher.bundle.UI_FIX_SHA, launcher.bundle.FETCH_SHA):
            with self.subTest(sha=sha), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); state = root / 'state'; data = root / 'data'
                (state / 'overlay/android').mkdir(parents=True)
                boot = data / 'files/ruby/boot-ok-v1'; boot.parent.mkdir(parents=True)
                boot.touch()
                child = Mock(pid=123); child.poll.return_value = None
                def start(*args):
                    self.assertFalse(boot.exists(), 'stale receipt accepted')
                    boot.touch()
                    return child
                with patch.object(launcher, 'verify', return_value=root / 'engine.apk'), \
                     patch.object(launcher.jailbreak, 'STATE', state), patch.object(launcher.jailbreak, 'DATA', data), \
                     patch.object(launcher.control, 'start_overlay', side_effect=start), \
                     patch.object(launcher.control, 'spring_pids', return_value=[123]), \
                     patch.object(launcher.control, 'is_overlay_process', return_value=True), \
                     patch.object(launcher.jailbreak, 'digest', return_value=sha), \
                     patch.object(launcher.control, 'stop_spring') as stop, \
                     patch.object(launcher.time, 'monotonic', side_effect=[0, 0, 0, 0, 4, 4]), \
                     patch.object(launcher.time, 'sleep'):
                    reply = launcher.launch({'backup': str(root), 'apk_sha256': sha}, timeout=10)
                    self.assertEqual(reply['pid'], 123)
                    record = json.loads((state / 'active.json').read_text())
                    self.assertTrue(record['localTest'])
                    self.assertEqual(record, reply)
                    self.assertEqual(record['apk_sha256'], sha)
                    child.terminate.assert_not_called(); stop.assert_not_called()

    def test_fresh_receipt_cannot_authorize_another_or_duplicate_engine(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); state = root / 'state'; data = root / 'data'
            (state / 'overlay/android').mkdir(parents=True)
            boot = data / 'files/ruby/boot-ok-v1'; boot.parent.mkdir(parents=True)
            child = Mock(pid=123); child.poll.return_value = None
            def start(*args):
                boot.touch(); return child
            for pids, matched in (([123, 124], True), ([123], False)):
                with self.subTest(pids=pids, matched=matched), \
                     patch.object(launcher, 'verify', return_value=root / 'engine.apk'), \
                     patch.object(launcher.jailbreak, 'STATE', state), patch.object(launcher.jailbreak, 'DATA', data), \
                     patch.object(launcher.control, 'start_overlay', side_effect=start), \
                     patch.object(launcher.control, 'spring_pids', return_value=pids), \
                     patch.object(launcher.control, 'is_overlay_process', return_value=matched), \
                     patch.object(launcher.control, 'stop_spring') as stop, \
                     patch.object(launcher.time, 'monotonic', side_effect=[0, 0, 0, 0, 4, 4]), \
                     patch.object(launcher.time, 'sleep'):
                    with self.assertRaisesRegex(RuntimeError, 'only running test engine'):
                        launcher.launch({'backup': str(root), 'apk_sha256': launcher.TEST_SHA}, timeout=10)
                    self.assertFalse((state / 'active.json').exists()); stop.assert_not_called()


if __name__ == '__main__':
    unittest.main()
