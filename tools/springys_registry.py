"""Transactional local .springys registry.

The caller supplies an idempotent reconcile(desired_hooks, desired_tweaks) function. It must
apply the desired supported hooks, respring as needed and raise on failure.
The registry never executes code from a package.
"""
import hashlib
import json
import os
from pathlib import Path
import tempfile

import springys
from file_lock import exclusive_lock


class RegistryError(ValueError):
    pass


class RecoveryRequired(RuntimeError):
    pass


def _atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.winterx-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _json(path, value):
    _atomic(path, json.dumps(value, ensure_ascii=False, sort_keys=True).encode('utf-8'))


def _same_tree(base, code_digest):
    """Check immutable staged code and manifest before materializing a revision."""
    try:
        if base.is_symlink() or any((base / name).is_symlink() for name in
                                  ('code', 'code/main.js', 'manifest.json', 'sha256', 'manifest.sha256')):
            return False
        code = (base / 'code/main.js').read_bytes()
        if hashlib.sha256(code).hexdigest() != code_digest:
            return False
        record = (base / 'sha256').read_text(encoding='utf-8').strip()
        manifest_sha = (base / 'manifest.sha256').read_text(encoding='utf-8').strip()
        return record == code_digest and hashlib.sha256((base / 'manifest.json').read_bytes()).hexdigest() == manifest_sha
    except (OSError, ValueError):
        return False


class Registry:
    def __init__(self, root, reconcile, supported_hooks=('test.settings',), supported_tweaks=False):
        self.root = Path(root)
        self.reconcile = reconcile
        self.supported = frozenset(supported_hooks)
        self.supported_tweaks = supported_tweaks
        self.root.mkdir(parents=True, exist_ok=True)
        self.index = self.root / 'installed.json'
        self.journal = self.root / 'operation.json'

    def _lock(self):
        return exclusive_lock(self.root / '.lock')

    def _read(self):
        if not self.index.exists():
            return {}
        value = json.loads(self.index.read_text(encoding='utf-8'))
        if not isinstance(value, dict):
            raise RegistryError('Installed package registry is invalid')
        return value

    @staticmethod
    def _hooks(entries):
        return frozenset(item['hook'] for item in entries.values() if item.get('hook'))

    @staticmethod
    def _tweaks(entries):
        return {key: dict(value) for key, value in entries.items()
                if value.get('type') == 'tweak'}

    def _recover_locked(self):
        if not self.journal.exists():
            return False
        pending = json.loads(self.journal.read_text(encoding='utf-8'))
        old, new = pending['before'], pending['after']
        current = self._read()
        if current == new:
            self.reconcile(self._hooks(new), self._tweaks(new))
        else:
            self.reconcile(self._hooks(old), self._tweaks(old))
            _json(self.index, old)
        self.journal.unlink()
        return True

    def recover(self):
        with self._lock():
            return self._recover_locked()

    def list(self):
        with self._lock():
            if self.journal.exists():
                raise RecoveryRequired('A previous package operation needs recovery')
            return self._read()

    def _change(self, before, after):
        _json(self.journal, {'before': before, 'after': after})
        try:
            self.reconcile(self._hooks(after), self._tweaks(after))
            _json(self.index, after)
        except Exception as failure:
            try:
                self.reconcile(self._hooks(before), self._tweaks(before))
                _json(self.index, before)
                self.journal.unlink()
            except Exception as rollback:
                raise RecoveryRequired('Package operation failed and recovery is required: ' + str(rollback)) from failure
            raise
        self.journal.unlink()

    def install(self, package, expected_sha256=None):
        metadata, images = springys.inspect(package, expected_sha256, include_code=True)
        tweak = metadata.get('type') == 'tweak'
        if tweak and not self.supported_tweaks:
            raise RegistryError('This WinterX engine does not support executable tweaks yet')
        if not tweak and metadata['hook'] not in self.supported:
            raise RegistryError('This WinterX version does not support hook ' + metadata['hook'])
        with self._lock():
            self._recover_locked()
            before = self._read()
            previous = before.get(metadata['id'])
            if tweak and (not previous or previous.get('type') != 'tweak') and len(self._tweaks(before)) >= springys.MAX_TWEAKS:
                raise RegistryError('At most 8 executable tweaks can be installed in this development engine')
            if previous and previous.get('sha256') == metadata['sha256']:
                return previous
            if tweak:
                # Keep every revision immutable so interrupted updates can restore
                # the old code, not just the old installed.json metadata.
                relative_stage = 'tweaks/' + metadata['sha256']
                staging = self.root / relative_stage
                if staging.exists() and not _same_tree(staging, metadata['code_sha256']):
                    raise RegistryError('Staging directory for tweak code failed integrity check')
                if not staging.exists():
                    staging.parent.mkdir(parents=True, exist_ok=True)
                    with tempfile.TemporaryDirectory(prefix='.tweak-stage-', dir=staging.parent) as tmp:
                        staged = Path(tmp) / 'revision'
                        _atomic(staged / 'code/main.js', metadata['code'])
                        manifest_bytes = json.dumps({k: v for k, v in metadata.items() if k not in ('code', 'sha256')},
                                                    ensure_ascii=False, sort_keys=True).encode('utf-8')
                        _atomic(staged / 'manifest.json', manifest_bytes)
                        _atomic(staged / 'manifest.sha256', (hashlib.sha256(manifest_bytes).hexdigest() + '\n').encode('ascii'))
                        _atomic(staged / 'sha256', (metadata['code_sha256'] + '\n').encode('utf-8'))
                        os.rename(staged, staging)
            art_paths = {}
            for source, image in images.items():
                suffix = Path(source).suffix.lower()
                name = hashlib.sha256(image).hexdigest() + suffix
                target = self.root / 'art' / name
                if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != hashlib.sha256(image).hexdigest():
                    raise RegistryError('Stored artwork failed integrity check')
                if not target.exists():
                    _atomic(target, image)
                art_paths[source] = 'art/' + name
            record = dict(metadata)
            record.pop('code', None)
            if tweak:
                record['tweak_stage'] = relative_stage
            record['icon'] = art_paths.get(metadata['icon'])
            record['previews'] = [art_paths[x] for x in metadata['previews']]
            after = dict(before)
            after[metadata['id']] = record
            self._change(before, after)
            return record

    def uninstall(self, package_id):
        with self._lock():
            self._recover_locked()
            before = self._read()
            if package_id not in before:
                raise RegistryError('Package is not installed')
            after = dict(before)
            removed = after.pop(package_id)
            self._change(before, after)
            return removed
