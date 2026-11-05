#!/usr/bin/env python3
"""Run WinterX on a rooted Android phone or emulator, from macOS, Linux or Windows.

One-time setup for a device (Spring must be installed and logged in; the core built with extensions/build.py):

    python3 tools/rooted_launch.py setup --core out/core

Every time you want Spring with WinterX (keep the window open; it also serves Ruby's source refreshes):

    python3 tools/rooted_launch.py start

Needs: adb (Android SDK platform-tools), Node.js (to build the loader once), and Frida's Python bindings
(`pip install frida==17.25.2`). The device needs root over adb (`adb root`, as on emulators without Google Play) or a
working `su`. Pick a device with --serial or WINTERX_SERIAL when more than one is connected.
"""
import argparse
import hashlib
import json
import lzma
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import toolchain

FRIDA = '17.25.2'
# Official release builds (github.com/frida/frida), checked before they are pushed to the device.
FRIDA_SERVER = {
    'arm64-v8a': ('android-arm64', '08d7b7f02256621c9089cecd6495a5eb43861bf560a7ed86ad376e75d16a1fb6',
                  '7bb6219131819c11e5fe53b3e32fae0b8d1ff4c2a9c35c1a549d2703ea0f3b9b'),
    'x86_64': ('android-x86_64', 'ee675076d25599dd55c3b080ccf61c02b44d00653a06db2b0e2a2149ef69dad1',
               '81a916d8e5e23c01350a31521b364489751785a17954b340cfaa644b8c474d19'),
}
DEVICE_SERVER = '/data/local/tmp/winterx-frida-' + FRIDA
GUEST_PORT, HOST_PORT = 27042, 27048
WORK = Path(os.environ.get('WINTERX_HOME', Path.home() / '.winterx')) / 'android'


def sha(data): return hashlib.sha256(data).hexdigest()


