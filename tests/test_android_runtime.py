import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from android_runtime import RootRuntime
from private_files import AccessError


class AndroidRuntimeTests(unittest.TestCase):
    def test_forward_must_belong_to_the_explicit_device_and_loopback_server(self):
        with tempfile.TemporaryDirectory() as name:
            runtime = RootRuntime('emulator-5582', Path(name))
            runtime.store.runner = Mock(return_value=subprocess.CompletedProcess([], 0,
                b'emulator-5582 tcp:27048 tcp:27042\n', b''))
            runtime.verify_transport()
            self.assertEqual(runtime.store.runner.call_args.args[0], ['adb', 'forward', '--list'])
            for data in (b'', b'emulator-5580 tcp:27048 tcp:27042\n', b'emulator-5582 tcp:27048 tcp:9999\n',
                         b'emulator-5582 tcp:27048 tcp:27042\nemulator-5580 tcp:27048 tcp:27042\n'):
                runtime.store.runner.return_value = subprocess.CompletedProcess([], 0, data, b'')
                with self.assertRaises(AccessError): runtime.verify_transport()

    def test_existing_process_is_never_stopped_by_staging_or_launch_guards(self):
        with tempfile.TemporaryDirectory() as name:
            runtime = RootRuntime('emulator-5582', Path(name))
            runtime.shell = Mock(return_value='42\n')
            with self.assertRaisesRegex(AccessError, 'Fully close Spring'): runtime.stopped()
            self.assertEqual(runtime.shell.call_count, 1)
            self.assertNotIn('force-stop', runtime.shell.call_args.args[0])
            self.assertNotIn('kill', runtime.shell.call_args.args[0])


if __name__ == '__main__': unittest.main()
