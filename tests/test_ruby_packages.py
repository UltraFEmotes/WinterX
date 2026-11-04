import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import ruby_packages
import springys


class PackageIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.marker = self.root / 'settings'
        self.changes = []
        def apply(enabled):
            self.changes.append(enabled)
            if enabled:
                self.marker.touch()
            else:
                self.marker.unlink(missing_ok=True)
            return {'ok': True}
        self.service = ruby_packages.Packages(self.root / 'ruby', self.marker, apply)
        self.service.imports.mkdir(parents=True)
        self.make_package('one.springys', '1.0')

    def tearDown(self):
        self.temp.cleanup()

    def make_package(self, filename, version):
        manifest = {'format': springys.FORMAT, 'id': 'me.test.settings', 'name': 'Test',
                    'version': version, 'author': 'Tester', 'description': 'Test package', 'hook': 'test.settings'}
        with zipfile.ZipFile(self.service.imports / filename, 'w') as archive:
            archive.writestr('manifest.json', json.dumps(manifest))

    def test_install_update_uninstall(self):
        self.assertEqual(len(self.service.scan()['available']), 1)
        self.service.install('one.springys')
        self.assertTrue(self.marker.exists())
        self.make_package('two.springys', '2.0')
        self.service.install('two.springys')
        result = self.service.scan()
        self.assertEqual(result['installed'][0]['version'], '2.0')
        self.service.uninstall('me.test.settings')
        self.assertFalse(self.marker.exists())
        self.assertEqual(self.service.scan()['installed'], [])

    def test_preexisting_manual_settings_preserved(self):
        self.marker.touch()
        with self.assertRaisesRegex(ValueError, 'existing Settings'):
            self.service.install('one.springys')
        self.assertTrue(self.marker.exists())
        self.assertEqual(self.changes, [])

    def test_failed_apply_restores_previous_state(self):
        count = 0
        def fail_once(enabled):
            nonlocal count
            count += 1
            if count == 1:
                return {'ok': False, 'message': 'failed'}
            return {'ok': True}
        self.service.apply = fail_once
        with self.assertRaisesRegex(RuntimeError, 'failed'):
            self.service.install('one.springys')
        self.assertEqual(self.service.registry.list(), {})
        self.assertEqual(count, 1)

    def test_other_manual_tweak_is_not_disabled(self):
        other = self.root / 'color-enabled'
        other.touch()
        calls = []
        self.service.hooks['test.colors'] = (other, lambda enabled: calls.append(enabled) or {'ok': True})
        self.service.registry.supported = frozenset(self.service.hooks)
        self.service.install('one.springys')
        self.service.uninstall('me.test.settings')
        self.assertTrue(other.is_file())
        self.assertEqual(calls, [])

    def test_multiple_hooks_and_shared_hook_removal(self):
        marker = self.root / 'color-enabled'
        calls = []
        def apply_color(enabled):
            calls.append(enabled)
            if enabled: marker.touch()
            else: marker.unlink(missing_ok=True)
            return {'ok': True}
        self.service.hooks['test.colors'] = (marker, apply_color)
        self.service.registry.supported = frozenset(self.service.hooks)
        for name in ('first', 'second'):
            manifest = {'format': springys.FORMAT, 'id': 'me.test.' + name, 'name': name,
                        'version': '1.0', 'author': 'Tester', 'description': 'Color', 'hook': 'test.colors'}
            with zipfile.ZipFile(self.service.imports / (name + '.springys'), 'w') as archive:
                archive.writestr('manifest.json', json.dumps(manifest))
        self.service.install('one.springys')
        self.service.install('first.springys')
        self.service.install('second.springys')
        self.service.uninstall('me.test.first')
        self.assertTrue(marker.exists())
        self.service.uninstall('me.test.second')
        self.assertFalse(marker.exists())
        self.assertTrue(self.marker.exists())
        self.assertEqual(calls, [True, False])

    def test_rejects_escape_and_links(self):
        with self.assertRaises(ValueError):
            self.service.install('../one.springys')
        (self.service.imports / 'link.springys').symlink_to(self.service.imports / 'one.springys')
        with self.assertRaises(ValueError):
            self.service.install('link.springys')


if __name__ == '__main__':
    unittest.main()
