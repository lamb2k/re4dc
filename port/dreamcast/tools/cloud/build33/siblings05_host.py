#!/usr/bin/env python3
"""Actual EF05 sibling consumers with protected retired cells; host only."""
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
BASE='7c1f53fa9b2f88251ab17998904a27d127c65aa0'
spec=importlib.util.spec_from_file_location('extract',DC/'tools/d367/world_submit_spike/check_runtime.py')
extract=importlib.util.module_from_spec(spec);spec.loader.exec_module(extract)

def source(revision,path):
    return subprocess.check_output(['git','show',f'{revision}:{path.relative_to(ROOT)}'],cwd=ROOT,text=True) if revision else path.read_text()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--sanitize',action='store_true')
    p.add_argument('--source-revision')
    p.add_argument('--case',default='all')
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    bridge=DC/'game/model_bridge.cpp';ui=DC/'game/ui_bridge.cpp'
    b=source(a.source_revision,bridge);u=ui.read_text()
    begin=b.index('#if defined(RE4DC_SOB_DUMP) && RE4DC_SOB_DUMP\n')
    sig='extern "C" int re4dc_sob_bake_skip('
    end=b.index(sig);function=extract.function(b[end:],sig)
    end+=len(function);end=b.index('#endif',end)+len('#endif')
    siblings=b[begin:end].replace('#include "trans.h"','').replace('#include "trans_ot.h"','')
    begin=u.index('struct alignas(32) Room4Cell');end=u.index('#if defined(RE4DC_GC_CENSUS_TRIM)',begin)
    room=u[begin:end]
    for sig in ('void* room_alloc4(', 'void room_free4(',
                'extern "C" int re4dc_room4_live_generation(',
                'extern "C" int re4dc_room4_cell_valid(',
                'extern "C" unsigned re4dc_room4_cell_incarnation(',
                'extern "C" void re4dc_room4_open(', 'extern "C" void re4dc_room4_close(',
                'extern "C" int re4dc_room4_state('):
        room+='\n'+extract.function(u[u.rindex(sig):],sig)+'\n'
    template=HERE/'siblings05_fixture.cpp.in'
    fixture=out/'fixture.cpp'
    # Match the real bake table's 0x41 rest hash with a synthetic matrix word;
    # the actual bind/allocator path is exercised, rather than installing Obj.
    mul=16777619;inv=pow(mul,-1,1<<32);h=2166136261
    for _ in range(44):h=h*mul&0xffffffff
    forward={((h^i)*mul^j)*mul&0xffffffff:(i,j) for i in range(256) for j in range(256)}
    target=0x00ed2644;tail=None
    for k in range(256):
        for l in range(256):
            prior=((target*inv&0xffffffff)^l)*inv&0xffffffff;prior^=k
            if prior in forward:tail=bytes((*forward[prior],k,l));break
        if tail:break
    assert tail is not None
    fixture.write_text(template.read_text().replace('@ROOM@',room).replace('@SIBLINGS@',siblings)
        .replace('@REST_WORD@',str(int.from_bytes(tail,'little'))+'U'))
    command=['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-parentheses',
             '-DRE4DC_STATIC_OBJ_LIFETIME05=1','-DRE4DC_SOB_DUMP=1','-DRE4DC_STATIC_OBJ_BAKE=1',
             '-DRE4DC_NATIVE_ACTOR_SKIN_LAZY=1','-I',str(DC/'game/platform/include'),str(fixture),'-o',str(out/'fixture')]
    command.insert(3,'-DRE4DC_SIBLING05_FIXTURE_CURRENT='+str(int('bool rest_current(' in siblings)))
    if a.sanitize:command[2:3]=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-no-pie']
    build=subprocess.run(command,capture_output=True)
    (out/'compile.log').write_bytes(build.stdout+build.stderr)
    if build.returncode:raise RuntimeError(build.stderr.decode())
    run=subprocess.run([str(out/'fixture'),a.case],capture_output=True,
        env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
    (out/'run.log').write_bytes(run.stdout+run.stderr)
    receipt={'verdict':'PASS' if not run.returncode else 'FAIL','returncode':run.returncode,
        'revision':a.source_revision or 'working-tree','sanitize':a.sanitize,'case':a.case,
        'command':command,'checks':run.stdout.decode().splitlines(),
        'bridge_sha256':hashlib.sha256(b.encode()).hexdigest(),
        'inputs':{str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest()
                  for x in (ui,template,Path(__file__),DC/'game/platform/include/static_obj_lifetime05.hpp',
                            DC/'game/platform/include/static_obj_siblings05.hpp')}}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
    if run.returncode:raise SystemExit(1)

if __name__=='__main__':main()
