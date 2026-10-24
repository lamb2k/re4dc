#!/usr/bin/env python3
"""Explain the preserved bounded search; never broaden its source-face cohort.

Float refusal categories/ranks are heuristic diagnostics, NOT exact negative
certificates. Recheck the 20 closest opposite-plane pairs with exact arithmetic.
Inspect their existing per-LOD meshlets only as unsupported target counterfactuals.
"""
import argparse
import collections
import heapq
import json
import math
import resource
import statistics
from fractions import Fraction as Q
from pathlib import Path
from itertools import product
import feasibility as f
from exact_shadow import cross, dot, sub, prove


def classify(tri,eye,target):
    a,b,c=tri;n=cross(sub(b,a),sub(c,a));es=tuple(product(*zip(*eye)))
    def extent(k,origin,box):
        lo,hi=box
        base=sum(k[j]*(lo[j]-origin[j]) for j in range(3));d=[k[j]*(hi[j]-lo[j]) for j in range(3)]
        return base+sum(min(0,x) for x in d),base+sum(max(0,x) for x in d)
    ee=extent(n,a,eye)
    if ee[0]>0:sigma=1
    elif ee[1]<0:sigma=-1
    else:return 'eye_plane_crossing_or_contact',None
    n=tuple(sigma*x for x in n);tt=extent(n,a,target)
    if tt[1]>=0:return 'target_not_strictly_opposite_plane',None
    # All deltas positive. Normalize edge lower bounds only for ranking; this
    # is not a certified barycentric minimum and may reorder close candidates.
    maxdelta=max(sigma*ee[0],sigma*ee[1])-tt[0]
    edge_min=float('inf')
    for u,v in ((a,b),(b,c),(c,a)):
        for e in es:
            k=tuple(sigma*x for x in cross(sub(e,u),sub(v,u)))
            edge_min=min(edge_min,extent(k,u,target)[0])
    score=edge_min/maxdelta
    return ('triangle_edge_coverage' if edge_min<=0 else 'float_candidate'),score


