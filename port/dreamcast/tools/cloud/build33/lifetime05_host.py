#!/usr/bin/env python3
"""Run actual SOB and room-cell functions with synthetic allocation/submission edges."""
import argparse, hashlib, importlib.util, json, os, subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
DC=HERE.parents[2]
ROOT=DC.parents[1]
spec=importlib.util.spec_from_file_location('extract',DC/'tools/d367/world_submit_spike/check_runtime.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
function=module.function

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--sanitize',action='store_true')
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    bridge=DC/'game/model_bridge.cpp';ui=DC/'game/ui_bridge.cpp'
    b=bridge.read_text();u=ui.read_text()
    start=b.index('#if defined(RE4DC_STATIC_OBJ_BATCH) && RE4DC_STATIC_OBJ_BATCH\n')
    sob=b[start:b.index('#if defined(RE4DC_SOB_DUMP)',start)]
    begin=u.index('struct alignas(32) Room4Cell')
    end=u.index('#if defined(RE4DC_GC_CENSUS_TRIM)',begin)
    room=u[begin:end]
    for signature in ('void* room_alloc4(', 'void room_free4(',
                      'extern "C" int re4dc_room4_live_generation(',
                      'extern "C" int re4dc_room4_cell_valid(',
                      'extern "C" unsigned re4dc_room4_cell_incarnation(',
                      'extern "C" void re4dc_room4_open(',
                      'extern "C" void re4dc_room4_close(',
                      'extern "C" int re4dc_room4_state('):
        room+='\n'+function(u[u.rindex(signature):],signature)+'\n'
    template=HERE/'lifetime05_fixture.cpp.in'
    source=template.read_text().replace('@ROOM@',room).replace('@SOB@',sob)
    fixture=out/'fixture.cpp';fixture.write_text(source)
    binary=out/'fixture'
    command=['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function',
             '-DRE4DC_STATIC_OBJ_BATCH=2','-DRE4DC_STATIC_OBJ_LIFETIME05=1',
             '-I',str(DC/'game/platform/include'),str(fixture),'-o',str(binary)]
    if args.sanitize:command[2:3]=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie']
    compile=subprocess.run(command,capture_output=True)
    (out/'compile.log').write_bytes(compile.stdout+compile.stderr)
    if compile.returncode:raise RuntimeError(compile.stderr.decode())
    env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    run=subprocess.run([str(binary)],capture_output=True,env=env)
    (out/'run.log').write_bytes(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError(f'fixture exit {run.returncode}: '+run.stderr.decode())
    paths=(bridge,ui,template,Path(__file__),DC/'game/platform/include/static_obj_lifetime05.hpp')
    receipt={'verdict':'PASS','sanitized':args.sanitize,'command':command,'tests':run.stdout.decode().splitlines(),
             'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
