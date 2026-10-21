#!/usr/bin/env python3
"""Opt-in exact PAL8 composition for already-qualified canonical alpha/gray chains.

This shares one 256-color palette. It does not convert UI, actors, unclassified
keys or independent-color palettes, nor enable any runtime/release default.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys

TOOLS=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(TOOLS),str(TOOLS/'d367')]
import compact_native_pal8 as pal8
import convert_tpl as tpl
import compose_candidate as compose
import mipmap_twiddled as tw
import texpack


def sha(data):return hashlib.sha256(data).hexdigest()


def build(original_pack,selected_pack,coverage,policy,*,enabled=False):
    original,before=map(compose._read,(original_pack,selected_pack))
    if set(original)!=set(before):raise ValueError('original and selected key namespaces differ')
    if coverage['source_pack_sha256']!=sha(original_pack) or policy['source_pack_sha256']!=sha(original_pack):
        raise ValueError('coverage names another original pack')
    if policy['selected_candidate_pack_sha256']!=sha(selected_pack):raise ValueError('policy names another selected pack')
    cov={tuple(int(x,16) for x in r['key'].split('-')):r for r in coverage['normal_rows']}
    pol={tuple(int(x,16) for x in r['key'].split('-')):r for r in policy['normal_rows']}
    if set(cov)!=set(before) or set(pol)!=set(before):raise ValueError('coverage must describe exactly every normal packed winner')
    for key in before:
        if cov[key]['package_sha256']!=sha(original[key]) or pol[key]['original_package_sha256']!=sha(original[key]) or pol[key]['candidate_package_sha256']!=sha(before[key]):
            raise ValueError('member hash differs from bound normal coverage')
    after=dict(before);frames=[];held=collections.Counter()
    for key,blob in sorted(before.items()):
        p=pol[key];t=tpl.TEXTURE.unpack_from(blob,48)
        if not (p.get('native_world_selected') or p.get('selective_effect_candidate') or p.get('generic_effect_candidate')):
            held['not-in-already-qualified-cohort']+=1;continue
        if p.get('source_proven_fixed_ID_UI') or p.get('separate_actor_candidate'):
            held['UI-or-separate-actor-owner']+=1;continue
        if (p.get('native_world_selected') and not cov[key]['native_world_references'] or
                not p.get('native_world_selected') and not cov[key]['source_references']):
            held['missing-source-owner-binding']+=1;continue
        if t[3]!=tpl.FORMAT_ARGB4444 or t[7]!=tpl.PAYLOAD_TWIDDLED or t[1]!=t[2] or not t[6]&tpl.FLAG_MIPMAP:
            held['not-existing-square-native-ARGB4444-chain']+=1;continue
        n=tw.read_native_twiddled(blob);words=struct.unpack('<%dH'%(len(n.payload)//2),n.payload)
        if not all(((w>>8)&15)==((w>>4)&15)==(w&15) for w in words):
            held['independent-color-palette-kept-native']+=1;continue
        candidate,row=pal8.compact(blob,enabled=True)
        if not row['changed']:held[row['reason']]+=1;continue
        if enabled:after[key]=candidate
        row.update(key='%08x-%08x'%key,selected=bool(enabled),
            original_package_sha256=sha(original[key]),selected_base_package_sha256=sha(blob),
            qualified_owner='native-world' if p.get('native_world_selected') else 'source-qualified-world-effect',
            native_world_references=cov[key]['native_world_references'],
            source_references=cov[key]['source_references'])
        frames.append(row)
    palettes={pal8.read_native_pal8(after[k]).palette for k in after if after[k]!=before[k]}
    if len(palettes)>1:raise ValueError('canonical cohort unexpectedly needs distinct palettes')
    result,_=texpack.build(after);texpack.verify(result)
    changed={k for k in before if before[k]!=after[k]}
    if not enabled and result!=selected_pack:raise ValueError('OFF changed the selected pack')
    if len(changed)!=(len(frames) if enabled else 0):raise ValueError('unselected member changed')
    rooms=collections.defaultdict(set);instances=collections.Counter();resources=collections.defaultdict(set)
    for key in before:
        for ref in cov[key]['native_world_references']:
            rooms[ref['package']].add(key);instances[ref['package']]+=1
        if key in changed and not cov[key]['native_world_references']:
            for ref in cov[key]['source_references']:resources[ref['path']].add(key)
    def inventory(keys):
        a,b=(compose.request_inventory(p,keys) for p in (before,after))
        return dict(before=a,after=b,payload_delta_bytes=b['payload_bytes']-a['payload_bytes'],
            plain32_delta_bytes=b['plain_alloc32_bytes']-a['plain_alloc32_bytes'],
            PAL8_keys=sum(tpl.TEXTURE.unpack_from(after[k],48)[3]==5 for k in keys),
            scope='Unique selected key/reference union, not simultaneous target residency.')
    per_room={name:dict(**inventory(keys),reference_instances=instances[name]) for name,keys in sorted(rooms.items())}
    members=[dict(key='%08x-%08x'%k,before_sha256=sha(original[k]),selected_base_sha256=sha(before[k]),
        after_sha256=sha(after[k]),changed=original[k]!=after[k],changed_from_base=k in changed) for k in sorted(before)]
    return result,dict(schema='re4dc-canonical-PAL8-candidate-1',candidate_only=True,enabled=bool(enabled),
        original_pack_sha256=sha(original_pack),base_pack_sha256=sha(selected_pack),candidate_pack_sha256=sha(result),
        candidate_pack_bytes=len(result),archive_delta_from_base=len(result)-len(selected_pack),
        archive_delta_from_original=len(result)-len(original_pack),changed_from_base=len(changed),
        unchanged_from_base=len(before)-len(changed),changed_from_original=sum(r['changed'] for r in members),
        unchanged_from_original=sum(not r['changed'] for r in members),frames=frames,held=dict(held),members=members,
        before_inventory=compose.request_inventory(before,before),after_inventory=compose.request_inventory(after,after),
        per_room_world_reference_requests=per_room,
        effect_resource_selected_key_requests={name:inventory(keys) for name,keys in sorted(resources.items())},
        canonical_palettes=len(palettes),palette_entries=256 if palettes else 0,aligned_PAL4_slots=16 if palettes else 0,
        required_build_knobs=['TEX_PAL4_ALPHA=1','CAST_MIPMAP=1','TEX_PAL4_MIPMAP=1',
            'TEX_TWIDDLED_MIPMAP=1','TEX_PAL8_ALPHA=1','TEX_PAL8_MIPMAP=1'],
        sampler_policy='Existing dimensions, UV, material, wrap, mip chain and alpha flags retained; only exact palette representation changes.',
        limits=['Original bases and already-filtered levels stay exact as encoded RGBA, not a rendered hardware identity claim.',
            'Inherited native/VQ/PAL4 candidate knobs remain required; actor candidates stay separate and all unrelated members remain exact.',
            'One shared palette still needs combined actual PAL4/PAL8/UI capacity and KOS/VRAM/look qualification.',
            'Reference sums are not simultaneous residency. No FPS claim, renderer/SH4ZAM/recipe/default/release or SD change.']),before,after


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('original-pack','selected-pack','coverage','policy','output'):ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--generate',action='store_true')
    args=ap.parse_args(argv)
    if args.output.exists() or not args.output.parent.is_dir():ap.error('output must be a new private directory')
    original,base=args.original_pack.read_bytes(),args.selected_pack.read_bytes()
    if shutil.disk_usage(args.output.parent).free<3*len(base)+512*1024*1024:raise ValueError('insufficient private output headroom')
    cov,policy=args.coverage.read_bytes(),args.policy.read_bytes()
    if json.loads(policy)['original_coverage_sha256']!=sha(cov):raise ValueError('policy is bound to different original coverage bytes')
    result,report,before,after=build(original,base,json.loads(cov),json.loads(policy),enabled=args.generate)
    report.update(coverage_sha256=sha(cov),policy_sha256=sha(policy),tool_sha256=sha(Path(__file__).read_bytes()),
        converter_sha256=sha((TOOLS/'compact_native_pal8.py').read_bytes()))
    args.output.mkdir();(args.output/'pal8-packages').mkdir();outputs={}
    def write(rel,data):
        with (args.output/rel).open('xb') as f:f.write(data)
        outputs[rel]=dict(bytes=len(data),sha256=sha(data))
    write('tex.pak',result)
    for row in report['frames']:
        if row['selected']:
            key=tuple(int(x,16) for x in row['key'].split('-'));write('pal8-packages/'+row['key']+'.re4tex',after[key])
    write('candidate.json',(json.dumps(report,indent=2)+'\n').encode())
    write('outputs.json',(json.dumps(outputs,indent=2)+'\n').encode())
    (args.output/'SHA256SUMS').write_text(''.join('%s  %s\n'%(r['sha256'],p) for p,r in sorted(outputs.items())))
    print(json.dumps({k:report[k] for k in ('candidate_pack_sha256','changed_from_base','changed_from_original','archive_delta_from_base','canonical_palettes')}))
    return 0


if __name__=='__main__':raise SystemExit(main())
