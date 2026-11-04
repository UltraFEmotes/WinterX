#!/usr/bin/env python3
"""Back up a fully stopped Spring and select the checksum-pinned local test. Never launch it."""
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import tempfile

import launch_local_test as launcher
import local_test_bundle as bundle

ROOT = Path(__file__).resolve().parents[1]
PROTECTED = ('ios4_pages.json', 'ios6_pages.json', 'ios7_pages.json',
             'ruby/icon-positions-v1.json', 'ruby/freeme-slots-v1.json', 'ruby/dockin.capacity')
REGISTRY = 'files/sapps-data/com.ruby.manager/files/package-registry/'
OWNED = {REGISTRY + 'installed.json', REGISTRY + '.lock',
         *( 'files/ruby/' + name.lower() + '.enabled' for name, _ in bundle.BUNDLE)}


def stopped():
    if launcher.control.spring_pids():
        raise RuntimeError('Fully quit Spring Launcher first. Preparation never stops or restarts it.')


def hashes(files):
    result = {}
    for relative in PROTECTED:
        path = files / relative
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError('Unexpected protected data path: ' + relative)
        if path.is_file():
            result[relative] = launcher.jailbreak.digest(path)
    return result


def inventory(data):
    """Record all persisted data, including links without following them."""
    result = {}
    for folder in ('files', 'shared_prefs'):
        for path in (data / folder).rglob('*'):
            relative = path.relative_to(data).as_posix()
            if path.is_symlink():
                result[relative] = 'link:' + os.readlink(path)
            elif path.is_file():
                result[relative] = launcher.jailbreak.digest(path)
    return result


def preserved(before, after):
    for path in before.keys() | after.keys():
        if path in OWNED:
            continue
        if path not in before and path.startswith(REGISTRY + 'art/'):
            continue
        if before.get(path) != after.get(path):
            raise RuntimeError('Persisted data changed outside the three local-test hooks: ' + path)


def prepare(apk):
    stopped()
    apk = Path(apk)
    if apk.is_symlink():
        raise ValueError('The local test APK must not be a symlink.')
    apk = apk.resolve(strict=True)
    if launcher.jailbreak.digest(apk) != launcher.TEST_SHA:
        raise ValueError('The local test APK failed its pinned checksum check.')
    records = bundle.inputs(apk, launcher.jailbreak.digest, launcher.TEST_SHA)
    state, data = launcher.jailbreak.STATE, launcher.jailbreak.DATA
    if state.is_symlink() or not (state / 'overlay/android').is_dir():
        raise ValueError('The prepared Mac.APK overlay is missing or unsafe.')
    plan_path = state / 'local-test.json'
    active_path = state / 'active.json'
    for path in (plan_path, active_path):
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError('Unexpected local-test record path.')
    previous = json.loads(plan_path.read_text()) if plan_path.exists() else None
    bundle.registry_root(data)
    before = hashes(data / 'files')
    persisted_before = inventory(data)
    backup = state / 'backups' / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-before-local-combined')
    stopped()
    launcher.control.snapshot_app_data(data, backup)
    for path in (plan_path, active_path):
        if path.exists():
            shutil.copy2(path, backup / (path.stem + '-before.json'))
    if hashes(backup / 'files') != before or hashes(data / 'files') != before:
        raise RuntimeError('Protected data changed while preparing; the new test was not selected.')
    if inventory(backup) != persisted_before or inventory(data) != persisted_before:
        raise RuntimeError('Persisted data changed during backup; the new test was not selected.')
    stopped()
    bundle.activate(data, records, stopped)
    bundle.verify(data, records)
    persisted_after = inventory(data)
    preserved(persisted_before, persisted_after)
    if hashes(data / 'files') != before:
        raise RuntimeError('Protected data changed; the new test was not selected. No backup was restored.')
    stopped()
    plan = {'status': 'prepared', 'label': 'SnowyHome + DockIn + FreeMe', 'apk': str(apk), 'apk_sha256': launcher.TEST_SHA,
            'backup': str(backup), 'layout_sha256': before, 'previous_test': previous,
            'packages': previous.get('packages', []) if previous else [],
            'prepared_at': datetime.now().isoformat(), 'engine_launched': False,
            'draft_tweaks_installed': True, 'bundled_packages': records,
            'persisted_data_verified': True,
            'safe_mode_preserved': (data / 'files/ruby/safe-mode.enabled').is_file()}
    fd, name = tempfile.mkstemp(prefix='.local-test-', suffix='.tmp', dir=state)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(plan, out, indent=2); out.write('\n'); out.flush(); os.fsync(out.fileno())
        os.replace(name, plan_path)
    finally:
        if os.path.exists(name): os.unlink(name)
    return plan


if __name__ == '__main__':
    plan = prepare(bundle.ENGINE)
    print('Combined local test prepared; SnowyHome, DockIn and FreeMe installed/enabled. Spring was not launched.')
    print('Backup: ' + plan['backup'])
    print('Start it yourself with Start WinterX Local Test.command, not the stock launcher.')
