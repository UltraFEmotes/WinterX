#!/usr/bin/env python3
"""Build an isolated, unsigned Spring 0.8.1 Settings-test APK for validation."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

EXPECTED = 'f07f980fe681a6de9c4ce8735ae1c0bb0f852f447fbdb925d2dec37cf9778e5c'
PATCH = Path(__file__).with_name('settings_test.py')


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    output = args.output.resolve()
    if source == output:
        parser.error('output must not overwrite the source APK')
    if output.exists():
        parser.error('output already exists; choose a new name')
    if sha256(source) != EXPECTED:
        parser.error('unsupported APK: expected the supplied Spring 0.8.1 build')
    if not shutil.which('apktool'):
        parser.error('apktool is required')
    with tempfile.TemporaryDirectory(prefix='ruby-apk-') as scratch:
        decoded = Path(scratch) / 'decoded'
        built = Path(scratch) / 'apktool-rebuilt.apk'
        assembled = Path(scratch) / 'unsigned.apk'
        subprocess.run(['apktool','d','--no-res','-f','-o',str(decoded),str(source)],check=True)
        subprocess.run(['python3',str(PATCH),str(decoded)],check=True)
        subprocess.run(['apktool','b',str(decoded),'-o',str(built)],check=True)
        with zipfile.ZipFile(built) as apk:
            dex = apk.read('classes.dex')
            if not all(s in dex for s in (b'ruby-test', b'Ruby Test', b'Ruby Settings test is working!')):
                raise ValueError('built APK is missing the expected patch strings')
        # Preserve every original resource and the untouched secondary DEX.
        # apktool's repack dropped an original resource in this APK. Reuse the
        # original ZIP entries instead, and remove only obsolete v1 signatures.
        def signature(name):
            upper = name.upper()
            if not upper.startswith('META-INF/'):
                return False
            leaf = upper[len('META-INF/'):]
            return '/' not in leaf and (leaf == 'MANIFEST.MF' or leaf.endswith(('.SF', '.RSA', '.DSA', '.EC')))
        with zipfile.ZipFile(source) as original, zipfile.ZipFile(assembled, 'w', allowZip64=True) as out:
            for info in original.infolist():
                if signature(info.filename):
                    continue
                if info.filename == 'classes.dex':
                    out.writestr(info, dex)
                else:
                    with original.open(info) as src, out.open(info, 'w') as dst:
                        shutil.copyfileobj(src, dst, 1024 * 1024)
        with zipfile.ZipFile(source) as original, zipfile.ZipFile(assembled) as out:
            before = {i.filename: (i.CRC, i.file_size) for i in original.infolist()
                      if not signature(i.filename) and i.filename != 'classes.dex'}
            after = {i.filename: (i.CRC, i.file_size) for i in out.infolist()
                     if i.filename != 'classes.dex'}
            if before != after:
                raise ValueError('repacked APK did not preserve its original non-DEX entries')
        output.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents accidental replacement of another build.
        with assembled.open('rb') as src, output.open('xb') as dst:
            shutil.copyfileobj(src, dst)
    print('Created unsigned test APK:',output)
    print('This is a test build; runtime and installation behavior are not verified.')


if __name__ == '__main__':
    main()
