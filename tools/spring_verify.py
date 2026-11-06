#!/usr/bin/env python3
"""Check a patched, decoded Spring: every Spring class, method and field that WinterX's inserted code references
must exist there (searching superclasses). Android/Java/Kotlin library references are not Spring's and are skipped.

    python3 tools/spring_verify.py DECODED
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spring_translate

LIBRARY = ('Lwinterx/', 'Lruby/', 'Ljava', 'Landroid', 'Lkotlin', 'Lorg/json/', 'Lorg/xmlpull/', 'Ldalvik/')


def problems(decoded):
    target = spring_translate.declared(decoded)
    found = {}
    for directory, _, files in os.walk(decoded):
        if os.sep + 'smali' not in directory: continue
        for file in files:
            path = os.path.join(directory, file); text = open(path, errors='ignore').read()
            if 'winterx' not in text and 'Lruby/' not in text: continue
            for owner, name, rest in re.findall(r'(L[^;\s()\["]+;)->([^(:\s"]+)(\([^)\s"]*\)[^\s,}"]+|:[^\s,}"]+)', text):
                if owner.startswith(LIBRARY): continue
                member, current, seen = name + rest, owner, set()
                while current in target and current not in seen:
                    if member in target[current][0]: break
                    seen.add(current); current = target[current][1]
                else:
                    if current is None or current in target or current.startswith('Lcom/guille') or owner not in target:
                        found.setdefault(os.path.relpath(path, decoded), set()).add(owner + '->' + member)
    return found


if __name__ == '__main__':
    result = problems(sys.argv[1])
    for path, refs in sorted(result.items()):
        print(path)
        for ref in sorted(refs): print('   ', ref[:170])
    print('unresolved references:', sum(len(v) for v in result.values()))
    sys.exit(1 if result else 0)
