"""Prepare a separate Mac.APK root without modifying the signed Spring bundle.

The overlay deliberately shares Spring's data and SD card. It must only be
used while the original Spring process is stopped; never run both against the
same data at once. This module creates paths only and does not launch Spring.
"""
from pathlib import Path


def prepare(base, overlay_parent):
    base = Path(base).resolve(strict=True)
    root = Path(overlay_parent).resolve() / 'android'
    if root == base or base in root.parents or root in base.parents:
        raise ValueError('Overlay must be separate from the original Mac.APK root')
    data = base / 'data/data'
    system = base / 'data/system'
    sdcard = base / 'sdcard'
    for path in (data, system, sdcard):
        if not path.is_dir():
            raise ValueError('Missing Mac.APK directory: ' + str(path))
    targets = ((root / 'data/data', data), (root / 'data/system', system), (root / 'sdcard', sdcard))
    # Refuse unknown pre-existing paths rather than deleting or redirecting them.
    for link, target in targets:
        if link.is_symlink():
            if link.resolve() != target.resolve():
                raise ValueError('Overlay link points somewhere unexpected: ' + str(link))
        elif link.exists():
            raise ValueError('Overlay path already exists and is not a link: ' + str(link))
    (root / 'data').mkdir(parents=True, exist_ok=True)
    for link, target in targets:
        if not link.is_symlink():
            link.symlink_to(target, target_is_directory=True)
    (root / 'data/app').mkdir(parents=True, exist_ok=True)
    return root
