#!/usr/bin/env python3
"""lane mipmap22: (1) install the rect21 tables for the mipfix22 pack + texconv22 add-on,
(2) remap dc/resident.bin so a room lists the scoped (WORLD_RECT21) key in place of its original.

  tables_resident.py tables <rect21 dir> <mipfix dir> <addon-manifest.json>
  tables_resident.py parts <resident.bin in> <out> <origins.inc> <world dir> <scoped_representations.inc> <report.tsv> [keep.tsv]
      (preferred) remap from the worlds' parsed part records; keeps the original where a part or a first-sight load
      still uses it; replacement records carry the package's stored size for the preload estimate.
  tables_resident.py resident <resident.bin in> <resident.bin out> <origins.inc> <world dir dc/native> [report.tsv] [keep.tsv]
      keep.tsv (room hex, original key): originals another consumer still loads; listed beside the scoped key.
"""
import json, re, struct, sys
from collections import defaultdict
from pathlib import Path

ROW = re.compile(r'^\{0x([0-9a-f]+)U,0x([0-9a-f]+)U')


def key(l):
    return tuple(int(x, 16) for x in ROW.match(l).groups())


def rows(p):
    return [l for l in Path(p).read_text().splitlines() if l.startswith('{')]


def tables(rdir, mdir, man):
    rdir, mdir = Path(rdir), Path(mdir)
    rep = rows(mdir / 'scoped_representations792.inc') + rows(mdir / 'addon_scoped_representations.inc')
    rep = sorted(rep, key=key)
    assert len({key(l) for l in rep}) == len(rep) == 798, len(rep)
    (rdir / 'scoped_representations.inc').write_text(
        '// lane mipmap22: mipfix22 792 rows (quality-gate rebound) + texconv22 add-on 6 rows, sorted\n' + '\n'.join(rep) + '\n')
    org = rows(rdir / 'scoped_origins792.inc')
    have = {key(l) for l in org}
    for e in json.load(open(man))['held23']:
        if not e.get('addon_key'):
            continue
        sc, sf = (int(x, 16) for x in e['addon_key'].split('-'))
        oc, of = (int(x, 16) for x in e['original_key'].split('-'))
        if (sc, sf) not in have:
            org.append('{0x%08xU,0x%08xU,0x%08xU,0x%08xU},' % (sc, sf, oc, of))
    org = sorted(org, key=key)
    missing = {key(l) for l in rep} - {key(l) for l in org}
    assert not missing, ['%08x-%08x' % k for k in missing]
    (rdir / 'scoped_origins.inc').write_text(
        '// lane mipmap22: scoped_origins792.inc + texconv22 add-on origins, sorted by scoped key\n' + '\n'.join(org) + '\n')
    h = rdir / 'world_rect_bind.h'
    t = re.sub(r'qualified_count==\d+U', 'qualified_count==798U', h.read_text())
    h.write_text(t)
    print('tables: representations %d origins %d' % (len(rep), len(org)))


def resident(src, dst, origins, wdir, report=None, keep=None):
    keepset = set()
    if keep:
        for l in Path(keep).read_text().splitlines():
            if l and not l.startswith('#') and not l.startswith('room	'):
                r, k = l.split('	')[:2]
                keepset.add((int(r, 16), tuple(int(x, 16) for x in k.split('-'))))
    o2s = defaultdict(list)
    for l in rows(origins):
        sc, sf, oc, of = (int(x, 16) for x in re.findall(r'0x([0-9a-f]+)U', l)[:4])
        o2s[(oc, of)].append((sc, sf))
    worlds = {}
    for w in Path(wdir).glob('*/ps2-world.r4pw'):
        worlds[int(w.parent.name[1:], 16)] = w.read_bytes()
    b = Path(src).read_bytes()
    assert len(b) % 512 == 0
    recs = [struct.unpack_from('<4H2I', b, i) for i in range(0, len(b), 16)]
    out, rep, changed = [], [], 0
    for room, w, h, f, c, n in recs:
        sub = []
        wb = worlds.get(room)
        if room and wb is not None:
            for sc, sf in o2s.get((c, n), []):
                if struct.pack('<II', sc, sf) in wb:
                    sub.append((sc, sf))
        if sub:
            if (room, (c, n)) in keepset:
                out.append((room, w, h, f, c, n))   # another consumer still draws the original (first-sight log)
            for sc, sf in sub:
                out.append((room, w, h, f, sc, sf)); rep.append('%03x\t%08x-%08x\t%08x-%08x' % (room, c, n, sc, sf))
            changed += 1
        else:
            out.append((room, w, h, f, c, n))
    real = sorted({r for r in out if r[1]}, key=lambda r: (r[0] == 0 and r[1] == 0, r[0], r[4], r[5]))
    real = [r for r in real if not (r[0] == 0 and r[1] == 0 and not (r[4] | r[5]))]
    real.sort(key=lambda r: (r[0], r[4], r[5]))
    while len(real) % 32:
        real.append((0, 0, 0, 0, 0, 0))
    Path(dst).write_bytes(b''.join(struct.pack('<4H2I', *r) for r in real))
    if report:
        Path(report).write_text('room\toriginal\tscoped\n' + '\n'.join(rep) + '\n')
    print('resident: records %d -> %d, %d original keys remapped' % (len(recs), len(real), changed))


