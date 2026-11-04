#!/usr/bin/env python3
"""Check the built splash assets and Safe Mode drawing in isolation."""
import argparse
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FRAMEWORK = Path('/Applications/Mac.apk.app/Contents/lib/android-framework.jar')
JAVA = Path.home() / 'Library/Application Support/Mac.apk/runtime/Resources/jre/bin/java'
JAVAC = Path('/opt/homebrew/opt/openjdk/bin/javac')

p = argparse.ArgumentParser()
p.add_argument('apk', type=Path)
p.add_argument('jar', type=Path)
a = p.parse_args()
with zipfile.ZipFile(a.apk) as archive:
    logo = (ROOT / 'patches/appearance/winterx-boot.webp').read_bytes()
    for name in ('res/DX.webp', 'res/WM.webp'):
        if archive.read(name) != logo: raise AssertionError('Missing splash replacement: ' + name)
with tempfile.TemporaryDirectory(prefix='winterx-appearance-check-') as scratch:
    root = Path(scratch); classes = root / 'classes'; classes.mkdir(); data = root / 'data'; data.mkdir()
    sources = [HERE / 'android/app/Application.java', HERE / 'android/app/ActivityThread.java']
    sources += sorted((HERE / 'safe').rglob('*.java'))
    classpath = str(a.jar.resolve(strict=True)) + ':' + str(FRAMEWORK)
    subprocess.run([str(JAVAC), '--release', '21', '-cp', classpath, '-d', str(classes), *(str(s) for s in sources)], check=True)
    subprocess.run([str(JAVA), '-Druby.test.dir=' + str(data), '-cp', str(classes) + ':' + classpath, 'SafeAppearanceCheck'], check=True)
print('Both Spring splash assets replaced')
