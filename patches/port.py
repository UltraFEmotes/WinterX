#!/usr/bin/env python3
"""Apply WinterX's Spring 0.8.1 smali patches to another Spring version through a name map.

The patch scripts (settings_test.py, icon_positions/patch_smali.py and the modules it uses) are written against 0.8.1:
file paths, method signatures, anchors and inserted code all use its obfuscated names, and some anchors also depend
on its compiler's registers, labels and line numbers. This runs them unchanged against another decoded Spring with:

* every name in paths, signatures, anchors, replacements and regex patterns translated through the map;
* an anchor that no longer matches exactly retried with any registers, labels and line numbers, carrying the
  registers it finds over into the inserted code. Every such retry is reported, because a register the patch
  only *uses* (rather than finds in the anchor) may hold something else in the new version.

    python3 patches/port.py MAP.json DECODED [--report report.json]
"""
import argparse
import builtins
import json
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'icon_positions'), str(HERE.parent / 'tools')]
import spring_map

REGISTER = re.compile(r'\b([vp]\d+)\b')
LABEL = re.compile(r':(cond|goto|try_start|try_end|catch|catchall|pswitch|sswitch|array)_[0-9a-f]+\b')
LINE = re.compile(r'^    \.line \d+\n', re.M)


class Port:
    def __init__(self, mapping, decoded):
        self.t = spring_map.Translator(mapping)
        self.decoded = Path(decoded)
        self.files = {}                            # class name -> path inside the decoded tree
        for directory, _, names in os.walk(self.decoded):
            for name in names:
                if name.endswith('.smali'):
                    path = Path(directory) / name
                    head = re.search(r'^\.class [^\n]*?L([^;]+);', path.read_text(errors='ignore'), re.M)
                    if head: self.files[head.group(1)] = path
        self.reverse = {v: k for k, v in mapping['classes'].items()}
        self.report = []
        self.failures = []                         # survey mode: what didn't port, instead of stopping
        self.survey = False

    # ----- names -----

    def text(self, value): return self.t.text(value) if isinstance(value, str) else value

    def signature(self, line, owner):
        """A '.method ... name(desc)' line of a 0.8.1 class, as the new version declares it (its own modifiers)."""
        m = re.match(r'(\.method (?:[a-z-]+ )*)(\S+?)(\(.*)$', line.split('\n')[0])
        if not m: return self.text(line)
        member = self.t.member(owner, m.group(2), m.group(3))
        target, mapped = member[1:].split(';->', 1)
        rest = line[len(line.split('\n')[0]):]
        declared = self.declaration(target, mapped)
        self.pshift = 0
        if declared:
            was, now = ' static ' in m.group(1) + ' ', ' static ' in declared + ' '
            self.pshift = 1 if was and not now else -1 if now and not was else 0
            return declared + self.shift(self.text(rest))
        return m.group(1) + mapped + self.text(rest)

    def declaration(self, cls, member):
        """The new version's own '.method ... member' line, when that class declares it."""
        path = self.files.get(cls)
        if path is None: return None
        found = re.search(r'^(\.method (?:[a-z-]+ )*)' + re.escape(member) + r'$', path.read_text(), re.M)
        return found.group(0) if found else None

    def shift(self, code):
        """Parameter registers move by one when a method became an instance (or static) method."""
        if not getattr(self, 'pshift', 0): return code
        return re.sub(r'\bp(\d+)\b', lambda r: 'p%d' % (int(r.group(1)) + self.pshift), code)

    def path(self, relative):
        """'smali/x1.1/i1.1.smali' (0.8.1) -> where that class lives in the new tree, relative to it."""
        name = re.sub(r'^smali(?:_classes\d+)?/', '', relative)[:-len('.smali')]
        name = re.sub(r'\.1(?=/|$)', '', name)       # apktool's case-collision suffixes
        target = self.files.get(self.t.cls(name))
        if target is None: raise ValueError('No class for ' + relative + ' (' + self.t.cls(name) + ')')
        return str(target.relative_to(self.decoded))

    def regex(self, pattern):
        """Translate Spring names inside a regex, where a descriptor's parentheses are escaped and groups aren't."""
        held = pattern.replace(r'\(', '\x01').replace(r'\)', '\x02').replace(r'\$', '\x03')
        token = re.compile(r'L([^;\s()\[\x01\x02"\\]+);(?:->([^\x01:\s"\\]+)(\x01[^\x02\s"]*\x02[^\s,}"\\\x01()|]+|:[^\s,}"\\()|]+))?')
        def swap(m):
            owner, name, rest = m.group(1), m.group(2), m.group(3)
            if name is None: return 'L' + self.t.cls(owner) + ';'
            plain = rest.replace('\x01', '(').replace('\x02', ')').replace('\x03', '$')
            mapped = self.t.member(owner, name, plain)
            return mapped.replace('(', '\x01').replace(')', '\x02')
        return token.sub(swap, held).replace('\x01', r'\(').replace('\x02', r'\)').replace('\x03', r'\$')

    def owner_of(self, text):
        """The 0.8.1 name of the class a (new-version) smali file declares."""
        head = re.search(r'^\.class [^\n]*?L([^;]+);', text, re.M)
        return self.reverse.get(head.group(1), head.group(1)) if head else None

    def moved(self, line, owner):
        """The new class a 0.8.1 method now lives in, when that isn't its class's counterpart."""
        m = re.match(r'\.method (?:[a-z-]+ )*(\S+?)(\(.*)$', line.split('\n')[0])
        if not m: return None
        key = 'L%s;->%s%s' % (owner, m.group(1), m.group(2))
        target = self.t.members.get(key)
        if target is None: return None
        new_owner = target[1:].split(';->', 1)[0]
        return new_owner if new_owner != self.t.cls(owner) else None

    def in_class(self, text, start, owner, transform):
        """Apply a method transform to a moved method; anchors inside still use the 0.8.1 owner's names."""
        line = self.signature(start, owner).split('\n')[0]
        if text.count(line) != 1: raise ValueError('Expected one moved method: ' + line)
        self.current_owner = owner
        first = text.index(line); end = text.index('.end method', first) + len('.end method')
        return text[:first] + transform(text[first:end]) + text[end:]

    # ----- the final pass -----

    def snapshot(self):
        """Remember every file as the new version shipped it, to tell inserted lines from its own."""
        self.original = {path: path.read_text(errors='ignore') for path in self.files.values()}

    @staticmethod
    def registers(descriptor, static):
        """[(first register, width, type)] for each parameter: p0 is 'this' for instance methods."""
        types = re.findall(r'\[*(?:L[^;]+;|[ZBCSIJFD])', descriptor[1:descriptor.index(')')])
        out, n = [], 0 if static else 1
        for t in types:
            width = 2 if t in ('J', 'D') else 1
            out.append((n, width, t)); n += width
        return out, n

    def param_map(self, old_line, new_line):
        """Old pN -> new pM, aligning the two parameter lists by their (translated) types."""
        o = re.search(r'(\(.*)$', old_line).group(1); n = re.search(r'(\(.*)$', new_line).group(1)
        os_, ns = ' static ' in old_line, ' static ' in new_line
        (old, old_count), (new, new_count) = self.registers(o, os_), self.registers(n, ns)
        mapping = {} if os_ else {'p0': None if ns else 'p0'}
        a = [self.t.desc(t) for _, _, t in old]; b = [t for _, _, t in new]
        for i, j in spring_map.lcs(a, b):
            for k in range(old[i][1]): mapping['p%d' % (old[i][0] + k)] = 'p%d' % (new[j][0] + k)
        return mapping, new_count - 1

    def finish(self):
        """Translate, once, every line the 0.8.1 patches added; widen pass-through calls to the full new parameters."""
        import difflib
        for cls, path in list(self.files.items()) + [(None, p) for p in (self.decoded / 'smali').rglob('*.smali') if p not in self.files.values()]:
            text = path.read_text(errors='ignore')
            before = self.original.get(path)
            if before == text: continue
            owner_old = self.owner_of(text) if text.lstrip().startswith('.class') else None
            lines = text.split('\n')
            added = self.added_lines(before, lines)
            vanished = self.vanished(before, lines) if before is not None else {}
            out, mapping, last, method_new = [], {}, None, None
            for i, line in enumerate(lines):
                if line.startswith('.method '):
                    if i in self.renamed:                                    # keep the new version's real signature
                        name = re.match(r'\.method (?:[a-z-]+ )*(\S+?)\(', line).group(1)
                        original = self.renamed[i]
                        line = re.sub(r'(\.method (?:[a-z-]+ )*)\S+?\(', lambda r: r.group(1) + name + '(', original, count=1)
                    elif i in added and owner_old:
                        line = self.signature(line, owner_old)
                        name = re.match(r'\.method (?:[a-z-]+ )*(\S+?)\(', line).group(1)
                        if name in vanished: line = vanished[name]           # a wrapper keeps the original's exact signature
                        elif name.startswith('winterxStock') and i in self.stock_of:
                            line = re.sub(r'(\.method (?:[a-z-]+ )*)\S+?\(', lambda r: r.group(1) + name + '(', self.stock_of[i], count=1)
                    method_new = line
                    old_line = self.old_method_line(owner_old, line) if owner_old else None
                    mapping, last = self.param_map(old_line, line) if old_line else ({}, None)
                elif i in added:
                    line = self.t.text(line)
                    if mapping:
                        if last is not None and re.search(r'/range \{p0 \.\. p\d+\}, L[^;]+;->winterxStock', line):
                            line = re.sub(r'\{p0 \.\. p\d+\}', '{p0 .. p%d}' % last, line)
                        else:
                            line = re.sub(r'\bp\d+\b', lambda r: mapping.get(r.group(0)) or r.group(0), line)
                out.append(line)
            result = '\n'.join(out)
            # Calls to a renamed stock method use its real (new-version) signature.
            stock = dict(re.findall(r'^\.method (?:[a-z-]+ )*(winterxStock\w+)(\(.*)$', result, re.M))
            if stock:
                result = re.sub(r'->(winterxStock\w+)\([^)\s]*\)[^\s,}]+', lambda r: '->' + r.group(1) + stock.get(r.group(1), r.group(0)[len(r.group(1)) + 2:]) if r.group(1) in stock else r.group(0), result)
            path.write_text(result)

    @staticmethod
    def blocks(lines):
        """[(start, end, declaration)] of each method, plus the text outside methods as declaration None."""
        out, start = [], None
        for i, line in enumerate(lines):
            if line.startswith('.method '): start = i
            elif line.startswith('.end method') and start is not None: out.append((start, i + 1, lines[start])); start = None
        return out

    def added_lines(self, before, lines):
        """Indexes of lines the patches added, compared method by method (fast on Spring's huge classes)."""
        import difflib
        if before is None: return set(range(len(lines)))
        old_lines = before.split('\n')
        old_methods = {}
        for s0, e0, decl in self.blocks(old_lines): old_methods.setdefault(decl, old_lines[s0:e0])
        old_bodies = {tuple(body[1:]): decl for decl, body in old_methods.items()}
        now_decls = set(l for l in lines if l.startswith('.method '))
        gone = {decl: body for decl, body in old_methods.items() if decl not in now_decls}
        added, covered = set(), set()
        self.renamed = {}                                                   # line -> the new version's own declaration
        for s0, e0, decl in self.blocks(lines):
            covered.update(range(s0, e0))
            body = lines[s0:e0]
            original = old_methods.get(decl)
            if original == body: continue
            if original is None:
                if tuple(body[1:]) in old_bodies:                              # a renamed stock method
                    added.add(s0); self.renamed[s0] = old_bodies[tuple(body[1:])]; continue
                # A renamed *and* edited stock method: diff it against the vanished original it overlaps most,
                # so Spring's own lines are never mistaken for inserted (0.8.1) code.
                mine = set(body[1:]); best, score = None, 0.0
                for decl_old, old_body in gone.items():
                    other = set(old_body[1:]); overlap = len(mine & other) / (len(mine | other) or 1)
                    if overlap > score: best, score = decl_old, overlap
                if best is None or score < 0.5:
                    added.update(range(s0, e0)); continue                      # a new method
                original = gone[best]; added.add(s0)
                matcher = difflib.SequenceMatcher(None, original, body, autojunk=False)
                same = set()
                for block in matcher.get_matching_blocks(): same.update(range(block.b, block.b + block.size))
                added.update(s0 + i for i in range(1, len(body)) if i not in same)
                continue
            matcher = difflib.SequenceMatcher(None, original, body, autojunk=False)
            same = set()
            for block in matcher.get_matching_blocks(): same.update(range(block.b, block.b + block.size))
            added.update(s0 + i for i in range(len(body)) if i not in same)
        inside = set()
        for a, b, _ in self.blocks(old_lines): inside.update(range(a, b))
        outside_old = set(l for i, l in enumerate(old_lines) if i not in inside)
        added.update(i for i in range(len(lines)) if i not in covered and lines[i] not in outside_old)
        return added

    def vanished(self, before, lines):
        """Original methods whose declaration no longer appears (renamed to winterxStock... or wrapped): name -> declaration.
        Also pairs each added winterxStock method with the vanished original its body overlaps most (self.stock_of)."""
        old_lines = before.split('\n'); now = set(l for l in lines if l.startswith('.method '))
        gone = {}
        for a, b, decl in self.blocks(old_lines):
            if decl not in now: gone[decl] = set(old_lines[a + 1:b])
        self.stock_of = {}
        for a, b, decl in self.blocks(lines):
            if ' winterxStock' in decl and gone:
                body = set(lines[a + 1:b])
                best = max(gone, key=lambda d: len(body & gone[d]) / (len(body | gone[d]) or 1))
                self.stock_of[a] = best
        names = {}
        for decl in gone:
            n = re.match(r'\.method (?:[a-z-]+ )*(\S+?)\(', decl).group(1); names.setdefault(n, decl)
        return names

    def old_method_line(self, owner_old, new_line):
        """The 0.8.1 declaration a new-version method corresponds to (through the member map, or itself for new ones)."""
        m = re.match(r'(\.method (?:[a-z-]+ )*)(\S+?)(\(.*)$', new_line)
        if not m: return None
        if not hasattr(self, 'reverse_members'):
            self.reverse_members = {v: k for k, v in self.t.members.items()}
        target = 'L%s;->%s%s' % (self.t.cls(owner_old), m.group(2), m.group(3))
        old = self.reverse_members.get(target)
        return m.group(1) + old.split(';->', 1)[1] if old else None

    def located(self, decoded):
        """A Path whose / turns a 0.8.1 'smali/...smali' path into the new version's file."""
        port, base = self, type(Path())
        class Located(base):
            def __truediv__(self, other):
                if isinstance(other, str) and re.match(r'^smali.*\.smali$', other): return Path(port.decoded / port.path(other))
                return Located(base.__truediv__(self, other))
        return Located(decoded)

    # ----- matching -----

    def flexible(self, old):
        """A regex for an anchor with any registers, labels and line numbers (registers captured consistently)."""
        old = LINE.sub('', old)
        pattern, seen, last = '', {}, 0
        for m in re.finditer(r'\.locals \d+|\b[vp]\d+\b|:(?:cond|goto|try_start|try_end|catch|catchall|pswitch|sswitch|array)_[0-9a-f]+\b', old):
            pattern += re.escape(old[last:m.start()])
            token = m.group(0)
            if token.startswith('.locals'): pattern += r'\.locals (?P<locals>\d+)'
            elif token.startswith(':'): pattern += r':[a-z_]+_[0-9a-f]+'
            elif token in seen: pattern += '(?P=r%d)' % seen[token]
            else: seen[token] = len(seen); pattern += r'(?P<r%d>[vp]\d+)' % seen[token]
            last = m.end()
        pattern += re.escape(old[last:])
        pattern = pattern.replace(r'\n', r'\n(?:    \.line \d+\n)?')
        return re.compile(pattern), {v: k for k, v in seen.items()}

    def replace_once(self, text, old, new, where='', owner=None):
        """old/new are 0.8.1 text; translated here, once (a '.method' line by its 0.8.1 owner)."""
        # The anchor is found in the new version's terms; inserted code stays in 0.8.1 terms until finish().
        old = self.signature(old, owner) if owner and old.startswith('.method') else self.shift(self.text(old))
        if owner and new.startswith('.method'):
            first, rest = (new.split('\n', 1) + [''])[:2]
            if self.signature(first, owner) == old.split('\n')[0]: new = old.split('\n')[0] + ('\n' + rest if rest else '')
        if text.count(old) == 1: return text.replace(old, new, 1)
        regex, names = self.flexible(old)
        found = list(regex.finditer(text))
        if len(found) != 1:
            raise ValueError('%s: anchor not found (%d flexible matches): %s' % (where, len(found), old.strip()[:160]))
        match = found[0]
        groups = match.groupdict()
        if groups.get('locals') is not None:
            locals_now = groups.pop('locals')
            new = re.sub(r'\.locals \d+', '.locals ' + locals_now, new, count=1)
        else: groups.pop('locals', None)
        renames = {names[int(k[1:])]: v for k, v in groups.items()}
        changed = {k: v for k, v in renames.items() if k != v}
        adapted = REGISTER.sub(lambda m: renames.get(m.group(1), m.group(1)), new) if changed else new
        scratch = sorted(set(REGISTER.findall(new)) - set(renames))
        self.report.append({'where': where, 'anchor': old.strip()[:120], 'registers': changed, 'unchecked': scratch})
        return text[:match.start()] + adapted + text[match.end():]


