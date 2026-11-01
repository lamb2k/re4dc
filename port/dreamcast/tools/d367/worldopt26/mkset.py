#!/usr/bin/env python3
# mkset.py <out store dir> <release fixture json (t11-fix.py output: its 'replace' map)>: data set wsg26
# (lane worldopt26 2026-10-26). The inputs are the files the release recipe stages (n256 sets, mip22b R4PW, icells26).
# For every n256 route room of the current release data line: spatial strip groups (tools/ps2_strip_groups.py default
# mode, 4 groups: kd split of opaque/punch strips, corners renumbered by first use in group order) on the shipped
# 256-vertex package. Mesh size unchanged, mesh crc new. The R4SG policy word is the shipped R4SG's (the certified policy
# source crc), or the room's certificate source crc (r103: no shipped R4SG). r100's PCL2 interior cell gets the new mesh
# crc in its header (word 2); nothing else in it depends on corner order.
import hashlib, json, os, re, struct, subprocess, sys, zlib
OUT, FIX = sys.argv[1], sys.argv[2]
T = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))
rep = json.load(open(FIX))['replace']
I = {}
for k, v in rep.items():
    m = re.match(r'dc/native/(r1[0-9a-f]{2})/ps2-world\.re4mesh$', k)
    if m and '/n256' in v:
        r = m.group(1); g = lambda f: rep.get('dc/native/%s/%s' % (r, f))
        I[r] = dict(mesh=v, sg=g('ps2-world.r4sg'), r4pw=g('ps2-world.r4pw'), cell=g('interior.cell'))
INC = T + '/d367/texture_rect21/provenance_certificates_n256.inc'
rows = {}
for line in open(INC):
    m = re.match(r'\{0x([0-9a-f]+)U,(.*)\},', line.strip())
    if m:
        v = [int(x.rstrip('U'), 0) for x in m.group(2).split(',')]
        rows[int(m.group(1), 16)] = v  # world_bytes,placements,parts,meshes,phys_crc,fnv,mesh_crc,mesh_bytes,source_crc
report = {}
for room in sorted(I):
    inp = I[room]
    d = '%s/dc/native/%s' % (OUT, room); os.makedirs(d, exist_ok=True)
    om, og = d + '/ps2-world.re4mesh', d + '/ps2-world.r4sg'
    rj = '%s/reports/%s-sg.json' % (OUT, room); os.makedirs(os.path.dirname(rj), exist_ok=True)
    subprocess.run([sys.executable, T + '/ps2_strip_groups.py', inp['mesh'], inp['r4pw'], om, og, '--groups', '4',
                    '--report', rj], check=True, capture_output=True, cwd=T)
    src = open(inp['mesh'], 'rb').read(); new = open(om, 'rb').read()
    crc_in = struct.unpack_from('<I', src, 12)[0]; crc = struct.unpack_from('<I', new, 12)[0]
    assert len(new) == len(src) and crc == zlib.crc32(new[80:]) & 0xffffffff
    if crc == crc_in:                       # already spatial (r101): ship nothing for this room
        os.remove(om); os.remove(og); os.rmdir(d); report[room] = dict(unchanged=True); continue
    row = rows.get(int(room[1:], 16))
    if inp['sg']:
        pol = struct.unpack_from('<I', open(inp['sg'], 'rb').read(32), 24)[0]
    else:
        assert row and row[6] == crc_in, room
        pol = row[8]
    b = bytearray(open(og, 'rb').read()); struct.pack_into('<I', b, 24, pol); open(og, 'wb').write(b)
    certified = bool(row and row[6] == crc_in and row[7] == len(src))
    report[room] = dict(mesh_crc_in='%08x' % crc_in, mesh_crc='%08x' % crc, mesh_bytes=len(new), policy='%08x' % pol,
                        certified=certified, r4sg_bytes=len(b),
                        r4sg_bytes_in=os.path.getsize(inp['sg']) if inp['sg'] else 0,
                        mesh_in=inp['mesh'], r4pw=inp['r4pw'], r4sg_in=inp['sg'])
    if inp.get('cell'):
        c = bytearray(open(inp['cell'], 'rb').read())
        assert c[:4] == b'PCL2' and struct.unpack_from('<I', c, 8)[0] == crc_in
        struct.pack_into('<I', c, 8, crc); open(d + '/interior.cell', 'wb').write(c)
        report[room]['cell_in'] = inp['cell']
json.dump(report, open(OUT + '/report.json', 'w'), indent=1, sort_keys=True)
# certificate rows for the generated include (same rows as the n256 table; only mesh_crc differs)
with open(OUT + '/cert-rows.txt', 'w') as f:
    for room, r in sorted(report.items()):
        if r.get('certified'):
            f.write('%s %s %s\n' % (room, r['mesh_crc_in'], r['mesh_crc']))
print(json.dumps({k: (v.get('mesh_crc') or 'unchanged') for k, v in report.items()}))
