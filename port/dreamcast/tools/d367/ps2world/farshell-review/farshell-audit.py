#!/usr/bin/env python3
"""Read-only source/asset census for the far-shell proposal. No game or bake launches."""
from pathlib import Path
import collections
import hashlib
import json
import struct
import sys
import zlib

TREE = Path('/root/probe/codex-cpu-t15-20261016/tree')
ROOT = Path('/mnt/c/Game Dev/Emulators')
OUT = ROOT / '_codex_cpu_t15_20261016'
PEER = ROOT / 'farshell-20261016'
sys.path.insert(0, str(TREE / 'port/dreamcast/tools'))
import ps2_world_far_lod as F
import ps2_world_spatial_batch as S


def signature(path):
    p = Path(path)
    b = p.read_bytes()
    return dict(path=str(p), bytes=len(b), sha256=hashlib.sha256(b).hexdigest())


def census(room, meshpath, sidepath, idpath, gated):
    b = Path(meshpath).read_bytes()
    p = F.read(b)
    h, meta, places = S.side_read(sidepath, p)
    idblob = Path(idpath).read_bytes()
    ih = struct.unpack_from('<4s3I', idblob)
    assert ih == (b'R4ID', 1, len(places), h[5]) and len(idblob) % 32 == 0
    ids = idblob[16:16+len(places)]
    assert len(ids) == len(places)
    result = dict(room=room, mesh=signature(meshpath), sidecar=signature(sidepath), ids=signature(idpath),
                  meshes=len(p['meshes']), parts=len(p['parts']), meshlets=len(p['lets']),
                  stored_vertices=len(p['verts']), placements=len(places),
                  gated_placements=sorted(gated), dynamic_placements=[], rows=[], summary={})
    result['sidecar_crc32'] = f'{h[5]:08x}'
    idcounts = collections.Counter(ids)
    result['unique_runtime_dynamic_ids'] = sorted(k for k,v in idcounts.items() if k < 250 and v == 1)
    result['raw_id_rule'] = 'Conservative protection of all id<250; only unique ids get runtime dyn slots. This is not a claim that every protected placement moves.'
    counts = collections.defaultdict(collections.Counter)
    used_keys = collections.defaultdict(set)
    for i, pl in enumerate(places):
        m = p['meshes'][pl[0]]
        reason = ('sky' if room == 'r101' and pl[1] <= 2 else
                  'live_gate' if pl[1] in gated else 'dynamic_id' if ids[pl[1]] < 250 else
                  'nonuniform' if S.uniform_scale(pl) is None else 'immutable_candidate')
        if ids[pl[1]] < 250:
            result['dynamic_placements'].append(dict(placement=pl[1], id=ids[pl[1]], mesh_bin=m[0]))
        row = dict(placement=pl[1], mesh_index=pl[0], mesh_bin=m[0], object_id=ids[pl[1]], category=reason,
                   by_pass={})
        for pi in range(m[6], m[6]+m[7]):
            part = p['parts'][pi]
            pas = meta[pi][4]
            verts = tris = strips_n = meshlets = 0
            fc, nc = p['plods'][pi]
            for cl in p['clusters'][fc:fc+nc]:
                lv = p['levels'][cl[6]]
                for li in range(lv[0], lv[0]+lv[1]):
                    corners, strips = F.let_corners(p, p['lets'][li])
                    verts += len(corners)
                    strips_n += len(strips)
                    meshlets += 1
                    for strip in strips:
                        for a,b,c in F.crb.strip_triangles(strip):
                            vs = [p['verts'][corners[k]][:3] for k in (a,b,c)]
                            tris += len(set(vs)) == 3
            cat = reason if pas == 0 else 'protected_alpha_pass'
            count = counts[(cat, pas)]
            count.update(parts=1, triangles=tris, vertex_references=verts, strips=strips_n, meshlets=meshlets)
            used_keys[(cat,pas)].add(tuple(meta[pi][:4]))
            key = str(pas)
            if key not in row['by_pass']:
                row['by_pass'][key] = dict(parts=0, triangles=0, vertex_references=0)
            d = row['by_pass'][key]
            d['parts'] += 1
            d['triangles'] += tris
            d['vertex_references'] += verts
        result['rows'].append(row)
    result['summary'] = [dict(category=k[0], pass_=k[1], **v, texture_keys=len(used_keys[k]))
                         for k,v in sorted(counts.items())]
    return result


