#!/usr/bin/env python3
"""Private square PS2-frame mip candidate, retaining compact base encodings.

Only source-proved complete EFF frames qualify. Shared non-effect consumers,
rectangles, atlases and unknown owners are held. No game/default changes.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
from pathlib import Path
import re
import shutil
import sys

TOOLS=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(TOOLS))
sys.path.insert(0,str(TOOLS/'d367'))
import convert_tpl as tpl
import mipmap_pal4 as pal4
import mipmap_compact_vq as compact_mips
import mipmap_vq as vq
import texpack
from compose_candidate import bound_candidate,request_inventory
from world_candidate import sha
from vram.vq_pak import read_pak


def library_proofs(original,coverage,root):
    index=(root/'KEYS.tsv').read_bytes()
    bykey=collections.defaultdict(list)
    for row in csv.DictReader(index.decode().splitlines(),delimiter='\t'):
        bykey[row['key']].append(row)
    out={}
    for row in coverage['normal_rows']:
        if row['material']!='ps2-source':continue
        key=tuple(int(v,16) for v in row['key'].split('-'))
        for info in bykey.get(row['key'],[]):
            room=info['room']
            if not re.fullmatch(r'common|em[0-9a-z]{2}|wep[0-9a-z]{2}|r[0-9a-f]{3}',room):
                raise ValueError('unexpected effect-library group')
            path=root/room/(row['key']+'.re4tex')
            if path.is_file() and sha(path.read_bytes())==sha(original[key]):
                out[row['key']]=dict(path=str(path),sha256=sha(original[key]),
                    index_sha256=sha(index),frames=bykey[row['key']])
                break
    return out


def build_candidate(original,base_pack,coverage,proofs,*,enabled=False,engine='auto'):
    if coverage['source_pack_sha256']!=sha(original):
        raise ValueError('coverage belongs to another original pack')
    for pack in (original,base_pack):texpack.verify(pack)
    source,base=map(read_pak,(original,base_pack))
    if set(source)!=set(base) or texpack.build(base)[0]!=base_pack:
        raise ValueError('base key namespace/control differs')
    after=dict(base);rows=[];held=[];groups=collections.defaultdict(set)
    for owner in coverage['normal_rows']:
        if owner['material']!='ps2-source':continue
        name=owner['key'];key=tuple(int(v,16) for v in name.split('-'))
        if owner['width']!=owner['height']:
            held.append(dict(key=name,reason='rectangular-frame-needs-own-domain-contract'));continue
        if not owner['source_references'] or any(r['owner_category']!='effect' for r in owner['source_references']):
            held.append(dict(key=name,reason='shared-non-effect-consumer-sampling-open'));continue
        if name not in proofs or proofs[name]['sha256']!=sha(source[key]):
            raise ValueError('selected frame lacks exact source-library match: '+name)
        native=pal4.read_native_pal4(source[key])
        flags=native.header[10]
        if not flags>>31 or (flags&2047,(flags>>11)&2047)!=(native.size,native.size):
            held.append(dict(key=name,reason='covered-domain-is-not-the-complete-square-frame'));continue
        reference,palrow=pal4.add_mipmaps(source[key],enabled=enabled,engine=engine)
        fmt=tpl.TEXTURE.unpack_from(base[key],48)
        if fmt[7]==tpl.PAYLOAD_VQ:
            if enabled:
                after[key],row=compact_mips.add_mipmaps(base[key],reference,enabled=True,engine=engine)
            else:
                row=dict(changed=False,before_payload_bytes=fmt[5],after_payload_bytes=fmt[5],extra_payload_bytes=0)
            family='existing-lossless-VQ-base'
        else:
            if base[key]!=source[key]:raise ValueError('unexpected modified palette base')
            after[key],row=reference,palrow
            family='compact-PAL4'
        current=tpl.TEXTURE.unpack_from(after[key],48)
        row.update(key=name,family=family,library_proof=proofs[name],
            source_original_package_sha256=sha(source[key]),source_refs=owner['source_references'],
            before_alloc32=request_inventory(base,{key})['plain_alloc32_bytes'],
            after_alloc32=request_inventory(after,{key})['plain_alloc32_bytes'],
            original_base_RGBA_alpha_exact=True,covered_UV_flags_exact=True)
        rows.append(row)
        for info in proofs[name]['frames']:
            groups[info['room']].add(key)
    result,count=texpack.build(after);texpack.verify(result)
    changed={k for k in base if base[k]!=after[k]}
    selected={tuple(int(v,16) for v in r['key'].split('-')) for r in rows}
    if changed!=(selected if enabled else set()) or not enabled and result!=base_pack:
        raise ValueError('unselected FX key changed or OFF differs from selected base')
    group_rows={g:dict(before=request_inventory(base,keys),after=request_inventory(after,keys)) for g,keys in sorted(groups.items())}
    report=dict(schema='re4dc-square-PS2-effect-mip-candidate-1',candidate_only=True,enabled=bool(enabled),
        original_pack_sha256=sha(original),base_pack_sha256=sha(base_pack),candidate_pack_sha256=sha(result),
        base_pack_bytes=len(base_pack),candidate_pack_bytes=len(result),archive_delta_from_base=len(result)-len(base_pack),
        packages=count,selected_frames=len(rows),changed_from_base=len(changed),unchanged_from_base=count-len(changed),
        overall_changed_from_original=sum(source[k]!=after[k] for k in source),
        family_counts=dict(collections.Counter(r['family'] for r in rows)),held=held,frames=rows,
        before_inventory=request_inventory(base,set(base)),after_inventory=request_inventory(after,set(after)),
        group_frame_inventories=group_rows,
        required_build_knobs=['CAST_MIPMAP=1','TEX_TWIDDLED_MIPMAP=1','TEX_PAL4_ALPHA=1','TEX_PAL4_MIPMAP=1'] if enabled else [],
        sampler_policy='Existing effect sprite and haze paths use bilinear filtering, UV clamp, MODULATEALPHA and default MIPD. Covered dimensions, UVs, source blend/depth/fog and timing stay unchanged. Cached header keys include the complete PVR format/mip bit.',
        reference_scope='Palette mip references are new filtered/quantized candidates, not shipped or visually accepted chains. VQ lower-level error is measured against those references.',
        resource_scope='Per-group frame inventories overlap and are not simultaneous live effects, pool peaks or runtime allocation observations.',
        limits=['No blanket UI/font/atlas or unknown-owner conversion.','No new renderer, default, recipe, game build, guest, live VRAM, FPS, console or release claim.'])
    return result,report,base,after


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('source-pack','base-candidate','coverage','effects-library','output'):
        ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--generate',action='store_true')
    ap.add_argument('--engine',choices=('auto','python','numpy'),default='auto')
    args=ap.parse_args(argv)
    if args.output.exists() or not args.output.parent.is_dir():ap.error('output must be a new private directory')
    original=args.source_pack.read_bytes()
    if shutil.disk_usage(args.output.parent).free<3*len(original)+512*1024*1024:raise ValueError('insufficient private candidate headroom')
    base=bound_candidate(args.base_candidate,original)
    coverage=json.loads(args.coverage.read_text())
    proofs=library_proofs(read_pak(original),coverage,args.effects_library)
    result,report,before,after=build_candidate(original,base,coverage,proofs,enabled=args.generate,engine=args.engine)
    report.update(tool_sha256=sha(Path(__file__).read_bytes()),generator_sha256=sha((TOOLS/'mipmap_compact_vq.py').read_bytes()),exact_library_matches=len(proofs))
    report['members']=[dict(key='%08x-%08x'%k,before_sha256=sha(before[k]),after_sha256=sha(after[k]),changed=before[k]!=after[k]) for k in sorted(before)]
    args.output.mkdir();outputs={}
    def write(path,data):
        with path.open('xb') as f:f.write(data)
        outputs[path.relative_to(args.output).as_posix()]=dict(size=len(data),sha256=sha(data))
    write(args.output/'tex.pak',result)
    (args.output/'mip-packages').mkdir()
    for k in sorted(k for k in before if before[k]!=after[k]):write(args.output/'mip-packages'/('%08x-%08x.re4tex'%k),after[k])
    write(args.output/'candidate.json',(json.dumps(report,indent=2)+'\n').encode())
    write(args.output/'outputs.json',(json.dumps(outputs,indent=2)+'\n').encode())
    (args.output/'SHA256SUMS').write_text(''.join('%s  %s\n'%(r['sha256'],p) for p,r in sorted(outputs.items())),encoding='ascii')
    print(json.dumps({k:report[k] for k in ('selected_frames','family_counts','changed_from_base',
        'unchanged_from_base','overall_changed_from_original','archive_delta_from_base','candidate_pack_sha256')}))
    return 0


if __name__=='__main__':raise SystemExit(main())
