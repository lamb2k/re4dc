#!/usr/bin/env python3
"""ps2leon neck (lane garr18, 2026-10-19; LEON_HEADLESS): the PS2 neck model Leon shows after his head comes off.

  build_neck.py <out dir>

Source: cPlLeon::setHead(0) (pl_leon.cpp; called by em10PlHeadLost (chainsaw / claw), emWepPlHeadLost (thrown scythe),
obj16PlHeadLost (parasite head) and em25 / em2c / em2d / em31 / em32 kills, overseas regions only) deletes the head
shape, hair and eye infos (pl00 arcs 8 / 6 / 9, roles 3 / 4 / 7) and adds pl00 arc 0xB with TPL 7, the neck stump.
The PS2 disc has the same file and arc (pl00.dat arc 0xB: 37 triangles, diffuse 2 = the atlas tile of role 3).

Packed exactly as build_hands.py packs a hand pose: arm A's mesh.json with role 3 replaced by the PS2 section (arm A's
rules: PS2 positions, normals and weights, PS2 UVs / 256 into the atlas tile of the PS2 texture), pack_arm.py's
pipeline (pack_coarse_actor, build_blob, verify_blob, patch_header); role 3's arrays and chunk row are taken from that
header. Output ps2leon_neck.h (namespace leon_neck: arrays, one Chunk row, spans) and report-neck.json.
"""
import copy, hashlib, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import leon_sources as ls  # noqa: E402
import build_hands as bh  # noqa: E402

ROLE, FILE, ARC = 3, 'pl00', 0xB


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    base = json.loads((ls.WORK / 'arms/a/mesh.json').read_text())
    mesh = copy.deepcopy(base)
    mesh['triangles'] = [t for t in mesh['triangles'] if t['source_info'] != ROLE]
    tris = bh.pose_triangles(ROLE, FILE, ARC, mesh['positions_mm'], mesh['weights'])
    mesh['triangles'] += tris
    mesh['source_info_counts'] = {str(k): sum(t['source_info'] == k for t in mesh['triangles']) for k in range(8)}
    arrays, wt, row = bh.pack_role(mesh, ROLE, out / 'work')
    pc, nc, pal, tri, sb = row
    lines = ['// Private generated asset (ps2leon build_neck.py). Do not commit.',
             '// LEON_HEADLESS: the PS2 neck (pl00 arc 0xB, TPL 7) Leon shows after setHead(0) (namespace leon_neck).',
             'namespace leon_neck {', 'using leon4k::Chunk; using leon4k::Weight;']
    for a in ('pos', 'nrm', 'uv', 'gx'):
        lines.append('alignas(32) static const unsigned char n_%s[] = {%s};' % (a, arrays[a]))
    lines.append('static const Weight n_weights[] = {%s};' % wt)
    lines.append('static Chunk chunk = {%d,%d,%d,%d,%d,%d,n_pos,n_nrm,n_uv,n_gx,n_weights};' % (ROLE, pc, nc, pal, tri, sb))
    lines.append('#define RE4DC_LEON_NECK_INPUT {RE4DC_OWNER_SPAN(leon_neck::n_pos),RE4DC_OWNER_SPAN(leon_neck::n_nrm),'
                 'RE4DC_OWNER_SPAN(leon_neck::n_uv),RE4DC_OWNER_SPAN(leon_neck::n_gx),RE4DC_OWNER_SPAN(leon_neck::n_weights)}')
    lines.append('}')
    text = '\n'.join(lines) + '\n'
    (out / 'ps2leon_neck.h').write_text(text)
    nbytes = sum(len(arrays[a].split(',')) for a in ('pos', 'nrm', 'uv', 'gx'))
    rep = dict(source='%s arc %#x (PS2 USA disc)' % (FILE, ARC), role=ROLE, triangles=tri, positions=pc, normals=nc,
               palettes=pal, stream_bytes=sb, array_bytes=nbytes, header_sha256=hashlib.sha256(text.encode()).hexdigest())
    (out / 'report-neck.json').write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep))


if __name__ == '__main__':
    main()
