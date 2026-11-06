"""Which registers are dead at a point in a smali method (always written before being read on every path from it)."""
import re

WRITES = re.compile(r'^\s+(move(?:-object|-wide)?(?:/from16|/16)?|move-result(?:-object|-wide)?|move-exception|const[a-z0-9/-]*|'
                    r'new-instance|new-array|[is]get[a-z-]*|aget[a-z-]*|instance-of|array-length|check-cast|'
                    r'(?:neg|not|int-to|long-to|float-to|double-to)[a-z-]*|(?:add|sub|mul|div|rem|and|or|xor|shl|shr|ushr|rsub)-[a-z]+(?:/lit\d+|/2addr)?|cmp[a-z-]*|filled-new-array)\s')


def parse(body):
    lines = [l for l in body.split('\n') if l.strip() and not l.strip().startswith(('.line', '.local', '.end local', '.restart', '.param', '.end param', '.prologue'))]
    labels = {l.strip(): i for i, l in enumerate(lines) if l.strip().startswith(':')}
    return lines, labels


def regs(text):
    m = re.search(r'\{([^}]*)\}', text)
    if m:
        inner = m.group(1).strip()
        r = re.match(r'([vp])(\d+) \.\. ([vp])(\d+)', inner)
        if r: return [r.group(1) + str(n) for n in range(int(r.group(2)), int(r.group(4)) + 1)]
        return [x.strip() for x in inner.split(',') if x.strip()]
    return re.findall(r'\b[vp]\d+\b', text)


def dead(body, index, candidates):
    """Registers in candidates never read before written on any path starting at line index."""
    lines, labels = parse(body)
    result = set()
    for reg in candidates:
        seen, stack, ok = set(), [index], True
        while stack and ok:
            i = stack.pop()
            while i < len(lines):
                if i in seen: break
                seen.add(i)
                line = lines[i].strip()
                op = line.split()[0]
                if op.startswith(':') or op.startswith('.'):
                    if op in ('.catch', '.catchall'):
                        target = line.split()[-1]
                        if target in labels: stack.append(labels[target])
                    i += 1; continue
                if op.startswith('return') or op.startswith('throw'):
                    if reg in regs(line): ok = False
                    break
                used = regs(line)
                wide = '-wide' in op
                # /2addr instructions read their first register before writing it.
                if (WRITES.match(lines[i]) and used and used[0] == reg and reg not in used[1:]
                        and not op.startswith(('iput', 'sput', 'aput')) and not op.endswith('/2addr')):
                    break                          # written first on this path
                if reg in used or (wide and any(r[0] == reg[0] and int(r[1:]) + 1 == int(reg[1:]) for r in used[:1])):
                    ok = False; break              # read (or part of a wide pair) before any write
                targets = [t for t in re.findall(r':[a-z_0-9]+', line)]
                if op.startswith(('if-', 'goto', 'packed-switch', 'sparse-switch')):
                    for t in targets:
                        if t in labels: stack.append(labels[t])
                    if op.startswith('goto'): break
                i += 1
        if ok: result.add(reg)
    return result
