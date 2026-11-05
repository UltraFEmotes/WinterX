#!/usr/bin/env python3
"""Run SSH configuration and in-memory info checks without binding a port or starting a shell."""
import argparse
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('jar', type=Path)
    parser.add_argument('--javac', default='javac'); parser.add_argument('--java', default='java'); args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='winterx-ssh-check-') as tmp:
        root = Path(tmp).resolve(); classes = root / 'classes'; classes.mkdir(); files = root / 'private'; files.mkdir()
        subprocess.run([args.javac, '--release', '8', '-cp', str(args.jar.resolve()), '-d', str(classes),
                        *map(str, (HERE / 'test').rglob('*.java'))], check=True)
        for check in ('SshEngineCheck', 'FetchCheck', 'AppCommandCheck', 'BuiltinShellCheck'):
            subprocess.run([args.java, '-Xverify:all', '-cp', str(classes) + ':' + str(args.jar.resolve()),
                            'winterx.ssh.' + check, str(files)], check=True)


if __name__ == '__main__': main()
