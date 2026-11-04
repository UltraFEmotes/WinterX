import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import launch_local_test as launcher


class LocalTestLauncherTests(unittest.TestCase):
    def test_alpha6_is_pinned_and_old_alpha4_plan_is_rejected(self):
        self.assertEqual(launcher.TEST_SHA, '6bdbd8e566b6ad436cb73d57330be17f360ea3832e5b70bba5cc221822604157')
        with patch.object(launcher.control, 'spring_pids', return_value=[]), \
             patch.object(launcher.control, 'start_overlay') as start:
            with self.assertRaises(ValueError):
                launcher.launch({'status': 'prepared', 'apk_sha256': '6bb01ac880241c0b7337abb7117505a9727d2fbd6993c76721682d427092f9c4'})
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
                 patch.object(launcher.control, 'stop_spring') as stop, \
                 patch.object(launcher.time, 'monotonic', side_effect=[0, 0, 0, 0, 4, 4]), \
                 patch.object(launcher.time, 'sleep'):
                reply = launcher.launch({'backup': str(root)}, timeout=10)
                self.assertEqual(reply['pid'], 123)
                self.assertTrue(json.loads((state / 'active.json').read_text())['localTest'])
                child.terminate.assert_not_called(); stop.assert_not_called()


if __name__ == '__main__':
    unittest.main()