def box_stats(targets):
    dimensions=[tuple(float(b-a) for a,b in zip(*t['box'])) for t in targets]
    diag=[math.sqrt(sum(d*d for d in ds)) for ds in dimensions]
    return dict(count=len(targets),axis_mm={axis:dict(min=min(d[k] for d in dimensions),median=statistics.median(d[k] for d in dimensions),max=max(d[k] for d in dimensions)) for k,axis in enumerate(('x','y','z'))},diagonal_mm=dict(min=min(diag),median=statistics.median(diag),max=max(diag)),smallest=[dict(instance=t['instance'],placement=t['placement'],part=t['part'],cluster=t['cluster'],level_count=t['level_count'],dimensions_mm=dimensions[i],diagonal_mm=diag[i]) for i,t in sorted(enumerate(targets),key=lambda z:diag[z[0]])[:20]])


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--report',type=Path,required=True);ap.add_argument('--source-tree',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.out.exists():raise ValueError('Preserve old diagnostics')
    resource.setrlimit(resource.RLIMIT_AS,(f.LIMIT,f.LIMIT))
    report=json.loads(a.report.read_text());faces=report['selected_faces']
    if len(faces)!=512 or report['domains']!=19 or report['exact_attempts']!=0:raise ValueError('Expected frozen bounded512 zero-accepted search')
    profile=Path(report['source']['profile']['path']);source=f.audit.bind_source(a.source_tree,profile)
    for name,pin in report['inputs'].items():
        if f.digest(Path(pin['path']))!=pin['sha256']:raise ValueError('Input changed')
    root=Path(report['inputs']['ps2-world.r4pw']['path']).parent
    p=f.Pkg(root/'ps2-world.re4mesh',root/'ps2-world.r4pw');policy=(root/'ps2-world.r4pw').read_bytes();ids=(root/'ps2-world.ids').read_bytes()
    materials,_=f.material_census(a.source_tree,Path(report['material']['pack']['path']),p)
    _,targets,census=f.collect(p,policy,ids[16:16+len(p.placements)],materials)
    if census!=report['census']:raise ValueError('Census changed')
    domains=f.cells(Path(report['control_cells']['path']),p);domainmap={d['cell']:d for d in domains}
    eligible=[t for t in targets if t['static'] and t['ordinary'] and 'box' in t];targetmap={t['instance']:t for t in eligible}
    counts=collections.Counter();closest=[];tested=0
    for si,face in enumerate(faces):
        world,_=f.mapping(p,face['placement']);tri=tuple(tuple(float(x) for x in world(q)) for q in face['grid'])
        for d in domains:
            for t in eligible:
                if t['placement']==face['placement'] and t['cluster']==face['cluster']:continue
                category,score=classify(tri,d['box_float'],t['box_float']);counts[category]+=1;tested+=1
                if score is not None:
                    item=(score,si,d['cell'],t['instance'])
                    if len(closest)<20:heapq.heappush(closest,item)
                    elif item>closest[0]:heapq.heapreplace(closest,item)
        if (si+1)%64==0:print(json.dumps(dict(diagnostic_faces=si+1,total=512)),flush=True)
    if tested!=report['pair_tests']:raise ValueError('Search cohort changed')
    ranked=[];meshlet_tests=[]
    for score,si,cell,target in sorted(closest,reverse=True):
        face=faces[si];t=targetmap[target];d=domainmap[cell];world,_=f.mapping(p,face['placement']);tri=tuple(world(q) for q in face['grid'])
        proof=prove(tri,d['box'],t['box'])
        ranked.append(dict(source=si,cell=cell,target=target,heuristic_edge_score=score,exact_nominal=proof,target_dimensions_mm=[float(b-a) for a,b in zip(*t['box'])],single_lod=face['level_count']==1,prefix=t['placement']>face['placement']))
        targetworld,_=f.mapping(p,t['placement']);cl=p.clusters[t['cluster']]
        counts_l=[p.levels[cl['first_level']+lv][1] for lv in range(cl['level_count'])]
        for lv in f.audit.selectable(counts_l):
            first,nm,_=p.levels[cl['first_level']+lv]
            for li in range(first,first+nm):
                cs,_=p.let_tris(li);wc=[targetworld(c[:3]) for c in cs]
                if not wc:continue
                box=(tuple(min(q[k] for q in wc) for k in range(3)),tuple(max(q[k] for q in wc) for k in range(3)))
                exact=prove(tri,d['box'],box)
                safe=prove(tri,d['box'],box,vertex_error=32,eye_error=32,target_error=32,eye_clearance=2000,target_clearance=32) if exact['proven'] else None
                meshlet_tests.append(dict(source=si,cell=cell,target_cluster_instance=target,target_level=lv,target_meshlet=li,vertices=len(cs),dimensions_mm=[float(b-a) for a,b in zip(*box)],nominal=exact,requested_interval=safe,current_pvs_representable=False,renderer_admitted=False))
    static=a.source_tree/'port/dreamcast/game/platform/native_static.cpp'
    text=static.read_text();snippets={}
    for label,needle in [('per_part_first_instance','const std::uint16_t* base=nullptr;'),('cluster_bit','pvs_cur')]:
        hits=[dict(line=i+1,text=line.strip()) for i,line in enumerate(text.splitlines()) if needle in line]
        snippets[label]=hits
    out=dict(kind='Same bounded512 cohort refusal diagnostics and closest existing per-LOD meshlet counterfactuals',tool=f.identity(Path(__file__)),input=f.identity(a.report),source=source,float_diagnostic_categories=dict(counts),category_scope='Heuristic float refusal categories only, never exact exclusion of all tested pairs; no no-false-negative prefilter claim.',tested_pairs=tested,target_cluster_box_sizes=box_stats(eligible),closest_opposite_plane_pairs=ranked,exact_ranked_pairs_proven=sum(x['exact_nominal']['proven'] for x in ranked),existing_meshlet_counterfactuals=meshlet_tests,existing_meshlet_nominal_proofs=sum(x['nominal']['proven'] for x in meshlet_tests),existing_meshlet_requested_interval_proofs=sum(bool(x['requested_interval'] and x['requested_interval']['proven']) for x in meshlet_tests),current_runtime_scope=dict(static_source=f.identity(static),source_snippets=snippets,smallest_existing_PVS_target='placement-owned cluster instance bit, shared across source LOD choices',existing_per_lod_meshlet_bits=False,new_partition_approved=False),unclosed_stages=dict(uncertainty='Only evaluated after exact nominal positives; requested perturbations are not renderer error proof.',near='No current full-cell clipping receipt.',raster='No edge/sample/depth conservatism proof.',runtime='No actual source cull/material/numeric/emission/prefix/16-panel receipt admission.'),renderer_admitted=0,modelled_ms=None,go_1ms=False,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,limits=dict(rlimit_as_bytes=f.LIMIT,jobs=1),scope='No larger source search, no converter/renderer/data changes, no table emitted. Per-LOD meshlet positives, if any, do not establish an all-LOD or runtime target contract.')
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as dst:json.dump(out,dst,indent=1);dst.write('\n')
    print(json.dumps({k:out[k] for k in ('float_diagnostic_categories','tested_pairs','exact_ranked_pairs_proven','existing_meshlet_nominal_proofs','existing_meshlet_requested_interval_proofs','peak_rss_kib')}))

if __name__=='__main__':main()
