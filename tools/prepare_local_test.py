#!/usr/bin/env python3
"""Back up a fully stopped Spring and select the checksum-pinned local test. Never launch it."""
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import tempfile

import launch_local_test as launcher

ROOT = Path(__file__).resolve().parents[1]
PROTECTED = ('ios4_pages.json', 'ios6_pages.json', 'ios7_pages.json',
             'ruby/icon-positions-v1.json', 'ruby/freeme-slots-v1.json', 'ruby/dockin.capacity')


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


def prepare(apk):
    stopped()
    apk = Path(apk)
    if apk.is_symlink():
        raise ValueError('The local test APK must not be a symlink.')
    apk = apk.resolve(strict=True)
    if launcher.jailbreak.digest(apk) != launcher.TEST_SHA:
        raise ValueError('The local test APK failed its pinned checksum check.')
    state, data = launcher.jailbreak.STATE, launcher.jailbreak.DATA
    if state.is_symlink() or not (state / 'overlay/android').is_dir():
        raise ValueError('The prepared Mac.APK overlay is missing or unsafe.')
    plan_path = state / 'local-test.json'
    active_path = state / 'active.json'
    for path in (plan_path, active_path):
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError('Unexpected local-test record path.')
    previous = json.loads(plan_path.read_text()) if plan_path.exists() else None
    before = hashes(data / 'files')
    backup = state / 'backups' / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-before-local-alpha8')
    stopped()
    launcher.control.snapshot_app_data(data, backup)
    for path in (plan_path, active_path):
        if path.exists():
            shutil.copy2(path, backup / (path.stem + '-before.json'))
    if hashes(backup / 'files') != before or hashes(data / 'files') != before:
        raise RuntimeError('Protected data changed while preparing; the new test was not selected.')
    stopped()
    plan = {'status': 'prepared', 'label': 'alpha8', 'apk': str(apk), 'apk_sha256': launcher.TEST_SHA,
            'backup': str(backup), 'layout_sha256': before, 'previous_test': previous,
            'packages': previous.get('packages', []) if previous else [],
            'prepared_at': datetime.now().isoformat(), 'engine_launched': False,
            'draft_tweaks_installed': False}
    fd, name = tempfile.mkstemp(prefix='.local-test-', suffix='.tmp', dir=state)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(plan, out, indent=2); out.write('\n'); out.flush(); os.fsync(out.fileno())
        os.replace(name, plan_path)
    finally:
        if os.path.exists(name): os.unlink(name)
    return plan


if __name__ == '__main__':
    plan = prepare(ROOT / 'builds/WinterXSpring-0.8.1-layout-alpha8-local.apk')
    print('Local alpha8 prepared; Spring was not launched and no packages were installed.')
    print('Backup: ' + plan['backup'])
    print('Start it yourself with Start WinterX Local Test.command, not the stock launcher.')
