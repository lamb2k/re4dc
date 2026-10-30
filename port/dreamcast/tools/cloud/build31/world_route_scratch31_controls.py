#!/usr/bin/env python3
"""Actual primary Make/CPP route-scratch controls, with inert parse-only paths.

No SDK command or source TU is built. The unchanged public release chain is
read, then the separately qualified direct-strip profile is selected explicitly.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
GAME=ROOT/'port/dreamcast/game'
NATIVE=GAME/'platform/native_static.cpp'

def module(name,file):
    spec=importlib.util.spec_from_file_location(name,file)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);opts=ap.parse_args()
    out=opts.output.resolve();out.mkdir(parents=True,exist_ok=False)
    profile=module('route_public_profile',HERE/'stream_portal_profile.py')
    control=module('route_primary_make',HERE/'world_mutation31_target.py')
    release=profile.release_chain(out)
    # These overrides select the existing Build12 payload/profile. They do not
    # turn direct strips into a streamed/portal or broad ALLON configuration.
    separate=['SCENERY_DIRECT_STRIPS=1','SCENERY_LOCAL_INDEXED=0','MESH_FASTPATH=1',
        'MESH_VP_SCHED=1','HW_LEAN=1','SCENERY_CHUNK=1','WORLD_VERT=0','SCENERY21_AB=0',
        'SCENERY_DEDUP=0','SCENERY_CONE=0','SCENERY_PIECE_STATE=0','PS2_PVS=0',
        'PS2_INTERIOR_CULL=0','WORLD_RECT21=0','FOLIAGE_MIP24=0','SCENERY_STREAM=0','SCENERY_RECORD_SPLIT=0',
        'WORLD_SCRATCH=0','TA_HASH=0','CPU_BACKFACE=0','WORLD_PORTAL29=0',
        'WORLD_PORTAL_COMPLETION=0','WORLD_PORTAL_STREAM31=0']
    base=[*release,*profile.source_only_paths(out),*separate]
    absent=control.accepted(out,base)
    zero=control.accepted(out,[*base,'WORLD_ROUTE_SCRATCH31=0'])
    assert absent==zero and not any('RE4DC_WORLD_ROUTE_SCRATCH31' in x for x in absent)
    on=[*base,'WORLD_ROUTE_SCRATCH31=1'];enabled=control.accepted(out,on)
    (out/'enabled-command.json').write_text(json.dumps(enabled,indent=2)+'\n')
    assert enabled.count('-DRE4DC_WORLD_ROUTE_SCRATCH31=1')==1
    for target in ('platform/native_ui.o','platform/native_model.o'):
        p=control.make(out,on,target);assert p.returncode==0,p.stderr
        assert '-DRE4DC_WORLD_ROUTE_SCRATCH31' not in p.stdout
    cases=[]
    for value in ('','2','-1','%','0%','1%','0 1','1 1','0 ','1 '):
        p=control.make(out,[*base,'WORLD_ROUTE_SCRATCH31='+value],'platform/native_static.o')
        assert p.returncode!=0,('invalid selector',repr(value));cases.append('selector='+repr(value))
    # GNU Make strips whitespace immediately after command-line '=' before
    # storing a variable; the fragment sees the valid literal1 in this case.
    assert control.accepted(out,[*base,'WORLD_ROUTE_SCRATCH31= 1'])==enabled
    for name,value in [('SCENERY_DIRECT_STRIPS','0'),('MESH_FASTPATH','0'),('MESH_VP_SCHED','0'),
        ('HW_LEAN','0'),('SCENERY_STREAM','1'),('SCENERY_RECORD_SPLIT','1'),('WORLD_SCRATCH','1'),
        ('TA_HASH','1'),('CPU_BACKFACE','1'),('NATIVE_MESH','0'),('MESH_LOD','0'),
        ('PS2_WORLD_DRAW','0'),('PS2_WORLD_MESH','0'),('TA_DIRECT','0'),('MESH_DIRECT','0'),
        ('IO_ALIGNED','0'),('SCENERY_CHUNK','0'),('PS2_WORLD_ROOMS','0'),('SCENERY_LOCAL_INDEXED','1')]:
        p=control.make(out,[*on,name+'='+value],'platform/native_static.o')
        assert p.returncode!=0,name;cases.append(name+'='+value)
    # Exercise the actual consumer guard independently when Make is bypassed.
    src=NATIVE.read_text();start=src.index('#ifndef RE4DC_WORLD_ROUTE_SCRATCH31')
    guard=src[start:src.index('#if RE4DC_SCENERY_LOCAL_INDEXED || RE4DC_SCENERY_DIRECT_STRIPS',start)]
    defaults=src.index('#ifndef RE4DC_MESH_FASTPATH')
    guard+=src[defaults:src.index('#if RE4DC_SCENERY_CLIP_INDEXED26 && !RE4DC_MESH_FASTPATH',defaults)]
    definitions=[x for x in enabled if x.startswith('-DRE4DC_')]
    headers=[]
    for name in ('native-static.h','frontend30.h','scenery30.h','tahash.h'):
        p=control.make(out,on,name,dry=False);assert p.returncode==0,p.stderr
        headers.append(out/'obj'/name)
    settings='\n'.join(path.read_text() for path in headers)+'\n'
    def cpp(extra,success):
        p=subprocess.run(['g++','-E','-P','-x','c++',*definitions,'-'],input=(settings+extra+guard).encode(),capture_output=True)
        assert (p.returncode==0)==success,p.stderr.decode()
    cpp('',True)
    for name,value in [('SCENERY_DIRECT_STRIPS',0),('MESH_FASTPATH',0),('MESH_VP_SCHED',0),
        ('HW_LEAN',0),('SCENERY_STREAM',1),('SCENERY_RECORD_SPLIT',1),('WORLD_SCRATCH',1),
        ('TA_HASH',1),('CPU_BACKFACE',1),('WORLD_ROUTE_SCRATCH31',2)]:
        cpp('#undef RE4DC_'+name+'\n#define RE4DC_'+name+' '+str(value)+'\n',False)
    report=dict(status='PASS',scope=__doc__,release_assignments=len(release),
        primary_make_absent_zero_identity=True,affected_TU_only='platform/native_static.o',
        command_line_leading_whitespace='GNU Make normalizes assignment before selector evaluation',
        make_refusals=cases,cpp_refusals=10,target_compiled=False,
        generated_settings_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in headers},
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (Path(__file__),GAME/'Makefile',GAME/'scenery_data_variants.mk',NATIVE)})
    (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status='PASS',release_assignments=len(release),make_refusals=len(cases),cpp_refusals=10)))

if __name__=='__main__':main()
