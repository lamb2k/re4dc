#!/usr/bin/env python3
"""Compose sealed compact bases and world mips without dropping shared chains.

The private opt-in candidate regenerates overlapping chains from the compact
base, reusing spare codebook slots. Lower-level error is explicit and requires
look acceptance; there are no game defaults, renderer or sampler changes.
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
from pathlib import Path
import shutil
import sys

TOOLS=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(TOOLS))
sys.path.insert(0,str(TOOLS/'d367'))
import convert_tpl as tpl
import mipmap_compact_vq as compact_mips
import mipmap_vq as vq
import texpack
from vram.vq_pak import read_pak
from world_candidate import rounded,sha


def request_inventory(packages,keys):
    rows=[tpl.TEXTURE.unpack_from(packages[k],48) for k in keys]
    payload=sum(t[5] for t in rows)
    plain=sum(rounded(t[5],32) for t in rows)
    placed=sum(rounded(t[5]+2016,32) if t[7]==tpl.PAYLOAD_VQ or t[5]<=2048
               else rounded(t[5],32) for t in rows)
    return dict(keys=len(rows),payload_bytes=payload,plain_alloc32_bytes=plain,
        ui_vram_page_retry_upper_request_bytes=placed,
        VQ_keys=sum(t[7]==tpl.PAYLOAD_VQ for t in rows),
        mipmapped_keys=sum(bool(t[6]&tpl.FLAG_MIPMAP) for t in rows))


def _read(pack):
    texpack.verify(pack)
    members=read_pak(pack)
    if texpack.build(members)[0]!=pack:
        raise ValueError("input does not have an exact canonical control")
    return members


def compose(original,compact_pack,world_pack,coverage,*,enabled=False,engine="auto"):
    before,compact,world=map(_read,(original,compact_pack,world_pack))
    if set(before)!=set(compact) or set(before)!=set(world):
        raise ValueError("candidate key namespaces differ")
    if coverage['source_pack_sha256']!=sha(original):
        raise ValueError("coverage describes another original pack")
    compact_keys={k for k in before if before[k]!=compact[k]}
    mip_keys={k for k in before if before[k]!=world[k]}
    coverage_rows={tuple(int(v,16) for v in r['key'].split('-')):r for r in coverage['normal_rows']}
    if set(coverage_rows)!=set(before):
        raise ValueError('coverage does not include exactly the original packed winners')
    if any(not coverage_rows[k]['source_owned_lossless_vq_selection'] for k in compact_keys):
        raise ValueError('compact input includes an owner-unclassified or unselected key')
    if any(not coverage_rows[k]['native_world_references'] for k in mip_keys):
        raise ValueError('world input includes a key without a selected native-world reference')
    overlap=compact_keys&mip_keys
    after=dict(before)
    regenerated=[]
    if enabled:
        after.update({k:compact[k] for k in compact_keys})
        after.update({k:world[k] for k in mip_keys-overlap})
        for key in sorted(overlap):
            after[key],row=compact_mips.add_mipmaps(compact[key],world[key],enabled=True,engine=engine)
            row['key']='%08x-%08x'%key
            regenerated.append(row)
        for key in mip_keys:
            if not tpl.TEXTURE.unpack_from(after[key],48)[6]&tpl.FLAG_MIPMAP:
                raise ValueError("composition dropped an existing selected mip chain")
    result,count=texpack.build(after)
    texpack.verify(result)
    changed={k for k in before if before[k]!=after[k]}
    if changed!=(compact_keys|mip_keys if enabled else set()) or not enabled and result!=original:
        raise ValueError("composition touched an unselected key or OFF differs")
    rooms=collections.defaultdict(set)
    for row in coverage['normal_rows']:
        key=tuple(int(v,16) for v in row['key'].split('-'))
        for ref in row['native_world_references']:
            rooms[ref['package']].add(key)
    per_room={}
    for name,keys in sorted(rooms.items()):
        a,b,c=(request_inventory(p,keys) for p in (before,world,after))
        per_room[name]=dict(original=a,previous_world_mips=b,composed=c,
            composed_minus_original_payload=c['payload_bytes']-a['payload_bytes'],
            composed_minus_original_plain32=c['plain_alloc32_bytes']-a['plain_alloc32_bytes'],
            composed_minus_previous_world_plain32=c['plain_alloc32_bytes']-b['plain_alloc32_bytes'],
            composed_minus_original_page_retry_upper=c['ui_vram_page_retry_upper_request_bytes']-a['ui_vram_page_retry_upper_request_bytes'],
            composed_minus_previous_world_page_retry_upper=c['ui_vram_page_retry_upper_request_bytes']-b['ui_vram_page_retry_upper_request_bytes'])
    report=dict(schema='re4dc-compact-world-mip-composition-1',candidate_only=True,enabled=bool(enabled),
        original_pack_sha256=sha(original),compact_input_pack_sha256=sha(compact_pack),
        previous_world_mip_pack_sha256=sha(world_pack),candidate_pack_sha256=sha(result),
        original_pack_bytes=len(original),candidate_pack_bytes=len(result),
        archive_delta_bytes=len(result)-len(original),packages=count,
        compact_base_keys=len(compact_keys),world_mip_keys=len(mip_keys),
        overlapping_keys=len(overlap),changed_keys=len(changed),unchanged_keys=count-len(changed),
        generated_mip_rows=regenerated,
        original_inventory=request_inventory(before,set(before)),
        previous_world_mip_inventory=request_inventory(world,set(world)),
        composed_inventory=request_inventory(after,set(after)),per_room=per_room,
        original_accepted_world_outputs_exact=len(mip_keys-overlap),
        other_compact_outputs_exact=len(compact_keys-overlap),
        exact_reference_lower_chains=sum(r['exact_all_reference_levels'] for r in regenerated),
        lower_chains_needing_look_review=sum(not r['exact_all_reference_levels'] for r in regenerated),
        sampler_policy='CAST_MIPMAP and existing Package TCW mip bit; unchanged dimensions, UVs, wrap, filter and MIPD configuration. Preserve SH4ZAM/SKIN_SH4ZAM and batch UV contract.',
        required_build_knobs=['CAST_MIPMAP=1','TEX_TWIDDLED_MIPMAP=1'] if enabled else [],
        resource_scope='Descriptor-derived requests for source-referenced keys, not observed allocations, simultaneous live residency, pinned/dynamic split, peak or largest block. UI_VRAM may retry payload+2016 on page-placement failure; its upper request is reported separately.',
        limits=['No global sampler change or mip addition to UI, text or the other compact-only keys.',
            'Lower native mip targets are deliberately filtered/quantized; exact full-resolution base is distinct from lower-level quality.',
            'No game build, visual acceptance, target VRAM, frame-time, physical console or release gate.'])
    return result,report,before,after


def bound_candidate(path,original):
    receipt=json.loads((path/'candidate.json').read_text())
    pack=(path/'tex.pak').read_bytes()
    if receipt.get('source_pack_sha256',receipt.get('original_pack_sha256'))!=sha(original) or receipt['candidate_pack_sha256']!=sha(pack):
        raise ValueError("sealed candidate source/archive hash mismatch")
    before,after=map(_read,(original,pack))
    if set(before)!=set(after):
        raise ValueError('sealed candidate key namespace differs')
    expected={r['key']:r for r in receipt['members']}
    if len(receipt['members'])!=len(before) or set(expected)!={'%08x-%08x'%k for k in before}:
        raise ValueError("sealed candidate member receipt is incomplete")
    for key in before:
        row=expected['%08x-%08x'%key]
        if (sha(before[key]),sha(after[key]),before[key]!=after[key])!=(row['before_sha256'],row['after_sha256'],row['changed']):
            raise ValueError("sealed candidate member SHA mismatch")
    return pack


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-pack',type=Path,required=True)
    ap.add_argument('--compact-candidate',type=Path,required=True)
    ap.add_argument('--world-mip-candidate',type=Path,required=True)
    ap.add_argument('--coverage',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--generate',action='store_true')
    ap.add_argument('--engine',choices=('auto','python','numpy'),default='auto')
    args=ap.parse_args(argv)
    if args.output.exists() or not args.output.parent.is_dir():
        ap.error('output must be a new private directory')
    original=args.source_pack.read_bytes()
    if shutil.disk_usage(args.output.parent).free < 3*len(original)+512*1024*1024:
        raise ValueError('insufficient private composition headroom')
    compact=bound_candidate(args.compact_candidate,original)
    world=bound_candidate(args.world_mip_candidate,original)
    coverage_bytes=args.coverage.read_bytes()
    result,report,before,after=compose(original,compact,world,json.loads(coverage_bytes),enabled=args.generate,engine=args.engine)
    report.update(updated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        coverage_sha256=sha(coverage_bytes),tool_sha256=sha(Path(__file__).read_bytes()),
        generator_sha256=sha((TOOLS/'mipmap_compact_vq.py').read_bytes()))
    report['members']=[dict(key='%08x-%08x'%key,before_sha256=sha(before[key]),
        after_sha256=sha(after[key]),changed=before[key]!=after[key]) for key in sorted(before)]
    args.output.mkdir()
    outputs={}
    def write(path,data):
        with path.open('xb') as f:f.write(data)
        outputs[path.relative_to(args.output).as_posix()]=dict(size=len(data),sha256=sha(data))
    write(args.output/'tex.pak',result)
    (args.output/'regenerated-mip-packages').mkdir()
    for row in report['generated_mip_rows']:
        key=tuple(int(v,16) for v in row['key'].split('-'))
        write(args.output/'regenerated-mip-packages'/(row['key']+'.re4tex'),after[key])
    write(args.output/'candidate.json',(json.dumps(report,indent=2)+'\n').encode())
    write(args.output/'outputs.json',(json.dumps(outputs,indent=2)+'\n').encode())
    (args.output/'SHA256SUMS').write_text(''.join('%s  %s\n'%(r['sha256'],p)
        for p,r in sorted(outputs.items())),encoding='ascii')
    print(json.dumps({k:report[k] for k in ('changed_keys','unchanged_keys','overlapping_keys',
        'exact_reference_lower_chains','lower_chains_needing_look_review','candidate_pack_sha256','archive_delta_bytes')}))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
