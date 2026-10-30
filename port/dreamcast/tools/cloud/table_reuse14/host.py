#!/usr/bin/env python3
"""Whole actor TU A-B-A tables and emitted words; established host AVK/SQ adapters."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('actor32',HERE.parent/'build32/actor_runtime_host.py')
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
DC,ROOT=runtime.DC,runtime.ROOT
ADAPTER=runtime.adapter
BASE='400e8e40c99e1229cd9e17a427681d4bb963bc1c'

def source(text):
    text,adaptations=ADAPTER.host_source(text)
    for signature,counter in (('void skin_position_matrix(const Frame& f, unsigned i, float out[16]) {','table14_host_matrices'),
                               ('void avk_build_all(Frame& f) {','table14_host_builds')):
        assert text.count(signature)==1
        text=text.replace(signature,signature+'\n    ++'+counter+';')
    return text,adaptations

def flags(fast,grouped,enabled):
    defs=dict(RE4DC_ACTOR_TABLE_REUSE14=enabled,RE4DC_ACTOR_TRANSACTION=1,RE4DC_ACTOR_SKIN_OWNER_POOL=0,
        RE4DC_ACTOR_FORMAT32=1,RE4DC_ACTOR_LIGHT_FAST_ONLY=fast,RE4DC_ACTOR_UV16=0,
        RE4DC_ACTOR_DIRECT=1,RE4DC_ACTOR_BACKFACE_CONE=0,RE4DC_COARSE_ONE_SUBMIT=grouped,
        RE4DC_ACTOR_VTX_KERNEL=1,RE4DC_ACTOR_ASM=0,RE4DC_AVK_RIGID6=1,RE4DC_ACTOR_LIGHT_N16=0,
        RE4DC_ACTOR_NO_CLEAR=1,RE4DC_ACTOR_MOVCA=0,RE4DC_ACTOR_LOD_BUDGET=0,
        RE4DC_NATIVE_ACTOR_SKIN=1,RE4DC_NATIVE_ACTOR_SKIN_LAZY=1,RE4DC_ACTOR_PRELIT=1,
        RE4DC_ACTOR_SETUP_LEAN=1,RE4DC_COARSE_GATE_ONCE=0)
    return ['-std=c++20','-O2','-fno-fast-math','-ffp-contract=off','-ffunction-sections','-fdata-sections',
        *['-D'+k+'='+str(v) for k,v in defs.items()]]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--sanitize',action='store_true')
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    (out/'host/dc').mkdir(parents=True)
    (out/'host/dc/pvr.h').write_text(ADAPTER.PVR);(out/'host/dc/sq.h').write_text(ADAPTER.SQ)
    adapted,adaptations=source(ADAPTER.ACTOR.read_text());(out/'native_actor_host.inc').write_text(adapted)
    prefix=(ADAPTER.HERE/'fixture_actor.cpp.in').read_text()
    prefix=prefix[:prefix.index('void ordinary(')]
    prefix='unsigned table14_host_matrices=0,table14_host_builds=0;\n'+prefix
    (out/'fixture.cpp').write_text(prefix+(HERE/'cases.cpp.in').read_text())
    rows=[]
    for fast in (0,1):
        for grouped in (0,1):
            outputs=[]
            for enabled in (0,1):
                name=f'f{fast}-g{grouped}-e{enabled}';exe=out/name;raw=out/(name+'.ta')
                command=['g++',*flags(fast,grouped,enabled),'-I'+str(out/'host'),'-I'+str(DC/'game/platform'),
                    '-I'+str(DC/'game/platform/include'),'-I'+str(DC/'room'),str(out/'fixture.cpp'),
                    str(DC/'room/pvr_geometry.cpp'),str(DC/'room/source_lighting.cpp'),'-Wl,--gc-sections','-o',str(exe)]
                if args.sanitize:command[1:1]=['-fsanitize=address,undefined','-fno-sanitize-recover=all',
                    '-fno-omit-frame-pointer','-fno-pie','-no-pie']
                p=subprocess.run(command,capture_output=True,text=True)
                (out/(name+'.compile.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr[-14000:]
                p=subprocess.run([str(exe),str(raw)],capture_output=True,text=True,
                    env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1'))
                (out/(name+'.run.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr[-14000:]
                outputs.append(raw.read_bytes());rows.append(dict(fast=fast,grouped=grouped,enabled=enabled,result=json.loads(p.stdout)))
            assert outputs[0]==outputs[1],f'emitted words differ fast={fast} grouped={grouped}'
    paths=[ADAPTER.ACTOR,DC/'game/platform/include/native_actor_table_reuse14.inc',DC/'game/skin_table_reuse14.mk',
        DC/'game/Makefile',Path(__file__),HERE/'cases.cpp.in']
    report=dict(status='PASS',scope=__doc__,sanitized=args.sanitize,profiles=rows,adaptations=adaptations,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status='PASS',sanitized=args.sanitize,profiles=rows)))

if __name__=='__main__':main()
