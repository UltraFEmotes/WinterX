#!/usr/bin/env python3
"""Map Spring's obfuscated names from one version to another (classes, methods and fields).

Spring is obfuscated, so every release renames its classes and members. WinterX's core and its tweaks are written
against one version's names; this maps them onto another's, so the core can be re-anchored and compiled tweaks can be
translated. It works on two apktool-decoded trees (smali), the way deobfuscation mappers do:

1. Names that aren't obfuscated (Android, Kotlin, com/guille/spring/...) map to themselves.
2. Classes are paired by strings only they contain, then by their exact shape.
3. Every pair spreads: a matched method or field whose types mention obfuscated classes pairs those classes too.
4. Inside each class pair, methods are paired by signature and body similarity, and fields by type and order.
Steps 2 to 4 repeat until nothing new is found.

    python3 tools/spring_map.py OLD_DECODED NEW_DECODED map.json [--report used-names.txt]
"""
import argparse
import collections
import json
import os
import re
import sys

OBFUSCATED = re.compile(r'^(?:[A-Za-z][0-9]?|[a-z][0-9]?[a-z]?)/[A-Za-z][0-9A-Za-z]{0,2}(?:\$.*)?$')
CLASS_REF = re.compile(r'L([^;()\[\s]+);')
STRING = re.compile(r'const-string(?:/jumbo)? [vp]\d+, "((?:[^"\\]|\\.)*)"')
INVOKE = re.compile(r'invoke-[a-z/-]+ \{[^}]*\}, L([^;]+);->([^(]+)(\([^)]*\)\S+)')
FIELD_REF = re.compile(r'[is](?:get|put)[a-z-]* [vp]\d+(?:, [vp]\d+)?, L([^;]+);->([^:]+):(\S+)')
OPCODE = re.compile(r'^\s+([a-z][a-z0-9/-]+)', re.M)
REF = re.compile(r'L([^;\s]+);->([^(:\s]+)(\([^)]*\)\S+|:\S+)')


def obfuscated(name): return bool(OBFUSCATED.match(name))


class Member:
    __slots__ = ('name', 'descriptor', 'static', 'strings', 'calls', 'fields', 'opcodes', 'index', 'refs')


class Klass:
    __slots__ = ('name', 'super', 'interfaces', 'flags', 'fields', 'methods', 'strings')


def parse(root):
    classes = {}
    for directory, _, files in os.walk(root):
        if os.sep + 'smali' not in directory: continue
        for file in files:
            if not file.endswith('.smali'): continue
            text = open(os.path.join(directory, file), errors='ignore').read()
            head = re.search(r'^\.class ([^\n]*?)L([^;]+);', text, re.M)
            if not head: continue
            k = Klass(); k.name = head.group(2); k.flags = head.group(1).strip()
            sup = re.search(r'^\.super L([^;]+);', text, re.M); k.super = sup.group(1) if sup else ''
            k.interfaces = sorted(re.findall(r'^\.implements L([^;]+);', text, re.M))
            k.fields = []
            for i, m in enumerate(re.finditer(r'^\.field ([^\n]*?)(\S+):(\S+?)(?: = [^\n]*)?$', text, re.M)):
                f = Member(); f.name = m.group(2); f.descriptor = m.group(3); f.static = 'static' in m.group(1); f.index = i
                k.fields.append(f)
            k.methods = []
            for i, m in enumerate(re.finditer(r'^\.method ([^\n]*?)(\S+?)(\([^\n]*)\n(.*?)^\.end method', text, re.M | re.S)):
                f = Member(); f.name = m.group(2); f.descriptor = m.group(3); f.static = 'static' in m.group(1); f.index = i
                body = m.group(4)
                f.strings = frozenset(STRING.findall(body))
                f.calls = collections.Counter((o, n, d) for o, n, d in INVOKE.findall(body) if not obfuscated(o))
                f.fields = collections.Counter((o, n, d) for o, n, d in FIELD_REF.findall(body) if not obfuscated(o))
                f.opcodes = collections.Counter(OPCODE.findall(body))
                # In order: every Spring method called and field touched, for matching by usage.
                f.refs = [(kind, owner, name, desc) for kind, owner, name, desc in
                          ((('m',) + c) if c[2].startswith('(') else (('f',) + c) for c in REF.findall(body))
                          if obfuscated(owner) or owner.startswith('com/guille/spring/')]
                k.methods.append(f)
            k.strings = frozenset(s for m in k.methods for s in m.strings if len(s) >= 3)
            classes[k.name] = k
    return classes


