#!/usr/bin/env python3
"""Spring's code under another package name, for the rootless clone that installs beside the original.

Only the bare package literal changes: Spring compares app IDs against "com.guille.spring" to recognise itself in its
app lists. Provider authorities and its permission are built at run time from getPackageName(), and its classes keep
their names (only the manifest's package changes). Every other string mentioning the package was reviewed and is
listed below; anything new stops the build so it can be reviewed too.
"""
import re

PACKAGE = 'com.guille.spring'
# Class names (in Class.forName/ComponentName strings and Kotlin's cast messages) and fixed intent/channel names.
REVIEWED = re.compile(r'^(?:null cannot be cast to non-null type )?com\.guille\.spring(?:\.[a-z0-9_]+)*\.[A-Z][\w$.]*$'
                      r'|^com\.guille\.spring\.(?:CLOCK_FIRE|LOCK_RAISE|OPEN_MESSAGES|whatsapp|messages)$'
                      r'|^store/com\.guille\.spring@1$')       # Spring's own update check: still the original app
LITERAL = re.compile(r'^(\s*const-string(?:/jumbo)? [vp]\d+, )"([^"\n]*com\.guille\.spring[^"\n]*)"$', re.M)


def rename(text, package):
    """(new smali text, literals renamed, unreviewed literals)."""
    renamed, unknown = 0, []
    def replace(match):
        nonlocal renamed
        value = match.group(2)
        if value == PACKAGE:
            renamed += 1
            return match.group(1) + '"' + package + '"'
        if not REVIEWED.match(value): unknown.append(value)
        return match.group(0)
    return LITERAL.sub(replace, text), renamed, unknown
