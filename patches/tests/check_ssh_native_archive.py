#!/usr/bin/env python3
"""Actual native single-archive file import in disposable roots; no Spring launch or live install."""
import argparse
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
FRAMEWORK = Path('/Applications/Mac.apk.app/Contents/lib/android-framework.jar')
JAVAC = Path('/opt/homebrew/opt/openjdk/bin/javac')
JAVA = Path.home() / 'Library/Application Support/Mac.apk/runtime/Resources/jre/bin/java'
TEMP = Path('/private/var/folders/d_/dxvj2n8d31gdmcdyl0983n9h0000gn/T/opencode')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('jar', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='winterx-native-archive-', dir=TEMP if TEMP.is_dir() else None) as name:
        base = Path(name).resolve()
        classes = base / 'classes'
        classes.mkdir()
        cp = str(args.jar.resolve(strict=True)) + ':' + str(FRAMEWORK)
        sources = [HERE / 'android/app/Application.java', HERE / 'android/app/ActivityThread.java', *sorted((HERE / 'actions_native').rglob('*.java'))]
        subprocess.run([str(JAVAC), '--release', '21', '-cp', cp, '-d', str(classes), *map(str, sources)], check=True)
        data = base / 'data'
        data.mkdir()
        alias = base / 'aliased-data'
        alias.symlink_to(data, target_is_directory=True)
        for kind, root in (('direct', data), ('aliased', alias)):
            for variant in ('false', 'true'):
                files = root / (kind + '-' + variant)
                files.mkdir()
                subprocess.run([str(JAVA), '-Xverify:all', '-Xmx512m', '-Druby.test.dir=' + str(files), '-cp', str(classes) + ':' + cp,
                                'winterx.ssh.NativeArchiveCheck', variant], check=True)


if __name__ == '__main__':
    main()
