"""Recoverable bridge-owned file batches. No app installation, engine switching or layout edits."""
import base64
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

from file_lock import exclusive_lock
from private_files import AccessError, AdbFiles, ConflictError, DirectoryFiles, MAX_FILE, SshFiles, relative_path

MAX_CHANGES = 128
MAX_BYTES = 32 * 1024 * 1024
MAX_JOURNAL = 46 * 1024 * 1024


class RecoveryRequired(AccessError):
    pass


def bridge_owned(path):
    """Narrow runtime/registry files only. Saved pages, preferences and tweak data never qualify."""
    path = relative_path(path)
    if path in {'ruby/' + name + '.enabled' for name in ('animaper', 'coloredbar', 'freeme', 'dockin')}:
        return True
    parts = path.split('/')
    if len(parts) >= 3 and parts[0] == 'winterx-tweaks' and re.fullmatch(r'[a-z0-9]+(?:[.-][a-z0-9]+)+', parts[1]):
        return '/'.join(parts[2:]) in {'manifest.json', 'manifest.sha256', 'sha256', 'enabled', 'code/main.js'}
    prefix = 'sapps-data/com.ruby.manager/files/'
    if not path.startswith(prefix): return False
    suffix = path[len(prefix):]
    if suffix in ('packages.json', 'sources.json', 'repository-catalogue.json'): return True
    if re.fullmatch(r'results/[0-9]+-[0-9]+\.json', suffix): return True
    if re.fullmatch(r'imports/repo-[0-9a-f]{64}\.springys', suffix): return True
    if re.fullmatch(r'package-art/(?:icon-64-)?[0-9a-f]{64}\.(?:png|jpg|jpeg)', suffix): return True
    if suffix in ('package-registry/installed.json', 'package-registry/operation.json'): return True
    if re.fullmatch(r'package-registry/art/(?:icon-64-)?[0-9a-f]{64}\.(?:png|jpg|jpeg)', suffix): return True
    return bool(re.fullmatch(r'package-registry/tweaks/[0-9a-f]{64}/(?:manifest\.json|manifest\.sha256|sha256|code/main\.js)', suffix))


def identity(store):
    if isinstance(store, DirectoryFiles):
        return {'kind': 'directory', 'root': str(store.root)}
    if isinstance(store, SshFiles) and store.identity is not None:
        return {'kind': 'ssh', 'host': store.host, 'port': store.port, **store.identity}
    if isinstance(store, AdbFiles) and store.identity is not None:
        return {'kind': 'adb', 'serial': store.serial, **store.identity}
    raise AccessError('Verify the private-folder target before starting a transaction')


