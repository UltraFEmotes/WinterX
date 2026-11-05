#!/usr/bin/env python3
"""Rooted Android/emulator runtime: preserve the installed APK, load core DEX at a fresh app start."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import queue
import shlex
import subprocess
import tempfile
import threading
import time
import uuid

from private_files import AdbFiles, AccessError

PACKAGE = 'com.guille.spring'
SOURCE_SHA = 'f07f980fe681a6de9c4ce8735ae1c0bb0f852f447fbdb925d2dec37cf9778e5c'
ABI = 'winterx-native-hooks-v1'
MAX_DEX = 32 * 1024 * 1024


class RootRuntime:
    def __init__(self, serial, state, access='su', adb='adb', frida_port=27048):
        if access not in ('su', 'shell'): raise ValueError('Rooted runtime access must be su or already-root ADB shell')
        if not isinstance(frida_port, int) or not 1024 <= frida_port <= 65535: raise ValueError('Invalid loopback Frida port')
        self.store = AdbFiles(serial, '/data/user/0/' + PACKAGE + '/files', access, adb)
        self.state = Path(state).resolve(); self.state.mkdir(parents=True, exist_ok=True)
        self.port = frida_port
        self.session = self.script = self.device = None
        self.identity = self.plan = None

    def shell(self, script): return self.store._run(script).decode('utf-8', errors='strict')

    def verify_transport(self):
        result = self.store.runner([self.store.adb, 'forward', '--list'], input=None,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20, check=False, shell=False)
        if result.returncode:
            raise AccessError('Could not verify the explicit ADB/Frida transport')
        entries = [line.split() for line in result.stdout.decode('utf-8', errors='strict').splitlines()]
        local = 'tcp:' + str(self.port)
        matches = [entry for entry in entries if len(entry) == 3 and entry[1] == local]
        if matches != [[self.store.serial, local, 'tcp:27042']]:
            raise AccessError('Forward this target\'s Frida loopback port first: adb -s ' + self.store.serial + ' forward ' + local + ' tcp:27042')

    def inspect(self):
        raw = self.shell('set -eu\nid -u\ngetprop ro.build.version.sdk\ngetprop ro.product.cpu.abi\npm path ' + PACKAGE + '\n')
        lines = raw.splitlines()
        if len(lines) != 4 or lines[0] != '0' or not lines[1].isdigit() or int(lines[1]) < 26:
            raise AccessError('A root-capable Android API 26+ target with one installed Spring APK is required')
        if lines[2] not in ('arm64-v8a', 'x86_64', 'armeabi-v7a', 'x86') or not lines[3].startswith('package:'):
            raise AccessError('Unsupported Android runtime identity')
        apk = lines[3][8:]
        if not re.fullmatch(r'/data/app/[A-Za-z0-9_~+./=-]+/base\.apk', apk): raise AccessError('Unexpected installed APK path')
        checksum = self.shell('sha256sum ' + shlex.quote(apk) + '\n').split()[0]
        if checksum != SOURCE_SHA: raise AccessError('Installed Spring must match the supported original 0.8.1 APK; no package is replaced')
        package = self.shell('dumpsys package ' + PACKAGE + '\n')
        uid = re.search(r'\buserId=(\d+)\b', package)
        version = re.search(r'\bversionName=([^\s]+)', package)
        if uid is None or version is None or version.group(1) != '0.8.1' or not 10000 <= int(uid.group(1)) < 100000:
            raise AccessError('Expected the original Spring 0.8.1 owner-user package')
        self.identity = {'serial': self.store.serial, 'uid': int(uid.group(1)), 'api': int(lines[1]), 'abi': lines[2],
                         'apkPath': apk, 'apkSha256': checksum, 'package': PACKAGE, 'access': self.store.access}
        return dict(self.identity)

    def stopped(self):
        pids = self.shell('pidof ' + PACKAGE + ' || true\n').strip()
        if pids: raise AccessError('Fully close Spring on this target first. The runtime never stops an existing Spring process.')

    def backup(self, limit=2 * 1024 * 1024 * 1024):
        self.stopped()
        path = self.state / ('before-core-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.tar')
        partial = path.with_suffix('.tar.partial')
        script = 'set -eu\ntest -d /data/user/0/' + PACKAGE + '\ntar -C /data/user/0/' + PACKAGE + ' -cf - .\n'
        marker = 'WINTERX_BACKUP_' + uuid.uuid4().hex
        script = 'set +e\n(\n' + script + ')\nstatus=$?\nprintf ' + shlex.quote('\n' + marker + ':%s\n') + ' "$status"\n'
        command = [self.store.adb, '-s', self.store.serial, 'exec-out', shlex.join(self.store._remote(script))]
        errors = tempfile.TemporaryFile()
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors)
        chunks = queue.Queue(maxsize=8)
        cancelled = threading.Event()
        def read():
            try:
                while not cancelled.is_set():
                    chunk = process.stdout.read(65536)
                    while not cancelled.is_set():
                        try: chunks.put(chunk, timeout=.2); break
                        except queue.Full: pass
                    if not chunk: return
            except (OSError, ValueError):
                if not cancelled.is_set():
                    try: chunks.put(b'', timeout=1)
                    except queue.Full: pass
        reader = threading.Thread(target=read, daemon=True); reader.start()
        digest = hashlib.sha256(); total = 0
        tail = b''
        try:
            deadline = time.monotonic() + 600
            with partial.open('xb') as output:
                partial.chmod(0o600)
                while True:
                    if time.monotonic() >= deadline: raise AccessError('Private-data backup timed out; staging refused')
                    try: chunk = chunks.get(timeout=min(1, max(.01, deadline - time.monotonic())))
                    except queue.Empty: continue
                    if not chunk: break
                    tail += chunk
                    if total + len(tail) > limit + 256: raise AccessError('Private-data backup exceeded its bound; staging refused')
                    if len(tail) > 256:
                        block, tail = tail[:-256], tail[-256:]
                        total += len(block); digest.update(block); output.write(block)
                footer = ('\n' + marker + ':0\n').encode()
                if not tail.endswith(footer): raise AccessError('Remote private-data backup failed or its status was truncated')
                tail = tail[:-len(footer)]; total += len(tail)
                if total > limit: raise AccessError('Private-data backup exceeded its bound; staging refused')
                digest.update(tail); output.write(tail)
                output.flush(); os.fsync(output.fileno())
            status = process.wait(timeout=60)
            if status: raise AccessError('Private-data backup failed; staging refused')
            os.replace(partial, path)
        except BaseException:
            cancelled.set()
            if process.poll() is None: process.kill(); process.wait(timeout=10)
            raise
        finally:
            cancelled.set(); reader.join(timeout=2)
            process.stdout.close(); errors.close()
        return {'path': str(path), 'sha256': digest.hexdigest(), 'bytes': total}

    def stage(self, payload):
        identity = self.inspect(); self.stopped()
        root = Path(payload).resolve(strict=True)
        manifest = json.loads((root / 'manifest.json').read_text())
        if (manifest.get('format') != 'winterx.android-runtime/1' or manifest.get('package') != PACKAGE or
                manifest.get('sourceApkSha256') != SOURCE_SHA or manifest.get('runtimeAbi') != ABI or manifest.get('preinstalledTweaks') != [] or
                set(manifest.get('files', {})) != {'spring-hooks.dex', 'winterx-core.dex'}):
            raise ValueError('Invalid core-only runtime manifest')
        values = {}
        for name, expected in manifest['files'].items():
            path = root / name
            if path.is_symlink() or path.stat().st_size > MAX_DEX: raise ValueError('Unsafe runtime DEX path')
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != expected or raw[:4] != b'dex\n': raise ValueError('Runtime DEX checksum mismatch')
            values[name] = raw
        backup = self.backup(); self.stopped()
        files = '/data/user/0/' + PACKAGE + '/files'
        self.shell('set -eu\ntest ! -L ' + files + '\nif test ! -e ' + files + '; then mkdir ' + files + '\nchown ' + str(identity['uid']) + ':' + str(identity['uid']) + ' ' + files + '\nchmod 700 ' + files + '\nrestorecon -F ' + files + '\nfi\n')
        verified = self.store.verify()
        if verified['owner'] != identity['uid']: raise AccessError('Spring private-folder ownership changed')
        revision = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
        paths = []
        for name, raw in values.items():
            self.stopped(); relative = 'ruby/runtime/' + revision + '/' + name
            old = self.store.read(relative, limit=24 * 1024 * 1024)
            if old is None: self.store.write(relative, raw, expected=None)
            elif old != raw: raise AccessError('Existing runtime revision differs; refusing replacement')
            remote = self.store.root + '/' + relative
            self.shell('chmod 444 ' + shlex.quote(remote) + '\n')
            paths.append({'path': remote, 'sha256': hashlib.sha256(raw).hexdigest()})
        self.stopped()
        if self.inspect() != identity: raise AccessError('Installed package changed during staging')
        plan = {'format': 'winterx.android-session/1', 'identity': identity, 'backup': backup,
                'configuration': {'package': PACKAGE, 'nonce': uuid.uuid4().hex, 'apkPath': identity['apkPath'],
                                  'filesRoot': self.store.root, 'files': paths, 'earlyClasses': manifest['earlyClasses']},
                'preinstalledTweaks': [], 'started': False}
        (self.state / 'android-runtime.json').write_text(json.dumps(plan, indent=2) + '\n')
        self.plan = plan
        return plan

    def launch(self, agent):
        import frida
        self.stopped(); identity = self.inspect()
        plan = self.plan or json.loads((self.state / 'android-runtime.json').read_text())
        if plan['identity'] != identity or plan.get('preinstalledTweaks') != []: raise AccessError('Staged runtime belongs to a different target/package')
        for file in plan['configuration']['files']:
            if self.shell('sha256sum ' + shlex.quote(file['path']) + '\n').split()[0] != file['sha256']:
                raise AccessError('Staged runtime file changed')
        source = Path(agent).read_text()
        if len(source) > 4 * 1024 * 1024: raise ValueError('Root loader script exceeds its limit')
        self.verify_transport()
        self.device = frida.get_device_manager().add_remote_device('127.0.0.1:' + str(self.port))
        pid = self.device.spawn([PACKAGE]); resumed = False
        try:
            self.session = self.device.attach(pid); self.script = self.session.create_script(source)
            self.script.load(); self.script.exports_sync.arm(plan['configuration']); self.device.resume(pid); resumed = True
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                report = self.script.exports_sync.status()
                if report.get('phase') == 'failed': raise AccessError(report.get('error', 'Root runtime injection failed'))
                if report.get('phase') == 'installed':
                    if report.get('nonce') != plan['configuration']['nonce'] or report.get('uid') != identity['uid'] or report.get('runtimeAbi') != ABI:
                        raise AccessError('Runtime acknowledgement did not match the package/UID/session')
                    plan.update(started=True, pid=pid, runtime=report)
                    (self.state / 'android-runtime.json').write_text(json.dumps(plan, indent=2) + '\n'); self.plan = plan
                    return report
                time.sleep(.1)
            raise AccessError('Runtime did not acknowledge loading; no package was replaced')
        except BaseException:
            if not resumed: self.device.kill(pid)  # Only this command's own unstarted child.
            if self.session is not None: self.session.detach()
            raise

    def verify_running(self, check_package=True):
        if self.script is None or self.plan is None: raise AccessError('No owned rooted runtime session')
        report = self.script.exports_sync.inspect()
        if (report.get('phase') != 'installed' or report.get('nonce') != self.plan['configuration']['nonce'] or
                report.get('runtimeAbi') != ABI or report.get('uid') != self.plan['identity']['uid'] or
                report.get('apkPath') != self.plan['identity']['apkPath'] or
                check_package and self.inspect() != self.plan['identity']):
            raise AccessError('Root runtime/package identity changed')
        return report

    def attach(self, agent):
        """Observe an already running, verified core; never inject late or restart it."""
        import frida
        identity = self.inspect(); plan = json.loads((self.state / 'android-runtime.json').read_text())
        if plan['identity'] != identity: raise AccessError('Staged core belongs to another target')
        pids = self.shell('pidof ' + PACKAGE + '\n').split()
        if len(pids) != 1 or not pids[0].isdigit(): raise AccessError('Expected one running Spring process')
        source = Path(agent).read_text()
        if len(source) > 4 * 1024 * 1024: raise ValueError('Root observer exceeds its bound')
        self.verify_transport()
        self.device = frida.get_device_manager().add_remote_device('127.0.0.1:' + str(self.port))
        self.session = self.device.attach(int(pids[0])); self.script = self.session.create_script(source)
        try:
            self.script.load(); self.script.exports_sync.observe(plan['configuration']); self.plan = plan
            return self.verify_running()
        except BaseException:
            self.session.detach(); raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True); parser.add_argument('--access', choices=('su', 'shell'), default='su')
    parser.add_argument('--adb', default='adb'); parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--frida-port', type=int, default=27048)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('inspect'); stage = commands.add_parser('stage'); stage.add_argument('payload', type=Path)
    launch = commands.add_parser('launch'); launch.add_argument('agent', type=Path)
    launch.add_argument('--bridge', action='store_true', help='Process explicit Ruby package requests while this verified session remains connected')
    launch.add_argument('--builtin-repo', type=Path, default=Path(__file__).resolve().parent.parent / 'builtin-repo',
                        help="Ruby's built-in source (default: this checkout's builtin-repo); listing it never installs a package")
    args = parser.parse_args(); runtime = RootRuntime(args.serial, args.state, args.access, args.adb, args.frida_port)
    if args.command == 'inspect': print(json.dumps(runtime.inspect(), indent=2))
    elif args.command == 'stage': print(json.dumps(runtime.stage(args.payload), indent=2))
    else:
        print(json.dumps(runtime.launch(args.agent), indent=2))
        print('Rooted runtime active. The installed Spring APK was not replaced; no tweaks were preinstalled.')
        bridge = None
        last_error = None
        detached = threading.Event()
        runtime.session.on('detached', lambda *args: detached.set())
        try:
            while not detached.is_set():
                try:
                    if args.bridge:
                        report = runtime.verify_running(check_package=False)
                        if report.get('coreFilesRoot'):
                            if bridge is None:
                                from native_bridge import NativeBridge
                                runtime.store.verify()
                                bridge = NativeBridge(runtime.store, runtime.state / 'ruby-bridge',
                                    lambda: runtime.verify_running(check_package=False), builtin=args.builtin_repo)
                                print('Ruby code-package bridge is ready.', flush=True)
                            count = bridge.once()
                            if count: print('Completed', count, 'Ruby package request(s).', flush=True)
                    if last_error is not None: print('Ruby bridge access recovered.', flush=True)
                    last_error = None
                except AccessError as error:
                    # A transport/guard failure must not destroy the owned Frida
                    # session. All writes still require runtime checks and the
                    # transaction's exact expected bytes, including recovery.
                    if str(error) != last_error: print('Ruby bridge paused:', str(error), flush=True)
                    last_error = str(error)
                detached.wait(2 if last_error is not None else 1)
        except KeyboardInterrupt:
            pass
        except Exception as failure:
            # Spring closing (swiped away, force-stopped, emulator shut down) destroys the script before or after
            # Frida's "detached" event; either way it is the normal end of a session, not a crash.
            import frida
            if not detached.is_set() and not isinstance(failure, (frida.InvalidOperationError, frida.ProcessNotFoundError, frida.TransportError)): raise
            detached.set()
        finally:
            if runtime.session is not None and not detached.is_set(): runtime.session.detach()
        print('Spring closed, so this WinterX session has ended. Start it again to reopen Spring with WinterX.', flush=True)


if __name__ == '__main__': main()
