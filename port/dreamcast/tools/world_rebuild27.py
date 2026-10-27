#!/usr/bin/env python3
"""Explicit, private r101 structural-floor authoring through the existing R4IM codec.

This first authoring operation selects named source features, without moving a
vertex or flattening an opening. It is intentionally separate from identity mode.
It preserves every uniquely owned scroll mesh at every LOD, and retains source
mesh/part/cluster/placement identities even when a static feature is absent.
No texture or game archive is an output. Nothing stages or enables these data.
"""
import argparse
import collections
import copy
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import zlib

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'd367/world_blender_roundtrip'))
import package as codec

SOURCE_INPUTS = ('ps2-world.re4mesh', 'ps2-world.r4pw', 'ps2-world.ids',
                 'ps2-world.r4tc', 'room.r4rc')
UNCHANGED_COMPANIONS = SOURCE_INPUTS[1:]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fnv(data):
    h = 2166136261
    for b in data:
        h = ((h ^ b) * 16777619) & 0xffffffff
    return h


def require(ok, why):
    if not ok:
        raise ValueError(why)


def load(source):
    require(source.name == 'r101', 'r101 directory required; no other room is supported')
    files = {n: (source/n).read_bytes() for n in SOURCE_INPUTS}
    d = codec.decode(files['ps2-world.re4mesh'], files['ps2-world.r4pw'], True)
    ids = files['ps2-world.ids']
    magic, version, count, policy = struct.unpack_from('<4s3I', ids)
    require((magic, version, count) == (b'R4ID', 1, len(d['placements'])), 'R4ID shape')
    require(len(ids) == (16+count+31)//32*32 and not any(ids[16+count:]), 'R4ID padding')
    require(all(p[1] < count for p in d['placements']), 'placement source fields')
    # Exactly the runtime's dyn slot admission: count the source ID table, not
    # mesh occurrences, and preserve ALL meshes referenced by a unique ID.
    counts = collections.Counter(ids[16:16+count])
    owners = {p[0] for p in d['placements']
              if ids[16+p[1]] < 250 and counts[ids[16+p[1]]] == 1}
    return d, files, owners, policy


def level_triangles(d, level):
    result = []
    for ji in range(level[0], level[0]+level[1]):
        local = codec.local_vertices(d, ji)
        for t in codec.triangles(d, ji):
            result.append(tuple(tuple(d['vertices'][local[k]]) for k in t))
    return result


def canonical(tris):
    return collections.Counter(min(t, t[1:]+t[:1], t[2:]+t[:2]) for t in tris)


def author_planar_boundary(tris, step, world_scale):
    """Rebuild one named ground/roof/facade using its single convex boundary.

    Holes, multiple boundaries, closed solids, strong relief and nonconvex
    outlines are refused. Boundary corners keep their source depth, UV/color
    and silhouette; interior tessellation/lighting detail is an approximation.
    """
    import numpy as np
    edges=collections.Counter()
    corners={}
    for t in tris:
        for v in t:corners.setdefault(v[:3],v)
        for a,b in zip(t,t[1:]+t[:1]):
            if a[:3]!=b[:3]:edges[tuple(sorted((a[:3],b[:3])))]+=1
    adjacent=collections.defaultdict(list)
    for (a,b),count in edges.items():
        if count==1:adjacent[a].append(b);adjacent[b].append(a)
        elif count>2:return tris,None
    if len(adjacent)<3 or any(len(v)!=2 for v in adjacent.values()):return tris,None
    start=min(adjacent);ring=[start];prev=None;cur=start
    while True:
        choices=[v for v in adjacent[cur] if v!=prev]
        nxt=choices[0]
        if nxt==start:break
        if nxt in ring:return tris,None
        ring.append(nxt);prev,cur=cur,nxt
    if len(ring)!=len(adjacent):return tris,None  # a second loop is an opening
    xyz=np.asarray(list(corners),float)*np.asarray(step)
    center=xyz.mean(0);_,axes=np.linalg.eigh((xyz-center).T@(xyz-center))
    projected=(xyz-center)@axes
    if np.ptp(projected[:,0])*world_scale>50:return tris,None
    # Remove only collinear boundary subdivisions, to 5 mm in actual world
    # space. No interior decimator or UV seam operation is run.
    while len(ring)>3:
        removed=False
        for i in range(len(ring)):
            a,b,c=(np.asarray(ring[k%len(ring)],float)*np.asarray(step) for k in (i-1,i,i+1))
            ac=c-a;length=np.linalg.norm(ac)
            distance=np.linalg.norm(np.cross(b-a,ac))/max(length,1e-12)
            if distance*world_scale<=5 and np.dot(b-a,b-c)<=0:
                ring.pop(i);removed=True;break
        if not removed:break
    rp=(np.asarray(ring,float)*np.asarray(step)-center)@axes[:,1:]
    turns=[]
    for i in range(len(ring)):
        a,b,c=(rp[k%len(ring)] for k in (i-1,i,i+1))
        ab,bc=b-a,c-b
        turns.append(float(ab[0]*bc[1]-ab[1]*bc[0]))
    if min(turns)<-1e-5 and max(turns)>1e-5:return tris,None
    vertices=[corners[v] for v in ring]
    out=[(vertices[0],vertices[i],vertices[i+1]) for i in range(1,len(vertices)-1)]
    if len(out)>=len(tris):return tris,None
    normal=sum((np.cross((np.asarray(t[1][:3])-t[0][:3])*step,
                         (np.asarray(t[2][:3])-t[0][:3])*step) for t in tris),np.zeros(3))
    t=out[0];newnormal=np.cross((np.asarray(t[1][:3])-t[0][:3])*step,
                               (np.asarray(t[2][:3])-t[0][:3])*step)
    if np.dot(normal,newnormal)<0:out=[(t[0],t[2],t[1]) for t in out]
    return out,dict(operation='single convex source-surface boundary retessellation',
             triangles_before=len(tris),triangles_after=len(out),boundary_vertices=len(ring),
             maximum_relief_mm=float(np.ptp(projected[:,0])*world_scale),
             openings='one source boundary, no holes',appearance_accepted=False)


def protected_source_pieces(d, path, pin, full_parts, author_features=False):
    """Map prior camera-visible losses to current connected SOURCE pieces.

    The source piece is retained exactly, rather than restoring every unrelated
    triangle using its texture. Unmatched evidence retains the whole source part
    and is reported; a filename or approximate location cannot waive a feature.
    """
    import numpy as np
    blob = path.read_bytes()
    require(sha(blob)==pin, 'protected feature evidence pin')
    flags=[r for r in json.loads(blob)['pieces'] if r['ortho_fail'] or r.get('cam_fail')]
    by = collections.defaultdict(list)
    for r in flags:
        by[(r['placement'],r['part'])].append(r)
    selected=collections.defaultdict(set)
    fallbacks=set()
    mapped=0
    authored=0
    authored_pieces={}
    evidence=[]
    for (pli,pi), records in by.items():
        if pi in full_parts:
            mapped += len(records)
            continue
        pl=d['placements'][pli];m=d['meshes'][pl[0]]
        require(m[6]<=pi<m[6]+m[7], 'protected part/placement source identity')
        fc,cc=d['part_lods'][pi]
        tris=[]; identities=[]
        for ci in range(fc,fc+cc):
            c=d['clusters'][ci]
            for ti,t in enumerate(level_triangles(d,d['levels'][c[6]])):
                tris.append(t);identities.append((ci,ti))
        local=np.asarray([[v[:3] for v in t] for t in tris],float)*np.asarray(m[11:14])+np.asarray(m[8:11])
        A=np.asarray(pl[2:]).reshape(3,4);world=local@A[:,:3].T+A[:,3]
        q=np.rint(world).astype(np.int64)
        parent={}
        def find(x):
            parent.setdefault(x,x)
            while parent[x]!=x:
                parent[x]=parent[parent[x]];x=parent[x]
            return x
        for t in q:
            root=find(tuple(t[0]))
            for v in t[1:]:
                other=find(tuple(v))
                if root!=other:parent[other]=root
        components=collections.defaultdict(list)
        for ti,t in enumerate(q):components[find(tuple(t[0]))].append(ti)
        boxes=[]
        for indices in components.values():
            xyz=world[indices].reshape(-1,3)
            boxes.append((indices,np.rint(xyz.min(0)).astype(int),np.rint(xyz.max(0)).astype(int)))
        for r in records:
            matches=[ix for ix,lo,hi in boxes if len(ix)==r['ntri'] and
                     max(np.max(np.abs(lo-r['lo'])),np.max(np.abs(hi-r['hi'])))<=3]
            if len(matches)!=1:
                fallbacks.add(pi)
                evidence.append(dict(placement=pli,part=pi,source_box=[r['lo'],r['hi']],
                                     result='whole source part retained; piece mapping ambiguous'))
                continue
            for ti in matches[0]:
                ci,ordinal=identities[ti];selected[ci].add(ordinal)
            mapped+=1
            detail=None
            if author_features and r.get('author_group') in ('ground-surfaces','roof-surfaces','facade-surfaces'):
                ts=[tris[ti] for ti in matches[0]]
                scale=float(np.linalg.norm(A[:,:3],axis=0).max())
                rebuilt,detail=author_planar_boundary(ts,np.asarray(m[11:14]),scale)
                if detail:
                    identity=tuple(identities[ti] for ti in matches[0])
                    authored_pieces[identity]=rebuilt
                    authored+=1
            evidence.append(dict(placement=pli,part=pi,source_box=[r['lo'],r['hi']],
                                 source_triangles=r['ntri'],result='authored named boundary' if detail else
                                 'exact connected source piece retained',authoring=detail))
    parts={pi for _,pi in by}-full_parts
    replacements={}
    for pi in parts-fallbacks:
        fc,cc=d['part_lods'][pi]
        for ci in range(fc,fc+cc):
            c=d['clusters'][ci];ts=level_triangles(d,d['levels'][c[6]])
            replacements[ci]=[t for ti,t in enumerate(ts) if ti in selected[ci]]
    # A source-connected roof may cross cluster boundaries. Keep its existing
    # identity by assigning the authored boundary to its first source cluster.
    # Its other cluster slots remain present, empty for this feature.
    for identity,rebuilt in authored_pieces.items():
        bycluster=collections.defaultdict(set)
        for ci,ti in identity:bycluster[ci].add(ti)
        if any(ci not in replacements for ci in bycluster):continue
        for ci,ordinals in bycluster.items():
            source=level_triangles(d,d['levels'][d['clusters'][ci][6]])
            remove=canonical([source[ti] for ti in ordinals])
            kept=[]
            for t in replacements[ci]:
                key=min(t,t[1:]+t[:1],t[2:]+t[:2])
                if remove[key]:remove[key]-=1
                else:kept.append(t)
            replacements[ci]=kept
        replacements[min(bycluster)].extend(rebuilt)
    return replacements,parts,dict(flagged_pieces=len(flags),mapped_source_pieces=mapped,
             mapped_exact=mapped-authored,authored_named_pieces=authored,
             fallback_whole_parts=sorted(fallbacks),records=evidence)


def solid_shells(d, owners, keep_parts):
    """Author opaque closed masses as PCA box shells, never a whole-room decimate.

    A 16x16 occupancy test on all three principal projections refuses openings,
    fences and branches. Thin/flat pieces, changing owners, alpha materials,
    non-box masses and out-of-grid shells retain their complete source geometry.
    New corners inherit the nearest source corner's UV and prelit value, and
    remain on the existing quantization grid and texture/part identity.
    """
    import numpy as np
    replacements, evidence = {}, []
    for mi, mesh in enumerate(d['meshes']):
        if mi in owners:
            continue
        step = np.asarray(mesh[11:14])
        for pi in range(mesh[6], mesh[6]+mesh[7]):
            if pi not in keep_parts or d['materials'][pi][4] != 0:
                continue
            fc, cc = d['part_lods'][pi]
            for ci in range(fc, fc+cc):
                c = d['clusters'][ci]
                tris = level_triangles(d, d['levels'][c[6]])
                # Connected source features, including UV/color seams welded
                # by position for component membership only.
                parents = {}
                def find(x):
                    parents.setdefault(x, x)
                    while parents[x] != x:
                        parents[x] = parents[parents[x]]
                        x = parents[x]
                    return x
                for t in tris:
                    root = find(t[0][:3])
                    for v in t[1:]:
                        other = find(v[:3])
                        if root != other:
                            parents[other] = root
                pieces = collections.defaultdict(list)
                for t in tris:
                    pieces[find(t[0][:3])].append(t)
                authored, changed = [], False
                for component, tt in enumerate(pieces.values()):
                    if len(tt) < 24 or len(tt) > 2000:
                        authored.extend(tt)
                        continue
                    corners = list(dict.fromkeys(v for t in tt for v in t))
                    q = np.asarray([v[:3] for v in corners], float)
                    pos = q*step
                    center = pos.mean(axis=0)
                    _, axes = np.linalg.eigh((pos-center).T@(pos-center))
                    if np.linalg.det(axes) < 0:
                        axes[:, 0] *= -1
                    local = (pos-center)@axes
                    lo, hi = local.min(axis=0), local.max(axis=0)
                    extent = hi-lo
                    # A broad near-planar face gets a two-triangle authored
                    # surface only when its in-plane footprint has no opening.
                    planar = extent[0] <= max(max(step)*2, extent[1]*.005)
                    if extent[1] < max(step)*8:
                        authored.extend(tt)
                        continue
                    index = {v: n for n, v in enumerate(corners)}
                    lt = local[np.asarray([[index[v] for v in t] for t in tt])]
                    cover = []
                    for a, b in (((1,2),) if planar else ((0,1),(0,2),(1,2))):
                        samples = np.asarray([[lo[a]+extent[a]*(u+.5)/16,
                                              lo[b]+extent[b]*(v+.5)/16]
                                             for u in range(16) for v in range(16)])
                        hit = np.zeros(256, bool)
                        for tri in lt[:, :, [a,b]]:
                            x, y, z = tri
                            ab, ac = y-x, z-x
                            den = ab[0]*ac[1]-ab[1]*ac[0]
                            if abs(den) < 1e-12:
                                continue
                            ap = samples-x
                            u = (ap[:,0]*ac[1]-ap[:,1]*ac[0])/den
                            v = (ab[0]*ap[:,1]-ab[1]*ap[:,0])/den
                            hit |= (u>=-1e-6)&(v>=-1e-6)&(u+v<=1.000001)
                        cover.append(float(hit.mean()))
                    if min(cover) < .98:
                        authored.extend(tt)
                        continue
                    box = (np.asarray([[(lo[0]+hi[0])*.5,
                                         hi[1] if u else lo[1],hi[2] if v else lo[2]]
                                        for u,v in ((0,0),(1,0),(1,1),(0,1))]) if planar else
                           np.asarray([[hi[a] if bits>>a&1 else lo[a] for a in range(3)]
                                       for bits in range(8)]))
                    world = box@axes.T+center
                    grid = np.rint(world/step).astype(int)
                    # The fixed source grid/mesh bounds are an explicit budget.
                    if (grid<0).any() or (grid>65535).any():
                        authored.extend(tt)
                        continue
                    nearest = ((world[:,None,:]-pos[None,:,:])**2).sum(axis=2).argmin(axis=1)
                    vertices = [tuple(int(v) for v in g)+tuple(corners[int(n)][3:])
                                for g, n in zip(grid, nearest)]
                    faces = []
                    if planar:
                        source_pos = np.asarray([[np.asarray(v[:3])*step for v in t] for t in tt])
                        normal = np.cross(source_pos[:,1]-source_pos[:,0],source_pos[:,2]-source_pos[:,0]).sum(axis=0)
                        ring = [0,1,2,3]
                        if np.dot(np.cross(world[1]-world[0],world[2]-world[0]),normal)<0:
                            ring.reverse()
                        faces = [(vertices[ring[0]],vertices[ring[1]],vertices[ring[2]]),
                                 (vertices[ring[0]],vertices[ring[2]],vertices[ring[3]])]
                    # Six actual opaque surfaces; orient each away from center.
                    for axis in (() if planar else range(3)):
                        other = [a for a in range(3) if a != axis]
                        for side in (0,1):
                            ring = [((side<<axis)|(u<<other[0])|(v<<other[1]))
                                    for u,v in ((0,0),(1,0),(1,1),(0,1))]
                            normal = np.cross(world[ring[1]]-world[ring[0]],world[ring[2]]-world[ring[0]])
                            if np.dot(normal, world[ring].mean(axis=0)-world.mean(axis=0)) < 0:
                                ring.reverse()
                            faces.extend([(vertices[ring[0]],vertices[ring[1]],vertices[ring[2]]),
                                          (vertices[ring[0]],vertices[ring[2]],vertices[ring[3]])])
                    authored.extend(faces)
                    changed = True
                    evidence.append(dict(mesh=mi,source_bin=mesh[0],part=pi,cluster=ci,
                        component=component,source_triangles=len(tt),shell_triangles=len(faces),
                        primitive='broad planar quad' if planar else 'opaque box shell',
                        principal_projection_coverage=cover,
                        source_corners_sha256=sha(json.dumps(tt).encode()),
                        shell_corners_sha256=sha(json.dumps(faces).encode()),
                        material_unchanged=True,uv_method='nearest source corner; appearance unaccepted'))
                if changed:
                    replacements[ci] = authored
    return replacements, evidence


def install_shells(out, replacements):
    """Reuse existing stripifier and indexed 256-vertex packer for authored parts."""
    import mesh_lod
    original = copy.deepcopy(out)
    out['vertices'], out['meshlets'], out['commands'], out['levels'], out['parts'] = [], [], [], [], []
    for pi, part in enumerate(original['parts']):
        first = len(out['meshlets'])
        base = len(out['vertices'])
        fc, cc = original['part_lods'][pi]
        kept = set()
        for ci in range(fc,fc+cc):
            if ci in replacements:
                continue
            c=original['clusters'][ci]
            for lv in original['levels'][c[6]:c[6]+c[7]]:
                for ji in range(lv[0],lv[0]+lv[1]):
                    kept.update(codec.local_vertices(original,ji))
        oldmap={vi:base+k for k,vi in enumerate(sorted(kept))}
        out['vertices'].extend(original['vertices'][vi] for vi in sorted(kept))
        pool={tuple(original['vertices'][vi]):new-base for vi,new in oldmap.items()}
        for ci in range(fc, fc+cc):
            c = original['clusters'][ci]
            for ordinal in range(c[7]):
                lv = original['levels'][c[6]+ordinal]
                start = len(out['meshlets'])
                if ci in replacements:
                    # Same reconstructed solid feature at every source distance.
                    ts = replacements[ci] if lv[1] else []
                    strips = mesh_lod.stripify(ts)
                    chunks = mesh_lod.pack_meshlets(strips,256,lambda v:v[:3])
                    for chunk in chunks:
                        keys = list(dict.fromkeys(v for s in chunk for v in s))
                        local = {v:i for i,v in enumerate(keys)}
                        offsets = []
                        for v in keys:
                            if v not in pool:
                                pool[v] = len(out['vertices'])-base
                                out['vertices'].append(v)
                            offsets.append(pool[v])
                        require(max(offsets, default=0)<=65535, 'authored part pool too large')
                        st = [[local[v] for v in s] for s in chunk]
                        size = sum(1+len(s) for s in st)
                        bounds = [min(v[a] for v in keys) for a in range(3)]+[max(v[a] for v in keys) for a in range(3)]
                        out['meshlets'].append([base,0,size,len(keys),0x8000|len(st),*bounds])
                        out['commands'].append(dict(pool=offsets,strips=st))
                    allq = [v for t in ts for v in t]
                    if allq:
                        bounds = [min(v[a] for v in allq) for a in range(3)]+[max(v[a] for v in allq) for a in range(3)]
                        out['clusters'][ci][:6] = [min(original['clusters'][ci][a],bounds[a]) if a<3 else
                                                 max(original['clusters'][ci][a],bounds[a]) for a in range(6)]
                else:
                    for ji in range(lv[0], lv[0]+lv[1]):
                        rec = list(original['meshlets'][ji])
                        indices=[oldmap[v] for v in codec.local_vertices(original,ji)]
                        # Compact the original shared vertex identities once per
                        # part, keeping contiguous plain ranges and pool aliases.
                        if rec[4]&0x8000:
                            rec[0]=base
                            offsets=[v-base for v in indices]
                        else:
                            rec[0]=min(indices)
                            require(indices==list(range(rec[0],rec[0]+len(indices))), 'authored pass broke plain range')
                            offsets=list(range(len(indices)))
                        out['meshlets'].append(rec)
                        out['commands'].append(dict(pool=offsets,strips=original['commands'][ji]['strips']))
                out['levels'].append([start,len(out['meshlets'])-start,lv[2]])
        out['parts'].append(part[:6]+[first,len(out['meshlets'])-first]+part[8:])
    cursor=0
    for rec,cmd in zip(out['meshlets'],out['commands']):
        cursor += cursor%2 if rec[4]&0x8000 else 0
        rec[1]=cursor
        cursor += (2*rec[3] if rec[4]&0x8000 else 0)+sum(1+len(s) for s in cmd['strips'])
    return out


def compile_selection(d, keep_parts):
    out = copy.deepcopy(d)
    out['schema'] = codec.SCHEMA
    out.pop('index_layout', None)
    out['vertices'], out['meshlets'], out['commands'] = [], [], []
    out['levels'], out['parts'] = [], []
    # Preserve the original corner/strip order of retained features. Only remove
    # absent static features and compact each part's referenced vertex pool.
    for pi, part in enumerate(d['parts']):
        first = len(out['meshlets'])
        old_vertices = set()
        fc, cc = d['part_lods'][pi]
        selected = []
        if pi in keep_parts:
            for c in d['clusters'][fc:fc+cc]:
                for lv in d['levels'][c[6]:c[6]+c[7]]:
                    selected.extend(range(lv[0], lv[0]+lv[1]))
            for ji in selected:
                old_vertices.update(codec.local_vertices(d, ji))
        remap = {old: len(out['vertices'])+k for k, old in enumerate(sorted(old_vertices))}
        out['vertices'].extend(d['vertices'][old] for old in sorted(old_vertices))
        for c in d['clusters'][fc:fc+cc]:
            for lv in d['levels'][c[6]:c[6]+c[7]]:
                start = len(out['meshlets'])
                if pi in keep_parts:
                    for ji in range(lv[0], lv[0]+lv[1]):
                        rec = list(d['meshlets'][ji])
                        local = [remap[k] for k in codec.local_vertices(d, ji)]
                        base = min(local)
                        rec[0] = base
                        if not rec[4] & 0x8000:
                            require(local == list(range(base, base+len(local))),
                                    'plain meshlet lost contiguous source vertices')
                        out['meshlets'].append(rec)
                        out['commands'].append(dict(pool=[k-base for k in local],
                                                    strips=d['commands'][ji]['strips']))
                out['levels'].append([start, len(out['meshlets'])-start, lv[2]])
        out['parts'].append(part[:6]+[first, len(out['meshlets'])-first]+part[8:])
    cursor = 0
    for rec, command in zip(out['meshlets'], out['commands']):
        cursor += cursor % 2 if rec[4] & 0x8000 else 0
        rec[1] = cursor
        cursor += (2*rec[3] if rec[4] & 0x8000 else 0)+sum(1+len(s) for s in command['strips'])
    return out


def report(d, out, owners, groups, part_group, replacements=None):
    rows = []
    exact = 0
    for mi, mesh in enumerate(d['meshes']):
        for pi in range(mesh[6], mesh[6]+mesh[7]):
            fc, cc = d['part_lods'][pi]
            n0 = n1 = 0
            for ci in range(fc, fc+cc):
                c = d['clusters'][ci]
                for ordinal in range(c[7]):
                    li = c[6]+ordinal
                    a, b = level_triangles(d, d['levels'][li]), level_triangles(out, out['levels'][li])
                    if replacements and ci in replacements:
                        require(canonical(b) == canonical(replacements[ci] if a else []), 'authored shell not serialized exactly')
                    elif pi in part_group:
                        require(a == b, 'retained oriented corner/strip sequence changed')
                        exact += 1
                    else:
                        require(not b, 'omitted static feature still has triangles')
                    if ordinal == 0:
                        n0 += len(a)
                        n1 += len(b)
            rows.append(dict(mesh=mi, source_bin=mesh[0], part=pi,
                             group=part_group.get(pi, 'omitted-floor-detail'),
                             owner_exact=mi in owners, l0_triangles_before=n0,
                             l0_triangles_after=n1,
                             texture_key='%08x-%08x' % tuple(d['materials'][pi][:2])))
    require(out['meshes'] == d['meshes'] and out['placements'] == d['placements'] and
            out['materials'] == d['materials'] and
            [c[6:] for c in out['clusters']] == [c[6:] for c in d['clusters']] and
            out['part_lods'] == d['part_lods'], 'source identity tables changed')
    return dict(schema='re4dc.world-rebuild27.selection/1', room='r101',
                operation='explicit source-feature structural proxy; no decimation',
                selected_groups=groups, unique_owner_meshes=sorted(owners),
                exact_retained_levels=exact, feature_rows=rows,
                l0_triangles_before=sum(r['l0_triangles_before'] for r in rows),
                l0_triangles_after=sum(r['l0_triangles_after'] for r in rows),
                source_identity_tables_unchanged=True,
                appearance_accepted=False, timing_available=False,
                lostpart_verdict='NOT RUN; intentionally sparse floor is not a complete world')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--groups', required=True, help='comma-separated explicit additive feature group names')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--name', required=True)
    ap.add_argument('--solid-shells', action='store_true',
                    help='explicit primitive authoring; requires numpy, preserves changing owners')
    ap.add_argument('--protected-pieces', type=Path,
                    help='pinned prior lost-part evidence; retain precise connected features, not whole parts')
    ap.add_argument('--author-planar-features',action='store_true',
                    help='rebuild explicitly named roof/facade pieces through their source boundary')
    args = ap.parse_args()
    require(not (args.solid_shells and args.protected_pieces),
            'primitive authoring and source-piece restoration need separate named candidates')
    require(not args.author_planar_features or args.protected_pieces,
            'named planar authoring requires protected-piece feature input')
    require(not args.out.exists(), 'output exists; use a new immutable candidate name')
    plan_blob = args.plan.read_bytes()
    plan = json.loads(plan_blob)
    require(plan['room'] == 'r101', 'plan room')
    require(set(SOURCE_INPUTS) <= plan['source_sha256'].keys(),
            'all five source pins are required: '+', '.join(SOURCE_INPUTS))
    d, files, owners, policy = load(args.source)
    for name, pin in plan['source_sha256'].items():
        blob = files[name] if name in files else (args.source/name).read_bytes()
        require(sha(blob) == pin, 'source pin mismatch: '+name)
    names = args.groups.split(',')
    require(len(set(names)) == len(names) and all(n in plan['groups'] for n in names), 'unknown/duplicate group')
    part_group = {}
    for mi in sorted(owners):
        m = d['meshes'][mi]
        for pi in range(m[6], m[6]+m[7]):
            part_group[pi] = 'changing-owner-exact'
    for name in names:
        spec = plan['groups'][name]
        for mi in spec.get('meshes', []):
            require(0 <= mi < len(d['meshes']), 'mesh feature outside source')
            m = d['meshes'][mi]
            for pi in range(m[6], m[6]+m[7]):
                if mi not in owners and (not spec.get('opaque_only', False) or d['materials'][pi][4] == 0):
                    part_group.setdefault(pi, name)
        for pi in spec.get('parts', []):
            require(0 <= pi < len(d['parts']), 'part feature outside source')
            part_group.setdefault(pi, name)
    piece_replacements, piece_evidence = {}, None
    if args.protected_pieces:
        piece_replacements, selected_parts, piece_evidence = protected_source_pieces(
            d,args.protected_pieces,plan['protected_evidence']['sha256'],set(part_group),args.author_planar_features)
        for pi in selected_parts:
            part_group[pi]='exact-protected-connected-pieces'
    out = compile_selection(d, set(part_group))
    replacements, authored_features = {}, []
    if piece_replacements:
        out=install_shells(out,piece_replacements)
        replacements.update(piece_replacements)
    if args.solid_shells:
        replacements, authored_features = solid_shells(d, owners, set(part_group))
        if replacements:
            out = install_shells(out, replacements)
    mesh = codec.serialize_mesh(out)
    policy_blob = codec.serialize_policy(out)
    require(policy_blob == files['ps2-world.r4pw'], 'policy must be unchanged')
    out = codec.decode(mesh, policy_blob)
    receipt = report(d, out, owners, names, part_group, replacements)
    receipt['authored_solid_features'] = authored_features
    receipt['authored_clusters'] = len(replacements)
    receipt['protected_piece_mapping'] = piece_evidence
    args.out.mkdir(parents=True)
    (args.out/'ps2-world.raw.re4mesh').write_bytes(mesh)
    (args.out/'ps2-world.r4pw').write_bytes(policy_blob)
    # Fresh strip groups; original policy-source CRC is a separately qualified
    # mapping admitted by the candidate-specific default-off runtime table.
    result = subprocess.run([sys.executable, str(HERE/'ps2_strip_groups.py'),
             str(args.out/'ps2-world.raw.re4mesh'), str(args.out/'ps2-world.r4pw'),
             str(args.out/'ps2-world.re4mesh'), str(args.out/'ps2-world.r4sg'),
             '--groups', '4', '--report', str(args.out/'strip-groups.json')],
             check=True, capture_output=True, text=True)
    (args.out/'strip-groups.log').write_text(result.stdout+result.stderr)
    mesh = (args.out/'ps2-world.re4mesh').read_bytes()
    grouped = codec.decode(mesh, policy_blob)
    for lv, glv in zip(out['levels'], grouped['levels']):
        require(canonical(level_triangles(out, lv)) == canonical(level_triangles(grouped, glv)),
                'strip groups changed oriented corner triangles')
    sg = bytearray((args.out/'ps2-world.r4sg').read_bytes())
    struct.pack_into('<I', sg, 24, policy)
    (args.out/'ps2-world.r4sg').write_bytes(sg)
    for n in UNCHANGED_COMPANIONS:
        (args.out/n).write_bytes(files[n])
    companion_hashes = {}
    for n in UNCHANGED_COMPANIONS:
        copied = (args.out/n).read_bytes()
        require(copied == files[n], 'companion copy readback mismatch: '+n)
        companion_hashes[n] = sha(copied)
    mh = struct.unpack_from('<4s19I', mesh)
    row = [0x101, len(policy_blob), len(out['placements']), len(out['parts']), len(out['meshes']),
           struct.unpack_from('<I', policy_blob, 20)[0], fnv(policy_blob), mh[3], len(mesh), policy]
    header = '// PRIVATE GENERATED candidate source-policy mapping; no visibility certification.\n'
    header += 'static constexpr Certificate rebuild27_certificates[] = {\n'
    header += '{%s},\n};\n' % ','.join('0x%08xU' % v for v in row)
    (args.out/'world_rebuild27_certificates.inc').write_text(header)
    receipt.update(name=args.name, source_directory=str(args.source),
                   source_sha256={n: sha(v) for n, v in files.items()},
                   plan_sha256=sha(plan_blob), tool_sha256=sha(Path(__file__).read_bytes()),
                   candidate_sha256=sha(mesh), candidate_bytes=len(mesh),
                   candidate_crc='%08x' % mh[3], certificate_row=row,
                   runtime_policy_mapping_required=True,
                   unchanged_companions=list(UNCHANGED_COMPANIONS),
                   unchanged_companion_sha256=companion_hashes,
                   unchanged_companions_readback_verified=True,
                   output_sha256={'ps2-world.re4mesh': sha(mesh), **companion_hashes},
                   room_file='Whole source room.r4rc unchanged: GRID/OCCL/SRCB/SCDD preserved; no new visibility proof')
    (args.out/'RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n')
    (args.out/'feature-plan.json').write_bytes(plan_blob)
    (args.out/'RECIPE.txt').write_text('Explicit private r101 candidate, default off.\n'+
         'Command: '+json.dumps(sys.argv)+'\nNo texture/archive output. No timing or appearance acceptance.\n')
    sums = ''.join('%s  %s\n' % (sha(p.read_bytes()), p.name) for p in sorted(args.out.iterdir()) if p.is_file())
    (args.out/'SHA256SUMS').write_text(sums)
    print(json.dumps({k: receipt[k] for k in ('name','l0_triangles_before','l0_triangles_after',
          'candidate_bytes','candidate_crc','candidate_sha256','exact_retained_levels')}, indent=2))


if __name__ == '__main__':
    main()
