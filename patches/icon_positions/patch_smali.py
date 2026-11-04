#!/usr/bin/env python3
"""Inject verified Spring 0.8.1 free-position hook calls into decoded smali."""
import argparse
import os
from pathlib import Path
import re

RENDER = 'smali/I1/h0.1.smali'
CONTROLLER = 'smali/E1/O1.smali'
SPRING = 'smali/x1.1/i1.1.smali'
STATUS = 'smali/I1/k0.1.smali'
FILES = 'smali/J1/I.smali'
SAPP_MANAGER = 'smali/J1/y.1.smali'


def method(text, start, transform):
    if text.count(start) != 1:
        raise ValueError('Expected one method: ' + start)
    first = text.index(start)
    end = text.index('.end method', first) + len('.end method')
    return text[:first] + transform(text[first:end]) + text[end:]


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Expected one patch anchor: ' + old[:100])
    return text.replace(old, new, 1)


def invoke_grid(text, profile, entry, row, page):
    pattern = (r'    iget ' + re.escape(row) + r', ' + re.escape(entry) + r', LE1/c;->b:I'
               r'(?:(?!\n\.end method).)*?' + r'    iget ' + re.escape(entry) + r', ' + re.escape(entry) + r', LE1/c;->c:I'
               r'(?:(?!\n\.end method).)*?' + r'    invoke-static \{' + re.escape(profile) + ', ' + re.escape(row) + ', ' + re.escape(entry) + r'\}, LE1/d4;->w\(LE1/i6;II\)LM1/b;')
    updated, count = re.subn(pattern, f'    invoke-static {{{profile}, {entry}, {page}}}, Lwinterx/layout/SpringHooks;->location(LE1/i6;LE1/c;I)LM1/b;', text, flags=re.S)
    if count != 1:
        raise ValueError('Unexpected Spring grid coordinate anchor: ' + str(count))
    return updated


