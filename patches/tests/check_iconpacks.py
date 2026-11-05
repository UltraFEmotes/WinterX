#!/usr/bin/env python3
"""Check real ZIPs with native SnowyHome import/bitmap models in disposable storage only."""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FRAMEWORK = Path('/Applications/Mac.apk.app/Contents/lib/android-framework.jar')
JAVAC = Path('/opt/homebrew/opt/openjdk/bin/javac')
JAVA = Path.home() / 'Library/Application Support/Mac.apk/runtime/Resources/jre/bin/java'
sys.path.insert(0, str(ROOT / 'tools'))
import iconpack


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('jar', type=Path)
    parser.add_argument('packs', nargs='+', type=Path)
    parser.add_argument('--source-snowy', action='store_true', help='Development source overlay; not packaged-engine evidence')
    args = parser.parse_args()
    inputs = [(path.resolve(strict=True), iconpack.inspect(path)) for path in args.packs]
    if args.source_snowy: print('SOURCE OVERLAY: not packaged-engine verification', flush=True)
    with tempfile.TemporaryDirectory(prefix='winterx-real-iconpacks-') as name:
        root = Path(name).resolve(); classes = root / 'classes'; classes.mkdir()
        data = root / 'data'; data.mkdir(); alias = root / 'overlay-data'; alias.symlink_to(data, target_is_directory=True)
        sources = [HERE / 'android/app/Application.java', HERE / 'android/app/ActivityThread.java',
                   ROOT / 'patches/icon_positions/test/android/util/Log.java', HERE / 'snowy/IconPackArchiveCheck.java']
        if args.source_snowy: sources += sorted((ROOT / 'patches/icon_positions/src/winterx/snowy').glob('*.java'))
        cp = str(args.jar.resolve(strict=True)) + ':' + str(FRAMEWORK)
        subprocess.run([str(JAVAC), '--release', '21', '-cp', cp, '-d', str(classes), *map(str, sources)], check=True)
        for index, (path, result) in enumerate(inputs):
            for parent, variant in ((data, 'direct'), (alias, 'aliased')):
                files = parent / f'pack-{index}-{variant}'; inbox = files / 'ruby/snowyhome/inbox'; inbox.mkdir(parents=True)
                shutil.copy2(path, inbox / 'fixture.zip')
                subprocess.run([str(JAVA), '-Xverify:all', '-Druby.test.dir=' + str(files), '-cp', str(classes) + ':' + cp,
                                'winterx.snowy.IconPackArchiveCheck', result[3]], check=True)
            if hashlib.sha256(path.read_bytes()).hexdigest() != result[3]: raise AssertionError('Input pack was modified')
    print('All input ZIPs preserved; no Spring process, live data, listener or network used.')


if __name__ == '__main__': main()
