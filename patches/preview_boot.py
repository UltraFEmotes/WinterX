#!/usr/bin/env python3
"""Add only the WinterX boot receipt and splash to decoded Spring 0.9 Preview 1.

This bootstrap is for compatibility research; it does not implement tweaks,
Safe Mode, app protection, or the welcome alert and must not be deployed as a
complete jailbreak.
"""
import argparse
from pathlib import Path
import settings_test as old


def method(source, signature):
    start = source.index(signature)
    end = source.index('.end method', start) + len('.end method')
    return source[start:end]


def apply(decoded):
    decoded = Path(decoded)
    activity = decoded / 'smali/com/guille/spring/LauncherActivity.smali'
    before = activity.read_text()
    if before.count(old.BOOT_MARKER) != 1:
        raise ValueError('Unexpected preview Activity boot entry')
    after = before.replace(old.BOOT_MARKER, old.BOOT_PATCH, 1)
    start = after.index('.method public onCreate(Landroid/os/Bundle;)V')
    end = after.index('.end method', start)
    on_create = after[start:end]
    if on_create.count(old.CONTENT_CALL) != 3:
        raise ValueError('Unexpected preview Activity content paths')
    after = after[:start] + on_create.replace(old.CONTENT_CALL, old.CONTENT_PATCH) + after[end:]
    folder = decoded / 'smali/ruby'
    if folder.exists():
        raise ValueError('Ruby hooks already exist')
    hooks = ('.class public final Lruby/RubyHooks;\n.super Ljava/lang/Object;\n\n' +
             method(old.HOOKS, '.method public static boot(Landroid/app/Activity;)V') + '\n\n' +
             method(old.HOOKS, '.method public static showBoot(Landroid/app/Activity;)V') + '\n')
    folder.mkdir()
    (folder / 'RubyHooks.smali').write_text(hooks)
    (folder / 'BootDismiss.smali').write_text(old.BOOT_DISMISS)
    activity.write_text(after)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('decoded', type=Path)
    apply(parser.parse_args().decoded)
