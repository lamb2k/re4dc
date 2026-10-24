#!/usr/bin/env python3
"""Authenticated point-eye discovery, never an occlusion certificate or admission."""
import argparse, collections, gc, hashlib, json, os, resource, struct, sys, time
from itertools import product
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent/'interior_vis23/triangle_shadow_next'),str(HERE.parent/'interior_vis23')]
import feasibility as f
from smaller_domains import raw_cameras
from rays import Scene, discover, MAX_RAYS
BASE='721dff3ec91941516d30898d5f60836a450d09f8'
MAX_OUTPUT=16*1024*1024


def transform(pkg,pi):
    pl=pkg.placements[pi];mesh=pkg.meshes[pl['mesh']];a=pl['affine'];o=mesh['origin'];s=mesh['step']
    def world(q):
        x=[o[k]+s[k]*int(q[k]) for k in range(3)]
        return tuple(sum(a[i][k]*x[k] for k in range(3))+a[i][3] for i in range(3))
    return world


def box_of(corners,world):
    if not corners:raise ValueError('Empty target corners')
    lo=[min(c[k] for c in corners) for k in range(3)];hi=[max(c[k] for c in corners) for k in range(3)]
    points=[world(q) for q in product(*zip(lo,hi))]
    return [[min(q[k] for q in points) for k in range(3)],[max(q[k] for q in points) for k in range(3)]]


def inventory(pkg,policy,ids,materials):
    conditional=f.audit.conditional_fields(ids);out=[]
    for pi,pl in enumerate(pkg.placements):
        mesh=pkg.meshes[pl['mesh']];world=transform(pkg,pi);_,det=f.mapping(pkg,pi)
        static=pl['placement'] not in conditional and det!=0
        for part in range(mesh['first_part'],mesh['first_part']+mesh['part_count']):
            meta=pkg.pmeta[part];fc,nc=pkg.plod[part]
            eligible=bool(static and materials[part]['eligible'] and meta['pass_']==0 and not(policy[32+part*16+15]&1) and meta['cull'] in (0,2))
            for ci in range(fc,fc+nc):
                cl=pkg.clusters[ci];allcorners=[];counts=[]
                for lv in range(cl['level_count']):
                    fm,nm,_=pkg.levels[cl['first_level']+lv];counts.append(nm)
                    for li in range(fm,fm+nm):allcorners.extend(pkg.let_tris(li)[0])
                out.append(dict(instance=len(out),placement=pi,field=pl['placement'],owner=ids[pl['placement']],part=part,cluster=ci,
                    static=static,ordinary=meta['pass_']==0,source_eligible=eligible,selectable=f.audit.selectable(counts),
                    box=None if not allcorners else box_of(allcorners,world),level_count=cl['level_count']))
    return out


def validate_selection(pkg,targets,selected):
    if len(selected)!=len(targets):raise ValueError('Replay namespace cardinality')
    for t,row in zip(targets,selected):
        if any(t[k]!=row[k] for k in ('instance','placement','part','cluster')):raise ValueError('Replay target namespace')
        lv=row['level']
        if type(lv)is not int or lv < -1 or (lv>=0 and lv not in t['selectable']):raise ValueError('Unproven selected LOD')
        if lv>=0:
            cl=pkg.clusters[t['cluster']];fm,nm,_=pkg.levels[cl['first_level']+lv]
            if type(row['meshlets'])is not int or not 0<=row['meshlets']<=nm:raise ValueError('Replay clipped meshlet count extent')


