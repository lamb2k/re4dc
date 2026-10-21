#!/usr/bin/env python3
"""Recover exact hand/headless inputs and trace actual selected LOD UV paths."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import re
import shutil
import struct
import zlib
import atlas_split as atlas


def audit(uv,stream,tiles):
    words=list(struct.iter_unpack('<2H',uv));owners=Counter();corners=[]
    triangles=atlas.read_fe(stream)
    for triangle in triangles:
        triangle_owners=set()
        for c in triangle:
            u,v=words[c[2]];x,y=u/64,(32768-v)/64
            found=[name for name,t in tiles.items() if t['x']<=x<t['x']+t['width'] and t['y']<=y<t['y']+t['height']]
            if len(found)!=1:raise ValueError('dynamic corner owner absent or ambiguous')
            name=found[0];owners[name]+=1;triangle_owners.add(name);corners.append((x,y,tiles[name]))
        if len(triangle_owners)!=1:raise ValueError('dynamic triangle crosses tile owners')
    crosses={}
    for side in (512,256,128,64,32,16,8,4,2,1):
        scale=512//side;count=0
        for x,y,t in corners:
            a,b=math.floor(x/scale-.5),math.floor(y/scale-.5)
            count+=(a*scale<t['x'] or (a+2)*scale>t['x']+t['width'] or b*scale<t['y'] or (b+2)*scale>t['y']+t['height'])
        crosses[str(side)]=count
    return dict(triangles=len(triangles),corners=len(corners),owners=dict(owners),conservative_crossing_corners=crosses,
                selected_square128_tile_used=atlas.TARGET in owners,levels=stream[3],pending_lod=bool(stream[2]&128))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for arg in ('source-root','hands','head-dir','bound-elf','resolved-knobs','out'):
        ap.add_argument('--'+arg,type=Path,required=True)
    a=ap.parse_args()
    if a.out.exists():raise ValueError('preserve existing consumer recovery')
    a.out.mkdir(parents=True);inputs=a.out/'inputs';inputs.mkdir()
    manifest=json.loads((a.source_root/'leon-v1/inputs/original_release_manifest.json').read_text())
    tiles=json.loads((a.source_root/'leon-v1/inputs/leon_tiles.json').read_text())['source_uv_tiles']
    def selected(path,name):
        b=path.read_bytes();expected=manifest[name]
        if len(b)!=expected['size'] or atlas.sha(b)!=expected['sha256']:raise ValueError('original selected archive mismatch: '+name)
        shutil.copy2(path,inputs/path.name)
        return b,dict(original_path=name,size=len(b),sha256=atlas.sha(b),original_manifest_exact=True)
    hands,hproof=selected(a.hands,'dc/native/pl00/leon_hands_pl00.re4hp')
    h=struct.unpack_from('<8I',hands)
    if h[0]!=0x3150484c or h[1]&65535!=1 or h[6]!=len(hands) or atlas.hands_pack.fnv(hands[32:])!=h[7]:
        raise ValueError('hand directory identity')
    nrows,nblobs,nsrc=h[1]>>16,h[2]&65535,h[2]>>16
    if nrows>24 or nblobs>24 or nsrc>48:raise ValueError('hand directory capacity')
    hand_rows=[]
    for i in range(nblobs):
        e=struct.unpack_from('<BB11H',hands,32+nrows*12+i*24)
        offset=e[12]*32;parts={}
        for name,size in zip(('pos','nrm','uv','gx','weights'),e[6:11]):
            if offset<h[5] or offset+size>len(hands):raise ValueError('hand array bounds')
            parts[name]=hands[offset:offset+size];offset+=atlas.r32(size)
        item=audit(parts['uv'],parts['gx'],tiles)
        if item['triangles']!=e[5]:raise ValueError('hand triangle count')
        item.update(blob=i,role=e[0],flags=e[1],uv_sha256=atlas.sha(parts['uv']),stream_sha256=atlas.sha(parts['gx']))
        hand_rows.append(item)
    neck=a.head_dir/'ps2leon_neck.h';shutil.copy2(neck,inputs/neck.name)
    arrays=atlas.hands_pack.arrays(neck.read_text())['n']
    neck_row=audit(arrays['uv'],arrays['gx'],tiles)
    elf=a.bound_elf.read_bytes()
    if atlas.sha(elf)!='4c92ce29920476605c297bc5ea319bde9bbd24a1a5a5a6bc5012c4a31ebc9a2c':raise ValueError('unchanged QA ELF identity')
    anchors={name:dict(bytes=len(arrays[name]),sha256=atlas.sha(arrays[name]),occurrences=elf.count(arrays[name]))
             for name in ('pos','nrm','uv','gx')}
    if not all(row['occurrences'] for row in anchors.values()):raise ValueError('selected neck bytes absent from exact QA ELF')
    archives={};payloads=[]
    for name in ('pl00','pl08'):
        b,proof=selected(a.head_dir/(name+'.drs'),'em/'+name+'.drs');archives[name]=proof
        candidates=[];at=-1
        while True:
            at=b.find(b'RE4H',at+1)
            if at<0:break
            if at+128>len(b):continue
            w=struct.unpack_from('<32I',b,at)
            if w[1]!=1 or w[2]<128 or at+w[2]>len(b):continue
            payload=b[at:at+w[2]]
            if zlib.crc32(payload[128:])&0xffffffff==w[3]:candidates.append((w,payload))
        if len(candidates)!=1:raise ValueError('flying-head payload ambiguous')
        payloads.append(candidates[0])
    if payloads[0][1]!=payloads[1][1]:raise ValueError('pl00/pl08 flying-head payload differs')
    w,payload=payloads[0]
    face=audit(payload[w[14]:w[14]+w[15]],payload[w[20]:w[20]+w[21]],tiles)
    if face['triangles']!=w[22]:raise ValueError('flying face triangle count')
    knobs=dict(line.split('=',1) for line in a.resolved_knobs.read_text().splitlines() if '=' in line and not line.startswith('#'))
    lod={key:knobs[key] for key in ('LEON_LOD','NATIVE_ACTOR_LOD','NATIVE_ACTOR_UV16','LEON_HAND_PACK','LEON_HEADLESS')}
    if lod['LEON_LOD']!='0':raise ValueError('alternate package LOD is selected; recover its exact package first')
    code=atlas.TOOLS.parent/'game'/'platform'/'native_actor_fast.cpp'
    text=code.read_text()
    if 'blob->flags & kLodPending' not in text:raise ValueError('runtime LOD pending gate changed')
    result=dict(schema='re4dc-atlas-dynamic-consumers-1',original_manifest_sha256=atlas.sha((a.source_root/'leon-v1/inputs/original_release_manifest.json').read_bytes()),
        hands=dict(proof=hproof,blobs=nblobs,rows=nrows,sources=nsrc,uv_consumers=hand_rows),
        neck=dict(header_sha256=atlas.sha(neck.read_bytes()),exact_current_QA_ELF_anchors=anchors,sampling=neck_row),
        flying_head=dict(archives=archives,payload_sha256=atlas.sha(payload),face=face,
            hair=dict(triangles=w[27],uv_bytes=w[24],stream_bytes=w[26],material='separate colour/mask, repeat; never sample the body atlas')),
        lod=dict(resolved=lod,resolved_receipt_sha256=atlas.sha(a.resolved_knobs.read_bytes()),runtime_source_sha256=atlas.sha(code.read_bytes()),
            preencoded_streams_have_no_levels_or_pending_bit=all(not r['levels'] and not r['pending_lod'] for r in hand_rows+[neck_row,face]),
            interpretation='Generic LOD needs kLodPending to rebuild. These selected FE/v3 streams have no pending bit/extra levels. LEON_LOD package substitution is default0/unselected; its package is not an original manifest entry.'),
        runtime_sampling_look_and_residency_accepted=False)
    atlas.dump(a.out/'consumer-provenance.json',result)
    files=[p for p in sorted(a.out.rglob('*')) if p.is_file()]
    (a.out/'SHA256SUMS').write_text(''.join(atlas.sha(p.read_bytes())+'  '+p.relative_to(a.out).as_posix()+'\n' for p in files))
    print(json.dumps(dict(hand_blobs=nblobs,hand_corners=sum(r['corners'] for r in hand_rows),neck_triangles=neck_row['triangles'],flying_face_triangles=face['triangles'],lod=lod)))

if __name__=='__main__':main()
