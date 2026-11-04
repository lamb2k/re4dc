#!/usr/bin/env python3
"""ps2leon wound (lane bosscast-wound, 2026-11-03; LEON_WOUND): the PS2 wound overlay Leon wears from the r317 Krauser knife
fight on (chapter 5).

  build_wound.py <out dir>        (Windows Python: numpy, Pillow; leon_sources.py's paths)

Source: cPlLeon::setWound() (pl_leon.cpp; r317.cpp after the knife fight, and cPlLeon::setModel whenever
pG->Scenario_flg[0] & 0x20) adds player arc 0xE with TPL 0xF as a tenth model info. The PS2 disc has the same file and
arc (pl08.dat / pl00.dat arc 0xE: 5 triangles, one bone (4), material flag 4: colour TPL image 0 + mask image 1, 32 x 16).

Geometry: packed as build_neck.py packs the neck (arm A's mesh.json with role 3 replaced by the PS2 section, PS2
positions, normals and weights, pack_role = pack_coarse_actor / build_blob / verify_blob / patch_header), except that
the UVs stay in the wound picture's own space (PS2 raw UV / 256, each triangle shifted by whole pictures so every corner
is >= 0: the sampler repeats), as the flying head's hair run (build_head.py): the runtime draws the whole chunk as one
run on material 1, the wound pair.
Picture: the PS2 TPL 0xF colour (image 0) with the mask's intensity (image 1, red) as alpha, one material-pair package
(ps2_items_tex.build: graded alpha -> twiddled ARGB4444) under the pair key the runtime asks for
(R4MPv001 over the GameCube colour / mask keys of TPL 0xF = 8f359de1-44158660; island18 saw it missing). The PS2
pictures match the GameCube orientation (mean abs difference: colour 2.2, mask 3.9 of 255).

Outputs: ps2leon_wound.h (namespace leon_wound: arrays, one Chunk row, the input spans; private, not committed),
dc/tex/8/8f359de1-44158660.re4tex, manifest.tsv (the disc paths, D3_DATA set), report-wound.json, wound-pair.png.
"""
import copy, hashlib, importlib.util, json, struct, sys, zlib
from pathlib import Path
import numpy as np
from PIL import Image
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1])]
import leon_sources as ls  # noqa: E402
import build_hands as bh  # noqa: E402
import ps2_bin as pb  # noqa: E402

ROLE, FILE, ARC, TPL = 3, 'pl08', 0xE, 0xF
GC_COLOUR, GC_MASK = (2728875949, 3850146139), (871626886, 146191603)   # gen_wound_records.py t_pl08_15
WA = ls.PRIV / 'world-agent-20260926'


