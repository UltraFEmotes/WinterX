import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from private_files import AccessError, ConflictError, DirectoryFiles
from private_transaction import RecoveryRequired, Transactions


class PrivateTransactionTests(unittest.TestCase):
    def fixture(self, root):
        files = root / 'files'; files.mkdir()
        (files / 'ruby').mkdir()
        (files / 'ios6_pages.json').write_bytes(b'protected layout')
        (files / 'ruby/freeme-slots-v1.json').write_bytes(b'protected cells')
        (files / 'ruby/dockin.capacity').write_bytes(b'7\n')
        store = DirectoryFiles(files)
        return store, Transactions(store, root / 'host-state')

    def test_commit_owned_markers_without_touching_layout_or_preferences(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); store, tx = self.fixture(root)
            tx.apply([('ruby/freeme.enabled', None, b'enabled'), ('ruby/dockin.enabled', None, b'enabled')])
            self.assertEqual(store.read('ruby/dockin.enabled'), b'enabled')
            self.assertFalse(tx.recover())
            self.assertEqual(store.read('ios6_pages.json'), b'protected layout')
            self.assertEqual(store.read('ruby/freeme-slots-v1.json'), b'protected cells')
            self.assertEqual(store.read('ruby/dockin.capacity'), b'7\n')
            for path in ('ios6_pages.json', 'ruby/freeme-slots-v1.json', 'ruby/dockin.capacity',
                         'winterx-tweaks/me.example/state.json', 'winterx-tweaks/me.example/data/file.txt'):
                with self.subTest(path=path), self.assertRaises(AccessError): tx.apply([(path, None, b'oops')])

    def test_failed_transfer_rolls_back_already_written_files(self):
        with tempfile.TemporaryDirectory() as name:
            store, tx = self.fixture(Path(name)); write = store.write
            def fail(path, value, **args):
                if path == 'ruby/dockin.enabled': raise AccessError('device disconnected')
                return write(path, value, **args)
            with patch.object(store, 'write', side_effect=fail), self.assertRaises(AccessError):
                tx.apply([('ruby/freeme.enabled', None, b'yes'), ('ruby/dockin.enabled', None, b'yes')])
            self.assertIsNone(store.read('ruby/freeme.enabled'))
            self.assertEqual(json.loads(tx.journal.read_text())['status'], 'rolled-back')

    def test_pending_crash_recovery_and_external_edits_fail_closed(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); store, tx = self.fixture(root)
            tx.apply([('ruby/freeme.enabled', None, b'yes')])
            record = json.loads(tx.journal.read_text()); record['status'] = 'pending'; tx._save(record)
            store.write('ruby/freeme.enabled', b'user edit', expected=b'yes')
            with self.assertRaises(RecoveryRequired): tx.recover()
            self.assertEqual(store.read('ruby/freeme.enabled'), b'user edit')
            with self.assertRaises(RecoveryRequired): tx.apply([('ruby/dockin.enabled', None, b'yes')])
            self.assertIsNone(store.read('ruby/dockin.enabled'))
            store.write('ruby/freeme.enabled', b'yes', expected=b'user edit')
            self.assertTrue(Transactions(store, root / 'host-state').recover())
            self.assertIsNone(store.read('ruby/freeme.enabled'))

    def test_preflight_conflict_and_wrong_target_journal_refused(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); store, tx = self.fixture(root)
            store.write('ruby/freeme.enabled', b'existing', expected=None)
            with self.assertRaises(ConflictError): tx.apply([('ruby/freeme.enabled', None, b'oops')])
            self.assertFalse(tx.journal.exists())
            tx.apply([('ruby/freeme.enabled', b'existing', b'new')])
            other = root / 'other-files'; other.mkdir()
            with self.assertRaises(AccessError): Transactions(DirectoryFiles(other), root / 'host-state').recover()