def lcs(a, b):
    """Index pairs of a longest common subsequence (sizes are small: one method body each)."""
    n, m = len(a), len(b)
    if n * m > 400000: return []
    table = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            table[i][j] = table[i + 1][j + 1] + 1 if a[i] == b[j] else max(table[i + 1][j], table[i][j + 1])
    pairs, i, j = [], 0, 0
    while i < n and j < m:
        if a[i] == b[j]: pairs.append((i, j)); i += 1; j += 1
        elif table[i + 1][j] >= table[i][j + 1]: i += 1
        else: j += 1
    return pairs


def similarity(a, b):
    """0..1: how alike two method bodies are (strings, framework calls/fields, instruction mix)."""
    def jaccard(x, y):
        if not x and not y: return 1.0
        inter = sum((x & y).values()) if isinstance(x, collections.Counter) else len(x & y)
        union = sum((x | y).values()) if isinstance(x, collections.Counter) else len(x | y)
        return inter / union if union else 1.0
    return (2 * jaccard(a.strings, b.strings) + 2 * jaccard(a.calls, b.calls) + jaccard(a.fields, b.fields)
            + 2 * jaccard(a.opcodes, b.opcodes)) / 7


class Mapper:
    def __init__(self, old, new):
        self.old, self.new = old, new
        self.classes = {}                       # old -> new
        self.taken = set()
        self.methods = {}                       # "Lold;->name(desc)" -> "Lnew;->name(desc)"
        self.fields = {}                        # "Lold;->name:type" -> "Lnew;->name:type"
        for name in old:
            if not obfuscated(name) and name in new: self.pair(name, name, 'same name')
        self.how = collections.Counter()

    def pair(self, a, b, why=''):
        if a in self.classes or b in self.taken: return self.classes.get(a) == b
        if a not in self.old or b not in self.new: return False
        self.classes[a] = b; self.taken.add(b)
        if why: getattr(self, 'how', collections.Counter())[why] += 1
        # Inner classes follow their outer class's name.
        return True

    def normalise(self, descriptor, mapping=True):
        """A descriptor with mapped classes renamed and unmapped obfuscated ones blanked."""
        def swap(m):
            name = m.group(1)
            if not obfuscated(name): return 'L' + name + ';'
            return 'L' + self.classes[name] + ';' if mapping and name in self.classes else 'L?;'
        return CLASS_REF.sub(swap, descriptor)

    def blank(self, descriptor):
        return CLASS_REF.sub(lambda m: 'L' + m.group(1) + ';' if not obfuscated(m.group(1)) else 'L?;', descriptor)

    def unify(self, old_descriptor, new_descriptor):
        """Pair the obfuscated classes in two descriptors that are known to correspond."""
        a, b = CLASS_REF.findall(old_descriptor), CLASS_REF.findall(new_descriptor)
        if len(a) != len(b): return 0
        found = 0
        for x, y in zip(a, b):
            if obfuscated(x) and obfuscated(y) and x not in self.classes and y not in self.taken:
                if self.pair(x, y, 'types'): found += 1
        return found

    # ----- class seeding -----

    def by_strings(self):
        index = collections.defaultdict(set)
        for name, k in self.new.items():
            if name in self.taken: continue
            for s in k.strings: index[s].add(name)
        found = 0
        for name, k in self.old.items():
            if name in self.classes or not obfuscated(name) or not k.strings: continue
            votes = collections.Counter()
            for s in k.strings:
                if len(index[s]) <= 2:
                    for other in index[s]: votes[other] += 1
            if not votes: continue
            top = votes.most_common(2)
            if (len(top) == 1 or top[0][1] > top[1][1]) and top[0][1] >= max(1, 0.3 * len(k.strings)):
                if self.pair(name, top[0][0], 'strings'): found += 1
        return found

    def shape(self, k, mapping=True):
        return (self.normalise(k.super, mapping) if k.super else '', tuple(self.normalise('L' + i + ';', mapping) for i in k.interfaces),
                tuple(sorted(self.normalise(f.descriptor, mapping) + ('s' if f.static else '') for f in k.fields)),
                tuple(sorted(self.normalise(m.descriptor, mapping) + ('s' if m.static else '') for m in k.methods)))

    def by_shape(self):
        reverse = {v: k for k, v in self.classes.items()}
        def new_shape(k):
            def swap(m):
                name = m.group(1)
                if not obfuscated(name): return 'L' + name + ';'
                return 'L' + name + ';' if name in reverse else 'L?;'
            norm = lambda d: CLASS_REF.sub(swap, d)
            return (norm('L' + k.super + ';')[1:-1] if k.super else '', tuple(norm('L' + i + ';') for i in k.interfaces),
                    tuple(sorted(norm(f.descriptor) + ('s' if f.static else '') for f in k.fields)),
                    tuple(sorted(norm(m.descriptor) + ('s' if m.static else '') for m in k.methods)))
        groups = collections.defaultdict(list)
        for name, k in self.new.items():
            if name in self.taken or not obfuscated(name): continue
            groups[new_shape(k)].append(name)
        old_groups = collections.defaultdict(list)
        for name, k in self.old.items():
            if name in self.classes or not obfuscated(name): continue
            s = self.shape(k); s = (s[0][1:-1] if s[0].startswith('L') else s[0],) + s[1:]
            old_groups[s].append(name)
        found = 0
        for s, names in old_groups.items():
            if len(names) == 1 and len(groups.get(s, ())) == 1 and (s[2] or s[3]):
                if self.pair(names[0], groups[s][0], 'shape'): found += 1
        return found

    # ----- members -----

    def members(self):
        """Pair methods and fields inside every class pair; spread to the classes their types mention."""
        found = 0
        for a, b in list(self.classes.items()):
            ka, kb = self.old[a], self.new[b]
            if obfuscated(a) or obfuscated(b) or a.startswith('com/guille/spring/'):
                found += self.pair_methods(ka, kb)
                found += self.pair_fields(ka, kb)
            if ka.super and kb.super and obfuscated(ka.super): found += self.unify('L' + ka.super + ';', 'L' + kb.super + ';')
            for x, y in zip(ka.interfaces, kb.interfaces): found += self.unify('L' + x + ';', 'L' + y + ';')
        return found

    def pair_methods(self, ka, kb):
        found = 0
        done_new = {v.split('->', 1)[1] for k, v in self.methods.items() if k.startswith('L' + ka.name + ';->')}
        for m in ka.methods:
            key = 'L' + ka.name + ';->' + m.name + m.descriptor
            if key in self.methods: continue
            want = self.normalise(m.descriptor)
            options = [n for n in kb.methods if n.static == m.static and (n.name + n.descriptor) not in done_new
                       and self.compatible(want, n.descriptor) and (n.name == m.name if not self._obf_member(m.name) else True)]
            if not options: continue
            scored = sorted(((similarity(m, n), n) for n in options), key=lambda x: -x[0])
            best, score = scored[0][1], scored[0][0]
            second = scored[1][0] if len(scored) > 1 else -1
            if len(scored) == 1 and score >= 0.35 or score >= 0.6 and score - second >= 0.08:
                self.methods[key] = 'L' + kb.name + ';->' + best.name + best.descriptor
                done_new.add(best.name + best.descriptor)
                found += 1 + self.unify(m.descriptor, best.descriptor)
        return found

    @staticmethod
    def _obf_member(name): return len(name) <= 3 and name[0].isalpha() or name.startswith('access$')

    def compatible(self, want, descriptor):
        """Whether a new descriptor fits an old one whose known classes are already renamed."""
        a, b = want, self.blank(descriptor)
        if self.blank(a) != b: return False
        for x, y in zip(CLASS_REF.findall(want), CLASS_REF.findall(descriptor)):
            if x == '?' or not obfuscated(y): continue
            if x != y and (x in self.new and obfuscated(x)): return False
        return True

    def pair_fields(self, ka, kb):
        found = 0
        groups_a, groups_b = collections.defaultdict(list), collections.defaultdict(list)
        for f in ka.fields: groups_a[(self.blank(f.descriptor), f.static)].append(f)
        for f in kb.fields: groups_b[(self.blank(f.descriptor), f.static)].append(f)
        for key, olds in groups_a.items():
            news = groups_b.get(key, [])
            if len(olds) != len(news): continue
            for f, g in zip(sorted(olds, key=lambda x: x.index), sorted(news, key=lambda x: x.index)):
                name = 'L' + ka.name + ';->' + f.name + ':' + f.descriptor
                if name in self.fields: continue
                self.fields[name] = 'L' + kb.name + ';->' + g.name + ':' + g.descriptor
                found += 1 + self.unify(f.descriptor, g.descriptor)
        return found

    def usage(self):
        """Line up what each matched method pair calls and touches, in order; same slot and type means same member."""
        found = 0
        for old_key, new_key in list(self.methods.items()):
            a, b = self.method(self.old, old_key), self.method(self.new, new_key)
            if a is None or b is None or not a.refs or not b.refs: continue
            ka = [self.ref_key(r) for r in a.refs]; kb = [self.ref_key(r, new=True) for r in b.refs]
            for i, j in lcs(ka, kb):
                found += self.pair_ref(a.refs[i], b.refs[j])
        return found

    @staticmethod
    def method(classes, key):
        owner, rest = key[1:].split(';->', 1)
        k = classes.get(owner)
        return next((m for m in k.methods if m.name + m.descriptor == rest), None) if k else None

    def ref_key(self, ref, new=False):
        kind, owner, name, desc = ref
        desc = desc[1:] if desc.startswith(':') else desc
        if new:
            reverse = self.reverse()
            o = owner if not obfuscated(owner) else ('?' if owner not in reverse else owner)
            return (kind, o, self.blank(desc))
        o = owner if not obfuscated(owner) else self.classes.get(owner, '?')
        return (kind, o, self.blank(desc))

    def reverse(self):
        if getattr(self, '_reverse_size', -1) != len(self.classes):
            self._reverse = {v: k for k, v in self.classes.items()}; self._reverse_size = len(self.classes)
        return self._reverse

    def pair_ref(self, ra, rb):
        kind, oa, na, da = ra; _, ob, nb, db = rb
        found = 0
        if obfuscated(oa) and obfuscated(ob) and oa not in self.classes and ob not in self.taken:
            if self.pair(oa, ob, 'usage'): found += 1
        if self.classes.get(oa) != ob: return found
        if kind == 'f':
            key, value = 'L%s;->%s%s' % (oa, na, da), 'L%s;->%s%s' % (ob, nb, db)
            if key not in self.fields:
                self.fields[key] = value; found += 1 + self.unify(da[1:], db[1:])
        else:
            key, value = 'L%s;->%s%s' % (oa, na, da), 'L%s;->%s%s' % (ob, nb, db)
            if key not in self.methods and (na == nb or self._obf_member(na)):
                self.methods[key] = value; found += 1 + self.unify(da, db)
        return found

    def inner(self):
        """Inner/lambda classes: Outer$1 follows Outer."""
        found = 0
        for a, b in list(self.classes.items()):
            for suffix in [n[len(a):] for n in self.old if n.startswith(a + '$')]:
                if a + suffix not in self.classes and b + suffix in self.new and b + suffix not in self.taken:
                    if self.pair(a + suffix, b + suffix, 'inner'): found += 1
        return found

    # ----- evidence and repair -----

    def votes(self):
        """For each old obfuscated class: which new class every mapped member signature says it is."""
        tally = collections.defaultdict(collections.Counter)
        for table in (self.methods, self.fields):
            for k, v in table.items():
                ok, ov = k.split('->', 1), v.split('->', 1)
                pairs = [(ok[0][1:-1], ov[0][1:-1])] + list(zip(CLASS_REF.findall(ok[1]), CLASS_REF.findall(ov[1])))
                for x, y in pairs:
                    if obfuscated(x) and obfuscated(y): tally[x][y] += 1
        return tally

    def unpair(self, a):
        b = self.classes.pop(a, None)
        if b is None: return
        self.taken.discard(b)
        prefix = 'L' + a + ';->'
        for table in (self.methods, self.fields):
            for k in [k for k in table if k.startswith(prefix)]: del table[k]

    def repair(self):
        """Move class pairings the evidence outvotes, then drop member pairs that disagree with the classes."""
        moved = 0
        tally = self.votes()
        owner = {v: k for k, v in self.classes.items()}
        for a, counts in sorted(tally.items(), key=lambda x: -sum(x[1].values())):
            (best, n), current = counts.most_common(1)[0], self.classes.get(a)
            if best == current or n < 2 or n <= counts.get(current, 0) * 2: continue
            rival = owner.get(best)
            if rival is not None and tally.get(rival, {}).get(best, 0) >= n: continue   # the rival has better evidence
            if rival is not None: self.unpair(rival)
            self.unpair(a)
            if self.pair(a, best, 'repair'): moved += 1; owner = {v: k for k, v in self.classes.items()}
        for table in (self.methods, self.fields):
            for k, v in list(table.items()):
                ok, ov = k.split('->', 1), v.split('->', 1)
                pairs = [(ok[0][1:-1], ov[0][1:-1])] + list(zip(CLASS_REF.findall(ok[1]), CLASS_REF.findall(ov[1])))
                if any(obfuscated(x) and self.classes.get(x, y) != y for x, y in pairs): del table[k]
        return moved

    def run(self):
        for _ in range(6):
            for _ in range(12):
                found = self.by_strings() + self.inner() + self.members() + self.usage() + self.by_shape()
                if not found: break
            if not self.repair(): break
        return self

    def contradictions(self):
        tally = self.votes()
        return {a: c for a, c in tally.items() if self.classes.get(a) and c.most_common(1)[0][0] != self.classes[a]}



