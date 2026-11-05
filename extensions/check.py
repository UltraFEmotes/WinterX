#!/usr/bin/env python3
"""Verify a core-only engine and Ruby-installed code packages in disposable JVM application roots."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import ruby_packages

FRAMEWORK = Path('/Applications/Mac.apk.app/Contents/lib/android-framework.jar')
JAVA = Path.home() / 'Library/Application Support/Mac.apk/runtime/Resources/jre/bin/java'
JAVAC = Path('/opt/homebrew/opt/openjdk/bin/javac')


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('jar', type=Path); parser.add_argument('packages', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='winterx-code-package-check-') as name:
        base = Path(name).resolve(); classes = base / 'classes'; classes.mkdir()
        cp = str(args.jar.resolve(strict=True)) + ':' + str(FRAMEWORK)
        sources = [ROOT / 'patches/tests/android/app/Application.java', ROOT / 'patches/tests/android/app/ActivityThread.java',
                   ROOT / 'patches/icon_positions/test/android/util/Log.java', ROOT / 'extensions/tests/NativePackagesCheck.java',
                   ROOT / 'extensions/tests/NativeLifecycleCheck.java', ROOT / 'extensions/tests/MethodHooksCheck.java']
        subprocess.run([str(JAVAC), '--release', '21', '-cp', cp, '-d', str(classes), *map(str, sources)], check=True)
        for installed in (False, True):
            for variant in (False, True):
                root = base / ('installed-' + str(installed) + '-' + str(variant)); root.mkdir()
                if installed:
                    app = root / 'sapps-data/com.ruby.manager/files'; (app / 'imports').mkdir(parents=True)
                    packages = ruby_packages.Packages(app, root / 'ruby/settings-test.enabled', lambda enabled: None,
                        tweak_root=root / 'winterx-tweaks', supported_tweaks=True, supported_native=True, supported_capabilities=('native.hooks',))
                    for archive in sorted(args.packages.glob('*.springys')):
                        shutil.copy2(archive, app / 'imports' / archive.name); packages.install(archive.name)
                    if len(packages.registry.list()) != 7: raise RuntimeError('Expected seven independently installed Ruby packages')
                subprocess.run([str(JAVA), '-Xverify:all', '-Druby.test.dir=' + str(root), '-cp', str(classes) + ':' + cp,
                                'NativePackagesCheck', str(installed).lower(), str(variant).lower()], check=True)
        probe = base / 'probe'; probe.mkdir()
        subprocess.run([str(JAVAC), '--release', '8', '-cp', cp, '-d', str(probe),
                        str(ROOT / 'extensions/tests/probe/Probe.java')], check=True)
        archive = base / 'probe.jar'
        with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as output:
            for path in probe.rglob('*.class'): output.write(path, path.relative_to(probe).as_posix())
        for scenario in ('dependencies', 'missing', 'cycle', 'safe', 'bad-start', 'bad-call', 'bad-type', 'integrity'):
            root = base / scenario; root.mkdir()
            subprocess.run([str(JAVA), '-Xverify:all', '-cp', str(classes) + ':' + cp,
                            'NativeLifecycleCheck', str(root), str(archive), scenario], check=True)
        hooks = base / 'hook-probe'; hooks.mkdir()
        subprocess.run([str(JAVAC), '--release', '8', '-cp', cp, '-d', str(hooks),
                        str(ROOT / 'extensions/tests/hooks/HookProbe.java')], check=True)
        hook_archive = base / 'hook-probe.jar'
        with zipfile.ZipFile(hook_archive, 'x', zipfile.ZIP_DEFLATED) as output:
            for path in hooks.rglob('*.class'): output.write(path, path.relative_to(hooks).as_posix())
        for scenario in ('hooks', 'safe'):
            root = base / ('method-' + scenario); root.mkdir()
            subprocess.run([str(JAVA), '-Xverify:all', '-cp', str(classes) + ':' + cp,
                            'MethodHooksCheck', str(root), str(hook_archive), scenario], check=True)


if __name__ == '__main__': main()
