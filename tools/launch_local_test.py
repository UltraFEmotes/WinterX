#!/usr/bin/env python3
"""Launch the prepared local test only from a fully stopped Spring session."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'patches'))
import macapk_controls as control
import macapk_jailbreak as jailbreak

TEST_SHA = '6bdbd8e566b6ad436cb73d57330be17f360ea3832e5b70bba5cc221822604157'


def verify(plan):
    if control.spring_pids():
        raise RuntimeError('Fully quit Spring Launcher first. This command never stops or resprings it.')
    if plan.get('status') != 'prepared' or plan.get('apk_sha256') != TEST_SHA:
        raise ValueError('The local test has not been prepared and verified.')
    apk = Path(plan['apk']).resolve(strict=True)
    if jailbreak.digest(apk) != TEST_SHA:
        raise ValueError('The local test APK failed its checksum check.')
    if not Path(plan['backup']).is_dir():
        raise ValueError('The stopped-session backup is missing.')
    return apk


def launch(plan, timeout=120):
    apk = verify(plan)
    root = jailbreak.STATE / 'overlay/android'
    if not root.is_dir():
        raise ValueError('The prepared Mac.APK overlay is missing.')
    boot = jailbreak.DATA / 'files/ruby/boot-ok-v1'
    if boot.is_symlink() or (boot.exists() and not boot.is_file()):
        raise ValueError('Unexpected boot receipt path.')
    # No stock launcher is started, and no in-place restart/fallback is attempted.
    boot.unlink(missing_ok=True)
    child = control.start_overlay(apk, root, jailbreak.STATE / 'local-test-runtime.log')
    try:
        end = time.monotonic() + timeout
        receipt_at = None
        while time.monotonic() < end:
            if child.poll() is not None:
                raise RuntimeError('The test engine exited during startup. See .ruby-state/local-test-runtime.log.')
            if boot.is_file() and not boot.is_symlink():
                if receipt_at is None:
                    receipt_at = time.monotonic()
                if time.monotonic() - receipt_at >= 3:
                    record = {'pid': child.pid, 'apk': str(apk), 'apk_sha256': TEST_SHA,
                              'backup': plan['backup'], 'localTest': True}
                    active = jailbreak.STATE / 'active.json'
                    temp = active.with_suffix('.tmp')
                    temp.write_text(json.dumps(record), encoding='utf-8')
                    os.replace(temp, active)
                    return record
            time.sleep(.25)
        raise TimeoutError('The test engine did not produce a fresh startup receipt.')
    except BaseException:
        # Only clean up this command's own failed child. Never launch another engine.
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=10)
        raise


def main():
    plan = json.loads((jailbreak.STATE / 'local-test.json').read_text(encoding='utf-8'))
    record = launch(plan)
    print('Local alpha6 engine started. Unlock Spring and open Settings.')
    print('Try ColoredBar, Animaper, then Code Tweak Example → Run My Code.')
    print('Saved-layout backup: ' + record['backup'])
    print('For Ruby package operations, start the Ruby bridge separately.')


if __name__ == '__main__':
    try:
        main()
    except Exception as failure:
        print('Local test was not started: ' + str(failure), file=sys.stderr)
        sys.exit(1)
