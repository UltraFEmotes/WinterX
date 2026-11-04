#!/usr/bin/env python3
"""Build and inspect draft WinterX .springys packages without extracting them."""
import argparse
import json
from pathlib import Path
import tempfile
import os
import zipfile

import springys


def build(source, destination):
    source = Path(source).resolve(strict=True)
    destination = Path(destination).resolve()
    if not source.is_dir() or destination.suffix != '.springys':
        raise ValueError('Supply a package directory and a .springys output path')
    if destination.exists():
        raise ValueError('Output already exists')
    manifest_path = source / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'), object_pairs_hook=springys._object)
    if not isinstance(manifest, dict):
        raise ValueError('Manifest must be an object')
    previews = manifest.get('previews', [])
    if not isinstance(previews, list):
        raise ValueError('previews must be a list')
    artwork = set(previews + ([manifest['icon']] if manifest.get('icon') is not None else []))
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.springys-', dir=destination.parent)
    try:
        with os.fdopen(fd, 'w+b') as stream, zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('manifest.json', manifest_path.read_bytes())
            entries = sorted(artwork)
            if manifest.get('format') == springys.FORMAT2:
                entries.append(springys.CODE_ENTRY)
            for name in entries:
                path = source / name
                if name == springys.CODE_ENTRY:
                    resolved = path.resolve(strict=True)
                    if path.is_symlink() or not resolved.is_relative_to(source) or resolved != path.absolute():
                        raise ValueError('Tweak code must not contain symlinks or leave the package directory')
                    if not resolved.is_file() or resolved.stat().st_size > springys.MAX_CODE:
                        raise ValueError('tweak/main.js is missing or exceeds 256 KB')
                    archive.writestr(name, resolved.read_bytes())
                    continue
                springys._art_path(name)
                resolved = path.resolve(strict=True)
                if not resolved.is_relative_to(source) or not resolved.is_file() or path.is_symlink():
                    raise ValueError('Artwork must be a regular file inside the package directory')
                if resolved.stat().st_size > springys.MAX_ART:
                    raise ValueError('Artwork exceeds 2 MB')
                archive.writestr(name, resolved.read_bytes())
        metadata, _ = springys.inspect(temporary)
        # Exclusive creation prevents replacing an existing package.
        with open(temporary, 'rb') as src, open(destination, 'xb') as dst:
            import shutil
            shutil.copyfileobj(src, dst)
        return metadata
    finally:
        os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('build')
    p.add_argument('directory', type=Path)
    p.add_argument('output', type=Path)
    p = sub.add_parser('inspect')
    p.add_argument('package', type=Path)
    args = parser.parse_args()
    result = build(args.directory, args.output) if args.command == 'build' else springys.inspect(args.package)[0]
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
