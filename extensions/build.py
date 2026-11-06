#!/usr/bin/env python3
"""Build a core-only engine/Android injection payload, or independent source-backed code packages."""
import argparse
import base64
import hashlib
import importlib.util
import json
import re
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'tools'))
import native_package
import toolchain
import generate
import method_hooks

spec = importlib.util.spec_from_file_location('legacy_build', ROOT / 'patches/icon_positions/build.py')
legacy = importlib.util.module_from_spec(spec); spec.loader.exec_module(legacy)
FORBIDDEN = ('Lwinterx/animaper/', 'Lwinterx/coloredbar/', 'Lwinterx/layout/', 'Lwinterx/snowy/', 'Lwinterx/ssh/', 'Lwinterx/messages/', 'Lwinterx/packages/', 'Lorg/apache/sshd/')


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compile_path(*extra):
    """android.jar plus, when it's the public SDK one, stubs for the few hidden Android APIs WinterX code uses."""
    paths = [toolchain.android_jar(), *extra]
    if not toolchain.macapk() and not os.environ.get('WINTERX_ANDROID_JAR'):
        stubs = Path(tempfile.mkdtemp(prefix='winterx-stubs-'))
        run(toolchain.jdk_tool('javac'), '--release', '8', '-cp', toolchain.android_jar(), '-d', stubs,
            *sorted((HERE / 'stubs').rglob('*.java')))
        paths.append(stubs)
    return os.pathsep.join(map(str, paths))
def run(*command, env=None): subprocess.run(list(map(str, command)), check=True, env=env)


def dex_classes(raw):
    if len(raw) < 112 or raw[:4] != b'dex\n': raise ValueError('Invalid DEX')
    string_count, strings, type_count, types = struct.unpack_from('<IIII', raw, 56)
    class_count, classes = struct.unpack_from('<II', raw, 96)
    if any(value > len(raw) for value in (strings + 4 * string_count, types + 4 * type_count, classes + 32 * class_count)):
        raise ValueError('Invalid DEX tables')
    result = []
    for index in range(class_count):
        type_index = struct.unpack_from('<I', raw, classes + index * 32)[0]
        string_index = struct.unpack_from('<I', raw, types + type_index * 4)[0]
        offset = struct.unpack_from('<I', raw, strings + string_index * 4)[0]
        for _ in range(5):
            value = raw[offset]; offset += 1
            if value < 128: break
        end = raw.index(0, offset)
        result.append(raw[offset:end].decode('ascii'))
    return result


def class_jar(classes, output, libraries=()):
    entries = {path.relative_to(classes).as_posix(): path.read_bytes() for path in classes.rglob('*.class')}
    for library in libraries:
        with zipfile.ZipFile(library) as archive:
            for info in archive.infolist():
                if info.is_dir() or info.filename.startswith('META-INF/') or info.filename.startswith('winterx/') or info.filename.endswith('module-info.class'): continue
                if info.filename in entries: raise ValueError('Duplicate dependency class/resource: ' + info.filename)
                entries[info.filename] = archive.read(info.filename)
    with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name, value in sorted(entries.items()):
            info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED; info.external_attr = 0o100644 << 16
            archive.writestr(info, value)


BOOT_OVERLAY = 'smali/x1.1/R1.smali'
BOOT_CALLS = ('invoke-virtual {v0, v1}, Landroid/widget/ImageView;->setImageResource(I)V',
              'invoke-virtual {v2, p1}, Landroid/widget/ImageView;->setImageResource(I)V')


def boot_art(decoded):
    """Route only the boot overlay's two drawables through BootArt; rooted mode cannot replace APK resources."""
    path = decoded / BOOT_OVERLAY; text = path.read_text()
    for call in BOOT_CALLS:
        if text.count(call) != 1: raise ValueError('Unexpected Spring boot overlay: ' + call)
        registers = call[call.index('{'):call.index('}') + 1]
        text = text.replace(call, 'invoke-static ' + registers + ', Lwinterx/appearance/BootArt;->apply(Landroid/widget/ImageView;I)V', 1)
    path.write_text(text)


