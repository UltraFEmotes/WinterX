"""Source-backed .springys/3 Java/Dex packages, independent of the Spring engine APK."""
import hashlib
import io
import json
from pathlib import Path
import re
import stat
import struct
from urllib.parse import urlsplit
import zipfile
import zlib

FORMAT = 'winterx.springys/3'
API = 'winterx.native/1'
DEX = 'code/classes.dex'
JAR = 'code/classes.jar'
MAX_FILES = 128
MAX_PAYLOAD = 16 * 1024 * 1024
MAX_EXPANDED = 32 * 1024 * 1024
CLASS = re.compile(r'^[a-zA-Z_$][\w$]*(?:\.[a-zA-Z_$][\w$]*)+$', re.ASCII)
POINT = re.compile(r'^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+$')
SOURCE = re.compile(r'^source/(?:[A-Za-z0-9_$.-]+/)*[A-Za-z0-9_$.-]+\.(?:java|js|json)$')
LICENSE = re.compile(r'^licenses/[A-Za-z0-9._-]+/(?:LICENSE|NOTICE)(?:\.txt)?$')
APP = re.compile(r'^apps/[A-Za-z0-9][A-Za-z0-9._-]{0,80}\.sapp$')
INJECT = re.compile(r'^inject/[A-Za-z0-9][A-Za-z0-9._-]{0,80}\.js$')
MAX_APPS = 4
# Trusted WinterX apps keep their pinned installs; a package can never replace them.
RESERVED_APPS = frozenset(('com.ruby.manager', 'com.ruby.jailbreak', 'com.winterx.iexplored'))
META = frozenset(('format', 'type', 'runtime', 'api', 'entry', 'id', 'name', 'version', 'description', 'author',
                  'license', 'source', 'exports', 'capabilities', 'files', 'icon', 'previews', 'features', 'requires', 'settings_entry', 'apps', 'inject'))


def safe_path(name):
    return (isinstance(name, str) and len(name) <= 240 and not name.startswith('/') and '\\' not in name
            and all(part not in ('', '.', '..') for part in name.split('/')))


def reserved_class(name):
    return (name.startswith(('java/', 'javax/', 'android/', 'dalvik/', 'com/guille/spring/',
                            'winterx/extension/', 'winterx/runtime/', 'winterx/tweaks/', 'winterx/recovery/', 'winterx/appearance/'))
            or bool(re.match(r'^(?:[A-Za-z]|[A-Za-z][0-9]+)/', name)))


def dex_classes(raw):
    """Read bounded class definitions without executing DEX or trusting its table offsets."""
    if (len(raw) < 112 or raw[:8] not in (b'dex\n035\0', b'dex\n037\0', b'dex\n038\0', b'dex\n039\0', b'dex\n040\0')
            or struct.unpack_from('<III', raw, 32) != (len(raw), 112, 0x12345678)
            or raw[12:32] != hashlib.sha1(raw[32:]).digest()
            or struct.unpack_from('<I', raw, 8)[0] != zlib.adler32(raw[12:]) & 0xffffffff):
        raise ValueError('Invalid Android DEX header/checksum')
    string_count, strings, type_count, types = struct.unpack_from('<IIII', raw, 56)
    class_count, classes = struct.unpack_from('<II', raw, 96)
    if not 1 <= class_count <= 20000:
        raise ValueError('Invalid Android DEX class count')
    for offset, count, width in ((strings, string_count, 4), (types, type_count, 4), (classes, class_count, 32)):
        if offset < 112 or offset % 4 or offset + count * width > len(raw):
            raise ValueError('Invalid Android DEX table')
    result = []
    for index in range(class_count):
        type_index = struct.unpack_from('<I', raw, classes + index * 32)[0]
        if type_index >= type_count: raise ValueError('Invalid DEX class type index')
        string_index = struct.unpack_from('<I', raw, types + type_index * 4)[0]
        if string_index >= string_count: raise ValueError('Invalid DEX type string index')
        offset = struct.unpack_from('<I', raw, strings + string_index * 4)[0]
        for _ in range(5):
            if offset >= len(raw): raise ValueError('Truncated DEX string')
            byte = raw[offset]; offset += 1
            if byte < 128: break
        else: raise ValueError('Invalid DEX string length')
        end = raw.find(b'\0', offset, min(len(raw), offset + 1024))
        if end < 0: raise ValueError('Unterminated DEX class name')
        name = raw[offset:end].decode('ascii')
        if not re.fullmatch(r'L[A-Za-z0-9_$/-]+;', name) or not safe_path(name[1:-1]):
            raise ValueError('Invalid DEX class name')
        result.append(name)
    if len(result) != len(set(result)): raise ValueError('Duplicate DEX class definition')
    return result