def world_part_keys(blob):
    """Texture keys of an R4PW sidecar's part (material) records: header '<4s7I', then 16-byte parts '<IIHH4B'."""
    magic, version, placements, parts, meshes, crc, r0, r1 = struct.unpack_from('<4s7I', blob)
    assert magic == b'R4PW' and len(blob) == 32 + 16 * parts + 52 * placements, 'R4PW layout'
    return {(c, f) for c, f, *_ in struct.iter_unpack('<IIHH4B', blob[32:32 + 16 * parts])}


def stored_dims(rep_inc):
    """scoped key -> stored (width, height) of its package, from scoped_representations.inc."""
    out = {}
    for l in rows(rep_inc):
        v = [int(x) for x in re.findall(r'(?<![0-9a-fx])(\d+)U', l)]
        c, f = key(l)
        out[(c, f)] = (v[2], v[3])   # {crc,fnv,logical w,h,{stored w,h,...}} -> decimal fields: lw, lh, sw, sh, ...
    return out


def resident_parts(src, dst, origins, wdir, rep_inc, report, keep=None):
    keepset = set()
    if keep:
        for l in Path(keep).read_text().splitlines():
            if l and not l.startswith('#') and not l.startswith('room\t'):
                r, k = l.split('\t')[:2]
                keepset.add((int(r, 16), tuple(int(x, 16) for x in k.split('-'))))
    o2s = defaultdict(list)
    for l in rows(origins):
        sc, sf, oc, of = (int(x, 16) for x in re.findall(r'0x([0-9a-f]+)U', l)[:4])
        o2s[(oc, of)].append((sc, sf))
    dims = stored_dims(rep_inc)
    parts = {int(w.parent.name[1:], 16): world_part_keys(w.read_bytes()) for w in Path(wdir).glob('*/ps2-world.r4pw')}
    b = Path(src).read_bytes()
    recs = [struct.unpack_from('<4H2I', b, i) for i in range(0, len(b), 16)]
    out, rep = [], []
    n = dict(references=0, remapped=0, kept=0, dropped=0)
    for room, w, h, f, c, fn in recs:
        cand = o2s.get((c, fn), [])
        if not room or not w or not cand:
            out.append((room, w, h, f, c, fn)); continue
        n['references'] += 1
        pk = parts.get(room, set())
        sub = [s for s in cand if s in pk]
        if not sub:   # this room's world does not draw a scoped version: the original stays
            out.append((room, w, h, f, c, fn)); n['kept'] += 1
            rep.append('%03x\t%08x-%08x\t-\tkept:no-scoped-part' % (room, c, fn)); continue
        still = (c, fn) in pk or (room, (c, fn)) in keepset
        if still:
            out.append((room, w, h, f, c, fn)); n['kept'] += 1
        else:
            n['remapped'] += 1
        for s in sub:
            sw, sh = dims.get(s, (w, h))
            out.append((room, sw, sh, f, s[0], s[1]))
            rep.append('%03x\t%08x-%08x\t%08x-%08x\t%s' % (room, c, fn, s[0], s[1],
                       'kept+scoped:' + ('world-part' if (c, fn) in pk else 'first-sight') if still else 'remapped'))
    real = sorted({r for r in out if r[1]}, key=lambda r: (r[0], r[4], r[5]))
    while len(real) % 32:
        real.append((0, 0, 0, 0, 0, 0))
    Path(dst).write_bytes(b''.join(struct.pack('<4H2I', *r) for r in real))
    Path(report).write_text('room\toriginal\tscoped\twhy\n' + '\n'.join(rep) + '\n')
    print('resident(parts): ' + ' '.join('%s=%d' % kv for kv in n.items()) + ' records %d -> %d' % (len(recs), len(real)))


if __name__ == '__main__':
    if sys.argv[1] == 'tables':
        tables(*sys.argv[2:5])
    elif sys.argv[1] == 'parts':
        resident_parts(*sys.argv[2:])
    else:
        resident(*sys.argv[2:])
