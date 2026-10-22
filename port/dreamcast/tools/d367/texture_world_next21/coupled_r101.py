#!/usr/bin/env python3
"""Verify unchanged r101 metadata against the proposed semantic certificate."""
from pathlib import Path
import importlib.util,json,struct,sys,zlib
spec=importlib.util.spec_from_file_location('p',Path(__file__).with_name('prepare_r101.py'));p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

def main():
    out=Path(sys.argv[1]);destination=Path(sys.argv[2]);p.require(not destination.exists(),'preserve metadata proof')
    report=json.loads((out/'receipt.json').read_text());c=report['certificate'];files=json.loads(p.FILES.read_text())['files'];track=Path(report['geometry']['source_track']);checks={}
    def existing(path):
        r=files['/dc/native/r101/'+path]
        with track.open('rb') as f:f.seek((r['extent']-45000)*2048);b=f.read(r['bytes'])
        p.require(p.sha(b)==r['sha256'],'unchanged metadata '+path);return b,r
    ids,identity=existing('ps2-world.ids');ih=struct.unpack_from('<4s3I',ids)
    p.require(ih[:2]==(b'R4ID',1) and ih[2]==c['placements'] and ih[3]==c['source_crc'] and ih[2]<=len(ids)-16,'R4ID source contract')
    counts={};
    for x in ids[16:16+ih[2]]:
        if x<250:counts[x]=min(counts.get(x,0)+1,2)
    checks['R4ID']=dict(**identity,source_crc=ih[3],placement_count=ih[2],unique_source_ids=sum(x==1 for x in counts.values()),physical_crc_would_fail=ih[3]!=c['physical_body_crc'],metadata_bytes_changed=False)
    tc,identity=existing('ps2-world.r4tc');th=struct.unpack_from('<4s5I',tc)
    p.require(th[:2]==(b'R4TC',1) and th[3]==c['parts'] and th[4]==c['source_crc'] and len(tc)==24+((c['parts']+3)&~3) and zlib.crc32(tc[24:24+c['parts']])&0xffffffff==th[5],'R4TC source contract')
    classes=[tc[24+x] for x in c['changed_records']];p.require(all(x==1 for x in classes),'selected parts not all opaque class')
    checks['R4TC']=dict(**identity,classifier=th[2],body_crc=th[5],source_crc=th[4],changed_records_classes=classes,all_selected_OP=True,metadata_bytes_changed=False)
    sg,identity=existing('ps2-world.r4sg');gh=struct.unpack_from('<4s7I',sg);mesh,mh,_=p.original_mesh()
    p.require(gh[:2]==(b'R4SG',1) and gh[2]==mh[6] and 0<gh[3]<=8 and gh[4:7]==(c['mesh_crc'],c['mesh_bytes'],c['source_crc']) and len(sg)==32+16*gh[2]*gh[3] and zlib.crc32(sg[32:])&0xffffffff==gh[7],'R4SG source contract')
    checks['R4SG']=dict(**identity,meshlets=gh[2],groups=gh[3],mesh_crc=gh[4],mesh_bytes=gh[5],source_crc=gh[6],body_crc=gh[7],metadata_bytes_changed=False)
    rc,identity=existing('room.r4rc');p.require(rc[:8]==b'R4RC\x01\0\x40\0' and struct.unpack_from('<I',rc,8)[0]==0x101 and struct.unpack_from('<I',rc,16)[0]==len(rc),'R4RC header')
    n=struct.unpack_from('<I',rc,12)[0];p.require(0<n<=8,'R4RC section count');sections={}
    for i in range(n):
        tag,version,flags,at,size=struct.unpack_from('<4sHHII',rc,64+32*i);p.require(at%16==0 and at>=64+32*n and at+size<=len(rc),'R4RC section extent');b=rc[at:at+size];sections[tag.rstrip(b'\0').decode()]=dict(version=version,flags=flags,bytes=size,sha256=p.sha(b))
        if tag==b'OCCL':
            anchor=struct.unpack_from('<I',b,12)[0];p.require(version==2 and anchor==c['source_crc'],'OCCL source anchor');sections['OCCL']['source_crc']=anchor
    p.require('OCCL' in sections,'r101 OCCL expected')
    checks['R4RC']=dict(**identity,sections=sections,metadata_bytes_changed=False)
    result=dict(schema=1,room='r101',certificate=c,checks=checks,PCL=dict(applies=False,reason='Actual native_static PCL selector is room0x100; addingr101 does not change that selector or any PCL constants.'),PVS=dict(active=False,reason='Existing recorded recipe PS2_PVS0; no r101 PVS file in frozen baseline membership. Future enablement requires its own exact source/mesh anchor gate.'),AREA=dict(applies=False,reason='Existing area-hide authored table is room0x107; r101 key-only remap changes no placement or dynamic predicates.'),SCPS_SCCN_SCDD=dict(metadata_bytes_changed=False,reason='All use unchanged geometry identity; this delta uses original r101room.r4rc byteexact, no sc21 alternate data admitted.'),limits=['Format/semantic source-contract proof on exact bytes, plus actual certificate helper host probe. No full target loader/heap/scheduler or runtime OCCL execution claimed.','Proposed source mapping must be integrated into the actual source then separately target qualified. Original metadata must remain byte exact; do not combine forged CRC rewrites.','All nine converted textures are RGB565 opaque across all levels; key remapping preserves all12OP class rows and all geometry/placements/material fields.'])
    destination.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:checks[k].get('source_crc') for k in checks}))
if __name__=='__main__':main()
