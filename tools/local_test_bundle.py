"""Stopped-session activation of three checksum-pinned local-test hooks only.

Not an offline third-party installer: live Ruby retains running-engine checks.
No executable code, other hooks or saved preferences change here.
"""
import json
from pathlib import Path

import springys
import springys_registry
import tweak_runtime

ROOT = Path(__file__).resolve().parents[1]
ENGINE_SHA = '49bf7482544ab22bc528c482c25e5133c1ddef94cff4e5192bc8383abd52bc9f'
ENGINE = ROOT / 'builds/WinterXSpring-0.8.1-snowyhome-experimental2.apk'
BUNDLE = (
    ('SnowyHome', '466237e8c8430a037a4b1c91cbfd7eaed17eda8a454e63c4ae217684a2c152aa'),
    ('DockIn', '40d6fa90dfca5c760f474d6587ba9e20ce2fa9acdad063c73e4263ba3394727a'),
    ('FreeMe', 'b85a98fc6849c9b0c729a59aff9b1ef0045045580886f9b4afcfda78ce793fdb'),
)
CHECKS = (tweak_runtime.snowyhome_supported_by, tweak_runtime.dockin_supported_by,
          tweak_runtime.freeme_supported_by)


def regular(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Local-test storage must not contain symlinks: ' + str(path))
    if path.exists() and not path.is_file():
        raise ValueError('Expected a regular local-test file: ' + str(path))
    return path


def registry_root(data):
    root = Path(data) / 'files/sapps-data/com.ruby.manager/files/package-registry'
    for name in ('installed.json', 'operation.json', '.lock'):
        regular(root / name)
    if (root / 'operation.json').exists():
        raise RuntimeError('Recover the existing Ruby package operation before preparing the local test.')
    return root


def inputs(apk, digest, expected_sha=ENGINE_SHA):
    if digest(apk) != expected_sha or not all(check(apk) for check in CHECKS):
        raise ValueError('The combined local-test engine failed checksum/capability verification.')
    records = []
    for name, sha in BUNDLE:
        path = regular(ROOT / 'builds' / (name + '-0.1.0-local-bundle.springys'))
        metadata, _ = springys.inspect(path, sha)
        key = name.lower()
        if (metadata.get('id') != 'com.winterx.' + key or metadata.get('hook') != 'tweak.' + key
                or metadata.get('format') != 'winterx.springys/1' or metadata.get('type') == 'tweak'):
            raise ValueError('Unexpected compiled local-test package: ' + name)
        records.append({'id': metadata['id'], 'hook': metadata['hook'], 'name': name,
                        'sha256': sha, 'source': str(path)})
    return records


def activate(data, records, stopped):
    """Called only after a fresh backup and explicit combined-test preparation."""
    stopped()
    root = registry_root(data)
    before = json.loads((root / 'installed.json').read_text()) if (root / 'installed.json').exists() else {}
    if not isinstance(before, dict):
        raise ValueError('Invalid installed package registry')
    markers = {record['hook']: regular(Path(data) / 'files/ruby' / (record['name'].lower() + '.enabled'))
               for record in records}
    manual = {hook for hook, marker in markers.items() if marker.is_file()
              and hook not in springys_registry.Registry._hooks(before)}
    unchanged_hooks = springys_registry.Registry._hooks(before) - markers.keys()
    unchanged_tweaks = springys_registry.Registry._tweaks(before)

    def reconcile(hooks, tweaks):
        stopped()
        if hooks - markers.keys() != unchanged_hooks or tweaks != unchanged_tweaks:
            raise RuntimeError('Combined-test preparation cannot change other hooks or executable tweaks.')
        for hook, marker in markers.items():
            stopped()
            regular(marker)
            enabled = hook in hooks or hook in manual
            if enabled and not marker.is_file():
                springys_registry._atomic(marker, b'enabled\n')
            elif not enabled:
                marker.unlink(missing_ok=True)

    registry = springys_registry.Registry(root, reconcile,
        supported_hooks=tuple(unchanged_hooks | markers.keys()), supported_tweaks=False)
    for record in records:
        stopped()
        registry.install(record['source'], expected_sha256=record['sha256'])
    current = registry.list()
    # Same-hash installed entries also need their marker rechecked.
    reconcile(registry._hooks(current), registry._tweaks(current))
    return records


def verify(data, records):
    expected = {('com.winterx.' + name.lower(), 'tweak.' + name.lower(), sha) for name, sha in BUNDLE}
    if not isinstance(records, list) or len(records) != len(BUNDLE):
        raise ValueError('The combined-test package receipt is missing.')
    actual = {(r.get('id'), r.get('hook'), r.get('sha256')) for r in records if isinstance(r, dict)}
    if actual != expected:
        raise ValueError('The combined-test package receipt failed its pinned check.')
    root = registry_root(data)
    installed = json.loads((root / 'installed.json').read_text())
    for name, sha in BUNDLE:
        key = name.lower()
        record = installed.get('com.winterx.' + key, {})
        marker = regular(Path(data) / 'files/ruby' / (key + '.enabled'))
        if record.get('sha256') != sha or record.get('hook') != 'tweak.' + key or not marker.is_file():
            raise ValueError(name + ' is not installed/enabled for the combined local test; prepare it again.')
