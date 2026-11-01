#!/usr/bin/env python3
"""Actual SOB producer, scoped plan owner and native Builder with synthetic packet edges."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
DC=HERE.parents[2]
ROOT=DC.parents[1]
spec=importlib.util.spec_from_file_location('extract',DC/'tools/d367/world_submit_spike/check_runtime.py')
extract=importlib.util.module_from_spec(spec);spec.loader.exec_module(extract)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--sanitize',action='store_true')
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    bridge=(DC/'game/model_bridge.cpp').read_text()
    start=bridge.index('#if defined(RE4DC_STATIC_OBJ_BATCH) && RE4DC_STATIC_OBJ_BATCH\n')
    sob=bridge[start:bridge.index('#if defined(RE4DC_SOB_DUMP)',start)]
    storage=(DC/'room/room_storage.cpp').read_text()
    arena='namespace re4dc::storage {\n'+''.join(extract.function(storage,s) for s in
        ('std::size_t align_up(', 'void Arena::init(', 'std::uint8_t* Arena::allocate(', 'void Arena::reset(', 'void Arena::rewind('))+'\n}\n'
    actor=(DC/'game/platform/native_actor_fast.cpp').read_text()
    registry_start=actor.index('struct SkinEntry {')
    registry=actor[registry_start:actor.index('// ---------------------------------------------------------- info context --',registry_start)]
    readers='\n'.join(extract.function(actor,s) for s in
        ('extern "C" int re4dc_actor_skin_register(', 'extern "C" void re4dc_actor_materialize('))
    text=(HERE/'fixture.cpp.in').read_text().replace('@SOB@',sob).replace('@ARENA@',arena)
    text=text.replace('@SKIN_REGISTRY@',registry).replace('@SKIN_READERS@',readers)
    fixture=out/'fixture.cpp';fixture.write_text(text)
    (out/'dc').mkdir();(out/'kos').mkdir()
    (out/'dc/pvr.h').write_text('#pragma once\n#include <cstdint>\n#include <cstddef>\n'
        'struct pvr_vertex_t{std::uint32_t flags;float x,y,z,u,v;std::uint32_t argb,oargb;};\n'
        'struct pvr_poly_hdr_t{std::uint32_t words[8];};\n'
        '#define PVR_CMD_VERTEX 0xe0000000U\n#define PVR_CMD_VERTEX_EOL 0xf0000000U\n'
        'int pvr_prim(const void*,std::size_t);\n')
    (out/'kos/fs.h').write_text('#pragma once\nusing file_t=int;\n')
    flags=['-std=c++20','-O2','-fstack-usage','-Wall','-Wextra','-Wno-unused-function','-Wno-unused-parameter',
           '-DRE4DC_STATIC_OBJ_BATCH=2','-DRE4DC_STATIC_OBJ_LIFETIME05=1','-DRE4DC_MODEL_DRAW_PLANS=1',
           '-DRE4DC_PLAN_OWNER_SCOPED=1','-DRE4DC_D349_RENDERER_STACK=1','-DRE4DC_MODEL_ROOM_STRIPS=1',
           '-DRE4DC_NATIVE_ACTOR=1','-DRE4DC_NATIVE_ACTOR_FAST=1','-DRE4DC_NATIVE_ACTOR_SKIN=1',
           '-DRE4DC_MODEL_STREAM_FIX=1','-DRE4DC_NATIVE_STATIC=1']
    if args.sanitize:flags[1:2]=['-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer','-no-pie']
    includes=['-I'+str(out),'-I'+str(DC/'game/platform'),'-I'+str(DC/'game/platform/include'),'-I'+str(DC/'room')]
    sources=[str(fixture),str(DC/'game/platform/native_model.cpp'),str(DC/'game/platform/native_draw_plan_owner.cpp'),
             str(DC/'room/native_draw_plan.cpp'),str(DC/'room/pvr_geometry.cpp'),str(DC/'room/source_lighting.cpp')]
    results=[];profiles=[]
    for lazy in (0,1):
        for enabled in (0,1):
            name=str(enabled) if lazy else f'{enabled}-lazy0';exe=out/f'spans{name}'
            command=['g++',*flags,f'-DRE4DC_STATIC_OBJ_SPANS10={enabled}',
                f'-DRE4DC_NATIVE_ACTOR_SKIN_LAZY={lazy}',*includes,*sources,'-o',str(exe)]
            run=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
            (out/f'compile-{name}.log').write_text(run.stdout+run.stderr)
            assert run.returncode==0,run.stderr
            run=subprocess.run([str(exe)],capture_output=True,text=True,env=dict(os.environ,
                ASAN_OPTIONS='detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
            (out/f'run-{name}.log').write_text(run.stdout+run.stderr)
            assert run.returncode==0,run.stderr
            profiles.append({'spans':enabled,'lazy':lazy,'result':run.stdout.strip()})
            if lazy:results.append(run.stdout.strip())
    paths=[DC/'game/Makefile',DC/'game/static_obj_spans10.mk',DC/'game/model_bridge.cpp',
        DC/'game/platform/native_model.cpp',DC/'game/platform/native_draw_plan_owner.cpp',
        DC/'game/platform/native_actor_fast.cpp',
        DC/'game/platform/include/static_obj_spans10.h',DC/'game/platform/include/static_obj_spans10.inc',
        HERE/'fixture.cpp.in',Path(__file__)]
    report={'status':'PASS','sanitized':args.sanitize,'runs':results,'skin_profiles':profiles,
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
