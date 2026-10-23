#!/usr/bin/env python3
"""Inventory chapter 1/2 world workload and existing AREA coverage before PVS.

This ranks full-detail package workload, not visibility yield or milliseconds.
Room/portal classification and captured interior views remain prerequisites.
Generated identities/statistics go to private evidence, never package assets.
"""
import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage',required=True,type=Path)
    ap.add_argument('--private',required=True,type=Path)
    ap.add_argument('--source',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path)
    a=ap.parse_args()
    sys.path.insert(0,str(a.private/'helpers'/'interior'));from r4im import Pkg
    native=a.source/'port/dreamcast/game/platform/native_static.cpp'
    text=native.read_text();start=text.index('namespace area {')
    area=text[start:text.index('\nconst Room* cur=',start)]
    area_rooms={int(x,16) for x in re.findall(r'\{0x([0-9a-f]+),0x[0-9a-f]+U,\d+,\{',area)}
    rows=[]
    for room in sorted((a.stage/'dc/native').glob('r1??')):
        if not (room/'ps2-world.re4mesh').exists():continue
        number=int(room.name[1:],16)
        if number>0x11f:continue
        p=Pkg(room/'ps2-world.re4mesh',room/'ps2-world.r4pw')
        ids=room/'ps2-world.ids';unique=set();ids_crc=None
        if ids.exists():
            b=ids.read_bytes();magic,ver,n,ids_crc=struct.unpack_from('<4sIII',b)
            assert magic==b'R4ID' and ver==1 and n==len(p.placements)
            values=b[16:16+n];unique={i for i,v in enumerate(values) if v<250 and values.count(v)==1}
        opq=trans=instances=single=0
        for pl in p.placements:
            m=p.meshes[pl['mesh']]
            for part in range(m['first_part'],m['first_part']+m['part_count']):
                first,n=p.plod[part]
                for c in range(first,first+n):
                    cl=p.clusters[c];fm,nm,_=p.levels[cl['first_level']]
                    vertices=sum(p.lets[x]['vc'] for x in range(fm,fm+nm))
                    if p.pmeta[part]['pass_']==0:opq+=vertices
                    else:trans+=vertices
                    instances+=1;single+=cl['level_count']==1
        room_source=a.source/f'src/st1/{room.name}.cpp'
        actions=[]
        if room_source.exists():
            for line_no,line in enumerate(room_source.read_text().splitlines(),1):
                if re.search(r'SmdSetTrans\(|SmdGetObjPtr\([^)]*\)->be_flag',line):
                    actions.append({'line':line_no,'source':line.strip()})
        rows.append(dict(room=room.name,mesh_sha256=sha(room/'ps2-world.re4mesh'),
                         physical_policy_sha256=sha(room/'ps2-world.r4pw'),
                         mesh_crc=f'{p.mesh_crc:08x}',physical_policy_crc=f'{p.sidecar_crc:08x}',
                         ids_source_crc=None if ids_crc is None else f'{ids_crc:08x}',
                         placements=len(p.placements),cluster_instances=instances,single_lod_instances=single,
                         full_detail_opaque_corners=opq,full_detail_other_pass_corners=trans,
                         unique_id_fields=len(unique),area_table_present=number in area_rooms,
                         recovered_source_visibility_actions=actions,
                         actual_pvs_cuts=None,actual_ms=None))
    rows.sort(key=lambda r:(-r['full_detail_opaque_corners'],r['room']))
    report=dict(kind='package workload census, not admitted visibility yield',
                source_head=__import__('subprocess').check_output(['wsl.exe','-d','Ubuntu-24.04','-u','root','--','git','-C','/root/work/lanes/interior-vis23','rev-parse','HEAD'],text=True).strip() if sys.platform=='win32' else None,
                existing_area_rooms=[f'r{x:03x}' for x in sorted(area_rooms)],
                area_source=str(native),area_source_sha256=sha(native),
                next_steps=['r109: audit existing init/hide/broken-state dynamic bindings before any new AREA table',
                            'r107: existing PS2_AREA_HIDE table and flags already implement area-dependent group hiding',
                            'r102/r112: historical 14% global ray ceilings are not current interior-view or runtime evidence',
                            'rank actual interior views by guarded selected-corner cuts before requesting target builds',
                            'castle remains deferred; no actor wall-cut work'],rooms=rows)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps({'rooms':len(rows),'area_rooms':report['existing_area_rooms'],
                      'full_detail_workload_order':[(r['room'],r['full_detail_opaque_corners']) for r in rows]}))


if __name__=='__main__':main()
