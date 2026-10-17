#!/usr/bin/env python3
"""Bounded r101 experiment: batch immutable opaque parts in the existing R4IM/R4PW formats.

No runtime change. Explicit fixture opt-in only; never overwrite source assets. Keep every dynamic
placement and object id, reusing emptied fixed rows for batches; other empty rows use the pass mask. Sky rows 0..2,
all ids below 250, every placement in the required live-object manifest, nonuniform transforms, mixed static/dynamic meshes and non-opaque passes remain
source-identical. New room-space meshes group whole parts by X/Z cell and material, retaining each
source cluster, every LOD, strips, winding, colours and the existing strip-group culling path.
Positions/UVs are requantized, so this is a visual candidate, not a bit-identical rendering claim.
"""
import argparse
import collections
import copy
import hashlib
import json
import math
import struct
import subprocess
import sys
import zlib
from pathlib import Path
import ps2_world_far_lod as F


def side_read(path, mesh):
    b = Path(path).read_bytes()
    h = struct.unpack_from('<4s7I', b)
    assert h[:2] == (b'R4PW', 1) and h[3:5] == (len(mesh['parts']), len(mesh['meshes']))
    assert len(b) == 32 + h[3]*16 + h[2]*52 and zlib.crc32(b[32:]) == h[5]
    meta = [struct.unpack_from('<IIHH4B', b, 32+16*i) for i in range(h[3])]
    places = [struct.unpack_from('<HH12f', b, 32+16*h[3]+52*i) for i in range(h[2])]
    return h, meta, places


def aff_of(p):
    return [p[2:6], p[6:10], p[10:14]]


def uniform_scale(p):
    a = aff_of(p)
    ns = [math.sqrt(sum(x*x for x in row[:3])) for row in a]
    if min(ns) <= 0 or max(ns)-min(ns) > max(ns)*1e-5:
        return None
    if any(abs(sum(a[r][k]*a[t][k] for k in range(3))) > max(ns)**2*1e-5
           for r in range(3) for t in range(r)):
        return None
    return sum(ns)/3


def transform(mesh, p, v):
    xyz = [mesh[8+k]+mesh[11+k]*v[k] for k in range(3)]
    return tuple(sum(p[2+4*r+k]*xyz[k] for k in range(3))+p[5+4*r] for r in range(3))