class Transactions:
    def __init__(self, store, state, *, owned=bridge_owned, policy='bridge-owned-v1', before_write=None):
        self.store, self.target = store, identity(store)
        self.owned, self.policy, self.before_write = owned, policy, before_write
        self.state = Path(state)
        if self.state.is_symlink() or (self.state.exists() and not self.state.is_dir()):
            raise AccessError('Transaction state must be a real host directory')
        if isinstance(store, DirectoryFiles) and self.state.resolve().is_relative_to(store.root):
            raise AccessError('Host recovery state must not be inside Spring\'s private folder')
        self.state.mkdir(parents=True, exist_ok=True)
        self.journal = self.state / 'private-transaction.json'
        self.lock = self.state / 'private-transaction.lock'

    def _save(self, record):
        if self.journal.is_symlink(): raise AccessError('Transaction journal must not be a symlink')
        fd, name = tempfile.mkstemp(prefix='.private-transaction-', dir=self.state)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as out:
                json.dump(record, out, separators=(',', ':')); out.flush(); os.fsync(out.fileno())
            os.replace(name, self.journal)
        finally:
            if os.path.exists(name): os.unlink(name)

    @staticmethod
    def _encoded(value):
        return None if value is None else base64.b64encode(value).decode('ascii')

    @staticmethod
    def _decoded(value):
        if value is None: return None
        if not isinstance(value, str) or len(value) > (MAX_FILE + 2) // 3 * 4:
            raise AccessError('Invalid transaction payload')
        try: raw = base64.b64decode(value, validate=True)
        except (ValueError, TypeError) as exc: raise AccessError('Invalid transaction payload') from exc
        if len(raw) > MAX_FILE: raise AccessError('Transaction payload exceeds the file limit')
        return raw

    def _validated(self, record):
        if (not isinstance(record, dict) or record.get('format') != 'winterx.private-transaction/1'
                or record.get('target') != self.target or record.get('policy', 'bridge-owned-v1') != self.policy
                or record.get('status') not in ('pending', 'committed', 'rolled-back')):
            raise AccessError('Transaction journal does not match the verified target')
        values = record.get('changes')
        if not isinstance(values, list) or not 1 <= len(values) <= MAX_CHANGES:
            raise AccessError('Invalid transaction change count')
        seen, total, changes = set(), 0, []
        for item in values:
            path = item.get('path') if isinstance(item, dict) else None
            try: owned = isinstance(path, str) and self.owned(path)
            except ValueError as exc: raise AccessError('Invalid transaction path') from exc
            if not owned or path in seen:
                raise AccessError('Transaction contains a non-owned or duplicate path')
            seen.add(path)
            if not {'path', 'before', 'after'}.issubset(item):
                raise AccessError('Incomplete transaction change')
            before, after = self._decoded(item['before']), self._decoded(item['after'])
            total += len(before or b'') + len(after or b'')
            if total > MAX_BYTES: raise AccessError('Transaction batch exceeds the byte limit')
            changes.append((path, before, after))
        return changes

    def _restore(self, record):
        conflicts = []
        for path, before, after in reversed(self._validated(record)):
            try:
                current = self.store.read(path)
                if current == before: continue
                if current != after:
                    conflicts.append(path); continue
                if self.before_write is not None: self.before_write()
                if before is None: self.store.remove(path, expected=after)
                else: self.store.write(path, before, expected=after)
            except (AccessError, OSError):
                conflicts.append(path)
        if conflicts:
            # Leave the pending journal intact. Recovery must not clobber an external edit.
            raise RecoveryRequired('Private-folder recovery blocked for: ' + ', '.join(conflicts)[:400])
        record['status'] = 'rolled-back'; self._save(record)

    def _recover(self):
        if self.journal.is_symlink(): raise AccessError('Transaction journal must not be a symlink')
        if not self.journal.exists(): return False
        with self.journal.open('rb') as source: raw = source.read(MAX_JOURNAL + 1)
        if len(raw) > MAX_JOURNAL: raise AccessError('Transaction journal exceeds its bound')
        try: record = json.loads(raw)
        except (ValueError, UnicodeError, RecursionError) as exc: raise AccessError('Invalid transaction journal') from exc
        self._validated(record)
        if record['status'] != 'pending': return False
        self._restore(record); return True

    def recover(self):
        with exclusive_lock(self.lock): return self._recover()

    def apply(self, changes, checks=()):
        """changes: iterable of (relative path, expected bytes/None, replacement bytes/None)."""
        items, total = [], 0
        for path, before, after in changes:
            for value in (before, after):
                if value is not None and (not isinstance(value, bytes) or len(value) > MAX_FILE):
                    raise ValueError('Transaction files must be bounded bytes or None')
                total += len(value or b'')
            if total > MAX_BYTES: raise ValueError('Transaction batch exceeds the byte limit')
            items.append({'path': path, 'before': self._encoded(before), 'after': self._encoded(after)})
            if len(items) > MAX_CHANGES: raise ValueError('Too many transaction files')
        record = {'format': 'winterx.private-transaction/1', 'id': uuid.uuid4().hex,
                  'target': self.target, 'policy': self.policy, 'status': 'pending', 'changes': items}
        decoded = self._validated(record)
        with exclusive_lock(self.lock):
            self._recover()
            for path, expected in checks:
                if self.store.read(relative_path(path)) != expected:
                    raise ConflictError('Private input changed before transaction: ' + path)
            for path, before, after in decoded:
                if self.store.read(path) != before: raise ConflictError('Private file changed before transaction: ' + path)
            self._save(record)  # Durable expected/replacement bytes before the first remote write.
            try:
                for path, before, after in decoded:
                    if before == after: continue
                    if self.before_write is not None: self.before_write()
                    if after is None: self.store.remove(path, expected=before)
                    else: self.store.write(path, after, expected=before)
                record['status'] = 'committed'; self._save(record)
            except BaseException:
                record['status'] = 'pending'
                self._restore(record)
                raise
        return record['id']
