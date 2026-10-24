#!/usr/bin/env python3
"""texpak_live.py <disc tree> --out DIR [--observed LOG]... [--write-pak]   (lane purge-movies24, 2026-10-24; offline)

Dead tex.pak key prune, by key liveness over a disc's final file tree (fp_iso.py extract). A key of the tree's
dc/tex.pak is LIVE when some other file on the disc can make the runtime ask for it:
  1. scan: the key's two u32 words appear, little- or big-endian at a 4-byte boundary, in any file of the tree
     (1ST_READ.BIN and the overlays for code tables, dc/native packages and their part tables, dc/resident.bin, the
     R4NREF / R4PREF records of the room / enemy / sub screen archives, the rekeyed r4pw parts, ...);
  2. record: an R4NREF / R4PREF record (crc @8, fnv @12) anywhere names it (also non-pak keys, for 4);
  3. tpl: it is the source-texel identity (prepare_native_ui.image_identity = native_ui.cpp full_hash) of a GameCube
     TPL image found anywhere on the disc (magic 0x0020AF30, parsed by convert_tpl.parse_tpl);
  4. pair: it is material_pair_identity(colour, mask) of two keys from 1-3 found in the same file.
Every other key is DEAD: nothing on the disc can produce its identity. Loose dc/tex/<n>/<key>.re4tex files are left
alone (texpack::find wins over them anyway; t11-fix.py's DROP_LOOSE owns them).
--observed: game logs ("native UI: load /cd/dc/tex/<n>/<key>.re4tex", census / TEXCHK runs); every observed pak key
must be live, else exit 1 (the recall gate of this model). --write-pak: DIR/tex.pak = the pack with the live keys only
(texpack.build + verify, same package bytes). Output: DIR/live.tsv (key, bytes, reasons), DIR/SUMMARY.txt.
Never applied by this tool: the coordinator stages DIR/tex.pak as the last data set of the final line, then TEXCHK
over all rooms (incl. the castle)."""
import argparse, collections, os, re, struct, sys, zlib
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2])); sys.path.insert(0, str(HERE.parents[1]))
import texpack                     # noqa: E402
import convert_tpl as ct           # noqa: E402
import prepare_native_ui as pnu    # noqa: E402

TPL_MAGIC = b'\x00\x20\xaf\x30'
REC = re.compile(rb'R4[NP]REF\x00\x00')
LOAD = re.compile(r'load /cd/dc/tex/[0-9a-f]+/([0-9a-f]{8})-([0-9a-f]{8})\.re4tex')


def pak_index(blob):
    texpack.verify(blob)
    _m, _v, count, ioff, _d = struct.unpack_from('<8s4I', blob, 0)
    return {struct.unpack_from('<II', blob, ioff + 16 * i): struct.unpack_from('<II', blob, ioff + 16 * i + 8)
            for i in range(count)}


def scan_pairs(b, keys64_le, keys64_be):
    """pak keys whose (crc, fnv) words sit at a 4-byte boundary, LE or BE"""
    n = len(b) // 4 * 4
    if n < 8:
        return set()
    out = set()
    for dt, ks in (('<u4', keys64_le), ('>u4', keys64_be)):
        w = np.frombuffer(b[:n], dtype=dt).astype(np.uint64)
        v = w[:-1] | (w[1:] << np.uint64(32))
        hit = np.isin(v, ks)
        for x in np.unique(v[hit]):
            x = int(x); out.add((x & 0xffffffff, x >> 32))
    return out


def records(b):
    out = set()
    for m in REC.finditer(b):
        if m.start() + 16 <= len(b):
            out.add(struct.unpack_from('<II', b, m.start() + 8))
    return out


def tpl_keys(b):
    out, i = set(), b.find(TPL_MAGIC)
    while i >= 0:
        try:
            for img in ct.parse_tpl(b[i:]):
                k = pnu.image_identity(img)[0]
                out.add(tuple(int(x, 16) for x in k.split('-')))
        except Exception:
            pass
        i = b.find(TPL_MAGIC, i + 4)
    return out


