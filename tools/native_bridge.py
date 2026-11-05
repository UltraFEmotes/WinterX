"""Ruby-driven native/JavaScript package installs on an actually verified rooted runtime."""
import json
from pathlib import Path
import re
import tempfile
import time

from file_lock import exclusive_lock
from private_files import AccessError, relative_path
from private_transaction import Transactions, RecoveryRequired, bridge_owned
from portable_bridge import APP, REQUEST, _object
import native_package
import ruby_packages
import ruby_repositories
import springys_registry

MAX_FILES = 512
# Handled inside a core that advertises its own package manager; repositories stay with the bridge.
CORE_ACTIONS = frozenset(('scan_packages', 'install_package', 'remove_package'))
MAX_BYTES = 32 * 1024 * 1024


def native_owned(path):
    path = relative_path(path)
    if bridge_owned(path) or path == APP + '/live.json': return True
    match = re.fullmatch(r'winterx-tweaks/([a-z0-9]+(?:[.-][a-z0-9]+)+)/(.+)', path)
    if match: tail = match[2]
    else:
        match = re.fullmatch(re.escape(APP) + r'/package-registry/tweaks/[0-9a-f]{64}/(.+)', path)
        if not match: return False
        tail = match[1]
    return tail in (native_package.DEX, native_package.JAR) or bool(native_package.SOURCE.fullmatch(tail) or native_package.LICENSE.fullmatch(tail)
                                                                     or native_package.APP.fullmatch(tail) or native_package.INJECT.fullmatch(tail))


