#!/usr/bin/env python3
"""Build an isolated Spring 0.8.1 free-icon test APK, without installing it."""
import argparse
import errno
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE_HASH = 'f07f980fe681a6de9c4ce8735ae1c0bb0f852f447fbdb925d2dec37cf9778e5c'
FRAMEWORK = Path('/Applications/Mac.apk.app/Contents/lib/android-framework.jar')
JAVAC = Path('/opt/homebrew/opt/openjdk/bin/javac')
JAR = Path('/opt/homebrew/opt/openjdk/bin/jar')
JAVA = Path('/opt/homebrew/opt/openjdk/bin/java')
BOOT_LOGO = ROOT / 'patches/appearance/winterx-boot.webp'
BOOT_RESOURCES = frozenset(('res/DX.webp', 'res/WM.webp'))
D8 = Path.home() / 'Library/Android/sdk/build-tools/36.0.0/lib/d8.jar'
CONVERTER_JAVA = Path.home() / 'Library/Application Support/Mac.apk/runtime/Resources/jre/bin/java'
CONVERTER = Path('/Applications/Mac.apk.app/Contents/lib/macapk-loader.jar')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()


def run(*args):
    subprocess.run([str(x) for x in args], check=True)


def signature(name):
    name = name.upper()
    if not name.startswith('META-INF/'):
        return False
    tail = name[len('META-INF/'):]
    return '/' not in tail and (tail == 'MANIFEST.MF' or tail.endswith(('.SF', '.RSA', '.DSA', '.EC')))


def decode_input(source, output):
    """Decode only bytecode/metadata; assembly below copies real resources from stock."""
    required = ('AndroidManifest.xml', 'resources.arsc', 'classes.dex', 'classes2.dex')
    with zipfile.ZipFile(source) as stock, zipfile.ZipFile(output, 'x') as out:
        for name in required:
            info = stock.getinfo(name)
            with stock.open(info) as src, out.open(info, 'w') as dst:
                shutil.copyfileobj(src, dst, 1024 * 1024)


def publish_output(source, output):
    """Exclusive creation, without another full APK copy on the same filesystem."""
    try:
        os.link(source, output)
    except OSError as failure:
        if failure.errno not in (errno.EXDEV, errno.ENOTSUP, errno.EPERM): raise
        with source.open('rb') as src, output.open('xb') as dst: shutil.copyfileobj(src, dst)


def build(source, output):
    source = Path(source).resolve(strict=True)
    output = Path(output).resolve()
    if source == output or output.exists(): raise ValueError('Output must be a new file')
    if digest(source) != SOURCE_HASH: raise ValueError('Unsupported Spring APK')
    with tempfile.TemporaryDirectory(prefix='winterx-icon-build-') as name:
        temp = Path(name)
        original_jar = temp / 'spring.jar'
        run(CONVERTER_JAVA, '-Xmx2g', '-cp', CONVERTER, 'com.macapk.dex.Main',
            '--classpath', FRAMEWORK, '--threads', '6', source, original_jar)
        classes = temp / 'classes'; classes.mkdir()
        sources = sorted((HERE / 'src').rglob('*.java'))
        run(JAVAC, '--release', '8', '-cp', str(original_jar) + ':' + str(FRAMEWORK), '-d', classes, *sources)
        helpers = temp / 'helpers.jar'
        run(JAR, 'cf', helpers, '-C', classes, 'winterx')
        ssh_library = os.environ.get('WINTERX_SSH_LIBRARY')
        if ssh_library:
            # Development-only library from patches/ssh/build.py; never selected or installed here.
            with zipfile.ZipFile(ssh_library) as library, zipfile.ZipFile(helpers, 'a') as merged:
                existing = set(merged.namelist())
                for info in library.infolist():
                    if info.is_dir() or info.filename.startswith('META-INF/'):
                        continue
                    if info.filename in existing: raise ValueError('Duplicate optional SSH class/resource: ' + info.filename)
                    merged.writestr(info, library.read(info.filename)); existing.add(info.filename)
        dex_dir = temp / 'dex'; dex_dir.mkdir()
        run(JAVA, '-Xmx1g', '-cp', D8, 'com.android.tools.r8.D8', '--min-api', '24',
            '--classpath', original_jar, '--lib', FRAMEWORK, '--output', dex_dir, helpers)
        helper_dex = (dex_dir / 'classes.dex').read_bytes()
        decoded = temp / 'decoded'
        decode_source = temp / 'decode-input.apk'
        decode_input(source, decode_source)
        run('apktool', 'd', '--no-res', '-f', '-o', decoded, decode_source)
        run('python3', ROOT / 'patches/settings_test.py', decoded)
        run('python3', HERE / 'patch_smali.py', decoded)
        rebuilt = temp / 'rebuilt.apk'
        run('apktool', 'b', decoded, '-o', rebuilt)
        with zipfile.ZipFile(rebuilt) as apk: primary = apk.read('classes.dex')
        if b'winterx/layout/SpringHooks' not in primary or b'winterx/layout/SpringHooks' not in helper_dex:
            raise ValueError('Free-icon hooks missing from build')
        assembled = temp / 'assembled.apk'
        with zipfile.ZipFile(source) as stock, zipfile.ZipFile(assembled, 'x', allowZip64=True) as out:
            if 'classes3.dex' in stock.namelist(): raise ValueError('Unexpected third stock DEX')
            for info in stock.infolist():
                if signature(info.filename): continue
                if info.filename == 'classes.dex': out.writestr(info, primary)
                elif info.filename in BOOT_RESOURCES: out.writestr(info, BOOT_LOGO.read_bytes())
                else:
                    with stock.open(info) as src, out.open(info, 'w') as dst: shutil.copyfileobj(src, dst, 1024 * 1024)
            out.writestr('classes3.dex', helper_dex, compress_type=zipfile.ZIP_DEFLATED)
            if ssh_library:
                with zipfile.ZipFile(ssh_library) as library:
                    for name in library.namelist():
                        if not name.endswith(('.class', '/')) and not name.startswith('META-INF/'):
                            target = 'winterx-ssh/' + name if name.startswith('licenses/') else name
                            if target in out.namelist() or '..' in target.split('/') or target.startswith('/'):
                                raise ValueError('Unsafe/duplicate optional SSH resource: ' + target)
                            out.writestr(target, library.read(name))
        with zipfile.ZipFile(source) as stock, zipfile.ZipFile(assembled) as result:
            before = {i.filename: (i.CRC, i.file_size) for i in stock.infolist() if not signature(i.filename) and i.filename != 'classes.dex' and i.filename not in BOOT_RESOURCES}
            extra = set(result.namelist()) - set(stock.namelist()) - {'classes3.dex'} if ssh_library else set()
            after = {i.filename: (i.CRC, i.file_size) for i in result.infolist() if i.filename not in ('classes.dex', 'classes3.dex') and i.filename not in BOOT_RESOURCES and i.filename not in extra}
            if before != after: raise ValueError('Unexpected modification to stock APK resources')
            for name in BOOT_RESOURCES:
                if result.read(name) != BOOT_LOGO.read_bytes(): raise ValueError('Boot logo was not installed')
        output.parent.mkdir(parents=True, exist_ok=True)
        publish_output(assembled, output)
    print('Built isolated test APK:', output)
    print('SHA-256:', digest(output))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    build(args.source, args.output)