def pair_key(c, m):
    payload = b'R4MPv001' + struct.pack('<4I', c[0], c[1], m[0], m[1])
    fnv = 2166136261
    for x in payload:
        fnv = ((fnv ^ x) * 16777619) & 0xffffffff
    return (zlib.crc32(payload) & 0xffffffff, fnv)


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    a.add_argument('tree', type=Path); a.add_argument('--out', required=True, type=Path)
    a.add_argument('--observed', action='append', default=[]); a.add_argument('--write-pak', action='store_true')
    a.add_argument('--max-pairs', type=int, default=4000, help='skip the pair step for files with more found keys')
    o = a.parse_args(argv)
    blob = (o.tree / 'dc' / 'tex.pak').read_bytes()
    idx = pak_index(blob)
    keys = set(idx)
    le = np.array(sorted({k[0] | (k[1] << 32) for k in keys}), dtype=np.uint64)
    why = collections.defaultdict(set)
    nfiles = 0
    for p in sorted(o.tree.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(o.tree).as_posix()
        if rel == 'dc/tex.pak' or rel.startswith('dc/tex/'):
            continue
        b = p.read_bytes(); nfiles += 1
        found = set()
        for k in scan_pairs(b, le, le):
            why[k].add('scan:' + rel); found.add(k)
        for k in records(b):
            found.add(k)
            if k in keys: why[k].add('record:' + rel)
        if TPL_MAGIC in b:
            for k in tpl_keys(b):
                found.add(k)
                if k in keys: why[k].add('tpl:' + rel)
        if 1 < len(found) <= o.max_pairs:
            fl = sorted(found)
            for c in fl:
                for m in fl:
                    if c != m:
                        k = pair_key(c, m)
                        if k in keys: why[k].add('pair:' + rel)
        elif len(found) > o.max_pairs:
            print('pairs skipped (%d keys): %s' % (len(found), rel))
    live = {k for k in keys if why.get(k)}
    o.out.mkdir(parents=True, exist_ok=True)
    with open(o.out / 'live.tsv', 'w') as w:
        w.write('key\tbytes\tlive\treasons\n')
        for k in sorted(keys):
            r = sorted(why.get(k, ()))
            w.write('%08x-%08x\t%d\t%d\t%s\n' % (k[0], k[1], idx[k][1], 1 if r else 0, ','.join(r[:6])))
    obs = set()
    for f in o.observed:
        for m in LOAD.finditer(open(f, errors='replace').read()):
            obs.add((int(m.group(1), 16), int(m.group(2), 16)))
    obs &= keys
    missed = sorted(obs - live)
    sec = lambda n: (n + 2047) // 2048 * 2048
    dead = keys - live
    lines = ['tree %s files %d' % (o.tree, nfiles),
             'pak keys %d bytes %d (sector-rounded %d)' % (len(keys), sum(v[1] for v in idx.values()),
                                                           sum(sec(v[1]) for v in idx.values())),
             'live %d bytes %d' % (len(live), sum(idx[k][1] for k in live)),
             'dead %d bytes %d (sector-rounded %d)' % (len(dead), sum(idx[k][1] for k in dead),
                                                      sum(sec(idx[k][1]) for k in dead)),
             'by reason: ' + ' '.join('%s=%d' % (r, n) for r, n in sorted(collections.Counter(
                 min(x.split(':')[0] for x in why[k]) for k in live).items())),
             'observed pak keys %d, not live %d%s' % (len(obs), len(missed),
                                                      (': ' + ' '.join('%08x-%08x' % k for k in missed[:20])) if missed else '')]
    if o.write_pak:
        pk = {k: blob[idx[k][0]:idx[k][0] + idx[k][1]] for k in live}
        out = texpack.build(pk); texpack.verify(out)
        (o.out / 'tex.pak').write_bytes(out)
        lines.append('tex.pak %d -> %d bytes' % (len(blob), len(out)))
    (o.out / 'SUMMARY.txt').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    return 1 if missed else 0


if __name__ == '__main__':
    sys.exit(main())
