#!/usr/bin/env python3
"""Exercise the free-icon geometry and persistence adapter without Spring."""
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
FRAMEWORK = Path('/Applications/Mac.apk.app/Contents/lib/android-framework.jar')
JAVA = Path.home() / 'Library/Application Support/Mac.apk/runtime/Resources/jre/bin/java'
JAVAC = Path('/opt/homebrew/opt/openjdk/bin/javac')
with tempfile.TemporaryDirectory(prefix='winterx-icons-') as temp:
    root = Path(temp)
    classes = root / 'classes'; classes.mkdir()
    sources = [HERE / ('src/winterx/layout/' + name + '.java') for name in ('IconPositions', 'IconRuntime', 'GridSlots', 'DockGeometry')] + list((HERE / 'test').rglob('*.java'))
    sources.append(HERE / 'src/winterx/animaper/Effects.java')
    subprocess.run([str(JAVAC), '--release', '21', '-cp', str(FRAMEWORK), '-d', str(classes), *(str(p) for p in sources)], check=True)
    cp = str(classes) + ':' + str(FRAMEWORK)
    subprocess.run([str(JAVA), '-cp', cp, 'IconPositionsCheck', str(root)], check=True)
    subprocess.run([str(JAVA), '-cp', cp, 'IconRuntimeCheck', str(root)], check=True)
    subprocess.run([str(JAVA), '-cp', cp, 'GridSlotsCheck', str(root)], check=True)
    subprocess.run([str(JAVA), '-cp', cp, 'DockGeometryCheck'], check=True)
    subprocess.run([str(JAVA), '-cp', cp, 'winterx.animaper.EffectsCheck'], check=True)
