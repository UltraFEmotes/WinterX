#!/usr/bin/env python3
"""Validate WinterX .springys packages and their iOS-style artwork metadata."""
import hashlib
import io
import json
import re
import stat
import struct
import zipfile

FORMAT = 'winterx.springys/1'
FORMAT2 = 'winterx.springys/2'
CODE_ENTRY = 'tweak/main.js'
MAX_ZIP = 12 * 1024 * 1024
MAX_UNPACKED = 24 * 1024 * 1024
MAX_ART = 2 * 1024 * 1024
MAX_FILES = 20
MAX_CODE = 256 * 1024
MAX_PAGES = 20
MAX_TWEAKS = 8
ID_RE = re.compile(r'^[a-z0-9]+(?:[.-][a-z0-9]+)+$')
VERSION_RE = re.compile(r'^[0-9]+(?:\.[0-9]+){1,3}(?:[-+][0-9A-Za-z.-]+)?$')
HOOK_RE = re.compile(r'^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+$')
ROW_RE = re.compile(r'^[a-z0-9-]{1,40}$')
ART_RE = re.compile(r'^assets/[A-Za-z0-9][A-Za-z0-9._/-]*\.(?:png|jpg|jpeg)$', re.I)


class PackageError(ValueError):
    pass


def _object(pairs):
    d = {}
    for key, value in pairs:
        if key in d:
            raise PackageError('Duplicate JSON key: ' + key)
        d[key] = value
    return d


def _validate_settings(settings):
    """Validate the declarative Settings schema a v2 manifest may declare."""
    if not isinstance(settings, dict) or not settings:
        raise PackageError('settings must be an object')
    pages = [('main', settings.get('main'))]
    extra = settings.get('pages')
    if extra is not None:
        if not isinstance(extra, dict) or not extra:
            raise PackageError('settings.pages must be an object')
        pages += list(extra.items())
    if len(pages) > MAX_PAGES:
        raise PackageError('settings has too many pages (max 20)')
    page_ids = {name for name, _ in pages}
    if extra is not None and 'main' in extra:
        raise PackageError('settings.pages cannot redefine main')
    for page_name, page in pages:
        if not isinstance(page, dict):
            raise PackageError('settings page must be an object: ' + page_name)
        if page_name != 'main' and not ROW_RE.fullmatch(page_name):
            raise PackageError('Invalid settings page id: ' + page_name)
        title = page.get('title')
        if title is not None and (not isinstance(title, str) or len(title) > 60 or '\x00' in title):
            raise PackageError('Invalid settings page title in ' + page_name)
        sections = page.get('sections')
        if not isinstance(sections, list) or not 1 <= len(sections) <= 40:
            raise PackageError('settings page must declare sections: ' + page_name)
        row_ids = set()
        for section in sections:
            if not isinstance(section, dict):
                raise PackageError('settings section must be an object')
            section_id = section.get('id')
            if section_id is not None and (not isinstance(section_id, str) or not ROW_RE.fullmatch(section_id)):
                raise PackageError('Invalid settings section id')
            header = section.get('title')
            if header is not None and (not isinstance(header, str) or len(header) > 60 or '\x00' in header):
                raise PackageError('Invalid settings section title')
            rows = section.get('rows')
            if not isinstance(rows, list) or not 1 <= len(rows) <= 40:
                raise PackageError('settings section must declare rows')
            for row in rows:
                if not isinstance(row, dict):
                    raise PackageError('settings row must be an object')
                row_id = row.get('id')
                if not isinstance(row_id, str) or not ROW_RE.fullmatch(row_id):
                    raise PackageError('Invalid settings row id')
                if row_id in row_ids:
                    raise PackageError('Duplicate settings row id: ' + row_id)
                row_ids.add(row_id)
                if row.get('type') not in ('button', 'toggle', 'page'):
                    raise PackageError('settings row type must be button, toggle or page')
                title = row.get('title')
                if not isinstance(title, str) or not title.strip() or len(title) > 60 or '\x00' in title:
                    raise PackageError('Invalid settings row title')
                if row.get('type') == 'page' and (not isinstance(row.get('page'), str) or row.get('page') not in page_ids):
                    raise PackageError('settings page row needs an existing target page id')


def _text(obj, key, limit, optional=False):
    value = obj.get(key)
    if optional and value is None:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > limit or '\x00' in value:
        raise PackageError('Invalid ' + key)
    return value


def _art_path(value):
    if not isinstance(value, str) or not ART_RE.fullmatch(value):
        raise PackageError('Artwork must be a PNG or JPEG inside assets/')
    if any(part in ('', '.', '..') for part in value.split('/')):
        raise PackageError('Invalid artwork path')
    return value


def _image(name, payload):
    if not payload or len(payload) > MAX_ART:
        raise PackageError('Artwork too large or empty: ' + name)
    if name.lower().endswith('.png'):
        if len(payload) < 24 or payload[:8] != b'\x89PNG\r\n\x1a\n' or payload[12:16] != b'IHDR':
            raise PackageError('Invalid PNG: ' + name)
        width, height = struct.unpack('>II', payload[16:24])
        if not 1 <= width <= 4096 or not 1 <= height <= 4096:
            raise PackageError('PNG dimensions out of range: ' + name)
    elif not (payload.startswith(b'\xff\xd8\xff') and payload.endswith(b'\xff\xd9')):
        raise PackageError('Invalid JPEG: ' + name)


