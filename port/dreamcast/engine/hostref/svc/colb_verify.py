#!/usr/bin/env python3
"""colb_verify.py <tree> <out dir> <tool files...> (lane eng-skel2; colbake.sh --verify): the baked collision's receipt.

1. COLB-RECEIPT.txt: every input (the tree's archives, the tool files given) and every output has the SHA-256 written
   there (a stale receipt, a changed tool or a changed output: FAIL).
2. Each output archive against its input: the same entries and tags; every entry but SAT and EAT the same bytes; each
   SAT / EAT entry's files (a table's files, or the one file) baked: the cSatFile header the original's but x8
   (0xC0B2), version 1, the normal table inside the file and the original's bytes, the tables' FNV-1a hash the one the
   bake printed (COLB-LOG.txt).
Exit 0 when every room holds."""
import hashlib
import os
import re
import struct
import sys

MAGIC = 0xC0B2
SIZEOF_PIECE = 80          # sizeof(ColPiece), 32-bit


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def fnv(b, h=2166136261):
    for x in b:
        h = ((h ^ x) * 16777619) & 0xFFFFFFFF
    return h


def entries(d):
    num = struct.unpack_from('<I', d, 0)[0]
    ofs = list(struct.unpack_from('<%dI' % num, d, 0x10))
    tags = [d[0x10 + 4 * num + 4 * i:0x10 + 4 * num + 4 * i + 4] for i in range(num)]
    offs = sorted(set(ofs)) + [len(d)]
    ext = [min(x for x in offs if x > o) - o for o in ofs]
    return tags, ofs, ext


def files(d, o):
    ver = d[o]
    if ver == 0xFF or not (ver & 0x80):
        return [0]
    first = struct.unpack_from('<I', d, o + 4)[0]
    n = d[o + 1] or (first - 4) // 4
    return list(struct.unpack_from('<%dI' % n, d, o + 4))


def main():
    tree, out, tools = sys.argv[1], sys.argv[2], sys.argv[3:]
    bad = []
    rec = open(os.path.join(out, 'COLB-RECEIPT.txt')).read().splitlines()
    log = open(os.path.join(out, 'COLB-LOG.txt')).read()
    rooms = []
    tool_sha = {os.path.basename(t): sha(t) for t in tools}
    for line in rec:
        if line.startswith('in '):
            _, h, name = line.split()
            rooms.append(name[:-4])
            if sha(os.path.join(tree, name)) != h:
                bad.append('input changed: ' + name)
        elif line.startswith('tool '):
            _, h, name = line.split()
            if tool_sha.get(os.path.basename(name)) != h:
                bad.append('tool changed: ' + name)
        elif line.startswith('out '):
            _, h, name = line.split()
            if sha(os.path.join(out, name)) != h:
                bad.append('output changed: ' + name)
    if set(tool_sha) - set(os.path.basename(l.split()[2]) for l in rec if l.startswith('tool ')):
        bad.append('a tool is not in the receipt')
    for r in rooms:
        a = open(os.path.join(tree, r + '.arc'), 'rb').read()
        b = open(os.path.join(out, r + '.arc'), 'rb').read()
        ta, oa, ea = entries(a)
        tb, ob, eb = entries(b)
        if ta != tb:
            bad.append(r + ': entries differ')
            continue
        nb = 0
        for i, t in enumerate(ta):
            if t not in (b'SAT\0', b'EAT\0'):
                if a[oa[i]:oa[i] + ea[i]] != b[ob[i]:ob[i] + ea[i]]:
                    bad.append('%s entry %d %s: bytes differ' % (r, i, t[:3].decode()))
                continue
            fa, fb = files(a, oa[i]), files(b, ob[i])
            if len(fa) != len(fb) or (len(fa) > 1 and a[oa[i]:oa[i] + 4] != b[ob[i]:ob[i] + 4]):
                bad.append('%s entry %d: file table differs' % (r, i))
                continue
            h, seen = 2166136261, set()
            for k, (x, y) in enumerate(zip(fa, fb)):
                fo, go = oa[i] + x, ob[i] + y
                if y in seen:
                    continue
                seen.add(y)
                ha, hb = a[fo:fo + 0x14], b[go:go + 0x14]
                if struct.unpack_from('<H', ha, 8)[0] != 0 or struct.unpack_from('<H', hb, 8)[0] != MAGIC or \
                        ha[:8] + ha[10:] != hb[:8] + hb[10:]:
                    bad.append('%s entry %d file %d: header' % (r, i, k))
                    continue
                nv, nn = struct.unpack_from('<2H', ha, 2)
                ver, onorm, opiece, nbytes = struct.unpack_from('<IiII', b, go + 0x14)
                if ver != 1 or b[go + onorm:go + onorm + 12 * nn] != a[fo + 0x14 + 12 * nv:fo + 0x14 + 12 * nv + 12 * nn]:
                    bad.append('%s entry %d file %d: normal table' % (r, i, k))
                if any(b[go + opiece:go + opiece + SIZEOF_PIECE]):
                    bad.append('%s entry %d file %d: record not empty' % (r, i, k))
                h = fnv(b[go + opiece + SIZEOF_PIECE:go + nbytes], h)
                nb += 1
            m = re.search(r'COLB %s %s entry %d: \d+ B -> \d+ B, tables ([0-9a-f]{8})' % (re.escape(r), t[:3].decode(), i), log)
            if not m or int(m.group(1), 16) != h:
                bad.append('%s entry %d: tables hash %08x, the bake printed %s' % (r, i, h, m.group(1) if m else 'none'))
        print('%s: %d baked files, archive %d -> %d B' % (r, nb, len(a), len(b)))
    for x in bad[:40]:
        print('FAIL', x)
    print('colb_verify: %d rooms, %s' % (len(rooms), 'every check holds' if not bad else '%d FAILS' % len(bad)))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