def install(port):
    """Point the patch scripts at the new version."""
    import patch_smali, settings_test, coloredbar
    modules = [patch_smali, settings_test, coloredbar]
    for name in ('patch_dockin', 'patch_snowy', 'patch_messageplus', 'patch_rendering', 'patch_animaper', 'patch_actions'):
        modules.append(__import__(name))
    # Modules keep working in 0.8.1 terms; files are found through Located paths when opened.
    for module in (patch_smali, coloredbar): module.Path = lambda *a: port.located(Path(*a))
    # The helpers every module receives or calls.
    def method(text, start, transform):
        owner = port.owner_of(text)
        try:
            if start.startswith('.method'):
                moved = port.moved(start, owner)
                if moved is not None:                         # 0.9 put this method in another class
                    path = port.files[moved]; other = path.read_text()
                    path.write_text(port.in_class(other, start, owner, transform))
                    return text
            raw = start
            start = port.signature(start, owner) if start.startswith('.method') else port.text(start)
            # A method an earlier patch inserted (DockIn's winterxStockR, ...) stays in 0.8.1 terms until finish().
            if text.count(start) != 1 and re.match(r'\.method (?:[a-z-]+ )*winterx', raw) and text.count(raw) == 1:
                start = raw
            if text.count(start) != 1 and start.startswith('.method'):
                start = start.split('\n')[0]                    # the method line alone; .locals may differ
            if text.count(start) != 1: raise ValueError('Expected one method: ' + start)
            first = text.index(start); end = text.index('.end method', first) + len('.end method')
            port.current_owner = owner
            return text[:first] + transform(text[first:end]) + text[end:]
        except Exception as failure:
            if not port.survey: raise
            port.failures.append({'class': owner, 'method': start.split('\n')[0][:140], 'error': str(failure)[:300]})
            return text
    def replace_once(text, old, new):
        # A whole file names its own class; a method body uses the class of the method() call around it.
        owner = port.owner_of(text) if text.lstrip().startswith('.class') else getattr(port, 'current_owner', None)
        try:
            if owner and old.startswith('.method') and text.lstrip().startswith('.class') and port.moved(old, owner):
                path = port.files[port.moved(old, owner)]     # a moved method: patch it where it lives now
                path.write_text(port.replace_once(path.read_text(), old, new, where='moved method of ' + owner, owner=owner))
                return text
            return port.replace_once(text, old, new, where='replace_once in ' + str(owner), owner=owner)
        except Exception as failure:
            if not port.survey: raise
            port.failures.append({'class': owner, 'method': 'anchor', 'error': str(failure)[:300]})
            return text
    patch_smali.method, patch_smali.replace_once = method, replace_once
    settings_test.patched = lambda path, old, new: port.replace_once(path.read_text(), old, new, where=str(path))
    # Regex patterns and replacements written with 0.8.1 names (escaped or not).
    class Re:
        def __getattr__(self, name): return getattr(re, name)
        @staticmethod
        def _p(pattern): return port.regex(pattern) if isinstance(pattern, str) else pattern
        def subn(self, pattern, repl, string, *a, **k): return re.subn(self._p(pattern), repl, string, *a, **k)
        def sub(self, pattern, repl, string, *a, **k): return re.sub(self._p(pattern), repl, string, *a, **k)
        def finditer(self, pattern, string, *a, **k): return re.finditer(self._p(pattern), string, *a, **k)
        def search(self, pattern, string, *a, **k): return re.search(self._p(pattern), string, *a, **k)
        def compile(self, pattern, *a, **k): return re.compile(self._p(pattern), *a, **k)
    for module in modules:
        if getattr(module, 're', None) is re: module.re = Re()
    return modules


