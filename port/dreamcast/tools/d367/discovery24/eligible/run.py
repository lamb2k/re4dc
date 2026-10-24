#!/usr/bin/env python3
"""CURRENT_HOST_REPLAY eligible earlier-source hints; never a certificate."""
import argparse,collections,hashlib,json,os,resource,sys,time,gc,struct
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path[:0]=[str(HERE),str(HERE.parent)]
import rank
from rays import discover
from pool import EligibleScene,source_allowed
from ledger import Ledger
import selection,runtime,subprocess
LIMIT=256*1024*1024;OUTPUT_CAP=16*1024*1024;FINAL_METADATA_RESERVE=64*1024

def output_budget(existing,report_size):
    if existing+report_size+FINAL_METADATA_RESERVE>OUTPUT_CAP:raise ValueError('Entire unit output cap incl64KiB final log/receipt reserve')


def audit_union(rows):
    keys=set();levels={};total=0
    for row in rows:
        t=row['target'];key=(t['instance'],t['level'],t['meshlet'])
        if key in keys or (t['instance'] in levels and levels[t['instance']]!=t['level']):raise ValueError('Duplicate tuple or alternative LOD counted in one view')
        keys.add(key);levels[t['instance']]=t['level'];total+=t['host_corner_records']
    return total

def patch_associations(pid,source,cases):
    keys=('instance','level','meshlet')
    alone=[x for x in cases if x['sampled_patch_hit_counts'].get(pid,0)==x['sample_count']]
    return dict(patch_id=pid,source=source,
        associated_target_tuples=[[x['target'][k] for k in keys] for x in cases],
        associated_target_corner_records_union=audit_union(cases),
        patch_sample_hits_by_target=[dict(target_tuple=[x['target'][k] for k in keys],patch_samples_hit=x['sampled_patch_hit_counts'].get(pid,0),target_samples=x['sample_count']) for x in cases],
        alone_all_fixed_samples_target_tuples=[[x['target'][k] for k in keys] for x in alone],
        alone_all_fixed_samples_corner_records_union=audit_union(alone),
        warning='Associated/touched target work only, not work hidden by this patch. Even single-patch all-sample hits are NO_CERTIFICATE. Groups overlap; never add group totals.')

def source_record(t,level,li,pkg,materials,policy,conditional):
    m=pkg.pmeta[t['part']];_,det=rank.f.mapping(pkg,t['placement'])
    s={k:t[k] for k in ('placement','field','owner','part','cluster')};s.update(level=level,meshlet=li,level_count=t['level_count'])
    s['prerequisites']=dict(static=t['static'],unconditional=t['field'] not in conditional,nonsingular=det!=0,level_count=t['level_count'],pass_=m['pass_'],cull=m['cull'],vertex_alpha=bool(policy[32+t['part']*16+15]&1),material_eligible=materials[t['part']]['eligible']);s['prerequisites']['pass']=s['prerequisites'].pop('pass_')
    return s

