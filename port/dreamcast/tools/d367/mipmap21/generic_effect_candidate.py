#!/usr/bin/env python3
"""Source-qualified square native16/VQ EFF mips outside PS2-frame packages.

Preserves full-resolution texels/codebooks/indices and the selected compact
base ancestor. Fixed ID UI, native actor/world aliases and unproved consumers
are held. No runtime, recipe, defaults or target execution is changed.
"""
from __future__ import annotations
import argparse
import collections
import json
from pathlib import Path
import re
import shutil
import sys

TOOLS=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(TOOLS));sys.path.insert(0,str(TOOLS/'d367'))
import convert_tpl as tpl
import effect_consumers
import effect_policy
import mipmap_compact_vq as compact_mips
import mipmap_twiddled as twiddled
import mipmap_vq as vq
import texpack
from compose_candidate import _read,bound_candidate,request_inventory
from world_candidate import sha


def frame_rows(coverage):
    return [dict(key=r['key'],package_sha256=r['package_sha256'],source_refs=r['source_references'],
        shared_native_binding=bool(r['native_world_references'] or r['native_registry_references']))
        for r in coverage['normal_rows'] if r['material']!='ps2-source' and r['width']==r['height']
        and r['native_format']<3 and r['source_references']
        and all(s['owner_category']=='effect' for s in r['source_references'])]


def source_policy(coverage,manifest,source_root,source_code_root):
    frames=frame_rows(coverage);parsed={};metadata={}
    for rel in sorted({r['path'] for f in frames for r in f['source_refs']}):
        if rel not in manifest or not re.fullmatch(r'(?:st[1-5]/r[0-9a-f]{3}\.arc|em/[a-z0-9]+\.drs|etc/core\.das|ss/(?:cmn|eng)/[a-z0-9_]+\.dat)',rel):
            raise ValueError('unexpected source path in effect proof')
        path=source_root/rel
        if not path.is_file():metadata[rel]=dict(retained=False,reason='named-exact-retained-input-absent');continue
        blob=path.read_bytes();digest=sha(blob)
        if digest!=manifest[rel]['sha256'] or len(blob)!=manifest[rel]['size']:
            metadata[rel]=dict(retained=False,reason='named-input-not-original-hash',actual_sha256=digest);continue
        try:parsed[rel]=effect_consumers.source_bindings(blob,separate_model_namespace=True)
        except ValueError as e:metadata[rel]=dict(retained=True,parsed=False,sha256=digest,reason=str(e));continue
        metadata[rel]=dict(retained=True,parsed=True,path=str(path),sha256=digest,size=len(blob),
            EFF_blocks=len(parsed[rel]['effects']),compact_sequences=parsed[rel]['compact_sequences'])
    app=(source_code_root/'src/game/esp_app.cpp').read_text()
    common={int(i,16) for i in re.findall(r'EspFuncTblSet\(0x([0-9a-fA-F]+),[^,]+,\s*EspCommonTrans\)',app)}
    rows=[]
    for frame in frames:
        row=effect_policy.classify(frame,parsed,metadata,common)
        if frame['shared_native_binding']:
            row.update(decision='hold-shared-native-world-or-actor',reasons=['another-native-material-consumer-is-bound'])
        rows.append(row)
    return dict(schema='re4dc-generic-EFF-consumer-policy-1',sampling_contract_version=2,
        source_pack_sha256=coverage['source_pack_sha256'],keys=len(rows),rows=rows,
        decisions=dict(collections.Counter(r['decision'] for r in rows)),source_files=metadata,
        common_sprite_ids=sorted(common),
        limits=['Source-qualified candidate only; source records do not prove all dynamic consumers or actual draw.',
                'Missing/mismatched original inputs, fixed UI, native material aliases and special effects remain held.'])