def runtime(apk, destination):
    apk = Path(apk).resolve(strict=True); destination = Path(destination).resolve()
    if destination.exists(): raise ValueError('Runtime output must be a new directory')
    if sha(apk) != legacy.SOURCE_HASH: raise ValueError('Unsupported Spring input APK')
    destination.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='winterx-core-build-') as directory:
        work = Path(directory)
        api = destination / 'spring-api.jar'
        toolchain.dex_to_jar(apk, api)
        decode_input = work / 'input.apk'; legacy.decode_input(apk, decode_input)
        decoded = work / 'decoded'; run(*toolchain.apktool(), 'd', '--no-res', '-o', decoded, decode_input)
        env = dict(os.environ)
        for flag in ('ANIMAPER', 'TRUSTED_FILES', 'INBOX', 'SNOWYHOME', 'MESSAGEPLUS', 'SSH_ACTIONS'): env['WINTERX_BUILD_' + flag] = '1'
        run(sys.executable, ROOT / 'patches/settings_test.py', decoded, env=env)
        run(sys.executable, ROOT / 'patches/icon_positions/patch_smali.py', decoded, env=env)
        boot_art(decoded)
        generated = work / 'generated'; contracts = generate.generate(decoded, generated)
        art = generated / 'winterx/appearance'; art.mkdir(parents=True, exist_ok=True)
        # Last smali change: every Spring method gets its hook check (see method_hooks.py).
        hookable = method_hooks.instrument(decoded)
        (generated / 'winterx/extension').mkdir(parents=True, exist_ok=True)
        (generated / 'winterx/extension/MethodTable.java').write_text(method_hooks.table_source(hookable))
        (destination / 'hookable-methods.txt').write_text('\n'.join(hookable) + '\n')
        (art / 'BootArtData.java').write_text('package winterx.appearance;\n\nfinal class BootArtData {\n    static final String WEBP = "' +
            base64.b64encode(legacy.BOOT_LOGO.read_bytes()).decode('ascii') + '";\n    private BootArtData() {}\n}\n')
        shutil.copy2(generated / 'native-api.json', destination / 'native-api.json')
        classes = work / 'classes'; classes.mkdir()
        sources = sorted((HERE / 'runtime/src').rglob('*.java')) + sorted(generated.rglob('*.java'))
        run(toolchain.jdk_tool('javac'), '--release', '8', '-cp', compile_path(api), '-d', classes, *sources)
        sdk = destination / 'winterx-native-api.jar'; class_jar(classes, sdk)
        dex = work / 'runtime-dex'; dex.mkdir()
        run(toolchain.jdk_tool('java'), '-Xmx1g', '-cp', toolchain.d8(), 'com.android.tools.r8.D8', '--min-api', '26', '--classpath', api, '--lib', toolchain.android_jar(), '--output', dex, sdk)
        runtime_dex = (dex / 'classes.dex').read_bytes()
        defined = dex_classes(runtime_dex)
        forbidden = [name for name in defined if name.startswith(FORBIDDEN)]
        if forbidden: raise ValueError('Tweak implementation leaked into core runtime: ' + repr(forbidden))
        for path in (decoded / 'smali').rglob('*.smali'):
            text = path.read_text()
            if any(prefix in text for prefix in FORBIDDEN): raise ValueError('Native engine still links a bundled tweak: ' + str(path))
        rebuilt = work / 'rebuilt.apk'; run(*toolchain.apktool(), 'b', decoded, '-o', rebuilt)
        with zipfile.ZipFile(rebuilt) as archive: primary = archive.read('classes.dex')
        engine = destination / 'WinterX-core-0.8.1.apk'
        with zipfile.ZipFile(apk) as original, zipfile.ZipFile(engine, 'x', allowZip64=True) as output:
            for info in original.infolist():
                if legacy.signature(info.filename): continue
                if info.filename == 'classes.dex': output.writestr(info, primary)
                elif info.filename in legacy.BOOT_RESOURCES: output.writestr(info, legacy.BOOT_LOGO.read_bytes())
                else:
                    with original.open(info) as src, output.open(info, 'w') as dst: shutil.copyfileobj(src, dst, 1024 * 1024)
            output.writestr('classes3.dex', runtime_dex, compress_type=zipfile.ZIP_DEFLATED)
        payload = destination / 'android-runtime'; payload.mkdir()
        (payload / 'spring-hooks.dex').write_bytes(primary); (payload / 'winterx-core.dex').write_bytes(runtime_dex)
        manifest = {'format': 'winterx.android-runtime/1', 'package': 'com.guille.spring', 'springVersion': '0.8.1',
            'sourceApkSha256': legacy.SOURCE_HASH, 'minimumApi': 26, 'runtimeAbi': 'winterx-native-hooks-v1',
            'files': {name: sha(payload / name) for name in ('spring-hooks.dex', 'winterx-core.dex')},
            'preinstalledTweaks': [], 'earlyClasses': ['com.guille.spring.LauncherActivity', 'x1.i1', 'I1.h0', 'I1.T0', 'I1.Y', 'A.o']}
        (payload / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        audit = {'apk': str(engine), 'apk_sha256': sha(engine), 'core_classes': defined, 'bundled_tweak_classes': forbidden,
                 'preinstalled_tweaks': [], 'hook_contracts': len(contracts), 'runtime_dex_sha256': sha(payload / 'winterx-core.dex')}
        (destination / 'core-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps(audit, indent=2))


# Other Spring versions: built from the 0.8.1 patches through a name map (tools/spring_map.py, patches/port.py).
VERSIONS = {
    'c500d2f7316c36e3f97fb65bda7178445513630d132f711fe80bfc79a7a16cb6': {
        'name': '0.9-preview1', 'map': ROOT / 'tools/spring-maps/0.8.1-to-0.9p1.json',
        'hand': 'port09', 'skip': '', 'boot_overlay': 'r1/F2',
        'contracts': ROOT / 'tools/spring-maps/0.9p1-contracts.json'},
}
GENERATED = ('winterx/extension/NativeHooks', 'winterx/extension/MethodTable', 'winterx/appearance/BootArtData', 'winterx/runtime/SpringVersionData')


def runtime_version(apk, destination, base):
    """A core for another Spring version. base: a finished 0.8.1 core build (its spring-api.jar compiles the runtime,
    which is then translated). The patches, hook tables and method table come from this version's own code."""
    import spring_translate, spring_verify
    apk = Path(apk).resolve(strict=True); destination = Path(destination).resolve(); base = Path(base).resolve(strict=True)
    version = VERSIONS.get(sha(apk))
    if version is None: raise ValueError('Unsupported Spring input APK')
    if destination.exists(): raise ValueError('Runtime output must be a new directory')
    mapping = json.loads(version['map'].read_text())
    translator_classes = mapping['classes']
    destination.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='winterx-core-build-') as directory:
        work = Path(directory)
        api = destination / 'spring-api.jar'; toolchain.dex_to_jar(apk, api)
        decode_input = work / 'input.apk'; legacy.decode_input(apk, decode_input)
        decoded = work / 'decoded'; run(*toolchain.apktool(), 'd', '--no-res', '-o', decoded, decode_input)
        env = dict(os.environ)
        for flag in ('ANIMAPER', 'TRUSTED_FILES', 'INBOX', 'SNOWYHOME', 'MESSAGEPLUS', 'SSH_ACTIONS'): env['WINTERX_BUILD_' + flag] = '1'
        report = destination / 'port-report.json'
        # --survey: anchors the version's hand-port module covers are expected to miss; anything else fails below.
        run(sys.executable, ROOT / 'patches/port.py', version['map'], decoded, '--survey', '--hand', version['hand'],
            *(('--skip', version['skip']) if version['skip'] else ()), '--report', report, env=env)
        left = [f for f in json.loads(report.read_text())['failures'] if not f['error'].startswith(('info:', 'skipped'))]
        if left: raise ValueError('Patches that did not port: ' + json.dumps(left, indent=1))
        unresolved = spring_verify.problems(str(decoded))
        if unresolved: raise ValueError('Inserted code references names this Spring lacks: ' + json.dumps({k: sorted(v) for k, v in unresolved.items()}, indent=1))
        overlay = next(p for p in (decoded / 'smali').rglob('*.smali') if re.search(r'^\.class [^\n]* L' + re.escape(version['boot_overlay']) + ';', p.read_text(errors='ignore'), re.M))
        global BOOT_OVERLAY
        saved, BOOT_OVERLAY = BOOT_OVERLAY, str(overlay.relative_to(decoded))
        try: boot_art(decoded)
        finally: BOOT_OVERLAY = saved
        generated = work / 'generated'; contracts = generate.generate(decoded, generated, json.loads(version['contracts'].read_text()))
        art = generated / 'winterx/appearance'; art.mkdir(parents=True, exist_ok=True)
        hookable = method_hooks.instrument(decoded)
        (generated / 'winterx/extension').mkdir(parents=True, exist_ok=True)
        (generated / 'winterx/extension/MethodTable.java').write_text(method_hooks.table_source(hookable))
        (destination / 'hookable-methods.txt').write_text('\n'.join(hookable) + '\n')
        (art / 'BootArtData.java').write_text('package winterx.appearance;\n\nfinal class BootArtData {\n    static final String WEBP = "' +
            base64.b64encode(legacy.BOOT_LOGO.read_bytes()).decode('ascii') + '";\n    private BootArtData() {}\n}\n')
        shutil.copy2(generated / 'native-api.json', destination / 'native-api.json')
        (generated / 'winterx/runtime').mkdir(parents=True, exist_ok=True)
        (generated / 'winterx/runtime/SpringVersionData.java').write_text('package winterx.runtime;\n\n/** Generated: the Spring version this core was built for. */\n'
            'public final class SpringVersionData {\n    public static final String VALUE = "%s";\n    private SpringVersionData() {}\n}\n' % version['name'])
        # What this Spring declares, for checking tweaks translated to it (build.py package --version-core).
        import gzip
        index = {cls: [sorted(members), parent] for cls, (members, parent) in spring_translate.declared(str(decoded)).items()}
        with gzip.open(destination / 'spring-declared.json.gz', 'wt') as out: json.dump({'version': version['name'], 'classes': index}, out)
        # The runtime is written against 0.8.1: compile it there (base's generated classes only as classpath), then translate.
        classes = work / 'classes'; classes.mkdir()
        run(toolchain.jdk_tool('javac'), '--release', '8', '-cp', compile_path(base / 'spring-api.jar', base / 'winterx-native-api.jar'),
            '-d', classes, *sorted((HERE / 'runtime/src').rglob('*.java')))
        runtime_jar = work / 'runtime.jar'; class_jar(classes, runtime_jar)
        dex_a = work / 'dex-a'; dex_a.mkdir()
        run(toolchain.jdk_tool('java'), '-Xmx1g', '-cp', toolchain.d8(), 'com.android.tools.r8.D8', '--min-api', '26',
            '--classpath', base / 'spring-api.jar', '--classpath', base / 'winterx-native-api.jar', '--lib', toolchain.android_jar(), '--output', dex_a, runtime_jar)
        translated = work / 'runtime-translated.dex'
        result = spring_translate.translate_dex(mapping, str(decoded), dex_a / 'classes.dex', translated,
                                                skip={'L' + name + ';' for name in GENERATED})
        if not result['ok']: raise ValueError('Core runtime did not translate: ' + json.dumps(result, indent=1))
        # The generated tables are this version's own: compile them against it.
        gen_classes = work / 'gen-classes'; gen_classes.mkdir()
        run(toolchain.jdk_tool('javac'), '--release', '8', '-cp', compile_path(api, runtime_jar), '-d', gen_classes, *sorted(generated.rglob('*.java')))
        gen_jar = work / 'generated.jar'; class_jar(gen_classes, gen_jar)
        dex_b = work / 'dex-b'; dex_b.mkdir()
        run(toolchain.jdk_tool('java'), '-Xmx1g', '-cp', toolchain.d8(), 'com.android.tools.r8.D8', '--min-api', '26',
            '--classpath', api, '--classpath', runtime_jar, '--lib', toolchain.android_jar(), '--output', dex_b, gen_jar)
        merged = work / 'merged'; merged.mkdir()
        run(toolchain.jdk_tool('java'), '-Xmx1g', '-cp', toolchain.d8(), 'com.android.tools.r8.D8', '--min-api', '26',
            '--lib', toolchain.android_jar(), '--output', merged, translated, dex_b / 'classes.dex')
        runtime_dex = (merged / 'classes.dex').read_bytes()
        defined = dex_classes(runtime_dex)
        forbidden = [name for name in defined if name.startswith(FORBIDDEN)]
        if forbidden: raise ValueError('Tweak implementation leaked into core runtime: ' + repr(forbidden))
        rebuilt = work / 'rebuilt.apk'; run(*toolchain.apktool(), 'b', decoded, '-o', rebuilt)
        with zipfile.ZipFile(rebuilt) as archive: primary = archive.read('classes.dex'); secondary = archive.read('classes2.dex')
        engine = destination / ('WinterX-core-%s.apk' % version['name'])
        with zipfile.ZipFile(apk) as original, zipfile.ZipFile(engine, 'x', allowZip64=True) as output:
            for info in original.infolist():
                if legacy.signature(info.filename): continue
                if info.filename == 'classes.dex': output.writestr(info, primary)
                elif info.filename == 'classes2.dex': output.writestr(info, secondary)
                elif info.filename in legacy.BOOT_RESOURCES: output.writestr(info, legacy.BOOT_LOGO.read_bytes())
                else:
                    with original.open(info) as src, output.open(info, 'w') as dst: shutil.copyfileobj(src, dst, 1024 * 1024)
            output.writestr('classes3.dex', runtime_dex, compress_type=zipfile.ZIP_DEFLATED)
        payload = destination / 'android-runtime'; payload.mkdir()
        (payload / 'spring-hooks.dex').write_bytes(primary); (payload / 'winterx-core.dex').write_bytes(runtime_dex)
        early = ['com.guille.spring.LauncherActivity'] + [translator_classes.get(n, n).replace('/', '.') for n in ('x1/i1', 'I1/h0', 'I1/T0', 'I1/Y', 'A/o')]
        manifest = {'format': 'winterx.android-runtime/1', 'package': 'com.guille.spring', 'springVersion': version['name'],
            'sourceApkSha256': sha(apk), 'minimumApi': 26, 'runtimeAbi': 'winterx-native-hooks-v1',
            'files': {name: sha(payload / name) for name in ('spring-hooks.dex', 'winterx-core.dex')},
            'preinstalledTweaks': [], 'earlyClasses': early}
        (payload / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        shutil.copy2(base / 'winterx-native-api.jar', destination / 'winterx-native-api.jar')   # tweaks still compile against 0.8.1
        audit = {'apk': str(engine), 'apk_sha256': sha(engine), 'spring_version': version['name'], 'core_classes': defined,
                 'bundled_tweak_classes': forbidden, 'preinstalled_tweaks': [], 'hook_contracts': len(contracts),
                 'runtime_dex_sha256': sha(payload / 'winterx-core.dex')}
        (destination / 'core-audit.json').write_text(json.dumps(audit, indent=2) + '\n')
    print(json.dumps({k: v for k, v in audit.items() if k != 'core_classes'}, indent=2))

def version_code(stage, work, versions, cores):
    """code/<version>/ for each supported Spring version the author didn't write by hand: the 0.8.1 build, translated."""
    import gzip, spring_translate
    built = {}
    for core in cores or ():
        core = Path(core).resolve(strict=True)
        with gzip.open(core / 'spring-declared.json.gz', 'rt') as source: data = json.load(source)
        built[data['version']] = {cls: (set(members), parent) for cls, (members, parent) in data['classes'].items()}
    maps = {v['name']: v['map'] for v in VERSIONS.values()}
    for version in versions:
        if version == '0.8.1' or (stage / 'code' / version / 'classes.dex').exists(): continue
        if version not in maps: raise ValueError('No name map for Spring ' + version + '; write code/' + version + '/ by hand')
        if version not in built: raise ValueError('Pass --version-core with a built ' + version + ' core to translate for it')
        folder = stage / 'code' / version; folder.mkdir(parents=True, exist_ok=True)
        result = spring_translate.translate_dex(json.loads(maps[version].read_text()), None, stage / 'code/classes.dex',
                                                folder / 'classes.dex', target=built[version])
        if not result['ok']: raise ValueError('Code did not translate to Spring %s: %s' % (version, json.dumps(result, indent=1)))
        wrapped = work / ('dex-' + version + '.apk')
        with zipfile.ZipFile(wrapped, 'w') as archive: archive.write(folder / 'classes.dex', 'classes.dex')
        toolchain.dex_to_jar(wrapped, folder / 'classes.jar')


def package(source, destination, sdk, spring_api=None, library=None, version_cores=None):
    source = Path(source).resolve(strict=True); destination = Path(destination).resolve()
    if destination.exists(): raise ValueError('Package output already exists')
    sdk = Path(sdk).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix='winterx-native-package-') as directory:
        work = Path(directory); stage = work / 'package'; shutil.copytree(source, stage)
        classes = work / 'classes'; classes.mkdir()
        cp = [sdk]
        if spring_api: cp.append(Path(spring_api).resolve(strict=True))
        if library: cp.append(Path(library).resolve(strict=True))
        sources = sorted((stage / 'source').rglob('*.java'))
        if not sources: raise ValueError('Native packages must include editable Java source')
        run(toolchain.jdk_tool('javac'), '--release', '8', '-cp', compile_path(*cp), '-d', classes, *sources)
        code = stage / 'code'; code.mkdir(exist_ok=True)
        jar = code / 'classes.jar'; class_jar(classes, jar, [library] if library else [])
        if library:
            with zipfile.ZipFile(library) as archive:
                for name in archive.namelist():
                    if name.startswith('licenses/') and not name.endswith('/'):
                        target = stage / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(archive.read(name))
        dex = work / 'dex'; dex.mkdir()
        command = [toolchain.jdk_tool('java'), '-Xmx1g', '-cp', toolchain.d8(), 'com.android.tools.r8.D8', '--min-api', '26', '--classpath', sdk]
        if spring_api: command.extend(['--classpath', spring_api])
        command.extend(['--lib', toolchain.android_jar(), '--output', dex, jar]); run(*command)
        shutil.copy2(dex / 'classes.dex', code / 'classes.dex')
        manifest = json.loads((stage / 'manifest.json').read_text())
        version_code(stage, work, manifest.get('spring') or [], version_cores)
        metadata = native_package.build(stage, destination)
    print(json.dumps(metadata, indent=2))
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    core = sub.add_parser('runtime'); core.add_argument('apk', type=Path); core.add_argument('output', type=Path)
    core.add_argument('--base', type=Path, help='for Spring versions other than 0.8.1: a finished 0.8.1 core build')
    module = sub.add_parser('package'); module.add_argument('source', type=Path); module.add_argument('output', type=Path)
    module.add_argument('--sdk', type=Path, required=True); module.add_argument('--spring-api', type=Path); module.add_argument('--library', type=Path)
    module.add_argument('--version-core', type=Path, action='append', help='a built core for another Spring version the package supports (repeatable)')
    args = parser.parse_args()
    if args.command == 'runtime':
        if sha(args.apk) in VERSIONS:
            if not args.base: raise SystemExit('This Spring version builds from a 0.8.1 core: pass --base')
            runtime_version(args.apk, args.output, args.base)
        else: runtime(args.apk, args.output)
    else: package(args.source, args.output, args.sdk, args.spring_api, args.library, args.version_core)


if __name__ == '__main__': main()
