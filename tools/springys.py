#!/usr/bin/env python3
"""Validate WinterX .springys packages and their iOS-style artwork metadata."""
import hashlib
import json
import re
import stat
import struct
import zipfile

FORMAT = 'winterx.springys/1'
MAX_ZIP = 12 * 1024 * 1024
MAX_UNPACKED = 24 * 1024 * 1024
MAX_ART = 2 * 1024 * 1024
MAX_FILES = 16
ID_RE = re.compile(r'^[a-z0-9]+(?:[.-][a-z0-9]+)+$')
VERSION_RE = re.compile(r'^[0-9]+(?:\.[0-9]+){1,3}(?:[-+][0-9A-Za-z.-]+)?$')
HOOK_RE = re.compile(r'^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)+$')
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


def inspect(path, expected_sha256=None):
    """Return normalized metadata and artwork bytes. Does not extract or execute files."""
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
    import io
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
                if info.filename != 'manifest.json':
                    _art_path(info.filename)
                    if info.file_size > MAX_ART:
                        raise PackageError('Artwork exceeds 2 MB')
            if 'manifest.json' not in names or archive.getinfo('manifest.json').file_size > 128 * 1024:
                raise PackageError('Missing or oversized manifest.json')
            manifest = json.loads(archive.read('manifest.json').decode('utf-8'), object_pairs_hook=_object)
            if not isinstance(manifest, dict) or manifest.get('format') != FORMAT:
                raise PackageError('Unsupported package format')
            package_id = _text(manifest, 'id', 120)
            version = _text(manifest, 'version', 64)
            hook = _text(manifest, 'hook', 120)
            if not ID_RE.fullmatch(package_id) or not VERSION_RE.fullmatch(version) or not HOOK_RE.fullmatch(hook):
                raise PackageError('Invalid package ID, version or hook')
            name = _text(manifest, 'name', 80)
            description = _text(manifest, 'description', 4000)
            author = _text(manifest, 'author', 120)
            icon = _art_path(manifest['icon']) if manifest.get('icon') is not None else None
            previews = manifest.get('previews', [])
            if not isinstance(previews, list) or len(previews) > 5:
                raise PackageError('previews must be a list of at most five images')
            previews = [_art_path(p) for p in previews]
            artwork = set(previews + ([icon] if icon else []))
            if set(names) != {'manifest.json'} | artwork:
                raise PackageError('Package must contain only the manifest and its referenced artwork')
            media = {}
            for name_in_zip in artwork:
                payload = archive.read(name_in_zip)
                _image(name_in_zip, payload)
                media[name_in_zip] = payload
            result = {'format': FORMAT, 'id': package_id, 'version': version, 'name': name,
                      'description': description, 'author': author, 'hook': hook,
                      'icon': icon, 'previews': previews, 'sha256': digest}
            return result, media
    except PackageError:
        raise
    except (zipfile.BadZipFile, KeyError, UnicodeError, ValueError, TypeError, OSError) as e:
        raise PackageError('Invalid .springys package: ' + str(e)) from e
