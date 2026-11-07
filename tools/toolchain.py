"""Find the build and device tools on macOS, Linux and Windows.

Every value can be overridden with an environment variable, so any layout works:

  WINTERX_JDK          JDK folder (default: $JAVA_HOME, then javac on PATH, then Homebrew's OpenJDK)
  ANDROID_HOME         Android SDK (also ANDROID_SDK_ROOT; default: the usual SDK folder for this OS)
  WINTERX_ANDROID_JAR  android.jar to compile against (default: newest platforms/android-*/android.jar,
                       or Mac.APK's framework when Mac.APK is installed)
  WINTERX_D8           d8.jar (default: newest build-tools/*/lib/d8.jar)
  WINTERX_APKTOOL      apktool command or apktool .jar (default: apktool on PATH)
  WINTERX_DEX2JAR      dex2jar's d2j-dex2jar script (default: on PATH; used when Mac.APK isn't installed)
  WINTERX_MACAPK       Mac.APK.app folder (macOS only; enables Mac.APK's converter and JVM checks)
  WINTERX_APKSIGNER, WINTERX_ZIPALIGN, WINTERX_AAPT2
                       Android build-tools for the rootless clone (default: newest build-tools/*/)
"""
import os
from pathlib import Path
import platform
import shutil
import sys

WINDOWS = os.name == 'nt'
MACOS = sys.platform == 'darwin'
EXE = '.exe' if WINDOWS else ''


def _env_path(name):
    value = os.environ.get(name)
    return Path(value).expanduser() if value else None


def _version_key(path):
    parts = []
    for piece in path.name.replace('android-', '').replace('-', '.').split('.'):
        parts.append(int(piece) if piece.isdigit() else -1)
    return parts


def jdk_tool(name):
    """java, javac or jar from the configured JDK."""
    for base in (_env_path('WINTERX_JDK'), _env_path('JAVA_HOME')):
        if base and (base / 'bin' / (name + EXE)).exists(): return base / 'bin' / (name + EXE)
    found = shutil.which(name)
    if found and not (MACOS and found == '/usr/bin/' + name):  # macOS's stub asks to install Java
        return Path(found)
    for base in (Path('/opt/homebrew/opt/openjdk'), Path('/usr/local/opt/openjdk')):
        if (base / 'bin' / name).exists(): return base / 'bin' / name
    raise SystemExit('Java %s not found: install a JDK (17 or newer) and set JAVA_HOME or WINTERX_JDK.' % name)


def android_sdk():
    for name in ('ANDROID_HOME', 'ANDROID_SDK_ROOT'):
        value = _env_path(name)
        if value and value.is_dir(): return value
    home = Path.home()
    candidates = [home / 'Library/Android/sdk'] if MACOS else []
    if WINDOWS: candidates.append(Path(os.environ.get('LOCALAPPDATA', home / 'AppData/Local')) / 'Android/Sdk')
    candidates += [home / 'Android/Sdk', home / 'Android/sdk']
    for candidate in candidates:
        if candidate.is_dir(): return candidate
    raise SystemExit('Android SDK not found: install it (Android Studio or the command-line tools) and set ANDROID_HOME.')


def _newest(paths):
    paths = [path for path in paths if path.exists()]
    return max(paths, key=lambda path: _version_key(path.parent if path.name.endswith('.jar') else path)) if paths else None


def macapk():
    """Mac.APK's app folder when installed (macOS only)."""
    value = _env_path('WINTERX_MACAPK') or (Path('/Applications/Mac.apk.app') if MACOS else None)
    return value if value and (value / 'Contents/lib/macapk-loader.jar').exists() else None


def android_jar():
    """Classes to compile Android code against: Mac.APK's framework, or the SDK's android.jar."""
    explicit = _env_path('WINTERX_ANDROID_JAR')
    if explicit: return explicit
    app = macapk()
    if app and (app / 'Contents/lib/android-framework.jar').exists(): return app / 'Contents/lib/android-framework.jar'
    found = _newest(list((android_sdk() / 'platforms').glob('android-*/android.jar')))
    if found: return found
    raise SystemExit('No android.jar found: run "sdkmanager \\"platforms;android-34\\"" or set WINTERX_ANDROID_JAR.')