class NativeBridge:
    def __init__(self, store, state, verify_runtime, fetch=ruby_repositories.download, builtin=None):
        self.store, self.state, self.verify_runtime = store, Path(state), verify_runtime
        self.fetch, self.builtin = fetch, builtin
        self.last_heartbeat = 0
        self.completed = set()
        self.check_runtime()
        self.transactions = Transactions(store, state, owned=native_owned, policy='native-code-v1', before_write=self.check_runtime)

    def check_runtime(self):
        result = self.verify_runtime()
        if (not isinstance(result, dict) or result.get('phase') != 'installed' or result.get('runtimeAbi') != 'winterx-native-hooks-v1'
                or result.get('coreFilesRoot') != str(self.store.root)):
            raise AccessError('Native package operations require the actual compatible running core')
        return result

    def core_manages_packages(self):
        try:
            raw = self.store.read('ruby/capabilities-v1.json', 65536)
            return bool(raw) and json.loads(raw).get('packageManager') == 'winterx-pm-v1'
        except (ValueError, AccessError, OSError):
            return False

    def _snapshot(self):
        paths = {APP + '/' + name for name in ('packages.json', 'sources.json', 'repository-catalogue.json',
                  'package-registry/installed.json', 'package-registry/operation.json')}
        for tree in ('imports', 'package-registry', 'package-art'):
            for path in self.store.list_files(APP + '/' + tree, limit=MAX_FILES):
                if path.endswith('/.lock'): continue
                if tree == 'imports':
                    if path.count('/') != (APP + '/imports/file').count('/') or not path.lower().endswith('.springys'): continue
                elif not native_owned(path): raise AccessError('Unrecognized registry-owned path')
                paths.add(path)
        registry_raw = self.store.read(APP + '/package-registry/installed.json', limit=512 * 1024)
        registry = json.loads(registry_raw, object_pairs_hook=_object) if registry_raw else {}
        if not isinstance(registry, dict): raise AccessError('Invalid Ruby registry')
        for package_id, record in registry.items():
            if record.get('type') != 'tweak': continue
            if not re.fullmatch(r'[a-z0-9]+(?:[.-][a-z0-9]+)+', package_id): raise AccessError('Invalid installed code package ID')
            names = tuple(record.get('files', {})) if record.get('runtime') == 'java' else ('code/main.js',)
            for name in (*names, 'manifest.json', 'manifest.sha256', 'sha256', 'enabled'):
                path = 'winterx-tweaks/' + package_id + '/' + name
                if not native_owned(path): raise AccessError('Package declares a non-runtime file')
                paths.add(path)
        if len(paths) > MAX_FILES: raise AccessError('Ruby package snapshot exceeds its file bound')
        values, size = {}, 0
        for path in sorted(paths):
            value = self.store.read(path); size += len(value or b'')
            if size > MAX_BYTES: raise AccessError('Ruby snapshot exceeds its byte bound')
            values[path] = value
        return values

    @staticmethod
    def _materialize(root, snapshot):
        for name, value in snapshot.items():
            if value is not None:
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(value)

    @staticmethod
    def _outputs(root):
        result, size = {}, 0
        for subtree in (root / APP, root / 'winterx-tweaks'):
            for path in sorted(subtree.rglob('*')):
                if path.is_symlink(): raise AccessError('Package mirror contains a link')
                if not path.is_file() or path.name == '.lock': continue
                name = path.relative_to(root).as_posix()
                value = path.read_bytes(); size += len(value)
                if size > MAX_BYTES or len(result) >= MAX_FILES: raise AccessError('Package mirror exceeds its bound')
                result[name] = value
        return result

    def process(self, request):
        if request in self.completed: return False
        match = REQUEST.fullmatch(request)
        if not match: return False
        result_path = APP + '/results/' + match[1] + '.json'
        if self.store.read(result_path, 65536) is not None:
            self.completed.add(request)
            return False
        raw = self.store.read(request, 65536)
        if raw is None: return False
        action = ''; log = []  # Real steps, shown in Ruby's install console
        try:
            self.check_runtime(); log.append('Checked the running WinterX core')
            request_data = json.loads(raw, object_pairs_hook=_object)
            if not isinstance(request_data, dict) or request_data.get('id') != match[1]: raise ValueError('Invalid Ruby request')
            action = request_data.get('action')
            if action in CORE_ACTIONS and self.core_manages_packages():
                self.completed.add(request)
                return False
            if action not in ('scan_packages', 'install_package', 'remove_package', 'add_repository', 'remove_repository', 'refresh_repositories'):
                raise ValueError('Unsupported native package-manager operation')
            before = self._snapshot(); log.append('Read %d private package-manager files' % len(before))
            with tempfile.TemporaryDirectory(prefix='native-ruby-', dir=self.state) as name:
                root = Path(name); self._materialize(root, before)
                packages = ruby_packages.Packages(root / APP, root / 'ruby/settings-test.enabled', lambda enabled: {'ok': False},
                    tweak_root=root / 'winterx-tweaks', supported_tweaks=True, supported_native=True,
                    supported_capabilities=('native.hooks', 'home.read', 'home.grid'))
                packages.registry.recover()
                if action == 'install_package':
                    record = packages.install(request_data.get('filename'))
                    log.append('Verified %s %s (%s)' % (record.get('name', record['id']), record.get('version', ''), record['id']))
                    log.append('Checksum %s… matches' % record['sha256'][:16])
                    if record.get('runtime') == 'java': log.append('Unpacked Java/Dex code into its own folder')
                elif action == 'remove_package':
                    record = packages.uninstall(request_data.get('packageId'))
                    log.append('Removed %s %s; its saved preferences were kept' % (record.get('name', record['id']), record.get('version', '')))
                elif action in ('add_repository', 'remove_repository', 'refresh_repositories'):
                    repositories = ruby_repositories.Repositories(root / APP, packages, self.fetch, self.builtin)
                    if action == 'add_repository': repositories.add(request_data.get('url', ''))
                    elif action == 'remove_repository': repositories.remove(request_data.get('url', ''))
                    else: repositories.refresh()
                ruby_packages._atomic(root / APP / 'packages.json', json.dumps(packages.scan()).encode())
                after = self._outputs(root)
                changes = []
                for path in sorted(set(before) | set(after)):
                    old, new = before.get(path), after.get(path)
                    if old == new: continue
                    if not native_owned(path): raise AccessError('Package operation tried to change user-owned files')
                    # New package IDs can have preserved data/code from an earlier
                    # removal. Recheck those exact owned paths, never their state/data.
                    if path not in before:
                        old = self.store.read(path)
                        before[path] = old
                    changes.append((path, old, new))
                restart = action == 'install_package'
                log.append('Wrote %d package-manager files; none of your own files changed' % len(changes))
                reply = {'ok': True, 'action': action, 'restartRequired': restart, 'log': log,
                         'message': 'Code package installed. Reopen Spring through WinterX to load it.' if restart else 'Ruby package operation completed.'}
                changes.append((result_path, None, json.dumps(reply).encode()))
                self.transactions.apply(changes, checks=[(request, raw), *before.items()])
            self.completed.add(request)
            return True
        except (RecoveryRequired, springys_registry.RecoveryRequired): raise
        except (AccessError, OSError, ValueError, KeyError, TypeError) as error:
            reply = {'ok': False, 'action': action if isinstance(action, str) else '', 'message': str(error)[:250], 'log': log[:20]}
            self.transactions.apply([(result_path, None, json.dumps(reply).encode())], checks=[(request, raw)])
            self.completed.add(request)
            return True

    def once(self):
        with exclusive_lock(self.state / 'native-ruby.lock'):
            report = self.check_runtime(); self.transactions.recover()
            if time.monotonic() - self.last_heartbeat >= 3:
                live_path = APP + '/live.json'; old = self.store.read(live_path, 65536)
                value = json.dumps({'active': True, 'safeModeSupported': True, 'nativePackagesSupported': True,
                    'safeMode': report.get('safeMode', False), 'loadedPackages': report.get('loadedPackages', []),
                    'features': report.get('features', []),
                    'observedAt': int(time.time() * 1000), 'runtimeAbi': report['runtimeAbi']}).encode()
                self.transactions.apply([(live_path, old, value)])
                self.last_heartbeat = time.monotonic()
            return sum(self.process(path) for path in self.store.list_files(APP + '/requests', limit=MAX_FILES) if REQUEST.fullmatch(path))
