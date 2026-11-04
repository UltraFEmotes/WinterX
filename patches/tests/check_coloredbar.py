#!/usr/bin/env python3
"""Isolated ColoredBar preference/model and software-bitmap checks; does not start Spring."""
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
    parser.add_argument('--packaged', action='store_true', help='Use the actual helper from the converted APK')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='winterx-coloredbar-check-') as tmp:
        base = Path(tmp)
        classes = base / 'classes'; classes.mkdir()
        data = base / 'data'; data.mkdir()
        sources = [HERE / 'android/app/Application.java', HERE / 'android/app/ActivityThread.java']
        # Use Mac.APK's actual Bitmap/Canvas for render checks, not the older pixel spy.
        sources += sorted((HERE / 'coloredbar').glob('*.java'))
        if not args.packaged:
            sources += sorted((ROOT / 'patches/icon_positions/src/winterx/coloredbar').glob('*.java'))
            sources += sorted((ROOT / 'patches/icon_positions/src/winterx/appearance').glob('*.java'))
        cp = str(args.jar.resolve(strict=True)) + ':' + str(FRAMEWORK)
        subprocess.run([str(JAVAC), '--release', '21', '-cp', cp, '-d', str(classes), *(str(s) for s in sources)], check=True)
        subprocess.run([str(JAVA), '-Druby.test.dir=' + str(data), '-cp', str(classes) + ':' + cp,
                        'winterx.coloredbar.ColoredBarCheck'], check=True)
        if args.packaged:
            settings_data = base / 'settings-data'; settings_data.mkdir()
            subprocess.run([str(JAVA), '-Druby.test.dir=' + str(settings_data), '-cp', str(classes) + ':' + cp,
                            'winterx.coloredbar.SettingsArtworkCheck'], check=True)


if __name__ == '__main__':
    main()
