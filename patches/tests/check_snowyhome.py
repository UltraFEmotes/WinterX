#!/usr/bin/env python3
"""SnowyHome native model/software-bitmap checks. Source overlay by default; never launches Spring."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FRAMEWORK = Path('/Applications/Mac.apk.app/Contents/lib/android-framework.jar')
JAVAC = Path('/opt/homebrew/opt/openjdk/bin/javac')
JAVA = Path.home() / 'Library/Application Support/Mac.apk/runtime/Resources/jre/bin/java'
sys.path.insert(0, str(ROOT / 'tools'))
import iconpack


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('jar', type=Path)
    parser.add_argument('--packaged', action='store_true'); args = parser.parse_args()
    if not args.packaged: print('SOURCE OVERLAY: this does not verify the prepared alpha8 or packaged SnowyHome hooks', flush=True)
    with tempfile.TemporaryDirectory(prefix='winterx-snowy-check-') as name:
        root = Path(name); classes = root / 'classes'; classes.mkdir(); data = root / 'data'; data.mkdir()
        source = root / 'pack-source'; (source / 'icons').mkdir(parents=True)
        Image.new('RGBA', (64, 64), (20, 80, 200, 160)).save(source / 'icons/mail.png')
        (source / 'manifest.json').write_text(json.dumps({'format': iconpack.FORMAT, 'id': 'me.example.icons',
            'name': 'Test Icons', 'author': 'Fixture', 'version': '0.1.0', 'icons': {'mail': {'file': 'icons/mail.png'}}}))
        archive = root / 'fixture.zip'; iconpack.build(source, archive)
        target = iconpack.export(archive, data / 'ruby/snowyhome/packs')
        sources = [HERE / 'android/app/Application.java', HERE / 'android/app/ActivityThread.java',
                   ROOT / 'patches/icon_positions/test/android/util/Log.java', HERE / 'snowy/SnowyHomeCheck.java']
        if not args.packaged:
            sources += sorted((ROOT / 'patches/icon_positions/src/winterx/snowy').glob('*.java'))
            sources.append(ROOT / 'patches/icon_positions/src/winterx/layout/LayoutSettings.java')
        cp = str(args.jar.resolve(strict=True)) + ':' + str(FRAMEWORK)
        subprocess.run([str(JAVAC), '--release', '21', '-cp', cp, '-d', str(classes), *map(str, sources)], check=True)
        subprocess.run([str(JAVA), '-Xverify:all', '-Druby.test.dir=' + str(data), '-cp', str(classes) + ':' + cp,
                        'winterx.snowy.SnowyHomeCheck', target.name, str(args.packaged).lower()], check=True)


if __name__ == '__main__': main()
