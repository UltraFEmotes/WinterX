"""Check a Spring field map against Kotlin data-class toString() labels ("dockApps=" names the same field in both
versions), printing pairs that disagree and writing the label-based pairs to FIXES.json.

    python3 tools/spring_labels.py OLD_DECODED NEW_DECODED map.json FIXES.json
"""
import json, os, re, sys

def labels(root):
    out = {}
    for d, _, fs in os.walk(root):
        for f in fs:
            if not f.endswith('.smali'): continue
            t = open(os.path.join(d, f), errors='ignore').read()
            head = re.search(r'^\.class[^\n]* L([^;]+);', t, re.M)
            if not head or '.method public final toString()Ljava/lang/String;' not in t: continue
            i = t.index('.method public final toString()Ljava/lang/String;'); b = t[i:t.index('.end method', i)]
            lines = [l.strip() for l in b.split('\n') if l.strip() and not l.strip().startswith('.line')]
            names = {}
            for k, l in enumerate(lines):
                m = re.search(r'const-string v\d+, "(?:\w+\(|, )?(\w+)="', l)
                if not m: continue
                for x in lines[k + 1:k + 6]:
                    g = re.search(r'iget\S* v\d+, p0, L[^;]+;->(\w+):(\S+)', x)
                    if g: names[m.group(1)] = g.group(1) + ':' + g.group(2); break
            if names: out[head.group(1)] = names
    return out

old, new, mapping = labels(sys.argv[1]), labels(sys.argv[2]), json.load(open(sys.argv[3]))
wrong, fixes = 0, {}
for oc, names in old.items():
    nc = mapping['classes'].get(oc, oc)
    if nc not in new: continue
    for label, ofield in names.items():
        nfield = new[nc].get(label)
        if not nfield: continue
        key = 'L%s;->%s' % (oc, ofield); want = 'L%s;->%s' % (nc, nfield)
        have = mapping['fields'].get(key)
        if have != want:
            wrong += 1; fixes[key] = want
            print('%-40s %-22s map %-40s label says %s' % (oc, label, have, want))
json.dump(fixes, open(sys.argv[4], 'w'), indent=1)
print('disagreements:', wrong, 'of', sum(len(v) for v in old.values()))
