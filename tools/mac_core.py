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


def checked_core(directory):
    directory = Path(directory).resolve(strict=True)
    audit = json.loads((directory / 'core-audit.json').read_text())
    manifest = json.loads((directory / 'android-runtime/manifest.json').read_text())
    apk = directory / 'WinterX-core-0.8.1.apk'
    if (apk.is_symlink() or audit.get('apk_sha256') != jailbreak.digest(apk) or
            audit.get('preinstalled_tweaks') != [] or audit.get('bundled_tweak_classes') != [] or
            manifest.get('runtimeAbi') != ABI or manifest.get('sourceApkSha256') != jailbreak.ORIGINAL_SHA or
            manifest.get('preinstalledTweaks') != []):
        raise ValueError('Build and verify a core-only Spring 0.8.1 runtime first')
    with zipfile.ZipFile(apk) as archive:
        defined = []
        for name in archive.namelist():
            if name.startswith('classes') and name.endswith('.dex'):
                defined.extend(dex_classes(archive.read(name)))
        if any(name.startswith(FORBIDDEN) for name in defined):
            raise ValueError('Tweak implementation is bundled in this APK')
        if 'Lwinterx/extension/NativeRuntime;' not in defined or b'winterx/extension/NativeHooks' not in archive.read('classes.dex'):
            raise ValueError('The core native runtime or native bindings are missing')
    return {'core': str(directory), 'apk': str(apk), 'apk_sha256': audit['apk_sha256'], 'runtimeAbi': ABI}


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
        atomic_json(state / 'core-plan.json', plan)
        return plan


def launch(timeout=120):
    stopped()
    state = jailbreak.STATE
    with exclusive_lock(state / 'core.lock'):
        path = state / 'core-plan.json'
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
        child = control.start_overlay(Path(core['apk']), android_root, state / 'core-runtime.log')
        try:
            deadline = time.monotonic() + timeout; observed = None
            while time.monotonic() < deadline:
                if child.poll() is not None: raise RuntimeError('Core exited during startup; see .ruby-state/core-runtime.log')
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


def serve(child, record):
    from native_bridge import NativeBridge
    from private_files import AccessError, DirectoryFiles
    root = Path(record['data']) / 'files'; store = DirectoryFiles(root)
    apk = Path(record['apk']); pinned_stat = apk.stat()
    def verify():
        current = apk.stat()
        if (child.poll() is not None or control.spring_pids() != [child.pid] or
                not control.is_overlay_process(child.pid, apk, jailbreak.STATE / 'overlay/android') or
                bundle.data_root(jailbreak.DATA) / 'files' != root or
                (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) !=
                (pinned_stat.st_dev, pinned_stat.st_ino, pinned_stat.st_size, pinned_stat.st_mtime_ns)):
            raise AccessError('The verified running Mac.APK core changed')
        return {'phase': 'installed', 'runtimeAbi': ABI, 'coreFilesRoot': str(root),
                'safeMode': (root / 'ruby/safe-mode.enabled').exists()}
    bridge = NativeBridge(store, jailbreak.STATE / 'native-code-bridge', verify, builtin=ROOT / 'builtin-repo')
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
    args = parser.parse_args()
    if args.command == 'prepare':
        plan = prepare(args.core)
        print('Core prepared. Backup:', plan['backup'])
        print('Launch when ready: python3 tools/mac_core.py launch --bridge')
    else:
        child, record = launch()
        print('Core-only WinterX started for Spring 0.8.1. Install tweaks through Ruby.', flush=True)
        if args.bridge:
            try: serve(child, record)
            except KeyboardInterrupt: pass


if __name__ == '__main__': main()