def lm(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def pair_key():
    b = b'R4MPv001' + struct.pack('<4I', *GC_COLOUR, *GC_MASK)
    h = 2166136261
    for c in b:
        h = ((h ^ c) * 16777619) & 0xffffffff
    return '%08x-%08x' % (zlib.crc32(b) & 0xffffffff, h)


def wound_triangles(positions, weights):
    m, tris = bh.ps2_section(FILE, ARC)
    assert len(m.materials) == 1 and m.materials[0]['flag'] == 4 and m.materials[0]['diffuse'] == 0 and m.materials[0]['opacity'] == 1, m.materials
    vid, out = {}, []
    for node, cs in tris:
        P = np.asarray([c['p'] for c in cs], float)
        if np.linalg.norm(np.cross(P[1] - P[0], P[2] - P[0])) < 1e-6:
            continue
        st = [(c['raw']['uv'][0] / 256.0, c['raw']['uv'][1] / 256.0) for c in cs]
        du = -min(0, int(min(s[0] for s in st) // 1)); dv = -min(0, int(min(s[1] for s in st) // 1))
        tc = []
        for c, s in zip(cs, st):
            pk = tuple(np.round(c['p'], 4))
            w = tuple(sorted(((int(b), float(x)) for b, x in c['w']), key=lambda bw: -bw[1])[:3])
            sw = sum(x for _, x in w)
            assert w and sw > 0 and all(b < 119 for b, _ in w)
            w = tuple(sorted((b, x / sw) for b, x in w))
            vk = (pk, w)
            if vk not in vid:
                vid[vk] = len(positions)
                positions.append([float(x) for x in c['p']])
                weights.append([[b, x] for b, x in w])
            uv = [s[0] + du, s[1] + dv]
            assert all(0 <= x * 32768 <= 65535 for x in uv), uv
            tc.append(dict(vertex=vid[vk], normal=[float(x) for x in c['n']], uv=uv))
        out.append(dict(source_info=ROLE, corners=tc))
    return out


def picture(out):
    ents = {i + 4: (t, b) for i, t, b in pb.dat_entries(ls._cached('ps2-%s.dat' % FILE, lambda: pb.afs_read(ls.PS2_ISO, '%s.dat' % FILE)))}
    tag, tpl = ents[TPL]
    assert tag == 'TPL'
    dec = lm('ps2_tpl_decode', WA / 'from-main/ps2-trees/tools/ps2_tpl_decode.py')
    p = dec.parse_tpl(tpl)
    im = []
    for h in p['entries'][:2]:
        w, hh, px, _ = dec.decode(tpl, h)
        assert (w, hh) == (32, 16) and h['interlace'] == 0, (w, hh, h['interlace'])
        im.append(np.frombuffer(bytes(px), np.uint8).reshape(hh, w, 4))
    work = out / 'work'; work.mkdir(parents=True, exist_ok=True)
    Image.fromarray(im[0]).save(work / 'colour.png'); Image.fromarray(im[1]).save(work / 'mask.png')
    it = lm('ps2_items_tex', HERE.parents[1] / 'ps2_items_tex.py')
    wd, h, fmt, ptype, payload, mode, vq = it.build(work / 'colour.png', False, work / 'mask.png')
    key = pair_key()
    data, _ = it.w.re4dctx_bytes('PS2 leon wound %s' % key, wd, h, fmt, ptype, payload)
    rel = 'dc/tex/%s/%s.re4tex' % (key[0], key)
    (out / rel).parent.mkdir(parents=True, exist_ok=True); (out / rel).write_bytes(data)
    pair = im[0].copy(); pair[..., 3] = im[1][..., 0]
    Image.fromarray(pair).resize((256, 128), Image.NEAREST).save(out / 'wound-pair.png')
    return rel, dict(key=key, width=wd, height=h, format=fmt, alpha=mode, vq=bool(vq), vram_bytes=len(payload), bytes=len(data),
                     sha256=hashlib.sha256(data).hexdigest(), ps2_tpl_sha256=hashlib.sha256(tpl).hexdigest())


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    base = json.loads((ls.WORK / 'arms/a/mesh.json').read_text())
    mesh = copy.deepcopy(base)
    mesh['triangles'] = [t for t in mesh['triangles'] if t['source_info'] != ROLE]
    tris = wound_triangles(mesh['positions_mm'], mesh['weights'])
    mesh['triangles'] += tris
    mesh['source_info_counts'] = {str(k): sum(t['source_info'] == k for t in mesh['triangles']) for k in range(8)}
    arrays, wt, row = bh.pack_role(mesh, ROLE, out / 'work')
    pc, nc, pal, tri, sb = row
    assert tri == len(tris) and pal == 1, row
    uvb = bytes(int(v, 0) for v in arrays['uv'].replace('\n', '').split(',') if v.strip())
    want = {(round(c['uv'][0] * 32768), round(c['uv'][1] * 32768)) for t in tris for c in t['corners']}
    assert set(struct.iter_unpack('<2H', uvb)) == want, 'chunk UVs are not the wound picture UVs'
    lines = ['// Private generated asset (ps2leon build_wound.py). Do not commit.',
             '// LEON_WOUND: the PS2 wound overlay (pl08 arc 0xE, TPL 0xF) Leon wears after setWound() (namespace leon_wound).',
             'namespace leon_wound {', 'using leon4k::Chunk; using leon4k::Weight;']
    for a in ('pos', 'nrm', 'uv', 'gx'):
        lines.append('alignas(32) static const unsigned char w_%s[] = {%s};' % (a, arrays[a]))
    lines.append('static const Weight w_weights[] = {%s};' % wt)
    lines.append('static Chunk chunk = {%d,%d,%d,%d,%d,%d,w_pos,w_nrm,w_uv,w_gx,w_weights};' % (ROLE, pc, nc, pal, tri, sb))
    lines.append('}')
    text = '\n'.join(lines) + '\n'
    (out / 'ps2leon_wound.h').write_text(text)
    rel, tex = picture(out)
    (out / 'manifest.tsv').write_text(rel + '\n')
    rep = dict(source='%s arc %#x / TPL %#x (PS2 USA disc)' % (FILE, ARC, TPL), role=ROLE, triangles=tri, positions=pc,
               normals=nc, palettes=pal, stream_bytes=sb, uv_words=len(uvb) // 4,
               header_sha256=hashlib.sha256(text.encode()).hexdigest(), picture=dict(path=rel, **tex))
    (out / 'report-wound.json').write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep))


if __name__ == '__main__':
    main()
