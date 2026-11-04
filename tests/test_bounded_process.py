from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from bounded_process import OutputLimitError, run


class BoundedProcessTests(unittest.TestCase):
    def test_binary_round_trip_and_nonzero_exit(self):
        payload = b'\x00\xff\r\n\x80'
        result = run([sys.executable, '-c', 'import sys; sys.stdout.buffer.write(sys.stdin.buffer.read()); sys.stderr.buffer.write(b"error"); sys.exit(7)'], input=payload)
        self.assertEqual(result.stdout, payload); self.assertEqual(result.stderr, b'error')
        self.assertEqual(result.returncode, 7)
        with self.assertRaises(subprocess.CalledProcessError):
            run([sys.executable, '-c', 'raise SystemExit(2)'], check=True)

    def test_stdout_and_stderr_overflow_fail_with_bounded_capture(self):
        for stream in ('stdout', 'stderr'):
            with self.subTest(stream=stream), self.assertRaises(OutputLimitError):
                run([sys.executable, '-c', f'import sys; sys.{stream}.buffer.write(b"x" * 200000)'], output_limit=100, error_limit=100)

    def test_stalled_child_is_terminated_at_deadline(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            run([sys.executable, '-c', 'import time; time.sleep(30)'], timeout=.2)

    def test_invalid_input_and_host_shell_are_refused(self):
        for options in ({'shell': True}, {'input': 'text'}, {'timeout': 0}, {'output_limit': -1}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                run(['never-executed'], **options)
