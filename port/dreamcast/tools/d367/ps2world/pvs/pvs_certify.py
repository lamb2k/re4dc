#!/usr/bin/env python3
"""Prepare geometric certificates; never marks runtime liveness accepted.

Usage: pvs_certify.py PACKAGE WORK ROOM [--limit N]
Requires current effective policy plus original.r4pw, ids and append provenance
already authenticated by pvs_prep. Outputs proof-bits.bin and proof.json; these
are proof candidates until runtime admission establishes every dependency live.
"""
import hashlib,json,struct,sys
from pathlib import Path
import numpy as np
from pvs_emit import load_cells,load_inst
from pvs_prove import corners,triangle_hides,quad_hides
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'interior'))
from r4im import Pkg


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pairs(p,pi,cl,level=0):
    cluster=p.clusters[cl];first,count,_=p.levels[cluster['first_level']+level]
    M=p.wq(p.placements[pi])
    for li in range(first,first+count):
        gc,indices=p.let_tris(li);gc=gc[:,:3].astype(np.int64)
        world=gc.astype(np.float64)@M[:,:3].T+M[:,3]
        edge_map={}
        for ti,tri in enumerate(indices):
            for a,b in zip(tri,tri[1:]+tri[:1]):
                if a==b:continue
                key=tuple(sorted((a,b)))
                for tj,old in edge_map.get(key,[]):
                    if len(set(tri)|set(old))!=4:continue
                    # The continuous pair predicate checks both actual planes.
                    # Quantized source walls need not be exactly coplanar: their
                    # identical cached diagonal still closes the real surface.
                    xyz=gc[list(set(tri)|set(old))]
                    coplanar=int(np.dot(np.cross(xyz[1]-xyz[0],xyz[2]-xyz[0]),xyz[3]-xyz[0]))==0
                    edges={}
                    for it in (old,tri):
                        for u,v in zip(it,it[1:]+it[:1]):
                            if (v,u) in edges:del edges[(v,u)]
                            else:edges[(u,v)]=1
                    if len(edges)!=4:continue
                    order=[next(iter(edges))[0]]
                    for _ in range(3):
                        nxt=[v for u,v in edges if u==order[-1]]
                        if len(nxt)!=1:break
                        order.append(nxt[0])
                    if len(set(order))!=4 or (order[-1],order[0]) not in edges:continue
                    boundary=world[order]
                    ts=world[np.array([old,tri])]
                    yield boundary,ts,dict(level=level,meshlet=li,triangle_indices=[tj,ti],corner_indices=[list(old),list(tri)],boundary_corner_indices=order,exact_shared_corner_cache=True,exact_grid_coplanar=coplanar)
                edge_map.setdefault(key,[]).append((ti,tri))


