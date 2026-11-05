"""Universal method hooks: give every Spring method a cheap hook check at build time.

Each instrumented method starts with:

    table = MethodHooks.table            # null until any tweak hooks something
    if (table != null && table[ID]) {     # this method is hooked
        result = MethodHooks.call(ID, this, boxed arguments)
        if (result != MethodHooks.PASS) return result (unboxed)
    }
    ...original code...

Hooks run in load order and can call the original (see winterx.extension.MethodHooks). Constructors, static
initialisers, abstract/native methods and Android/AndroidX/WinterX/Ruby classes are left alone. A method whose
registers can't be extended without breaking 4-bit register encodings is skipped and simply isn't hookable.
"""
from pathlib import Path
import re

EXCLUDED = ('android/', 'androidx/', 'winterx/', 'ruby/', 'j$/', 'kotlin/', 'kotlinx/')
METHOD = re.compile(r'^\.method (?P<flags>[^\n]*?)(?P<name>[^\s(]+)\((?P<params>[^)]*)\)(?P<ret>\S+)$')
TYPE = re.compile(r'\[*(?:[ZBSCIJFD]|L[^;]+;)')
SCRATCH = 3
BOX = {'Z': ('Ljava/lang/Boolean;', 'Z'), 'B': ('Ljava/lang/Byte;', 'B'), 'S': ('Ljava/lang/Short;', 'S'),
       'C': ('Ljava/lang/Character;', 'C'), 'I': ('Ljava/lang/Integer;', 'I'), 'J': ('Ljava/lang/Long;', 'J'),
       'F': ('Ljava/lang/Float;', 'F'), 'D': ('Ljava/lang/Double;', 'D')}
HOOKS = 'Lwinterx/extension/MethodHooks;'


def parameters(text):
    types = TYPE.findall(text)
    if ''.join(types) != text: raise ValueError('Unparsed descriptor: ' + text)
    return types


def prologue(index, static, params, ret):
    """Smali for the hook check; uses only v0..v2, which are always free at method entry."""
    lines = ['    sget-object v0, %s->table:[Z' % HOOKS, '    if-eqz v0, :wx_hook_skip',
             '    const v1, %#x' % index, '    aget-boolean v0, v0, v1', '    if-eqz v0, :wx_hook_skip',
             '    const v0, %#x' % len(params), '    new-array v1, v0, [Ljava/lang/Object;']
    register = 0 if static else 1
    for position, kind in enumerate(params):
        if kind in BOX:
            boxed, primitive = BOX[kind]
            last = register + (1 if kind in 'JD' else 0)
            lines += ['    invoke-static/range {p%d .. p%d}, %s->valueOf(%s)%s' % (register, last, boxed, primitive, boxed),
                      '    move-result-object v2']
        else:
            lines.append('    move-object/from16 v2, p%d' % register)
        lines += ['    const v0, %#x' % position, '    aput-object v2, v1, v0']
        register += 2 if kind in 'JD' else 1
    lines += ['    const v0, %#x' % index]
    lines.append('    const/4 v2, 0x0' if static else '    move-object/from16 v2, p0')
    lines += ['    invoke-static {v0, v2, v1}, %s->call(ILjava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;' % HOOKS,
              '    move-result-object v0', '    sget-object v1, %s->PASS:Ljava/lang/Object;' % HOOKS,
              '    if-eq v0, v1, :wx_hook_skip']
    if ret == 'V': lines.append('    return-void')
    elif ret[0] in 'L[': lines += ['    check-cast v0, %s' % ret, '    return-object v0']
    elif ret == 'Z': lines += ['    check-cast v0, Ljava/lang/Boolean;', '    invoke-virtual {v0}, Ljava/lang/Boolean;->booleanValue()Z', '    move-result v0', '    return v0']
    elif ret == 'C': lines += ['    check-cast v0, Ljava/lang/Character;', '    invoke-virtual {v0}, Ljava/lang/Character;->charValue()C', '    move-result v0', '    return v0']
    elif ret in 'BSI':
        lines += ['    check-cast v0, Ljava/lang/Number;', '    invoke-virtual {v0}, Ljava/lang/Number;->intValue()I', '    move-result v0']
        if ret == 'B': lines.append('    int-to-byte v0, v0')
        if ret == 'S': lines.append('    int-to-short v0, v0')
        lines.append('    return v0')
    elif ret == 'F': lines += ['    check-cast v0, Ljava/lang/Number;', '    invoke-virtual {v0}, Ljava/lang/Number;->floatValue()F', '    move-result v0', '    return v0']
    elif ret in 'JD':
        name = 'longValue' if ret == 'J' else 'doubleValue'
        lines += ['    check-cast v0, Ljava/lang/Number;', '    invoke-virtual {v0}, Ljava/lang/Number;->%s()%s' % (name, ret), '    move-result-wide v0', '    return-wide v0']
    else: raise ValueError('Unknown return type ' + ret)
    return lines + ['    :wx_hook_skip']