def apply(root):
    paths = {name: Path(root) / name for name in (RENDER, CONTROLLER, SPRING, STATUS, FILES, SAPP_MANAGER)}
    contents = {name: path.read_text() for name, path in paths.items()}
    if os.environ.get('WINTERX_BUILD_TRUSTED_FILES') == '1':
        file_start = '.method public final f(Ljava/lang/String;)Ljava/io/File;'
        def resolve_files(m):
            anchor = file_start + '\n    .locals 7'
            body = ('\n    iget-object v0, p0, LJ1/I;->c:Ljava/io/File;\n'
                    '    invoke-static {v0, p1}, Lwinterx/runtime/TrustedFiles;->resolve(Ljava/io/File;Ljava/lang/String;)Ljava/io/File;\n'
                    '    move-result-object v0\n    if-eqz v0, :winterx_sandbox\n'
                    '    return-object v0\n    :winterx_sandbox')
            return replace_once(m, anchor, anchor + body)
        contents[FILES] = method(contents[FILES], file_start, resolve_files)
        protect_start = '.method public final b(Ljava/lang/String;)Ljava/io/File;'
        def protect_root(m):
            anchor = '    iget-object v0, p0, LJ1/I;->c:Ljava/io/File;'
            body = ('\n    invoke-static {v0, p1}, Lwinterx/runtime/TrustedFiles;->protectedRoot(Ljava/io/File;Ljava/io/File;)Z\n'
                    '    move-result v0\n    if-nez v0, :cond_0\n'
                    '    iget-object v0, p0, LJ1/I;->c:Ljava/io/File;')
            return replace_once(m, anchor, anchor + body)
        contents[FILES] = method(contents[FILES], protect_start, protect_root)
    if os.environ.get('WINTERX_BUILD_INBOX') == '1':
        constructor = '.method public constructor <init>(Lcom/guille/spring/LauncherActivity;Lx1/h0;Lx1/h0;LA1/a;Lx1/z;Lx1/h0;)V'
        def watch_inbox(m):
            return replace_once(m, '    return-void',
                '    invoke-static {p0}, Lwinterx/runtime/InboxMonitor;->start(LJ1/y;)V\n    return-void')
        contents[SAPP_MANAGER] = method(contents[SAPP_MANAGER], constructor, watch_inbox)
    # Renderer has separate row/column registers; leave its page-scroll offset unchanged.
    def render(m):
        pattern = r'    iget v8, v7, LE1/c;->b:I(?:(?!\n\.end method).)*?    iget v9, v7, LE1/c;->c:I(?:(?!\n\.end method).)*?    invoke-static \{v13, v8, v9\}, LE1/d4;->w\(LE1/i6;II\)LM1/b;'
        call = ('    invoke-static {v13, v7, v12, v14}, Lwinterx/animaper/Animaper;->location(LE1/i6;LE1/c;II)LM1/b;'
                if os.environ.get('WINTERX_BUILD_ANIMAPER') == '1' else
                '    invoke-static {v13, v7, v12}, Lwinterx/layout/SpringHooks;->location(LE1/i6;LE1/c;I)LM1/b;')
        result, count = re.subn(pattern, call, m, flags=re.S)
        if count != 1: raise ValueError('Unexpected renderer coordinate anchor')
        return result
    wallpaper_start = '.method public static h(Landroid/graphics/Canvas;Landroid/graphics/Paint;LE1/i6;Ljava/util/Map;Landroid/graphics/Bitmap;)V'
    def wallpaper(m):
        anchor = wallpaper_start + '\n    .locals 23'
        body = ('\n    move-object/from16 v0, p0\n    move-object/from16 v1, p2\n'
                '    invoke-static {v0, v1}, Lwinterx/safe/SafeAppearance;->wallpaper(Landroid/graphics/Canvas;LE1/i6;)Z\n'
                '    move-result v0\n    if-eqz v0, :winterx_normal_wallpaper\n'
                '    return-void\n    :winterx_normal_wallpaper')
        return replace_once(m, anchor, anchor + body)
    contents[RENDER] = method(contents[RENDER], wallpaper_start, wallpaper)
    status_start = '.method public final d(Landroid/graphics/Canvas;LE1/q6;LI1/I0;LI1/q1;Ljava/util/Map;ZZ)V'
    def status(m):
        old = '    return-void'
        count = m.count(old)
        if count < 1: raise ValueError('Status bar return not found')
        # p2 is reused for text in Spring's renderer. p1 remains its Canvas.
        new = ('    move-object/from16 v0, p1\n'
               '    invoke-static {v0}, Lwinterx/safe/SafeAppearance;->status(Landroid/graphics/Canvas;)V\n'
               '    return-void')
        return m.replace(old, new)
    contents[STATUS] = method(contents[STATUS], status_start, status)
    contents[RENDER] = method(contents[RENDER], '.method public static i0(LE1/q6;)Ljava/util/ArrayList;', render)
    contents[SPRING] = method(contents[SPRING], '.method public final o1(FF)LE1/A0;', lambda m: invoke_grid(m, 'v0', 'v7', 'v8', 'v2'))
    def position(m):
        # Save A0.c before p1 is reused for the icon object on secondary pages.
        anchor = '    iget p1, p1, LE1/A0;->c:I'
        m = replace_once(m, anchor, anchor + '\n    move v4, p1')
        first = '    iget v0, p1, LE1/c;->b:I'
        # Both branches share this sequence; mark each with its appropriate page.
        pattern = r'    iget v0, p1, LE1/c;->b:I(?:(?!\n\.end method).)*?    iget p1, p1, LE1/c;->c:I(?:(?!\n\.end method).)*?    invoke-static \{v1, v0, p1\}, LE1/d4;->w\(LE1/i6;II\)LM1/b;'
        matches = list(re.finditer(pattern, m, flags=re.S))
        if len(matches) != 2: raise ValueError('Unexpected home animation anchors')
        replacement = '    invoke-static {v1, p1, v4}, Lwinterx/layout/SpringHooks;->location(LE1/i6;LE1/c;I)LM1/b;'
        # Second branch corresponds to page zero.
        second = matches[1]
        m = m[:second.start()] + '    const/4 v4, 0x0\n' + replacement + m[second.end():]
        first_match = re.search(pattern, m, flags=re.S)
        return m[:first_match.start()] + replacement + m[first_match.end():]
    contents[SPRING] = method(contents[SPRING], '.method public final n4(LE1/A0;)LM1/b;', position)
    def insert_entry(signature, locals_decl, body):
        def apply_entry(m):
            anchor = signature + '\n    ' + locals_decl
            return replace_once(m, anchor, anchor + '\n\n' + body)
        return apply_entry
    start = '.method public final o(IIFFJ)V'
    contents[CONTROLLER] = method(contents[CONTROLLER], start, insert_entry(start, '.locals 12', '    invoke-static {p0, p1, p2}, Lwinterx/layout/SpringHooks;->begin(LE1/O1;II)V'))
    start = '.method public final x(J)V'
    contents[CONTROLLER] = method(contents[CONTROLLER], start, insert_entry(start, '.locals 9', '    invoke-static {p0}, Lwinterx/layout/SpringHooks;->beforeDrop(LE1/O1;)V'))
    for name, locals_decl in [('v(II)LM1/b;', '.locals 5'), ('w(IIJLjava/lang/String;)LM1/b;', '.locals 1')]:
        start = '.method public final ' + name
        body = ('    invoke-static {p0, p1, p2}, Lwinterx/layout/SpringHooks;->editLocation(LE1/O1;II)LM1/b;\n'
                '    move-result-object v0\n    if-eqz v0, :winterx_grid_fallback\n'
                '    return-object v0\n    :winterx_grid_fallback')
        contents[CONTROLLER] = method(contents[CONTROLLER], start, insert_entry(start, locals_decl, body))
    for name, text in contents.items():
        paths[name].write_text(text)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('decoded', type=Path)
    apply(p.parse_args().decoded)
