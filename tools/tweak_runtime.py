"""Capability detection for the development third-party tweak engine (no launch/install)."""
import hashlib
import json
from pathlib import Path
import zipfile


def supported_by(apk):
    try:
        with zipfile.ZipFile(apk) as archive:
            helpers = archive.read('classes3.dex')
            return (b'winterx/tweaks/TweakHost' in helpers and b'winterx/tweaks/TweakSettings' in helpers
                    and b'winterxCreate' in archive.read('classes.dex'))
    except (OSError, KeyError, zipfile.BadZipFile):
        return False


def active_engine(state, is_running):
    """Only a hash-verified RUNNING overlay proves capability, not a selected APK."""
    try:
        record = json.loads((Path(state) / 'active.json').read_text(encoding='utf-8'))
        apk = Path(record['apk'])
        digest = hashlib.sha256()
        with apk.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        if digest.hexdigest() != record['apk_sha256'] or not is_running(int(record['pid']), apk, Path(state) / 'overlay/android'):
            return None
        return apk
    except (OSError, ValueError, KeyError, TypeError):
        return None


def coloredbar_supported_by(apk):
    try:
        with zipfile.ZipFile(apk) as archive:
            return (b'coloredbar.exclusions.json' in archive.read('classes3.dex')
                    and b'winterx/coloredbar/ColoredBar' in archive.read('classes.dex'))
    except (OSError, KeyError, zipfile.BadZipFile):
        return False