def settings(port, decoded):
    """settings_test.main() for any version: the same patches, located through the map."""
    import settings_test as st
    decoded = Path(decoded)
    def cls(name): return port.files[port.t.cls(name)]
    def attempt(label, action):
        try: action()
        except Exception as failure:
            if not port.survey: raise
            port.failures.append({'class': label, 'method': '', 'error': str(failure)[:300]})
    texts = {}
    def read(name):
        if name not in texts: texts[name] = cls(name).read_text()
        return texts[name]
    def change(name, old, new, where): texts[name] = port.replace_once(read(name), old, new, where=where)
    # Settings page factories: hook their start and decorate every page they return.
    for name, line in (('E1/B0', '.method public a(Ljava/lang/String;)LE1/T6;'), ('E1/b4', '.method public final a(Ljava/lang/String;)LE1/T6;')):
        def page(name=name, line=line):
            text = read(name); start = port.signature(line, name)
            if text.count(start) != 1: raise ValueError('Settings page factory missing: ' + start)
            begin = text.index(start); body_start = text.index('\n', text.index('.locals', begin)) 
            end = text.index('.end method', begin)
            method_text = text[begin:end]
            locals_line = re.search(r'\n    \.locals \d+', method_text).group(0)
            method_text = method_text.replace(locals_line, locals_line + st.PAGE_HOOK, 1)
            decorate = lambda m: ('    invoke-static/range {%s .. %s}, Lwinterx/tweaks/TweakSettings;->decorate(LE1/T6;)LE1/T6;\n'
                '    move-result-object %s\n    invoke-static/range {%s .. %s}, Lwinterx/animaper/AnimaperSettings;->decorate(LE1/T6;)LE1/T6;\n'
                '    move-result-object %s\n    return-object %s' % ((m.group(1),) * 7))
            method_text, count = re.subn(r'^    return-object ([vp]\d+)$', decorate, method_text, flags=re.M)
            if count < 2: raise ValueError('Settings page return hooks were not found in ' + name)
            texts[name] = text[:begin] + method_text + text[end:]
        attempt(name + ' page', page)
    attempt('E1/Z3 root row', lambda: change('E1/Z3', st.ROOT_MARKER, st.ROOT_PATCH, 'Settings root row'))
    attempt('E1/Z3 iOS 6 root row', lambda: change('E1/Z3', st.IOS6_ROOT_MARKER, st.IOS6_ROOT_PATCH, 'iOS 6 Settings root row'))
    attempt('x1/i1 Settings taps', lambda: change('x1/i1', st.TAP_MARKER, st.TAP_PATCH, 'Settings tap routing'))
    attempt('x1/i1 delete guard', lambda: change('x1/i1', st.DELETE_MARKER, st.DELETE_PATCH, 'Ruby delete guard'))
    def unlock():
        text = read('x1/i1'); start = port.signature(st.UNLOCK_START, 'x1/i1')
        if text.count(start) != 1: raise ValueError('Unlock method missing: ' + start)
        begin = text.index(start); end = text.index('.end method', begin)
        texts['x1/i1'] = text[:begin] + port.replace_once(text[begin:end], st.UNLOCK_CALL, st.UNLOCK_PATCH, 'unlock') + text[end:]
    attempt('x1/i1 unlock', unlock)
    activity = 'com/guille/spring/LauncherActivity'
    attempt('LauncherActivity boot', lambda: change(activity, st.BOOT_MARKER, st.BOOT_PATCH, 'boot'))
    texts[activity] = read(activity) + st.HOME_WRAPPER
    quickjs = 'com/guille/spring/sapp/QuickJs'
    texts[quickjs] = read(quickjs) + st.TWEAK_QUICKJS
    for name, text in texts.items(): cls(name).write_text(text)
    ruby = decoded / 'smali/ruby'; ruby.mkdir(parents=True, exist_ok=True)
    (ruby / 'RubyHooks.smali').write_text(st.HOOKS)
    (ruby / 'Noop.smali').write_text(st.NOOP)
    (ruby / 'BootDismiss.smali').write_text(st.BOOT_DISMISS)
    import coloredbar
    attempt('ColoredBar', lambda: coloredbar.apply(decoded))
    pattern = re.compile(r'invoke-virtual(/range)? (\{[^}]+\}), Landroid/content/res/AssetManager;->open\(Ljava/lang/String;\)Ljava/io/InputStream;')
    count = 0
    for path in decoded.rglob('*.smali'):
        if path.parent == ruby: continue
        text, n = pattern.subn(lambda m: 'invoke-static' + (m.group(1) or '') + ' ' + m.group(2) + ', Lruby/RubyHooks;->openAsset(Landroid/content/res/AssetManager;Ljava/lang/String;)Ljava/io/InputStream;', path.read_text())
        if n: path.write_text(text); count += n
    port.failures.append({'class': 'asset loaders', 'method': '', 'error': 'info: %d AssetManager.open calls routed (0.8.1 has 43)' % count})


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('map'); parser.add_argument('decoded'); parser.add_argument('--report')
    parser.add_argument('--survey', action='store_true', help='record and skip anchors that fail, to list them all')
    parser.add_argument('--hand', help='module of hand-ported insertions for this version (e.g. port09)')
    parser.add_argument('--skip', help='patch modules not applied on this version, comma-separated (e.g. patch_dockin)')
    args = parser.parse_args()
    port = Port(json.load(open(args.map)), args.decoded)
    port.survey = args.survey
    port.snapshot()
    install(port)
    import patch_smali
    settings(port, args.decoded)
    if args.skip:
        for name in args.skip.split(','):
            module = __import__(name); module.apply = lambda *a, **k: None
            port.failures.append({'class': name, 'method': '', 'error': 'skipped on this version: ' + name})
    try: patch_smali.apply(port.located(Path(args.decoded)))
    except Exception as failure:
        if not port.survey: raise
        port.failures.append({'class': 'patch_smali', 'method': '', 'error': str(failure)[:300]})
    port.finish()
    if args.hand:
        import importlib; hand = importlib.import_module(args.hand)
        done = hand.apply(port)
        port.failures = [f for f in port.failures if not any(n in f['error'] or n in f['method'] for n in hand.HANDLED)]
        print('hand-ported:', ', '.join(done))
    if args.report: json.dump({'flexible': port.report, 'failures': port.failures, 'unmapped': sorted(port.t.missing)}, open(args.report, 'w'), indent=1)
    print('flexible anchors:', len(port.report), '| failures:', len(port.failures), '| unmapped names:', len(port.t.missing))


if __name__ == '__main__': main()
