#!/usr/bin/env python3
"""Verify converted APK renderer/controller classes without starting Spring or JNI."""
import argparse
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
FRAMEWORK = Path('/Applications/Mac.apk.app/Contents/lib/android-framework.jar')
JAVAC = Path('/opt/homebrew/opt/openjdk/bin/javac')
JAVA = Path.home() / 'Library/Application Support/Mac.apk/runtime/Resources/jre/bin/java'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('jar', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='winterx-engine-hooks-') as tmp:
        base = Path(tmp)
        classes = base / 'classes'; classes.mkdir()
        data = base / 'data'; data.mkdir()
        sources = [HERE / 'android/app/Application.java', HERE / 'android/app/ActivityThread.java',
                   HERE / 'tweaks/EngineHooksCheck.java']
        cp = str(args.jar.resolve(strict=True)) + ':' + str(FRAMEWORK)
        subprocess.run([str(JAVAC), '--release', '21', '-cp', cp, '-d', str(classes), *(str(s) for s in sources)], check=True)
        subprocess.run([str(JAVA), '-Xverify:all', '-Druby.test.dir=' + str(data),
                        '-cp', str(classes) + ':' + cp, 'EngineHooksCheck'], check=True)


if __name__ == '__main__':
    main()
