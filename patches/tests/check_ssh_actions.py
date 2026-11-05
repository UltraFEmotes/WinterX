#!/usr/bin/env python3
"""Guarded .sapp dispatcher checks with non-acting native spies; no live apps, listener or shell."""
import argparse
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FRAMEWORK = Path('/Applications/Mac.apk.app/Contents/lib/android-framework.jar')
JAVAC = Path('/opt/homebrew/opt/openjdk/bin/javac')
JAVA = Path.home() / 'Library/Application Support/Mac.apk/runtime/Resources/jre/bin/java'
TEMP = Path('/private/var/folders/d_/dxvj2n8d31gdmcdyl0983n9h0000gn/T/opencode')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('jar', type=Path)
    parser.add_argument('--packaged', action='store_true', help='Use the actual dispatcher helper from the converted APK')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='winterx-ssh-actions-', dir=TEMP if TEMP.is_dir() else None) as name:
        base = Path(name).resolve()
        classes = base / 'classes'
        classes.mkdir()
        sources = [HERE / 'android/app/Application.java', HERE / 'android/app/ActivityThread.java', HERE / 'android/app/Activity.java',
                   HERE / 'ssh/winterx/ssh/SshServerEngine.java', *sorted((HERE / 'actions').rglob('*.java'))]
        if not args.packaged:
            sources.append(ROOT / 'patches/icon_positions/src/winterx/ssh/SshActions.java')
        cp = str(args.jar.resolve(strict=True)) + ':' + str(FRAMEWORK)
        subprocess.run([str(JAVAC), '--release', '21', '-cp', cp, '-d', str(classes), *map(str, sources)], check=True)
        direct = base / 'data'
        direct.mkdir()
        alias = base / 'aliased-data'
        alias.symlink_to(direct, target_is_directory=True)
        for kind, root in (('direct', direct), ('aliased', alias)):
            files = root / kind
            files.mkdir()
            subprocess.run([str(JAVA), '-Xverify:all', '-Xmx512m', '-Druby.test.dir=' + str(files),
                            '-cp', str(classes) + ':' + cp, 'winterx.ssh.SshActionsCheck'], check=True)


if __name__ == '__main__':
    main()
