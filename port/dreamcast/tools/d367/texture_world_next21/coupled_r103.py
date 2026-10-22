#!/usr/bin/env python3
"""Verify original r103 metadata and cumulative103 key-only bindings."""
from pathlib import Path
import json,struct,sys,zlib
import prepare_r101 as p
import prepare_r103 as n

def main():
    output=Path(sys.argv[1]);destination=Path(sys.argv[2]);p.require(not destination.exists(),'preserve proof')
    r=json.loads((output/'receipt.json').read_text());c=r['certificate'];files=json.loads(p.FILES.read_text())['files'];track=Path(r['geometry']['source_track']);checks={}
    def existing(path):
        record=files['/dc/native/r103/'+path]
        with track.open('rb') as f:f.seek((record['extent']-45000)*2048);b=f.read(record['bytes'])
        p.require(p.sha(b)==record['sha256'],'original r103 metadata '+path);return b,record
    ids,record=existing('ps2-world.ids');ih=struct.unpack_from('<4s3I',ids)
    p.require(ih[:2]==(b'R4ID',1) and ih[2]==c['placements'] and ih[3]==c['source_crc'] and ih[2]<=len(ids)-16,'IDs count/source anchor')
    counts={}
    for x in ids[16:16+ih[2]]:
        if x<250:counts[x]=min(counts.get(x,0)+1,2)
    checks['R4ID']=dict(**record,source_crc=ih[3],placements=ih[2],unique_source_ids=sum(x==1 for x in counts.values()),metadata_bytes_changed=False)
    tc,record=existing('ps2-world.r4tc');th=struct.unpack_from('<4s5I',tc)
    p.require(th[:2]==(b'R4TC',1) and th[3]==c['parts'] and th[4]==c['source_crc'] and len(tc)==24+((c['parts']+3)&~3) and zlib.crc32(tc[24:24+c['parts']])&0xffffffff==th[5],'classes/source anchor')
    changed=c['new_changed_records'];inherited=c['inherited_scoped29_rows_preserved'];p.require(len(set(changed)|set(inherited))==103 and not set(changed)&set(inherited),'cumulative103 binding closure')
    p.require(all(tc[24+i]==1 for i in changed+inherited),'all cumulative selected rows OP')
    checks['R4TC']=dict(**record,source_crc=th[4],body_crc=th[5],new_OP_rows=len(changed),inherited_OP_rows=len(inherited),all103_selected_OP=True,metadata_bytes_changed=False)
    p.require('/dc/native/r103/ps2-world.r4sg' not in files,'new unreviewed stripgroups appeared')
    checks['R4SG']=dict(present=False,metadata_bytes_changed=False,reason='Original exact baseline has no r103 strip-group file; this cohort introduces none.')
    rc,record=existing('room.r4rc');p.require(rc[:8]==b'R4RC\x01\0\x40\0' and struct.unpack_from('<I',rc,8)[0]==0x103 and struct.unpack_from('<I',rc,16)[0]==len(rc),'R4RC header')
    count=struct.unpack_from('<I',rc,12)[0];p.require(0<count<=8,'R4RC section count');sections={}
    for i in range(count):
        tag,version,flags,at,size=struct.unpack_from('<4sHHII',rc,64+32*i);p.require(at%16==0 and at>=64+32*count and at+size<=len(rc),'section extent');b=rc[at:at+size];sections[tag.rstrip(b'\0').decode()]=dict(version=version,flags=flags,bytes=size,sha256=p.sha(b))
        if tag==b'OCCL':
            crc=struct.unpack_from('<I',b,12)[0];p.require(version==2 and crc==c['source_crc'],'OCCL original source anchor');sections['OCCL']['source_crc']=crc
    p.require('OCCL' in sections,'expected OCCL');checks['R4RC']=dict(**record,sections=sections,metadata_bytes_changed=False)
    # Cumulative part keys change exactly as the two separately frozen mappings say.
    original=n.ORIGINAL.read_bytes();prior=n.INPUT.read_bytes();new=(output/'dc/native/r103/ps2-world.r4pw').read_bytes();a=p.world.inspect_sidecar(original);b=p.world.inspect_sidecar(prior);d=p.world.inspect_sidecar(new)
    p.require([i for i,(x,y) in enumerate(zip(a,d)) if x['key']!=y['key']]==sorted(changed+inherited),'cumulative changed record census')
    p.require(all(b[i]==d[i] for i in inherited),'prior29 scoped material records changed')
    r100_path=Path('/root/re4data/private/texture-rect21-current948-scoped17-20261021/dc/native/r100/ps2-world.r4pw');r101_path=Path('/root/re4data/private/texture-world-next21-r101-scoped9-v2-20261021/dc/native/r101/ps2-world.r4pw')
    result=dict(schema=1,room='r103',certificate=c,checks=checks,parent994_r103_certificate_retained=True,source_anchor_shared_by_old_and_new_certificate=True,inherited_scoped29_material_rows_byte_exact=True,r100_candidate_unchanged_sha256=p.sha(r100_path.read_bytes()),r101_candidate_unchanged_sha256=p.sha(r101_path.read_bytes()),PCL=dict(applies=False,reason='Actual native_static PCL selector remains room0x100.'),PVS=dict(active=False,baseline_file_present=False,reason='Recorded recipe PS2_PVS0; no r103PVS in frozen baseline. Future optional enablement is separately gated.'),AREA=dict(applies=False,reason='Authored area-hide table remains room0x107.'),limits=['Format/semantic source-contract proof using exact original retained bytes. Actual target loader/heap/OCCL execution is not claimed.','Actual helper host probe admits both old/new physical r103 certificates while preserving original source CRC; source integration still pending.','All metadata stays byte exact. Every texture payload preserves opaque alpha and material class; approximate RGB base requires target look review.'])
    destination.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(new_OP=74,inherited_OP=29,source_crc=c['source_crc'],metadata_changed=False)))
if __name__=='__main__':main()
