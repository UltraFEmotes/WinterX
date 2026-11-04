import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import launch_local_test as launcher


class LocalTestLauncherTests(unittest.TestCase):
    def test_alpha8_is_pinned_and_old_alpha6_plan_is_rejected(self):
        self.assertEqual(launcher.TEST_SHA, 'e1fc328e5cb794f8d8ebbac713e9cfaba6d7db08af14c5c13345c80137b6c6db')
        with patch.object(launcher.control, 'spring_pids', return_value=[]), \
             patch.object(launcher.control, 'start_overlay') as start:
            with self.assertRaises(ValueError):
                launcher.launch({'status': 'prepared', 'apk_sha256': '6bdbd8e566b6ad436cb73d57330be17f360ea3832e5b70bba5cc221822604157'})
            start.assert_not_called()

    def test_running_spring_is_never_stopped_or_replaced(self):
        with patch.object(launcher.control, 'spring_pids', return_value=[42]), \
             patch.object(launcher.control, 'stop_spring') as stop, \
             patch.object(launcher.control, 'start_overlay') as start:
            with self.assertRaises(RuntimeError): launcher.launch({})
            stop.assert_not_called(); start.assert_not_called()

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
        with tempfile.TemporaryDirectory() as tmp:
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
                 patch.object(launcher.jailbreak, 'digest', return_value=launcher.TEST_SHA), \
                 patch.object(launcher.control, 'stop_spring') as stop, \
                 patch.object(launcher.time, 'monotonic', side_effect=[0, 0, 0, 0, 4, 4]), \
                 patch.object(launcher.time, 'sleep'):
                reply = launcher.launch({'backup': str(root)}, timeout=10)
                self.assertEqual(reply['pid'], 123)
                self.assertTrue(json.loads((state / 'active.json').read_text())['localTest'])
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
                        launcher.launch({'backup': str(root)}, timeout=10)
                    self.assertFalse((state / 'active.json').exists()); stop.assert_not_called()


if __name__ == '__main__':
    unittest.main()
