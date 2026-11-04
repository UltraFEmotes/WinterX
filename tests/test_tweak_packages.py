import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import ruby_packages
import ruby_repositories
import springys
import springys_tool


class TweakPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.files = self.root / 'ruby'
        self.tweaks = self.root / 'spring/files/winterx-tweaks'
        self.packages = ruby_packages.Packages(self.files, self.root / 'settings.enabled',
                                              lambda enabled: {'ok': True}, tweak_root=self.tweaks, supported_tweaks=True)
        self.packages.imports.mkdir(parents=True)
        self.manifest = json.loads((ROOT / 'examples/code-tweak/manifest.json').read_text())
        self.code = b'WinterX.log("custom code");\n'

    def tearDown(self):
        self.tmp.cleanup()

    def package(self, name='test.springys', manifest=None, code=None, extra=()):
        path = self.packages.imports / name
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('manifest.json', json.dumps(self.manifest if manifest is None else manifest))
            if code is not False:
                archive.writestr(springys.CODE_ENTRY, self.code if code is None else code)
            for key, value in extra:
                archive.writestr(key, value)
        return path

    def target(self):
        return self.tweaks / self.manifest['id']

    def test_inspect_and_builder_are_json_safe(self):
        path = self.root / 'example.springys'
        result = springys_tool.build(ROOT / 'examples/code-tweak', path)
        self.assertEqual(result['format'], springys.FORMAT2)
        self.assertEqual(result['entry'], springys.CODE_ENTRY)
        self.assertEqual(result['settings'], self.manifest['settings'])
        json.dumps(result)
        self.assertNotIn('code', result)
        code = springys.inspect(path, include_code=True)[0]['code']
        self.assertEqual(hashlib.sha256(code).hexdigest(), result['code_sha256'])

    def test_older_engine_does_not_mark_code_tweaks_installed(self):
        self.package()
        self.packages.registry.supported_tweaks = False
        with self.assertRaises(ValueError): self.packages.install('test.springys')
        self.assertEqual(self.packages.registry.list(), {})
        self.assertFalse((self.target() / 'enabled').exists())

    def test_home_capabilities_are_explicit_validated_preserved_and_engine_gated(self):
        self.package(manifest=dict(self.manifest, capabilities=['home.read', 'home.grid']))
        with self.assertRaisesRegex(ValueError, 'home API'):
            self.packages.install('test.springys')
        self.assertEqual(self.packages.registry.list(), {})
        self.packages.registry.supported_capabilities = frozenset(('home.read', 'home.grid'))
        record = self.packages.install('test.springys')
        self.assertEqual(record['capabilities'], ['home.read', 'home.grid'])
        self.assertEqual(json.loads((self.target() / 'manifest.json').read_text())['capabilities'], record['capabilities'])
        for invalid in (['home.read', 'home.read'], ['home.root'], {}, [None], 'home.read'):
            self.package(manifest=dict(self.manifest, capabilities=invalid))
            with self.assertRaises(ValueError): springys.inspect(self.packages.imports / 'test.springys')

    def test_runtime_capacity_is_enforced_before_staging(self):
        for number in range(springys.MAX_TWEAKS):
            self.package(manifest=dict(self.manifest, id='me.example.tweak' + str(number)))
            self.packages.install('test.springys')
        self.package(manifest=dict(self.manifest, id='me.example.extra'))
        with self.assertRaises(ValueError): self.packages.install('test.springys')
        self.assertEqual(len(self.packages.registry.list()), springys.MAX_TWEAKS)

    def test_converting_a_hook_to_code_does_not_bypass_capacity(self):
        legacy = {'format': springys.FORMAT, 'id': 'me.example.legacy', 'name': 'Legacy',
                  'version': '0.1.0', 'author': 'Example', 'description': 'Legacy hook', 'hook': 'test.settings'}
        self.package(manifest=legacy, code=False)
        self.packages.install('test.springys')
        for number in range(springys.MAX_TWEAKS):
            self.package(manifest=dict(self.manifest, id='me.example.tweak' + str(number)))
            self.packages.install('test.springys')
        self.package(manifest=dict(self.manifest, id=legacy['id'], version='0.2.0'))
        with self.assertRaises(ValueError): self.packages.install('test.springys')
        self.assertEqual(self.packages.registry.list()[legacy['id']]['hook'], 'test.settings')

    def test_unrelated_package_changes_do_not_disable_unchanged_code(self):
        self.package()
        self.packages.install('test.springys')
        enabled = self.target() / 'enabled'
        original_unlink = Path.unlink
        def guard(path, *args, **kwargs):
            self.assertNotEqual(path, enabled, 'unchanged runtime was disabled')
            return original_unlink(path, *args, **kwargs)
        with patch.object(Path, 'unlink', guard):
            self.package('second.springys', dict(self.manifest, id='me.example.second'))
            self.packages.install('second.springys')
            self.packages.uninstall('me.example.second')
        self.assertTrue(enabled.is_file())

    def test_install_update_remove_preserves_preferences_and_rollback_revisions(self):
        self.package()
        first = self.packages.install('test.springys')
        self.assertTrue((self.target() / 'enabled').is_file())
        self.assertEqual((self.target() / 'code/main.js').read_bytes(), self.code)
        installed_manifest = json.loads((self.target() / 'manifest.json').read_text())
        self.assertEqual(installed_manifest['settings'], self.manifest['settings'])
        (self.target() / 'state.json').write_text('{"helloCount":7}')
        (self.target() / 'data').mkdir()
        (self.target() / 'data/example.txt').write_text('user data')
        next_code = b'WinterX.log("updated custom code");\n'
        self.package('update.springys', dict(self.manifest, version='0.2.0'), next_code)
        second = self.packages.install('update.springys')
        self.assertNotEqual(first['tweak_stage'], second['tweak_stage'])
        self.assertEqual((self.target() / 'code/main.js').read_bytes(), next_code)
        old_stage = self.packages.registry.root / first['tweak_stage']
        self.assertEqual((old_stage / 'code/main.js').read_bytes(), self.code)
        self.packages.uninstall(self.manifest['id'])
        self.assertFalse((self.target() / 'enabled').exists())
        self.assertEqual((self.target() / 'state.json').read_text(), '{"helloCount":7}')
        self.assertEqual((self.target() / 'data/example.txt').read_text(), 'user data')
        self.packages.install('update.springys')
        self.assertTrue((self.target() / 'enabled').is_file())
        json.dumps(self.packages.scan())

    def test_failed_update_restores_actual_code(self):
        self.package()
        first = self.packages.install('test.springys')
        self.package('update.springys', dict(self.manifest, version='0.2.0'), b'WinterX.log("new");')
        original = self.packages.registry.reconcile
        calls = []
        def fail_after_materialize(hooks, tweaks):
            original(hooks, tweaks)
            calls.append(tweaks)
            if len(calls) == 1:
                raise RuntimeError('simulated interrupted install')
        self.packages.registry.reconcile = fail_after_materialize
        with self.assertRaises(RuntimeError):
            self.packages.install('update.springys')
        self.assertEqual(self.packages.registry.list()[self.manifest['id']], first)
        self.assertEqual((self.target() / 'code/main.js').read_bytes(), self.code)
        self.assertTrue((self.target() / 'enabled').is_file())
        self.assertFalse(self.packages.registry.journal.exists())

    def test_journal_recovery_restores_actual_code(self):
        self.package()
        self.packages.install('test.springys')
        before = self.packages.registry.list()
        self.package('update.springys', dict(self.manifest, version='0.2.0'), b'WinterX.log("new");')
        self.packages.install('update.springys')
        after = self.packages.registry.list()
        self.packages.registry.index.write_text(json.dumps(before))
        self.packages.registry.journal.write_text(json.dumps({'before': before, 'after': after}))
        self.assertTrue(self.packages.registry.recover())
        self.assertEqual((self.target() / 'code/main.js').read_bytes(), self.code)

    def test_repository_catalogue_has_no_code_bytes(self):
        path = self.package()
        raw = path.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        index = json.dumps({'format': 'winterx.repository/1', 'name': 'Tweak Code',
                            'packages': [{'url': 'test.springys', 'sha256': sha}]}).encode()
        def fetch(url, limit):
            return index if url.endswith('index.json') else raw
        repo = ruby_repositories.Repositories(self.files, self.packages, fetch=fetch)
        catalogue = repo.add('https://example.com/index.json')
        self.assertEqual(catalogue['packages'][0]['type'], 'tweak')
        self.assertNotIn('code', catalogue['packages'][0])
        json.dumps(catalogue)

    def test_invalid_code_and_manifest_are_rejected(self):
        for code in (False, b'', b' \n ', b'\x00', b'\xff', b'x' * (springys.MAX_CODE + 1)):
            with self.subTest(code=str(code)[:20]):
                self.package(code=code)
                with self.assertRaises(springys.PackageError): springys.inspect(self.packages.imports / 'test.springys')
        for changes in ({'type': 'hook'}, {'entry': '../main.js'}, {'hook': 'tweak.unknown'}, {'id': '../bad'}):
            self.package(manifest=dict(self.manifest, **changes))
            with self.assertRaises(springys.PackageError): springys.inspect(self.packages.imports / 'test.springys')
        self.package(extra=[('../escape.js', b'code')])
        with self.assertRaises(springys.PackageError): springys.inspect(self.packages.imports / 'test.springys')

    def test_duplicate_rows_and_unknown_page_targets_are_rejected(self):
        for field, value in (('id', 'hello'), ('page', 'missing')):
            manifest = copy.deepcopy(self.manifest)
            rows = manifest['settings']['main']['sections'][0]['rows']
            rows[-1][field] = value
            self.package(manifest=manifest)
            with self.assertRaises(springys.PackageError): springys.inspect(self.packages.imports / 'test.springys')

    def test_symlinked_code_or_engine_storage_is_rejected(self):
        source = self.root / 'source'
        source.mkdir()
        (source / 'manifest.json').write_text(json.dumps(self.manifest))
        (source / 'tweak').mkdir()
        outside = self.root / 'outside.js'
        outside.write_bytes(self.code)
        (source / 'tweak/main.js').symlink_to(outside)
        with self.assertRaises(ValueError): springys_tool.build(source, self.root / 'bad.springys')
        self.package()
        outside_dir = self.root / 'outside'
        outside_dir.mkdir()
        self.tweaks.mkdir(parents=True)
        self.target().symlink_to(outside_dir, target_is_directory=True)
        with self.assertRaises(Exception): self.packages.install('test.springys')
        self.assertFalse((outside_dir / 'code/main.js').exists())


if __name__ == '__main__':
    unittest.main()
