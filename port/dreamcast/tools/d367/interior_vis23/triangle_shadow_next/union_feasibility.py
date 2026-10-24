#!/usr/bin/env python3
"""Fixed20 actual shared-index union feasibility, no runtime/data changes.

Same129 authentic eyes/full old Y, same whole-cluster targets. Conditional
counterfactual is ONLY the prior40 authored per-LOD meshlet boxes, never new
PVS targets. Actual cache/kernel/transform/unchanged-clip identity is required
for eventual runtime admission; this host geometry does not establish it.
"""
import argparse
import collections
import json
import resource
from pathlib import Path
from fractions import Fraction as Q
import feasibility as f
import smaller_domains as s
from exact_union import boundary,prove_union

SMALLER_SHA='e42fac7e3521c7ac549f2fb1a7ddd47aaffcb5b7d80d94f496cdf83a8fc5e6b7'
UNION_REVIEW='f26ed9355bae23be24f0445580191b06a73106e26810a5587f2903c5cb06565d'


def panel_neighbors(p,policy,face):
    pi,part,ci,li=(face[k] for k in ('placement','part','cluster','meshlet'))
    pl=p.placements[pi];mesh=p.meshes[pl['mesh']];meta=p.pmeta[part];cl=p.clusters[ci]
    fc,nc=p.plod[part]
    if not(mesh['first_part']<=part<mesh['first_part']+mesh['part_count'] and fc<=ci<fc+nc and cl['level_count']==face['level_count']==1):return [],'owner_or_lod'
    if meta['pass_'] or meta['cull'] not in (0,2) or policy[32+16*part+15]&1:return [],'material'
    first,nm,_=p.levels[cl['first_level']]
    if not first<=li<first+nm:return [],'meshlet_owner'
    cs,ts=p.let_tris(li);seed=tuple(face['corners'])
    if seed not in ts or len(cs)!=p.lets[li]['vc'] or not 0<len(cs)<=256:return [],'source_triple_or_extent'
    actual=tuple(tuple(0 if mesh['step'][k]==0 else cs[j][k] for k in range(3)) for j in seed)
    if actual!=tuple(map(tuple,face['grid'])):return [],'source_positions'
    world,det=f.mapping(p,pi)
    if not det:return [],'singular'
    pairs=[];seen=set()
    for mate in ts:
        mate=tuple(mate)
        # Exact source CORNER identity: same projected cache slot, never weld
        # coordinate-equal corners from different UV/index/kernel histories.
        if mate in seen or len(set(seed)&set(mate))!=2 or len(set(seed)|set(mate))!=4:continue
        seen.add(mate)
        try:_,cycle,common=boundary((seed,mate))
        except ValueError:continue
        points={i:world(cs[i][:3]) for i in set(cycle)}
        pairs.append(dict(triangles=(seed,mate),positions=points,boundary=cycle,shared=common))
    return pairs,None if pairs else 'no_actual_shared_index_neighbor'


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-tree',type=Path,required=True);ap.add_argument('--r6',type=Path,required=True);ap.add_argument('--base-evidence',type=Path,required=True);ap.add_argument('--smaller-evidence',type=Path,required=True);ap.add_argument('--review',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.out.exists():raise ValueError('Preserve previous report')
    resource.setrlimit(resource.RLIMIT_AS,(f.LIMIT,f.LIMIT))
    smallpath=a.smaller_evidence/'report.json';basepath=a.base_evidence/'bounded512-report.json';diagpath=a.base_evidence/'diagnostic-report.json'
    if f.digest(smallpath)!=SMALLER_SHA or f.digest(basepath)!=s.MAIN_REPORT or f.digest(diagpath)!=s.PAIR_REPORT or f.digest(a.review)!=UNION_REVIEW:raise ValueError('Unreviewed frozen cohort/theorem')
    small=json.loads(smallpath.read_text());base=json.loads(basepath.read_text());diag=json.loads(diagpath.read_text());pairs=diag['closest_opposite_plane_pairs']
    if len(pairs)!=20 or len(small['per_camera'])!=129 or len(base['selected_faces'])!=512:raise ValueError('Fixed cohort changed')
    if f.digest(a.r6/'report.json')!=f.REPORT_SHA:raise ValueError('R6 source changed')
    prior=json.loads((a.r6/'report.json').read_text());prep=a.r6/'prepared/prepare-receipt.json'
    if f.digest(prep)!=prior['prepared_receipt']['sha256']:raise ValueError('Original camera receipt changed')
    source=f.audit.bind_source(a.source_tree,a.r6/'current-resolved-knobs.txt')
    for name,pin in base['inputs'].items():
        if f.digest(Path(pin['path']))!=pin['sha256']:raise ValueError('Exact source input changed')
    root=Path(base['inputs']['ps2-world.r4pw']['path']).parent;p=f.Pkg(root/'ps2-world.re4mesh',root/'ps2-world.r4pw');policy=(root/'ps2-world.r4pw').read_bytes()
    materials,_=f.material_census(a.source_tree,Path(base['material']['pack']['path']),p)
    currentfaces,targets,census=f.collect(p,policy,(root/'ps2-world.ids').read_bytes()[16:16+len(p.placements)],materials)
    if census!=base['census']:raise ValueError('Current material/ownership/allLOD prerequisites changed')
    faces=base['selected_faces']
    # JSON grid rows are lists; canonical tuple conversion keeps exact integers.
    available={(x['placement'],x['part'],x['cluster'],x['meshlet'],tuple(x['corners']),tuple(map(tuple,x['grid']))) for x in currentfaces}
    frames,weights,logs=s.raw_cameras(json.loads(prep.read_text()),prior,a.r6)
    if [(x['label'],x['frame'],x['view_bits'],[str(v) for v in x['eye']]) for x in frames]!=[(x['label'],x['frame'],x['view_bits'],x['eye_exact']) for x in small['per_camera']]:raise ValueError('Authentic retained eye mismatch')
    domains=f.cells(a.base_evidence/'preserved-control.pvs',p);domainmap={x['cell']:x for x in domains}
    panels=[];byseed=collections.defaultdict(list);refused=[]
    for si in sorted({q['source'] for q in pairs}):
        face=faces[si];key=(face['placement'],face['part'],face['cluster'],face['meshlet'],tuple(face['corners']),tuple(map(tuple,face['grid'])))
        if key not in available:raise ValueError('Seed not in current stable unconditional descriptor cohort')
        neighbors,reason=panel_neighbors(p,policy,face)
        if reason:refused.append(dict(seed_source=si,reason=reason))
        for neighbor in neighbors:
            panel=dict(face,seed_source=si,triangles=neighbor['triangles'],shared_indices=neighbor['shared'],boundary_indices=neighbor['boundary'],positions=neighbor['positions'],correlated_cache_indices=True)
            byseed[si].append(len(panels));panels.append(panel)
    rows=[dict(label=x['label'],frame=x['frame'],old_cell=old['old_cell'],variants={}) for x,old in zip(frames,small['per_camera'])]
    summaries={}
    for size in (2000,500,250):
        reason=collections.Counter();nominal_count=0;safe_count=0;case_count=0;price_sums=collections.defaultdict(collections.Counter)
        for camera,old,row in zip(frames,small['per_camera'],rows):
            relevant=[q for q in pairs if q['cell']==old['old_cell']];cases=[];box=None
            if relevant:
                box=domainmap[old['old_cell']]['box'] if size==2000 else s.window(camera['eye'],domainmap[old['old_cell']]['box'],size)
                if size!=2000 and [[str(v) for v in q] for q in box]!=old['variants'][str(size)]['box_exact']:raise ValueError('Local complete domain changed')
                for pair in relevant:
                    for panel_id in byseed[pair['source']]:
                        panel=panels[panel_id];target=targets[pair['target']]
                        nominal=prove_union(panel['positions'],panel['triangles'],box,target['box']);case_count+=1
                        if nominal['proven']:nominal_count+=1
                        else:reason[nominal['reason']]+=1
                        safe=prove_union(panel['positions'],panel['triangles'],box,target['box'],vertex_error=32,eye_error=32,target_error=32,eye_clearance=2000,target_clearance=32) if nominal['proven'] else None
                        if safe and safe['proven']:safe_count+=1
                        cases.append(dict(source=panel_id,seed_source=pair['source'],target=pair['target'],nominal=nominal,requested_interval=safe))
            selected=weights[row['label']][row['frame']]
            if len(selected)!=318 or any(r['instance']!=i or any(r[k]!=targets[i][k] for k in ('placement','part','cluster')) for i,r in enumerate(selected)):raise ValueError('Current target selector namespace changed')
            pricing=s.price(cases,selected,targets,panels)
            row['variants'][str(size)]=dict(cases=cases,pricing=pricing,box_exact=None if box is None else [[str(v) for v in q] for q in box],actual_selector_preimage_certified=False)
            for k,v in pricing.items():
                if isinstance(v,int):price_sums[row['label']][k]+=v
        summaries[str(size)]=dict(cases=case_count,exact_nominal_positive_cases=nominal_count,requested_interval_positive_cases=safe_count,refusals=dict(reason),host_corner_sums={k:dict(v) for k,v in price_sums.items()},runtime_admitted=0)
        print(json.dumps(dict(size=size,summary=summaries[str(size)])),flush=True)
    counterfactual=None
    if not any(v['exact_nominal_positive_cases'] for v in summaries.values()):
        previous=diag['existing_meshlet_counterfactuals']
        if len(previous)!=40:raise ValueError('Prior40 meshlet cohort changed')
        records=[];summary={}
        for size in (2000,500,250):
            reasons=collections.Counter();positive=0;safe_positive=0;count=0
            for camera,old in zip(frames,small['per_camera']):
                relevant=[q for q in previous if q['cell']==old['old_cell']]
                if not relevant:continue
                box=domainmap[old['old_cell']]['box'] if size==2000 else s.window(camera['eye'],domainmap[old['old_cell']]['box'],size)
                for q in relevant:
                    target=targets[q['target_cluster_instance']];cl=p.clusters[target['cluster']];lv=q['target_level'];li=q['target_meshlet']
                    first,nm,_=p.levels[cl['first_level']+lv]
                    if not first<=li<first+nm:raise ValueError('Prior meshlet source membership changed')
                    cs,_=p.let_tris(li);world,_=f.mapping(p,target['placement']);points=[world(c[:3]) for c in cs];bbox=(tuple(min(v[k] for v in points) for k in range(3)),tuple(max(v[k] for v in points) for k in range(3)))
                    for panel_id in byseed[q['source']]:
                        panel=panels[panel_id];nominal=prove_union(panel['positions'],panel['triangles'],box,bbox);count+=1
                        if nominal['proven']:positive+=1
                        else:reasons[nominal['reason']]+=1
                        safe=prove_union(panel['positions'],panel['triangles'],box,bbox,vertex_error=32,eye_error=32,target_error=32,eye_clearance=2000,target_clearance=32) if nominal['proven'] else None
                        if safe and safe['proven']:safe_positive+=1
                        selected=weights[camera['label']][camera['frame']][target['instance']]
                        records.append(dict(camera_label=camera['label'],frame=camera['frame'],size=size,source_panel=panel_id,seed_source=q['source'],target_cluster_instance=target['instance'],target_level=lv,target_meshlet=li,authored_corner_records=len(cs),camera_cluster_level_matches=selected['level']==lv,camera_cluster_has_any_selected_corners=selected['corners']>0,nominal=nominal,requested_interval=safe,current_pvs_representable=False,runtime_admitted=False))
            summary[str(size)]=dict(cases=count,exact_nominal_positive_cases=positive,requested_interval_positive_cases=safe_positive,refusals=dict(reasons),runtime_admitted=0)
            print(json.dumps(dict(meshlet_counterfactual_size=size,summary=summary[str(size)])),flush=True)
        counterfactual=dict(kind='Only the exact prior40 authored per-LOD meshlet boxes, unsupported by current PVS target bits',prior_boxes=40,summaries=summary,per_camera_cases=records,actual_cut_corners=None,scope='Authored vertex counts are not per-meshlet selected replay counters. No all-LOD/current target namespace or speed claim.')
    publicpanels=[{k:([[str(v) for v in point] for _,point in sorted(panel['positions'].items())] if k=='positions' else value) for k,value in panel.items()} for panel in panels]
    out=dict(kind='Bounded actual shared-cache-index two-triangle union IDEAL feasibility',tool=f.identity(Path(__file__)),dependencies={p.name:f.identity(p) for p in [Path(__file__).with_name(n) for n in ('exact_union.py','exact_shadow.py','smaller_domains.py','feasibility.py')]},source=source,theorem_review=f.identity(a.review),base_report=f.identity(basepath),fixed_pairs=f.identity(diagpath),smaller_domains=f.identity(smallpath),authentic_logs=logs,source_faces_fixed=512,pairs_fixed=20,actual_retained_cameras=129,candidate_panels=publicpanels,source_refusals=refused,whole_cluster_summaries=summaries,per_camera=rows,meshlet_counterfactual=counterfactual,ideal_uncertainty=base['ideal_uncertainty'],runtime_admitted_cuts=0,modelled_ms=None,go_1ms=False,limits=dict(address_space_bytes=f.LIMIT,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,jobs=1),limitations=['Same actual indices guarantee a shared IDEAL endpoint variable, not qualified actual shader/cache/raster state.','Same whole meshlet/one-LOD/owner/material and exact parity triples retained; no welded position, plane flattening or convex-hull fill.','Current cull side/near/far/actual kernel-transform-clip identity/material/numeric/committed-prefix receipts and raster seam/depth coverage remain unclosed.','Requested32mm interval geometry is not a universal SH4/raster bound. Selector preimage and true eye error remain unproved.','Current whole-cluster corner weights are historical baked-pose host replay, not current runtime counters. One-source price is one actual two-triangle panel; nominal unions may require an unconstructed multi-panel certificate.','No table, runtime/data/target partition, SDK, guest, media, converter or actor change. Prefer small local fallback windows; full grid allocation is unapproved.'])
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as dst:json.dump(out,dst,indent=1);dst.write('\n')
    print(json.dumps(dict(candidate_panels=len(panels),source_refusals=refused,limits=out['limits'],runtime_admitted=0,modelled_ms=None)))

if __name__=='__main__':main()
