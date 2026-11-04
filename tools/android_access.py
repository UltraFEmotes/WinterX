#!/usr/bin/env python3
"""Check Spring private-folder transport access. Does not install or restart Spring."""
import argparse
import json
from pathlib import Path

from private_files import AdbFiles, DirectoryFiles, write_probe


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--serial', help='Explicit ADB serial (USB or already paired ADB endpoint)')
    target.add_argument('--directory', type=Path, help='Already accessible/mounted Spring private files folder')
    parser.add_argument('--files-root', default='/data/user/0/com.guille.spring/files')
    parser.add_argument('--access', choices=('shell', 'run-as', 'su'), default='shell')
    parser.add_argument('--adb', default='adb', help='Path to platform-tools adb / adb.exe')
    parser.add_argument('--write-probe', action='store_true', help='Explicitly create, read and remove one unique probe file')
    args = parser.parse_args(argv)
    if args.serial:
        store = AdbFiles(args.serial, args.files_root, args.access, args.adb)
        info = store.verify()
    else:
        store = DirectoryFiles(args.directory)
        info = {'access': 'directory', 'filesRoot': str(store.root)}
    if args.write_probe:
        print('Checking write access with one temporary probe; no apps or layouts will be changed.', flush=True)
        write_probe(store)
        print('Probe round trip passed; the probe was removed.', flush=True)
    info.update(writeRoundTrip=args.write_probe, androidDeploymentVerified=False)
    print(json.dumps(info, indent=2))


if __name__ == '__main__':
    main()
