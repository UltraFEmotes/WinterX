import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from private_files import AccessError, AdbFiles, ConflictError, DirectoryFiles, relative_path, write_probe


class PrivateFilesTests(unittest.TestCase):
    def test_shared_folder_binary_atomic_write_conflict_and_probe(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            layouts = root / 'ios6_pages.json'; layouts.write_bytes(b'important layout')
            positions = root / 'ruby/icon-positions-v1.json'; positions.parent.mkdir(); positions.write_bytes(b'important positions')
            store = DirectoryFiles(root)
            self.assertIsNone(store.read('ruby/test.json'))
            payload = b'\x00\xff\r\n\n\x80'
            store.write('ruby/test.json', payload, expected=None)
            self.assertEqual(store.read('ruby/test.json'), payload)
            with self.assertRaises(ConflictError):
                store.write('ruby/test.json', b'oops', expected=None)
            with self.assertRaises(ConflictError):
                store.remove('ruby/test.json', expected=b'wrong')
            with self.assertRaises(AccessError):
                store.read('ruby/test.json', limit=1)
            store.write('ruby/test.json', b'next', expected=payload)
            store.remove('ruby/test.json', expected=b'next')
            write_probe(store)
            self.assertEqual(store.list_files('ruby'), ['ruby/icon-positions-v1.json'])
            self.assertEqual(layouts.read_bytes(), b'important layout')
            self.assertEqual(positions.read_bytes(), b'important positions')

    def test_path_traversal_windows_devices_and_symlinks_refused(self):
        for value in ['', '/root', 'a//b', '../x', 'a/../b', 'a/./b', 'a\\b', 'a:b', 'a\nx', 'NUL', 'con.json', 'a/COM1.log', 'name.']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                relative_path(value)
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); store = DirectoryFiles(root)
            try:
                (root / 'link').symlink_to(root / 'outside')
            except OSError:
                if os.name == 'nt':
                    return  # Non-admin Windows may not grant symlink creation.
                raise
            for action in [lambda: store.read('link'), lambda: store.write('link', b'x', expected=None), lambda: store.list_files('link')]:
                with self.assertRaises(AccessError):
                    action()

    @staticmethod
    def runner(stdout=b'', code=0):
        return Mock(return_value=subprocess.CompletedProcess([], code, stdout, b''))

    def verified_adb(self, access='shell', root=False):
        uid = b'0' if root else b'10123'
        runner = self.runner(b'/data/user/0/com.guille.spring/files\n' + uid + b'\n10123:10123\nrw\n')
        store = AdbFiles('emulator-5554', access=access, runner=runner)
        self.assertEqual(store.verify()['owner'], 10123)
        return store, runner

    def test_explicit_device_modes_and_no_host_shell(self):
        for mode, suffix in [('shell', ['sh', '-c']), ('run-as', ['run-as', 'com.guille.spring', 'sh', '-c']), ('su', ['su', '-c'])]:
            store, runner = self.verified_adb(mode, root=mode == 'su')
            args, kwargs = runner.call_args
            self.assertEqual(args[0][0:4], ['adb', '-s', 'emulator-5554', 'exec-out'])
            self.assertEqual(args[0][4:-1], suffix)
            self.assertFalse(kwargs['shell'])
            self.assertNotIn('text', kwargs)
            self.assertEqual(kwargs['timeout'], 20)
        for serial in ['', '-a', 'a; rm', 'a\nb', None]:
            with self.assertRaises(ValueError):
                AdbFiles(serial)
        for root in ['/data', '/data/user', '/', 'relative/files', '/data/../files']:
            with self.assertRaises(ValueError):
                AdbFiles('emulator-5554', root=root)

    def test_identity_access_and_unverified_calls_fail_closed(self):
        store = AdbFiles('device', runner=self.runner())
        with self.assertRaises(AccessError):
            store.read('ruby/anything')
        for reply in [b'/data/user/0/com.guille.spring/files\n2000\n10123:10123\nrw\n',
                      b'/data/user/0/com.guille.spring/files\n0\n0:0\nrw\n',
                      b'/data/user/0/com.guille.spring/files\n0\n10123:10123\ndenied\n', b'random']:
            store = AdbFiles('device', runner=self.runner(reply))
            with self.assertRaises(AccessError):
                store.verify()
            self.assertIsNone(store.identity)

    def test_binary_read_missing_and_size_limits(self):
        store, runner = self.verified_adb()
        runner.return_value = subprocess.CompletedProcess([], 0, b'\x00\xff\r\n', b'')
        self.assertEqual(store.read('ruby/test', 4), b'\x00\xff\r\n')
        self.assertIn('head -c 5', runner.call_args.args[0][-1])
        with self.assertRaises(AccessError):
            store.read('ruby/test', 3)
        runner.return_value = subprocess.CompletedProcess([], 44, b'', b'')
        self.assertIsNone(store.read('ruby/missing'))
        runner.return_value = subprocess.CompletedProcess([], 1, b'', b'permission denied')
        with self.assertRaises(AccessError):
            store.read('ruby/test')

    def test_root_writes_preserve_owner_selinux_and_expected_hash(self):
        store, runner = self.verified_adb('su', root=True)
        runner.return_value = subprocess.CompletedProcess([], 0, b'', b'')
        store.write('ruby/coloredbar.color', b'#123456', expected=b'#C9253D')
        script = runner.call_args.args[0][-1]
        self.assertIn('chown 10123:10123', script)
        self.assertIn('restorecon -F', script)
        self.assertIn('Enforcing', script)
        self.assertIn(hashlib.sha256(b'#C9253D').hexdigest(), script)
        self.assertIn('test ! -L', script)
        self.assertIn('set -C', script)
        self.assertLess(script.index('trap '), script.index('cat >'))
        self.assertEqual(runner.call_args.kwargs['input'], b'#123456')
        self.assertNotIn('chmod 777', script)
        self.assertNotIn('setenforce', script)
        self.assertNotIn('am force-stop', script)
        runner.return_value = subprocess.CompletedProcess([], 45, b'', b'')
        with self.assertRaises(ConflictError):
            store.write('ruby/test', b'next', expected=None)

    def test_listing_is_bounded_and_confined(self):
        store, runner = self.verified_adb()
        prefix = '/data/user/0/com.guille.spring/files/'
        runner.return_value = subprocess.CompletedProcess([], 0, (prefix + 'ruby/one\0' + prefix + 'ruby/two\0').encode(), b'')
        self.assertEqual(store.list_files('ruby'), ['ruby/one', 'ruby/two'])
        with self.assertRaises(AccessError):
            store.list_files('ruby', limit=1)
        for value in [b'/data/other\0', (prefix + 'outside\0').encode(), (prefix + 'ruby/../x\0').encode(), b'truncated']:
            runner.return_value = subprocess.CompletedProcess([], 0, value, b'')
            with self.assertRaises((AccessError, ValueError)):
                store.list_files('ruby')


if __name__ == '__main__':
    unittest.main()
