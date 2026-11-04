#!/usr/bin/env python3
"""Prepare WinterX Safe Mode for the next jailbreak when Spring cannot boot."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'patches'))
import macapk_controls as control
import macapk_jailbreak as jailbreak


def main():
    if control.spring_pids():
        raise RuntimeError('Close the entire Spring Launcher first, then run this command again.')
    if jailbreak.digest(jailbreak.ORIGINAL) != jailbreak.ORIGINAL_SHA:
        raise RuntimeError('The installed Spring version is not supported by this WinterX build.')
    if jailbreak.digest(jailbreak.PATCHED) != jailbreak.PATCH_SHA:
        raise RuntimeError('The WinterX build failed verification.')
    ruby = jailbreak.DATA / 'files/ruby'
    if ruby.is_symlink() or (ruby.exists() and not ruby.is_dir()):
        raise RuntimeError('The WinterX state directory is not safe to modify.')
    ruby.mkdir(parents=True, exist_ok=True)
    marker = ruby / 'safe-mode.enabled'
    if marker.is_symlink() or (marker.exists() and not marker.is_file()):
        raise RuntimeError('Unexpected Safe Mode marker.')
    marker.touch(exist_ok=True)
    print('Safe Mode is prepared. Open Spring Launcher, start the Ruby bridge, and jailbreak with WinterX.')
    print('Once Spring starts, open Ruby to remove a tweak or leave Safe Mode.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Could not prepare Safe Mode:', exc, file=sys.stderr)
        sys.exit(1)
