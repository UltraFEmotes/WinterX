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


def freeme_supported_by(apk):
    """Require the sparse-grid ABI and its native hooks, not the older pixel-position test."""
    try:
        with zipfile.ZipFile(apk) as archive:
            return (b'freeme-grid-v1' in archive.read('classes3.dex')
                    and b'winterx/layout/FreeMe' in archive.read('classes.dex')
                    and b'winterx/layout/SpringHooks' in archive.read('classes.dex'))
    except (OSError, KeyError, zipfile.BadZipFile):
        return False


def dockin_supported_by(apk):
    """Require the native dock ABI, layout/controller hooks and actual launch-size integration."""
    try:
        with zipfile.ZipFile(apk) as archive:
            primary = archive.read('classes.dex')
            helpers = archive.read('classes3.dex')
            return (b'dockin-native-v1' in helpers and b'winterx/layout/DockMotion' in helpers
                    and b'winterx/layout/DockIn' in primary and b'launchSize' in primary
                    and b'winterx/layout/SpringHooks' in primary)
    except (OSError, KeyError, zipfile.BadZipFile):
        return False


def snowyhome_supported_by(apk):
    """Helpers alone are insufficient: the opt-in renderer hooks must also be packaged."""
    try:
        with zipfile.ZipFile(apk) as archive:
            primary, helpers = archive.read('classes.dex'), archive.read('classes3.dex')
            return (b'snowyhome-render-v1' in helpers and b'winterx/snowy/SnowySettings' in helpers
                    and b'winterx/snowy/SnowyHome' in primary and b'winterxStockIcon' in primary
                    and b'hiddenLabels' in primary and b'artwork' in primary)
    except (OSError, KeyError, zipfile.BadZipFile):
        return False
