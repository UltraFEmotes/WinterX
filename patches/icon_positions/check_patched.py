#!/usr/bin/env python3
"""Exercise the patched Spring classes and a fresh-process position reload."""
import argparse
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
FRAMEWORK = Path('/Applications/Mac.apk.app/Contents/lib/android-framework.jar')
JAVA = Path.home() / 'Library/Application Support/Mac.apk/runtime/Resources/jre/bin/java'
JAVAC = Path('/opt/homebrew/opt/openjdk/bin/javac')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('jar', type=Path, help='Mac.APK-converted jar from the patched APK')
args = parser.parse_args()
jar = args.jar.resolve(strict=True)
with tempfile.TemporaryDirectory(prefix='winterx-patched-icons-') as temp:
    root = Path(temp)
    classes = root / 'classes'; classes.mkdir()
    data = root / 'data'; data.mkdir()
    sources = list((HERE / 'test/android').rglob('*.java')) + list((HERE / 'integration').glob('Patched*Check.java'))
    subprocess.run([str(JAVAC), '--release', '21', '-cp', str(jar) + ':' + str(FRAMEWORK), '-d', str(classes), *(str(s) for s in sources)], check=True)
    cp = ':'.join((str(classes), str(jar), str(FRAMEWORK)))
    disabled = root / 'disabled'; disabled.mkdir()
    subprocess.run([str(JAVA), '-cp', cp, 'PatchedDisabledCheck', str(disabled)], check=True)
    scaled = root / 'scaled'; scaled.mkdir()
    subprocess.run([str(JAVA), '-cp', cp, 'PatchedScaleCheck', str(scaled)], check=True)
    scaled_tall = root / 'scaled-tall'; scaled_tall.mkdir()
    subprocess.run([str(JAVA), '-cp', cp, 'PatchedScaleCheck', str(scaled_tall), 'true'], check=True)
    subprocess.run([str(JAVA), '-cp', cp, 'PatchedControllerCheck', str(data)], check=True)
    (data / 'ruby/safe-mode.enabled').unlink()
    subprocess.run([str(JAVA), '-cp', cp, 'PatchedPersistenceCheck', str(data)], check=True)
    for variant in ('false', 'true'):
        freeme = root / ('freeme-' + variant); freeme.mkdir()
        subprocess.run([str(JAVA), '-cp', cp, 'PatchedFreeMeCheck', str(freeme), variant], check=True)
        subprocess.run([str(JAVA), '-cp', cp, 'PatchedFreeMePersistenceCheck', str(freeme)], check=True)
        dockin = root / ('dockin-' + variant); dockin.mkdir()
        subprocess.run([str(JAVA), '-cp', cp, 'PatchedDockInCheck', str(dockin), variant], check=True)
