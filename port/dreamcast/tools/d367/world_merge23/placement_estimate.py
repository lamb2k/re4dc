#!/usr/bin/env python3
"""Estimate whole placement/material context merges with bounded child meshlets.

Unlike estimate.py's preliminary meshlet probe, a context may own many <=256
corner meshlets. Every eligible original part is moved in full, or left intact.
Results are static camera geometry estimates, never whole-frame timing claims.
"""
import argparse, collections, json, struct
from pathlib import Path
import numpy as np
from estimate import cameras,load,excluded_placements,selection,strips_emitted,sg
from inputs import identity, validate_ownership, lod_policy


def candidates(D,files,room,full_detail,bake_uv=False):
    p=D['p'];exclude=excluded_placements(D,files,room)
    uses=collections.Counter(x['mesh'] for x in p.placements)
    policy=files['r4pw'].read_bytes();parts={};pieces={};reasons=collections.Counter()
    for pi,pl in enumerate(p.placements):
        mesh=p.meshes[pl['mesh']]
        if pl['placement'] in exclude:reasons['live_owned_or_sky_placements']+=1;continue
        if uses[pl['mesh']]>1:reasons['instanced_placements']+=1;continue
        for part in range(mesh['first_part'],mesh['first_part']+mesh['part_count']):
            meta=policy[32+16*part:48+16*part];raw=p.m[p.o_part+36*part:p.o_part+36*(part+1)]
            if meta[12]!=0 or meta[15] or raw[9]!=255:reasons['nonopaque_or_alpha_parts']+=1;continue
            fc,cc=p.plod[part];clusters=p.clusters[fc:fc+cc]
            if not full_detail and any(c['level_count']!=1 for c in clusters):
                reasons['multi_LOD_parts']+=1;continue
            keys=[]
            for cl in clusters:
                fm,mc,_=p.levels[cl['first_level']]
                for li in range(fm,fm+mc):
                    nv=int(D['vc'][li]);assert 0<nv<=256
                    cg=D['CG'][D['c0'][li]:D['c0'][li+1]];M=D['WQ'][pi]
                    xyz=cg@M[:,:3].T+M[:,3]
                    key=(pi,li);keys.append(key)
                    pieces[key]=dict(nv=nv,lo=xyz.min(0),hi=xyz.max(0),center=(xyz.min(0)+xyz.max(0))*.5)
            if not keys:continue
            lo=np.min([pieces[k]['lo'] for k in keys],0);hi=np.max([pieces[k]['hi'] for k in keys],0)
            parts[(pi,part)]=dict(members=keys,center=(lo+hi)*.5,
                                 material=((meta[:14]+meta[15:]).hex(),raw[9:12].hex(),'' if bake_uv else raw[20:].hex()))
    return parts,pieces,dict(reasons)


def group_parts(parts,pieces,cell):
    buckets=collections.defaultdict(list)
    for key,p in parts.items():
        bucket=(tuple(np.floor(p['center']/cell).astype(int)),p['material'])
        buckets[bucket].append(key)
    groups=[]
    for bucket,members in sorted(buckets.items()):
        if len({pi for pi,_ in members})<2:continue
        keys=[k for m in members for k in parts[m]['members']]
        # Geometry payload is packed across original placements. Context size
        # is unbounded; only each contained native meshlet has the 256 cap.
        keys.sort(key=lambda k:tuple(pieces[k]['center'])+k)
        batches=[];batch=[];nv=0
        for key in keys:
            if batch and nv+pieces[key]['nv']>256:
                batches.append(batch);batch=[];nv=0
            batch.append(key);nv+=pieces[key]['nv']
        if batch:batches.append(batch)
        output=[]
        for batch in batches:
            output.append(dict(members=batch,nv=sum(pieces[k]['nv'] for k in batch),
                               lo=np.min([pieces[k]['lo'] for k in batch],0),
                               hi=np.max([pieces[k]['hi'] for k in batch],0)))
        groups.append(dict(context=bucket,source_parts=members,batches=output))
    return groups


def source_part_map(D):
    p=D['p'];result={}
    for pi,pl in enumerate(p.placements):
        mesh=p.meshes[pl['mesh']]
        for part in range(mesh['first_part'],mesh['first_part']+mesh['part_count']):
            fc,cc=p.plod[part]
            for cl in p.clusters[fc:fc+cc]:
                for lv in p.levels[cl['first_level']:cl['first_level']+cl['level_count']]:
                    fm,mc,_=lv
                    for li in range(fm,fm+mc):result[(pi,li)]=(pi,part)
    return result