class Device:
    def __init__(self, serial):
        self.adb = str(toolchain.adb())
        if not serial:
            listed = [line.split()[0] for line in subprocess.run([self.adb, 'devices'], capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout.splitlines()[1:]
                      if line.strip().endswith('device')]
            if len(listed) != 1: raise SystemExit('Connect exactly one device, or pick one with --serial (see "adb devices"): ' + ', '.join(listed or ['none']))
            serial = listed[0]
        self.serial = serial

    def run(self, *args, check=True, text=True):
        # adb would otherwise read this terminal's input and swallow what the user types at our prompts.
        return subprocess.run([self.adb, '-s', self.serial, *args], capture_output=True, text=text, check=check, stdin=subprocess.DEVNULL)

    def shell(self, command, check=True):
        return self.run('shell', command, check=check).stdout.strip()

    def rooted(self):
        self.run('root', check=False); time.sleep(1.5)
        self.run('wait-for-device')
        if self.shell('id -u') == '0': return 'shell'
        if self.shell("su -c 'id -u' 2>/dev/null", check=False) == '0': return 'su'
        raise SystemExit('This device has no root over adb. WinterX on Android needs a rooted phone or an emulator image without Google Play.')

    def spring_running(self):
        return bool(self.shell('pidof com.guille.spring', check=False))


def privileged(access, command):
    """The command as root: directly over a root adb shell, or through su."""
    return command if access == 'shell' else "su -c '%s'" % command.replace("'", "'\\''")


def state_dir(serial):
    return WORK / 'devices' / serial.replace(':', '_').replace('/', '_')


def loader():
    path = WORK / 'root-loader.js'
    if not path.exists():
        agent = ROOT / 'tools/android_agent'
        npm = shutil.which('npm.cmd' if toolchain.WINDOWS else 'npm'); node = shutil.which('node')
        if not npm or not node: raise SystemExit('Node.js is needed once to build the loader: install it from https://nodejs.org')
        if not (agent / 'node_modules').exists(): subprocess.run([npm, 'ci'], cwd=agent, check=True)
        WORK.mkdir(parents=True, exist_ok=True)
        subprocess.run([node, str(agent / 'build.mjs'), str(path)], cwd=agent, check=True)
    return path


def frida_server(device, access):
    abi = device.shell('getprop ro.product.cpu.abi')
    if abi not in FRIDA_SERVER: raise SystemExit('No pinned Frida server for this CPU (%s). Supported: %s' % (abi, ', '.join(FRIDA_SERVER)))
    asset, packed_sha, binary_sha = FRIDA_SERVER[abi]
    local = WORK / ('frida-server-%s-%s' % (FRIDA, asset))
    if not local.exists() or sha(local.read_bytes()) != binary_sha:
        url = 'https://github.com/frida/frida/releases/download/%s/frida-server-%s-%s.xz' % (FRIDA, FRIDA, asset)
        print('Downloading Frida server for', abi, '…')
        packed = urllib.request.urlopen(url, timeout=120).read()
        if sha(packed) != packed_sha: raise SystemExit('Downloaded Frida server failed its checksum; not using it.')
        binary = lzma.decompress(packed)
        if sha(binary) != binary_sha: raise SystemExit('Unpacked Frida server failed its checksum; not using it.')
        WORK.mkdir(parents=True, exist_ok=True); local.write_bytes(binary)
    on_device = device.shell(privileged(access, 'sha256sum %s 2>/dev/null' % DEVICE_SERVER), check=False).split()
    if not on_device or on_device[0] != binary_sha:
        device.run('push', str(local), '/data/local/tmp/.winterx-frida-upload')
        device.shell(privileged(access, 'mv /data/local/tmp/.winterx-frida-upload %s && chmod 700 %s' % (DEVICE_SERVER, DEVICE_SERVER)))
    return binary_sha


def ensure_server(device, access):
    frida_server(device, access)
    running = device.shell("ps -A -o ARGS | grep '^winterx-frida-%s -l 127.0.0.1:%d' | head -1" % (FRIDA, GUEST_PORT), check=False)
    if not running:
        print('Starting the Frida server on the device…')
        device.shell(privileged(access, 'setsid %s -l 127.0.0.1:%d </dev/null >/data/local/tmp/winterx-frida.log 2>&1 &' % (DEVICE_SERVER, GUEST_PORT)))
        time.sleep(3)
    device.run('forward', 'tcp:%d' % HOST_PORT, 'tcp:%d' % GUEST_PORT)


def runtime(device, access, *args):
    command = [sys.executable, '-u', str(ROOT / 'tools/android_runtime.py'), '--serial', device.serial, '--access', access,
               '--adb', device.adb, '--state', str(state_dir(device.serial)), *map(str, args)]
    return subprocess.run(command)


def close_spring(device, reason):
    if not device.spring_running(): return
    answer = input('Spring is running on the device. Close it %s? [y/N] ' % reason).strip().lower()
    if answer != 'y': raise SystemExit('Left Spring running; nothing changed.')
    device.shell('am force-stop com.guille.spring'); time.sleep(1)


def check_frida_python():
    try:
        import frida
    except ImportError:
        raise SystemExit('Frida\'s Python bindings are missing: run  %s -m pip install frida==%s' % (Path(sys.executable).name, FRIDA))
    if frida.__version__ != FRIDA:
        raise SystemExit('Frida %s is installed but WinterX needs %s: run  %s -m pip install frida==%s' % (frida.__version__, FRIDA, Path(sys.executable).name, FRIDA))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--serial', default=os.environ.get('WINTERX_SERIAL'), help='device from "adb devices" (default: the only one)')
    commands = parser.add_subparsers(dest='command', required=True)
    setup = commands.add_parser('setup', help='prepare a device once (backs up Spring\'s data first)')
    setup.add_argument('--core', type=Path, required=True, help='core build folder from extensions/build.py runtime')
    commands.add_parser('start', help='start Spring with WinterX and keep Ruby\'s bridge running')
    args = parser.parse_args()
    check_frida_python()
    device = Device(args.serial); access = device.rooted()
    ensure_server(device, access)
    if args.command == 'setup':
        payload = args.core.resolve(strict=True) / 'android-runtime'
        manifest = json.loads((payload / 'manifest.json').read_text())
        print('Preparing %s for WinterX core (%s)…' % (device.serial, manifest.get('runtimeAbi')))
        close_spring(device, 'to stage the WinterX core')
        state_dir(device.serial).mkdir(parents=True, exist_ok=True)
        result = runtime(device, access, 'stage', payload)
        if result.returncode: raise SystemExit(result.returncode)
        print('Done. Start Spring with WinterX any time with:  %s tools/rooted_launch.py start' % Path(sys.executable).name)
        return
    if not (state_dir(device.serial) / 'android-runtime.json').exists():
        raise SystemExit('This device isn\'t set up yet: run  tools/rooted_launch.py setup --core out/core')
    agent = loader()
    close_spring(device, 'so WinterX can start it')
    for attempt in (1, 2):
        log = WORK / ('last-launch-%s.log' % device.serial.replace(':', '_'))
        process = subprocess.Popen([sys.executable, '-u', str(ROOT / 'tools/android_runtime.py'), '--serial', device.serial, '--access', access,
                                    '--adb', device.adb, '--state', str(state_dir(device.serial)), 'launch', str(agent), '--bridge'],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        started = False
        with log.open('w') as record:
            for line in process.stdout:
                print(line, end='', flush=True); record.write(line); record.flush()
                started |= 'Rooted runtime active' in line
        if process.wait() == 0 or started: raise SystemExit(process.returncode)
        if attempt == 1:
            # A Frida attach timeout leaves Android restarting a stock Spring; close only that one and retry once.
            print('Launch didn\'t start; retrying once…'); time.sleep(2)
            device.shell('am force-stop com.guille.spring'); time.sleep(1)
    raise SystemExit(1)


if __name__ == '__main__':
    main()