def bundled_app(path, raw):
    """A bundled Spring app: a .sapp ZIP whose app.json names a non-reserved app ID and a positive build."""
    import springys
    error = springys.PackageError
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as app:
            infos = app.infolist()
            if len(infos) > 512 or sum(info.file_size for info in infos) > 40 * 1024 * 1024:
                raise error('Bundled app exceeds its limits: ' + path)
            names = app.namelist()
            if 'app.json' not in names or 'main.js' not in names or app.getinfo('app.json').file_size > 64 * 1024:
                raise error('Bundled app needs app.json and main.js: ' + path)
            manifest = json.loads(app.read('app.json').decode('utf-8'), object_pairs_hook=springys._object)
    except zipfile.BadZipFile as failure:
        raise error('Bundled app is not a valid .sapp: ' + path) from failure
    if not isinstance(manifest, dict): raise error('Invalid bundled app manifest: ' + path)
    app_id = springys._text(manifest, 'id', 120)
    if not springys.ID_RE.fullmatch(app_id) or app_id in RESERVED_APPS:
        raise error('Bundled app cannot use app ID ' + app_id)
    build = manifest.get('build')
    if not isinstance(build, int) or isinstance(build, bool) or build < 1:
        raise error('Bundled app needs a positive integer build: ' + path)
    result = {'path': path, 'id': app_id, 'build': build, 'name': springys._text(manifest, 'name', 80)}
    if isinstance(manifest.get('version'), str): result['version'] = manifest['version']
    return result


