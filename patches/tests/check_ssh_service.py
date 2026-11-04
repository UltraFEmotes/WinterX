#!/usr/bin/env python3
"""Check SSH service ownership/cancellation with a no-socket engine spy, never user data."""
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
    parser.add_argument('jar', type=Path); parser.add_argument('--packaged', action='store_true'); args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='winterx-ssh-service-') as name:
        root = Path(name); classes = root / 'classes'; classes.mkdir(); data = root / 'data'; data.mkdir()
        sources = [HERE / 'android/app/Application.java', HERE / 'android/app/ActivityThread.java']
        sources += sorted((HERE / 'ssh').rglob('*.java'))
        if not args.packaged: sources.append(ROOT / 'patches/icon_positions/src/winterx/ssh/SshService.java')
        cp = str(args.jar.resolve(strict=True)) + ':' + str(FRAMEWORK)
        subprocess.run([str(JAVAC), '--release', '21', '-cp', cp, '-d', str(classes), *map(str, sources)], check=True)
        subprocess.run([str(JAVA), '-Xverify:all', '-Druby.test.dir=' + str(data), '-cp', str(classes) + ':' + cp,
                        'winterx.ssh.SshServiceCheck'], check=True)


if __name__ == '__main__': main()
