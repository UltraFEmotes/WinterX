#!/usr/bin/env python3
"""Packaged Spring 0.8.1 software-renderer transition checks; never starts a launcher."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FRAMEWORK = Path('/Applications/Mac.apk.app/Contents/lib/android-framework.jar')
JAVAC = Path('/opt/homebrew/opt/openjdk/bin/javac')
JAVA = Path.home() / 'Library/Application Support/Mac.apk/runtime/Resources/jre/bin/java'
TEMP = Path('/private/var/folders/d_/dxvj2n8d31gdmcdyl0983n9h0000gn/T/opencode')
CASES = ('scroll-k', 'scroll-o', 'folder-upper', 'folder-lower', 'folder-anchor',
         'folder-retained', 'folder-content', 'warm-tiles', 'warm-dock',
         'dock-scroll', 'folder-prewarm', 'folder-queued', 'folder-bookkeeping',
         'cache-lifecycle', 'barrel-render', 'barrel-sparse')
sys.path.insert(0, str(ROOT / 'tools'))
import iconpack


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('jar', type=Path, help='Unmodified converted engine to exercise, without helper overlays')
    parser.add_argument('--negative-control', action='store_true', help='Require each chosen case to reach its exact renderer regression assertion')
    parser.add_argument('--case', action='append', choices=CASES, help='Run only these cases')
    parser.add_argument('--artifacts', type=Path, help='New directory for reports and rendered PNGs; refuses overwrites')
    args = parser.parse_args()
    jar = args.jar.resolve(strict=True)
    artifacts = args.artifacts.resolve() if args.artifacts else None
    if artifacts:
        artifacts.mkdir(parents=True, exist_ok=False)
    results = []
    with tempfile.TemporaryDirectory(prefix='winterx-render-check-', dir=TEMP if TEMP.is_dir() else None) as name:
        base = Path(name).resolve()
        classes = base / 'classes'; classes.mkdir()
        source = base / 'pack-source'; (source / 'icons').mkdir(parents=True)
        icons = {}
        for app, color in (('mail', '#1450c8'), ('phone', '#00c870'), ('safari', '#e0a020')):
            Image.new('RGBA', (64, 64), color).save(source / ('icons/' + app + '.png'))
            icons[app] = {'file': 'icons/' + app + '.png'}
        (source / 'manifest.json').write_text(json.dumps({'format': iconpack.FORMAT,
            'id': 'me.example.render-fixture', 'name': 'Renderer Fixture', 'author': 'Fixture',
            'version': '0.1.0', 'icons': icons}))
        archive = base / 'fixture.zip'; iconpack.build(source, archive)
        revision = iconpack.inspect(archive)[3]
        token = hashlib.sha256(b'fixture.zip').hexdigest()
        sources = [HERE / 'android/app/Application.java', HERE / 'android/app/ActivityThread.java',
                   ROOT / 'patches/icon_positions/test/android/util/Log.java',
                   HERE / 'render/RendererTransitionsCheck.java']
        cp = str(jar) + ':' + str(FRAMEWORK)
        subprocess.run([str(JAVAC), '--release', '21', '-cp', cp, '-d', str(classes), *map(str, sources)], check=True)
        direct = base / 'data'; direct.mkdir()
        alias = base / 'aliased-data'; alias.symlink_to(direct, target_is_directory=True)
        for root_kind, files in (('direct', direct), ('aliased', alias)):
            for variant in ('false', 'true'):
                for case in args.case or CASES:
                    label = root_kind + '-' + variant + '-' + case
                    data = files / label; (data / 'ruby/snowyhome/inbox').mkdir(parents=True)
                    shutil.copy2(archive, data / 'ruby/snowyhome/inbox/fixture.zip')
                    command = [str(JAVA), '-Xverify:all', '-Xmx512m', '-Druby.test.dir=' + str(data),
                               '-cp', str(classes) + ':' + cp, 'winterx.render.RendererTransitionsCheck',
                               case, variant, revision, token]
                    if artifacts:
                        output = artifacts / label; output.mkdir()
                        command.append(str(output))
                    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
                    log = result.stdout + result.stderr
                    expected = 'java.lang.AssertionError: RENDER_REGRESSION: ' + case
                    passed = result.returncode == 0 if not args.negative_control else result.returncode == 1 and expected in log
                    results.append({'case': case, 'root': root_kind, 'native_variant': variant,
                                    'returncode': result.returncode, 'passed': passed,
                                    'expected_regression': args.negative_control, 'output': log})
                    if artifacts:
                        (output / 'check.log').write_text(log)
                    print(('PASS ' if passed else 'FAIL ') + label + (' (expected old-engine regression)' if args.negative_control and passed else ''), flush=True)
                    if not passed:
                        print(log, flush=True)
    if artifacts:
        (artifacts / 'report.json').write_text(json.dumps({'jar': str(jar),
            'jar_sha256': hashlib.sha256(jar.read_bytes()).hexdigest(),
            'negative_control': args.negative_control, 'results': results}, indent=2) + '\n')
    failures = [result for result in results if not result['passed']]
    print('Packaged renderer transitions: %d/%d checks passed; disposable data only' % (len(results) - len(failures), len(results)))
    return bool(failures)


if __name__ == '__main__':
    sys.exit(main())
