import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from private_files import AccessError, DirectoryFiles
from portable_bridge import APP, Bridge
import springys_registry
import springys_tool


class PortableBridgeTests(unittest.TestCase):
    def fixture(self, root):
        files = root / 'files'; files.mkdir(); app = files / APP; app.mkdir(parents=True)
        (files / 'ruby').mkdir(); (files / 'ios6_pages.json').write_bytes(b'protected layout')
        (files / 'ruby/freeme-slots-v1.json').write_bytes(b'saved cells')
        store = DirectoryFiles(files)
        return store, Bridge(store, root / 'host-state', builtin=None), app

    def request(self, app, n, action, **values):
        path = app / f'requests/{n}-0.json'; path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({'id': f'{n}-0', 'action': action, **values}))
        return APP + f'/requests/{n}-0.json'

    def test_scan_is_bounded_idempotent_and_does_not_read_or_write_user_state(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); store, bridge, app = self.fixture(root)
            (app / 'imports').mkdir()
            springys_tool.build(ROOT / 'builtin-repo/sources/freeme', app / 'imports/draft.springys')
            self.request(app, 1, 'scan_packages')
            with patch.object(store, 'read', wraps=store.read) as reads:
                self.assertEqual(bridge.once(), 1); self.assertEqual(bridge.once(), 0)
                self.assertFalse(any(c.args[0].startswith(('ruby/', 'winterx-tweaks/')) or c.args[0] == 'ios6_pages.json' for c in reads.call_args_list))
            inventory = json.loads((app / 'packages.json').read_text())
            self.assertEqual(inventory['available'][0]['id'], 'com.winterx.freeme')
            self.assertEqual(inventory['installed'], [])
            self.assertEqual(store.read('ios6_pages.json'), b'protected layout')
            self.assertEqual(store.read('ruby/freeme-slots-v1.json'), b'saved cells')

    def test_repository_uses_existing_validation_and_hash_named_imports(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); store, bridge, app = self.fixture(root)
            archive = root / 'package.springys'; springys_tool.build(ROOT / 'builtin-repo/sources/dockin', archive)
            payload = archive.read_bytes(); sha = hashlib.sha256(payload).hexdigest()
            index = json.dumps({'format': 'winterx.repository/1', 'name': 'Fixture', 'packages': [{'url': 'dockin.springys', 'sha256': sha}]}).encode()
            def fetch(url, limit):
                value = payload if url.endswith('.springys') else index
                self.assertLessEqual(len(value), limit); return value
            bridge.fetch = fetch
            self.request(app, 1, 'add_repository', url='https://fixture.invalid/index.json')
            self.assertEqual(bridge.once(), 1)
            self.assertTrue(json.loads((app / 'results/1-0.json').read_text())['ok'])
            self.assertEqual((app / ('imports/repo-' + sha + '.springys')).read_bytes(), payload)
            self.assertEqual(json.loads((app / 'sources.json').read_text()), ['https://fixture.invalid/index.json'])
            self.request(app, 2, 'install_package', filename='repo-' + sha + '.springys'); bridge.once()
            reply = json.loads((app / 'results/2-0.json').read_text())
            self.assertFalse(reply['ok']); self.assertIn('verified', reply['message'])
            self.assertFalse((store.root / 'ruby/dockin.enabled').exists())

    def test_scan_does_not_silently_reconcile_a_pending_package_operation(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); store, bridge, app = self.fixture(root)
            registry = app / 'package-registry'; registry.mkdir()
            journal = registry / 'operation.json'; pending = b'{"before":{},"after":{}}'; journal.write_bytes(pending)
            self.request(app, 1, 'scan_packages')
            with self.assertRaises(springys_registry.RecoveryRequired): bridge.once()
            self.assertEqual(journal.read_bytes(), pending)
            self.assertFalse((app / 'results/1-0.json').exists())

    def test_conflicting_input_is_preserved_and_success_is_not_reported(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); store, bridge, app = self.fixture(root)
            self.request(app, 1, 'scan_packages')
            snapshot = bridge._snapshot
            def drift():
                value = snapshot(); (app / 'packages.json').write_bytes(b'user edit'); return value
            with patch.object(bridge, '_snapshot', side_effect=drift): bridge.once()
            self.assertEqual((app / 'packages.json').read_bytes(), b'user edit')
            self.assertFalse(json.loads((app / 'results/1-0.json').read_text())['ok'])

    def test_invalid_request_and_unowned_app_actions_cannot_control_processes(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); store, bridge, app = self.fixture(root)
            for n, action in enumerate(('jailbreak', 'set_safe_mode', 'queue_app_install', 'remove_package'), 1):
                self.request(app, n, action)
            bridge.once()
            for n in range(1, 5): self.assertFalse(json.loads((app / f'results/{n}-0.json').read_text())['ok'])
            path = app / 'requests/5-0.json'; path.write_bytes(b'{"id":"5-0","id":"5-0","action":"scan_packages"}')
            bridge.once(); self.assertFalse(json.loads((app / 'results/5-0.json').read_text())['ok'])
