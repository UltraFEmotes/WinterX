#!/usr/bin/env python3
"""Prepare or launch the core-only Mac.APK runtime, with a stopped-session backup and optional Ruby bridge."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'patches'))
import macapk_controls as control
import macapk_jailbreak as jailbreak
import macapk_overlay as overlay
import local_test_bundle as bundle
from file_lock import exclusive_lock
from native_package import dex_classes
from prepare_local_test import inventory

ABI = 'winterx-native-hooks-v1'
FORBIDDEN = ('Lwinterx/animaper/', 'Lwinterx/coloredbar/', 'Lwinterx/layout/', 'Lwinterx/snowy/',
             'Lwinterx/ssh/', 'Lwinterx/messages/', 'Lwinterx/packages/', 'Lorg/apache/sshd/')


def stopped():
    if control.spring_pids():
        raise RuntimeError('Fully quit Spring Launcher first. Core preparation/launch never closes an existing session.')


# Spring versions a core may be built from: the installed 0.8.1, or another version's own APK (run as an overlay).
SPRING_SOURCES = {jailbreak.ORIGINAL_SHA: '0.8.1',
                  'c500d2f7316c36e3f97fb65bda7178445513630d132f711fe80bfc79a7a16cb6': '0.9-preview1'}


def checked_core(directory):
    directory = Path(directory).resolve(strict=True)
    audit = json.loads((directory / 'core-audit.json').read_text())
    manifest = json.loads((directory / 'android-runtime/manifest.json').read_text())
    version = SPRING_SOURCES.get(manifest.get('sourceApkSha256'))
    apk = directory / ('WinterX-core-%s.apk' % version)
    if (version is None or apk.is_symlink() or not apk.is_file() or audit.get('apk_sha256') != jailbreak.digest(apk) or
            audit.get('preinstalled_tweaks') != [] or audit.get('bundled_tweak_classes') != [] or
            manifest.get('runtimeAbi') != ABI or manifest.get('preinstalledTweaks') != []):
        raise ValueError('Build and verify a core-only Spring runtime first')
    with zipfile.ZipFile(apk) as archive:
        defined = []
        for name in archive.namelist():
            if name.startswith('classes') and name.endswith('.dex'):
                defined.extend(dex_classes(archive.read(name)))
        if any(name.startswith(FORBIDDEN) for name in defined):
            raise ValueError('Tweak implementation is bundled in this APK')
        if 'Lwinterx/extension/NativeRuntime;' not in defined or b'winterx/extension/NativeHooks' not in archive.read('classes.dex'):
            raise ValueError('The core native runtime or native bindings are missing')
    return {'core': str(directory), 'apk': str(apk), 'apk_sha256': audit['apk_sha256'], 'runtimeAbi': ABI, 'springVersion': version}


def plan_path(state, version):
    """0.8.1 keeps core-plan.json; other versions get their own, so switching never overwrites the other."""
    return state / ('core-plan.json' if version in (None, '0.8.1') else 'core-plan-%s.json' % version)


def booted_data(since):
    """The Spring data folder whose boot receipt appeared after since (Mac.APK keeps one folder per Spring version)."""
    root = jailbreak.BASE / 'data/data'
    for folder in sorted(root.glob('com.guille.spring_*')):
        receipt = folder / 'files/ruby/boot-ok-v1'
        if receipt.is_file() and not receipt.is_symlink() and receipt.stat().st_mtime >= since: return folder.resolve(), receipt
    return None, None


def atomic_json(path, value):
    if path.is_symlink() or path.exists() and not path.is_file():
        raise ValueError('Unexpected core state path')
    fd, temporary = tempfile.mkstemp(prefix='.core-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as output:
            json.dump(value, output, indent=2); output.write('\n'); output.flush(); os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def prepare(directory):
    stopped(); core = checked_core(directory)
    if jailbreak.digest(jailbreak.ORIGINAL) != jailbreak.ORIGINAL_SHA:
        raise ValueError('Installed Spring must be the original supported 0.8.1 build')
    state = jailbreak.STATE
    if state.is_symlink() or state.exists() and not state.is_dir(): raise ValueError('Unsafe host state directory')
    state.mkdir(parents=True, exist_ok=True)
    with exclusive_lock(state / 'core.lock'):
        data = bundle.data_root(jailbreak.DATA)
        def guard():
            stopped()
            if bundle.data_root(jailbreak.DATA) != data: raise RuntimeError('Spring data-root alias changed')
        guard(); before = inventory(data)
        backup = state / 'backups' / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-before-core')
        control.snapshot_app_data(data, backup)
        for name in ('core-plan.json', 'local-test.json', 'active.json'):
            path = state / name
            if path.is_symlink() or path.exists() and not path.is_file(): raise ValueError('Unsafe existing engine record')
            if path.exists(): (backup / (name + '.before')).write_bytes(path.read_bytes())
        guard()
        if inventory(backup) != before or inventory(data) != before:
            raise RuntimeError('Persisted data changed during backup; core was not selected')
        android_root = overlay.prepare(jailbreak.BASE, state / 'overlay')
        guard()
        if inventory(data) != before: raise RuntimeError('Persisted data changed during preparation')
        plan = {**core, 'format': 'winterx.mac-core/1', 'status': 'prepared', 'data': str(data),
                'androidRoot': str(android_root), 'backup': str(backup), 'preparedAt': datetime.now().isoformat(),
                'preinstalledTweaks': [], 'persistedDataVerified': True}
        atomic_json(plan_path(state, core.get('springVersion')), plan)
        return plan


def launch(timeout=120, version=None):
    stopped()
    state = jailbreak.STATE
    with exclusive_lock(state / 'core.lock'):
        path = plan_path(state, version)
        if path.is_symlink(): raise ValueError('Unsafe core plan')
        plan = json.loads(path.read_text())
        if plan.get('format') != 'winterx.mac-core/1' or plan.get('status') != 'prepared' or plan.get('preinstalledTweaks') != []:
            raise ValueError('Prepare a verified core-only runtime first')
        core = checked_core(plan['core'])
        if any(plan.get(key) != value for key, value in core.items()): raise ValueError('Prepared core changed')
        data = bundle.data_root(jailbreak.DATA)
        if str(data) != plan.get('data') or not Path(plan['backup']).is_dir(): raise ValueError('Prepared data root or backup is missing')
        stopped()
        android_root = overlay.prepare(jailbreak.BASE, state / 'overlay')
        if str(android_root) != plan['androidRoot']: raise ValueError('Prepared overlay changed')
        boot = data / 'files/ruby/boot-ok-v1'
        if boot.resolve() != boot.absolute() or boot.is_symlink() or boot.exists() and not boot.is_file():
            raise ValueError('Unsafe runtime boot receipt')
        stopped(); boot.unlink(missing_ok=True)
        started = time.time() - 1
        child = control.start_overlay(Path(core['apk']), android_root, state / 'core-runtime.log')
        try:
            deadline = time.monotonic() + timeout; observed = None
            while time.monotonic() < deadline:
                if child.poll() is not None: raise RuntimeError('Core exited during startup; see .ruby-state/core-runtime.log')
                if core.get('springVersion', '0.8.1') != '0.8.1':                     # its own data folder, found by its receipt
                    found, receipt = booted_data(started)
                    if found is not None: data, boot = found, receipt
                if boot.is_file() and not boot.is_symlink():
                    if observed is None: observed = time.monotonic()
                    if time.monotonic() - observed >= 3:
                        if (control.spring_pids() != [child.pid] or not control.is_overlay_process(child.pid, core['apk'], android_root)
                                or jailbreak.digest(Path(core['apk'])) != core['apk_sha256']):
                            raise RuntimeError('Fresh boot receipt does not match the sole running core')
                        record = {**core, 'pid': child.pid, 'backup': plan['backup'], 'data': str(data), 'coreOnly': True}
                        atomic_json(state / 'active.json', record)
                        return child, record
                time.sleep(.25)
            raise TimeoutError('Core did not produce a fresh boot receipt')
        except BaseException:
            if child.poll() is None:
                child.terminate()
                try: child.wait(timeout=10)
                except Exception: child.kill(); child.wait(timeout=10)
            raise


def switch(version, timeout=180):
    """The WinterX app's Jailbreak for a modular core: quit Spring, then start the prepared core for version with its
    package bridge in the background, and wait until that core is the one running."""
    import subprocess
    state = jailbreak.STATE
    path = plan_path(state, version)
    if not path.is_file() or path.is_symlink():
        raise ValueError('Prepare the Spring %s core on this Mac first (tools/mac_core.py prepare)' % version)
    active = state / 'active.json'
    try:
        record = json.loads(active.read_text())
        if (record.get('springVersion') == version and control.spring_pids() == [int(record['pid'])] and
                control.is_overlay_process(int(record['pid']), record['apk'], state / 'overlay/android')):
            return {'ok': True, 'message': 'Successfully Jailbroken', 'springVersion': version}
    except (OSError, ValueError, TypeError, KeyError):
        pass
    control.stop_spring()
    started = time.time()
    log = (state / ('core-launch-%s.log' % version)).open('w')
    child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), 'launch', '--bridge', '--spring', version],
                             cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if child.poll() is not None:
            tail = Path(log.name).read_text(errors='replace').strip().splitlines()[-1:] or ['no output']
            raise RuntimeError('Spring %s did not start: %s' % (version, tail[0]))
        try:
            record = json.loads(active.read_text())
            if active.stat().st_mtime >= started and record.get('springVersion') == version:
                return {'ok': True, 'message': 'Successfully Jailbroken', 'springVersion': version}
        except (OSError, ValueError):
            pass
        time.sleep(.5)
    raise TimeoutError('Spring %s did not finish starting' % version)


def serve(child, record):
    from native_bridge import NativeBridge
    from private_files import AccessError, DirectoryFiles
    root = Path(record['data']) / 'files'; store = DirectoryFiles(root)
    apk = Path(record['apk']); pinned_stat = apk.stat()
    def verify():
        current = apk.stat()
        if (child.poll() is not None or control.spring_pids() != [child.pid] or
                not control.is_overlay_process(child.pid, apk, jailbreak.STATE / 'overlay/android') or
                Path(record['data']).resolve() / 'files' != root or
                (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) !=
                (pinned_stat.st_dev, pinned_stat.st_ino, pinned_stat.st_size, pinned_stat.st_mtime_ns)):
            raise AccessError('The verified running Mac.APK core changed')
        return {'phase': 'installed', 'runtimeAbi': ABI, 'coreFilesRoot': str(root),
                'safeMode': (root / 'ruby/safe-mode.enabled').exists()}
    version = record.get('springVersion', '0.8.1')                    # each Spring version keeps its own bridge state
    state = jailbreak.STATE / ('native-code-bridge' if version == '0.8.1' else 'native-code-bridge-' + version)
    bridge = NativeBridge(store, state, verify, builtin=ROOT / 'builtin-repo')
    print('Ruby code-package bridge is ready.', flush=True)
    while child.poll() is None:
        count = bridge.once()
        if count: print('Completed', count, 'Ruby package request(s).', flush=True)
        time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare_command = commands.add_parser('prepare'); prepare_command.add_argument('core', type=Path)
    launch_command = commands.add_parser('launch'); launch_command.add_argument('--bridge', action='store_true')
    launch_command.add_argument('--spring', help='which prepared Spring version to start (default 0.8.1), e.g. 0.9-preview1')
    args = parser.parse_args()
    if args.command == 'prepare':
        plan = prepare(args.core)
        print('Core prepared. Backup:', plan['backup'])
        print('Launch when ready: python3 tools/mac_core.py launch --bridge')
    else:
        child, record = launch(version=args.spring)
        print('Core-only WinterX started for Spring %s. Install tweaks through Ruby.' % record.get('springVersion', '0.8.1'), flush=True)
        if args.bridge:
            try: serve(child, record)
            except KeyboardInterrupt: pass


if __name__ == '__main__': main()
