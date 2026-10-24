#!/usr/bin/env python3
"""Count real paired-panel/material prerequisite hit rates before target work.

Counts are offline prerequisites only. Actual resident upload, source pose,
numeric frame guard and emitted geometry receipts remain unqualified.
"""
import argparse
import json
import hashlib
import re
import struct
import sys
from pathlib import Path

import numpy as np


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage',type=Path,required=True)
    ap.add_argument('--private',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--selected-source-lods',type=Path,help='RESEARCH ONLY: price actual selected source levels from replay rows')
    ap.add_argument('--rect21',action='store_true',help='match complete immutable descriptors, as qualified opaque_ready does')
    ap.add_argument('--rooms',nargs='+',default=['r10d','r102','r109','r112','r111','r113'])
    a=ap.parse_args()
    selections=None if a.selected_source_lods is None else json.loads(a.selected_source_lods.read_text())
    assert selections is None or len(a.rooms)==1,'selected level replay must name one authenticated room'
    header_path=Path(__file__).resolve().parents[3]/'room/texture_package.hpp'
    header=header_path.read_text()
    adapter=Path(__file__).resolve().parent.parent/'texture_rect21'
    table=(adapter/'scoped_representations.inc').read_text()
    representations={}
    for line in table.splitlines():
        if not line.startswith('{'):continue
        fields=[int(x,0) for x in re.findall(r'(0x[0-9a-f]+|[0-9]+)U',line)]
        assert len(fields)==11
        representations[tuple(fields[:4])]=tuple(fields[4:])
    assert len(representations)==798
    def bit(name):
        return 1<<int(re.search(name+r'\s*=\s*1U\s*<<\s*(\d+)U',header)[1])
    flags={name:bit(name) for name in ('kAlpha','kBinaryAlpha','kMipmap','kTopDrop')}
    forbidden_flags=flags['kAlpha']|flags['kBinaryAlpha']|flags['kTopDrop']
    sys.path[:0]=[str(a.private/'helpers'/'pvs'),str(a.private/'helpers'/'interior')]
    from pvs_certify import pairs
    from r4im import Pkg
    with (a.stage/'dc/tex.pak').open('rb') as f:
        magic,ver,n,offset,data,crc=struct.unpack('<8s5I',f.read(28))
        assert magic==b'RE4PAK1\0' and ver==1
        f.seek(offset);raw=f.read(16*n)
        index={(c,k):(off,size) for c,k,off,size in struct.iter_unpack('<4I',raw)}
        textures={}
        def texture(key):
            if key in textures:return textures[key]
            if key not in index:return None
            off,size=index[key];f.seek(off);head=f.read(48)
            th=struct.unpack('<8s10I',head)
            assert th[0]==b'RE4DCTX\0' and th[4]==1
            f.seek(off+th[5]);t=struct.unpack('<64s8I',f.read(96))
            result=dict(width=t[1],height=t[2],format=t[3],flags=t[6],payload=t[7],data_size=t[5],payload_crc32=th[8])
            textures[key]=result;return result
        reports=[]
        for name in a.rooms:
            d=a.stage/'dc/native'/name;p=Pkg(d/'ps2-world.re4mesh',d/'ps2-world.r4pw')
            policy=(d/'ps2-world.r4pw').read_bytes()
            b=(d/'ps2-world.ids').read_bytes();count=struct.unpack_from('<I',b,8)[0];ids=b[16:16+count]
            unique={i for i,v in enumerate(ids) if v<250 and ids.count(v)==1}
            report=dict(room=name,mesh_crc=f'{p.mesh_crc:08x}',physical_policy_crc=f'{p.sidecar_crc:08x}',
                        single_lod_opaque_instances=0,multiple_lod_opaque_instances=0,large_vertical_pairs=0,
                        material_shape_eligible_pairs=0,static_source_pairs=0,
                        conditional_source_pairs=0,material_rejections={},eligible_sources=[])
            histogram={}
            if selections is not None:
                actual=list(p.iter_clusters())
                for view in selections:
                    assert len(view['instances'])==len(actual)
                    for row,instance in zip(view['instances'],actual):
                        assert (row['placement'],row['part'],row['cluster'])==instance[:3]
                        if row['corners'] and row['level']>=0:
                            k=tuple(instance[:3]);h=histogram.setdefault(k,{})
                            h[row['level']]=h.get(row['level'],0)+1
            seen=set()
            for instance,(pi,part,cl,pas,cull,*_) in enumerate(p.iter_clusters()):
                if pas or cull not in (0,2):continue
                level_count=p.clusters[cl]['level_count']
                if level_count!=1 and selections is None:continue
                if selections is not None and (pi,part,cl) not in histogram:continue
                level=0 if selections is None else max(histogram[(pi,part,cl)],key=lambda k:(histogram[(pi,part,cl)][k],-k))
                assert 0<=level<level_count
                report['single_lod_opaque_instances' if level_count==1 else 'multiple_lod_opaque_instances']+=1
                meta=p.pmeta[part];key=(meta['crc'],meta['fnv']);tex=texture(key)
                reason=None
                if tex is None:reason='not in pack; loose residency must be inspected'
                elif tex['format']!=0:reason='not intrinsic RGB565'
                elif tex['flags']&forbidden_flags:reason='alpha, binary-alpha or top-drop flags'
                elif (tex['width'],tex['height'])!=(meta['w'],meta['h']):
                    descriptor=tuple(tex[k] for k in ('width','height','format','flags','payload','data_size','payload_crc32'))
                    logical=(*key,meta['w'],meta['h'])
                    if not a.rect21 or representations.get(logical)!=descriptor:reason='dimension mismatch without authenticated rect21 descriptor'
                # table_guard also requires the source part reserved-bit0 clear.
                policy_reserved=policy[32+16*part+15]
                if policy_reserved&1:reason='source material animation/reserved bit'
                for boundary,ts,identity in pairs(p,pi,cl,level):
                    nrm=np.cross(ts[0,1]-ts[0,0],ts[0,2]-ts[0,0])
                    area=sum(np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0])) for t in ts)
                    if area<=2e6 or abs(nrm[1])>=.5*np.linalg.norm(nrm):continue
                    report['large_vertical_pairs']+=1
                    if reason:
                        report['material_rejections'][reason]=report['material_rejections'].get(reason,0)+1
                        continue
                    report['material_shape_eligible_pairs']+=1
                    field=p.placements[pi]['placement'];conditional=field in unique
                    report['conditional_source_pairs' if conditional else 'static_source_pairs']+=1
                    source=(pi,part,cl)
                    if source not in seen:
                        seen.add(source);report['eligible_sources'].append(dict(placement=pi,field=field,part=part,cluster=cl,
                            conditional=conditional,source_level=level,source_level_count=level_count,selected_level_view_counts=None if selections is None else histogram[(pi,part,cl)],key=f'{key[0]:08x}-{key[1]:08x}',texture=tex))
            reports.append(report)
    out=dict(kind='actual package prerequisite census; no runtime cuts or predicted ms',
             actual_texture_flag_constants=flags,rect21_enabled=a.rect21,selected_source_lods_research=selections is not None,
             selected_source_lods_sha256=None if selections is None else hashlib.sha256(a.selected_source_lods.read_bytes()).hexdigest(),
             rect21_inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (adapter/'world_rect_bind.h',adapter/'scoped_representations.inc')},
             texture_header_sha256=hashlib.sha256(header_path.read_bytes()).hexdigest(),rooms=reports)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=1)+'\n')
    print(json.dumps(out))


if __name__=='__main__':main()
