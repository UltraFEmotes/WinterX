#!/usr/bin/env python3
"""Wrap Spring 0.8.1's per-app artwork maps without modifying stock bitmap caches."""
import re
from pathlib import Path


def patch(text):
    for name, signature, expected in (
        ('g', '(Landroid/graphics/Canvas;LE1/q6;LI1/I0;Ljava/lang/String;J)V', 14),
        ('m', '(Landroid/graphics/Canvas;LE1/q6;LI1/I0;Ljava/lang/String;JZ)V', 18),
    ):
        start = '.method public final ' + name + signature
        if text.count(start) != 1:
            raise ValueError('ColoredBar dispatcher anchor missing: ' + start)
        first = text.index(start)
        end = text.index('.end method', first)
        body = text[first:end]
        local = re.search(r'    \.locals (\d+)', body)
        count = int(local.group(1))
        # Extra locals survive Spring's reuse of p4. Never guess an app from the
        # currently selected one: transitions/snapshots render other apps too.
        body = body.replace(local.group(0), '    .locals ' + str(count + 2) + '\n'
                            + '    move-object/16 v' + str(count + 1) + ', p4\n'
                            + '    invoke-static/range {p2 .. p2}, Lwinterx/coloredbar/ColoredBar;->observe(LE1/q6;)V', 1)
        pattern = r'^    iget-object (v\d+), (v\d+|p0), LI1/T0;->\w+:Ljava/util/Map;$'
        def wrap(match):
            register = match.group(1)
            return (match.group(0) + '\n    move-object/16 v' + str(count) + ', ' + register
                    + '\n    invoke-static/range {v' + str(count) + ' .. v' + str(count + 1)
                    + '}, Lwinterx/appearance/RubyAppearance;->assets(Ljava/util/Map;Ljava/lang/String;)Ljava/util/Map;'
                    + '\n    move-result-object ' + register
                    + '\n    move-object/16 v' + str(count) + ', ' + register
                    + '\n    invoke-static/range {v' + str(count) + ' .. v' + str(count + 1)
                    + '}, Lwinterx/coloredbar/ColoredBar;->assets(Ljava/util/Map;Ljava/lang/String;)Ljava/util/Map;'
                    + '\n    move-result-object ' + register)
        body, found = re.subn(pattern, wrap, body, flags=re.M)
        if found != expected:
            raise ValueError('Unexpected ColoredBar map count in ' + name + ': ' + str(found))
        text = text[:first] + body + text[end:]
    return text


def patch_settings(text):
    """Settings bypasses T0's maps via S0; tint returned artwork, never its cache."""
    start = '.method public final get(Ljava/lang/Object;)Ljava/lang/Object;'
    if text.count(start) != 1: raise ValueError('ColoredBar Settings loader anchor missing')
    first = text.index(start)
    end = text.index('.end method', first)
    body = text[first:end]
    if body.count('    .locals 2') != 1: raise ValueError('Unexpected Settings loader locals')
    body = body.replace('    .locals 2', '    .locals 4\n    move-object v2, p1', 1)
    def tint(match):
        register = match.group(1)
        return ('    move-object v3, ' + register
                + '\n    invoke-static {v2, v3}, Lwinterx/coloredbar/ColoredBar;->settingsAsset(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;'
                + '\n    move-result-object ' + register + '\n' + match.group(0))
    body, found = re.subn(r'^    return-object (v1|p1)$', tint, body, flags=re.M)
    if found != 2: raise ValueError('Unexpected Settings loader return count: ' + str(found))
    return text[:first] + body + text[end:]


def patch_appstore(text):
    """The deferred App Store renderer also reads T0.p outside its dispatchers."""
    start = '.method private final d(Ljava/lang/Object;)Ljava/lang/Object;'
    if text.count(start) != 1: raise ValueError('ColoredBar App Store renderer anchor missing')
    first = text.index(start)
    end = text.index('.end method', first)
    body = text[first:end]
    if body.count('    .locals 95') != 1 or body.count('"ios6/apps/appstore/NavBar.png"') != 1:
        raise ValueError('Unexpected App Store renderer layout')
    body = body.replace('    .locals 95', '    .locals 97\n    const-string v96, "appstore"', 1)
    anchor = '    iget-object v8, v2, LI1/T0;->p:Ljava/util/Map;'
    if body.count(anchor) != 1: raise ValueError('App Store artwork map anchor missing')
    body = body.replace(anchor, anchor + '\n    move-object/16 v95, v8'
                        + '\n    invoke-static/range {v95 .. v96}, Lwinterx/coloredbar/ColoredBar;->assets(Ljava/util/Map;Ljava/lang/String;)Ljava/util/Map;'
                        + '\n    move-result-object v8', 1)
    return text[:first] + body + text[end:]


def apply(decoded):
    for name, update in (('T0', patch), ('S0', patch_settings), ('N0', patch_appstore)):
        path = Path(decoded) / ('smali/I1/' + name + '.smali')
        path.write_text(update(path.read_text()))
