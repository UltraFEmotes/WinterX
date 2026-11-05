#!/usr/bin/env python3
"""Actual packaged Animaper/Barrel Settings and Canvas checks; no Spring launch or live data."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FRAMEWORK = Path('/Applications/Mac.apk.app/Contents/lib/android-framework.jar')
JAVAC = Path('/opt/homebrew/opt/openjdk/bin/javac')
JAVA = Path.home() / 'Library/Application Support/Mac.apk/runtime/Resources/jre/bin/java'
TEMP = Path('/private/var/folders/d_/dxvj2n8d31gdmcdyl0983n9h0000gn/T/opencode')
CHECKS = ('AnimaperCheck', 'AnimaperSettingsCheck', 'winterx.render.AnimaperCanvasCheck')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('jar', type=Path, help='Converted APK; no recompiled helper overlays')
    parser.add_argument('--artifacts', type=Path, help='New report directory; refuses overwrites')
    args = parser.parse_args()
    jar = args.jar.resolve(strict=True)
    artifacts = args.artifacts.resolve() if args.artifacts else None
    if artifacts:
        artifacts.mkdir(parents=True, exist_ok=False)
    results = []
    with tempfile.TemporaryDirectory(prefix='winterx-animaper-check-', dir=TEMP if TEMP.is_dir() else None) as name:
        base = Path(name).resolve()
        classes = base / 'classes'
        classes.mkdir()
        sources = [HERE / 'android/app/Application.java', HERE / 'android/app/ActivityThread.java',
                   ROOT / 'patches/icon_positions/test/android/util/Log.java', HERE / 'render/RendererTransitionsCheck.java',
                   *sorted((HERE / 'animaper').glob('*.java'))]
        cp = str(jar) + ':' + str(FRAMEWORK)
        subprocess.run([str(JAVAC), '--release', '21', '-cp', cp, '-d', str(classes), *map(str, sources)], check=True)
        direct = base / 'data'
        direct.mkdir()
        alias = base / 'aliased-data'
        alias.symlink_to(direct, target_is_directory=True)
        for root_kind, files in (('direct', direct), ('aliased', alias)):
            for variant in ('false', 'true'):
                for check in CHECKS:
                    label = root_kind + '-' + variant + '-' + check.rsplit('.', 1)[-1]
                    data = files / label
                    data.mkdir()
                    result = subprocess.run([str(JAVA), '-Xverify:all', '-Xmx512m', '-Druby.test.dir=' + str(data),
                        '-cp', str(classes) + ':' + cp, check, variant], capture_output=True, text=True, timeout=60)
                    log = result.stdout + result.stderr
                    results.append({'check': check, 'root': root_kind, 'native_variant': variant,
                                    'returncode': result.returncode, 'passed': result.returncode == 0, 'output': log})
                    if artifacts:
                        (artifacts / (label + '.log')).write_text(log)
                    print(('PASS ' if result.returncode == 0 else 'FAIL ') + label, flush=True)
                    if result.returncode:
                        print(log, flush=True)
    if artifacts:
        (artifacts / 'report.json').write_text(json.dumps({'jar_sha256': hashlib.sha256(jar.read_bytes()).hexdigest(), 'results': results}, indent=2) + '\n')
    failures = sum(not result['passed'] for result in results)
    print('Packaged Animaper/Barrel: %d/%d checks passed; disposable data only' % (len(results) - failures, len(results)))
    return bool(failures)


if __name__ == '__main__':
    sys.exit(main())
