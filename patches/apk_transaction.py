"""Reversible, offline APK replacement for the Mac.APK integration.

The caller is responsible for stopping Spring before activation or rollback.
This module does not stop, launch, or otherwise control an application.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def atomic_copy(source, target):
    source, target = Path(source), Path(target)
    fd, name = tempfile.mkstemp(prefix='.ruby-', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as out, source.open('rb') as inp:
            shutil.copyfileobj(inp, out, 1024 * 1024)
            out.flush()
            os.fsync(out.fileno())
        if target.exists():
            os.chmod(name, target.stat().st_mode & 0o777)
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def atomic_record(path, value):
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix='.ruby-state-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(value, out, indent=2)
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def prepare(target, patch, state, expected_original):
    target, patch, state = Path(target).resolve(strict=True), Path(patch).resolve(strict=True), Path(state).resolve()
    if target == patch:
        raise ValueError('Patch and installed APK must be different files')
    if digest(target) != expected_original:
        raise ValueError('Installed APK is not the expected original')
    state.mkdir(parents=True, exist_ok=True)
    journal, original = state / 'transaction.json', state / 'original.apk'
    if journal.exists():
        raise ValueError('A transaction already exists; resolve it before starting another')
    if original.exists():
        raise ValueError('Existing backup found; refusing to overwrite it')
    atomic_copy(target, original)
    if digest(original) != expected_original:
        raise IOError('Backup verification failed')
    record = {'target': str(target), 'patch': str(patch), 'original': str(original),
              'original_sha256': expected_original, 'patch_sha256': digest(patch), 'state': 'prepared'}
    atomic_record(journal, record)
    return record


def activate(state):
    journal = Path(state) / 'transaction.json'
    record = json.loads(journal.read_text(encoding='utf-8'))
    if record['state'] != 'prepared':
        raise ValueError('Transaction is not prepared')
    target, patch = Path(record['target']), Path(record['patch'])
    if digest(target) != record['original_sha256'] or digest(patch) != record['patch_sha256']:
        raise ValueError('APK changed after preparation')
    # Record intent first so recovery can restore the backup after a crash.
    record['state'] = 'activating'
    atomic_record(journal, record)
    atomic_copy(patch, target)
    if digest(target) != record['patch_sha256']:
        raise IOError('Installed APK verification failed')
    record['state'] = 'active_unverified'
    atomic_record(journal, record)
    return record


def rollback(state):
    journal = Path(state) / 'transaction.json'
    record = json.loads(journal.read_text(encoding='utf-8'))
    target, original = Path(record['target']), Path(record['original'])
    if record['state'] not in ('prepared', 'activating', 'active_unverified', 'verified'):
        raise ValueError('Transaction cannot be rolled back')
    if digest(original) != record['original_sha256']:
        raise ValueError('Backup failed verification')
    current = digest(target)
    if current not in (record['original_sha256'], record['patch_sha256']):
        raise ValueError('Installed APK changed independently; refusing to overwrite it')
    if current != record['original_sha256']:
        atomic_copy(original, target)
    if digest(target) != record['original_sha256']:
        raise IOError('Restored APK failed verification')
    record['state'] = 'rolled_back'
    atomic_record(journal, record)
    return record


def prepare_boot(state, marker):
    """Clear the hook's own previous receipt immediately before launching Spring."""
    journal = Path(state) / 'transaction.json'
    record = json.loads(journal.read_text(encoding='utf-8'))
    if record['state'] != 'active_unverified':
        raise ValueError('Transaction is not awaiting boot verification')
    marker = Path(marker)
    if marker.name != 'boot-ok-v1' or marker.parent.name != 'ruby' or marker.is_symlink():
        raise ValueError('Unexpected boot marker path')
    marker.unlink(missing_ok=True)
    record['boot_marker'] = str(marker.resolve())
    record['boot_started_ns'] = time.time_ns()
    atomic_record(journal, record)
    return record


def verify_boot(state):
    journal = Path(state) / 'transaction.json'
    record = json.loads(journal.read_text(encoding='utf-8'))
    if record['state'] != 'active_unverified' or 'boot_marker' not in record:
        raise ValueError('No boot is awaiting verification')
    marker = Path(record['boot_marker'])
    if marker.is_symlink() or not marker.is_file():
        return False
    if marker.stat().st_mtime_ns < record['boot_started_ns']:
        return False
    if digest(record['target']) != record['patch_sha256']:
        raise ValueError('Installed APK changed during boot')
    record['state'] = 'verified'
    atomic_record(journal, record)
    return True
