#!/usr/bin/env python3
"""Opt-in original-VQ chains for bounded source-owned Efm obj04 materials.

Uses the existing Efm/model codecs and VQ mip converter. Sprite and Efm numeric
IDs stay separate. Source proof does not establish active registry ownership,
rendered look, live VRAM or speed. No runtime/default/recipe changes.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import struct
import sys

TOOLS=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(TOOLS),str(TOOLS/'d367')]
import effect_consumers as ec
import effect_model_consumers as em
import mipmap_vq as vq
import texpack
from compose_candidate import _read,bound_candidate,request_inventory
from world_candidate import sha


def record_hold(body,record):
    # Only full, world obj04 records are qualified here. Compact, debris, rigid,
    # scroll, generator and render-target overrides require separate contracts.
    if (record.get('compact') or record.get('sprite_id')!=0xff or
            record.get('kind')!=0 or record.get('screen_parts') or
            record.get('reference_namespace')!='effect-model'):
        return 'unsupported-model-record-path'
    at=record['record_offset']
    if at<0 or at+0x12c>len(body):raise ValueError('model record outside source body')
    raw=body[at:at+0x12c]
    if sha(raw)!=record['record_sha256'] or raw[1]!=0xff or raw[2]!=record['model_index']:
        raise ValueError('model record differs from source proof')
    if struct.unpack_from('<I',raw,0xd0)[0] or raw[0xfe]:return 'render-target-or-motion-override'
    return None


def qualify(blob,source_path,expected_sha,coverage):
    if sha(blob)!=expected_sha:raise ValueError('effect model archive SHA differs')
    body,active,_=ec.archive(blob);proof=em.source_model_bindings(blob)
    rows=[]
    for eff in proof['effects']:
        for model in eff['models']:
            matches=[]
            for row in coverage['normal_rows']:
                refs=[r for r in row['source_references'] if r['path']==source_path and
                      r['arc_index']==eff['archive_entry'] and r['tpl_offset']==model['tpl_offset']]
                if refs:matches.append((row,refs))
            reason=None;materials=[]
            if len(matches)!=1:reason='requires-one-exact-model-TPL-descriptor'
            else:
                row,refs=matches[0]
                if (len(refs)!=1 or
                        refs[0]['file_sha256']!=expected_sha or refs[0]['active_body_offset']!=active or
                        refs[0]['image']!=0 or refs[0]['owner_category']!='effect' or
                        row['native_world_references'] or row['native_registry_references'] or
                        row.get('derived_pair_references')):
                    reason='shared-or-incomplete-source-material-aliases'
                elif row['layout']!=2 or row['native_format'] not in (0,1,2) or row['width']!=row['height']:
                    reason='requires-original-square-VQ'
                elif not model['sequence_references']:reason='no-local-model-record-consumer'
                else:
                    holds=[record_hold(body,r) for r in model['sequence_references']]
                    if any(holds):reason=next(h for h in holds if h)
                    else:
                        materials=em.model_materials(body[model['model_offset']:model['tpl_offset']],texture_count=1)
                        used=[m for m in materials if m['samples_texture']]
                        if not used or any(m['texture_index']!=0 or m['material_flags'] for m in used):
                            reason='special-or-unproved-model-material'
                        elif any(not m['UV_bounds'] or min(m['UV_bounds']['u_min'],m['UV_bounds']['v_min'])<0 or
                                 max(m['UV_bounds']['u_max'],m['UV_bounds']['v_max'])>1 for m in used):
                            reason='UV-domain-needs-separate-contract'
            rows.append(dict(key=matches[0][0]['key'] if len(matches)==1 else None,
                package_sha256=matches[0][0]['package_sha256'] if len(matches)==1 else None,
                decision='hold-'+reason if reason else 'local-world-obj04-original-VQ-proof',
                source_path=source_path,source_sha256=expected_sha,archive_entry=eff['archive_entry'],
                model=model,materials=materials,source_references=matches[0][1] if len(matches)==1 else []))
    return dict(schema='re4dc-bounded-Efm-model-consumer-policy-1',source_pack_sha256=coverage['source_pack_sha256'],
        source_path=source_path,source_sha256=expected_sha,source_bytes=len(blob),active_body_offset=active,
        rows=rows,limits=['Named archive registration/material proof; active registry owner, dynamic aliases and actual draw remain target gates.'])


def qualify_masked(blob,source_path,expected_sha,coverage):
    if sha(blob)!=expected_sha:raise ValueError('masked model archive SHA differs')
    body,active,_=ec.archive(blob);proof=em.source_model_bindings(blob)
    cov={r['key']:r for r in coverage['normal_rows']};rows=[];held=[]
    for eff in proof['effects']:
        for model in eff['models']:
            records=model['sequence_references']
            if not records or any(record_hold(body,r) for r in records):continue
            try:materials=em.masked_material_bindings(body,model)
            except ValueError as exc:
                held.append(dict(model=model['model_index'],reason=str(exc)));continue
            if len(materials)!=1:continue
            material=materials[0];name=material['pair_key'];row=cov.get(name)
            if (not row or row['layout']!=2 or row['width']!=row['height'] or
                    row['source_references'] or row['native_world_references'] or
                    row['native_registry_references'] or row.get('derived_pair_references')):continue
            # Both identities are recomputed from actual LE TPL metadata and GX
            # pixels. This fills an unclassified pair; it never overrides a
            # known competing owner or an already-selected package.
            rows.append(dict(key=name,package_sha256=row['package_sha256'],
                decision='source-world-obj04-original-VQ-candidate',source_references=[],
                source_path=source_path,source_sha256=expected_sha,archive_entry=eff['archive_entry'],
                active_body_offset=active,model=model,material_pair_proof=material,
                runtime_conditions=['ordinary model alpha ref0, same UV, original wrap; runtime state admission remains authoritative']))
    return dict(schema='re4dc-masked-Efm-source-policy-1',source_pack_sha256=coverage['source_pack_sha256'],rows=rows,held=held,
        limits=['Exact source mask identities/materials; current registry owner, flagsDC, alpha_omit and actual draw remain target gates.'])


def compose_alias_policy(policies,coverage):
    """Every known source alias must independently qualify before selection."""
    candidates={};held=[]
    for policy in policies:
        if policy['source_pack_sha256']!=coverage['source_pack_sha256']:raise ValueError('alias source pack differs')
        for row in policy['rows']:
            if row['decision']=='local-world-obj04-original-VQ-proof':candidates.setdefault(row['key'],[]).append(row)
            else:held.append(row)
    rows=[];cov={r['key']:r for r in coverage['normal_rows']}
    for name,group in candidates.items():
        ref=cov[name];bindings=[]
        for local in group:
            for binding in local['source_references']:
                if binding not in bindings:bindings.append(binding)
        if sorted(map(str,bindings))!=sorted(map(str,ref['source_references'])):
            held.extend(dict(r,decision='hold-unqualified-source-alias') for r in group);continue
        row=dict(group[0],decision='source-world-obj04-original-VQ-candidate',source_references=ref['source_references'],model_alias_proofs=group)
        rows.append(row)
    return dict(schema='re4dc-complete-Efm-model-alias-policy-1',source_pack_sha256=coverage['source_pack_sha256'],rows=rows,held=held,
        limits=['Exact static source aliases are all bound; active registry ownership, dynamic aliases and actual draw remain target gates.'])


def build(original,base_pack,coverage,policy,*,enabled=False,engine='python'):
    source,base=map(_read,(original,base_pack))
    if (set(source)!=set(base) or sha(original)!=coverage['source_pack_sha256'] or
            sha(original)!=policy['source_pack_sha256']):raise ValueError('model source/base namespace differs')
    cov={r['key']:r for r in coverage['normal_rows']}
    if len(cov)!=len(coverage['normal_rows']) or set(cov)!={'%08x-%08x'%k for k in source}:
        raise ValueError('model coverage namespace differs')
    after=dict(base);frames=[];seen=set()
    for row in policy['rows']:
        if row['decision']!='source-world-obj04-original-VQ-candidate':continue
        name=row['key'];key=tuple(int(v,16) for v in name.split('-'));ref=cov[name]
        if name in seen:raise ValueError('duplicate effect model selection')
        seen.add(name)
        if (sha(source[key])!=row['package_sha256'] or row['package_sha256']!=ref['package_sha256'] or
                row['source_references']!=ref['source_references'] or
                ref['native_world_references'] or ref['native_registry_references'] or ref.get('derived_pair_references')):
            raise ValueError('effect model material aliases or package differ')
        if base[key]!=source[key]:raise ValueError('effect model would replace an existing selected package')
        native=vq.read_native_vq(base[key])
        if native.mipmapped:raise ValueError('effect model already has a chain')
        after[key],result=vq.add_mipmaps(base[key],enabled=enabled,engine=engine)
        result.update(key=name,family='original-VQ-effect-model',source_policy=row);frames.append(result)
    result,count=texpack.build(after);texpack.verify(result)
    changed={k for k in after if base[k]!=after[k]}
    if changed!=({tuple(int(v,16) for v in n.split('-')) for n in seen} if enabled else set()) or not enabled and result!=base_pack:
        raise ValueError('model OFF/unselected member identity differs')
    report=dict(schema='re4dc-source-Efm-original-VQ-mip-candidate-1',candidate_only=True,enabled=bool(enabled),
        source_pack_sha256=sha(original),original_pack_sha256=sha(original),base_pack_sha256=sha(base_pack),
        candidate_pack_sha256=sha(result),candidate_pack_bytes=len(result),packages=count,
        selected_frames=len(frames),changed_from_base=len(changed),unchanged_from_base=count-len(changed),
        changed_from_original=sum(source[k]!=after[k] for k in source),archive_delta_from_base=len(result)-len(base_pack),
        before_inventory=request_inventory(base,set(base)),after_inventory=request_inventory(after,set(after)),frames=frames,
        members=[dict(key='%08x-%08x'%k,before_sha256=sha(source[k]),after_sha256=sha(after[k]),changed=source[k]!=after[k],
                      selected_base_sha256=sha(base[k]),changed_from_base=base[k]!=after[k]) for k in sorted(source)],
        required_build_knobs=['CAST_MIPMAP=1','TEX_TWIDDLED_MIPMAP=1','TEX_PAL4_ALPHA=1','TEX_PAL4_MIPMAP=1','TEX_PAL8_ALPHA=1','TEX_PAL8_MIPMAP=1'] if enabled else [],
        sampler_policy='Source materialSetup/ModelPart texId reaches model_bridge selected GXTexObj, then native_ui model_packet_begin: original wrap, blend/depth, MODULATEALPHA, bilinear and default MIPD retained. No sprite sampler substitution.',
        resource_scope='Descriptor/request inventory, not target live VRAM, performance or acceptance.',
        limits=policy['limits']+['Lower levels deliberately filter/quantize; rendered target sampling/look and combined resources/timing remain open. No full build, guest, recipe/default or release change.'])
    return result,report,base,after


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('source-pack','base-candidate','coverage','source-archive','source-sha256','output'):
        ap.add_argument('--'+name,required=True,type=str if name=='source-sha256' else Path)
    ap.add_argument('--masked-materials',action='store_true',help='opt-in exact source color/mask pair proof; ordinary model selection stays separate')
    ap.add_argument('--source-path',default='etc/core.das');ap.add_argument('--generate',action='store_true')
    a=ap.parse_args(argv)
    if a.output.exists() or not a.output.parent.is_dir():ap.error('output must be a new private directory')
    original=a.source_pack.read_bytes()
    if shutil.disk_usage(a.output.parent).free<3*len(original)+512*1024*1024:raise ValueError('insufficient candidate headroom')
    base=bound_candidate(a.base_candidate,original);coverage_bytes=a.coverage.read_bytes();coverage=json.loads(coverage_bytes)
    local=qualify(a.source_archive.read_bytes(),a.source_path,a.source_sha256,coverage)
    policy=(qualify_masked(a.source_archive.read_bytes(),a.source_path,a.source_sha256,coverage) if a.masked_materials else compose_alias_policy([local],coverage))
    result,report,before,after=build(original,base,coverage,policy,enabled=a.generate)
    report.update(tool_sha256=sha(Path(__file__).read_bytes()),coverage_sha256=sha(coverage_bytes))
    a.output.mkdir();(a.output/'mip-packages').mkdir()
    (a.output/'tex.pak').write_bytes(result)
    for k in before:
        if before[k]!=after[k]:(a.output/'mip-packages'/('%08x-%08x.re4tex'%k)).write_bytes(after[k])
    for name,value in (('candidate.json',report),('consumer-policy.json',policy)):
        (a.output/name).write_text(json.dumps(value,indent=2)+'\n')
    files=sorted(p for p in a.output.rglob('*') if p.is_file())
    (a.output/'SHA256SUMS').write_text(''.join('%s  %s\n'%(sha(p.read_bytes()),p.relative_to(a.output).as_posix()) for p in files))
    print(json.dumps({k:report[k] for k in ('selected_frames','candidate_pack_sha256','candidate_pack_bytes','changed_from_original','archive_delta_from_base')}))
    return 0

if __name__=='__main__':raise SystemExit(main())
