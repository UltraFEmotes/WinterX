#!/usr/bin/env python3
"""Development Ruby inventory/repository bridge. No APK installation or process control."""
import argparse
import json
from pathlib import Path
import re
import tempfile

from file_lock import exclusive_lock
from private_files import AccessError, AdbFiles, DirectoryFiles, SshFiles
from private_transaction import RecoveryRequired, Transactions, bridge_owned
import ruby_packages
import ruby_repositories
import springys_registry

ROOT = Path(__file__).resolve().parents[1]
APP = 'sapps-data/com.ruby.manager/files'
REQUEST = re.compile(re.escape(APP) + r'/requests/([0-9]{1,30}-[0-9]{1,30})\.json$')
MAX_FILES = 256
MAX_SNAPSHOT = 24 * 1024 * 1024
FIXED = ('packages.json', 'sources.json', 'repository-catalogue.json',
         'package-registry/installed.json', 'package-registry/operation.json')
TREES = ('imports', 'package-registry', 'package-art')


class InventoryPackages(ruby_packages.Packages):
    def _reconcile(self, hooks, tweaks=None):
        # Packages.scan() can run recovery. Do not let a read-oriented scan silently
        # enable code/markers in the absence of a verified running Android engine.
        raise springys_registry.RecoveryRequired('Package recovery requires a verified engine; this portable inventory bridge cannot reconcile tweaks yet')


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value: raise ValueError('Duplicate JSON field: ' + key)
        value[key] = item
    return value


