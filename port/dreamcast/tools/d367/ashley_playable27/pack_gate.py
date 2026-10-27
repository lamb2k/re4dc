#!/usr/bin/env python3
"""Run the actual target reader on pl01 player packages and corruptions.

pack_gate.py PACKAGE OUTPUT --room 20d [--control ROOM:PACKAGE]
Uses the actual narrow play identity flags; it does not infer role capacity
from host pointer sizes. No format or allocation ceiling is widened.
"""
import argparse
import importlib.util
import json
import subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
TOOLS=HERE.parent
GAME=TOOLS.parents[1]/'game'
spec=importlib.util.spec_from_file_location('registry_pack_test',TOOLS/'model_registry_pack_test.py')
pt=importlib.util.module_from_spec(spec);spec.loader.exec_module(pt)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('package',type=Path);ap.add_argument('output',type=Path)
    ap.add_argument('--room',required=True)
    ap.add_argument('--control',action='append',default=[])
    a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=False)
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
    def compile(source,output,player=True):
        cmd=cc+[str(source)]+['-D'+s for s in flags]+(['-DRE4DC_NMR_PL_ASHLEY=1'] if player else [])+['-o',str(output)]
        run=subprocess.run(cmd,capture_output=True,text=True)
        (a.output/(output.name+'-compile.log')).write_text(run.stdout+run.stderr)
        if run.returncode:raise RuntimeError(run.stderr)
    exe=a.output/'reader';legacy=a.output/'reader-no-player'
    source=TOOLS/'model_registry_pack_test.cpp'
    compile(source,exe);compile(source,legacy,False)
    layout_source=a.output/'layout.cpp'
    layout_source.write_text('#define main pack_reader_main\n#include "'+str(source)+'"\n#undef main\n'
        'int main(){std::printf("%u %u %u %u %u %u %u %u\\n",'
        're4dc_material::kBaseRoles,re4dc_material::kRoomRoles,re4dc_material::kRoleMaskWords,'
        'kRegChunks,kRegGeometry,kPackModels,kPackParts,kRegBones);}\n')
    compile(layout_source,a.output/'layout')
    layout=dict(zip(('base_roles','room_roles','role_mask_words','refs','geometry','models','part_facts','bones'),
        map(int,subprocess.check_output([str(a.output/'layout')],text=True).split())))
    good=a.package.read_bytes()
    generic,skipped=pt.cases(good);slots,_=pt.slot_cases(good)
    # The old generic fixture assumes two-section cattle and distinct body TPLs.
    # Here hand descriptors intentionally share body facts, so its ambiguity edit
    # is a no-op. Use real out-of-range role/table mutations for this package.
    replaced={'blob-family','identity-ambiguous','role-range','role-capacity'}
    skipped+=['generic-identity-ambiguous: shared body fact edit is a no-op']
    expected_override={'descriptor-sections':'descriptor','parents-short':'skeleton'}
    built=[(n,expected_override.get(n,w),p) for n,w,p in generic if n not in replaced]
    built += [(n,expected_override.get(n,w),p) for n,w,p in slots if n!='good']
    for name,why,mutate in [
        ('enemy-family','blob',lambda p:p.put(p.rec('sblob',0,32)+4,2)),
        ('zero-family','blob',lambda p:p.put(p.rec('sblob',0,32)+4,0)),
        ('role-range','role',lambda p:p.put(p.rec('role',0,32)+4,7)),
        ('role-capacity','table',lambda p:(p.put(p.sec('role')['table']+12,layout['room_roles']+1),
            p.put(p.sec('role')['table']+8,(layout['room_roles']+1)*32))),
        ('leon-119-source','skeleton',lambda p:p.put(p.rec('desc',0,48)+44,
            (p.u32(p.rec('desc',0,48)+44)&~(255<<8))|(119<<8))),
        ('foreign-model','blob',lambda p:p.put(p.rec('desc',0,48)+20,3))]:
        p=pt.Pack(good);mutate(p);built.append((name,why,p.fix()))
    files=[];expected={}
    for name,why,p in built:
        f=a.output/(name+'.re4nmr');f.write_bytes(p.b);files.append(str(f));expected[str(f)]=why
    result=subprocess.check_output([str(exe),a.room]+files,text=True)
    rows=[]
    for line in result.splitlines():
        f,why,detail=line.rsplit(' ',2)
        rows.append(dict(case=Path(f).stem,got=why,detail=int(detail),expected=expected[f],ok=why==expected[f]))
    refusal=subprocess.check_output([str(legacy),a.room,str(a.package)],text=True).split()[-2:]
    rows.append(dict(case='reader-without-player-refuses',got=refusal,ok=refusal[0]=='blob'))
    for control in a.control:
        room,path=control.split(':',1)
        on=subprocess.check_output([str(exe),room,path],text=True).split()[-2:]
        off=subprocess.check_output([str(legacy),room,path],text=True).split()[-2:]
        rows.append(dict(case='unchanged-'+room,got=on,off=off,ok=on==off and on[0]=='none'))
    report=dict(package=str(a.package),room=a.room,flags=flags+['RE4DC_NMR_PL_ASHLEY=1'],layout=layout,
        cases=rows,skipped=skipped,failures=sum(not r['ok'] for r in rows))
    (a.output/'results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    raise SystemExit(bool(report['failures']))


if __name__=='__main__':main()