def instrument(decoded):
    """Instrument smali/ in place. Returns the sorted list of hookable signatures (index = hook ID)."""
    root = Path(decoded) / 'smali'
    methods = []  # (signature, path, start line)
    texts = {}
    for path in sorted(root.rglob('*.smali')):
        text = path.read_text()
        match = re.search(r'^\.class [^\n]*?(L[^;\s]+;)$', text, re.M)
        if not match: continue
        owner = match.group(1)
        if owner[1:].startswith(EXCLUDED): continue
        texts[path] = text.split('\n')
        lines = texts[path]
        for number, line in enumerate(lines):
            header = METHOD.match(line)
            if not header: continue
            flags, name = header['flags'].split(), header['name']
            if name in ('<init>', '<clinit>') or 'abstract' in flags or 'native' in flags: continue
            methods.append((owner + '->' + name + '(' + header['params'] + ')' + header['ret'], path, number, 'static' in flags,
                            parameters(header['params']), header['ret']))
    methods.sort(key=lambda item: item[0])
    hookable, edits = [], {}
    for signature, path, number, static, params, ret in methods:
        lines = texts[path]
        locals_at = number + 1
        while not lines[locals_at].strip().startswith(('.locals', '.registers')):
            if lines[locals_at].strip() == '.end method': break
            locals_at += 1
        directive = lines[locals_at].strip()
        if not directive.startswith('.locals'): continue
        count = int(directive.split()[1], 0)
        width = (0 if static else 1) + sum(2 if kind in 'JD' else 1 for kind in params)
        if count < SCRATCH:
            # Growing .locals renumbers parameters; only safe while every register still fits 4-bit encodings.
            if SCRATCH + width > 16: continue
            count = SCRATCH
        insert, depth = locals_at + 1, None
        while insert < len(lines):
            stripped = lines[insert].strip()
            if depth:
                if stripped == depth: depth = None
                insert += 1; continue
            if stripped.startswith('.param') and not stripped.endswith('.end param'):
                # A .param with annotations runs to .end param; a bare one is a single line.
                following = lines[insert + 1].strip() if insert + 1 < len(lines) else ''
                if following.startswith('.annotation'): depth = '.end param'
                insert += 1; continue
            if stripped.startswith('.annotation'): depth = '.end annotation'; insert += 1; continue
            if not stripped or stripped == '.prologue' or stripped == '.end param': insert += 1; continue
            break
        index = len(hookable)
        hookable.append(signature)
        edits.setdefault(path, []).append((locals_at, '    .locals %d' % count, insert, prologue(index, static, params, ret)))
    for path, changes in edits.items():
        lines = texts[path]
        for locals_at, directive, insert, code in sorted(changes, key=lambda change: change[2], reverse=True):
            lines[insert:insert] = code
            lines[locals_at] = directive
        path.write_text('\n'.join(lines))
    return hookable


def table_source(signatures):
    """Java source holding every hookable signature, chunked under the class-file constant limit."""
    chunks, current, size = [], [], 0
    for signature in signatures:
        if size + len(signature) + 1 > 60000: chunks.append(current); current, size = [], 0
        current.append(signature); size += len(signature) + 1
    if current: chunks.append(current)
    quote = lambda text: '"' + text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'
    lines = ['package winterx.extension;', '', '/** Generated: every hookable Spring method, sorted; the index is its hook ID. */',
             'final class MethodTable {', '    private MethodTable() {}', '    static final int COUNT = %d;' % len(signatures),
             '    static String[] signatures() {', '        String[] result = new String[COUNT]; int at = 0;']
    for number in range(len(chunks)):
        lines.append('        for (String value : chunk%d().split("\\n", -1)) result[at++] = value;' % number)
    lines += ['        return result;', '    }']
    for number, chunk in enumerate(chunks):
        lines += ['    private static String chunk%d() { return %s; }' % (number, quote('\n'.join(chunk)))]
    lines.append('}')
    return '\n'.join(lines) + '\n'
