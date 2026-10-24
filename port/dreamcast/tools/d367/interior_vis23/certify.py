#!/usr/bin/env python3
"""Create/replay an exact paired-panel r10d candidate for the existing guards.

Requires prepare.py private output. Pinned geometric helpers are reused, with
only optional absent texture-descriptor hashing removed: material state still
must qualify through the runtime's actual opaque upload/header predicate.
No captured path or finite-ray visibility is used to clear a bit.
"""
import argparse
import hashlib
import importlib
import json
import math
import struct
import sys
import zlib
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('private',type=Path)
    ap.add_argument('--room',default='10d')
    ap.add_argument('--limit',type=int,default=128)
    ap.add_argument('--conditional-sources',action='store_true',
                    help='research geometry only: unique-ID source poses require additional runtime qualification')
    ap.add_argument('--single-triangles',action='store_true',
                    help='research single-triangle witnesses as duplicate exact receipt triangles')
    ap.add_argument('--conditional-targets',action='store_true',
                    help='research only: unique-ID target poses also require cached-delta-safe runtime qualification')
    ap.add_argument('--clearance',type=float,default=2000.,
                    help='continuous eye-to-plane clearance; frame receipts still independently reject clipping')
    ap.add_argument('--selected-source-lod-witnesses',action='store_true',help='RESEARCH ONLY: exact meshlet witness from one actually selected source LOD; unsupported by current runtime')
    ap.add_argument('--source-roster',type=Path,
                    help='restrict source instances to this authenticated package prerequisite census')
    a=ap.parse_args(); root=a.private; work=root/'work'; pkg=root/'inputs'
    assert a.clearance>=64., 'must exceed the 32 mm per-operand geometric budget'
    sys.path[:0]=[str(root/'helpers'/'pvs'),str(root/'helpers'/'interior')]
    # The historical helper assumed every package had r4tc. r10d does not.
    # Bind every present input, without manufacturing a descriptor or weakening
    # any geometry, policy, placement, opacity, or runtime admission requirement.
    source=(root/'helpers'/'pvs'/'pvs_certify.py').read_text()
    old="for name in ('ps2-world.re4mesh','ps2-world.r4pw','original.r4pw','ps2-world.ids','ps2-world.r4tc')}"
    new="for name in ('ps2-world.re4mesh','ps2-world.r4pw','original.r4pw','ps2-world.ids','ps2-world.r4tc') if (pkgdir/name).exists()}"
    assert source.count(old)==1
    adapted=source.replace(old,new)
    roster=None;source_keys=None;source_levels={}
    if a.source_roster:
        census=json.loads(a.source_roster.read_text())
        roster=next(x for x in census['rooms'] if int(x['room'][1:],16)==int(a.room,16))
        from r4im import Pkg
        pinned=Pkg(pkg/'ps2-world.re4mesh',pkg/'ps2-world.r4pw')
        assert roster['mesh_crc']==f'{pinned.mesh_crc:08x}' and roster['physical_policy_crc']==f'{pinned.sidecar_crc:08x}'
        source_keys={(x['placement'],x['part'],x['cluster']) for x in roster['eligible_sources']}
        source_levels={(x['placement'],x['part'],x['cluster']):x.get('source_level',0) for x in roster['eligible_sources']}
    marker='        for ti,t in enumerate(levels[0]):'
    assert adapted.count(marker)==1
    adapted=adapted.replace(marker,"        if SOURCE_KEYS is not None and (pi,part,cl) not in SOURCE_KEYS:continue\n"+marker)
    if a.selected_source_lod_witnesses:
        assert source_keys is not None and census['selected_source_lods_research'] and not a.single_triangles
        before="        panel_levels=[]\n        for level in range(cluster['level_count']):"
        after="        panel_levels=[]\n        for level in (SOURCE_LEVELS[(pi,part,cl)],):"
        assert adapted.count(before)==1;adapted=adapted.replace(before,after)
        before='level=0,triangle_index=int(ti)'
        assert adapted.count(before)==1;adapted=adapted.replace(before,'level=SOURCE_LEVELS[(pi,part,cl)],triangle_index=int(ti)')
    adapted=adapted.replace('clearance=2000.',f'clearance={a.clearance!r}')
    adapted=adapted.replace('clearance_mm=2000,',f'clearance_mm={a.clearance!r},')
    if a.conditional_sources:
        predicate="if I['dyn'][instance] or pas!=0 or cull not in (0,2):continue"
        assert adapted.count(predicate)==1
        adapted=adapted.replace(predicate,"if pas!=0 or cull not in (0,2):continue")
    if a.conditional_targets:
        predicate="target_ok=~I['dyn'] & (I['pas']==0)"
        assert adapted.count(predicate)==1
        adapted=adapted.replace(predicate,"target_ok=(I['pas']==0)")
    module=type(sys)('interior_vis23_certifier')
    module.__file__=str(root/'helpers'/'pvs'/'pvs_certify.py')
    exec(compile(adapted,module.__file__,'exec'),module.__dict__)
    module.SOURCE_KEYS=source_keys;module.SOURCE_LEVELS=source_levels
    pairs=module.pairs
    # Current pvs23_runtime.inc accepts source panels from one-level clusters.
    def single_level_pairs(p,pi,cl,level=0):
        if a.selected_source_lod_witnesses or p.clusters[cl]['level_count']==1:
            yield from pairs(p,pi,cl,level)
    module.pairs=single_level_pairs
    module.certify(pkg,work,int(a.room,16),limit=a.limit,margin=32.,pairs_only=not a.single_triangles)
    report=json.loads((work/'proof.json').read_text())
    if source_keys is not None:
        assert all((d['placement_index'],d['part'],d['cluster']) in source_keys for d in report['used_occluders'].values())
    C,I=importlib.import_module('pvs_emit').load_cells(work),importlib.import_module('pvs_emit').load_inst(work)
    # Admit at most sixteen panels and retain every earlier placement. Dropped
    # dependencies become all-visible, which can only reduce the candidate cut.
    scores={}
    for cell,target,dep in report['cell_target_proofs']:
        scores[dep]=scores.get(dep,0)+int(I['verts'][target])
    chosen=set(sorted(scores,key=lambda k:(-scores[k],k))[:16])
    used={k:v for k,v in report['used_occluders'].items() if int(k) in chosen}
    prefix=max((d['placement_index'] for d in used.values()),default=-1)
    proofs=[p for p in report['cell_target_proofs'] if p[2] in chosen and I['placement'][p[1]]>prefix]
    # Keep only panels actually needed after prefix retention.
    deps={p[2] for p in proofs};used={k:v for k,v in used.items() if int(k) in deps}
    prefix=max((d['placement_index'] for d in used.values()),default=-1)
    S=np.ones((C['nx']*C['nz'],C['ninst']),bool)
    for cell,target,dep in proofs:S[cell,target]=False
    (work/'proof-bits.bin').write_bytes(np.packbits(S,axis=1,bitorder='little').tobytes())
    report.update(used_occluders=used,cell_target_proofs=proofs,opaque_prefix_max_placement=prefix,
                  cleared_bits=len(proofs),cells_with_cuts=int((~S[C['has']]).any(1).sum()))
    report['hashes']['proof-bits.bin']=sha(work/'proof-bits.bin')
    (work/'proof.json').write_text(json.dumps(report,indent=1)+'\n')
    verifier=importlib.import_module('pvs_verify')
    if a.conditional_sources or a.conditional_targets or a.clearance!=2000. or a.selected_source_lod_witnesses:
        verify_source=(root/'helpers'/'pvs'/'pvs_verify.py').read_text()
        verify_source=verify_source.replace('clearance=2000.',f'clearance={a.clearance!r}')
        predicate="assert pas==0 and cull==D['cull'] and not I['dyn'][D['instance']]"
        if a.conditional_sources:
            assert verify_source.count(predicate)==1
            verify_source=verify_source.replace(predicate,"assert pas==0 and cull==D['cull']")
        if a.conditional_targets:
            predicate="assert C['has'][cell] and not I['dyn'][target] and I['pas'][target]==0"
            assert verify_source.count(predicate)==1
            verify_source=verify_source.replace(predicate,"assert C['has'][cell] and I['pas'][target]==0")
        if a.selected_source_lod_witnesses:
            before="assert len(panels)==p.clusters[cl]['level_count']"
            assert verify_source.count(before)==1
            verify_source=verify_source.replace(before,"assert len(panels)==1 and panels[0]['level']==D['level']")
            before="for level,Q in enumerate(panels):\n                assert Q['level']==level"
            after="for Q in panels:\n                level=Q['level'];assert 0<=level<p.clusters[cl]['level_count']"
            assert verify_source.count(before)==1;verify_source=verify_source.replace(before,after)
        conditional_verifier=type(sys)('interior_vis23_verifier')
        conditional_verifier.__file__=verifier.__file__
        exec(compile(verify_source,verifier.__file__,'exec'),conditional_verifier.__dict__)
        verifier=conditional_verifier
    verifier.verify(pkg,work,int(a.room,16))
    emitter=importlib.import_module('pvs_emit')
    # CLI selects geometric-candidate mode in the pinned emitter.
    argv=sys.argv[:];sys.argv=['pvs_emit.py','emit',str(work),str(root/'ps2-world.pvs'),'--geometric-candidate','--dilate','0','--near','0']
    emitter.main();sys.argv=argv
    from r4im import Pkg
    p=Pkg(pkg/'ps2-world.re4mesh',pkg/'ps2-world.r4pw')
    envelope=np.zeros(3)
    for pl in p.placements:
        mesh=p.meshes[pl['mesh']]; A=pl['affine']
        grid_abs=np.abs(mesh['origin'])+65535*np.abs(mesh['step'])
        envelope=np.maximum(envelope,np.abs(A[:,:3])@grid_abs+np.abs(A[:,3]))
    body=(root/'ps2-world.pvs').read_bytes()
    panels=[]
    for key,D in sorted(used.items(),key=lambda kv:int(kv[0])):
        if 'pair' in D:
            Q=D['pair']['all_lod_panels'][0]
            meshlet=Q['meshlet'];corners=sum(Q['corner_indices'],[])
        else:
            # One opaque triangle is a complete covering witness on its own.
            # Duplicate its exact oriented index triple for the existing two-
            # triangle receipt representation. This remains a research cohort
            # until root reviews that runtime interpretation and liveness.
            cl=p.clusters[D['cluster']];first,count,_=p.levels[cl['first_level']]
            target=D['triangle_index'];meshlet=None
            for ml in range(first,first+count):
                _,indices=p.let_tris(ml)
                if target<len(indices):
                    meshlet=ml;corners=list(indices[target])*2;break
                target-=len(indices)
            assert meshlet is not None
        panels.append([D['placement_index'],D['placement_field'],D['part'],D['cluster'],meshlet,corners])
    lines=['// Private generated descriptor; no public asset data.']
    if a.selected_source_lod_witnesses:
        lines+=['#if !defined(RE4DC_PS2_PVS_SELECTED_SOURCE_LODS) || !RE4DC_PS2_PVS_SELECTED_SOURCE_LODS',
                '#error Selected-LOD source witnesses require reviewed runtime admission support', '#endif']
    lines+=['constexpr Panel room_panels[] = {']
    for pi,field,part,cl,ml,corners in panels:
        lines.append('    {%d,%d,%d,%d,%d, {%s}},'%(pi,field,part,cl,ml,','.join(map(str,corners))))
    lines+=['};','constexpr Certificate certificates[] = {',
            '    {%dU,%dU,%dU,%dU,%dU,%dU,%dU,%dU,32U,room_panels, {%s}},'%(int(a.room,16),p.mesh_crc,p.mesh_bytes,p.sidecar_crc,len(body),zlib.crc32(body),max(prefix,0),len(panels),','.join(str(math.ceil(x))+'.0' for x in envelope)), '};']
    if panels:(root/'pvs23_certificates.inc').write_text('\n'.join(lines)+'\n')
    summaries=[]
    for cell in np.flatnonzero(C['has']):
        mask=~S[cell]; summaries.append(dict(cell=int(cell),instances_hidden=int(mask.sum()),
            level0_opaque_vertices_hidden=int(I['verts'][mask & (I['pas']==0)].sum())))
    result=dict(room=int(a.room,16),mesh_crc=f'{p.mesh_crc:08x}',physical_policy_crc=f'{p.sidecar_crc:08x}',
                table_bytes=len(body),heap_bytes=len(body)+((2*(len(p.placements)+1)+2*p.npart+31)&~31),
                panel_count=len(panels),prefix_max_placement=prefix,cleared_bits=len(proofs),
                sampled_domains=len(summaries),cell_summaries=summaries,world_abs=envelope.tolist(),
                runtime_admitted=False,actual_runtime_cuts=0,
                limitations=['continuous geometry replay only; target guarded path/pixels pending',
                             'L0 weights are not selected runtime transformed vertices',
                             'zero runtime cut claim until source/material/numeric/prefix guards actually admit'],
                certifier_adaptation='optional absent r4tc hash only; source panels restricted to one-level clusters; max16 dependencies; discarded proofs retained visible',
                pinned_certifier_sha256=sha(root/'helpers'/'pvs'/'pvs_certify.py'),
                adapted_certifier_sha256=hashlib.sha256(adapted.encode()).hexdigest(),
                output_hashes={f.name:sha(f) for f in (root/'ps2-world.pvs',work/'proof.json',work/'replay.json')})
    result['conditional_sources_research']=a.conditional_sources
    result['single_triangle_receipts_research']=a.single_triangles
    result['conditional_targets_research']=a.conditional_targets
    result['selected_source_lod_witnesses_research']=a.selected_source_lod_witnesses
    if a.selected_source_lod_witnesses:
        result['certifier_adaptation']='selected actual source LOD meshlet witness research only; targets retain all-LOD bounds; max16 dependencies; no current runtime support'
    if a.selected_source_lod_witnesses:
        result['limitations'].append('selected-LOD source meshlet witnesses are rejected by current one-LOD runtime guard; descriptor requires new reviewed capability')
        result['used_source_levels']=[d['level'] for d in used.values()]
    result['eye_to_plane_clearance_mm']=a.clearance
    result['source_roster']=None if a.source_roster is None else dict(path=str(a.source_roster),sha256=sha(a.source_roster))
    result['conditional_source_fields']=[d['placement_field'] for d in used.values() if I['dyn'][d['instance']]]
    if a.conditional_sources:
        result['limitations'].append('conditional source liveness requires target qualification of the reviewed affine-selection receipt; earlier captured e9bf7 camera binary predates that repair')
    (root/'qualification.json').write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
