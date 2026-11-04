import errno
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import file_lock


class FileLockTests(unittest.TestCase):
    def test_real_process_contention_and_release(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / 'registry.lock'
            program = ('import sys; sys.path.insert(0, sys.argv[1]); '
                       'from file_lock import exclusive_lock; '
                       'with_lock=exclusive_lock(sys.argv[2], timeout=0); '
                       'with_lock.__enter__(); with_lock.__exit__(None,None,None)')
            command = [sys.executable, '-c', program, str(Path(file_lock.__file__).parent), str(path)]
            with file_lock.exclusive_lock(path):
                child = subprocess.run(command, capture_output=True)
                self.assertNotEqual(child.returncode, 0)
                self.assertIn(b'TimeoutError', child.stderr)
            child = subprocess.run(command, capture_output=True)
            self.assertEqual(child.returncode, 0, child.stderr)
            self.assertTrue(path.exists())

    def test_windows_byte_lock_api_and_exception_release(self):
        calls = []
        def locking(fd, mode, length):
            calls.append((mode, length, os.lseek(fd, 0, os.SEEK_CUR), os.fstat(fd).st_size))
        win = SimpleNamespace(LK_NBLCK=2, LK_UNLCK=0, locking=locking)
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / 'new.lock'
            with patch.object(file_lock, 'os', SimpleNamespace(name='nt', fstat=os.fstat)), patch.dict(sys.modules, msvcrt=win):
                with self.assertRaisesRegex(RuntimeError, 'caller failed'):
                    with file_lock.exclusive_lock(path):
                        raise RuntimeError('caller failed')
            self.assertEqual(calls, [(2, 1, 0, 1), (0, 1, 0, 1)])
            self.assertEqual(path.read_bytes(), b'\0')

    def test_windows_timeout_does_not_unlock_unacquired_lock(self):
        calls = []
        def locking(fd, mode, length):
            calls.append(mode)
            raise OSError(errno.EACCES, 'busy')
        win = SimpleNamespace(LK_NBLCK=2, LK_UNLCK=0, locking=locking)
        with tempfile.TemporaryDirectory() as name:
            with patch.object(file_lock, 'os', SimpleNamespace(name='nt', fstat=os.fstat)), patch.dict(sys.modules, msvcrt=win):
                with self.assertRaises(TimeoutError):
                    with file_lock.exclusive_lock(Path(name) / 'lock', timeout=0):
                        self.fail('Acquired a busy lock')
            self.assertEqual(calls, [2])

    def test_rejects_symlinks_and_bad_timeout(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / 'lock'
            with self.assertRaises(ValueError):
                with file_lock.exclusive_lock(path, timeout=-1):
                    pass
            if os.name != 'nt':
                path.symlink_to(Path(name) / 'other')
                with self.assertRaises(ValueError):
                    with file_lock.exclusive_lock(path):
                        pass


if __name__ == '__main__':
    unittest.main()
