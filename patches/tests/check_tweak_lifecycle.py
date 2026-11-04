#!/usr/bin/env python3
"""Test runtime lifecycle with a QuickJs spy; does not execute JNI or start Spring."""
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
    parser.add_argument('--packaged', action='store_true', help='Use actual helpers from the converted APK, still with the JNI spy')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='winterx-tweak-lifecycle-') as tmp:
        base = Path(tmp)
        classes = base / 'classes'; classes.mkdir()
        data = base / 'data'; data.mkdir()
        sources = [HERE / 'android/app/Application.java', HERE / 'android/app/ActivityThread.java',
                   HERE / 'tweaks/runtime/com/guille/spring/sapp/QuickJs.java',
                   HERE / 'tweaks/runtime/android/util/Log.java', HERE / 'tweaks/TweakLifecycleCheck.java']
        if not args.packaged:
            sources += sorted((ROOT / 'patches/icon_positions/src/winterx/tweaks').glob('*.java'))
            sources += sorted((ROOT / 'patches/icon_positions/src/winterx/coloredbar').glob('*.java'))
        cp = str(args.jar.resolve(strict=True)) + ':' + str(FRAMEWORK)
        subprocess.run([str(JAVAC), '--release', '21', '-cp', cp, '-d', str(classes), *(str(s) for s in sources)], check=True)
        subprocess.run([str(JAVA), '-Druby.test.dir=' + str(data), '-cp', str(classes) + ':' + cp,
                        'winterx.tweaks.TweakLifecycleCheck'], check=True)


if __name__ == '__main__':
    main()