def inspect_archive(archive, digest, include_code=False):
    import springys
    error = springys.PackageError
    infos = archive.infolist()
    if not 4 <= len(infos) <= MAX_FILES or sum(info.file_size for info in infos) > MAX_EXPANDED:
        raise error('Native package exceeds its entry/expanded-byte limit')
    names = [info.filename for info in infos]
    if len(names) != len(set(names)) or len(names) != len({name.casefold() for name in names}):
        raise error('Duplicate or case-colliding native package path')
    for info in infos:
        if (not safe_path(info.filename) or info.is_dir() or (info.external_attr >> 16) & 0o170000 == stat.S_IFLNK
                or info.flag_bits & 1 or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                or info.file_size > MAX_PAYLOAD):
            raise error('Unsafe or oversized native package entry')
    if 'manifest.json' not in names or archive.getinfo('manifest.json').file_size > 128 * 1024:
        raise error('Native manifest missing or oversized')
    manifest = json.loads(archive.read('manifest.json').decode('utf-8'), object_pairs_hook=springys._object)
    if (not isinstance(manifest, dict) or set(manifest) - META or manifest.get('format') != FORMAT
            or manifest.get('type') != 'tweak' or manifest.get('runtime') != 'java' or manifest.get('api') != API):
        raise error('Invalid source-backed native package manifest')
    package_id = springys._text(manifest, 'id', 120)
    version = springys._text(manifest, 'version', 64)
    if not springys.ID_RE.fullmatch(package_id) or not springys.VERSION_RE.fullmatch(version):
        raise error('Invalid native package identity/version')
    for key, maximum in (('name', 80), ('description', 4000), ('author', 120), ('license', 80)):
        springys._text(manifest, key, maximum)
    entry = springys._text(manifest, 'entry', 180)
    if not CLASS.fullmatch(entry) or reserved_class(entry.replace('.', '/')):
        raise error('Native entry must name the package implementation, not a framework class')
    if manifest.get('capabilities') != ['native.hooks']:
        raise error('Native packages must declare the native.hooks capability')
    exports = manifest.get('exports')
    if (not isinstance(exports, list) or not 1 <= len(exports) <= 128
            or any(not isinstance(value, str) or len(value) > 160 or not POINT.fullmatch(value) for value in exports)
            or len(exports) != len(set(exports))):
        raise error('Invalid native hook exports')
    features = manifest.get('features', [])
    if (not isinstance(features, list) or len(features) > 32
            or any(not isinstance(value, str) or len(value) > 160 or not POINT.fullmatch(value) for value in features)
            or len(features) != len(set(features))):
        raise error('Invalid native feature declarations')
    requires = manifest.get('requires', [])
    if (not isinstance(requires, list) or len(requires) > 16
            or any(not isinstance(value, str) or len(value) > 120 or not springys.ID_RE.fullmatch(value) or value == package_id for value in requires)
            or len(requires) != len(set(requires))):
        raise error('Invalid native package dependencies')
    source = manifest.get('source')
    if not isinstance(source, str) or len(source) > 500 or any(ord(c) < 33 for c in source):
        raise error('Native packages must link their published source')
    url = urlsplit(source)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.fragment:
        raise error('Native source must be an HTTPS URL without credentials or fragments')
    if manifest.get('settings_entry') is not None and (not isinstance(manifest['settings_entry'], str) or len(manifest['settings_entry']) > 180 or not re.fullmatch(r'[A-Za-z0-9_./-]+', manifest['settings_entry'])):
        raise error('Invalid native Settings entry')
    declared = manifest.get('files')
    if (not isinstance(declared, dict) or DEX not in declared or JAR not in declared
            or any(not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value) for value in declared.values())):
        raise error('Native package must pin both Android DEX and JVM code')
    if not any(SOURCE.fullmatch(name) and name.endswith('.java') for name in declared):
        raise error('Native packages must include editable Java source')
    icon = springys._art_path(manifest['icon']) if manifest.get('icon') else None
    previews = manifest.get('previews', [])
    if not isinstance(previews, list) or len(previews) > 5:
        raise error('Invalid native package previews')
    previews = [springys._art_path(name) for name in previews]
    artwork = set(previews + ([icon] if icon else []))
    apps = manifest.get('apps', [])
    if (not isinstance(apps, list) or len(apps) > MAX_APPS or len(apps) != len(set(apps))
            or any(not isinstance(value, str) or not APP.fullmatch(value) for value in apps)):
        raise error('Invalid bundled app list')
    for app in apps:
        if app not in declared: raise error('Bundled app must be pinned in files: ' + app)
    inject = manifest.get('inject')
    if inject is not None:
        if not isinstance(inject, list) or not 1 <= len(inject) <= 16: raise error('Invalid app script injection list')
        for injection in inject:
            if not isinstance(injection, dict) or set(injection) - {'apps', 'script'}: raise error('Invalid app script injection entry')
            script, targets = injection.get('script'), injection.get('apps')
            if not isinstance(script, str) or not INJECT.fullmatch(script) or script not in declared:
                raise error('Injected script must be an inject/*.js file pinned in files')
            if not isinstance(targets, list) or not 1 <= len(targets) <= 32: raise error('Injected script needs a list of target app IDs')
            for target in targets:
                if not isinstance(target, str) or target != '*' and (not springys.ID_RE.fullmatch(target) or target in RESERVED_APPS):
                    raise error('Invalid injection target: ' + repr(target))
    if set(names) != {'manifest.json'} | set(declared) | artwork:
        raise error('Native package contains undeclared files')
    payloads = {}
    for name, expected in declared.items():
        if name not in (DEX, JAR) and not SOURCE.fullmatch(name) and not LICENSE.fullmatch(name) and not APP.fullmatch(name) and not INJECT.fullmatch(name):
            raise error('Unsupported native code/source/license path: ' + name)
        raw = archive.read(name)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise error('Native package payload checksum mismatch: ' + name)
        if name.startswith(('source/', 'inject/')):
            if not raw or len(raw) > 256 * 1024 or b'\0' in raw:
                raise error('Invalid or oversized native source file')
            raw.decode('utf-8', errors='strict')
        payloads[name] = raw
    try:
        classes = dex_classes(payloads[DEX])
    except (ValueError, IndexError, struct.error) as failure:
        raise error(str(failure)) from failure
    if 'L' + entry.replace('.', '/') + ';' not in classes:
        raise error('Native Android entry class is missing')
    if any(reserved_class(name[1:-1]) for name in classes):
        raise error('Native package cannot replace platform/Spring/runtime classes')
    with zipfile.ZipFile(io.BytesIO(payloads[JAR])) as jar:
        entries = jar.infolist()
        if len(entries) > 20000 or sum(info.file_size for info in entries) > 64 * 1024 * 1024:
            raise error('Native class archive exceeds its limits')
        class_names = jar.namelist()
        if len(class_names) != len(set(class_names)) or entry.replace('.', '/') + '.class' not in class_names:
            raise error('Native entry class missing or duplicated')
        for info in entries:
            name = info.filename
            if (info.flag_bits & 1 or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                    or (info.external_attr >> 16) & 0o170000 == stat.S_IFLNK):
                raise error('Unsafe native class archive entry')
            if info.is_dir():
                if not safe_path(name.rstrip('/')): raise error('Unsafe class archive directory')
                continue
            if not safe_path(name) or reserved_class(name):
                raise error('Native package cannot replace platform/Spring/runtime classes')
            if name.endswith('.class'):
                with jar.open(info) as source:
                    if source.read(4) != b'\xca\xfe\xba\xbe': raise error('Invalid JVM class payload')
    bundled = [bundled_app(app, payloads[app]) for app in apps]
    if len({app['id'] for app in bundled}) != len(bundled): raise error('Two bundled apps share an app ID')
    media = {}
    for name in artwork:
        value = archive.read(name); springys._image(name, value); media[name] = value
    metadata = dict(manifest)
    metadata.update(sha256=digest, code_sha256=declared[DEX], jvm_sha256=declared[JAR], icon=icon, previews=previews)
    if bundled: metadata['bundled_apps'] = bundled
    if include_code:
        metadata['native_payloads'] = payloads
    return metadata, media


