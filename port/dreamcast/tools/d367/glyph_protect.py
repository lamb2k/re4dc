"""glyph_protect.py (lane glyph27, 2026-11-02): the Dreamcast controller glyph pictures listed in rr/ui-glyph-protect.tsv.
They are UI made for the Dreamcast, not GameCube assets, so PS2/GC picture swap tools must leave them alone.

  import glyph_protect
  glyph_protect.keys()            -> {'6d33c3f9-9f8cf668': sha256, ...}
  glyph_protect.skip(key)         -> True for a protected key (swap tools: do not replace it)
  glyph_protect.check(pak_dict)   -> list of protected keys whose bytes differ ({(crc, fnv): bytes} or {'crc-fnv': bytes})
  python3 glyph_protect.py <tex.pak>   exits 1 and names each protected key a pack does not hold as listed
"""
import hashlib
import os
import struct
import sys

TSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rr', 'ui-glyph-protect.tsv')


def keys():
    out = {}
    for line in open(TSV):
        if line.startswith('#') or not line.strip():
            continue
        k, h = line.split('\t')[:2]
        out[k] = h
    return out


def skip(key):
    if isinstance(key, tuple):
        key = '%08x-%08x' % key
    return key.split('.')[0][:17] in keys()


def check(pak):
    bad = []
    for k, h in sorted(keys().items()):
        t = tuple(int(x, 16) for x in k.split('-'))
        b = pak.get(t, pak.get(k))
        if b is None or hashlib.sha256(b).hexdigest() != h:
            bad.append(k)
    return bad


def read_pak(path):
    b = open(path, 'rb').read()
    magic, ver, count, ioff, doff = struct.unpack_from('<8s4I', b, 0)
    assert magic == b'RE4PAK1\x00', path
    return {(c, f): b[o:o + n] for c, f, o, n in (struct.unpack_from('<4I', b, ioff + 16 * i) for i in range(count))}


if __name__ == '__main__':
    bad = check(read_pak(sys.argv[1]))
    for k in bad:
        print('glyph_protect: %s does not hold the protected controller glyph %s' % (sys.argv[1], k))
    print('glyph_protect: %d protected keys, %d differ' % (len(keys()), len(bad)))
    sys.exit(1 if bad else 0)
