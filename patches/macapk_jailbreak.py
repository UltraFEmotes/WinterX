"""Experimental Mac.APK jailbreak orchestration; not connected to Ruby yet."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

import macapk_controls as control
import macapk_overlay as overlay
import overlay_flow

WORKSPACE = Path(__file__).resolve().parents[1]
BASE = Path.home() / 'Library/Application Support/MacApk/com.guille.spring'
DATA = BASE / 'data/data/com.guille.spring_0.8.1'
ORIGINAL = control.APP / 'Contents/app/~~m4c4pk0Zx9AbC1dEfGhIjw==/com.guille.spring-Qm4c4pk0Zx9AbC1dEfGh8Q==/base.apk'
LEGACY_PATCHED = WORKSPACE / 'builds/RubySpring-0.8.1-experimental.apk'
SETTINGS_PATCH_SHA = 'e381d877fb3815735e49d329ffb551666091f3951071e435ba7e58c4018aeb4e'
ALPHA1_PATCH_SHA = 'dffc9292e8b5d3dae1519a64ca69267e2e5ea1efb4d53a3c19d6d1baa61654de'
EARLIER_PATCH_SHA = '395170c771edaa43de0815e03bf3badb964cc3e1cc1a36b2ab0d00264adc4b6d'
PREVIOUS_PATCH_SHA = '9c2a9b23ad342590a0c55bdc315748b47e13742a0ba8bd8659de12bc8a7b3b68'
BETA1_PATCH_SHA = '709c168a84730c3477ac6a03de157f37a23c043bcee2df8bf080b08d023b606a'
BETA2_PATCH_SHA = '5cf950290b7b7414e1e51b965b7adb459b93993407cc0a0f6b07a75265495dc1'
BETA3_PATCH_SHA = 'c696229fefc085ee625ca6673ee60a1b35ab32b34f5c06b88172f7a7d0c5fe4d'
BETA4_PATCH_SHA = 'a9a6ac34f07c2ad423a2a456349ccce8ebd49d36243ab57be0c4f1b782a15226'
SETTINGS_PAGE_PATCH_SHA = '09d82a948b4fd8bba87dd9c0cac4764258b85d304e1ca623e204ae77445a5163'
APPEARANCE_BETA_SHA = 'a1eb2e22caf405817879eb7af4e5520e3ffd7eecf63ca469e19984c7e07c01fe'
APPEARANCE_BETA2_SHA = 'd70255d55fd5eefa8adf0aa15d44d854b66ddc4d2ca434f54f38ffb1ae61a67d'
BRIDGELESS_ALPHA2_SHA = 'a52f16a8ec0537a30cbafd4bbc97e5a2f812b91568d27c2c25f08b42882bf4a4'
BRIDGELESS_ALPHA4_SHA = 'f03c4ae6c534337b2e046a8ee004c36caf5ee8f0e409b3d9727fc8031a410cfd'
LOCAL_ALPHA8_SHA = 'e1fc328e5cb794f8d8ebbac713e9cfaba6d7db08af14c5c13345c80137b6c6db'
LOCAL_SNOWY_SHA = '49bf7482544ab22bc528c482c25e5133c1ddef94cff4e5192bc8383abd52bc9f'
PATCHED = WORKSPACE / 'builds/WinterXSpring-0.8.1-native-controls-alpha.apk'
STATE = WORKSPACE / '.ruby-state'
ORIGINAL_SHA = 'f07f980fe681a6de9c4ce8735ae1c0bb0f852f447fbdb925d2dec37cf9778e5c'
LEGACY_PATCH_SHA = '98659eea58cd8d7100528b1985e91fa82bb8d7c2048e14dfd741afae91cd17bd'
PATCH_SHA = '6951e734de54f67c28de8186335c12f767d93054ae04092b9fad4f293ac4c2ab'

# Local builds differ byte-for-byte, so pin the exact file built on this Mac.
_local_build = STATE / 'local-build.json'
if _local_build.is_file():
    record = json.loads(_local_build.read_text())
    candidate = (WORKSPACE / record['apk']).resolve(strict=True)
    if not candidate.is_relative_to((WORKSPACE / 'builds').resolve()) or candidate.suffix != '.apk':
        raise ValueError('Invalid local build path')
    if len(record['sha256']) != 64 or any(c not in '0123456789abcdef' for c in record['sha256']):
        raise ValueError('Invalid local build hash')
    PATCHED, PATCH_SHA = candidate, record['sha256']


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def prepare():
    if (STATE / 'compatibility-pause').exists():
        raise RuntimeError('Jailbreak is paused while the Mac.APK startup crash is investigated')
    if digest(ORIGINAL) != ORIGINAL_SHA:
        raise ValueError('Installed Spring APK is not the supported 0.8.1 build')
    if digest(PATCHED) != PATCH_SHA:
        raise ValueError('Patched APK failed verification')
    pids = control.spring_pids()
    if len(pids) != 1:
        raise ValueError('Exactly one Spring window must be running')
    if not control.is_original_process(pids[0]):
        raise ValueError('Start the original Spring Launcher before jailbreaking')
    root = overlay.prepare(BASE, STATE / 'overlay')
    return root


def run():
    # A second tap or a bridge restart can leave multiple requests queued. If
    # the verified current overlay is already running, do not respring it again.
    active_path = STATE / 'active.json'
    if active_path.is_file():
        try:
            active = json.loads(active_path.read_text())
            pid = int(active['pid'])
            if (active.get('apk_sha256') == PATCH_SHA and digest(PATCHED) == PATCH_SHA and
                    Path(active.get('apk', '')).resolve() == PATCHED.resolve() and
                    control.spring_pids() == [pid] and
                    control.is_overlay_process(pid, PATCHED, STATE / 'overlay/android')):
                return {'ok': True, 'message': 'Successfully Jailbroken'}
        except (OSError, ValueError, TypeError, KeyError):
            pass
    root = prepare()
    child = None
    marker = DATA / 'files/ruby/boot-ok-v1'
    snapshot = STATE / 'backups' / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-' + str(os.getpid()))

    def start_patched():
        nonlocal child
        child = control.start_overlay(PATCHED, root, STATE / 'runtime.log')

    def healthy():
        return child is not None and child.poll() is None

    def stop_patched():
        # The child may fail before it registers a macOS application window;
        # always stop and reap this exact process before restarting the stock app.
        if child is None or child.poll() is not None:
            return
        child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=10)

    result = overlay_flow.run(marker, control.stop_spring, start_patched, stop_patched,
                              control.start_original, healthy=healthy,
                              before_start=lambda: control.snapshot_app_data(DATA, snapshot),
                              timeout=120, stability=3)
    result['backup'] = str(snapshot)
    if result['ok']:
        active = STATE / 'active.json'
        active.parent.mkdir(parents=True, exist_ok=True)
        tmp = active.with_suffix('.tmp')
        tmp.write_text(json.dumps({'pid': child.pid, 'apk_sha256': PATCH_SHA, 'apk': str(PATCHED), 'backup': str(snapshot)}))
        os.replace(tmp, active)
    return result


def upgrade_overlay(new_apk, new_sha):
    """Replace the running overlay by launching another verified APK, with fallback."""
    active_path = STATE / 'active.json'
    active = json.loads(active_path.read_text())
    old_apk = Path(active.get('apk', str(LEGACY_PATCHED)))
    new_apk = Path(new_apk).resolve(strict=True)
    root = STATE / 'overlay/android'
    old_pid = int(active['pid'])
    if (digest(old_apk) != active['apk_sha256'] or digest(new_apk) != new_sha or
            control.spring_pids() != [old_pid] or not control.is_overlay_process(old_pid, old_apk, root)):
        raise ValueError('The running Ruby overlay or APK verification did not match')
    snapshot = STATE / 'backups' / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-' + str(os.getpid()))
    marker = DATA / 'files/ruby/boot-ok-v1'
    child = None

    def start_new():
        nonlocal child
        child = control.start_overlay(new_apk, root, STATE / 'runtime.log')

    def healthy():
        return child is not None and child.poll() is None

    def stop_child():
        if child is None or child.poll() is not None:
            return
        child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=10)

    def write_active(apk, sha):
        active.update(pid=child.pid, apk=str(apk), apk_sha256=sha, backup=str(snapshot))
        temp = active_path.with_suffix('.tmp')
        temp.write_text(json.dumps(active))
        os.replace(temp, active_path)

    def restore_old():
        nonlocal child
        child = control.start_overlay(old_apk, root, STATE / 'runtime.log')
        write_active(old_apk, active['apk_sha256'])

    result = overlay_flow.run(marker, control.stop_spring, start_new, stop_child, restore_old,
                              healthy=healthy, before_start=lambda: control.snapshot_app_data(DATA, snapshot),
                              timeout=120, stability=3, success_message='Ruby patch updated',
                              fallback_name='previous Ruby session')
    if result['ok']:
        write_active(new_apk, new_sha)
    return result


def enable_settings_test():
    """Enable the Settings test in an already verified overlay and respring it."""
    active_path = STATE / 'active.json'
    active = json.loads(active_path.read_text())
    pid = int(active['pid'])
    root = STATE / 'overlay/android'
    active_apk = Path(active.get('apk', str(LEGACY_PATCHED)))
    active_sha = active.get('apk_sha256')
    if (active_sha not in (PATCH_SHA, LOCAL_ALPHA8_SHA, LOCAL_SNOWY_SHA, BRIDGELESS_ALPHA4_SHA, BRIDGELESS_ALPHA2_SHA, APPEARANCE_BETA2_SHA, SETTINGS_PAGE_PATCH_SHA, BETA4_PATCH_SHA, BETA3_PATCH_SHA, BETA2_PATCH_SHA, BETA1_PATCH_SHA, PREVIOUS_PATCH_SHA, EARLIER_PATCH_SHA, ALPHA1_PATCH_SHA, SETTINGS_PATCH_SHA, LEGACY_PATCH_SHA) or digest(active_apk) != active_sha or
            control.spring_pids() != [pid] or not control.is_overlay_process(pid, active_apk, root)):
        raise ValueError('The verified Ruby-patched Spring must be running first')
    setting = DATA / 'files/ruby/settings-test.enabled'
    if setting.is_symlink() or (setting.exists() and not setting.is_file()):
        raise ValueError('Unexpected Settings tweak marker')
    if setting.is_file():
        return {'ok': True, 'message': 'Settings test is already enabled'}
    boot_marker = DATA / 'files/ruby/boot-ok-v1'
    snapshot = STATE / 'backups' / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-' + str(os.getpid()))
    child = None

    def backup_and_enable():
        control.snapshot_app_data(DATA, snapshot)
        setting.parent.mkdir(parents=True, exist_ok=True)
        setting.touch(exist_ok=False)

    def start_patched():
        nonlocal child
        child = control.start_overlay(active_apk, root, STATE / 'runtime.log')

    def healthy():
        return child is not None and child.poll() is None

    def stop_patched():
        if child is None or child.poll() is not None:
            return
        child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=10)

    def restore_previous_overlay():
        setting.unlink(missing_ok=True)
        start_patched()
        # Live status uses the actual replacement PID after recovery.
        active['pid'] = child.pid
        temp = active_path.with_suffix('.tmp')
        temp.write_text(json.dumps(active))
        os.replace(temp, active_path)

    result = overlay_flow.run(boot_marker, control.stop_spring, start_patched, stop_patched,
                              restore_previous_overlay, healthy=healthy, before_start=backup_and_enable,
                              timeout=120, stability=3, success_message='Settings test installed',
                              fallback_name='previous Ruby session')
    if result['ok']:
        active['pid'] = child.pid
        temp = active_path.with_suffix('.tmp')
        temp.write_text(json.dumps(active))
        os.replace(temp, active_path)
    return result