def main():
    fixture_path = '/root/probe/codex-cpu-t15-20261016/logs/fix/cxt16base-cross.json'
    fixture = json.loads(Path(fixture_path).read_text())['replace']
    gatepath = ROOT / 're4-assets-private/crowd12-bake-20261015/r101-t13/append.json'
    gate = json.loads(gatepath.read_text())
    gated = {o['placement'] for o in gate['objects']}
    out = dict(note='Asset-only census, full package L0 instances, not camera-visible workload or performance savings.',
               fixture=signature(fixture_path), gate_manifest=signature(gatepath), rooms=[])
    for room in ['r101', 'r103']:
        base = f'dc/native/{room}/'
        mesh = fixture[base + ('ps2-wv5.re4mesh' if room == 'r101' else 'ps2-world.re4mesh')]
        out['rooms'].append(census(room, mesh, fixture[base+'ps2-world.r4pw'],
                                   fixture[base+'ps2-world.ids'], gated if room == 'r101' else set()))
    out['peer_source'] = census('r101', PEER/'src/r101/ps2-world.re4mesh', PEER/'src/r101/ps2-world.r4pw',
                                PEER/'src/r101/ps2-world.ids', gated)
    out['peer_files'] = [signature(PEER / path) for path in ['tools/fs_common.py','tools/fs_eyes.py',
                         'tools/fs_blender.py','tools/fs_pack.py','work/r101/params.json','work/r101/build.json',
                         'work/r101/pack.json','work/r101/far-shell.fsh']]
    out['peer_params'] = json.loads((PEER/'work/r101/params.json').read_text())
    out['peer_build'] = json.loads((PEER/'work/r101/build.json').read_text())
    out['peer_pack'] = json.loads((PEER/'work/r101/pack.json').read_text())
    assert out['rooms'][0]['sidecar_crc32'] == out['peer_source']['sidecar_crc32'] == gate['r4pw_crc'].lower().replace('0x','')
    peer_tree=Path('/root/probe/lanes-20261016/farshell')
    out['peer_runtime_files']=[signature(peer_tree / ('port/dreamcast/game/' + s)) for s in
        ['platform/far_shell.inc','platform/native_static.cpp','platform/native_ps2_world.cpp','game30.mk','dbgwarp_bridge.cpp']]
    flags=Path('/root/probe/lanes/route/out-fs16arW/resolved-knobs.txt')
    wanted=['FAR_SHELL','VIEW_DIST_OPTION','FOG_FAR','FOG_FAR_CAP','PS2_WORLD_DYNAMIC','PS2_WORLD_PARTS',
        'PS2_WORLD_MESH','PS2_WORLD_LEAN','PS2_PLACE_GATE','PS2_AREA_HIDE','PS2_PVS','PS2_STRIP_GROUPS','R101_ALIVE_CAP',
        'PS2_LEON','GANADO_LOD','GANADO_LOD_LEVEL','PACE_MODE','MOVIE_WORLD_ARENA','TA_VERTBUF_KB','TA_DOUBLEBUF','MESH_LOD_PX']
    out['peer_resolved_knobs']=dict(l.split('=',1) for l in flags.read_text().splitlines() if l.split('=',1)[0] in wanted)
    out['peer_resolved_knobs_file']=signature(flags)
    walkpath = Path('/root/probe/lanes-20261015/worldlod-work/walk/r101.json')
    walk = json.loads(walkpath.read_text()); pts = walk.pop('points')
    out['r101_floor_samples'] = dict(**walk, file=signature(walkpath), points=len(pts),
        bounds_mm=[[min(p[k] for p in pts) for k in range(3)], [max(p[k] for p in pts) for k in range(3)]],
        limitation='All upward collision floors, not a proven reachable-player or camera volume; 1m samples are not a continuous proof.')
    walk103path=OUT/'farshell-r103-floor-samples.json'
    walk103=json.loads(walk103path.read_text()); pts103=walk103.pop('points')
    out['r103_floor_samples']=dict(**walk103,file=signature(walk103path),points=len(pts103),
       bounds_mm=[[min(p[k] for p in pts103) for k in range(3)],[max(p[k] for p in pts103) for k in range(3)]],
       limitation=out['r101_floor_samples']['limitation'])
    try:
        import numpy as np
        eyes = np.load(PEER/'work/r101/eyes.npy')
        out['peer_camera_samples'] = dict(count=len(eyes), bounds_mm=[eyes.min(0).tolist(),eyes.max(0).tolist()],
            file=signature(PEER/'work/r101/eyes.npy'), limitation='Enemy route nodes plus 1.6m and explicit extras; not continuous player/camera coverage.')
        w = np.load(PEER/'work/r101/world.npz')
        protected = {r['placement'] for r in out['peer_source']['rows'] if r['category'] != 'immutable_candidate'}
        mask = (w['pass_'] == 0) & np.isin(w['placement'], list(protected))
        out['peer_opaque_input_protected'] = dict(triangles=int(mask.sum()),
             placements=sorted(set(int(x) for x in w['placement'][mask])),
             note='These protected triangles are admitted to the source BVH. No source-placement lineage survives in packed shell, so output overlap is unproven.')
    except ImportError:
        out['numpy_unavailable'] = True
    target = OUT/'farshell-source-census.json'
    target.write_text(json.dumps(out, indent=2)+'\n')
    print(json.dumps(dict(output=str(target), rooms=[{k:r[k] for k in ['room','meshes','parts','meshlets','stored_vertices','placements','summary']} for r in out['rooms']],
       peer_summary=out['peer_source']['summary'], peer_protected=out.get('peer_opaque_input_protected'),
       camera=out.get('peer_camera_samples'), walk=out['r101_floor_samples']),indent=2))


if __name__ == '__main__':
    main()
