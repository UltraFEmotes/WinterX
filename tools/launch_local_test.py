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
import local_test_bundle as bundle

TEST_SHA = bundle.ENGINE_SHA


def verify(plan):
    if control.spring_pids():
        raise RuntimeError('Fully quit Spring Launcher first. This command never stops or resprings it.')
    expected_sha = plan.get('apk_sha256')
    if plan.get('status') != 'prepared' or expected_sha not in (TEST_SHA, bundle.UI_FIX_SHA, bundle.FETCH_SHA):
        raise ValueError('The local test has not been prepared and verified.')
    apk = Path(plan['apk']).resolve(strict=True)
    if jailbreak.digest(apk) != expected_sha:
        raise ValueError('The local test APK failed its checksum check.')
    if not Path(plan['backup']).is_dir():
        raise ValueError('The stopped-session backup is missing.')
    bundle.verify(jailbreak.DATA, plan.get('bundled_packages'))
    return apk


def launch(plan, timeout=120):
    apk = verify(plan)
    expected_sha = plan['apk_sha256']
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
                    if (control.spring_pids() != [child.pid] or
                            not control.is_overlay_process(child.pid, apk, root) or
                            jailbreak.digest(apk) != expected_sha):
                        raise RuntimeError('The startup receipt does not match the only running test engine.')
                    record = {'pid': child.pid, 'apk': str(apk), 'apk_sha256': expected_sha,
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
    print(bundle.LABEL + ' experimental engine started.')
    print('Unlock Spring and open Settings for the five installed tweaks.')
    print('SnowyHome import/home APIs are included. SSH remains stopped until explicit Settings Start.')
    if record['apk_sha256'] == bundle.FETCH_SHA:
        print('Built-in neofetch / winterx-info is included; configure your public key and Start SSH before using it.')
    print('Message+ photo settings are included; video sending/reactions remain unavailable.')
    print('Try ColoredBar, Animaper, then Code Tweak Example → Run My Code.')
    print('Saved-layout backup: ' + record['backup'])
    print('For Ruby package operations, start the Ruby bridge separately.')
    print('These are local development packages, not working-catalogue releases.')


if __name__ == '__main__':
    try:
        main()
    except Exception as failure:
        print('Local test was not started: ' + str(failure), file=sys.stderr)
        sys.exit(1)
