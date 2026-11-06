#!/usr/bin/env python3
"""Translate compiled code (a .dex) written against one Spring version so it runs on another.

Uses a map from tools/spring_map.py. The DEX is disassembled with apktool's smali tools, every Spring class, method
and field reference is renamed in one pass, and the result is reassembled. Then every Spring name it references is
checked against the target version's decoded APK; anything missing fails the translation instead of crashing later.

    python3 tools/spring_translate.py map.json TARGET_DECODED in.dex out.dex
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spring_map
import toolchain


def run(*command):
    subprocess.run([str(c) for c in command], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def declared(decoded):
    """Every class, method and field declared in a decoded APK: {'Lowner;': {'name(desc)', 'name:type'}}."""
    names = {}
    for directory, _, files in os.walk(decoded):
        if os.sep + 'smali' not in directory: continue
        for file in files:
            if not file.endswith('.smali'): continue
            text = open(os.path.join(directory, file), errors='ignore').read()
            head = re.search(r'^\.class [^\n]*?(L[^;]+;)', text, re.M)
            if not head: continue
            members = set(re.findall(r'^\.method (?:[a-z-]+ )*(\S+?\(.*)$', text, re.M))
            members |= set(re.findall(r'^\.field (?:[a-z-]+ )*(\S+?:[^\s=]+)', text, re.M))
            sup = re.search(r'^\.super (L[^;]+;)', text, re.M)
            names[head.group(1)] = (members, sup.group(1) if sup else None)
    return names


def unresolved(smali_root, target):
    """Spring references in the translated code that the target APK doesn't declare (searching superclasses too)."""
    problems = set()
    for path in Path(smali_root).rglob('*.smali'):
        for owner, name, rest in re.findall(r'(L[^;\s()\["]+;)->([^(:\s"]+)(\([^)\s"]*\)[^\s,}"]+|:[^\s,}"]+)', path.read_text()):
            if owner not in target: continue                  # Android, Kotlin or the code's own classes
            member, seen, current = name + rest, set(), owner
            while current in target and current not in seen:
                if member in target[current][0]: break
                seen.add(current); current = target[current][1]
            else:
                if current not in target and current is not None and not current.startswith('Lcom/guille/'):
                    continue                                  # inherited from Android (getFilesDir, onCreate, ...)
                problems.add(owner + '->' + member)
    return sorted(problems)


def translate_dex(mapping, target_decoded, source, output, target=None, skip=()):
    """skip: class names (Lwinterx/...;) left out of the result, e.g. tables the target build regenerates."""
    translator = spring_map.Translator(mapping)
    target = target or declared(target_decoded)
    with tempfile.TemporaryDirectory(prefix='winterx-translate-') as directory:
        work = Path(directory)
        wrapped = work / 'in.apk'
        with zipfile.ZipFile(wrapped, 'w') as archive: archive.write(source, 'classes.dex')
        decoded = work / 'decoded'
        run(*toolchain.apktool(), 'd', '--no-res', '-f', '-o', decoded, wrapped)
        for path in (decoded / 'smali').rglob('*.smali'):
            text = path.read_text()
            head = re.search(r'^\.class [^\n]*?(L[^;]+;)', text, re.M)
            if head and head.group(1) in skip: path.unlink(); continue
            path.write_text(translator.smali(text))
        missing = dict(translator.missing)
        problems = unresolved(decoded / 'smali', target)
        if missing or problems:
            return {'ok': False, 'unmapped': sorted(missing), 'unresolved': problems}
        rebuilt = work / 'out.apk'
        run(*toolchain.apktool(), 'b', decoded, '-o', rebuilt)
        with zipfile.ZipFile(rebuilt) as archive: Path(output).write_bytes(archive.read('classes.dex'))
    return {'ok': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('map'); parser.add_argument('target_decoded'); parser.add_argument('source'); parser.add_argument('output')
    args = parser.parse_args()
    result = translate_dex(json.load(open(args.map)), args.target_decoded, args.source, args.output)
    print(json.dumps(result, indent=1))
    sys.exit(0 if result['ok'] else 1)


if __name__ == '__main__': main()
