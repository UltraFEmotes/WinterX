"""Queue Spring app changes and confirm them from Spring's installed files.

This module deliberately never stops or starts Spring. The caller provides a
process check; removals are deferred until the entire launcher is closed.
"""
import json
import hashlib
import zipfile
import os
from pathlib import Path
import re
import shutil
import tempfile
import time

APP_ID = re.compile(r'^[a-z0-9]+(?:[.][a-z0-9]+)+$')


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.sapp-state-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(value, out, ensure_ascii=False, sort_keys=True)
            out.flush(); os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


class Lifecycle:
    def __init__(self, spring_files, inbox, state, check_sapp, is_running, hot_install=False):
        self.files, self.inbox, self.state = map(Path, (spring_files, inbox, state))
        self.check_sapp, self.is_running = check_sapp, is_running
        self.hot_install = hot_install
        self.pending = self.state / 'pending.json'
        self.installed = self.state / 'installed.json'

    def _read(self, path):
        if not path.exists(): return {}
        value = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(value, dict): raise ValueError('Invalid app package state')
        return value

    def queue_install(self, app_id, sapp):
        if not isinstance(app_id, str) or not APP_ID.fullmatch(app_id): raise ValueError('Invalid app ID')
        source = Path(sapp).resolve(strict=True)
        manifest = self.check_sapp(str(source))
        if manifest.get('id') != app_id: raise ValueError('Spring app ID does not match package')
        build = manifest.get('build')
        if not isinstance(build, int) or isinstance(build, bool) or build < 1: raise ValueError('Invalid Spring app build')
        pending = self._read(self.pending)
        if app_id in pending: raise ValueError('An operation is already pending for this app')
        self.inbox.mkdir(parents=True, exist_ok=True)
        destination = self.inbox / ('ruby-app-' + app_id + '-' + str(build) + '.sapp')
        if destination.exists() or destination.is_symlink(): raise ValueError('That app is already queued')
        with zipfile.ZipFile(source) as archive:
            expected = {name: hashlib.sha256(archive.read(name)).hexdigest()
                        for name in archive.namelist() if not name.endswith('/') and
                        not name.startswith('__MACOSX/') and not name.endswith('.DS_Store')}
        pending[app_id] = {'action': 'install', 'build': build, 'inbox': destination.name,
                           'files': expected}
        # Record intent before publication; a crash may leave a harmless intent
        # without an inbox file, which is reported rather than called installed.
        atomic_json(self.pending, pending)
        try:
            fd, temporary = tempfile.mkstemp(prefix='.ruby-app-', suffix='.pending', dir=self.inbox)
            try:
                with source.open('rb') as src, os.fdopen(fd, 'wb') as dst:
                    shutil.copyfileobj(src, dst); dst.flush(); os.fsync(dst.fileno())
                os.replace(temporary, destination)
            finally:
                if os.path.exists(temporary): os.unlink(temporary)
        except Exception:
            pending.pop(app_id, None); atomic_json(self.pending, pending)
            raise
        return {'status': 'pending', 'message': ('Spring is installing the app. Reopen the app if it was already open.' if self.hot_install else 'Fully reopen Spring Launcher to install the app.')}

    def queue_remove(self, app_id):
        if not isinstance(app_id, str) or not APP_ID.fullmatch(app_id): raise ValueError('Invalid app ID')
        installed, pending = self._read(self.installed), self._read(self.pending)
        if app_id not in installed: raise ValueError('This app is not managed by Ruby')
        if app_id in pending: raise ValueError('An operation is already pending for this app')
        pending[app_id] = {'action': 'remove'}
        atomic_json(self.pending, pending)
        return {'status': 'pending', 'message': 'Fully close Spring Launcher to remove the app.'}

    def reconcile(self):
        pending, installed = self._read(self.pending), self._read(self.installed)
        running = self.is_running()
        for app_id, operation in list(pending.items()):
            if not APP_ID.fullmatch(app_id): raise ValueError('Invalid pending app ID')
            if operation['action'] == 'install':
                build = operation['build']
                manifest_path = self.files / 'sapps' / app_id / str(build) / 'app.json'
                queued = self.inbox / operation['inbox']
                if not queued.exists() and manifest_path.is_file() and not manifest_path.is_symlink():
                    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
                    app_root = manifest_path.parent.resolve(strict=True)
                    expected = operation.get('files', {})
                    matches = bool(expected)
                    for name, digest in expected.items():
                        path = app_root / name
                        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(app_root):
                            matches = False; break
                        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                            matches = False; break
                    if matches and manifest.get('id') == app_id and manifest.get('build') == build:
                        installed[app_id] = {'build': build}
                        atomic_json(self.installed, installed)
                        del pending[app_id]
                        atomic_json(self.pending, pending)
            elif operation['action'] == 'remove' and not running:
                app_dir = self.files / 'sapps' / app_id
                if app_dir.is_symlink(): raise ValueError('Unexpected app directory')
                if app_dir.exists():
                    backup = self.state / 'removed' / (app_id + '-' + str(time.time_ns()))
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(app_dir, backup)
                installed.pop(app_id, None)
                atomic_json(self.installed, installed)
                del pending[app_id]
                atomic_json(self.pending, pending)
            elif operation['action'] not in ('install', 'remove'):
                raise ValueError('Invalid pending action')
        return {'pending': pending, 'installed': installed}
