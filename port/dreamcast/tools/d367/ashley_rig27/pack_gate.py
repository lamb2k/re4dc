#!/usr/bin/env python3
"""Run the actual target registry validator on private Ashley packages and corruptions.

pack_gate.py <package> <output dir> [--room 117] [--partner-base <registry>]
Includes the original alias overlap mutations and explicit Ashley type/level
refusals. The optional room package proves combined record capacity/admission.
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
    ap.add_argument('--room',default='117');ap.add_argument('--partner-base',type=Path)
    ap.add_argument('--control',action='append',default=[],help='Unchanged original package as roomhex:path; readers must agree')
    a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    mat=(GAME/'coarse_actor_material.inc').read_text();reg=(GAME/'coarse_actor_owner_registry.inc').read_text()
    x,y=mat.index('struct Digest'),mat.index('struct SourceBlob');y=mat.index('\n',y)+1
    c=reg.index('namespace nmr {');d=reg.index('#else\n#include "native_model_registry.h"',c)
    types=('#pragma once\n#include <cstdint>\nnamespace re4dc_material {\n'+mat[x:y]+
           '#include "actor_material_records.inc"\n}\n'+reg[c:d])
    x=reg.index('nmr::Chunk registry_geom_view(');y=reg.index('\n}',x)+2
    types+='\n'+reg[x:y]+'\n'
    (a.output/'pack_test_types.h').write_text(types)
    flags=['RE4DC_NMR_ASHLEY=2','RE4DC_NMR_SLOTS=1','RE4DC_NMR_MASK=1','RE4DC_NMR_DROP_BUMP=1',
           'RE4DC_NMR_BONES=96','RE4DC_NMR_FACTS=224','RE4DC_ACTOR_PL08=1','RE4DC_NMR_POOL=1',
           'RE4DC_NMR_ROLES5=1','RE4DC_NMR_PARTNER=2','RE4DC_NMR_LOD=1','RE4DC_NMR_POOL_LOD=1',
           'RE4DC_NMR_IMMUTABLE_ALIAS=1','RE4DC_ROUTE_CH23=1','RE4DC_ROUTE_CH22=1','RE4DC_NMR_SHIFT=1',
           'RE4DC_NMR_R202_CAST_CAPACITY=1']
    cc=['g++','-std=c++17','-O1','-I',str(a.output),'-I',str(GAME),'-I',str(GAME/'platform/include'),
        str(TOOLS/'model_registry_pack_test.cpp')]
    exe=a.output/'reader'
    cmd=cc+['-D'+s for s in flags]+['-DRE4DC_ASHLEY_LOD=1','-o',str(exe)]
    run=subprocess.run(cmd,capture_output=True,text=True)
    (a.output/'compile.log').write_text(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError(run.stderr)
    legacy=a.output/'reader-no-ashley-lod'
    subprocess.run(cc+['-D'+s for s in flags]+['-o',str(legacy)],check=True,capture_output=True)
    good=a.package.read_bytes();built,skipped=pt.alias_cases(good)
    files=[];expected={}
    for name,why,p in built:
        f=a.output/(name+'.re4nmr');f.write_bytes(p.b);files.append(str(f));expected[str(f)]=why
    # Mutate independently of the hash gate: recompute all outer hashes.
    for name,fn in {
        'ashley-level3':lambda p: p.put(p.rec('desc',3,48)+44,(p.u32(p.rec('desc',3,48)+44)&~(15<<26))|(3<<26)),
        'foreign-model':lambda p: p.put(p.rec('desc',0,48)+20,4),
        'wrong-role-count':lambda p: p.put(p.rec('desc',0,48)+28,6),
        'wrong-source-count':lambda p:p.put(p.rec('desc',0,48)+44,(p.u32(p.rec('desc',0,48)+44)&~(255<<8))|(140<<8)),
    }.items():
        p=pt.Pack(good);fn(p);p.fix();f=a.output/(name+'.re4nmr');f.write_bytes(p.b)
        files.append(str(f));expected[str(f)]='descriptor'
    out=subprocess.check_output([str(exe),a.room]+files,text=True)
    rows=[]
    for line in out.splitlines():
        f,why,detail=line.rsplit(' ',2);rows.append(dict(case=Path(f).stem,got=why,detail=int(detail),expected=expected[f],ok=why==expected[f]))
    legacy_result=subprocess.check_output([str(legacy),a.room,str(a.package)],text=True).split()[-2]
    rows.append(dict(case='legacy-refuses-ashley-alias',got=legacy_result,ok=legacy_result=='header'))
    if a.partner_base:
        pair=subprocess.check_output([str(exe),a.room,str(a.partner_base),'+'+str(a.package)],text=True)
        accepted=[line.rsplit(' ',2)[1] for line in pair.splitlines()]
        rows.append(dict(case='combined-room-and-partner',got=accepted,ok=accepted==['none','none']))
    for control in a.control:
        room,path=control.split(':',1)
        on=subprocess.check_output([str(exe),room,path],text=True).split()[-2:]
        off=subprocess.check_output([str(legacy),room,path],text=True).split()[-2:]
        rows.append(dict(case='unchanged-'+room,got=on,legacy=off,ok=on==off and on[0]=='none'))
    failures=sum(not r['ok'] for r in rows)
    report=dict(package=str(a.package),room=a.room,cases=rows,skipped=skipped,failures=failures)
    (a.output/'results.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    raise SystemExit(bool(failures))


if __name__=='__main__':main()