def inspect(path, expected_sha256=None, *, include_code=False):
    """Return JSON-safe metadata and artwork bytes; include_code is installer-only.

    No files are extracted and no package code is executed here.
    """
    path = str(path)
    try:
        with open(path, 'rb') as source:
            raw = source.read(MAX_ZIP + 1)
    except OSError as e:
        raise PackageError(str(e)) from e
    if len(raw) > MAX_ZIP:
        raise PackageError('Package exceeds 12 MB')
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and (not isinstance(expected_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_sha256) or digest != expected_sha256):
        raise PackageError('Package SHA-256 does not match')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            if not 1 <= len(infos) <= MAX_FILES:
                raise PackageError('Invalid number of files')
            names = [i.filename for i in infos]
            if len(names) != len(set(names)):
                raise PackageError('Duplicate ZIP entry')
            if sum(i.file_size for i in infos) > MAX_UNPACKED:
                raise PackageError('Package expands beyond 24 MB')
            for info in infos:
                mode = (info.external_attr >> 16) & 0o170000
                if info.is_dir() or mode == stat.S_IFLNK or info.flag_bits & 1:
                    raise PackageError('Directories, links and encrypted entries are not supported')
                if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                    raise PackageError('Unsupported ZIP compression')
                if info.filename == 'manifest.json':
                    continue
                if info.filename == CODE_ENTRY:
                    if info.file_size > MAX_CODE:
                        raise PackageError('tweak/main.js exceeds 256 KB')
                    continue
                _art_path(info.filename)
                if info.file_size > MAX_ART:
                    raise PackageError('Artwork exceeds 2 MB')
            if 'manifest.json' not in names or archive.getinfo('manifest.json').file_size > 128 * 1024:
                raise PackageError('Missing or oversized manifest.json')
            manifest = json.loads(archive.read('manifest.json').decode('utf-8'), object_pairs_hook=_object)
            if not isinstance(manifest, dict):
                raise PackageError('Invalid manifest.json')
            package_format = manifest.get('format')
            if package_format == FORMAT2:
                return _inspect_v2(archive, names, manifest, digest, include_code)
            if package_format != FORMAT:
                raise PackageError('Unsupported package format')
            return _inspect_v1(archive, names, manifest, digest)
    except PackageError:
        raise
    except (zipfile.BadZipFile, KeyError, UnicodeError, ValueError, TypeError, OSError) as e:
        raise PackageError('Invalid .springys package: ' + str(e)) from e


def _inspect_v1(archive, names, manifest, digest):
    hook = _text(manifest, 'hook', 120)
    if not HOOK_RE.fullmatch(hook):
        raise PackageError('Invalid hook')
    return _read_package(archive, names, manifest, digest, hook=hook, code_name=None)


def _inspect_v2(archive, names, manifest, digest, include_code):
    if manifest.get('type') != 'tweak':
        raise PackageError('v2 packages must declare type "tweak"')
    if manifest.get('entry') != CODE_ENTRY:
        raise PackageError('v2 entry must be tweak/main.js')
    if 'hook' in manifest:
        raise PackageError('v2 code tweaks cannot select built-in marker hooks')
    if 'tweak/main.js' not in names:
        raise PackageError('v2 package is missing tweak/main.js')
    settings = manifest.get('settings')
    if settings is not None:
        _validate_settings(settings)
    return _read_package(archive, names, manifest, digest, code_name=CODE_ENTRY, include_code=include_code)


def _read_package(archive, names, manifest, digest, hook=None, code_name=None, include_code=False):
    if hook is not None:
        hook = _text(manifest, 'hook', 120)
        if not HOOK_RE.fullmatch(hook):
            raise PackageError('Invalid hook')
    package_id = _text(manifest, 'id', 120)
    version = _text(manifest, 'version', 64)
    if not ID_RE.fullmatch(package_id) or not VERSION_RE.fullmatch(version):
        raise PackageError('Invalid package ID or version')
    name = _text(manifest, 'name', 80)
    description = _text(manifest, 'description', 4000)
    author = _text(manifest, 'author', 120)
    icon = _art_path(manifest['icon']) if manifest.get('icon') is not None else None
    previews = manifest.get('previews', [])
    if not isinstance(previews, list) or len(previews) > 5:
        raise PackageError('previews must be a list of at most five images')
    previews = [_art_path(p) for p in previews]
    artwork = set(previews + ([icon] if icon else []))
    allowed = {'manifest.json'} | artwork
    if code_name:
        allowed.add(code_name)
    if set(names) != allowed:
        raise PackageError('Package must contain only the manifest, its artwork and its declared files')
    media = {}
    for name_in_zip in artwork:
        payload = archive.read(name_in_zip)
        _image(name_in_zip, payload)
        media[name_in_zip] = payload
    result = {'format': manifest['format'], 'id': package_id, 'version': version, 'name': name,
              'description': description, 'author': author,
              'icon': icon, 'previews': previews, 'sha256': digest}
    if code_name:
        code = archive.read(code_name)
        if not code or len(code) > MAX_CODE:
            raise PackageError('tweak/main.js is missing or exceeds 256 KB')
        script = code.decode('utf-8', errors='strict')
        if not script.strip() or '\x00' in script:
            raise PackageError('tweak/main.js is empty or contains NUL')
        if include_code:
            result['code'] = code
        result['code_sha256'] = hashlib.sha256(code).hexdigest()
        result['entry'] = CODE_ENTRY
        if 'settings' in manifest:
            result['settings'] = manifest['settings']
    if hook:
        result['hook'] = hook
    result['type'] = 'tweak' if code_name else 'hook'
    return result, media
