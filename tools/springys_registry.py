"""Transactional local .springys registry.

The caller supplies an idempotent reconcile(desired_hooks) function. It must
apply the desired supported hooks, respring as needed and raise on failure.
The registry never executes code from a package.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile

import springys


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


class Registry:
    def __init__(self, root, reconcile, supported_hooks=('test.settings',)):
        self.root = Path(root)
        self.reconcile = reconcile
        self.supported = frozenset(supported_hooks)
        self.root.mkdir(parents=True, exist_ok=True)
        self.index = self.root / 'installed.json'
        self.journal = self.root / 'operation.json'

    @contextmanager
    def _lock(self):
        with (self.root / '.lock').open('a+b') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _read(self):
        if not self.index.exists():
            return {}
        value = json.loads(self.index.read_text(encoding='utf-8'))
        if not isinstance(value, dict):
            raise RegistryError('Installed package registry is invalid')
        return value

    @staticmethod
    def _hooks(entries):
        return frozenset(item['hook'] for item in entries.values())

    def _recover_locked(self):
        if not self.journal.exists():
            return False
        pending = json.loads(self.journal.read_text(encoding='utf-8'))
        old, new = pending['before'], pending['after']
        current = self._read()
        if current == new:
            self.reconcile(self._hooks(new))
        else:
            self.reconcile(self._hooks(old))
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
            self.reconcile(self._hooks(after))
            _json(self.index, after)
        except Exception as failure:
            try:
                self.reconcile(self._hooks(before))
                _json(self.index, before)
                self.journal.unlink()
            except Exception as rollback:
                raise RecoveryRequired('Package operation failed and recovery is required: ' + str(rollback)) from failure
            raise
        self.journal.unlink()

    def install(self, package, expected_sha256=None):
        metadata, images = springys.inspect(package, expected_sha256)
        if metadata['hook'] not in self.supported:
            raise RegistryError('This WinterX version does not support hook ' + metadata['hook'])
        with self._lock():
            self._recover_locked()
            before = self._read()
            previous = before.get(metadata['id'])
            if previous and previous.get('sha256') == metadata['sha256']:
                return previous
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
