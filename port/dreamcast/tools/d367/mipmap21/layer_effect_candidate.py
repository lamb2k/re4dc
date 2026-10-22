#!/usr/bin/env python3
"""Layer newly source-qualified FX bytes without erasing later texture work."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import sys
TOOLS=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(TOOLS),str(TOOLS/'d367')]
import texpack
import compose_candidate as compose
import select_effect_candidate as selection
from world_candidate import sha


def layer(original,review_base,review_pack,review_receipt,policy,current,current_receipt,*,enabled=False):
    # Reuse the full exact-source/record/ancestor admission gate, not its labels.
    _,qualified,base,review=selection.select(original,review_base,review_pack,review_receipt,policy,enabled=True)
    source,before=map(compose._read,(original,current))
    if (set(source)!=set(before) or current_receipt.get('source_pack_sha256',current_receipt.get('original_pack_sha256'))!=sha(original)
            or current_receipt['candidate_pack_sha256']!=sha(current)):
        raise ValueError('current texture layer ancestry differs')
    rows={r['key']:r for r in current_receipt['members']}
    if len(rows)!=len(source) or len(current_receipt['members'])!=len(source):raise ValueError('current texture layer member receipt incomplete')
    for key in before:
        row=rows.get('%08x-%08x'%key)
        if row is None or (row['before_sha256'],row['after_sha256'],row['changed'])!=(sha(source[key]),sha(before[key]),source[key]!=before[key]):
            raise ValueError('current member is not bound to its receipt')
    selected={tuple(int(v,16) for v in r['key'].split('-')) for r in policy['rows'] if r['decision']=='world-common-sprite-source-candidate'}
    added=set();after=dict(before)
    for key in selected:
        if before[key]==review[key]:continue
        if before[key]!=base[key]:raise ValueError('selected effect conflicts with a later compact/mip layer; regenerate explicitly')
        added.add(key)
        if enabled:after[key]=review[key]
    result,_=texpack.build(after);texpack.verify(result)
    changed={k for k in after if after[k]!=before[k]}
    if changed!=(added if enabled else set()) or not enabled and result!=current:raise ValueError('OFF or unrelated current layer differs')
    members=[dict(key='%08x-%08x'%k,before_sha256=sha(source[k]),selected_base_sha256=sha(before[k]),after_sha256=sha(after[k]),
        changed=source[k]!=after[k],changed_from_base=k in changed) for k in sorted(before)]
    return result,dict(schema='re4dc-source-effect-followup-layer-1',candidate_only=True,enabled=bool(enabled),
        source_pack_sha256=sha(original),original_pack_sha256=sha(original),base_pack_sha256=sha(current),candidate_pack_sha256=sha(result),
        review_base_pack_sha256=sha(review_base),review_pack_sha256=sha(review_pack),sampling_contract_version=policy.get('sampling_contract_version',1),
        candidate_pack_bytes=len(result),archive_delta_from_base=len(result)-len(current),archive_delta_from_original=len(result)-len(original),
        qualified_effect_keys=len(selected),already_selected_effect_keys=len(selected)-len(added),newly_selected_effect_keys=len(added),
        changed_from_base=len(changed),unchanged_from_base=len(before)-len(changed),
        changed_from_original=sum(r['changed'] for r in members),unchanged_from_original=sum(not r['changed'] for r in members),
        frames=[r for r in review_receipt['frames'] if tuple(int(v,16) for v in r['key'].split('-')) in changed],
        held=qualified['held'],before_inventory=compose.request_inventory(before,before),after_inventory=compose.request_inventory(after,after),members=members,
        required_build_knobs=sorted(set(review_receipt['required_build_knobs'])|set(current_receipt.get('required_build_knobs',[]))|
            {'TEX_PAL4_MIPMAP=1','TEX_TWIDDLED_MIPMAP=1'}),sampler_policy=review_receipt['sampler_policy'],
        limits=['Source-qualified bytes reused exactly; original sampler/material/base/alpha contracts remain. Later unrelated texture members are preserved.',
            'Current aliases that differ from both exact review ancestors fail rather than losing newer compact bases or mips.',
            'Static bindings are not all dynamic/runtime consumers; missing/custom/RTT/screen and ID-UI holds remain open.',
            'No target look/palette/KOS/VRAM/timing, full build, guest, renderer/SH4ZAM, release/default or SD acceptance.']),before,after


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('source-pack','review-base-candidate','review-candidate','sampling-policy','current-candidate','output'):
        ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--generate',action='store_true');a=ap.parse_args(argv)
    if a.output.exists() or not a.output.parent.is_dir():ap.error('output must be a new private directory')
    source=a.source_pack.read_bytes()
    if shutil.disk_usage(a.output.parent).free<3*len(source)+512*1024*1024:raise ValueError('insufficient private layer headroom')
    base=compose.bound_candidate(a.review_base_candidate,source);current=compose.bound_candidate(a.current_candidate,source)
    review=(a.review_candidate/'tex.pak').read_bytes();review_bytes=(a.review_candidate/'candidate.json').read_bytes()
    pb=a.sampling_policy.read_bytes();policy=json.loads(pb)
    if policy['candidate_receipt_sha256']!=sha(review_bytes):raise ValueError('effect policy belongs to another review receipt')
    result,report,before,after=layer(source,base,review,json.loads(review_bytes),policy,current,json.loads((a.current_candidate/'candidate.json').read_text()),enabled=a.generate)
    report.update(sampling_policy_sha256=sha(pb),review_receipt_sha256=sha(review_bytes),tool_sha256=sha(Path(__file__).read_bytes()),
        record_sampling_source_sha256=sha((Path(__file__).parent/'effect_consumers.py').read_bytes()))
    a.output.mkdir();(a.output/'mip-packages').mkdir();outputs={}
    def write(name,data):
        with (a.output/name).open('xb') as f:f.write(data)
        outputs[name]=dict(size=len(data),sha256=sha(data))
    write('tex.pak',result)
    for key in sorted(k for k in after if after[k]!=before[k]):write('mip-packages/%08x-%08x.re4tex'%key,after[key])
    write('candidate.json',(json.dumps(report,indent=2)+'\n').encode());write('outputs.json',(json.dumps(outputs,indent=2)+'\n').encode())
    (a.output/'SHA256SUMS').write_text(''.join('%s  %s\n'%(v['sha256'],k) for k,v in sorted(outputs.items())))
    print(json.dumps({k:report[k] for k in ('newly_selected_effect_keys','changed_from_original','candidate_pack_bytes','candidate_pack_sha256','archive_delta_from_base')}))
    return 0


if __name__=='__main__':raise SystemExit(main())
