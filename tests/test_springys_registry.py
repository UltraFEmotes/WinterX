import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import springys
import springys_registry


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.calls = []
        self.registry = springys_registry.Registry(self.root / 'registry', self.calls.append)
        self.png = (Path(__file__).resolve().parents[1] / 'Ruby/icon.png').read_bytes()

    def tearDown(self):
        self.tmp.cleanup()

    def package(self, package_id, version='1.0', hook='test.settings'):
        path = self.root / (package_id + version + '.springys')
        manifest = {'format': springys.FORMAT, 'id': package_id, 'name': 'Test', 'version': version,
                    'description': 'Test package', 'author': 'Example', 'hook': hook,
                    'icon': 'assets/icon.png', 'previews': ['assets/preview.png']}
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('manifest.json', json.dumps(manifest))
            z.writestr('assets/icon.png', self.png)
            z.writestr('assets/preview.png', self.png)
        return path

    def test_install_update_remove_and_shared_hook(self):
        first = self.package('me.example.one')
        result = self.registry.install(first)
        self.assertEqual(result['version'], '1.0')
        self.assertTrue((self.registry.root / result['icon']).is_file())
        self.assertEqual(len(result['previews']), 1)
        self.registry.install(self.package('me.example.one', '1.1'))
        self.assertEqual(self.registry.list()['me.example.one']['version'], '1.1')
        self.registry.install(self.package('me.example.two'))
        self.registry.uninstall('me.example.one')
        self.assertEqual(self.calls[-1], frozenset({'test.settings'}))
        self.registry.uninstall('me.example.two')
        self.assertEqual(self.calls[-1], frozenset())
        self.assertEqual(self.registry.list(), {})

    def test_failed_apply_restores_previous_registry_and_hooks(self):
        self.registry.install(self.package('me.example.one'))
        old = self.registry.list()
        calls = []
        def reconcile(desired):
            calls.append(desired)
            if len(calls) == 1:
                raise RuntimeError('respring failed')
        self.registry.reconcile = reconcile
        with self.assertRaises(RuntimeError):
            self.registry.install(self.package('me.example.one', '1.1'))
        self.assertEqual(self.registry.list(), old)
        self.assertEqual(calls[-1], frozenset({'test.settings'}))
        self.assertFalse(self.registry.journal.exists())

    def test_interrupted_operation_recovers_before_state(self):
        self.registry.install(self.package('me.example.one'))
        old = self.registry.list()
        after = dict(old)
        after['me.example.two'] = dict(old['me.example.one'], id='me.example.two')
        self.registry.journal.write_text(json.dumps({'before': old, 'after': after}))
        self.assertTrue(self.registry.recover())
        self.assertEqual(self.registry.list(), old)
        self.assertFalse(self.registry.journal.exists())

    def test_unknown_hook_is_not_installed(self):
        with self.assertRaises(springys_registry.RegistryError):
            self.registry.install(self.package('me.example.unknown', hook='test.future'))
        self.assertEqual(self.registry.list(), {})


if __name__ == '__main__':
    unittest.main()
