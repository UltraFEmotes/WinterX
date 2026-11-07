#!/usr/bin/env python3
"""A small editor for binary AndroidManifest.xml files (the compiled "AXML" format inside an APK).

Two edits, both needed to install a renamed, debuggable copy of an app beside the original:
  rename(data, {"old": "new"})                    replace exact strings in the string pool (never part of a string)
  set_bool(data, "application", "debuggable", 0x0101000f, True)
                                                   set (or add) a boolean android: attribute on an element

Check results with `aapt2 dump xmltree`. The format: a RES_XML chunk holding a string pool, a resource map (string i
names attribute resource ID map[i]), then element chunks whose fields point into the string pool by index.

    python3 tools/axml.py IN.xml OUT.xml --rename old=new ... [--debuggable]
"""
import argparse
import struct

XML, STRINGS, RESOURCES = 0x0003, 0x0001, 0x0180
START_NS, END_NS, START, END, CDATA = 0x0100, 0x0101, 0x0102, 0x0103, 0x0104
UTF8 = 0x100
TYPE_STRING, TYPE_BOOLEAN = 0x03, 0x12
NONE = 0xFFFFFFFF
ANDROID = 'http://schemas.android.com/apk/res/android'


class Manifest:
    def __init__(self, data):
        kind, header, size = struct.unpack_from('<HHI', data, 0)
        if kind != XML or size != len(data): raise ValueError('Not a binary XML file')
        self.chunks = []                                        # (type, header size, header+body bytes) after the pool
        at = header
        while at < len(data):
            kind, head, size = struct.unpack_from('<HHI', data, at)
            chunk = data[at:at + size]
            if kind == STRINGS: self._read_pool(chunk)
            elif kind == RESOURCES: self.resources = list(struct.unpack_from('<%dI' % ((size - 8) // 4), chunk, 8))
            else: self.chunks.append([kind, head, bytearray(chunk)])
            at += size
        if not hasattr(self, 'resources'): self.resources = []

    # ----- string pool -----

    def _read_pool(self, chunk):
        _, head, size, count, styles, flags, start, style_start = struct.unpack_from('<HHIIIIII', chunk, 0)
        self.utf8 = bool(flags & UTF8)
        self.flags = flags
        offsets = struct.unpack_from('<%dI' % count, chunk, head)
        self.strings = [self._decode(chunk, start + o) for o in offsets]
        if styles:
            style_offsets = struct.unpack_from('<%dI' % styles, chunk, head + 4 * count)
            self.style_offsets = list(style_offsets)
            self.style_data = bytes(chunk[style_start:size])
        else:
            self.style_offsets, self.style_data = [], b''

    def _decode(self, chunk, at):
        if self.utf8:
            n, at = _len8(chunk, at)                            # length in UTF-16 units (unused)
            n, at = _len8(chunk, at)                            # length in bytes
            return bytes(chunk[at:at + n]).decode('utf-8', 'surrogatepass')
        n, at = _len16(chunk, at)
        return bytes(chunk[at:at + 2 * n]).decode('utf-16-le', 'surrogatepass')

    def _encode(self, text):
        if self.utf8:
            raw = text.encode('utf-8', 'surrogatepass')
            return _put8(len(text.encode('utf-16-le', 'surrogatepass')) // 2) + _put8(len(raw)) + raw + b'\0'
        raw = text.encode('utf-16-le', 'surrogatepass')
        return _put16(len(raw) // 2) + raw + b'\0\0'

    def _pool(self):
        data = bytearray(); offsets = []
        for text in self.strings:
            offsets.append(len(data)); data += self._encode(text)
        while len(data) % 4: data += b'\0'
        head = 28
        start = head + 4 * len(self.strings) + 4 * len(self.style_offsets)
        style_start = start + len(data) if self.style_offsets else 0
        body = struct.pack('<%dI' % len(offsets), *offsets) + struct.pack('<%dI' % len(self.style_offsets), *self.style_offsets)
        size = start + len(data) + len(self.style_data)
        flags = self.flags & ~0x1                                # the "sorted" flag no longer holds
        return struct.pack('<HHIIIIII', STRINGS, head, size, len(self.strings), len(self.style_offsets), flags, start,
                           style_start) + body + bytes(data) + self.style_data

    # ----- edits -----

    def rename(self, mapping):
        """Exact whole-string replacements; returns how many strings changed."""
        changed = 0
        for i, text in enumerate(self.strings):
            if text in mapping: self.strings[i] = mapping[text]; changed += 1
        return changed

    def _insert_resource_string(self, name, resource):
        """A new attribute-name string mapped to resource; it must sit inside the resource-mapped prefix of the pool."""
        for i, rid in enumerate(self.resources):
            if rid == resource and self.strings[i] == name: return i
        index = len(self.resources)
        self.strings.insert(index, name)
        self.resources.append(resource)
        # Every reference to a later string moves up by one.
        for chunk in self.chunks: _shift_refs(chunk, index)
        return index

    def set_bool(self, element, name, resource, value):
        """Set android:name on the first <element> (adding it, in resource-ID order, when missing)."""
        for chunk in self.chunks:
            if chunk[0] != START or self.strings[_u32(chunk[2], 20)] != element: continue
            attrs = _attributes(chunk[2])
            for k, (a_ns, a_name, raw, size, res0, kind, data) in enumerate(attrs):
                if self._resource(a_name) == resource:
                    _set_attr(chunk[2], k, a_ns, a_name, NONE, TYPE_BOOLEAN, 0xFFFFFFFF if value else 0)
                    return
            name_index = self._insert_resource_string(name, resource)
            ns = self.strings.index(ANDROID)                     # after the insert, which may have moved it
            attrs = _attributes(chunk[2])
            position = len(attrs)
            for k, attr in enumerate(attrs):
                rid = self._resource(attr[1])
                if rid is None or rid > resource: position = k; break
            _insert_attr(chunk, position, (ns, name_index, NONE, 8, 0, TYPE_BOOLEAN, 0xFFFFFFFF if value else 0))
            return
        raise ValueError('No <%s> element' % element)

    def _resource(self, string_index):
        return self.resources[string_index] if string_index < len(self.resources) else None

    def bytes(self):
        pool = self._pool()
        resources = struct.pack('<HHI', RESOURCES, 8, 8 + 4 * len(self.resources)) + struct.pack('<%dI' % len(self.resources), *self.resources)
        body = pool + resources + b''.join(bytes(c[2]) for c in self.chunks)
        return struct.pack('<HHI', XML, 8, 8 + len(body)) + body


# ----- element chunks -----
# Node header: type u16, headerSize u16 (16), size u32, line u32, comment u32. START body (at 16): ns u32, name u32,
# attributeStart u16 (20), attributeSize u16 (20), attributeCount u16, idIndex u16, classIndex u16, styleIndex u16,
# then attributes: ns u32, name u32, rawValue u32, value size u16, res0 u8, dataType u8, data u32.

def _u32(chunk, at): return struct.unpack_from('<I', chunk, at)[0]


def _attributes(chunk):
    start, size, count = struct.unpack_from('<HHH', chunk, 24)
    return [struct.unpack_from('<IIIHBBI', chunk, 16 + start + i * size) for i in range(count)]


def _set_attr(chunk, k, ns, name, raw, kind, data):
    start, size = struct.unpack_from('<HH', chunk, 24)
    struct.pack_into('<IIIHBBI', chunk, 16 + start + k * size, ns, name, raw, 8, 0, kind, data)


def _insert_attr(entry, position, attr):
    chunk = entry[2]
    start, size, count, id_index, class_index, style_index = struct.unpack_from('<HHHHHH', chunk, 24)
    at = 16 + start + position * size
    blob = struct.pack('<IIIHBBI', *attr) + b'\0' * (size - 20)
    chunk[at:at] = blob
    # 1-based positions of the id/class/style attributes move when one is inserted before them.
    fix = lambda i: i + 1 if i and i > position else i
    struct.pack_into('<HHHHHH', chunk, 24, start, size, count + 1, fix(id_index), fix(class_index), fix(style_index))
    struct.pack_into('<I', chunk, 4, len(chunk))


def _shift_refs(entry, index):
    """Move string references >= index up by one in one node chunk."""
    kind, _, chunk = entry
    def fix(at):
        v = _u32(chunk, at)
        if v != NONE and v >= index: struct.pack_into('<I', chunk, at, v + 1)
    fix(12)                                                     # comment
    if kind in (START_NS, END_NS): fix(16); fix(20)             # prefix, uri
    elif kind == END: fix(16); fix(20)                          # ns, name
    elif kind == CDATA: fix(16); _fix_value(chunk, 24, index)
    elif kind == START:
        fix(16); fix(20)
        start, size, count = struct.unpack_from('<HHH', chunk, 24)
        for i in range(count):
            at = 16 + start + i * size
            fix(at); fix(at + 4); fix(at + 8)
            _fix_value(chunk, at + 12, index)


def _fix_value(chunk, at, index):
    kind, data = chunk[at + 3], _u32(chunk, at + 4)
    if kind == TYPE_STRING and data != NONE and data >= index: struct.pack_into('<I', chunk, at + 4, data + 1)


# ----- string lengths -----

def _len8(data, at):
    n = data[at]
    if n & 0x80: return ((n & 0x7F) << 8) | data[at + 1], at + 2
    return n, at + 1


def _len16(data, at):
    n = struct.unpack_from('<H', data, at)[0]
    if n & 0x8000: return ((n & 0x7FFF) << 16) | struct.unpack_from('<H', data, at + 2)[0], at + 4
    return n, at + 2


def _put8(n):
    if n > 0x7FFF: raise ValueError('String too long')
    return bytes([n]) if n < 0x80 else bytes([0x80 | (n >> 8), n & 0xFF])


def _put16(n):
    if n > 0x7FFFFFFF: raise ValueError('String too long')
    return struct.pack('<H', n) if n < 0x8000 else struct.pack('<HH', 0x8000 | (n >> 16), n & 0xFFFF)


def edit(data, mapping=None, debuggable=False):
    manifest = Manifest(data)
    if mapping: manifest.rename(mapping)
    if debuggable: manifest.set_bool('application', 'debuggable', 0x0101000f, True)
    return manifest.bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('source'); parser.add_argument('output')
    parser.add_argument('--rename', action='append', default=[], help='old=new, an exact string')
    parser.add_argument('--debuggable', action='store_true')
    args = parser.parse_args()
    mapping = dict(item.split('=', 1) for item in args.rename)
    data = open(args.source, 'rb').read()
    open(args.output, 'wb').write(edit(data, mapping, args.debuggable))


if __name__ == '__main__': main()
