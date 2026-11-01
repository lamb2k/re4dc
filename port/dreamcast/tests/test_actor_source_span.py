#!/usr/bin/env python3
"""EF01 actual actor TU, immutable owner and parser-span consumer fixtures.

Existing host SQ/AVK adapters are transport/arithmetic boundaries; no console
performance or recovered gameplay acceptance is established by this test.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
DC = Path(__file__).resolve().parents[1]
ROOT = DC.parents[1]
spec = importlib.util.spec_from_file_location('span_runtime', DC/'tools/cloud/build32/actor_runtime_host.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


def make_policy():
    text='OBJDIR := fixture\ninclude '+str(DC/'game/actor_format32.mk')+'\nprint:;@echo $(GAME_CPPFLAGS):$(PLATFORM_CPPFLAGS)\n'
    def run(*options):
        return subprocess.run(['make','--no-print-directory','-f','-','print',*options],input=text.encode(),capture_output=True)
    absent=run()
    zero=run('ACTOR_SOURCE_SPAN=0')
    assert absent.returncode==zero.returncode==0 and absent.stdout==zero.stdout==b':\n'
    profile=['ACTOR_FORMAT32=1','NATIVE_ACTOR=1','NATIVE_ACTOR_FAST=1','NATIVE_ACTOR_UV16=1',
             'ACTOR_TRANSACTION=1','NATIVE_ACTOR_SKIN_LAZY=1']
    enabled=run(*profile,'ACTOR_SOURCE_SPAN=1')
    assert enabled.returncode==0 and enabled.stdout.count(b'-DRE4DC_ACTOR_SOURCE_SPAN=1')==2
    for bad in ('','2','0 1'):
        assert run(*profile,'ACTOR_SOURCE_SPAN='+bad).returncode!=0
    for missing in range(len(profile)):
        assert run(*[v for i,v in enumerate(profile) if i!=missing],'ACTOR_SOURCE_SPAN=1').returncode!=0
    return dict(absent_zero_flags=absent.stdout.decode().strip(),enabled_flags=enabled.stdout.decode().strip(),invalid_profiles=9)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    policy=make_policy()
    (out/'host/dc').mkdir(parents=True)
    (out/'host/dc/pvr.h').write_text(runtime.adapter.PVR)
    (out/'host/dc/sq.h').write_text(runtime.adapter.SQ)
    source, adaptations = runtime.adapter.host_source(runtime.adapter.ACTOR.read_text())
    (out/'native_actor_host.inc').write_text(source)
    producer = runtime.adapter.body((DC/'game/platform/include/coarse_actor_transaction.h').read_text(), 'inline bool source_span(')
    fixture = runtime.fixture()
    fixture = fixture[:fixture.rfind('int main(){')]
    fixture += '\n#include "coarse_actor_preflight.h"\nnamespace re4dc_actor {\n'+producer+'\n}\n'
    fixture += '\nextern "C" unsigned re4dc_actor_stream_begin(const void*,unsigned){return 0;}\nextern "C" void re4dc_actor_stream_end(unsigned,const void*,unsigned){}\n'
    fixture += (Path(__file__).with_suffix('.cpp.in')).read_text()
    (out/'fixture.cpp').write_text(fixture)
    rows=[]
    for pool in (0, 1):
        defs=dict(RE4DC_ACTOR_SOURCE_SPAN=1, RE4DC_ACTOR_TRANSACTION=1,
            RE4DC_ACTOR_SKIN_OWNER_POOL=pool, RE4DC_ACTOR_FORMAT32=1,
            RE4DC_ACTOR_LIGHT_FAST_ONLY=1, RE4DC_ACTOR_UV16=1,
            RE4DC_ACTOR_BACKFACE_CONE=2,
            RE4DC_ACTOR_DIRECT=1, RE4DC_COARSE_ONE_SUBMIT=1,
            RE4DC_ACTOR_VTX_KERNEL=1, RE4DC_ACTOR_ASM=0, RE4DC_AVK_RIGID6=1,
            RE4DC_ACTOR_LIGHT_N16=0, RE4DC_ACTOR_NO_CLEAR=1, RE4DC_ACTOR_MOVCA=0,
            RE4DC_ACTOR_LOD_BUDGET=0, RE4DC_NATIVE_ACTOR_SKIN=1,
            RE4DC_NATIVE_ACTOR_SKIN_LAZY=1, RE4DC_ACTOR_SETUP_LEAN=1)
        exe=out/('pool'+str(pool))
        cmd=['g++','-std=c++20','-O1','-g','-fno-fast-math','-ffp-contract=off',
            '-ffunction-sections','-fdata-sections','-Wall','-Wextra',
            *['-D'+k+'='+str(v) for k,v in defs.items()],
            '-I'+str(out/'host'),'-I'+str(DC/'game/platform'),
            '-I'+str(DC/'game/platform/include'),'-I'+str(DC/'room'),
            str(out/'fixture.cpp'),str(DC/'room/pvr_geometry.cpp'),
            str(DC/'room/source_lighting.cpp'),'-Wl,--gc-sections','-o',str(exe)]
        if args.sanitize:
            cmd[1:1]=['-fsanitize=address,undefined','-fno-sanitize-recover=all','-fno-omit-frame-pointer']
        built=subprocess.run(cmd,capture_output=True)
        (out/(exe.name+'.compile.log')).write_bytes(built.stdout+built.stderr)
        if built.returncode: raise RuntimeError(built.stderr.decode()[-10000:])
        env=dict(os.environ)
        if args.sanitize: env['ASAN_OPTIONS']='detect_leaks=0'
        run=subprocess.run([str(exe)],capture_output=True,env=env)
        (out/(exe.name+'.stdout')).write_bytes(run.stdout)
        (out/(exe.name+'.stderr')).write_bytes(run.stderr)
        if run.returncode: raise RuntimeError(run.stderr.decode()[-10000:])
        row=dict(pool=pool,command=cmd,result=json.loads(run.stdout))
        rows.append(row)
        print(json.dumps(row['result']),flush=True)
    inputs=[Path(__file__),Path(__file__).with_suffix('.cpp.in'),runtime.adapter.ACTOR,
        DC/'game/platform/include/actor_source_span.h',DC/'game/platform/include/actor_source_span.inc',
        DC/'game/platform/include/coarse_actor_transaction.h',DC/'game/coarse_actor_transaction.inc',
        DC/'game/platform/include/native_actor_owner_runs.inc']
    report=dict(status='PASS',arms=rows,make_policy=policy,adaptations=adaptations,scope=__doc__,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    (out/'actor-source-span.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__': main()
