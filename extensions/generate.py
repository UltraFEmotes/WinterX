"""Generate the small typed engine bindings for the public native hook ABI."""
import hashlib
import json
from pathlib import Path
import re

from contracts import DEFAULTS, EXTRA, POINTS, POLICIES, SCOPES

REFERENCE = re.compile(r'(Lwinterx/[A-Za-z0-9_/$]+;)->([A-Za-z0-9_$]+)(\([^\n ]*\)[^\n ]+)')
PRIMITIVES = {'V': 'void', 'Z': 'boolean', 'I': 'int', 'J': 'long', 'F': 'float', 'D': 'double', 'B': 'byte', 'S': 'short', 'C': 'char'}
BOXES = {'boolean': 'Boolean', 'int': 'Integer', 'long': 'Long', 'float': 'Float', 'double': 'Double', 'byte': 'Byte', 'short': 'Short', 'char': 'Character'}


def types(descriptor):
    params = re.findall(r'\[*(?:L[^;]+;|[ZBCSIJFD])', descriptor[1:descriptor.index(')')])
    return params, descriptor[descriptor.index(')') + 1:]


def java_type(value):
    if value.startswith('['): return java_type(value[1:]) + '[]'
    if value.startswith('L'): return value[1:-1].replace('/', '.').replace('$', '.')
    return PRIMITIVES[value]


def name(point): return point.replace('.', '_').replace('-', '_')


def generate(decoded, output, overrides=None):
    """overrides (another Spring version): {'extra': {point: [descriptor, fallback]}, 'defaults': {point: expr}, 'tiles': 'A.o'}."""
    overrides = overrides or {}
    extra = {k: tuple(v) for k, v in overrides.get('extra', {}).items()} or EXTRA
    defaults = dict(DEFAULTS, **overrides.get('defaults', {}))
    tiles = overrides.get('tiles', 'A.o')
    paths = sorted((Path(decoded) / 'smali').rglob('*.smali'))
    texts = {path: path.read_text() for path in paths}
    bindings, contracts = {}, {}
    for text in texts.values():
        for owner, method, descriptor in REFERENCE.findall(text):
            simple = owner.rsplit('/', 1)[-1][:-1]
            symbol = owner + '->' + method + descriptor
            if simple == 'AnimaperSettings' and method == 'decorate':
                bindings[symbol] = 'Lwinterx/tweaks/TweakSettings;->decorate' + descriptor; continue
            if simple == 'RenderPolicy' and method == 'tiles':
                bindings[symbol] = 'Lwinterx/extension/NativeHooks;->cache_tiles' + descriptor; continue
            point = POINTS.get((simple, method))
            if point is None: continue
            bindings[symbol] = 'Lwinterx/extension/NativeHooks;->' + name(point) + descriptor
            contracts[(point, descriptor)] = {'point': point, 'descriptor': descriptor, 'legacy': symbol}
    for point, (descriptor, fallback) in extra.items():
        contracts[(point, descriptor)] = {'point': point, 'descriptor': descriptor, 'fallback': fallback}
    source = ['package winterx.extension;', '', '/** Generated typed bindings. Actual tweak behavior is installed separately through Ruby. */', 'public final class NativeHooks {', '    private NativeHooks() {}']
    for (_, _), contract in sorted(contracts.items()):
        point, descriptor = contract['point'], contract['descriptor']
        parameters, result = types(descriptor)
        arguments = ', '.join('p' + str(index) for index in range(len(parameters)))
        signature = ', '.join(java_type(value) + ' p' + str(index) for index, value in enumerate(parameters))
        return_type = java_type(result)
        fallback = contract.get('fallback', defaults.get(point, '' if result == 'V' else 'false' if result == 'Z' else '0' if result in PRIMITIVES else 'null'))
        policy = POLICIES.get(point, 'all' if result == 'V' else 'first')
        contract.update(fallback=fallback, policy=policy)
        source.append('    public static ' + return_type + ' ' + name(point) + '(' + signature + ') {')
        array = 'new Object[]{' + arguments + '}'
        scope = SCOPES.get(point)
        if scope == 'frame': source.append('        return NativeScopes.frame("' + point + '", ' + array + ');')
        elif scope == 'frame-end': source.append('        NativeScopes.frameEnd("' + point + '", p0);')
        elif scope == 'icon': source.append('        return NativeScopes.icon("' + point + '", ' + array + ');')
        elif scope == 'icon-end': source.append('        NativeScopes.iconEnd("' + point + '", p0, p1);')
        elif scope == 'transaction-begin': source.append('        NativeRuntime.begin("' + point + '", ' + array + ');')
        elif scope == 'transaction-end': source.append('        NativeRuntime.finish("' + point + '", ' + array + ');')
        else:
            expected = 'null' if result == 'V' else BOXES.get(return_type, return_type) + '.class'
            dispatch = 'NativeRuntime.dispatch("' + point + '", ' + array + ', ' + (fallback or 'null') + ', "' + policy + '", false, ' + expected + ')'
            if result == 'V': source.append('        ' + dispatch + ';')
            else: source.append('        return (' + BOXES.get(return_type, return_type) + ') ' + dispatch + ';')
        source.append('    }')
    source += ['    public static ' + tiles + ' cache_tiles(' + tiles + ' original) { return cache_tiles_allowed() ? original : null; }', '}']
    target = Path(output) / 'winterx/extension/NativeHooks.java'; target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('\n'.join(source) + '\n')
    for path, text in texts.items():
        for original, replacement in bindings.items(): text = text.replace(original, replacement)
        if text != texts[path]: path.write_text(text)
    # Bootstrap only the generic package loader. It never installs/downloads a package.
    hook = Path(decoded) / 'smali/ruby/RubyHooks.smali'
    text = hook.read_text(); anchor = '    invoke-static {v0}, Lwinterx/runtime/Capabilities;->publish(Ljava/io/File;)V'
    if text.count(anchor) != 1: raise ValueError('Missing generic boot capability hook')
    hook.write_text(text.replace(anchor, '    invoke-static {v0}, Lwinterx/runtime/PackageService;->boot(Ljava/io/File;)V\n'
                                 '    invoke-static {v0}, Lwinterx/extension/NativeRuntime;->initialize(Ljava/io/File;)V\n' + anchor))
    contract_file = Path(output) / 'native-api.json'
    contract_file.write_text(json.dumps({'api': 'winterx.native/1', 'points': list(contracts.values())}, indent=2) + '\n')
    return list(contracts.values())
