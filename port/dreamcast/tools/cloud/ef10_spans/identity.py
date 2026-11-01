#!/usr/bin/env python3
"""Pinned OFF text/object identity and actual primary Make selector/target scope."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
DC=HERE.parents[2]
ROOT=DC.parents[1]
BASE='750d9abafbafd96fd6a42d130aed1018d2e96db9'

def run(command,**kw):
    p=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,**kw)
    assert p.returncode==0,p.stderr
    return p.stdout

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    stub=out/'stub';(stub/'dc').mkdir(parents=True)
    (stub/'dc/pvr.h').write_text('#pragma once\n#include <cstddef>\n#include <cstdint>\n'
        'struct pvr_vertex_t{std::uint32_t flags;float x,y,z,u,v;std::uint32_t argb,oargb;};\n'
        'struct pvr_poly_hdr_t{std::uint32_t words[8];};\n'
        '#define PVR_CMD_VERTEX 0xe0000000U\n#define PVR_CMD_VERTEX_EOL 0xf0000000U\n'
        'int pvr_prim(const void*,std::size_t);\n')
    includes=['-I'+str(stub),'-I'+str(DC/'game'),'-I'+str(DC/'game/platform'),
        '-I'+str(DC/'game/platform/include')]
    flags=['-DRE4DC_D349_RENDERER_STACK=1','-DRE4DC_MODEL_DRAW_PLANS=1','-DRE4DC_PLAN_OWNER_SCOPED=1',
           '-DRE4DC_STATIC_OBJ_BATCH=2','-DRE4DC_STATIC_OBJ_LIFETIME05=1','-DRE4DC_STATIC_OBJ_BATCH33=1']
    identity={}
    for filename,relative,kinds,extra in (
        ('native_model.cpp','game/platform/native_model.cpp',('text','object'),[]),
        ('model_bridge.cpp','game/model_bridge.cpp',('text',),['-D__sh__','-DRE4DC_GAME=1','-U__PPC__',
            '-I'+str(ROOT/'include'),'-I'+str(ROOT/'src'),'-I'+str(ROOT/'src/game')])):
        base=out/filename;base.write_bytes(subprocess.check_output(['git','show',f'{BASE}:port/dreamcast/{relative}'],cwd=ROOT))
        for kind in kinds:
            outputs=[]
            for source,mode,selector in ((base,'base',[]),(DC/relative,'absent',[]),(DC/relative,'zero',['-DRE4DC_STATIC_OBJ_SPANS10=0'])):
                path=out/f'{filename}-{kind}-{mode}'
                command=['g++','-std=c++20','-O2','-fno-ident',*includes,*flags,*extra,*selector,
                         *(['-E','-P'] if kind=='text' else ['-c']),str(source),'-o',str(path)]
                run(command);outputs.append(path.read_bytes())
            assert outputs[0]==outputs[1]==outputs[2],(filename,kind)
            identity[filename+' '+kind]={'bytes':len(outputs[0]),'sha256':hashlib.sha256(outputs[0]).hexdigest()}
    # Validate the exact expanded selector and every dependency using the real fragment.
    rules='OBJDIR := fixture\ninclude '+str(DC/'game/static_obj_spans10.mk')+'\n'
    targets=['model_bridge','platform/native_model','platform/native_draw_plan_owner','platform/native_ui']
    for t in targets:
        rules+='fixture/'+t+'.o:;@echo $('+('PLATFORM_CPPFLAGS' if t.startswith('platform/') else 'GAME_CPPFLAGS')+')\n'
    deps=['STATIC_OBJ_BATCH=2','STATIC_OBJ_LIFETIME05=1','MODEL_DRAW_PLANS=1','PLAN_OWNER_SCOPED=1','D349_RENDERER_STACK=1']
    def make(value=None,options=deps,target='model_bridge'):
        return subprocess.run(['make','--no-print-directory','-f','-','fixture/'+target+'.o',*options,
            *([] if value is None else ['STATIC_OBJ_SPANS10='+value])],input=rules,text=True,capture_output=True)
    assert make().returncode==make('0').returncode==0 and make().stdout==make('0').stdout=='\n'
    for value in ('','2','-1','%','0%','1%','0 1','1 1','yes','0 ','1 ','1\t',
                  '$(subst x, ,x)0','0$(subst x, ,x)','$(subst x, ,x)1','1$(subst x, ,x)'):
        assert make(value).returncode,value
    assert make('$(selected)',options=deps+['selected=1']).returncode==0
    assert make('$(selected)',options=deps+['selected=0']).stdout=='\n'
    for d in deps:
        name=d.split('=')[0]
        assert make('1',options=[x for x in deps if x!=d]+[name+'=0']).returncode,name
    for t in targets:
        p=make('1',target=t);assert p.returncode==0,p.stderr
        assert p.stdout.count('-DRE4DC_STATIC_OBJ_SPANS10=1')==int(t in targets[:2]),p.stdout
    # Expand actual primary commands. This does not execute any SDK or private producer.
    kos=out/'kos';kos.mkdir();(kos/'Makefile.rules').write_text('')
    (kos/'leon4k_runtime.h').write_text('// dry-run prerequisite\n')
    profile=['ACTOR_TRANSACTION=1','NATIVE_ACTOR=1','NATIVE_ACTOR_FAST=1','NATIVE_ACTOR_SKIN=1',
        'NATIVE_ACTOR_SKIN_LAZY=1','SKIN_PALETTE_LAZY=1','COARSE_SOURCE_ACTORS=1','COARSE_LEON=1',
        'COARSE_GANADO=1','COARSE_GANADO_CAST=1','COARSE_ONE_SUBMIT=1','COARSE_SKIN_FTRV=1','COARSE=1',
        'PACE_CATCHUP=2','PACE_TRANS_SKIP=4063','GAME_ATCHK=1','GAME_ATCHK_LIST=1',
        'COARSE_ACTOR_ASSET_DIR='+str(kos),'PVR_STREAM=1',*deps]
    arms=[]
    for selector in ([],['STATIC_OBJ_SPANS10=0'],['STATIC_OBJ_SPANS10=1']):
        p=subprocess.run(['make','--no-print-directory','-f','Makefile','-n','KOS_BASE='+str(kos),
            *profile,*selector,*['obj/'+t+'.o' for t in targets]],cwd=DC/'game',capture_output=True,text=True)
        assert p.returncode==0,p.stderr
        arms.append([line for line in p.stdout.splitlines() if line.startswith('kos-c++')])
    assert arms[0]==arms[1] and len(arms[2])==4
    for i,line in enumerate(arms[2]):assert line.count('-DRE4DC_STATIC_OBJ_SPANS10=1')==int(i<2),line
    for value in ('','2','%','0%','1%','0 1','1 ','$(subst x, ,x)1','1$(subst x, ,x)'):
        p=subprocess.run(['make','--no-print-directory','-f','Makefile','-n','KOS_BASE='+str(kos),
            *profile,'STATIC_OBJ_SPANS10='+value,'obj/model_bridge.o'],cwd=DC/'game',capture_output=True,text=True)
        assert p.returncode!=0,value
    report={'status':'PASS','base':BASE,'identity':identity,'make':'default0, exact expanded0/1, whitespace/dependencies, primary two-TU scope PASS'}
    (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
