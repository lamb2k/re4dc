#!/usr/bin/env python3
"""Select source-bound common world sprites from a sealed EFF mip review set.

The reviewed bytes are reused exactly. This opt-in private composition keeps
fixed ID UI, missing input, mixed screen/world and custom/generator holds.
Static source policy is not runtime look/resource acceptance.
"""
from __future__ import annotations
import argparse
import collections
import json
from pathlib import Path
import shutil
import sys

TOOLS=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(TOOLS));sys.path.insert(0,str(TOOLS/'d367'))
import texpack
from effect_consumers import record_sampling
from compose_candidate import _read,bound_candidate,request_inventory
from world_candidate import sha


def select(original,base_pack,review_pack,review_receipt,policy,*,enabled=False):
    if policy.get('sampling_contract_version',1) not in (1,2):
        raise ValueError('unknown effect sampling contract version')
    source,base,review=map(_read,(original,base_pack,review_pack))
    if (set(source)!=set(base) or set(source)!=set(review) or
            review_receipt['original_pack_sha256']!=sha(original) or
            review_receipt['base_pack_sha256']!=sha(base_pack) or
            review_receipt['candidate_pack_sha256']!=sha(review_pack) or
            policy['original_source_pack_sha256']!=sha(original) or
            policy['selected_base_pack_sha256']!=sha(base_pack) or
            policy['review_candidate_sha256']!=sha(review_pack)):
        raise ValueError('effect selection ancestry hash/namespace mismatch')
    members={r['key']:r for r in review_receipt['members']}
    if len(members)!=len(source) or len(review_receipt['members'])!=len(source):
        raise ValueError('incomplete effect review member receipt')
    # The first review superset's member receipts are relative to its selected
    # base archive, not the original source. Require both complete ancestors.
    for k in source:
        name='%08x-%08x'%k;r=members.get(name)
        if r is None or (r['before_sha256'],r['after_sha256'],r['changed'])!=(sha(base[k]),sha(review[k]),base[k]!=review[k]):
            raise ValueError('effect review member differs from ancestor receipt')
    frames={r['key']:r for r in review_receipt['frames']}
    changed={'%08x-%08x'%k for k in source if review[k]!=base[k]}
    rows={r['key']:r for r in policy['rows']}
    if (len(frames)!=len(review_receipt['frames']) or set(frames)!=changed or
            len(rows)!=len(policy['rows']) or set(rows)!=changed):
        raise ValueError('effect policy/review key selection differs')
    selected=set();held=[]
    for name,row in rows.items():
        if row['decision']!='world-common-sprite-source-candidate':
            held.append(dict(key=name,decision=row['decision'],reasons=row['reasons']));continue
        bindings=row['source_bindings'];records=[r for b in bindings for r in b['records']]
        if row['direct_ID_UI_consumers'] or not bindings or any(not b['records'] for b in bindings):
            raise ValueError('world sprite policy lacks exclusive known source-record bindings')
        for b in bindings:
            meta=policy['source_files'].get(b['source_path'],{})
            if not meta.get('retained') or not meta.get('parsed') or meta['sha256']!=b['source_sha256']:
                raise ValueError('world sprite source is not an exact parsed input')
        contracts=[record_sampling(r,policy['common_sprite_ids'],extended=policy.get('sampling_contract_version')==2) for r in records]
        if any(c.startswith('hold-') for c in contracts) or not any(c.startswith('common-world-sprite') for c in contracts):
            raise ValueError('world sprite policy contains a held screen/custom/generator record')
        selected.add(tuple(int(v,16) for v in name.split('-')))
    after=dict(base)
    if enabled:after.update({k:review[k] for k in selected})
    result,count=texpack.build(after);texpack.verify(result)
    altered={k for k in base if after[k]!=base[k]}
    if altered!=(selected if enabled else set()) or not enabled and result!=base_pack:
        raise ValueError('unselected effect bytes changed or OFF differs')
    groups=collections.defaultdict(set)
    for k in selected:
        for frame in frames['%08x-%08x'%k]['library_proof']['frames']:
            groups[frame['room']].add(k)
    report=dict(schema='re4dc-selective-source-world-effect-mip-candidate-1',candidate_only=True,
        sampling_contract_version=policy.get('sampling_contract_version',1),
        enabled=bool(enabled),original_pack_sha256=sha(original),base_pack_sha256=sha(base_pack),
        source_pack_sha256=sha(original),review_pack_sha256=sha(review_pack),candidate_pack_sha256=sha(result),
        packages=count,selected_frames=len(selected),changed_from_base=len(altered),
        unchanged_from_base=count-len(altered),changed_from_original=sum(source[k]!=after[k] for k in source),
        candidate_pack_bytes=len(result),archive_delta_from_base=len(result)-len(base_pack),
        archive_delta_from_original=len(result)-len(original),
        family_counts=dict(collections.Counter(frames['%08x-%08x'%k]['family'] for k in selected)),
        held=held,frames=[frames['%08x-%08x'%k] for k in sorted(selected)],
        original_inventory=request_inventory(source,set(source)),before_inventory=request_inventory(base,set(base)),
        after_inventory=request_inventory(after,set(after)),
        group_frame_inventories={g:dict(before=request_inventory(base,keys),after=request_inventory(after,keys)) for g,keys in sorted(groups.items())},
        members=[dict(key='%08x-%08x'%k,before_sha256=sha(source[k]),after_sha256=sha(after[k]),
            changed=source[k]!=after[k],selected_base_sha256=sha(base[k]),changed_from_base=base[k]!=after[k]) for k in sorted(source)],
        required_build_knobs=review_receipt['required_build_knobs'] if enabled else [],
        sampler_policy=review_receipt['sampler_policy'],resource_scope=review_receipt['resource_scope'],
        limits=['Static source policy is not proof of exclusive runtime uses, actual spawn/draw, rendered look or VRAM.',
                'Lower levels remain filtered/palette/VQ candidates; original exact RGBA/alpha is a separate property.',
                'No runtime/default, recipe, release, SD, full game build or guest change.'])
    return result,report,base,after


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('source-pack','base-candidate','review-candidate','sampling-policy','output'):
        ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--generate',action='store_true')
    args=ap.parse_args(argv)
    if args.output.exists() or not args.output.parent.is_dir():ap.error('output must be a new private directory')
    source=args.source_pack.read_bytes()
    if shutil.disk_usage(args.output.parent).free<3*len(source)+512*1024*1024:raise ValueError('insufficient candidate headroom')
    base=bound_candidate(args.base_candidate,source)
    review=(args.review_candidate/'tex.pak').read_bytes()
    receipt_bytes=(args.review_candidate/'candidate.json').read_bytes();receipt=json.loads(receipt_bytes)
    policy_bytes=args.sampling_policy.read_bytes();policy=json.loads(policy_bytes)
    if policy['candidate_receipt_sha256']!=sha(receipt_bytes):raise ValueError('sampling policy review receipt SHA differs')
    result,report,before,after=select(source,base,review,receipt,policy,enabled=args.generate)
    report.update(sampling_policy_sha256=sha(policy_bytes),review_receipt_sha256=sha(receipt_bytes),
        tool_sha256=sha(Path(__file__).read_bytes()),
        record_sampling_source_sha256=sha((Path(__file__).parent/'effect_consumers.py').read_bytes()))
    args.output.mkdir();outputs={}
    def write(path,data):
        with path.open('xb') as f:f.write(data)
        outputs[path.relative_to(args.output).as_posix()]=dict(size=len(data),sha256=sha(data))
    write(args.output/'tex.pak',result);(args.output/'mip-packages').mkdir()
    for k in sorted(k for k in before if before[k]!=after[k]):write(args.output/'mip-packages'/('%08x-%08x.re4tex'%k),after[k])
    write(args.output/'candidate.json',(json.dumps(report,indent=2)+'\n').encode())
    write(args.output/'outputs.json',(json.dumps(outputs,indent=2)+'\n').encode())
    (args.output/'SHA256SUMS').write_text(''.join('%s  %s\n'%(r['sha256'],p) for p,r in sorted(outputs.items())),encoding='ascii')
    print(json.dumps({k:report[k] for k in ('selected_frames','family_counts','changed_from_original',
        'candidate_pack_bytes','archive_delta_from_base','archive_delta_from_original','candidate_pack_sha256')}))
    return 0


if __name__=='__main__':raise SystemExit(main())
