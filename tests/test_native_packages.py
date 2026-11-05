"""Envelope/transaction fixtures; actual Java execution is covered by extensions/check.py."""
import io
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import struct
import unittest
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import native_package
import springys
import springys_registry
from native_bridge import APP, NativeBridge, native_owned
from private_files import AccessError, DirectoryFiles
from private_transaction import Transactions


def dex(entry='me.example.Entry'):
    descriptor = ('L' + entry.replace('.', '/') + ';').encode('ascii')
    raw = bytearray(152) + bytes([len(descriptor)]) + descriptor + b'\0'
    raw[:8] = b'dex\n035\0'
    struct.pack_into('<III', raw, 32, len(raw), 112, 0x12345678)
    struct.pack_into('<IIII', raw, 56, 1, 112, 1, 116)
    struct.pack_into('<II', raw, 96, 1, 120)
    struct.pack_into('<I', raw, 112, 152)
    raw[12:32] = hashlib.sha1(raw[32:]).digest()
    struct.pack_into('<I', raw, 8, zlib.adler32(raw[12:]) & 0xffffffff)
    return bytes(raw)


def package(root, package_id='me.example.native', requires=()):
    source = root / 'source-package'
    (source / 'source/me/example').mkdir(parents=True)
    (source / 'code').mkdir()
    (source / 'source/me/example/Entry.java').write_text('package me.example; public class Entry {}\n')
    (source / 'code/classes.dex').write_bytes(dex())
    with zipfile.ZipFile(source / 'code/classes.jar', 'w') as jar:
        jar.writestr('me/example/Entry.class', b'\xca\xfe\xba\xbe' + bytes(16))
    manifest = {'format': native_package.FORMAT, 'type': 'tweak', 'runtime': 'java', 'api': native_package.API,
        'id': package_id, 'name': 'Native Fixture', 'version': '0.2.0', 'author': 'Fixture', 'license': 'MIT',
        'source': 'https://example.org/source', 'entry': 'me.example.Entry', 'description': 'Independent code fixture',
        'capabilities': ['native.hooks'], 'exports': ['media.photo-quality'], 'previews': [], 'requires': list(requires)}
    (source / 'manifest.json').write_text(json.dumps(manifest))
    archive = root / 'fixture.springys'; native_package.build(source, archive)
    return source, archive