class Translator:
    """Rewrites smali (or text holding smali names) from one Spring version's names to another's, in one pass.

    Members are renamed through the map; a member of a renamed class that isn't in the map keeps its name only when
    that name isn't obfuscated (constructors, Android overrides, readable names), otherwise it's reported as missing.
    """
    TOKEN = re.compile(r'L([^;\s()\["]+);(?:->([^(:\s"]+)(\([^)\s"]*\)[^\s,}"]+|:[^\s,}"]+))?')

    def __init__(self, mapping):
        self.classes = mapping['classes']
        self.members = {}
        for table in ('methods', 'fields'):
            for k, v in mapping[table].items(): self.members[k] = v
        self.missing = collections.Counter()

    def cls(self, name): return self.classes.get(name, name)

    def desc(self, descriptor): return CLASS_REF.sub(lambda m: 'L' + self.cls(m.group(1)) + ';', descriptor)

    def member(self, owner, name, rest):
        key = 'L%s;->%s%s' % (owner, name, rest)
        if key in self.members: return self.members[key]
        if obfuscated(owner) and Mapper._obf_member(name) and name not in ('<init>', '<clinit>'):
            self.missing[key] += 1
        return 'L%s;->%s%s' % (self.cls(owner), name, self.desc(rest))

    def text(self, source):
        def swap(m):
            owner, name, rest = m.group(1), m.group(2), m.group(3)
            if name is None: return 'L' + self.cls(owner) + ';'
            return self.member(owner, name, rest)
        return self.TOKEN.sub(swap, source)

    def smali(self, source):
        """A whole smali class: its references, and its own .method/.field names when the class itself is renamed."""
        head = re.search(r'^\.class [^\n]*?L([^;]+);', source, re.M)
        owner = head.group(1) if head else None
        def declare(m):
            kind, mods, name, rest = m.group(1), m.group(2), m.group(3), m.group(4)
            if owner is None: return m.group(0)
            value = ''
            if kind == 'field' and ' = ' in rest: rest, value = rest.split(' = ', 1); value = ' = ' + self.text(value)
            declared = self.member(owner, name, rest).split(';->', 1)[1]     # rest keeps its ':' for fields
            return '.%s %s%s%s' % (kind, mods, declared, value)
        body = re.sub(r'^\.(method|field) ((?:[a-z-]+ )*)([^(:\s]+)(\([^\n]*|:[^\n]*)$', declare, source, flags=re.M)
        lines = body.split('\n')
        return '\n'.join(l if l.startswith(('.method ', '.field ')) else self.text(l) for l in lines)