def convert(src, meta, places, ids, cell, gated):
    out = {k: [] for k in src}
    out['strip'] = bytearray()
    out['pal'] = list(src['pal'])
    outmeta = []
    uses = collections.defaultdict(list)
    for i, p in enumerate(places):
        uses[p[0]].append(i)
    eligible = {mi for mi, rows in uses.items() if all(places[i][1] > 2 and places[i][1] not in gated and
                ids[places[i][1]] >= 250 and uniform_scale(places[i]) is not None for i in rows)}
    groups = collections.defaultdict(lambda: collections.defaultdict(list))
    removed = set()
    for mi in sorted(eligible):
        m = src['meshes'][mi]
        for pi in range(m[6], m[6]+m[7]):
            if meta[pi][4] != 0:
                continue
            removed.add(pi)
            fc, nc = src['plods'][pi]
            assert nc
            cs = src['clusters'][fc:fc+nc]
            for pli in uses[mi]:
                p = places[pli]
                lo = [min(c[k] for c in cs) for k in range(3)]
                hi = [max(c[3+k] for c in cs) for k in range(3)]
                lo, hi = F.world_box(m, aff_of(p), lo, hi)
                key = tuple(math.floor((lo[k]+hi[k])*.5/cell) for k in (0, 2))
                # Include every material flag; UV grids are unified below.
                material = meta[pi] + tuple(src['parts'][pi][2:6])
                groups[key][material].append((pli, pi))

    def copy_part(pi):
        p = src['parts'][pi]
        first = len(out['lets'])
        lo, hi = F.part_pool(src, pi)
        delta = len(out['verts'])-lo
        out['verts'].extend(src['verts'][lo:hi])
        for old in src['lets'][p[6]:p[6]+p[7]]:
            q = list(old)
            if len(out['strip']) & 1:
                out['strip'].append(0)
            q[0] += delta
            q[1] = len(out['strip'])
            size = old[2]+(2*old[3] if old[4]&F.INDEXED else 0)
            out['strip'].extend(src['strip'][old[1]:old[1]+size])
            out['lets'].append(q)
        fc, nc = src['plods'][pi]
        out['plods'].append([len(out['clusters']), nc])
        for c in src['clusters'][fc:fc+nc]:
            out['clusters'].append([*c[:6], len(out['levels']), c[7]])
            for lv in src['levels'][c[6]:c[6]+c[7]]:
                out['levels'].append([first+lv[0]-p[6], lv[1], lv[2]])
        out['parts'].append([*p[:6], first, p[7], *p[8:]])
        outmeta.append(meta[pi])

    # Original mesh indices, source metadata, placement order and dyn ids stay intact.
    kept_map = {}
    for mi, m in enumerate(src['meshes']):
        start = len(out['parts'])
        for pi in range(m[6], m[6]+m[7]):
            if pi not in removed:
                kept_map[pi] = len(out['parts'])
                copy_part(pi)
        out['meshes'].append([*m[:6], start, len(out['parts'])-start, *m[8:]])
    result_places = list(places)
    result_ids = list(ids)
    reuse = [i for i, p in enumerate(places) if p[0] in eligible and out['meshes'][p[0]][7] == 0]
    assert len(reuse) >= len(groups), 'not enough empty static rows for batches'
    lineage = []
    stats = dict(max_position_error_mm=0.0, max_uv_error=0.0, retained_parts=len(kept_map),
                 source_part_instances=0, batch_parts=0, cells=len(groups), strips_verified=0,
                 corners_verified=0, source_clusters=0)
    for cellkey, materials in sorted(groups.items()):
        members = [x for members in materials.values() for x in members]
        boxes = []
        for pli, pi in members:
            p = places[pli]; m = src['meshes'][p[0]]
            fc, nc = src['plods'][pi]
            for c in src['clusters'][fc:fc+nc]:
                boxes.append(F.world_box(m, aff_of(p), c[:3], c[3:6]))
        blo = [min(b[0][k] for b in boxes)-2 for k in range(3)]
        bhi = [max(b[1][k] for b in boxes)+2 for k in range(3)]
        origin = [F.f32(x) for x in blo]
        step = [F.f32(max(1e-5, (bhi[k]-origin[k])/65533)) for k in range(3)]
        bounds_hi = [F.f32(origin[k]+65535*step[k]) for k in range(3)]
        mesh_start = len(out['parts'])
        mi_out = len(out['meshes'])

        def qbox(lo, hi):
            qlo = [max(0, min(65535, math.floor((lo[k]-origin[k])/step[k]))) for k in range(3)]
            qhi = [max(0, min(65535, math.ceil((hi[k]-origin[k])/step[k]))) for k in range(3)]
            return qlo+qhi

        for material, members in sorted(materials.items()):
            first = len(out['lets']); fc_out = len(out['clusters']); pi_out = len(out['parts'])
            uv_values = []
            for pli, pi in members:
                p = src['parts'][pi]; lo, hi = F.part_pool(src, pi)
                uv_values.extend((p[8]+p[10]*v[3], p[9]+p[11]*v[4]) for v in src['verts'][lo:hi])
            uvb = [F.f32(min(v[k] for v in uv_values)) for k in range(2)]
            uvs = [F.f32(max(1e-12, (max(v[k] for v in uv_values)-uvb[k])/65535)) for k in range(2)]
            for pli, pi in members:
                place = places[pli]; mesh = src['meshes'][place[0]]; part = src['parts'][pi]
                scale = uniform_scale(place)
                letmap = {}
                for li in range(part[6], part[6]+part[7]):
                    old = src['lets'][li]; corners, strips = F.let_corners(src, old)
                    firstv = len(out['verts']); start = len(out['strip'])
                    for ci in corners:
                        v = src['verts'][ci]; world = transform(mesh, place, v)
                        q = [max(0, min(65535, round((world[k]-origin[k])/step[k]))) for k in range(3)]
                        uv = [part[8+k]+part[10+k]*v[3+k] for k in range(2)]
                        quv = [max(0, min(65535, round((uv[k]-uvb[k])/uvs[k]))) for k in range(2)]
                        stats['max_position_error_mm'] = max(stats['max_position_error_mm'],
                            math.sqrt(sum((origin[k]+step[k]*q[k]-world[k])**2 for k in range(3))))
                        stats['max_uv_error'] = max(stats['max_uv_error'],
                            *[abs(uvb[k]+uvs[k]*quv[k]-uv[k]) for k in range(2)])
                        out['verts'].append((*q, *quv, v[5]))
                    for strip in strips:
                        out['strip'].append(len(strip)); out['strip'].extend(strip)
                    lo, hi = F.world_box(mesh, aff_of(place), old[5:8], old[8:11])
                    letmap[li] = len(out['lets'])
                    out['lets'].append([firstv, start, len(out['strip'])-start, len(corners), len(strips), *qbox(lo, hi)])
                    lineage.append((pli, pi, li, pi_out, letmap[li], mi_out))
                fc, nc = src['plods'][pi]
                for c in src['clusters'][fc:fc+nc]:
                    lo, hi = F.world_box(mesh, aff_of(place), c[:3], c[3:6])
                    out['clusters'].append([*qbox(lo, hi), len(out['levels']), c[7]])
                    for lv in src['levels'][c[6]:c[6]+c[7]]:
                        start = letmap[lv[0]] if lv[1] else len(out['lets'])
                        assert [letmap[x] for x in range(lv[0], lv[0]+lv[1])] == list(range(start, start+lv[1]))
                        out['levels'].append([start, lv[1], F.f32(lv[2]*scale)])
                stats['source_clusters'] += nc
            out['parts'].append([32*(pi_out-mesh_start), 0, *material[8:12], first, len(out['lets'])-first, *uvb, *uvs])
            out['plods'].append([fc_out, len(out['clusters'])-fc_out])
            outmeta.append(material[:8])
            stats['source_part_instances'] += len(members); stats['batch_parts'] += 1
        count = len(out['parts'])-mesh_start
        out['meshes'].append([60000+mi_out, 0, 0x50, 0, count, 0, mesh_start, count,
                              *origin, *step, *origin, *bounds_hi])
        identity = (1.,0.,0.,0., 0.,1.,0.,0., 0.,0.,1.,0.)
        slot = reuse.pop(0)
        result_places[slot] = (mi_out, places[slot][1], *identity)
    # Retain the original sidecar capacity: unused part rows have no draw or vertex pool.
    # This keeps the world allocation and LUT/gather offsets, ids allocation and dynamic slots unchanged.
    stats['active_parts'] = len(out['parts'])
    assert len(out['parts']) <= len(src['parts'])
    while len(out['parts']) < len(src['parts']):
        out['parts'].append([0,0,0,255,0,0,len(out['lets']),0,0.,0.,1.,1.])
        out['plods'].append([len(out['clusters']),0]); outmeta.append(meta[0])
    # Read-back independently through the common R4IM parser, then compare every original strip.
    out = F.read(F.write(out))
    for oldpi, newpi in kept_map.items():
        a,b = src['parts'][oldpi],out['parts'][newpi]
        assert a[:6] == b[:6] and a[8:] == b[8:] and meta[oldpi] == outmeta[newpi]
        for oldli,newli in zip(range(a[6],a[6]+a[7]),range(b[6],b[6]+b[7])):
            ac, ast = F.let_corners(src,src['lets'][oldli]);bc, bst = F.let_corners(out,out['lets'][newli])
            assert ast == bst and [src['verts'][x] for x in ac] == [out['verts'][x] for x in bc]
    for pli,pi,li,opi,oli,omi in lineage:
        ac,ast = F.let_corners(src,src['lets'][li]);bc,bst = F.let_corners(out,out['lets'][oli])
        assert ast == bst and len(ac)==len(bc)
        om=out['meshes'][omi];op=out['parts'][opi]; sm=src['meshes'][places[pli][0]];sp=src['parts'][pi]
        for a,b in zip(ac,bc):
            av,bv=src['verts'][a],out['verts'][b]
            want=transform(sm,places[pli],av)
            got=[om[8+k]+om[11+k]*bv[k] for k in range(3)]
            assert math.dist(want,got)<=2.0, (want,got)
            assert av[5]==bv[5]
            for k in range(2):
                assert abs(sp[8+k]+sp[10+k]*av[3+k]-op[8+k]-op[10+k]*bv[3+k])<=0.0001
        stats['strips_verified'] += len(ast);stats['corners_verified'] += sum(map(len,ast))
    assert result_ids == list(ids)
    for i, p in enumerate(places):
        if p[1] <= 2 or p[1] in gated or ids[p[1]] < 250 or src['meshes'][p[0]][7] and out['meshes'][p[0]][7]:
            assert result_places[i] == p
    stats['dynamic_identity']='all protected placements, mesh bins and object ids retained; all id<250 geometry exact; batches reuse empty fixed rows'
    stats['retained_strip_attributes']='IDENTICAL'
    return out, outmeta, result_places, result_ids, stats


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mesh');ap.add_argument('sidecar');ap.add_argument('ids');ap.add_argument('out',type=Path)
    ap.add_argument('--cell-mm',type=float,default=16000)
    ap.add_argument('--max-bytes',type=int,required=True)
    ap.add_argument('--source-groups',required=True)
    ap.add_argument('--gated-manifest',required=True,help='ps2_world_append.py append.json: preserve every live-object placement')
    a=ap.parse_args();assert a.cell_mm>0 and not a.out.exists(), 'use a new output directory'
    blob=Path(a.mesh).read_bytes();src=F.read(blob);head,meta,places=side_read(a.sidecar,src)
    idblob=Path(a.ids).read_bytes();ih=struct.unpack_from('<4s3I',idblob)
    assert ih==(b'R4ID',1,len(places),head[5]) and len(idblob)%32==0
    ids=idblob[16:16+len(places)]
    assert all(p[1]<len(ids) for p in places)
    gate=json.loads(Path(a.gated_manifest).read_text())
    assert int(gate['r4pw_crc'],16)==head[5], 'gate manifest must match this source sidecar'
    gated={o['placement'] for o in gate['objects']}
    out,om,op,oi,stats=convert(src,meta,places,ids,a.cell_mm,gated)
    stats['protected_gate_placements']=sorted(gated)
    result=F.write(out); assert len(result)<=a.max_bytes, (len(result),a.max_bytes)
    body=b''.join(struct.pack('<IIHH4B',*m) for m in om)+b''.join(struct.pack('<HH12f',*p) for p in op)
    crc=zlib.crc32(body);side=struct.pack('<4s7I',b'R4PW',1,len(op),len(om),len(out['meshes']),crc,0,0)+body
    assert (len(side)+31)//32 <= (len(Path(a.sidecar).read_bytes())+31)//32, 'sidecar allocation grew'
    ib=struct.pack('<4s3I',b'R4ID',1,len(oi),crc)+bytes(oi);ib+=b'\0'*((-len(ib))%32)
    # Pad only the fallback L0 file to the retained L0 capacity. This keeps WORLD_VERT's world allocation identical.
    # Its topology matches the selected L5, so even a missing L5 cannot pair incompatible mesh/sidecar tables.
    a.out.mkdir(parents=True)
    (a.out/'before-groups.re4mesh').write_bytes(result);(a.out/'ps2-world.r4pw').write_bytes(side)
    (a.out/'ps2-world.ids').write_bytes(ib)
    subprocess.run([sys.executable,str(Path(__file__).with_name('ps2_strip_groups.py')),
        str(a.out/'before-groups.re4mesh'),str(a.out/'ps2-world.r4pw'),str(a.out/'ps2-wv5.re4mesh'),
        str(a.out/'ps2-wv5.r4sg'),'--report',str(a.out/'strip-groups.json')],check=True)
    final=(a.out/'ps2-wv5.re4mesh').read_bytes();padded=bytearray(final+b'\0'*(a.max_bytes-len(final)))
    struct.pack_into('<II',padded,8,len(padded),zlib.crc32(padded[80:]))
    (a.out/'ps2-world.re4mesh').write_bytes(padded)
    # L0 group file reserves exactly the source capacity and fails its CRC check if L5 was unavailable (safe fallback).
    sg=bytearray((a.out/'ps2-wv5.r4sg').read_bytes()); sg_capacity=len(Path(a.source_groups).read_bytes()); assert len(sg)<=sg_capacity
    (a.out/'ps2-world.r4sg').write_bytes(bytes(sg)+b'\0'*(sg_capacity-len(sg)))
    stats.update(cell_mm=a.cell_mm,bytes_in=len(blob),bytes_out=len(final),l0_capacity=a.max_bytes,
        meshes_in=len(src['meshes']),meshes_out=len(out['meshes']),parts_in=len(src['parts']),parts_out=len(out['parts']),
        placements_in=len(places),placements_out=len(op),meshlets_in=len(src['lets']),meshlets_out=len(out['lets']),
        sidecar_in=len(Path(a.sidecar).read_bytes()),sidecar_out=len(side),ids_in=len(idblob),ids_out=len(ib),
        input_sha256=hashlib.sha256(blob).hexdigest(),output_sha256=hashlib.sha256(final).hexdigest())
    (a.out/'report.json').write_text(json.dumps(stats,indent=2)+'\n');print(json.dumps(stats,indent=2))

if __name__=='__main__':main()