def build(source, output):
    """Package precompiled independent code and all its editable source deterministically."""
    import springys
    root = Path(source).resolve(strict=True); target = Path(output)
    manifest = json.loads((root / 'manifest.json').read_text(), object_pairs_hook=springys._object)
    payloads = {}
    for folder in ('code', 'source', 'licenses', 'apps', 'inject'):
        for path in sorted((root / folder).rglob('*')):
            if path.is_symlink():
                raise springys.PackageError('Native package sources cannot contain links')
            if path.is_file():
                payloads[path.relative_to(root).as_posix()] = path.read_bytes()
    manifest['files'] = {name: hashlib.sha256(value).hexdigest() for name, value in sorted(payloads.items())}
    artwork = set(manifest.get('previews', []) + ([manifest['icon']] if manifest.get('icon') else []))
    for name in artwork:
        springys._art_path(name); path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise springys.PackageError('Native artwork escaped the package')
        payloads[name] = path.read_bytes()
    payloads['manifest.json'] = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, value in sorted(payloads.items()):
            info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16; archive.writestr(info, value)
    raw = buffer.getvalue()
    if len(raw) > springys.MAX_ZIP:
        raise springys.PackageError('Native package exceeds the archive limit')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        inspect_archive(archive, hashlib.sha256(raw).hexdigest())
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as output:
        output.write(raw)
    return springys.inspect(target)[0]
