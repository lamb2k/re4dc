#!/usr/bin/env python3
"""Run the unchanged target package validator on the full partner PS2 rig.

full_rig_gate.py PACKAGE OUTPUT [--rooms-source STAGE] [--castle-primary PACK]
No Ashley LOD, alias exception, parser or storage expansion is enabled here.
Private outputs contain game data. Uses g++ in WSL; never starts a guest.
"""
import argparse
import importlib.util
import json
import subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
TOOLS=HERE.parent
GAME=TOOLS.parents[1]/'game'


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('package',type=Path);ap.add_argument('output',type=Path)
    ap.add_argument('--rooms-source',type=Path);ap.add_argument('--castle-primary',type=Path)
    a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    pt=module('registry_pack_test',TOOLS/'model_registry_pack_test.py')
    mat=(GAME/'coarse_actor_material.inc').read_text();reg=(GAME/'coarse_actor_owner_registry.inc').read_text()
    x,y=mat.index('struct Digest'),mat.index('struct SourceBlob');y=mat.index('\n',y)+1
    c=reg.index('namespace nmr {');d=reg.index('#else\n#include "native_model_registry.h"',c)
    types=('#pragma once\n#include <cstdint>\nnamespace re4dc_material {\n'+mat[x:y]+
        '#include "actor_material_records.inc"\n}\n'+reg[c:d])
    x=reg.index('nmr::Chunk registry_geom_view(');y=reg.index('\n}',x)+2
    (a.output/'pack_test_types.h').write_text(types+'\n'+reg[x:y]+'\n')
    flags=['RE4DC_NMR_ASHLEY=2','RE4DC_NMR_SLOTS=1','RE4DC_NMR_MASK=1','RE4DC_NMR_DROP_BUMP=1',
        'RE4DC_NMR_BONES=96','RE4DC_NMR_FACTS=128','RE4DC_ACTOR_PL08=1','RE4DC_NMR_POOL=1',
        'RE4DC_LEON_HEADLESS=1','RE4DC_LEON_PS2_RIG=1','RE4DC_ACTOR_GANADO_APP0_GRIP=1',
        'RE4DC_ACTOR_GANADO_PS2_STUMP=1','RE4DC_NMR_PARTNER=2','RE4DC_NMR_LOD=1',
        'RE4DC_NMR_POOL_LOD=1','RE4DC_NMR_IMMUTABLE_ALIAS=1','RE4DC_ROUTE_CH23=1',
        'RE4DC_ROUTE_CH22=1','RE4DC_NMR_SHIFT=1']
    cc=['g++','-std=c++17','-O1','-I',str(a.output),'-I',str(GAME),'-I',str(GAME/'platform/include')]
    def compile(source,output,wide=False):
        use=flags+(['RE4DC_NMR_ROLES5=1','RE4DC_NMR_R202_CAST_CAPACITY=1'] if wide else [])
        cmd=cc+[str(source)]+['-D'+s for s in use]+['-o',str(output)]
        run=subprocess.run(cmd,capture_output=True,text=True)
        (a.output/(output.name+'-compile.log')).write_text(run.stdout+run.stderr)
        if run.returncode:raise RuntimeError(run.stderr)
    exe=a.output/'reader';source=TOOLS/'model_registry_pack_test.cpp';compile(source,exe)
    layout_source=a.output/'layout.cpp'
    layout_source.write_text('#define main pack_reader_main\n#include "'+str(source)+'"\n#undef main\n'
        'int main(){std::printf("%u %u %u %u %u %u %u %u\\n",'
        're4dc_material::kBaseRoles,re4dc_material::kRoomRoles,re4dc_material::kRoleMaskWords,'
        'kRegChunks,kRegGeometry,kPackModels,kPackParts,kRegBones);}\n')
    compile(layout_source,a.output/'layout')
    layout=dict(zip(('base_roles','room_roles','role_mask_words','refs','geometry','models','part_facts','bones'),
        map(int,subprocess.check_output([str(a.output/'layout')],text=True).split())))
    good=a.package.read_bytes();generic,skipped=pt.cases(good);slots,_=pt.slot_cases(good)
    # Old cattle fixture edits of shared TPL body facts are a no-op here.
    replaced={'identity-ambiguous','role-range','role-capacity'}
    skipped+=['generic-identity-ambiguous: shared body fact edit is a no-op']
    override={'descriptor-sections':'descriptor','parents-short':'skeleton'}
    built=[(n,override.get(n,w),p) for n,w,p in generic if n not in replaced]
    built += [(n,override.get(n,w),p) for n,w,p in slots if n!='good']
    for name,why,mutate in [
        ('role-range','role',lambda p:p.put(p.rec('role',0,32)+4,7)),
        ('role-capacity','table',lambda p:(p.put(p.sec('role')['table']+12,layout['room_roles']+1),
            p.put(p.sec('role')['table']+8,(layout['room_roles']+1)*32))),
        ('nonpool-numbered-level','descriptor',lambda p:p.put(p.rec('desc',1,48)+44,
            p.u32(p.rec('desc',1,48)+44)|(1<<26)|(1<<25)|(1<<16))),
        ('ashley-alias-v2','header',lambda p:(p.put(8,2),p.put(56,1)))]:
        p=pt.Pack(good);mutate(p);built.append((name,why,p.fix()))
    files=[];expected={}
    for name,why,p in built:
        f=a.output/(name+'.re4nmr');f.write_bytes(p.b);files.append(str(f));expected[str(f)]=why
    result=subprocess.check_output([str(exe),'117']+files,text=True);rows=[]
    for line in result.splitlines():
        f,why,detail=line.rsplit(' ',2)
        rows.append(dict(case=Path(f).stem,got=why,detail=int(detail),expected=expected[f],ok=why==expected[f]))
    rooms=[]
    if a.rooms_source:
        rer=module('ashley_reroom',TOOLS/'ps2cast/ashley_reroom.py')
        for old in sorted(a.rooms_source.glob('dc/native/r*/partner.re4nmr')):
            room=old.parent.name;primary=old.parent/'registry.re4nmr'
            partner=a.output/(room+'-full.re4nmr');partner.write_bytes(rer.reroom(good,int(room[1:],16)))
            args=[str(exe),room[1:]]+([str(primary),'+'+str(partner)] if primary.exists() else [str(partner)])
            out=subprocess.check_output(args,text=True)
            rooms.append(dict(room=room,profile='actual narrow',result=out,ok=all(line.rsplit(' ',2)[1]=='none' for line in out.splitlines())))
    if a.castle_primary:
        rer=module('ashley_reroom_castle',TOOLS/'ps2cast/ashley_reroom.py')
        wide=a.output/'reader-existing-castle-wide';compile(source,wide,True)
        partner=a.output/'r202-full.re4nmr';partner.write_bytes(rer.reroom(good,0x202))
        out=subprocess.check_output([str(wide),'202',str(a.castle_primary),'+'+str(partner)],text=True)
        rooms.append(dict(room='r202',profile='existing castle wide, no Ashley expansion',result=out,
                          ok=all(line.rsplit(' ',2)[1]=='none' for line in out.splitlines())))
    report=dict(package=str(a.package),flags=flags,layout=layout,cases=rows,rooms=rooms,skipped=skipped,
        failures=sum(not r['ok'] for r in rows+rooms))
    (a.output/'results.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(dict(cases=len(rows),room_combinations=len(rooms),layout=layout,failures=report['failures']),indent=2))
    raise SystemExit(bool(report['failures']))


if __name__=='__main__':main()