class NativePackageTests(unittest.TestCase):
    def test_code_and_source_are_in_package_but_not_metadata(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name).resolve(); source, archive = package(root)
            info, _ = springys.inspect(archive)
            self.assertEqual(info['runtime'], 'java'); self.assertNotIn('hook', info)
            self.assertNotIn('native_payloads', info); json.dumps(info)
            private, _ = springys.inspect(archive, include_code=True)
            self.assertIn('source/me/example/Entry.java', private['native_payloads'])
            self.assertIn(native_package.DEX, private['native_payloads'])
            other = root / 'repeat.springys'; native_package.build(source, other)
            self.assertEqual(archive.read_bytes(), other.read_bytes())

    def test_native_support_is_separate_from_legacy_and_javascript_support(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name).resolve(); _, archive = package(root)
            registry = springys_registry.Registry(root / 'registry', lambda *args: None,
                supported_tweaks=True, supported_capabilities=('native.hooks',))
            with self.assertRaisesRegex(springys_registry.RegistryError, 'independent native-code'):
                registry.install(archive)
            self.assertEqual(registry.list(), {})

    def test_tampered_payload_and_platform_classes_are_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name).resolve(); source, archive = package(root)
            bad = root / 'tampered.springys'
            with zipfile.ZipFile(archive) as before, zipfile.ZipFile(bad, 'w') as after:
                for item in before.infolist():
                    after.writestr(item, b'changed' if item.filename == native_package.JAR else before.read(item.filename))
            with self.assertRaisesRegex(springys.PackageError, 'checksum'):
                springys.inspect(bad)
            with zipfile.ZipFile(source / 'code/classes.jar', 'a') as jar:
                jar.writestr('android/app/Activity.class', b'fake')
            with self.assertRaisesRegex(springys.PackageError, 'cannot replace'):
                native_package.build(source, root / 'shadow.springys')

    def test_dex_entry_integrity_and_reserved_classes_are_checked_separately(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name).resolve(); source, _ = package(root)
            for payload, error in ((dex('me.example.Other'), 'entry class'),
                                   (dex('x1.i1'), 'entry class'),
                                   (dex()[:-1] + b'x', 'checksum')):
                (source / 'code/classes.dex').write_bytes(payload)
                with self.assertRaisesRegex(springys.PackageError, error):
                    native_package.build(source, root / 'invalid.springys')
            for value in ('android/app/Activity', 'x1/i1', 'A/o', 'winterx/runtime/TrustedFiles'):
                self.assertTrue(native_package.reserved_class(value))

    def test_dependencies_refuse_missing_removal_and_cycles_before_changes(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name).resolve()
            paths = []
            for folder, package_id, requires in (('base', 'me.example.base', ()), ('child', 'me.example.child', ('me.example.base',)),
                                                  ('cycle', 'me.example.base', ('me.example.child',))):
                target = root / folder; target.mkdir(); paths.append(package(target, package_id, requires)[1])
            registry = springys_registry.Registry(root / 'registry', lambda *args: None,
                supported_native=True, supported_capabilities=('native.hooks',))
            with self.assertRaisesRegex(springys_registry.RegistryError, 'dependencies'): registry.install(paths[1])
            registry.install(paths[0]); registry.install(paths[1]); before = registry.list()
            with self.assertRaisesRegex(springys_registry.RegistryError, 'dependents'): registry.uninstall('me.example.base')
            with self.assertRaisesRegex(springys_registry.RegistryError, 'cycle'): registry.install(paths[2])
            self.assertEqual(registry.list(), before)
            self.assertFalse(registry.journal.exists())
            registry.uninstall('me.example.child'); registry.uninstall('me.example.base')
            self.assertEqual(registry.list(), {})

    def test_ruby_request_installs_code_preserving_user_state_and_layouts(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name).resolve(); _, archive = package(root)
            files = root / 'device'; files.mkdir(); store = DirectoryFiles(files)
            bridge = NativeBridge(store, root / 'host', lambda: {'phase': 'installed',
                'runtimeAbi': 'winterx-native-hooks-v1', 'coreFilesRoot': str(files)})
            self.assertFalse((files / 'winterx-tweaks').exists(), 'constructing bridge preinstalled code')
            imported = files / APP / 'imports/fixture.springys'; imported.parent.mkdir(parents=True); imported.write_bytes(archive.read_bytes())
            layout = files / 'ios6_pages.json'; layout.write_bytes(b'user layout')
            state = files / 'winterx-tweaks/me.example.native/state.json'; state.parent.mkdir(parents=True); state.write_bytes(b'user state')
            request = files / APP / 'requests/1-1.json'; request.parent.mkdir(); request.write_text(json.dumps({'id': '1-1', 'action': 'install_package', 'filename': 'fixture.springys'}))
            self.assertTrue(bridge.process(request.relative_to(files).as_posix()))
            reply = json.loads((files / APP / 'results/1-1.json').read_text())
            self.assertTrue(reply['ok'], reply); self.assertTrue(reply['restartRequired'])
            self.assertTrue((state.parent / native_package.DEX).is_file())
            self.assertTrue((state.parent / 'enabled').is_file())
            self.assertEqual(state.read_bytes(), b'user state'); self.assertEqual(layout.read_bytes(), b'user layout')
            self.assertFalse(bridge.process(request.relative_to(files).as_posix()), 'request repeated')
            request2 = files / APP / 'requests/1-2.json'; request2.write_text(json.dumps({'id': '1-2', 'action': 'remove_package', 'packageId': 'me.example.native'}))
            bridge.process(request2.relative_to(files).as_posix())
            self.assertFalse((state.parent / 'enabled').exists()); self.assertEqual(state.read_bytes(), b'user state')

    def test_native_file_policy_never_grants_login_layout_or_tweak_data(self):
        for path in ('ios6_pages.json', 'ruby/animaper.mode', 'ruby/ssh/authorized_keys',
                     'winterx-tweaks/me.example.native/state.json', 'winterx-tweaks/me.example.native/data/custom.json'):
            self.assertFalse(native_owned(path), path)
        self.assertTrue(native_owned('winterx-tweaks/me.example.native/code/classes.dex'))
        with tempfile.TemporaryDirectory() as name:
            root = Path(name).resolve(); files = root / 'device'; files.mkdir()
            with self.assertRaisesRegex(AccessError, 'actual compatible running core'):
                NativeBridge(DirectoryFiles(files), root / 'host', lambda: {'phase': 'stopped'})
            self.assertEqual(list(files.iterdir()), [])


if __name__ == '__main__': unittest.main()
