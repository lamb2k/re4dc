#!/usr/bin/env python3
"""Source-only full bridge OFF selection, sibling objects and primary Make."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

HERE=Path(__file__).resolve().parent;DC=HERE.parents[2];ROOT=DC.parents[1]
BASE='7c1f53fa9b2f88251ab17998904a27d127c65aa0'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m
host=load('siblings05_host',HERE/'siblings05_host.py')
profile=load('siblings05_profile',HERE.parent/'build18/build_profile.py')
def run(command,**kw):
    r=subprocess.run(command,capture_output=True,**kw)
    if r.returncode:raise RuntimeError(r.stderr.decode())
    return r.stdout
def tokens(data):
    return re.findall(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|\S',data.decode())
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    bridge=DC/'game/model_bridge.cpp';current=bridge.read_text()
    parent=host.source(BASE,bridge);rows={}
    # All source code is preprocessed; only includes are elided symmetrically.
    # This establishes complete bridge selection/token identity, not target PP.
    for arm,extra in [('absent',[]),('zero',['-DRE4DC_STATIC_OBJ_LIFETIME05=0'])]:
        pp=[]
        for label,body in [('parent',parent),('current',current)]:
            body=re.sub(r'^\s*#include[^\n]*','',body,flags=re.M)
            data=run(['g++','-E','-P','-x','c++','-','-DRE4DC_SOB_DUMP=1',
                      '-DRE4DC_STATIC_OBJ_BAKE=1','-DRE4DC_STATIC_OBJ_BATCH=2',*extra],input=body.encode())
            (out/f'{arm}-{label}-bridge.cpp').write_bytes(data);pp.append(data)
        assert tokens(pp[0])==tokens(pp[1]),arm
        rows[arm]={'whole_bridge_selected_tokens_equal':True,'tokens':len(tokens(pp[0]))}
    u=(DC/'game/ui_bridge.cpp').read_text()
    start=u.index('struct alignas(32) Room4Cell');end=u.index('#if defined(RE4DC_GC_CENSUS_TRIM)',start)
    room=u[start:end]
    for sig in ('void* room_alloc4(', 'void room_free4(',
                'extern "C" int re4dc_room4_live_generation(', 'extern "C" int re4dc_room4_cell_valid(',
                'extern "C" unsigned re4dc_room4_cell_incarnation(', 'extern "C" void re4dc_room4_open(',
                'extern "C" void re4dc_room4_close(', 'extern "C" int re4dc_room4_state('):
        room+='\n'+host.extract.function(u[u.rindex(sig):],sig)+'\n'
    for arm,define in [('absent',''),('zero','#define RE4DC_STATIC_OBJ_LIFETIME05 0\n')]:
        objects=[]
        for label,b in [('parent',parent),('current',current)]:
            begin=b.index('#if defined(RE4DC_SOB_DUMP) && RE4DC_SOB_DUMP\n')
            sig='extern "C" int re4dc_sob_bake_skip(';end=b.index(sig)
            end+=len(host.extract.function(b[end:],sig));end=b.index('#endif',end)+len('#endif')
            siblings=b[begin:end].replace('#include "trans.h"','').replace('#include "trans_ot.h"','')
            body=(HERE/'siblings05_fixture.cpp.in').read_text().replace('@ROOM@',room).replace('@REST_WORD@','0U')
            # Fixture assertions follow the extracted source. Pin only their
            # synthetic line numbers, leaving production tokens untouched.
            body=body.replace('@SIBLINGS@','#undef RE4DC_STATIC_OBJ_LIFETIME05\n'+define+siblings+'\n#line 10000\n')
            obj=out/f'{arm}-{label}.o'
            run(['g++','-std=c++20','-O2','-fno-ident','-DRE4DC_STATIC_OBJ_LIFETIME05=1',
                 '-DRE4DC_SIBLING05_FIXTURE_CURRENT=0','-DRE4DC_SOB_DUMP=1','-DRE4DC_STATIC_OBJ_BAKE=1',
                 '-DRE4DC_NATIVE_ACTOR_SKIN_LAZY=1','-I'+str(DC/'game/platform/include'),
                 '-x','c++','-','-c','-o',str(obj)],input=body.encode())
            objects.append(obj.read_bytes())
        assert objects[0]==objects[1],arm
        rows[arm]['actual_sibling_host_objects_equal']=True
        rows[arm]['object_sha256']=hashlib.sha256(objects[0]).hexdigest()
    kos=out/'make-kos';kos.mkdir();(kos/'Makefile.rules').write_text('')
    sdk=out/'make-sdk';(sdk/'include/sh4zam').mkdir(parents=True)
    (sdk/'include/sh4zam/shz_xmtrx.h').write_text('// make -n existence only; never compiled\n')
    # Full public release-chain parser, including ordered CH2 appends. No shell
    # recipe execution or private assets. Only make -n; no SDK/compiler call.
    options=['QA_MENU=0','QA_LINK=0','NMR_POOL_LOD=0','STATIC_OBJ_BAKE=1','PS2_PLACE_GATE=1',
             'WORLD_PREPARED09=0','STATIC_OBJ_SPANS10=0']
    make={}
    for arm,extra in [('absent',[]),('zero',['STATIC_OBJ_LIFETIME05=0']),
                      ('enabled',['STATIC_OBJ_LIFETIME05=1']),
                      ('dump-dependency',['STATIC_OBJ_LIFETIME05=0','SOB_DUMP=1']),
                      ('diagnostic',['STATIC_OBJ_LIFETIME05=1','SOB_DUMP=1'])]:
        dest=out/arm;dest.mkdir()
        command,recipe=profile.make_command(dest,ROOT,kos,sdk,[*options,*extra],dest/'obj/model_bridge.o')
        command.extend(str(dest/'obj'/unit) for unit in ('ui_bridge.o','platform/native_model.o','platform/native_static.o'))
        result=subprocess.run(command,cwd=DC/'game',capture_output=True,text=True)
        (out/f'{arm}-make.log').write_text(result.stdout+result.stderr)
        assert result.returncode==0,result.stderr
        lines=[line for line in result.stdout.splitlines() if ' -c ' in line and 'model_bridge.cpp' in line]
        assert len(lines)==1,lines
        flags=lines[0]
        assert '-DRE4DC_STATIC_OBJ_BAKE=1' in flags
        assert ('-DRE4DC_STATIC_OBJ_LIFETIME05=1' in flags)==(arm in ('enabled','diagnostic'))
        assert ('-DRE4DC_SOB_DUMP=1' in flags)==(arm in ('diagnostic','dump-dependency'))
        commands=[line for line in result.stdout.splitlines() if line.startswith('kos-c++ ') and ' -c ' in line]
        assert len(commands)==4,commands
        for line in commands:
            scoped='model_bridge.cpp' in line or ' -c ui_bridge.cpp ' in line
            assert ('-DRE4DC_STATIC_OBJ_LIFETIME05=1' in line)==(scoped and arm in ('enabled','diagnostic')),line
        make[arm]={'command':command,'recipe':recipe,'selected_commands':commands}
    receipt={'verdict':'PASS','baseline':BASE,'identity':rows,'primary_make':make,
        'limitations':['host objects cover actual extracted sibling source','includes-elided whole bridge token check',
                       'no SDK target preprocessing/object/link or runtime acceptance']}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'verdict':'PASS','identity':rows,'primary_make':list(make)},indent=2))
if __name__=='__main__':main()