def run_camera(pkg,targets,selected,eye,budget):
    validate_selection(pkg,targets,selected);scene=Scene();let_targets=[];source_counts=collections.Counter()
    for t,row in zip(targets,selected):
        lv=row['level']
        if lv<0:continue
        cl=pkg.clusters[t['cluster']];fm,nm,_=pkg.levels[cl['first_level']+lv];world=transform(pkg,t['placement'])
        for li in range(fm,fm+nm):
            cs,ts=pkg.let_tris(li)
            if t['static'] and t['ordinary'] and cs:
                let_targets.append(dict(**{k:t[k] for k in ('instance','placement','field','owner','part','cluster')},level=lv,meshlet=li,box=box_of(cs,world),
                    namespace='counterfactual whole meshlet; unsupported by current cluster PVS namespace'))
            if t['source_eligible']:
                src={k:t[k] for k in ('placement','field','owner','part','cluster')};src.update(level=lv,meshlet=li,level_count=cl['level_count'],source_cull=pkg.pmeta[t['part']]['cull'])
                before=len(scene.patch);scene.add_let(src,[world(c) for c in cs],ts);source_counts[t['placement']]+=len(scene.patch)-before
    whole=[dict(t,level=row['level'],historical_replay_meshlets=row['meshlets'],historical_replay_corners=row.get('corners'),authored_selected_level_meshlets=pkg.levels[pkg.clusters[t['cluster']]['first_level']+row['level']][1]) for t,row in zip(targets,selected) if t['static'] and t['ordinary'] and t['box'] is not None and row['level']>=0]
    required=sum(len(__import__('rays').samples(t['box'])) for t in whole+whole+let_targets)
    if budget+required>MAX_RAYS:raise ValueError('Full requested target inventory exceeds global110k rays; no truncation')
    scene.build();results=[]
    for kind,group in (('whole_cluster',whole),('counterfactual_meshlet',let_targets)):
        for t in group:
            excluded=dict(exclude_cluster=(t['placement'],t['cluster'])) if kind=='whole_cluster' else dict(exclude_meshlet=(t['placement'],t['cluster'],t['meshlet']))
            result=discover(scene,eye,t['box'],**excluded)
            def encode_hits(item):
                refs=sorted({r['hit']['triangle'] for r in item['rays'] if r['hit']})
                item['hit_source_refs']={str(i):scene.provenance(i) for i in refs}
                item['rays']=[[r['kind'],None if not r['hit'] else [r['hit'][k] for k in ('triangle','patch','t','distance_mm','source_edge_contact','facing_sign')]] for r in item['rays']]
                return refs
            refs=encode_hits(result)
            if kind=='whole_cluster':
                prefix=discover(scene,eye,t['box'],source_before=t['placement'],**excluded)
                encode_hits(prefix)
                prefix['source_filter']='strictly earlier physical placement only; actual renderer prefix receipts still unknown'
                result['prefix_only']=prefix
            result['target']=t;result['kind']=kind
            result['source_prefix_order']=all(scene.provenance(i)['placement']<t['placement'] for i in refs) if refs else None
            result['blockers']=['Finite point samples do not prove full-domain coverage','Actual material/header/depth/near/far/raster/strip emission receipts absent','Historical host replay LOD is not actual played LOD; all-LOD stability unknown','Full authored selected-LOD envelope includes unproven clipped meshlets; near/clip/cull/renderer survival unknown','Placement order is only a prerequisite; actual committed renderer source-prefix receipt unknown']
            if result['source_prefix_order'] is not True:result['blockers'].append('Current source prefix order not established')
            if kind!='whole_cluster':result['blockers'].append('Current namespace does not support this target let')
            results.append(result)
    results.sort(key=lambda r:(-int(r.get('prefix_only',{}).get('all_fixed_samples_hit',False)),-r.get('prefix_only',{}).get('usable_hit_count',0),-int(r['all_fixed_samples_hit']),-r['usable_hit_count']/r['sample_count'],-r['dominant_patch_hits'],r['target']['instance'],r['kind'],r['target'].get('meshlet',-1)))
    used={int(k) for row in results for item in (row,row.get('prefix_only',{})) for k in item.get('sampled_patch_hit_counts',{})}
    patches={}
    for pid in sorted(used):
        patch=dict(scene.patches[pid]);members=patch.pop('triangles')
        patch['triangles_count']=len(members)
        patch['actual_component_triangles']=[[scene.provenance(i)[k] for k in ('triangle','i0','i1','i2')] for i in members]
        patch['component_triangle_columns']=['source_triangle_ordinal','i0','i1','i2']
        patches[str(pid)]=patch
    summary=dict(source_triangles=len(scene.patch),source_degenerates=scene.degenerate,connected_patches=len(scene.patches),source_placements=dict(source_counts),
        whole_cluster_targets=len(whole),counterfactual_meshlet_targets=len(let_targets),rays=scene.rays,
        prefix_only_all_sample_hit_clusters=sum(r.get('prefix_only',{}).get('all_fixed_samples_hit',False) for r in results),
        prefix_only_rays=sum(r.get('prefix_only',{}).get('sample_count',0) for r in results),
        all_sample_hit_clusters=sum(r['all_fixed_samples_hit'] for r in results if r['kind']=='whole_cluster'),
        all_sample_hit_lets=sum(r['all_fixed_samples_hit'] for r in results if r['kind']!='whole_cluster'))
    return dict(summary=summary,patches=patches,ranked_targets=results),budget+scene.rays


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-tree',type=Path,required=True);ap.add_argument('--r6',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    resource.setrlimit(resource.RLIMIT_AS,(f.LIMIT,f.LIMIT))
    if a.out.exists() or a.out.is_relative_to(a.source_tree):raise ValueError('Exclusive private output outside source required')
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        if os.environ.get(key)!='1':raise ValueError('Explicit single numeric thread required: '+key)
    import subprocess
    if subprocess.check_output(['git','-C',str(a.source_tree),'merge-base','HEAD',BASE],text=True).strip()!=BASE:raise ValueError('Frozen source ancestry')
    r=a.r6
    if f.digest(r/'report.json')!=f.REPORT_SHA:raise ValueError('R6 report pin')
    prior=json.loads((r/'report.json').read_text());receipt=r/'prepared/prepare-receipt.json'
    if f.digest(receipt)!=prior['prepared_receipt']['sha256']:raise ValueError('Prepared receipt pin')
    prep=json.loads(receipt.read_text());source=f.audit.bind_source(a.source_tree,r/'current-resolved-knobs.txt')
    inputs=r/'prepared/inputs'
    for name,pin in f.audit.FROZEN_INPUT_SHA256.items():
        if f.digest(inputs/name)!=pin:raise ValueError('Frozen source input '+name)
    stage=json.loads((r/'current-staging-plan.json').read_text());pkg=f.Pkg(inputs/'ps2-world.re4mesh',inputs/'ps2-world.r4pw');policy=(inputs/'ps2-world.r4pw').read_bytes();ids=(inputs/'ps2-world.ids').read_bytes()
    original=f.Pkg(inputs/'ps2-world.re4mesh',inputs/'original.r4pw')
    if struct.unpack_from('<4sIII',ids)!=(b'R4ID',1,len(pkg.placements),original.sidecar_crc) or original.placements!=pkg.placements:raise ValueError('Physical ownership/affine binding')
    for name in ('ps2-world.re4mesh','ps2-world.r4pw','ps2-world.ids'):
        if f.digest(Path(stage['replace']['dc/native/r10d/'+name]))!=f.digest(inputs/name):raise ValueError('Current staged input binding')
    materials,mpins=f.material_census(a.source_tree,Path(stage['replace']['dc/tex.pak']),pkg)
    targets=inventory(pkg,policy,ids[16:16+len(pkg.placements)],materials)
    frames,weights,logs=raw_cameras(prep,prior,r);chosen=[q for q in frames if q['frame']==647]
    if [q['label'] for q in chosen]!=['hut','turn','walk']:raise ValueError('Exact three camera eyes required')
    out=dict(schema='DISCOVERY24_HINTS_ONLY_V1',source=source,frozen_source_base=BASE,inputs={name:f.identity(inputs/name) for name in f.audit.FROZEN_INPUT_SHA256},r6_report=f.identity(r/'report.json'),logs=logs,material_pins=mpins,material_parts=materials,physical_part_metadata=pkg.pmeta,
        camera_profile='Historical e9bf7 CAMERA captures:54 requested,55.4-55.8 total wall; no current55child qualification',
        selection='Authenticated R6 current-divisor20 baked-pose host selector replay, not observed playedLOD',
        source_geometry='Full authored selected-LOD envelope of unconditional intrinsic-opaque eligible actual PS2 triangles; direct authenticated LOD, clipped meshlet roster not inferred from aggregate counts; no512face cap; source cull side not reinterpreted',
        projection='Unused; no reconstructed truncated viewport/projection tail',classification='NO_CERTIFICATE',certificate=None,runtime_admitted=False,gain_ms=None,cameras=[])
    budget=0;start=time.monotonic()
    for camera in chosen:
        eye=[float(x) for x in camera['eye']];print(json.dumps(dict(start=camera['label'],frame=647)),flush=True)
        result,budget=run_camera(pkg,targets,weights[camera['label']][647],eye,budget)
        result['camera']={k:v for k,v in camera.items() if k!='eye'};result['camera']['eye_exact']=[str(x) for x in camera['eye']]
        out['cameras'].append(result);gc.collect();print(json.dumps(dict(done=camera['label'],summary=result['summary'])),flush=True)
    out['tool_pins']={str(p.relative_to(a.source_tree)):f.identity(p) for p in (Path(__file__),HERE/'rays.py',Path(f.__file__),Path(f.audit.__file__),HERE.parent/'interior_vis23/surface_mesh.py',HERE.parent/'interior_vis23/triangle_shadow_next/smaller_domains.py',HERE.parent/'interior_vis23/triangle_shadow_next/exact_shadow.py')}
    out['limits']=dict(rlimit_as_bytes=f.LIMIT,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,jobs=1,numeric_threads=1,total_rays=budget,seconds=time.monotonic()-start,maximum_triangles_per_camera=200000,maximum_rays=MAX_RAYS,maximum_output_bytes=MAX_OUTPUT)
    data=(json.dumps(out,separators=(',',':'))+'\n').encode()
    if len(data)>MAX_OUTPUT:raise ValueError('Full report exceeds16MiB; preserve refusal, no truncation')
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('xb') as dest:dest.write(data)
    print(json.dumps(dict(status='DISCOVERY_HINTS_ONLY',output=f.identity(a.out),limits=out['limits'])),flush=True)
if __name__=='__main__':main()
