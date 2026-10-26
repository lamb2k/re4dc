#!/usr/bin/env python3
"""store26.py <gen26 out dir> <store dir>: the props26 data store (lane props-ps2-26 2026-10-26).

Copies each room's member-source .dar, writes graft.json ({dest: [members]}, read by t11-fix.py DATA['props26']),
provenance.tsv (one row per grafted member body, with and without its zero tail: output_sha256 -> the PS2 BIN it was
converted from, so GC-ASSET attributes the grafted members to PS2), RECIPE.txt and SHA256SUMS.txt.
"""
import hashlib
import json
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1]), str(HERE.parent)]
import ps2_objects as po  # noqa: E402
import ps2_bin as pb  # noqa: E402
import room_smd as rs  # noqa: E402

sha = lambda b: hashlib.sha256(b).hexdigest()


def members(dar, names):
    """-> {name: body} (ETM sub-file bodies past the 0x40 record header; whole entries for '0x.. TAG')"""
    k, size, d, off = struct.unpack_from('<4I', dar, 0x20)
    pay = dar[off:off + size]
    ents = rs.tagged_entries(pay, '<')
    out = {}
    for i, (t, a, z) in enumerate(ents):
        nm = '%#04x %s' % (i + 4, t.rstrip(b'\0').decode('latin1'))
        if nm in names:
            out[nm] = pay[a:z]
        if t.rstrip(b'\0') == b'ETM':
            e = pay[a:z]
            for n, s, x in po.etm_entries(e, '<'):
                if n in names:
                    out[n] = e[s + 0x40:x]
    return out


def main():
    gen, store = Path(sys.argv[1]), Path(sys.argv[2])
    (store / 'st1').mkdir(parents=True, exist_ok=True)
    afs = pb.afs_index(po.PS2_ISO)
    graft, prov, lines = {}, [], []
    for gj in sorted((gen / 'reports').glob('*.graft.json')):
        g = json.loads(gj.read_text())
        room = gj.name.split('.')[0]
        rep = json.loads((gen / 'reports' / (room + '.json')).read_text())
        if not g['members']:
            continue
        dst = store / 'st1' / (room + '.dar')
        shutil.copyfile(g['source'], dst)
        graft[g['dest']] = g['members']
        body = members(dst.read_bytes(), set(g['members']))
        pe = {i + 4: (t, b) for i, t, b in pb.dat_entries(pb.afs_read(po.PS2_ISO, room + '.dat', afs))}
        pets = next((b for t, b in pe.values() if t == 'ETM'), b'')
        pent = {n: pets[a + 0x40:z] for n, a, z in po.etm_entries(pets, '<')} if pets else {}
        for o in rep['objects']:
            if o.get('skipped'):
                continue
            nm = o.get('name') or ('%#04x BIN' % int(o['gc_arc'], 16))
            src = pent.get(nm) if 'name' in o else pe[int(o['ps2_arc'], 16)][1]
            where = ('%s.dat:ETM/%s' % (room, nm)) if 'name' in o else ('%s.dat:%s' % (room, o['ps2_arc']))
            b = body[nm]
            for v in {b, b.rstrip(b'\0')}:
                prov.append((room, nm, sha(v), sha(src), where))
            lines.append('%s %s tris GC %s -> PS2 %s (raw %s) lod %s' % (room, nm, o['gc_tris'], o['out_tris'],
                         o['ps2_tris'], json.dumps(o.get('lod'))))
    (store / 'graft.json').write_text(json.dumps(graft, indent=1, sort_keys=True) + '\n')
    with open(store / 'provenance.tsv', 'w') as f:
        f.write('room\tmember\toutput_sha256\tps2_sha256\tps2_source\n')
        for r in prov:
            f.write('\t'.join(r) + '\n')
    (store / 'RECIPE.txt').write_text(
        'props26 data set (lane props-ps2-26, 2026-10-26): PS2 room objects (etc models / room BINs) that earlier sets\n'
        'shipped LARGER than the GameCube model (--keep-larger) reconverted from the PS2 BIN of the same object\n'
        '(PS2 USA BIO4DAT.AFS rNNN.dat) with tools/ps2_objects.py v4: mesh_lod reduction with the UV guard 0.02 inside\n'
        'the convert step, GX strips, --uv-fold, self-check (no more triangles and no more bytes than the GC model).\n'
        'Delivered as a GRAFT (graft.json): only these members are copied onto the composed archives; pictures unchanged\n'
        '(the objects keep the PS2 pictures earlier sets packaged).\n'
        'Command: tools/d367/props26/gen26.sh <t11-fix fixture json> <gen dir>; tools/d367/props26/store26.py <gen> <store>\n'
        'Members:\n' + ''.join('  %s\n' % l for l in lines))
    sums = []
    for p in sorted(store.rglob('*')):
        if p.is_file() and p.name != 'SHA256SUMS.txt':
            sums.append('%s  %s' % (sha(p.read_bytes()), p.relative_to(store)))
    (store / 'SHA256SUMS.txt').write_text('\n'.join(sums) + '\n')
    print('props26 store', store, len(graft), 'archives', sum(len(v) for v in graft.values()), 'members')


if __name__ == '__main__':
    main()
