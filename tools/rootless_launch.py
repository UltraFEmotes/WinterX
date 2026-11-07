#!/usr/bin/env python3
"""WinterX on Android without root: a patched copy of your own Spring, installed beside the original.

Without root nothing can get into the Spring you already have, so this builds "Spring Launcher (WinterX)" from your
own Spring APK, with WinterX's core built in, under its own app ID (com.winterx.spring). The original Spring stays
installed and untouched. The copy is signed with your own key (kept in ~/.winterx/android/; back it up, since updates
must be signed with the same key) and is debuggable, so this computer can reach its files over USB without root.

    python3 tools/rootless_launch.py start                 build (once per Spring/WinterX version), install, open
    python3 tools/rootless_launch.py bridge                serve Ruby's source refreshes while you use it
    python3 tools/rootless_launch.py safe-mode on|off      recovery, if a tweak keeps it from starting
    python3 tools/rootless_launch.py backup FILE.tar       the copy's data (layouts, apps, tweaks)

Needs adb (USB debugging on), a JDK, apktool and the Android build-tools (see docs/making-tweaks.md). Works for Spring
0.8.1 and 0.9 Preview 1 from just the phone's own Spring. Docs: docs/rootless-android.md.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import toolchain
from rooted_launch import Device, WORK
from android_runtime import SOURCES, SOURCE_SHA

ORIGINAL = 'com.guille.spring'
CLONE = 'com.winterx.spring'
ACTIVITY = CLONE + '/com.guille.spring.LauncherActivity'
VERSION_NAMES = {'0.8.1': '0.8.1', '0.9': '0.9-preview1'}
KEYS = WORK / 'winterx-signing.jks'
PASSWORD = WORK / 'winterx-signing.pass'


def sha(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''): digest.update(block)
    return digest.hexdigest()


def run(*command, **kwargs):
    return subprocess.run([str(c) for c in command], check=True, **kwargs)


def core_version():
    """Changes whenever WinterX's runtime or patches change, so a new WinterX rebuilds the copy."""
    digest = hashlib.sha256()
    for folder in ('extensions/runtime/src', 'patches', 'tools/spring-maps'):
        for path in sorted((ROOT / folder).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts: digest.update(path.relative_to(ROOT).as_posix().encode()); digest.update(path.read_bytes())
    for name in ('extensions/build.py', 'extensions/generate.py', 'extensions/method_hooks.py', 'tools/axml.py'):
        digest.update((ROOT / name).read_bytes())
    return digest.hexdigest()[:16]


def ensure_key():
    """The user's own signing key, created once. The copy can only be updated with the same key."""
    if KEYS.is_file() and PASSWORD.is_file(): return
    WORK.mkdir(parents=True, exist_ok=True)
    password = secrets.token_urlsafe(24)
    PASSWORD.write_text(password + '\n'); os.chmod(PASSWORD, 0o600)
    run(toolchain.jdk_tool('keytool'), '-genkeypair', '-keystore', KEYS, '-storepass', password, '-alias', 'winterx',
        '-keyalg', 'RSA', '-keysize', '3072', '-validity', '10000', '-dname', 'CN=WinterX rootless (this computer)',
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.chmod(KEYS, 0o600)
    print('Created your signing key in %s. Back up that folder: updates to the copy need the same key.' % WORK)


def pull_spring(device, dest):
    """The installed Spring APK, unchanged (no root needed to read an app's APK)."""
    paths = [line.split(':', 1)[1] for line in device.shell('pm path ' + ORIGINAL, check=False).splitlines() if line.startswith('package:')]
    if not paths: raise SystemExit('Install Spring on the phone first; WinterX builds its copy from it.')
    if len(paths) != 1: raise SystemExit('This Spring is installed as split APKs, which WinterX does not support.')
    device.run('pull', paths[0], str(dest))
    version = SOURCES.get(sha(dest))
    if version is None: raise SystemExit('This Spring version is not supported (WinterX supports 0.8.1 and 0.9 Preview 1).')
    return VERSION_NAMES[version]


def build(device, base_apk=None):
    """Build (or reuse) the copy for the installed Spring and this WinterX. Returns its path."""
    cache = WORK / 'rootless'; cache.mkdir(parents=True, exist_ok=True)
    apk = cache / 'spring.apk'
    version = pull_spring(device, apk)
    stamp = '%s-%s' % (version, core_version())
    output = cache / ('Spring-WinterX-%s.apk' % stamp)
    if output.is_file(): print('Your WinterX copy for Spring %s is up to date.' % version); return output, version
    print('Building WinterX into a copy of Spring %s (a few minutes the first time)…' % version)
    cores = cache / 'cores'; cores.mkdir(exist_ok=True)
    base = cores / ('0.8.1-' + core_version())
    builder = [sys.executable, ROOT / 'extensions/build.py']
    if version == '0.8.1':
        if not base.is_dir(): run(*builder, 'runtime', apk, base)
        core = base
    else:
        # WinterX's runtime for this version ships ready-made (extensions/prebuilt); a 0.8.1 APK is only needed when
        # it's missing or out of date (a development checkout).
        if base_apk and not base.is_dir():
            if sha(base_apk) != SOURCE_SHA: raise SystemExit('--base-apk must be the Spring 0.8.1 APK.')
            run(*builder, 'runtime', base_apk, base)
        core = cores / ('%s-%s' % (version, core_version()))
        if not core.is_dir():
            if base.is_dir(): run(*builder, 'runtime', apk, core, '--base', base)
            else:
                sys.path.insert(0, str(ROOT / 'extensions'))
                import build as core_build
                if core_build.prebuilt_runtime(core_build.VERSIONS[sha(apk)]) is None:
                    raise SystemExit('This checkout has no current prebuilt runtime for Spring %s. Pass --base-apk with a '
                                     'Spring 0.8.1 APK to build it.' % version)
                run(*builder, 'runtime', apk, core)
    ensure_key()
    run(*builder, 'clone', core, output, '--package', CLONE, '--keystore', KEYS, '--password-file', PASSWORD, stdout=subprocess.DEVNULL)
    print('Built', output.name)
    return output, version


def install(device, apk):
    installed = device.shell('pm path ' + CLONE, check=False).startswith('package:')
    print('Updating' if installed else 'Installing', 'Spring Launcher (WinterX) beside your original Spring…')
    result = device.run('install', '-r', str(apk), check=False)
    if result.returncode != 0 or 'Success' not in result.stdout:
        message = (result.stdout + result.stderr).strip().splitlines()[-1:] or ['unknown error']
        if 'INSTALL_FAILED_UPDATE_INCOMPATIBLE' in message[0]:
            raise SystemExit('Your WinterX copy was signed with a different key. Restore %s from your backup, or uninstall '
                             'Spring Launcher (WinterX) to start fresh.' % WORK)
        raise SystemExit('Install failed: ' + message[0])
    # Ruby and the WinterX app arrive through the copy's own sapps inbox, as on other installs.
    inbox = '/sdcard/Android/data/%s/files/sapps-inbox' % CLONE
    device.shell('mkdir -p ' + inbox, check=False)
    for name in ('Ruby.sapp', 'WinterX.sapp'):
        if (ROOT / name).is_file():
            device.run('push', str(ROOT / name), inbox + '/.' + name + '.pending')
            device.shell('mv %s/.%s.pending %s/%s' % (inbox, name, inbox, name), check=False)


def open_copy(device, first):
    device.run('shell', 'am', 'start', '-n', ACTIVITY, check=False)
    if first:
        print('\nOn the phone: sign in to Spring, then make "Spring Launcher (WinterX)" your Home app.')
        device.run('shell', 'am', 'start', '-a', 'android.settings.HOME_SETTINGS', check=False)
        print('(Home app settings are open; choose Spring Launcher (WinterX). Your original Spring is still there.)')


def files(device):
    from private_files import AdbFiles
    return AdbFiles(device.serial, '/data/user/0/%s/files' % CLONE, access='run-as', adb=device.adb)


def capabilities(store):
    raw = store.read('ruby/capabilities-v1.json', 65536)
    return json.loads(raw) if raw else {}


def bridge(device):
    """Ruby's computer side (source refreshes, live status), over adb run-as instead of root."""
    from native_bridge import NativeBridge
    store = files(device)
    def verify():
        if not device.shell('pidof ' + CLONE, check=False): raise SystemExit('Spring Launcher (WinterX) stopped.')
        found = capabilities(store)
        if found.get('install') != 'rootless' or found.get('nativeApi') != 'winterx-native-hooks-v1':
            raise SystemExit('This copy is not running a rootless WinterX core.')
        return {'phase': 'installed', 'runtimeAbi': 'winterx-native-hooks-v1', 'coreFilesRoot': store.root}
    state = WORK / 'rootless' / ('bridge-' + device.serial.replace(':', '_'))
    native = NativeBridge(store, state, verify, builtin=ROOT / 'builtin-repo')
    print('Ruby bridge is ready (Ctrl-C to stop).', flush=True)
    while True:
        if native.once(): print('Completed a Ruby request.', flush=True)
        time.sleep(1)


def safe_mode(device, on):
    marker = 'ruby/safe-mode.enabled'
    command = ('touch files/' + marker) if on else ('rm -f files/' + marker)
    device.run('shell', 'run-as', CLONE, 'sh', '-c', command)
    device.run('shell', 'am', 'force-stop', CLONE, check=False)
    print('Safe Mode is %s. Open Spring Launcher (WinterX) again.' % ('on: tweaks will not load' if on else 'off'))


def backup(device, output):
    with open(output, 'wb') as out:
        result = subprocess.run([device.adb, '-s', device.serial, 'exec-out', 'run-as', CLONE, 'tar', '-cf', '-', '.'],
                                stdout=out, stdin=subprocess.DEVNULL)
    if result.returncode: raise SystemExit('Backup failed')
    print('Saved the copy\'s data to', output)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--serial', default=os.environ.get('WINTERX_SERIAL'))
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('start', 'build'):
        command = sub.add_parser(name); command.add_argument('--base-apk', type=Path, help='a Spring 0.8.1 APK (for 0.9 builds)')
    sub.add_parser('bridge')
    mode = sub.add_parser('safe-mode'); mode.add_argument('state', choices=('on', 'off'))
    save = sub.add_parser('backup'); save.add_argument('output', type=Path)
    args = parser.parse_args()
    device = Device(args.serial)
    if args.command in ('start', 'build'):
        apk, version = build(device, args.base_apk)
        if args.command == 'start':
            first = not device.shell('pm path ' + CLONE, check=False).startswith('package:')
            install(device, apk); open_copy(device, first)
            print('\nWinterX (rootless) is ready on Spring %s. Install tweaks from Ruby.' % version)
    elif args.command == 'bridge': bridge(device)
    elif args.command == 'safe-mode': safe_mode(device, args.state == 'on')
    elif args.command == 'backup': backup(device, args.output)


if __name__ == '__main__':
    try: main()
    except KeyboardInterrupt: pass