class Bridge:
    def __init__(self, store, state, fetch=ruby_repositories.download, builtin=ROOT / 'builtin-repo'):
        self.store = store
        self.state = Path(state)
        self.transactions = Transactions(store, self.state)
        self.fetch, self.builtin = fetch, builtin

    def _paths(self):
        paths = {APP + '/' + relative for relative in FIXED}
        for tree in TREES:
            for path in self.store.list_files(APP + '/' + tree, limit=MAX_FILES):
                if path == APP + '/package-registry/.lock': continue
                if tree == 'imports':
                    if path.count('/') != (APP + '/imports/name').count('/') or not path.lower().endswith('.springys'): continue
                elif not bridge_owned(path):
                    raise AccessError('Unexpected file in a bridge-owned subtree: ' + path)
                paths.add(path)
                if len(paths) > MAX_FILES: raise AccessError('Ruby snapshot exceeds the file limit')
        return sorted(paths)

    def _snapshot(self):
        values, used = {}, 0
        for path in self._paths():
            value = self.store.read(path, limit=MAX_SNAPSHOT - used)
            used += len(value or b'')
            values[path] = value
        return values

    def _budgeted_fetch(self):
        used = 0
        def fetch(url, limit):
            nonlocal used
            value = self.fetch(url, min(limit, MAX_SNAPSHOT - used))
            used += len(value)
            if used > MAX_SNAPSHOT: raise AccessError('Repository transfer exceeds the batch byte limit')
            return value
        return fetch

    def _builtin_budget(self):
        if self.builtin is None: return
        root = Path(self.builtin).resolve(strict=True)
        with (root / 'index.json').open('rb') as source: raw = source.read(ruby_repositories.INDEX_LIMIT + 1)
        if len(raw) > ruby_repositories.INDEX_LIMIT: raise AccessError('Built-in index exceeds its bound')
        entries = json.loads(raw).get('packages', [])
        if not isinstance(entries, list) or len(entries) > ruby_repositories.MAX_PACKAGES:
            raise AccessError('Built-in catalogue exceeds its package limit')
        used = len(raw)
        for item in entries:
            path = (root / item['url']).resolve(strict=True)
            if not path.is_relative_to(root) or not path.is_file(): raise AccessError('Invalid built-in package path')
            size = path.stat().st_size
            if size > ruby_repositories.PACKAGE_LIMIT: raise AccessError('Built-in package exceeds its bound')
            used += size
        if used > MAX_SNAPSHOT: raise AccessError('Built-in catalogue exceeds the batch byte limit')

    @staticmethod
    def _materialize(root, before):
        for path, payload in before.items():
            if payload is None: continue
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)

    @staticmethod
    def _outputs(root):
        values, used = {}, 0
        app = root / APP
        for path in sorted(app.rglob('*')):
            if not path.is_file(): continue
            relative = path.relative_to(root).as_posix()
            if relative == APP + '/package-registry/.lock': continue
            if path.is_symlink(): raise AccessError('Unexpected mirror symlink')
            size = path.stat().st_size; used += size
            if used > MAX_SNAPSHOT: raise AccessError('Ruby mirror exceeds the batch byte limit')
            values[relative] = path.read_bytes()
            if len(values) > MAX_FILES: raise AccessError('Ruby mirror exceeds the file limit')
        return values

    def process(self, request):
        match = REQUEST.fullmatch(request)
        if not match: return False
        result = APP + '/results/' + match[1] + '.json'
        if self.store.read(result, limit=64 * 1024) is not None: return False
        raw = self.store.read(request, limit=64 * 1024)
        if raw is None: return False
        action = ''
        try:
            record = json.loads(raw, object_pairs_hook=_object)
            if not isinstance(record, dict) or record.get('id') != match[1]: raise ValueError('Invalid Ruby request ID')
            action = record.get('action', '')
            if action in ('install_package', 'remove_package'):
                raise AccessError('Portable tweak installation/removal requires verified running-engine support, which is not implemented yet')
            if action not in ('scan_packages', 'add_repository', 'remove_repository', 'refresh_repositories'):
                raise ValueError('This portable bridge supports only package inventory and repository requests')
            before = self._snapshot()
            with tempfile.TemporaryDirectory(prefix='winterx-portable-mirror-', dir=self.state) as name:
                root = Path(name); self._materialize(root, before)
                files = root / APP; files.mkdir(parents=True, exist_ok=True)
                packages = InventoryPackages(files, root / 'ruby/settings-test.enabled', lambda enabled: None)
                packages.registry.recover()  # Pending operations fail closed, including repository-only requests.
                if action != 'scan_packages':
                    self._builtin_budget()
                    repos = ruby_repositories.Repositories(files, packages, self._budgeted_fetch(), self.builtin)
                    if action == 'add_repository': repos.add(record.get('url', ''))
                    elif action == 'remove_repository': repos.remove(record.get('url', ''))
                    else: repos.refresh()
                ruby_packages._atomic(files / 'packages.json', json.dumps(packages.scan()).encode())
                after = self._outputs(root)
                changes = []
                for path in sorted(set(before) | set(after)):
                    old, new = before.get(path), after.get(path)
                    if old == new: continue
                    if not bridge_owned(path): raise AccessError('Portable bridge attempted to change a user-owned file')
                    changes.append((path, old, new))
                reply = {'ok': True, 'action': action, 'restartRequired': False,
                         'message': 'Package inventory/repository request completed; no tweaks were installed'}
                changes.append((result, None, json.dumps(reply).encode()))
                self.transactions.apply(changes, checks=[(request, raw), *before.items()])
            return True
        except (RecoveryRequired, springys_registry.RecoveryRequired):
            raise  # No misleading completion receipt while recovery is blocked.
        except (AccessError, ValueError, OSError, KeyError, TypeError) as exc:
            reply = {'ok': False, 'action': action if isinstance(action, str) else '', 'message': str(exc)[:250]}
            self.transactions.apply([(result, None, json.dumps(reply).encode())], checks=[(request, raw)])
            return True

    def once(self):
        with exclusive_lock(self.state / 'portable-bridge.lock'):
            self.transactions.recover()
            return sum(self.process(path) for path in self.store.list_files(APP + '/requests', limit=MAX_FILES) if REQUEST.fullmatch(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--serial'); target.add_argument('--directory', type=Path); target.add_argument('--ssh-host')
    parser.add_argument('--files-root', default='/data/user/0/com.guille.spring/files')
    parser.add_argument('--access', choices=('shell', 'run-as', 'su'), default='shell')
    parser.add_argument('--adb', default='adb')
    parser.add_argument('--ssh', default='ssh'); parser.add_argument('--ssh-port', type=int, default=22)
    parser.add_argument('--state', type=Path, required=True, help='Dedicated host recovery directory for this exact target')
    args = parser.parse_args()
    if args.ssh_host: store = SshFiles(args.ssh_host, args.files_root, args.access, args.ssh_port, args.ssh)
    elif args.serial: store = AdbFiles(args.serial, args.files_root, args.access, args.adb)
    else: store = DirectoryFiles(args.directory)
    if isinstance(store, AdbFiles): store.verify()
    count = Bridge(store, args.state).once()
    print('Processed', count, 'Ruby inventory/repository requests. No engine or app was installed, stopped or started.')


if __name__ == '__main__': main()
