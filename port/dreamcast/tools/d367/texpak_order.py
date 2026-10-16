#!/usr/bin/env python3
"""texpak_order.py <in tex.pak> <order.txt> <out tex.pak>: the same pack with its packages laid out in load order.
texpak_order.py --keys <run-output.txt>... : prints a load order from game logs (lane plainread16, 2026-10-16).

TEX_PACK_WINDOW (game30.mk) reads tex.pak through a read-ahead window during each room's preload pass; a window read
only helps when the next picture the pass loads is the next package in the file. This tool keeps every package byte
for byte and the index (sorted by key, the runtime's lookup) and only moves the packages: first the keys of order.txt
in their order (one "crc-fnv" or "crc fnv" per line, hex; '#' comments; keys not in the pack and repeats skipped), then
every other package in its old order. Packages still start on 2048-byte boundaries. The output passes texpack.py
--verify; the tool checks that every key maps to identical bytes in both packs. Deterministic.

--keys: the "native UI: load /cd/dc/tex/<n>/<crc>-<fnv>.re4tex" lines of each log, in the order given (give the
route's door runs in route order), first appearance wins. texlow/ and other loose files are not in the pack.
Run it LAST on the release's tex.pak (after every tex_merge.py), or the order is lost.
"""
import hashlib, re, struct, sys, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import texpack  # noqa: E402

LOAD = re.compile(r'native UI: load /cd/dc/tex/[0-9a-f]+/([0-9a-f]{8})-([0-9a-f]{8})\.re4tex')
KEY = re.compile(r'^\s*([0-9a-fA-F]{8})[-\s]+([0-9a-fA-F]{8})\s*$')


def read_pack(blob):
    texpack.verify(blob)
    count, data_at = struct.unpack_from('<I', blob, 12)[0], struct.unpack_from('<I', blob, 20)[0]
    entries = [struct.unpack_from('<4I', blob, 2048 + 16 * i) for i in range(count)]
    return entries, data_at


def reorder(blob, order):
    entries, data_at = read_pack(blob)
    by_key = {(e[0], e[1]): e for e in entries}
    # the old data order (by offset) is the fallback order; one copy per extent (merged packs may share one)
    extents, seen = [], set()
    for k in [(k[0], k[1]) for k in order if (k[0], k[1]) in by_key] + \
             [(e[0], e[1]) for e in sorted(entries, key=lambda e: (e[2], e[0], e[1]))]:
        ext = by_key[k][2:4]
        if ext not in seen:
            seen.add(ext)
            extents.append(ext)
    new_off, data, off = {}, bytearray(), data_at
    for (o, n) in extents:
        new_off[(o, n)] = off
        data += blob[o:o + n] + bytes((-n) % 2048)
        off += n + (-n) % 2048
    index = bytearray()
    for e in entries:  # same keys, same (sorted) order: only the offsets change
        index += struct.pack('<4I', e[0], e[1], new_off[(e[2], e[3])], e[3])
    index += bytes(data_at - 2048 - len(index))
    head = b'RE4PAK1\x00' + struct.pack('<5I', 1, len(entries), 2048, data_at, zlib.crc32(bytes(index)))
    head += bytes(2048 - len(head))
    out = bytes(head) + bytes(index) + bytes(data)
    # every key: identical bytes
    for e in entries:
        no = new_off[(e[2], e[3])]
        if out[no:no + e[3]] != blob[e[2]:e[2] + e[3]]:
            raise SystemExit('texpak_order: key %08x-%08x changed' % (e[0], e[1]))
    texpack.verify(out)
    return out, len(extents)


def keys_from_logs(paths):
    out, seen = [], set()
    for p in paths:
        for line in open(p, encoding='latin-1'):
            m = LOAD.search(line)
            if m:
                k = (int(m.group(1), 16), int(m.group(2), 16))
                if k not in seen:
                    seen.add(k)
                    out.append(k)
    return out


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == '--keys':
        for k in keys_from_logs(sys.argv[2:]):
            print('%08x-%08x' % k)
        return
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    blob = Path(sys.argv[1]).read_bytes()
    order = []
    for line in Path(sys.argv[2]).read_text().splitlines():
        line = line.split('#')[0]
        m = KEY.match(line)
        if m:
            order.append((int(m.group(1), 16), int(m.group(2), 16)))
    out, n = reorder(blob, order)
    Path(sys.argv[3]).write_bytes(out)
    print('texpak_order: %d order keys, %d packages, %d bytes (in %d), sha256 %s' % (
        len(order), n, len(out), len(blob), hashlib.sha256(out).hexdigest()))


if __name__ == '__main__':
    main()