def main():
    resource.setrlimit(resource.RLIMIT_AS,(LIMIT,LIMIT))
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-tree',required=True,type=Path);ap.add_argument('--source-commit',required=True);ap.add_argument('--r6',required=True,type=Path);ap.add_argument('--prior-report',required=True,type=Path);ap.add_argument('--runtime-pin',required=True,type=Path);ap.add_argument('--ledger',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    if a.out.parent.resolve()!=a.ledger.parent.resolve() or a.out.is_relative_to(a.source_tree):raise ValueError('Exclusive evidence output must share the existing tranche ledger parent outside source')
    a.out.mkdir(exist_ok=False);start=time.monotonic();
    if not HERE.is_relative_to(a.source_tree.resolve()):raise ValueError('Tool must belong to bound source checkout')
    git=lambda *args:subprocess.check_output(['git','-C',str(a.source_tree),'-c','index.threads=1','-c','core.preloadIndex=false',*args],text=True)
    if git('rev-parse','HEAD').strip()!=a.source_commit or git('status','--porcelain'):raise ValueError('Clean exact frozen source checkpoint required')
    actual_runtime=runtime.snapshot()
    if actual_runtime!=json.loads(a.runtime_pin.read_text()):raise ValueError('Host executable/NumPy/provider/floating-control drift')
    f=rank.f
    if f.digest(a.prior_report)!='f153b9a467a1c653346b1955868164453a36a847d81df67bc4f05a2edb058964':raise ValueError('Saved full-scene report pin')
    prior_report=json.loads(a.prior_report.read_text());r=a.r6
    if f.digest(r/'report.json')!=f.REPORT_SHA:raise ValueError('Frozen R6 report pin')
    prior=json.loads((r/'report.json').read_text());receipt=r/'prepared/prepare-receipt.json'
    if f.digest(receipt)!=prior['prepared_receipt']['sha256']:raise ValueError('Prepared inputs pin')
    source=f.audit.bind_source(a.source_tree,r/'current-resolved-knobs.txt');inputs=r/'prepared/inputs'
    for name,pin in f.audit.FROZEN_INPUT_SHA256.items():
        if f.digest(inputs/name)!=pin:raise ValueError('Frozen input '+name)
    stage=json.loads((r/'current-staging-plan.json').read_text());pkg=f.Pkg(inputs/'ps2-world.re4mesh',inputs/'ps2-world.r4pw');policy=(inputs/'ps2-world.r4pw').read_bytes();ids=(inputs/'ps2-world.ids').read_bytes()
    original=f.Pkg(inputs/'ps2-world.re4mesh',inputs/'original.r4pw')
    if original.placements!=pkg.placements or struct.unpack_from('<4sIII',ids)!=(b'R4ID',1,len(pkg.placements),original.sidecar_crc):raise ValueError('Original physical placement identity')
    for name in ('ps2-world.re4mesh','ps2-world.r4pw','ps2-world.ids'):
        if f.digest(Path(stage['replace']['dc/native/r10d/'+name]))!=f.digest(inputs/name):raise ValueError('Current staged source identity')
    materials,materialpins=f.material_census(a.source_tree,Path(stage['replace']['dc/tex.pak']),pkg)
    targets=rank.inventory(pkg,policy,ids[16:16+len(pkg.placements)],materials);conditional=f.audit.conditional_fields(ids[16:16+len(pkg.placements)])
    frames,weights,logs=rank.raw_cameras(json.loads(receipt.read_text()),prior,r);cameras=[c for c in frames if c['frame']==647]
    if [c['label'] for c in cameras]!=['hut','turn','walk']:raise ValueError('Exact three authentic views')
    rm,dm=selection.load();numeric_pkg=dm.Pkg(inputs/'ps2-world.re4mesh',inputs/'ps2-world.r4pw');contexts=[];planned=0
    for camera in cameras:
        current=selection.select(rm,numeric_pkg,camera,weights[camera['label']][647]);rank.validate_selection(pkg,targets,current);roster=[]
        for t,row in zip(targets,current):
            if row['level']<0:continue
            cl=pkg.clusters[t['cluster']];fm,nm,_=pkg.levels[cl['first_level']+row['level']]
            if any(not fm<=li<fm+nm for li in row['selected_meshlet_ids']):raise ValueError('Current replay exact selected-let membership')
            if not t['static'] or not t['ordinary']:continue
            world=rank.transform(pkg,t['placement'])
            for li in row['selected_meshlet_ids']:
                cs,_=pkg.let_tris(li)
                roster.append(dict(**{k:t[k] for k in ('instance','placement','field','owner','part','cluster')},level=row['level'],meshlet=li,host_corner_records=pkg.lets[li]['vc'],box=rank.box_of(cs,world),selected_strip_groups=None,group_policy='FROZEN_REPLAY_HAS_NO_SG_SELECTION; whole authored let pre-SG ceiling'))
        audit_union([dict(target=t) for t in roster]);planned+=27*len(roster);contexts.append((camera,current,roster))
    token=Ledger(a.ledger).reserve(planned,'full eligible discovery planned rays; no refund on failure/rerun')
    output=dict(classification='NO_CERTIFICATE',source_descriptor_prerequisites_only=True,unknown_renderer_obligations=['actual source side/winding','near/clip acceptance','material/depth/header commits','numeric/raster coverage','accepted source-prefix receipt'],schema='ELIGIBLE24_CURRENT_HOST_REPLAY_HINTS_V1',selection_label='CURRENT_HOST_REPLAY',historical_individual_let_or_group_identity=False,counts_and_lod_equality='Exact318-row old R6 equality is consistency only',source=source,inputs={n:f.identity(inputs/n) for n in f.audit.FROZEN_INPUT_SHA256},material_pins=materialpins,material_parts=materials,host_runtime=actual_runtime,authentic_camera_logs=logs,original_report=f.identity(a.prior_report),command=sys.argv,thread_policy='one worker and one numeric thread',source_pool='Complete current-host-selected static/unconditional nonsingular singleLOD pass0 intrinsic-opaque source lets, cull0/2, no vertex-alpha; strictly earlier placement enforced during BVH traversal',target_scope='Exact current-host-selected effective whole meshlets of unconditional/static ordinary target instances; no selected-group or guest-emission claim',certificate=None,runtime_admitted=False,gain_ms=None,views=[])
    for camera,current,roster in contexts:
        scene=EligibleScene(token);source_roster=[]
        for t,row in zip(targets,current):
            if row['level']<0:continue
            world=rank.transform(pkg,t['placement'])
            for li in row['selected_meshlet_ids']:
                s=source_record(t,row['level'],li,pkg,materials,policy,conditional)
                if not source_allowed(s):scene.refused+=1;continue
                cs,ts=pkg.let_tris(li);scene.add_source(s,[world(c) for c in cs],ts);source_roster.append(s)
        old=next(c for c in prior_report['cameras'] if c['camera']['label']==camera['label']);whole_old={x['target']['instance'] for x in old['ranked_targets'] if x['kind']=='whole_cluster' and x['prefix_only']['all_fixed_samples_hit']};whole_any={x['target']['instance'] for x in old['ranked_targets'] if x['kind']=='whole_cluster' and x['all_fixed_samples_hit']}
        if scene.patch:scene.build()
        rows=[];used=set()
        for target in roster:
            if scene.patch:
                result=discover(scene,[float(v) for v in camera['eye']],target['box'],exclude_cluster=(target['placement'],target['cluster']),source_before=target['placement'])
            else:
                token.take();raise ValueError('Empty eligible source scene: retain reserved failure, do not manufacture hits')
            refs=sorted({x['hit']['triangle'] for x in result['rays'] if x['hit']});result['hit_sources']={str(i):scene.provenance(i) for i in refs};used.update(int(pid) for pid in result['sampled_patch_hit_counts'])
            if any(x['placement']>=target['placement'] or (x['placement'],x['cluster'])==(target['placement'],target['cluster']) for x in result['hit_sources'].values()):raise ValueError('Traversal prefix/own-instance exclusion')
            result['rays']=[[x['kind'],None if not x['hit'] else [x['hit'][k] for k in ('triangle','patch','t','distance_mm','source_edge_contact','facing_sign')]] for x in result['rays']];result['target']=target;result['outside_old_prefix_wholecluster_hint']=target['instance'] not in whole_old;result['outside_old_any_wholecluster_hint']=target['instance'] not in whole_any
            rows.append(result)
        positives=[x for x in rows if x['all_fixed_samples_hit']];incremental=[x for x in positives if x['outside_old_prefix_wholecluster_hint']];patches={}
        for pid in sorted(used):
            q=dict(scene.patches[pid]);members=q.pop('triangles');q['component_triangles']=[[scene.provenance(i)[k] for k in ('triangle','i0','i1','i2')] for i in members];q['triangle_columns']=['ordinal','i0','i1','i2'];q['triangle_count']=len(members);patches[str(pid)]=q
        groups=[]
        for pid,q in patches.items():
            cases=[x for x in incremental if pid in {str(k) for k in x['sampled_patch_hit_counts']}]
            if cases:groups.append(patch_associations(int(pid),q['source'],cases))
        rows.sort(key=lambda x:(-int(x['all_fixed_samples_hit'] and x['outside_old_prefix_wholecluster_hint']),-x['target']['host_corner_records'],-x['usable_hit_count'],x['target']['instance'],x['target']['meshlet']))
        output['views'].append(dict(camera={k:v for k,v in camera.items() if k!='eye'},eye_exact=[str(v) for v in camera['eye']],target_roster=roster,source_roster=source_roster,source_triangles=len(scene.patch),source_patches=len(scene.patches),filtered_source_lets=scene.refused,ray_queries=scene.rays,all_sample_hit_lets=len(positives),all_hit_nonoverlap_corner_ceiling=audit_union(positives),incremental_lets_beyond_old_wholecluster_hints=len(incremental),incremental_nonoverlap_corner_ceiling=audit_union(incremental),ranked_lets=rows,patches=patches,common_source_groups=groups));gc.collect();print(json.dumps(dict(view=camera['label'],selected_targets=len(roster),eligible_triangles=len(scene.patch),hints=len(positives),incremental_hints=len(incremental),incremental_corners=audit_union(incremental))),flush=True)
    if token.used!=sum(v['ray_queries'] for v in output['views']):raise ValueError('Global ray query accounting mismatch')
    output['limits']=dict(address_cap_bytes=LIMIT,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,ray_reserved_this_run=planned,ray_queries_used=token.used,ledger=json.loads(a.ledger.read_text()),seconds=time.monotonic()-start,maximum_unit_output_bytes=OUTPUT_CAP,final_log_metadata_reserved_bytes=FINAL_METADATA_RESERVE)
    output['tool_pins']={str(p.relative_to(a.source_tree)):f.identity(p) for p in sorted(HERE.glob('*.py'))};output['parent_tool_pins']={p.name:f.identity(p) for p in (HERE.parent/'rank.py',HERE.parent/'rays.py',Path(rank.f.__file__),Path(rank.f.audit.__file__),HERE.parent.parent/'interior_vis23/surface_mesh.py',HERE.parent.parent/'interior_vis23/triangle_shadow_next/smaller_domains.py',HERE.parent.parent/'interior_vis23/triangle_shadow_next/exact_shadow.py')}
    data=(json.dumps(output,separators=(',',':'))+'\n').encode();existing=sum(p.stat().st_size for p in a.out.parent.rglob('*') if p.is_file())
    output_budget(existing,len(data))
    with (a.out/'report.json').open('xb') as f:f.write(data)
    print(json.dumps(dict(status='NO_CERTIFICATE',report=rank.f.identity(a.out/'report.json'),limits=output['limits'])),flush=True)
if __name__=='__main__':main()
