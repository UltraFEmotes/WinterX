import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import local_test_bundle as bundle
import prepare_local_test as preparation
import springys_tool


class LocalTestBundleTests(unittest.TestCase):
    def fixture(self, root):
        records, pins = [], []
        for name, _ in bundle.BUNDLE:
            source = bundle.ROOT / 'builtin-repo/sources' / name.lower()
            path = root / 'builds' / (name + '-0.1.0-local-bundle.springys')
            springys_tool.build(source, path)
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            pins.append((name, sha))
            records.append({'id': 'com.winterx.' + name.lower(), 'hook': 'tweak.' + name.lower(),
                            'name': name, 'sha256': sha, 'source': str(path)})
        return records, tuple(pins)

    def test_three_hooks_installed_without_changing_existing_code_settings_or_safe_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); data = root / 'data'; records, pins = self.fixture(root)
            registry = bundle.registry_root(data); registry.mkdir(parents=True)
            existing = {'example.code': {'type': 'tweak', 'code_sha256': 'old', 'tweak_stage': 'preserved'},
                        'example.bar': {'hook': 'tweak.coloredbar', 'sha256': 'old'}}
            (registry / 'installed.json').write_text(json.dumps(existing))
            files = data / 'files'; (files / 'ruby').mkdir()
            for name in ('dockin.capacity', 'safe-mode.enabled', 'freeme-slots-v1.json', 'coloredbar.enabled'):
                (files / 'ruby' / name).write_bytes(b'keep me')
            code = files / 'winterx-tweaks/example.code/data/save.txt'; code.parent.mkdir(parents=True)
            code.write_bytes(b'keep tweak state')
            before = preparation.inventory(data); stopped = Mock()
            with patch.object(bundle, 'BUNDLE', pins):
                bundle.activate(data, records, stopped)
                bundle.verify(data, records)
                after = json.loads((registry / 'installed.json').read_text())
                self.assertEqual({key: after[key] for key in existing}, existing)
                preparation.preserved(before, preparation.inventory(data))
                # Repeated preparation neither rewrites marker contents nor deletes saved preferences.
                marker = files / 'ruby/snowyhome.enabled'; marker.write_bytes(b'original marker')
                bundle.activate(data, records, stopped)
                self.assertEqual(marker.read_bytes(), b'original marker')
                marker.unlink()
                with self.assertRaisesRegex(ValueError, 'not installed/enabled'):
                    bundle.verify(data, records)
                bundle.activate(data, records, stopped)
                bundle.verify(data, records)
            self.assertGreater(stopped.call_count, 3)

    def test_inputs_reject_missing_engine_capabilities_and_changed_packages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); _, pins = self.fixture(root)
            with patch.object(bundle, 'ROOT', root), patch.object(bundle, 'BUNDLE', pins), \
                 patch.object(bundle, 'CHECKS', (lambda apk: False,)):
                with self.assertRaisesRegex(ValueError, 'capability'):
                    bundle.inputs('engine', lambda apk: bundle.ENGINE_SHA)
            with patch.object(bundle, 'ROOT', root), patch.object(bundle, 'BUNDLE', pins), \
                 patch.object(bundle, 'CHECKS', (lambda apk: True,)):
                bundle.inputs('engine', lambda apk: bundle.ENGINE_SHA)
                (root / 'builds/SnowyHome-0.1.0-local-bundle.springys').write_bytes(b'changed')
                with self.assertRaises(ValueError):
                    bundle.inputs('engine', lambda apk: bundle.ENGINE_SHA)

    def test_pending_registry_or_marker_symlink_fails_before_activation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); data = root / 'data'; records, _ = self.fixture(root)
            registry = bundle.registry_root(data); registry.mkdir(parents=True)
            journal = registry / 'operation.json'; journal.write_text('{}')
            with self.assertRaisesRegex(RuntimeError, 'Recover'):
                bundle.activate(data, records, Mock())
            journal.unlink()
            ruby = data / 'files/ruby'; ruby.mkdir()
            outside = root / 'outside'; outside.write_bytes(b'untouched')
            (ruby / 'snowyhome.enabled').symlink_to(outside)
            with self.assertRaisesRegex(ValueError, 'symlinks'):
                bundle.activate(data, records, Mock())
            self.assertEqual(outside.read_bytes(), b'untouched')
            self.assertFalse((registry / 'installed.json').exists())

    def test_stopped_guard_is_checked_before_any_write_and_preservation_refuses_other_edits(self):
        with self.assertRaises(RuntimeError):
            bundle.activate(Path('not-read'), [], Mock(side_effect=RuntimeError('running')))
        with self.assertRaisesRegex(RuntimeError, 'Persisted data changed'):
            preparation.preserved({'shared_prefs/test.xml': 'old'}, {'shared_prefs/test.xml': 'new'})
        with self.assertRaisesRegex(RuntimeError, 'Persisted data changed'):
            preparation.preserved({'files/keep.txt': 'old'}, {})


if __name__ == '__main__':
    unittest.main()
