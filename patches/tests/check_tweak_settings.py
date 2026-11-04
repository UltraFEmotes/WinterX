#!/usr/bin/env python3
"""Check executable-tweak Settings models against a converted Spring JAR, without launching Spring."""
import argparse
import hashlib
import json
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
    parser.add_argument('--packaged', action='store_true', help='Use the actual helpers from the converted APK, not recompiled sources')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='winterx-tweak-models-') as tmp:
        base = Path(tmp)
        classes = base / 'classes'; classes.mkdir()
        data = base / 'data'; data.mkdir()
        manifest = json.loads((ROOT / 'examples/code-tweak/manifest.json').read_text())
        tweak = data / 'winterx-tweaks' / manifest['id']; tweak.mkdir(parents=True)
        payload = json.dumps(manifest).encode()
        (tweak / 'manifest.json').write_bytes(payload)
        (tweak / 'manifest.sha256').write_text(hashlib.sha256(payload).hexdigest() + '\n')
        (tweak / 'enabled').touch()
        sources = [HERE / 'android/app/Application.java', HERE / 'android/app/ActivityThread.java',
                   HERE / 'tweaks/TweakSettingsCheck.java']
        if not args.packaged:
            sources += sorted((ROOT / 'patches/icon_positions/src/winterx/tweaks').glob('*.java'))
            sources += sorted((ROOT / 'patches/icon_positions/src/winterx/coloredbar').glob('*.java'))
            sources += sorted((ROOT / 'patches/icon_positions/src/winterx/appearance').glob('*.java'))
            sources += sorted((ROOT / 'patches/icon_positions/src/winterx/layout').glob('*.java'))
        cp = str(args.jar.resolve(strict=True)) + ':' + str(FRAMEWORK)
        subprocess.run([str(JAVAC), '--release', '21', '-cp', cp, '-d', str(classes), *(str(s) for s in sources)], check=True)
        subprocess.run([str(JAVA), '-Druby.test.dir=' + str(data), '-cp', str(classes) + ':' + cp,
                        'winterx.tweaks.TweakSettingsCheck'], check=True)


if __name__ == '__main__':
    main()
