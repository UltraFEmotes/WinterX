#!/usr/bin/env python3
"""Register a locally built WinterX APK for the Mac.APK bridge."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def configure(path):
    path = Path(path).resolve(strict=True)
    builds = (ROOT / 'builds').resolve()
    if not path.is_relative_to(builds) or not path.is_file() or path.suffix != '.apk':
        raise ValueError('APK must be a file inside this checkout’s builds directory')
    with zipfile.ZipFile(path) as apk:
        if b'winterx/layout/SpringHooks' not in apk.read('classes3.dex'):
            raise ValueError('WinterX hooks were not found in the APK')
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    state = ROOT / '.ruby-state'
    state.mkdir(exist_ok=True)
    temp = state / 'local-build.tmp'
    temp.write_text(json.dumps({'apk': str(path.relative_to(ROOT)), 'sha256': h.hexdigest()}) + '\n')
    temp.replace(state / 'local-build.json')
    print('Configured', path, 'SHA-256:', h.hexdigest())

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk')
    configure(parser.parse_args().apk)
