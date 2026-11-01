#!/usr/bin/env python3
"""prove_props.py (lane props-ps2-26 2026-10-26): exact-bytes PS2 proofs for the room-object model rows of a GC-ASSET
catalog, as provenance-reviewed.tsv rows; and the list of room-object rows that are NOT proven PS2.

  prove_props.py --catalog <gca/raw/catalog.json> --proofs <provenance proofs.json> --fixture <t11-fix pkg.json>
                 --lib <ps2lib> --tsv <rows out> [--left <unproven out>]

Scope: model rows inside st1 room archives (.dar records) that provenance.py (PROVENANCE_FOLLOW_BYTES=1) does not call
ps2. A row is proven when its bytes are reproduced from a PS2 source:
  * room BIN / ETM etc model: ps2_objects.rebuild(GC model, PS2 BIN of the same object) (converter v2/v3, no
    reduction; v4 rows are the props26 store's provenance.tsv) is byte-identical to the member (the object's PS2 BIN is
    the one props_inventory pairs: the ETM name, or the room BIN with the matching bounds);
  * ITM pickup: equal to the ps2lib items/<room>/<name>.bin that ps2_items.py built from the PS2 BIN (its json names
    ps2_bin_sha256).
Anything else is listed (--left) with its member name, for review.
"""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent), str(HERE.parent / 'gc_port23'), str(HERE)]
import build_catalog as bc  # noqa: E402
import ps2_bin as pb  # noqa: E402
import ps2_objects as po  # noqa: E402
import room_smd as rs  # noqa: E402


sha = lambda b: hashlib.sha256(b).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    for k in ('catalog', 'proofs', 'fixture', 'lib', 'tsv'):
        ap.add_argument('--' + k, required=True)
    ap.add_argument('--left')
    a = ap.parse_args()
    from assetpipe.rooms import GcIso
    cat = {e['sha256']: e for e in json.load(open(a.catalog))['entries']}
    prov = {e['sha256']: e for e in json.load(open(a.proofs))['entries']}
    fix = json.load(open(a.fixture))['replace']
    want = {}
    for h, e in cat.items():
        src = e.get('source', '')
        if e['kind'] == 'model' and src.startswith('st1/') and '.dar' in src and prov.get(h, {}).get('provenance') != 'ps2':
            want.setdefault(src.split('#')[0], set()).add(h)
    g = GcIso(po.GC_ISO)
    afs = pb.afs_index(po.PS2_ISO)
    lib = {}
    for j in [x for c in ('items', 'breakables') for x in Path(a.lib, c).rglob('*.json')]:
        try:
            d = json.loads(j.read_text())
        except Exception:
            continue
        if 'bin' in d and d.get('ps2_bin_sha256'):
            b = (j.parent / d['bin']).read_bytes()
            for v in (b, b.rstrip(b'\0')):
                lib[sha(v)] = (d, j)
    rows, left = [], []
    for f, hs in sorted(want.items()):
        room = f[4:8]
        dar = Path(fix[f]).read_bytes()
        _, size, _, off = struct.unpack_from('<4I', dar, 0x20)
        pay = dar[off:off + size]
        ents = rs.tagged_entries(pay, '<')
        gd = g.read(next(k for rr, k in g.rooms() if rr == room))
        if gd[:32] == rs.CONTAINER_MAGIC:
            gd = rs.decode_das(gd)
        ge = rs.tagged_entries(gd, '>')
        pe = {i + 4: (t, b) for i, t, b in pb.dat_entries(pb.afs_read(po.PS2_ISO, room + '.dat', afs))}
        pets = next((b for t, b in pe.values() if t == 'ETM'), None)
        pent = {n: pets[x + 0x40:z] for n, x, z in po.etm_entries(pets, '<')} if pets else {}
        # candidate (member name, current bytes, GC BE bytes, PS2 bytes) per model member
        cands = []
        for i, (t, s, e) in enumerate(ge):
            tt = t.rstrip(b'\0')
            if tt == b'BIN':
                p = pe.get(i + 4)
                pbin = p[1] if p and p[0] == 'BIN' else None
                cands.append(('%#04x BIN' % (i + 4), pay[ents[i][1]:ents[i][2]], gd[s:e], pbin, '%s.dat:%#04x' % (room, i + 4)))
                # other PS2 BINs (renumbered objects) are tried too
                for j, (pt, pbb) in pe.items():
                    if pt == 'BIN' and j != i + 4:
                        cands.append(('%#04x BIN' % (i + 4), pay[ents[i][1]:ents[i][2]], gd[s:e], pbb, '%s.dat:%#04x' % (room, j)))
            if tt == b'ETM':
                lb = pay[ents[i][1]:ents[i][2]]
                lents = {n: lb[x + 0x40:z] for n, x, z in po.etm_entries(lb, '<')}
                gb = gd[s:e]
                for n, x, z in po.etm_entries(gb, '>'):
                    if n.lower().endswith('.bin') and n in pent:
                        cands.append(('ETM/' + n, lents[n], gb[x + 0x40:z], pent[n], '%s.dat:ETM/%s' % (room, n)))
        payloads = {sha(pl): pl for pl in bc.model_payloads(pay)}
        for h in sorted(hs):
            done = None
            pl = payloads.get(h)
            if pl is not None and h not in lib:
                h2 = sha(pl.rstrip(b'\0'))   # a slot is the lib model zero padded to the GC model's size
                if h2 in lib:
                    lib[h] = lib[h2]
            if h in lib:
                d, j = lib[h]
                done = (d['ps2_bin_sha256'], '%s.dat %s (ps2lib %s)' % (room, d['name'], j.name),
                        'equal to ps2lib %s/%s (ps2_items.py built from the PS2 BIN)' % (j.parent.parent.name + '/' + j.parent.name, d['bin']))
            for name, cur, gbin, pbin, where in cands:
                if done or pbin is None:
                    continue
                if h not in (sha(cur), sha(cur.rstrip(b'\0'))):
                    continue
                po.LOD = False
                for fold in (False, True):
                    po.UV_FOLD = fold
                    try:
                        new = po.to_le(po.rebuild(gbin, pbin, tex_map=po.TEX_MAPS.get(name[4:].lower()))[0], name)
                    except Exception:
                        continue
                    finally:
                        po.UV_FOLD = False
                    if new.rstrip(b'\0') == cur.rstrip(b'\0'):
                        done = (sha(pbin), 'PS2 USA BIO4DAT.AFS ' + where,
                                'ps2_objects.rebuild (converter v%d) of GC %s %s with this PS2 BIN reproduces it byte for byte'
                                % (3 if fold else 2, room, name))
                        break
                po.LOD = True
                if done:
                    break
            if done:
                rows.append(('model', h[:40], h, done[0], done[1], done[2] + ' (prove_props.py, lane props-ps2-26)'))
            else:
                # name the member for review
                at = next((pay.find(pl) for pl in bc.model_payloads(pay) if sha(pl) == h), -1)
                ent = next(('%#04x %s' % (i + 4, t.rstrip(b'\0').decode()) for i, (t, s, e) in enumerate(ents) if s <= at < e), '?')
                left.append((f, ent, h))
    with open(a.tsv, 'w') as o:
        for r in rows:
            o.write('\t'.join(r) + '\n')
    if a.left:
        with open(a.left, 'w') as o:
            for r in left:
                o.write('\t'.join(r) + '\n')
    print('prove_props: %d proven PS2, %d left' % (len(rows), len(left)))


if __name__ == '__main__':
    main()
