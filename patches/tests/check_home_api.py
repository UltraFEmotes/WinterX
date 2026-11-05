#!/usr/bin/env python3
"""Check actual home API models in isolated storage. Never launches Spring."""
import argparse
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FRAMEWORK = Path('/Applications/Mac.apk.app/Contents/lib/android-framework.jar')
JAVAC = '/opt/homebrew/opt/openjdk/bin/javac'
JAVA = Path.home() / 'Library/Application Support/Mac.apk/runtime/Resources/jre/bin/java'


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('jar', type=Path)
    parser.add_argument('--packaged', action='store_true'); args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='winterx-home-api-') as tmp:
        root = Path(tmp).resolve(); classes = root / 'classes'; classes.mkdir(); data = root / 'data'; data.mkdir()
        alias = root / 'overlay-data'; alias.symlink_to(data, target_is_directory=True)
        sources = [HERE / 'android/app/Application.java', HERE / 'android/app/ActivityThread.java',
                   ROOT / 'patches/icon_positions/test/android/util/Log.java', HERE / 'tweaks/HomeApiCheck.java']
        if not args.packaged:
            sources += [ROOT / 'patches/icon_positions/src/winterx/tweaks/HomeApi.java',
                        ROOT / 'patches/icon_positions/src/winterx/layout/FreeMe.java']
        cp = str(args.jar.resolve(strict=True)) + ':' + str(FRAMEWORK)
        subprocess.run([JAVAC, '--release', '21', '-cp', cp, '-d', str(classes), *map(str, sources)], check=True)
        for files in (data / 'direct', alias / 'aliased'):
            files.mkdir()
            subprocess.run([str(JAVA), '-Xverify:all', '-Druby.test.dir=' + str(files), '-cp', str(classes) + ':' + cp,
                            'winterx.tweaks.HomeApiCheck'], check=True)


if __name__ == '__main__': main()
