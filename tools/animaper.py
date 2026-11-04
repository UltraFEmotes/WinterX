"""Animaper settings stored alongside WinterX's other tweak markers."""
from pathlib import Path
import os
import tempfile
import zipfile

MODES = ('wave', 'cascade', 'bounce', 'orbit', 'ripple', 'columns', 'fan', 'zigzag')


def set_mode(spring_data, mode):
    if mode not in MODES:
        raise ValueError('Unknown Animaper effect')
    folder = Path(spring_data) / 'files/ruby'
    if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
        raise ValueError('Invalid WinterX data folder')
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / 'animaper.mode'
    if destination.is_symlink(): raise ValueError('Invalid Animaper settings file')
    fd, temporary = tempfile.mkstemp(prefix='.animaper-', dir=folder)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            out.write(mode + '\n'); out.flush(); os.fsync(out.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
    return {'ok': True, 'message': 'Animaper effect set to ' + mode.title()}


def supported_by(apk):
    try:
        with zipfile.ZipFile(apk) as archive:
            return (b'winterx/animaper/Animaper' in archive.read('classes.dex') and
                    b'winterx/animaper/Animaper' in archive.read('classes3.dex'))
    except (OSError, KeyError, zipfile.BadZipFile):
        return False
