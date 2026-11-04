#!/usr/bin/env python3
import subprocess,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='winterx-trust-test-') as tmp:
    root=Path(tmp); classes=root/'classes'; classes.mkdir()
    with zipfile.ZipFile(ROOT/'builds/IExplored-0.3-bridgeless.sapp') as app:
        script=root/'main.js'; script.write_bytes(app.read('main.js'))
    with zipfile.ZipFile(ROOT/'builds/Ruby-1.4-bridgeless-v2.sapp') as app:
        ruby=root/'ruby.js'; ruby.write_bytes(app.read('main.js'))
    with zipfile.ZipFile(ROOT/'builds/IExplored-0.4-bridgeless.sapp') as app:
        next_script=root/'next.js'; next_script.write_bytes(app.read('main.js'))
    with zipfile.ZipFile(ROOT/'builds/Ruby-1.5-native.sapp') as app:
        ruby15=root/'ruby15.js'; ruby15.write_bytes(app.read('main.js'))
    with zipfile.ZipFile(ROOT/'builds/Ruby-1.6-native.sapp') as app:
        ruby16=root/'ruby16.js'; ruby16.write_bytes(app.read('main.js'))
    with zipfile.ZipFile(ROOT/'builds/Ruby-1.7-sources.sapp') as app:
        ruby17=root/'ruby17.js'; ruby17.write_bytes(app.read('main.js'))
    subprocess.run(['/opt/homebrew/opt/openjdk/bin/javac','-d',str(classes),
                    str(ROOT/'patches/icon_positions/src/winterx/runtime/TrustedFiles.java'),
                    str(ROOT/'patches/tests/trusted/TrustedFilesCheck.java')],check=True)
    subprocess.run(['/opt/homebrew/opt/openjdk/bin/java','-cp',str(classes),'TrustedFilesCheck',str(root),str(script),str(ruby),str(next_script),str(ruby15),str(ruby16),str(ruby17)],check=True)