def apply_overrides(result, overrides):
    """Hand-checked pins (from tools/spring-maps/*-overrides.json) win over automatic matches."""
    classes, methods = result['classes'], result['methods']
    for a, b in overrides.get('classes', {}).items():
        for other in [k for k, v in classes.items() if v == b and k != a]: del classes[other]
        classes[a] = b
    pinned_targets = set(overrides.get('methods', {}).values()) | set(overrides.get('fields', {}).values())
    for table in ('methods', 'fields'):
        for k in [k for k, v in result[table].items() if v in pinned_targets]: del result[table][k]
        result[table].update(overrides.get(table, {}))
    for table in ('methods', 'fields'):
        for k, v in list(result[table].items()):
            if k in overrides.get(table, {}): continue
            ok, ov = k.split('->', 1), v.split('->', 1)
            pairs = [(ok[0][1:-1], ov[0][1:-1])] + list(zip(CLASS_REF.findall(ok[1]), CLASS_REF.findall(ov[1])))
            if any(obfuscated(x) and classes.get(x, y) != y for x, y in pairs): del result[table][k]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('old'); parser.add_argument('new'); parser.add_argument('output')
    parser.add_argument('--report', help='a file of names (Lclass; or Lclass;->member) to check coverage for')
    parser.add_argument('--overrides', help='hand-checked pins to apply on top (tools/spring-maps/...-overrides.json)')
    args = parser.parse_args()
    old, new = parse(args.old), parse(args.new)
    mapper = Mapper(old, new); mapper.how = collections.Counter(); mapper.run()
    obf_old = [n for n in old if obfuscated(n)]
    result = {'format': 'winterx.spring-map/1',
              'classes': {k: v for k, v in sorted(mapper.classes.items()) if k != v or obfuscated(k)},
              'methods': dict(sorted(mapper.methods.items())), 'fields': dict(sorted(mapper.fields.items()))}
    if args.overrides: apply_overrides(result, json.load(open(args.overrides)))
    json.dump(result, open(args.output, 'w'), indent=1)
    print('obfuscated classes: %d of %d mapped' % (sum(1 for n in obf_old if n in mapper.classes), len(obf_old)))
    print('methods mapped: %d, fields mapped: %d' % (len(mapper.methods), len(mapper.fields)))
    print('class pairs still contradicted by member evidence: %d' % len(mapper.contradictions()))
    if args.report:
        missing = []
        names = [l.strip() for l in open(args.report) if l.strip()]
        for name in names:
            if '->' in name:
                ok = name in mapper.methods or name in mapper.fields
            else:
                ok = name.strip('L;') in mapper.classes
            if not ok: missing.append(name)
        print('report: %d of %d used names mapped' % (len(names) - len(missing), len(names)))
        for name in missing: print('  missing', name)


if __name__ == '__main__': main()
