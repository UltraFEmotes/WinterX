#!/usr/bin/env python3
"""Check a Mac.APK-converted patched JAR without launching a Spring window."""
import argparse
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
FRAMEWORK = Path('/Applications/Mac.apk.app/Contents/lib/android-framework.jar')
JAVA = Path.home() / 'Library/Application Support/Mac.apk/runtime/Resources/jre/bin/java'
JAVAC = Path('/opt/homebrew/opt/openjdk/bin/javac')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('jar', type=Path, help='Mac.APK dex2jvm output for the patched APK')
    a = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='ruby-hook-test-') as scratch:
        root = Path(scratch)
        classes = root / 'classes'
        classes.mkdir()
        sources = [HERE / 'android/app/Application.java', HERE / 'android/app/ActivityThread.java',
                   HERE / 'android/app/Activity.java', HERE / 'RubyHooksCheck.java']
        subprocess.run([str(JAVAC), '--release', '21', '-cp', str(FRAMEWORK), '-d', str(classes),
                        *(str(source) for source in sources)], check=True)
        for setting, safe in ((False, False), (True, False), (True, True)):
            enabled = setting and not safe
            data = root / ('setting-' + str(setting) + '-safe-' + str(safe))
            data.mkdir()
            if setting or safe:
                (data / 'ruby').mkdir()
            if setting:
                (data / 'ruby/settings-test.enabled').touch()
            if safe:
                (data / 'ruby/safe-mode.enabled').touch()
            cp = ':'.join((str(classes), str(a.jar.resolve(strict=True)), str(FRAMEWORK)))
            subprocess.run([str(JAVA), '-Druby.test.dir=' + str(data), '-cp', cp, 'RubyHooksCheck',
                            str(enabled).lower(), str(safe).lower()], check=True)
        welcome_classes = root / 'welcome-classes'
        welcome_classes.mkdir()
        welcome_sources = [HERE / 'android/app/Activity.java',
                           HERE / 'welcome/com/guille/spring/LauncherActivity.java',
                           HERE / 'welcome/x1/J.java', HERE / 'welcome/x1/H.java',
                           HERE / 'welcome/WelcomeCheck.java']
        compile_cp = ':'.join((str(a.jar.resolve(strict=True)), str(FRAMEWORK)))
        subprocess.run([str(JAVAC), '--release', '21', '-cp', compile_cp, '-d', str(welcome_classes),
                        *(str(source) for source in welcome_sources)], check=True)
        data = root / 'welcome-data'
        (data / 'ruby').mkdir(parents=True)
        cp = ':'.join((str(welcome_classes), str(a.jar.resolve(strict=True)), str(FRAMEWORK)))
        subprocess.run([str(JAVA), '-Druby.test.dir=' + str(data), '-cp', cp, 'WelcomeCheck'], check=True)
        protection = root / 'protection-classes'
        protection.mkdir()
        subprocess.run([str(JAVAC), '--release', '21', '-d', str(protection),
                        str(HERE / 'RubyProtectionCheck.java')], check=True)
        cp = ':'.join((str(protection), str(a.jar.resolve(strict=True)), str(FRAMEWORK)))
        subprocess.run([str(JAVA), '-cp', cp, 'RubyProtectionCheck'], check=True)
        boot_classes = root / 'boot-classes'
        boot_classes.mkdir()
        boot_sources = [HERE / 'boot/android/content/Context.java', HERE / 'boot/android/view/ViewParent.java',
                        HERE / 'boot/android/view/View.java', HERE / 'boot/android/view/ViewGroup.java',
                        HERE / 'boot/android/widget/TextView.java', HERE / 'boot/android/app/Activity.java',
                        HERE / 'boot/BootCheck.java']
        subprocess.run([str(JAVAC), '--release', '21', '-cp', compile_cp, '-d', str(boot_classes),
                        *(str(source) for source in boot_sources)], check=True)
        cp = ':'.join((str(boot_classes), str(a.jar.resolve(strict=True)), str(FRAMEWORK)))
        subprocess.run([str(JAVA), '-cp', cp, 'BootCheck'], check=True)
        tint_classes = root / 'tint-classes'
        tint_classes.mkdir()
        tint_sources = sorted((HERE / 'tint').rglob('*.java'))
        subprocess.run([str(JAVAC), '--release', '21', '-cp', compile_cp, '-d', str(tint_classes),
                        *(str(source) for source in tint_sources)], check=True)
        tint_data = root / 'tint-data'
        tint_data.mkdir()
        cp = ':'.join((str(tint_classes), str(a.jar.resolve(strict=True)), str(FRAMEWORK)))
        subprocess.run([str(JAVA), '-Druby.test.dir=' + str(tint_data), '-cp', cp, 'TintCheck'], check=True)


if __name__ == '__main__':
    main()