def price(D,parts,groups,cams,lod_px):
    mapping=source_part_map(D);replaced={x for g in groups for x in g['source_parts']};rows=[]
    for frame,cam in cams:
        V=np.array(cam[:12]).reshape(3,4);P=cam[12:19];near=P[6]/(P[5]-1);far=cam[19]
        pairs,mv,tv=selection(D,V,P,near,far,lod_px)
        base_vertices=sum(x['nv'] for x in pairs.values())
        ref=sg.view_counts(D,V,P,near,far,lod_px)
        assert base_vertices==ref['T1' if D['SG'] is not None else 'T0']
        tri={k:strips_emitted(D,*k,mv,tv,V,P,near,x['walk']) for k,x in pairs.items()}
        remaining={k:x for k,x in pairs.items() if mapping[k] not in replaced}
        old_contexts={mapping[k] for k in pairs};remain_contexts={mapping[k] for k in remaining}
        after_v=sum(x['nv'] for x in remaining.values());after_t=sum(tri[k] for k in remaining)
        after_meshlets=len(remaining);new_contexts=0;world_cells=set();new_drawn=set()
        a,c=sg.side_coefs(P)
        for group in groups:
            drawn=False
            for batch in group['batches']:
                center=(batch['lo']+batch['hi'])*.5;ext=(batch['hi']-batch['lo'])*.5
                v=(V[:,:3]@center+V[:,3])[None];r=(np.abs(V[:,:3])@ext)[None]
                out,_,_=sg.classify(v,r,a,c,near,far,False)
                if out[0]:continue
                drawn=True;after_v+=batch['nv'];after_meshlets+=1
                for k in batch['members']:
                    new_drawn.add(k);after_t+=strips_emitted(D,*k,mv,tv,V,P,near)
            if drawn:new_contexts+=1;world_cells.add(group['context'][0])
        # Original box selection can be a false positive. A missing selected
        # finest-level meshlet is safe only if it emits no original strip.
        for k in pairs:
            if mapping[k] in replaced and k in parts[mapping[k]]['members'] and k not in new_drawn:
                assert tri[k]==0,(frame,k,tri[k])
        rows.append(dict(frame=frame,before_selected_meshlets=len(pairs),
                         before_nonzero_transform_meshlets=sum(x['nv']>0 for x in pairs.values()),
                         before_emitting_meshlets=sum(x>0 for x in tri.values()),after_selected_meshlets=after_meshlets,
                         before_part_contexts=len(old_contexts),after_part_contexts=len(remain_contexts)+new_contexts,
                         before_placements=len({pi for pi,_ in old_contexts}),
                         after_placements=len({pi for pi,_ in remain_contexts})+len(world_cells),
                         before_vertices=base_vertices,after_vertices=after_v,
                         before_triangles=sum(tri.values()),after_triangles=after_t))
    mean={k:float(np.mean([r[k] for r in rows])) for k in rows[0] if k!='frame'}
    mean['part_context_drop_percent']=100*(1-mean['after_part_contexts']/mean['before_part_contexts'])
    mean['meshlet_selection_drop_percent']=100*(1-mean['after_selected_meshlets']/mean['before_selected_meshlets'])
    mean['vertex_growth_percent']=100*(mean['after_vertices']/mean['before_vertices']-1)
    return mean,rows


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--inputs',required=True,type=Path);ap.add_argument('--room',choices=('r101','r103'),required=True)
    ap.add_argument('--camera',required=True,type=Path);ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--cells',default='2000,4000,8000,16000');ap.add_argument('--full-detail',action='store_true')
    ap.add_argument('--bake-uv',action='store_true',help='Estimate final float UV baking rather than retaining per-part quantization')
    ap.add_argument('--lod-px',required=True,type=float,help='Effective runtime LOD divisor: quality lod_px times SCENERY_FAR_LOD when enabled')
    ap.add_argument('--profile-receipt',required=True,type=Path,help='Resolved runtime knobs or an explicit scenario receipt to hash into this report')
    args=ap.parse_args();policy=lod_policy(args.lod_px,args.profile_receipt)
    src=json.loads(args.inputs.read_text())[args.room];D,files=load(src)
    source_pin={n:identity(Path(__file__).parent/n) for n in ('placement_estimate.py','estimate.py','inputs.py')}
    parts,pieces,reasons=candidates(D,files,args.room,args.full_detail,args.bake_uv);cams=cameras(args.camera)
    results=[]
    for cell in map(int,args.cells.split(',')):
        groups=group_parts(parts,pieces,cell);mean,rows=price(D,parts,groups,cams,args.lod_px)
        keys={k for g in groups for b in g['batches'] for k in b['members']}
        corners=sum(pieces[k]['nv'] for k in keys);strip_bytes=sum(D['p'].lets[k[1]]['strip_bytes'] for k in keys)
        result=dict(cell_mm=cell,merged_contexts=len(groups),
                    source_parts_replaced=sum(len(g['source_parts']) for g in groups),
                    cross_placement_groups=len(groups),copied_corners=corners,
                    copied_payload_bytes=(22 if args.bake_uv else 18)*corners+strip_bytes,
                    conservative_added_room_bytes=(24 if args.bake_uv else 20)*corners+strip_bytes+sum(32*len(g['batches'])+64 for g in groups),
                    mean=mean,rows=rows,geometry_gate=mean['part_context_drop_percent']>=40 and mean['vertex_growth_percent']<=10,
                    memory_gate='PENDING; no allocation or runtime reader built')
        results.append(result);print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)
    report=dict(kind='OFFLINE STATIC GEOMETRY ESTIMATE; not runtime timings',room=args.room,
                source=src,source_tools=source_pin,ownership_binding=validate_ownership(files,src['provenance']),
                camera=identity(args.camera),frames=[f for f,_ in cams],selection_policy=policy,full_detail=args.full_detail,bake_uv=args.bake_uv,
                eligible_parts=len(parts),eligible_placements=len({pi for pi,_ in parts}),excluded=reasons,
                r100_data_delta_bytes=0,results=results,
                limitations=['Source full-detail geometry replaces LOD choice only in the explicit full-detail arm.',
                             'Unique live-owned props and repeated mesh instances remain on the original path.',
                             'Original strip order is kept within each source meshlet, not across regrouped opaque parts.',
                             'No claim that context reduction removes per-cluster or per-vertex cost.',
                             'Uses sgprice static reference model; placement world_out, sky-far and dynamic gates not replayed.',
                             'Data copy bound is conservative coexistence, not a proven replacement-layout heap delta.',
                             'r100 data unchanged, but s30 target code and BSS effects remain untested.'])
    with args.output.open('x') as f:json.dump(report,f,indent=2)

if __name__=='__main__':main()
