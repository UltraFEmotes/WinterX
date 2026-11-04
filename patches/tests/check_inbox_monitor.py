#!/usr/bin/env python3
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory(prefix='winterx-inbox-test-') as tmp:
    root=Path(tmp); classes=root/'classes'; classes.mkdir(); inbox=root/'inbox'; inbox.mkdir()
    sources=sorted((ROOT/'patches/tests/inbox').rglob('*.java'))
    sources.append(ROOT/'patches/icon_positions/src/winterx/runtime/InboxMonitor.java')
    subprocess.run(['/opt/homebrew/opt/openjdk/bin/javac','-d',str(classes),*(str(s) for s in sources)],check=True)
    subprocess.run(['/opt/homebrew/opt/openjdk/bin/java','-cp',str(classes),'InboxMonitorCheck',str(inbox)],check=True)
