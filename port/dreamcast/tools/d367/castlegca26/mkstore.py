#!/usr/bin/env python3
"""mkstore.py STORE ROOM CASTLE_DAR FINAL_DAR   (WSL; lane castle-gca-26, 2026-11-01)
Adds one castle room to data set cgca26's store (Disc 2 only, recipe.conf D2_DATA): the room archive ps2_objects.py +
ps2_objects_tex.py made from the castle content's st2/ROOM.dar becomes STORE/st2/ROOM.dar, and every member whose bytes
changed (rr/member_census.dar_members: ETM sub-files and whole tagged entries) is listed in STORE/graft.json, so the set
owns those members only (castle31/castle_fixture.py grafts them; gc_port23/provenance.py credits grafted members by
STORE/provenance.tsv). provenance.tsv: one row per changed model member (etNNNN.bin / room BIN), output sha256 of the
member body (with and without its zero tail, as provenance.graft_digests hashes it) and the sha256 of the PS2 source
member (BIO4DAT.AFS ROOM.dat ETM sub-file / tagged entry of the same index)."""
import hashlib, json, os, shutil, struct, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent.parent), str(HERE.parent / 'rr')]
import ps2_objects as po  # noqa: E402
import room_smd as rs  # noqa: E402
from member_census import dar_members  # noqa: E402

store, room, cdar, fdar = sys.argv[1:5]
sha = lambda b: hashlib.sha256(b).hexdigest()
S = Path(store); (S / 'st2').mkdir(parents=True, exist_ok=True)
a, b = Path(cdar).read_bytes(), Path(fdar).read_bytes()
ma, mb = dar_members(a), dar_members(b)
assert set(ma) == set(mb), 'member sets differ'
# the native tables (NTR / ESQ / MTC) are rebased by dar_graft itself when the ETM entry changes size: never grafted
changed = sorted(k for k in ma if ma[k] != mb[k] and k.split(' ')[-1] not in ('NTR', 'ESQ', 'MTC'))
members = [k[4:] if k.startswith('ETM/') else k for k in changed]
shutil.copyfile(fdar, S / 'st2' / ('%s.dar' % room))
gj = S / 'graft.json'
g = json.loads(gj.read_text()) if gj.exists() else {}
g['st2/%s.dar' % room] = members
gj.write_text(json.dumps(g, indent=1) + '\n')

_k, size, _d, off = struct.unpack_from('<4I', b, 0x20)
pay = b[off:off + size]
ents = rs.tagged_entries(pay, '<')
etm = next(pay[s:e] for t, s, e in ents if t.rstrip(b'\0') == b'ETM')
bodies = {n: etm[s + 0x40:e] for n, s, e in po.etm_entries(etm, '<')}
pe = {i + 4: (t, x) for i, t, x in po.pb.dat_entries(po.pb.afs_read(po.PS2_ISO, room + '.dat', po.pb.afs_index(po.PS2_ISO)))}
pbm = next(x for t, x in pe.values() if t == 'ETM')
pents = {n: pbm[s + 0x40:e] for n, s, e in po.etm_entries(pbm, '<')}
rows = []
for m in members:
    if m.startswith('0x'):
        i = int(m.split()[0], 16)
        if not m.endswith('BIN'):
            continue
        t, s, e = ents[i - 4]
        body, ps2, src = pay[s:e], pe[i][1], '%s.dat:%#04x %s' % (room, i, pe[i][0])
    else:
        if not m.endswith('.bin'):
            continue
        body, ps2, src = bodies[m], pents.get(m), '%s.dat:ETM/%s' % (room, m)
        if ps2 is None:
            continue
    for h in {sha(body), sha(body.rstrip(b'\0'))}:
        rows.append((room, m, h, sha(ps2), src))
pt = S / 'provenance.tsv'
old = [l for l in pt.read_text().splitlines()[1:] if not l.startswith(room + '\t')] if pt.exists() else []
with open(pt, 'w') as f:
    f.write('room\tmember\toutput_sha256\tps2_sha256\tps2_source\n')
    for l in old:
        f.write(l + '\n')
    for r in rows:
        f.write('\t'.join(r) + '\n')
print('mkstore %s: %d changed members (%d model rows): %s' % (room, len(members), len(rows) // 2 or len(rows), ' '.join(members)))
