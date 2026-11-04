"""Bounded SnowyHome icon-pack authoring. Never installs into Spring or executes pack code."""
import hashlib
import io
import json
from pathlib import Path
import re
import stat
import struct
import zipfile

FORMAT = 'winterx.iconpack/1'
MAX_ICONS = 128
MAX_ICON = 1024 * 1024
MAX_ZIP = 16 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024
FILE = re.compile(r'^icons/[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\.png$')
APP = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$')
ID = re.compile(r'^[a-z0-9]+(?:[.-][a-z0-9]+)+$')
SHA = re.compile(r'^[0-9a-f]{64}$')
RESERVED = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}


def filename(value):
    return (isinstance(value, str) and FILE.fullmatch(value) is not None
            and value.split('/')[1].split('.')[0].upper() not in RESERVED)


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value: raise ValueError('Duplicate icon-pack field: ' + key)
        value[key] = item
    return value


def manifest(raw):
    if not isinstance(raw, bytes) or len(raw) > 64 * 1024: raise ValueError('Icon-pack manifest exceeds 64 KiB')
    value = json.loads(raw, object_pairs_hook=_object)
    if not isinstance(value, dict) or value.get('format') != FORMAT: raise ValueError('Unsupported icon-pack format')
    if set(value) != {'format', 'id', 'name', 'author', 'version', 'icons'}: raise ValueError('Unexpected icon-pack fields')
    for key in ('id', 'name', 'author', 'version'):
        text = value[key]
        if not isinstance(text, str) or not text.strip() or len(text) > 80 or any(ord(c) < 32 for c in text):
            raise ValueError('Invalid icon-pack ' + key)
    if not ID.fullmatch(value['id']): raise ValueError('Invalid icon-pack ID')
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,3}(?:[-+][0-9A-Za-z.-]+)?', value['version']):
        raise ValueError('Invalid icon-pack version')
    icons = value['icons']
    if not isinstance(icons, dict) or not 1 <= len(icons) <= MAX_ICONS: raise ValueError('Icon packs need 1–128 icons')
    for app, item in icons.items():
        if not APP.fullmatch(app) or app == 'folder-utilities' or app.startswith('folder:'):
            raise ValueError('Map actual Spring app IDs, not folder IDs')
        if not isinstance(item, dict) or set(item) != {'file', 'sha256'}: raise ValueError('Invalid icon mapping')
        if not filename(item['file']): raise ValueError('Invalid portable icon filename')
        if not isinstance(item['sha256'], str) or not SHA.fullmatch(item['sha256']): raise ValueError('Invalid icon checksum')
    return value


def image(payload):
    if not payload or len(payload) > MAX_ICON: raise ValueError('Icon PNG must be at most 1 MiB')
    if len(payload) < 24 or payload[:8] != b'\x89PNG\r\n\x1a\n' or payload[12:16] != b'IHDR': raise ValueError('Expected a PNG icon')
    width, height = struct.unpack('>II', payload[16:24])
    if width != height or not 16 <= width <= 1024: raise ValueError('Icons must be square PNGs, 16–1024 pixels')
    # Header checks alone do not establish that an image can decode safely.
    from PIL import Image
    with Image.open(io.BytesIO(payload)) as source:
        if source.format != 'PNG' or source.size != (width, height) or getattr(source, 'n_frames', 1) != 1:
            raise ValueError('Expected a single-frame PNG icon')
        source.verify()
    with Image.open(io.BytesIO(payload)) as source: source.load()


