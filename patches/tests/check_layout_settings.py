#!/usr/bin/env python3
"""Check native layout Settings models without launching Spring or using user data."""
import argparse
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FRAMEWORK = Path('/Applications/Mac.apk.app/Contents/lib/android-framework.jar')
JAVAC = Path('/opt/homebrew/opt/openjdk/bin/javac')
JAVA = Path.home() / 'Library/Application Support/Mac.apk/runtime/Resources/jre/bin/java'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('jar', type=Path)
    parser.add_argument('--packaged', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='winterx-layout-models-') as name:
        temp = Path(name)
        classes = temp / 'classes'; classes.mkdir()
        data = temp / 'data'; data.mkdir()
        sources = [HERE / 'android/app/Application.java', HERE / 'android/app/ActivityThread.java', HERE / 'layout/LayoutSettingsCheck.java']
        # Failed preference changes log warnings; use the isolated logging stub, not Mac.APK JNI.
        sources.append(ROOT / 'patches/icon_positions/test/android/util/Log.java')
        if not args.packaged:
            for package in ('layout', 'tweaks', 'coloredbar', 'appearance'):
                sources += sorted((ROOT / 'patches/icon_positions/src/winterx' / package).glob('*.java'))
        cp = str(args.jar.resolve(strict=True)) + ':' + str(FRAMEWORK)
        subprocess.run([str(JAVAC), '--release', '21', '-cp', cp, '-d', str(classes), *map(str, sources)], check=True)
        subprocess.run([str(JAVA), '-Druby.test.dir=' + str(data), '-cp', str(classes) + ':' + cp, 'LayoutSettingsCheck', str(args.packaged).lower()], check=True)


if __name__ == '__main__':
    main()