def d8():
    explicit = _env_path('WINTERX_D8')
    if explicit: return explicit
    found = _newest(list((android_sdk() / 'build-tools').glob('*/lib/d8.jar')))
    if found: return found
    raise SystemExit('d8 not found: run "sdkmanager \\"build-tools;36.0.0\\"" or set WINTERX_D8.')


def build_tool(name):
    """apksigner, zipalign or aapt2 from the newest Android build-tools."""
    explicit = _env_path('WINTERX_' + name.upper())
    if explicit: return explicit
    suffix = '.bat' if WINDOWS and name == 'apksigner' else EXE
    found = _newest(list((android_sdk() / 'build-tools').glob('*/' + name + suffix)))
    if found: return found
    raise SystemExit('%s not found: run "sdkmanager \\"build-tools;36.0.0\\"" or set WINTERX_%s.' % (name, name.upper()))


def adb():
    found = shutil.which('adb')
    if found: return Path(found)
    path = android_sdk() / 'platform-tools' / ('adb' + EXE)
    if path.exists(): return path
    raise SystemExit('adb not found: run "sdkmanager platform-tools" or put adb on PATH.')


def apktool():
    """apktool as a command list."""
    explicit = os.environ.get('WINTERX_APKTOOL')
    if explicit:
        return [str(jdk_tool('java')), '-jar', explicit] if explicit.endswith('.jar') else [explicit]
    for name in (('apktool.bat', 'apktool') if WINDOWS else ('apktool',)):
        found = shutil.which(name)
        if found: return [found]
    raise SystemExit('apktool not found: install it (https://apktool.org) or set WINTERX_APKTOOL to its .jar.')


def dex_to_jar(apk, output):
    """Turn Spring's DEX into JVM classes for compiling against (and, with Mac.APK, for running JVM checks)."""
    import subprocess
    app = macapk()
    if app:
        java = Path.home() / 'Library/Application Support/Mac.apk/runtime/Resources/jre/bin/java'
        subprocess.run([str(java if java.exists() else jdk_tool('java')), '-Xmx3g', '-cp', str(app / 'Contents/lib/macapk-loader.jar'),
                        'com.macapk.dex.Main', '--classpath', str(android_jar()), '--threads', '6', str(apk), str(output)], check=True)
        return
    explicit = os.environ.get('WINTERX_DEX2JAR')
    names = [explicit] if explicit else (['d2j-dex2jar.bat'] if WINDOWS else ['d2j-dex2jar.sh', 'd2j-dex2jar'])
    for name in names:
        found = name if name and Path(name).exists() else shutil.which(name or '')
        if found:
            subprocess.run([found, '--force', '-o', str(output), str(apk)], check=True)
            return
    raise SystemExit('No DEX-to-JAR converter: install dex2jar (https://github.com/pxb1988/dex2jar) and set WINTERX_DEX2JAR to d2j-dex2jar.')


def describe():
    """Human-readable summary for `python3 tools/toolchain.py`."""
    rows = []
    for label, finder in (('java', lambda: jdk_tool('java')), ('javac', lambda: jdk_tool('javac')), ('Android SDK', android_sdk),
                          ('android.jar', android_jar), ('d8', d8), ('adb', adb), ('apktool', lambda: ' '.join(apktool())),
                          ('apksigner', lambda: build_tool('apksigner')), ('zipalign', lambda: build_tool('zipalign')),
                          ('keytool', lambda: jdk_tool('keytool')),
                          ('Mac.APK', lambda: macapk() or 'not installed (fine on Linux/Windows)')):
        try: rows.append((label, str(finder())))
        except SystemExit as missing: rows.append((label, 'MISSING: ' + str(missing)))
    converter = 'Mac.APK' if macapk() else (os.environ.get('WINTERX_DEX2JAR') or shutil.which('d2j-dex2jar') or shutil.which('d2j-dex2jar.sh') or 'MISSING: install dex2jar')
    rows.append(('DEX→JAR', str(converter)))
    width = max(len(label) for label, _ in rows)
    return '%s %s\n' % (platform.system(), platform.machine()) + '\n'.join('%s  %s' % (label.ljust(width), value) for label, value in rows)


if __name__ == '__main__':
    print(describe())