def inspect(path):
    path = Path(path)
    if not path.is_file(): raise ValueError('Icon pack must be a regular file')
    with path.open('rb') as source: raw = source.read(MAX_ZIP + 1)
    if len(raw) > MAX_ZIP: raise ValueError('Icon pack exceeds 16 MiB')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        if not 2 <= len(entries) <= MAX_ICONS + 1 or sum(item.file_size for item in entries) > MAX_TOTAL:
            raise ValueError('Icon pack exceeds the file/expanded byte limit')
        names = [item.filename for item in entries]
        if len(names) != len({name.lower() for name in names}) or 'manifest.json' not in names: raise ValueError('Duplicate or missing icon-pack entries')
        for item in entries:
            if item.is_dir() or stat.S_ISLNK(item.external_attr >> 16) or item.flag_bits & 1 or item.compress_type not in (0, 8):
                raise ValueError('Links/directories/encryption/unsupported compression are refused')
            if item.filename == 'manifest.json':
                if item.file_size > 64 * 1024: raise ValueError('Manifest exceeds 64 KiB')
            elif not filename(item.filename) or item.file_size > MAX_ICON: raise ValueError('Invalid icon-pack entry')
        manifest_raw = archive.read('manifest.json'); value = manifest(manifest_raw)
        wanted = {'manifest.json'} | {item['file'] for item in value['icons'].values()}
        if set(names) != wanted: raise ValueError('Icon pack contains unreferenced files')
        media = {}
        for app, item in value['icons'].items():
            file = item['file']
            if file not in media:
                media[file] = archive.read(file); image(media[file])
            if hashlib.sha256(media[file]).hexdigest() != item['sha256']: raise ValueError('Icon checksum mismatch: ' + app)
    return value, manifest_raw, media, hashlib.sha256(raw).hexdigest()


def build(source, destination):
    source, destination = Path(source).resolve(strict=True), Path(destination)
    if destination.exists(): raise ValueError('Output must be a new file')
    if (source / 'manifest.json').is_symlink() or not (source / 'manifest.json').is_file(): raise ValueError('Manifest must be a regular, non-linked file')
    with (source / 'manifest.json').open('rb') as file: raw = file.read(64 * 1024 + 1)
    if len(raw) > 64 * 1024: raise ValueError('Manifest exceeds 64 KiB')
    value = json.loads(raw, object_pairs_hook=_object)
    if not isinstance(value, dict) or not isinstance(value.get('icons'), dict): raise ValueError('Invalid icon-pack source')
    if not 1 <= len(value['icons']) <= MAX_ICONS: raise ValueError('Icon packs need 1–128 icons')
    media, used = {}, 0
    for app, item in value['icons'].items():
        if not isinstance(item, dict) or set(item) - {'file', 'sha256'} or not filename(item.get('file')):
            raise ValueError('Source icons need a file field')
        path = source / item['file']
        if any(parent.is_symlink() for parent in (source / 'icons', path)) or not path.is_file() or not path.resolve().is_relative_to(source):
            raise ValueError('Icon source links/escapes are refused')
        if item['file'] not in media:
            with path.open('rb') as file: payload = file.read(MAX_ICON + 1)
            image(payload); media[item['file']] = payload; used += len(payload)
            if used > MAX_TOTAL: raise ValueError('Icon sources exceed the byte limit')
        item['sha256'] = hashlib.sha256(media[item['file']]).hexdigest()
    raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode(); manifest(raw)
    if len(media) != len({name.lower() for name in media}): raise ValueError('Case-colliding icon files are refused')
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, payload in sorted({'manifest.json': raw, **media}.items()):
            entry = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0)); entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100600 << 16; archive.writestr(entry, payload)
    if out.tell() > MAX_ZIP: raise ValueError('Compressed pack exceeds 16 MiB')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as file: file.write(out.getvalue())
    return inspect(destination)


def export(path, destination):
    """Export a validated immutable revision to a NEW local directory, not Spring."""
    value, raw, media, digest = inspect(path)
    destination = Path(destination)
    if destination.exists() or destination.is_symlink(): raise ValueError('Export directory must be new')
    destination.mkdir(parents=True)
    target = destination / digest; (target / 'icons').mkdir(parents=True)
    for name, payload in {'manifest.json': raw, 'manifest.sha256': hashlib.sha256(raw).hexdigest().encode(), **media}.items():
        (target / name).write_bytes(payload)
    return target
