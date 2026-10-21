#!/usr/bin/env python3
"""Bind source BIN materials to an explicitly supplied archive, coverage and pack.

Read only. This diagnoses assets; it does not establish an actual draw, selected
runtime alias, target look, speed or hardware acceptance. No automatic remapping.
"""
from __future__ import annotations
import argparse, hashlib, json, struct, sys
from pathlib import Path
TOOLS=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(TOOLS),str(TOOLS/'d367')]
import room_smd, convert_tpl as tpl, prepare_native_ui, texpack
from vram.vq_pak import read_pak


def sha(blob): return hashlib.sha256(blob).hexdigest()


def image_keys(rows, archive_sha, tpl_slot):
    """Require an unambiguous source-index binding for this exact archive."""
    bindings={}
    for row in rows:
        for ref in row['source_references']:
            if ref['file_sha256']!=archive_sha or ref['arc_index']!=tpl_slot: continue
            image=ref['image']; value=(row['key'],ref['width'],ref['height'])
            if image in bindings and bindings[image]!=value:
                raise ValueError('ambiguous source texture index')
            bindings[image]=value
    return bindings


def material_key(image, mask, flags, bindings):
    if image==255:return None
    if image not in bindings:raise ValueError('source colour image is unbound')
    color=bindings[image]
    if not flags&4:return color[0]
    if mask not in bindings:raise ValueError('source mask image is unbound')
    alpha=bindings[mask]
    if color[1:]!=alpha[1:]:raise ValueError('source colour/mask dimensions differ')
    return prepare_native_ui.material_pair_identity(color[0],alpha[0])


def audit(archive,coverage,pack,models):
    digest=sha(archive)
    entries=room_smd.tagged_entries(archive,'<')
    count=struct.unpack_from('<I',archive)[0]
    floor=16+8*count
    if any(start<floor or start>end or end>len(archive) for _,start,end in entries):
        raise ValueError('source archive entry is out of bounds')
    texpack.verify(pack); packages=read_pak(pack)
    rows=[]
    for bin_slot,tpl_slot in models:
        if not 4<=bin_slot<count+4 or not 4<=tpl_slot<count+4:
            raise ValueError('source model/TPL slot is outside archive')
        tag,start,end=entries[bin_slot-4]
        if tag.rstrip(b'\0')!=b'BIN':raise ValueError('requested source model is not BIN')
        if entries[tpl_slot-4][0].rstrip(b'\0')!=b'TPL':raise ValueError('requested source images are not TPL')
        data=archive[start:end]; layout=room_smd.bin_layout(data,'<')
        if layout['version'] not in (0x20010801,0x20030818):raise ValueError('unsupported source BIN version')
        bindings=image_keys(coverage['normal_rows'],digest,tpl_slot)
        parts=[]
        for part,(relative,size) in enumerate(room_smd.part_headers(data,'<',layout)):
            at=layout['ptr']['parts']+relative
            stop=at+32+size
            if at<layout['ptr']['parts'] or stop>min(len(data),layout['region']['parts'][1]):
                raise ValueError('source part stream overruns BIN')
            flags,image,mask=data[at+11],data[at+12],data[at+14]
            key=material_key(image,mask,flags,bindings)
            member=packages.get(tuple(int(x,16) for x in key.split('-'))) if key else None
            selected=None
            if member:
                h=tpl.HEADER.unpack_from(member);t=tpl.TEXTURE.unpack_from(member,h[5])
                selected=dict(key=key,sha256=sha(member),width=t[1],height=t[2],format=t[3],payload_bytes=t[5],flags=t[6],layout=t[7])
            parts.append(dict(part=part,header_offset=start+at,flags=flags,image=image,mask=mask,alpha_ref=data[at+20],polygon_count=struct.unpack_from('<I',data,at+28)[0],stream_bytes=size,
                stream_sha256=sha(data[at+32:stop]),source_color=bindings.get(image),source_mask=bindings.get(mask) if flags&4 else None,
                expected_key=key,package=selected,missing=key is not None and member is None))
        rows.append(dict(bin_slot=bin_slot,tpl_slot=tpl_slot,offset=start,bytes=end-start,sha256=sha(data),parts=parts))
    return dict(schema='re4dc-issue52-material-binding-1',archive_sha256=digest,pack_sha256=sha(pack),models=rows,
        limits=['Source and supplied-pack bindings only.','Not proof of actual runtime alias, draw, look, speed or hardware acceptance.'])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ['archive','coverage','pack','out']:ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--model',action='append',required=True,help='BIN:TPl archive slots, decimal or0xhex')
    args=ap.parse_args(); models=[tuple(int(x,0) for x in m.split(':')) for m in args.model]
    if any(len(m)!=2 for m in models):raise ValueError('model needs BIN:TPL slots')
    if args.out.exists():raise ValueError('refusing to overwrite diagnostic output')
    report=audit(args.archive.read_bytes(),json.loads(args.coverage.read_text()),args.pack.read_bytes(),models)
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(models=len(report['models']),parts=sum(len(m['parts']) for m in report['models']),missing=sum(p['missing'] for m in report['models'] for p in m['parts']),out=str(args.out))))
if __name__=='__main__':main()

