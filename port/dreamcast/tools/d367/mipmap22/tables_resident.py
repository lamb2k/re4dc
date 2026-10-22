#!/usr/bin/env python3
"""lane mipmap22: (1) install the rect21 tables for the mipfix22 pack + texconv22 add-on,
(2) remap dc/resident.bin so a room lists the scoped (WORLD_RECT21) key in place of its original.

  tables_resident.py tables <rect21 dir> <mipfix dir> <addon-manifest.json>
  tables_resident.py resident <resident.bin in> <resident.bin out> <origins.inc> <world dir dc/native> [report.tsv]
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


def resident(src, dst, origins, wdir, report=None):
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


if __name__ == '__main__':
    if sys.argv[1] == 'tables':
        tables(*sys.argv[2:5])
    else:
        resident(*sys.argv[2:])
