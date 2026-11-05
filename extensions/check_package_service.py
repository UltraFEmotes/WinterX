#!/usr/bin/env python3
"""Check the core's in-process package manager against the Python registry on real packages.

Both install the same archives into disposable roots; the resulting registry and tweak trees must match byte for byte.
Then remove/reinstall/tamper/recovery and a bundled-app package are exercised in the Java implementation.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'tools'))
import ruby_packages
from check import FRAMEWORK, JAVA, JAVAC

APP = 'sapps-data/com.ruby.manager/files'


def tree(root):
    root = Path(root)
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted(root.rglob('*'))
            if path.is_file() and path.name != '.lock' and not path.name.startswith('.winterx-')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('core', type=Path, help='core build folder (core-engine.jar, winterx-native-api.jar, spring-api.jar)')
    parser.add_argument('packages', type=Path, help='folder of official .springys archives')
    args = parser.parse_args()
    core = args.core.resolve(strict=True)
    archives = sorted(args.packages.resolve(strict=True).glob('*.springys'))
    with tempfile.TemporaryDirectory(prefix='winterx-package-service-') as name:
        base = Path(name).resolve(); classes = base / 'classes'; classes.mkdir()
        cp = str(core / 'core-engine.jar') + ':' + str(FRAMEWORK)
        sources = [ROOT / 'patches/tests/android/app/Application.java', ROOT / 'patches/tests/android/app/ActivityThread.java',
                   ROOT / 'patches/icon_positions/test/android/util/Log.java', HERE / 'tests/PackageServiceCheck.java']
        subprocess.run([str(JAVAC), '--release', '21', '-cp', cp, '-d', str(classes), *map(str, sources)], check=True)

        def jvm(root, inbox, *extra):
            subprocess.run([str(JAVA), '-Xverify:all', '-cp', str(classes) + ':' + cp, 'PackageServiceCheck', str(root), str(inbox), *map(str, extra)], check=True)

        # Reference: the Python registry used by the bridge.
        python_root = base / 'python'; (python_root / APP / 'imports').mkdir(parents=True)
        packages = ruby_packages.Packages(python_root / APP, python_root / 'ruby/settings-test.enabled', lambda enabled: None,
            tweak_root=python_root / 'winterx-tweaks', supported_tweaks=True, supported_native=True, supported_capabilities=('native.hooks',))
        java_root = base / 'java'; (java_root / APP / 'imports').mkdir(parents=True); inbox = base / 'inbox'; inbox.mkdir()
        for archive in archives:
            shutil.copy2(archive, python_root / APP / 'imports' / archive.name); packages.install(archive.name)
            shutil.copy2(archive, java_root / APP / 'imports' / archive.name)
        jvm(java_root, inbox, 'install', *[archive.name for archive in archives])

        for relative in ('winterx-tweaks', APP + '/package-registry/tweaks', APP + '/package-registry/art'):
            expected, actual = tree(python_root / relative), tree(java_root / relative)
            if expected != actual:
                differing = sorted(set(expected) ^ set(actual)) or [key for key in expected if expected[key] != actual.get(key)]
                raise SystemExit('Java and Python installs differ under ' + relative + ': ' + repr(differing[:5]))
        registry = lambda root: json.loads((root / APP / 'package-registry/installed.json').read_text())
        if registry(python_root) != registry(java_root): raise SystemExit('Java and Python registries differ')
        print('Java and Python installs identical: %d packages, registry, revisions, enabled trees' % len(archives))

        ids = {json.loads(zipfile.ZipFile(archive).read('manifest.json'))['id']: archive.name for archive in archives}
        target, other = 'com.winterx.ssh', 'com.winterx.dockin'
        jvm(java_root, inbox, 'lifecycle', target, ids[target], other)

        # A package that bundles a Spring app, built with the real package builder.
        source = base / 'hello-app'; shutil.copytree(ROOT / 'examples/native-hello', source)
        (source / 'apps').mkdir()
        with zipfile.ZipFile(source / 'apps/HelloApp.sapp', 'w') as sapp:
            sapp.writestr('app.json', json.dumps({'id': 'me.example.hello-app', 'name': 'Hello App', 'version': '1.0', 'build': 1}))
            sapp.writestr('main.js', 'UIApplication.run(new UIViewController({ title: "Hello" }));\n')
        manifest = json.loads((source / 'manifest.json').read_text())
        manifest.update(id='me.example.hello-with-app', apps=['apps/HelloApp.sapp'])
        (source / 'manifest.json').write_text(json.dumps(manifest, indent=2))
        built = base / 'hello-with-app.springys'
        subprocess.run([sys.executable, str(HERE / 'build.py'), 'package', str(source), str(built),
                        '--sdk', str(core / 'winterx-native-api.jar'), '--spring-api', str(core / 'spring-api.jar')], check=True, stdout=subprocess.DEVNULL)
        apps_root = base / 'apps'; (apps_root / APP / 'imports').mkdir(parents=True); apps_inbox = base / 'apps-inbox'; apps_inbox.mkdir()
        shutil.copy2(built, apps_root / APP / 'imports' / built.name)
        jvm(apps_root, apps_inbox, 'apps', built.name, 'me.example.hello-app', 'me.example.hello-with-app')
    print('In-process package manager checks passed')


if __name__ == '__main__':
    main()
