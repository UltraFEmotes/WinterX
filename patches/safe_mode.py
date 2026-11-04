"""Reversible Safe Mode respring for a verified WinterX overlay."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

import macapk_controls as control
import overlay_flow


def verified_session(state, patched, expected_sha):
    """Require the configured WinterX overlay to be the only running Spring process."""
    state, patched = Path(state), Path(patched).resolve(strict=True)
    active = json.loads((state / 'active.json').read_text(encoding='utf-8'))
    pid = int(active['pid'])
    root = state / 'overlay/android'
    actual_sha = hashlib.sha256(patched.read_bytes()).hexdigest()
    if (actual_sha != expected_sha or active.get('apk_sha256') != expected_sha or
            Path(active.get('apk', '')).resolve() != patched or
            control.spring_pids() != [pid] or not control.is_overlay_process(pid, patched, root)):
        raise ValueError('The Safe Mode-compatible WinterX session must be running')
    return active


def set_live_animaper(data, state, patched, expected_sha, enabled):
    """Apply Animaper's live-read flag without recreating Spring's activity."""
    return set_live_tweak(data, state, patched, expected_sha, enabled, 'animaper.enabled', 'Animaper')


def set_live_tweak(data, state, patched, expected_sha, enabled, marker_name, label):
    """Enable only known live-read built-ins; never restart a Spring activity."""
    if marker_name not in ('animaper.enabled', 'coloredbar.enabled', 'freeme.enabled'):
        raise ValueError('Unsupported live tweak marker')
    if not isinstance(enabled, bool):
        raise ValueError(label + ' state must be a boolean')
    verified_session(state, patched, expected_sha)
    folder = Path(data) / 'files/ruby'
    if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
        raise ValueError('Unexpected WinterX data directory')
    folder.mkdir(parents=True, exist_ok=True)
    marker = folder / marker_name
    if marker.is_symlink() or (marker.exists() and not marker.is_file()):
        raise ValueError('Unexpected ' + label + ' marker')
    if enabled:
        marker.touch(exist_ok=True)
    else:
        marker.unlink(missing_ok=True)
    return {'ok': True, 'message': label + ' ' + ('enabled' if enabled else 'disabled')}


def set_marker_and_respring(data, state, patched, expected_sha, enabled, marker_name, label):
    data, state, patched = Path(data), Path(state), Path(patched).resolve(strict=True)
    active = verified_session(state, patched, expected_sha)
    active_path = state / 'active.json'
    root = state / 'overlay/android'
    if marker_name not in ('safe-mode.enabled', 'settings-test.enabled', 'ui-colors.enabled', 'free-icons.enabled', 'animaper.enabled'):
        raise ValueError('Unsupported tweak marker')
    marker = data / 'files/ruby' / marker_name
    boot = data / 'files/ruby/boot-ok-v1'
    if marker.is_symlink() or (marker.exists() and not marker.is_file()):
        raise ValueError('Unexpected tweak marker')
    old = marker.is_file()
    if old == enabled:
        return {'ok': True, 'message': label + ' is already ' + ('on' if old else 'off')}
    snapshot = state / 'backups' / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-safe-' + str(os.getpid()))
    child = None

    def set_marker(value):
        if value:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.touch(exist_ok=True)
        else:
            marker.unlink(missing_ok=True)

    def change():
        control.snapshot_app_data(data, snapshot)
        set_marker(enabled)

    def start():
        nonlocal child
        child = control.start_overlay(patched, root, state / 'runtime.log')

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

    def save_active():
        active['pid'] = child.pid
        temp = active_path.with_suffix('.tmp')
        temp.write_text(json.dumps(active), encoding='utf-8')
        os.replace(temp, active_path)

    def restore():
        set_marker(old)
        start()
        save_active()

    result = overlay_flow.run(boot, control.stop_spring, start, stop_child, restore,
                              healthy=healthy, before_start=change, timeout=120, stability=3,
                              success_message=label + (' enabled' if enabled else ' disabled'),
                              fallback_name='previous WinterX session')
    if result['ok']:
        save_active()
    return result


def set_safe_mode(data, state, patched, expected_sha, enabled):
    result = set_marker_and_respring(data, state, patched, expected_sha, enabled,
                                     'safe-mode.enabled', 'Safe Mode')
    result['safeMode'] = (data / 'files/ruby/safe-mode.enabled').is_file()
    return result