def certify(pkgdir,work,room,limit=32,margin=32.,pairs_only=False):
    pkgdir,work=Path(pkgdir),Path(work)
    p=Pkg(pkgdir/'ps2-world.re4mesh',pkgdir/'ps2-world.r4pw')
    meta=json.loads((work/'meta.json').read_text())
    assert meta['room']==room
    assert meta['static_qualified'] and 'ps2-world.ids' in meta['input_hashes'],'missing static provenance or ids'
    assert meta['static_provenance']['name'] in meta['input_hashes']
    for name,expected in meta['input_hashes'].items():assert sha(pkgdir/name)==expected,'stale prepared input: '+name
    for name,expected in meta['prepared_hashes'].items():assert sha(work/name)==expected,'stale prepared output: '+name
    assert sha(pkgdir/'original.r4pw')==meta['original_policy_sha256']
    C,I=load_cells(work),load_inst(work)
    rows=list(p.iter_clusters())
    assert len(rows)==C['ninst']==I['n']
    lo,hi=[],[];candidates=[]
    for instance,(pi,part,cl,pas,cull,_,_) in enumerate(rows):
        cluster=p.clusters[cl]
        levels=[p.cluster_tris_world(pi,cl,l) for l in range(cluster['level_count'])]
        pts=np.concatenate(levels).reshape(-1,3) if any(len(t) for t in levels) else np.empty((0,3))
        if not len(pts):
            # Empty clusters are retained, not used as occluders.
            lo.append([-1e9]*3);hi.append([1e9]*3);continue
        assert np.isfinite(pts).all() and np.max(abs(pts))<1e6,'unsupported coordinate magnitude'
        lo.append(np.nextafter(pts.min(0)-margin,-np.inf));hi.append(np.nextafter(pts.max(0)+margin,np.inf))
        if I['dyn'][instance] or pas!=0 or cull not in (0,2):continue
        for ti,t in enumerate(levels[0]):
            normal=np.cross(t[1]-t[0],t[2]-t[0]);area=np.linalg.norm(normal)
            if not pairs_only and cluster['level_count']==1 and area>2e6 and abs(normal[1])<0.5*area:candidates.append((float(area),instance,pi,part,cl,ti,t,cull,None))
        def panelkey(boundary):
            v=[tuple(x) for x in boundary]
            return min(tuple(v[k:]+v[:k]) for k in range(4))
        panel_levels=[]
        for level in range(cluster['level_count']):
            found={}
            for boundary,ts,identity in pairs(p,pi,cl,level):
                found.setdefault(panelkey(boundary),(boundary,ts,identity))
            panel_levels.append(found)
        common=set(panel_levels[0])
        for pl in panel_levels[1:]:common.intersection_update(pl)
        for key in sorted(common):
            boundary,ts,identity=panel_levels[0][key]
            normal=np.cross(ts[0,1]-ts[0,0],ts[0,2]-ts[0,0]);area=sum(np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0])) for t in ts)
            if area>2e6 and abs(normal[1])<0.5*np.linalg.norm(normal):
                deps=[]
                for pl in panel_levels:
                    qb,qt,qi=pl[key]
                    deps.append(dict(boundary=qb.tolist(),triangles=qt.tolist(),**qi))
                candidates.append((float(area),instance,pi,part,cl,identity['triangle_indices'][0],boundary,cull,dict(triangles=ts,all_lod_panels=deps,**identity)))
    lo,hi=np.array(lo),np.array(hi)
    candidates.sort(key=lambda t:(-t[0],t[1],t[5]))
    candidates=candidates[:limit]
    pinned={t[1] for t in candidates}
    target_ok=~I['dyn'] & (I['pas']==0)
    for i in pinned:target_ok[i]=False
    S=np.ones((C['nx']*C['nz'],C['ninst']),bool)
    proof=[];used={};cells_with_cut=0
    for cell in np.flatnonzero(C['has']):
        ix,iz=int(cell%C['nx']),int(cell//C['nx'])
        elo=np.array([C['x0']+ix*C['cell'],np.floor((C['ylo'][cell]-1000)/100)*100,C['z0']+iz*C['cell']])-32.
        ehi=np.array([C['x0']+(ix+1)*C['cell'],np.ceil((C['yhi'][cell]+1000)/100)*100,C['z0']+(iz+1)*C['cell']])+32.
        center=(elo+ehi)/2
        targets=np.where(np.arange(8)[None,:,None] & (1<<np.arange(3))[None,None,:],hi[:,None,:],lo[:,None,:])
        for ci,(_,instance,pi,part,cl,ti,t,cull,pair) in enumerate(candidates):
            n=np.cross(t[1]-t[0],t[2]-t[0]);side=np.dot(n,center-t[0])
            direction=1 if side>0 else -1
            if direction<0 and cull!=0:continue
            possible=target_ok & S[cell]
            possible &= ((targets-t[0])@n*direction).max(1)<0
            for a,b in zip(t,np.roll(t,-1,axis=0)):
                edge=np.cross(a-center,b-center)
                possible &= ((targets-center)@edge*direction).max(1)<0
            for target in np.flatnonzero(possible):
                proven=all(quad_hides(q['triangles'],q['boundary'],elo,ehi,lo[target],hi[target],two_sided=cull==0,vertex_error=margin,clearance=2000.) for q in pair['all_lod_panels']) if pair else triangle_hides(t,elo,ehi,lo[target],hi[target],two_sided=cull==0,vertex_error=margin,clearance=2000.)
                if proven:
                    S[cell,target]=False
                    proof.append([int(cell),int(target),int(ci)])
                    used[ci]=dict(instance=int(instance),placement_index=int(pi),placement_field=int(p.placements[pi]['placement']),part=int(part),cluster=int(cl),level=0,triangle_index=int(ti),triangle=t.tolist(),cull=int(cull),key=[p.pmeta[part]['crc'],p.pmeta[part]['fnv']])
                    if pair:used[ci]['pair']={k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in pair.items()}
        if not S[cell].all():cells_with_cut+=1
    # A runtime may wait for all dependency panels to be successfully submitted
    # in the ordinary opaque placement prefix. Never clear an earlier target.
    max_source_placement=max((d['placement_index'] for d in used.values()),default=-1)
    prefix_proof=[]
    for cell,target,dep in proof:
        if rows[target][0]>max_source_placement:prefix_proof.append([cell,target,dep])
        else:S[cell,target]=True
    prefix_dropped=len(proof)-len(prefix_proof);proof=prefix_proof
    cells_with_cut=int((~S[C['has']]).any(1).sum())
    packed=np.packbits(S,axis=1,bitorder='little').tobytes()
    (work/'proof-bits.bin').write_bytes(packed)
    report=dict(room=room,kind='continuous-triangle-geometric-candidate',runtime_admitted=False,clearance_mm=2000,vertex_uncertainty_mm=32,target_bound_expansion_mm=32,eye_bound_expansion_mm=32,occluder_lod_policy='single triangles from single-level clusters; exact directed quad panels certified at every actual LOD',pinned_instances=sorted(pinned),candidate_triangles=len(candidates),used_occluders=used,cell_target_proofs=proof,cells_with_cuts=cells_with_cut,cleared_bits=len(proof),set_cells=int(C['has'].sum()),cells=int(C['nx']*C['nz']),instances=int(C['ninst']),hashes={name:sha(work/name) for name in ('meta.json','cells.bin','inst.tsv','proof-bits.bin')},input_hashes={name:sha(pkgdir/name) for name in ('ps2-world.re4mesh','ps2-world.r4pw','original.r4pw','ps2-world.ids','ps2-world.r4tc')},runtime_requirements=['exact compiled certificate and all input identity checks','all used placements, source parts and opaque material keys guaranteed live this frame','no unsupported source hide/AREA/gate/root-pose/animation policy','near/FOV projection clip bound less than 1000mm ray radius','all panel vertices safely inside actual near/far to avoid shared-edge clipping ambiguity','opaque packet preflight and texture residency','ordinary opaque full geometry path with CPU backface off','unsupported state means draw all'])
    report['opaque_prefix_max_placement']=max_source_placement
    report['pairs_only']=pairs_only
    report['vertex_uncertainty_mm']=margin
    report['target_bound_expansion_mm']=margin
    report['prefix_early_bits_retained']=prefix_dropped
    report['input_hashes'].update(meta['input_hashes'])
    (work/'proof.json').write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps({k:report[k] for k in ('room','candidate_triangles','cells_with_cuts','cleared_bits','set_cells','cells','instances','runtime_admitted')}),flush=True)


if __name__=='__main__':
    a=sys.argv[1:];certify(a[0],a[1],int(a[2],16),int(a[a.index('--limit')+1]) if '--limit' in a else 32,float(a[a.index('--margin')+1]) if '--margin' in a else 32.,'--pairs-only' in a)