def build(original,base_pack,coverage,policy,*,enabled=False,engine='auto'):
    if policy.get('sampling_contract_version',2)!=2:raise ValueError('unsupported generic effect sampling contract')
    source,base=map(_read,(original,base_pack))
    if set(source)!=set(base) or coverage['source_pack_sha256']!=sha(original) or policy['source_pack_sha256']!=sha(original):
        raise ValueError('generic effect source/base policy identity differs')
    expected={r['key']:r for r in frame_rows(coverage)}
    policies={r['key']:r for r in policy['rows']}
    if len(policy['rows'])!=len(policies) or set(expected)!=set(policies):raise ValueError('effect policy namespace differs')
    after=dict(base);held=[];rows=[];groups=collections.defaultdict(set)
    for name,row in policies.items():
        if row['decision']!='world-common-sprite-source-candidate':
            held.append(dict(key=name,decision=row['decision'],reasons=row['reasons']));continue
        key=tuple(int(v,16) for v in name.split('-'))
        if row['package_sha256']!=sha(source[key]) or expected[name]['package_sha256']!=sha(source[key]):
            raise ValueError('source-qualified effect package hash differs')
        if expected[name]['shared_native_binding'] or row['direct_ID_UI_consumers']:
            raise ValueError('effect policy tries to convert a held shared/UI key')
        records=[r for b in row['source_bindings'] for r in b['records']]
        if not row['source_bindings'] or any(not b['records'] for b in row['source_bindings']):raise ValueError('effect policy lacks record bindings')
        for b in row['source_bindings']:
            m=policy['source_files'].get(b['source_path'],{})
            if not m.get('retained') or not m.get('parsed') or m['sha256']!=b['source_sha256']:raise ValueError('effect policy source is not exact')
        expected_refs={(b['path'],b['arc_index'],b['tpl_offset'],b['file_sha256']) for b in expected[name]['source_refs']}
        actual_refs={(b['source_path'],b['archive_entry'],b['tpl_offset'],b['source_sha256']) for b in row['source_bindings']}
        if actual_refs!=expected_refs or len(actual_refs)!=len(row['source_bindings']):
            raise ValueError('generic effect policy omits or duplicates an original source binding')
        if any((b['path'],b['arc_index']) in effect_policy.ID_UI for b in expected[name]['source_refs']):
            raise ValueError('generic effect source has a fixed-ID UI consumer')
        if any(effect_consumers.record_reference_namespace(r)!='effect-texture' for r in records):
            raise ValueError('generic effect policy contains a model or unresolved reference namespace')
        classes=[effect_consumers.record_sampling(r,policy['common_sprite_ids'],extended=True) for r in records]
        if any(c.startswith('hold-') for c in classes) or not any(c.startswith('common-world-sprite') for c in classes):raise ValueError('effect policy contains an unsupported sampler')
        st=tpl.TEXTURE.unpack_from(source[key],48);bt=tpl.TEXTURE.unpack_from(base[key],48)
        if st[6]&tpl.FLAG_MIPMAP or bt[6]&tpl.FLAG_MIPMAP:
            held.append(dict(key=name,decision='hold-existing-chain',reasons=['retain-already-selected-mip-package']));continue
        h=tpl.HEADER.unpack_from(source[key]);cover=h[10]
        if cover>>31 and (cover&2047,(cover>>11)&2047)!=(st[1],st[2]):
            held.append(dict(key=name,decision='hold-partial-covered-domain',reasons=['covered-UV-domain-is-not-full-frame']));continue
        if bt[7]==tpl.PAYLOAD_VQ and st[7]==tpl.PAYLOAD_TWIDDLED:
            reference,_=twiddled.add_mipmaps(source[key],enabled=True,engine=engine)
            after[key],result=compact_mips.add_mipmaps(base[key],reference,enabled=enabled,engine=engine)
            family='compact-base-VQ'
        elif base[key]==source[key]:
            converter=vq if st[7]==tpl.PAYLOAD_VQ else twiddled
            after[key],result=converter.add_mipmaps(base[key],enabled=enabled,engine=engine)
            family='original-VQ' if st[7]==tpl.PAYLOAD_VQ else 'original-native16'
        else:raise ValueError('generic effect has an unrecognized base ancestor change')
        result.update(key=name,family=family,source_policy=row)
        rows.append(result)
        for b in row['source_bindings']:groups[b['source_path']].add(key)
    result,count=texpack.build(after);texpack.verify(result)
    changed={k for k in base if base[k]!=after[k]}
    if len(changed)!=(len(rows) if enabled else 0) or not enabled and result!=base_pack:
        raise ValueError('effect OFF or selected-member identity differs')
    report=dict(schema='re4dc-generic-native16-EFF-mip-candidate-1',candidate_only=True,enabled=bool(enabled),
        source_pack_sha256=sha(original),original_pack_sha256=sha(original),base_pack_sha256=sha(base_pack),
        candidate_pack_sha256=sha(result),candidate_pack_bytes=len(result),archive_delta_from_original=len(result)-len(original),
        archive_delta_from_base=len(result)-len(base_pack),packages=count,selected_frames=len(rows),changed_from_base=len(changed),
        changed_from_original=sum(source[k]!=after[k] for k in source),family_counts=dict(collections.Counter(r['family'] for r in rows)),
        frames=rows,held=held,before_inventory=request_inventory(base,set(base)),after_inventory=request_inventory(after,set(after)),
        source_frame_inventories={g:dict(before=request_inventory(base,keys),after=request_inventory(after,keys)) for g,keys in sorted(groups.items())},
        required_build_knobs=['CAST_MIPMAP=1','TEX_TWIDDLED_MIPMAP=1','TEX_PAL4_ALPHA=1','TEX_PAL4_MIPMAP=1'] if enabled else [],
        sampler_policy='Existing native effect sprite bilinear/clamp/MODULATEALPHA/default-MIPD path; dimensions, UVs, blend/depth/fog, frame timing, base texels and accepted source VQ codebooks/indices stay exact. Preserve SH4ZAM/SKIN_SH4ZAM.',
        resource_scope='Overlapping static frame inventories, not observed allocator addresses, live residency, largest block, target VRAM or timing.',
        members=[dict(key='%08x-%08x'%k,before_sha256=sha(source[k]),after_sha256=sha(after[k]),changed=source[k]!=after[k],
            selected_base_sha256=sha(base[k]),changed_from_base=base[k]!=after[k]) for k in sorted(source)],
        limits=['Lower mip levels are filtered/quantized candidates requiring rendered look and sampling acceptance.',
                'No game build, guest, runtime/default, recipe, release or SD changes.'])
    return result,report,base,after


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('source-pack','base-candidate','coverage','release-manifest','retained-source-root','source-code-root','output'):
        ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--generate',action='store_true');ap.add_argument('--engine',choices=('auto','numpy','python'),default='auto')
    a=ap.parse_args(argv)
    if a.output.exists() or not a.output.parent.is_dir():ap.error('output must be a new private directory')
    original=a.source_pack.read_bytes()
    if shutil.disk_usage(a.output.parent).free<3*len(original)+512*1024*1024:raise ValueError('insufficient private candidate headroom')
    base=bound_candidate(a.base_candidate,original);coverage_bytes=a.coverage.read_bytes();coverage=json.loads(coverage_bytes)
    manifest_bytes=a.release_manifest.read_bytes();manifest=json.loads(manifest_bytes)
    policy=source_policy(coverage,manifest,a.retained_source_root,a.source_code_root)
    result,report,before,after=build(original,base,coverage,policy,enabled=a.generate,engine=a.engine)
    report.update(tool_sha256=sha(Path(__file__).read_bytes()),coverage_sha256=sha(coverage_bytes),release_manifest_sha256=sha(manifest_bytes))
    code=[Path(__file__),Path(__file__).with_name('effect_policy.py'),Path(__file__).with_name('effect_consumers.py'),
        TOOLS/'mipmap_compact_vq.py',TOOLS/'mipmap_vq.py',TOOLS/'mipmap_twiddled.py']
    code.extend(a.source_code_root/rel for rel in ('src/game/esp_app.cpp','src/game/esp_sub.cpp',
        'src/game/espgen00.cpp','src/game/esp0b.cpp','src/game/esp11.cpp','src/game/esp46.cpp',
        'src/game/esp4a.cpp','src/game/esp4c.cpp','src/game/cam_extra.cpp','src/game/cockpit.cpp',
        'src/st1/r101.cpp','src/st1/r10b.cpp','include/esp.h','include/global.h'))
    policy['source_code']=[dict(path=str(p),sha256=sha(p.read_bytes())) for p in code]
    a.output.mkdir();outputs={}
    def write(path,data):
        with path.open('xb') as f:f.write(data)
        outputs[path.relative_to(a.output).as_posix()]=dict(size=len(data),sha256=sha(data))
    write(a.output/'tex.pak',result);(a.output/'mip-packages').mkdir()
    for key in sorted(k for k in before if before[k]!=after[k]):write(a.output/'mip-packages'/('%08x-%08x.re4tex'%key),after[key])
    write(a.output/'consumer-policy.json',(json.dumps(policy,indent=2)+'\n').encode())
    write(a.output/'candidate.json',(json.dumps(report,indent=2)+'\n').encode())
    write(a.output/'outputs.json',(json.dumps(outputs,indent=2)+'\n').encode())
    (a.output/'SHA256SUMS').write_text(''.join('%s  %s\n'%(r['sha256'],p) for p,r in sorted(outputs.items())),encoding='ascii')
    print(json.dumps({k:report[k] for k in ('selected_frames','family_counts','changed_from_original','candidate_pack_bytes',
        'archive_delta_from_original','archive_delta_from_base','candidate_pack_sha256')}))
    print(json.dumps(policy['decisions']))
    return 0


if __name__=='__main__':raise SystemExit(main())
