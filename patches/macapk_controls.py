"""Mac.APK process controls for a single Spring window and a separate overlay.

These functions are not wired to the Ruby bridge yet. They must be exercised
on an isolated installation before they are allowed to control the user's app.
"""
from pathlib import Path
import ctypes
import ctypes.util
import os
import shutil
import subprocess
import time

BUNDLE_ID = 'org.macapk.app.com.guille.spring-0.8.1'
APP = Path('/Applications/Spring-Launcher.app')
RUNTIME = APP / 'Contents/MacOS/.Spring Launcher'


def spring_pids():
    # The original launcher and the direct overlay use different bundle IDs.
    # Inspect the exact runtime executable instead of guessing from the bundle.
    result = subprocess.run(['ps', '-ax', '-o', 'pid=,args='], capture_output=True, text=True, check=True)
    pids = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and parts[1].startswith(str(RUNTIME) + ' --apk ') and '--android-root ' in parts[1]:
            pids.append(int(parts[0]))
    return sorted(pids)


def is_original_process(pid):
    result = subprocess.run(['ps', '-p', str(pid), '-o', 'args='], capture_output=True, text=True, check=True)
    command = result.stdout.strip()
    original_root = str(APP / 'Contents/android')
    return '--android-root ' + original_root in command and '--apk ' + original_root + '/data/app/' in command


def is_overlay_process(pid, apk, android_root):
    result = subprocess.run(['ps', '-p', str(pid), '-o', 'args='], capture_output=True, text=True)
    if result.returncode:
        return False
    command = result.stdout.strip()
    return ('--apk ' + str(Path(apk).resolve()) in command and
            '--android-root ' + str(Path(android_root).resolve()) in command)


def stop_spring():
    pids = spring_pids()
    if len(pids) > 1:
        raise RuntimeError('More than one Spring window is running; refusing to choose')
    if not pids:
        return
    # Call NSRunningApplication directly. Compiling an AppKit Swift script on
    # every respring can take minutes when the developer toolchain cache is cold.
    request_quit(pids[0])
    end = time.monotonic() + 15
    while time.monotonic() < end:
        if not spring_pids():
            return
        time.sleep(.25)
    raise TimeoutError('Spring did not close; the APK was not changed')


def request_quit(pid):
    """Send the normal macOS quit event to exactly one process."""
    ctypes.CDLL('/System/Library/Frameworks/AppKit.framework/AppKit')
    objc = ctypes.CDLL(ctypes.util.find_library('objc'))
    objc.objc_getClass.argtypes = [ctypes.c_char_p]
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    send_class = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int)(('objc_msgSend', objc))
    send_bool = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(('objc_msgSend', objc))
    cls = objc.objc_getClass(b'NSRunningApplication')
    selector = objc.sel_registerName(b'runningApplicationWithProcessIdentifier:')
    app = send_class(cls, selector, pid)
    if not app:
        if pid in spring_pids():
            raise RuntimeError('Could not find the running Spring application')
        return
    if not send_bool(app, objc.sel_registerName(b'terminate')) and pid in spring_pids():
        raise RuntimeError('macOS refused to close Spring normally')


def snapshot_app_data(data, backup):
    data, backup = Path(data).resolve(strict=True), Path(backup)
    if backup.exists():
        raise ValueError('Backup already exists; refusing to overwrite it')
    backup.mkdir(parents=True, mode=0o700)
    # Spring is stopped before this callback. Do not include regenerable caches.
    for name in ('files', 'shared_prefs'):
        source = data / name
        if source.is_dir():
            shutil.copytree(source, backup / name, symlinks=True)
    return backup


def start_overlay(apk, android_root, log_path):
    if spring_pids():
        raise RuntimeError('Spring is still running; refusing simultaneous access to its data')
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('ab') as log:
        os.chmod(log_path, 0o600)
        return subprocess.Popen([str(RUNTIME), '--apk', str(Path(apk).resolve(strict=True)),
                                 '--android-root', str(Path(android_root).resolve(strict=True))],
                                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True)


def start_original():
    if spring_pids():
        raise RuntimeError('A Spring process is still running; refusing to start another')
    subprocess.run(['open', '-a', str(APP)], check=True)
