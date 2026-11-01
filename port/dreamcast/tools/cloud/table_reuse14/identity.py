#!/usr/bin/env python3
"""Whole hosted actor OFF text/object identity and real primary Make scope."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import host

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    (out/'host/dc').mkdir(parents=True)
    (out/'host/dc/pvr.h').write_text(host.ADAPTER.PVR);(out/'host/dc/sq.h').write_text(host.ADAPTER.SQ)
    base=subprocess.check_output(['git','show',host.BASE+':port/dreamcast/game/platform/native_actor_fast.cpp'],cwd=host.ROOT,text=True)
    current=host.ADAPTER.ACTOR.read_text();identity={}
    includes=['-I'+str(out/'host'),'-I'+str(host.DC/'game/platform'),'-I'+str(host.DC/'game/platform/include')]
    for fast in (0,1):
        common=[x for x in host.flags(fast,1,0) if not x.startswith('-DRE4DC_ACTOR_TABLE_REUSE14=')]
        for kind in ('text','object'):
            values=[]
            for mode,source,extra in (('base',base,[]),('absent',current,[]),('zero',current,['-DRE4DC_ACTOR_TABLE_REUSE14=0'])):
                adapted,_=host.ADAPTER.host_source(source);target=out/f'f{fast}-{mode}-{kind}'
                p=subprocess.run(['g++',*common,*includes,*extra,'-fno-ident','-x','c++','-',
                    *(['-E','-P'] if kind=='text' else ['-c']),'-o',str(target)],input=adapted,
                    capture_output=True,text=True)
                assert p.returncode==0,p.stderr[-12000:];values.append(target.read_bytes())
            assert values[0]==values[1]==values[2],(fast,kind)
            identity[f'fast{fast}-{kind}']={'bytes':len(values[0]),'sha256':hashlib.sha256(values[0]).hexdigest()}
    deps=['ACTOR_TRANSACTION=1','NATIVE_ACTOR_FAST=1','ACTOR_SKIN_OWNER_POOL=0']
    targets=['platform/native_actor_fast','coarse_actor','src/game/trans','platform/native_ui']
    rules='OBJDIR := fixture\ninclude '+str(host.DC/'game/skin_table_reuse14.mk')+'\n'
    for t in targets:rules+='fixture/'+t+'.o:;@echo $('+('PLATFORM_CPPFLAGS' if t.startswith('platform/') else 'GAME_CPPFLAGS')+')\n'
    def make(value=None,options=deps,target=targets[0]):
        return subprocess.run(['make','--no-print-directory','-f','-','fixture/'+target+'.o',*options,
            *([] if value is None else ['ACTOR_TABLE_REUSE14='+value])],input=rules,text=True,capture_output=True)
    assert make().returncode==make('0').returncode==0 and make().stdout==make('0').stdout=='\n'
    for value in ('','2','-1','%','0%','1%','0 1','1 1','0 ','1 ','1\t','$(subst x, ,x)1','1$(subst x, ,x)'):
        assert make(value).returncode,value
    assert make('$(selected)',deps+['selected=1']).returncode==0
    assert make('$(selected)',deps+['selected=0']).stdout=='\n'
    for d in deps:
        key,value=d.split('=');assert make('1',[x for x in deps if x!=d]+[key+'='+('1' if value=='0' else '0')]).returncode,d
    for t in targets:
        p=make('1',target=t);assert p.returncode==0,p.stderr
        assert p.stdout.count('-DRE4DC_ACTOR_TABLE_REUSE14=1')==int(t==targets[0])
    kos=out/'kos';kos.mkdir();(kos/'Makefile.rules').write_text('');(kos/'leon4k_runtime.h').write_text('// dry-run prerequisite\n')
    profile=[*deps,'NATIVE_ACTOR=1','NATIVE_ACTOR_SKIN=1','NATIVE_ACTOR_SKIN_LAZY=1',
        'SKIN_PALETTE_LAZY=1','COARSE_SOURCE_ACTORS=1','COARSE_LEON=1','COARSE_GANADO=1',
        'COARSE_GANADO_CAST=1','COARSE_ONE_SUBMIT=1','COARSE_SKIN_FTRV=1','COARSE=1','PACE_CATCHUP=2',
        'PACE_TRANS_SKIP=4063','GAME_ATCHK=1','GAME_ATCHK_LIST=1','D349_RENDERER_STACK=1','PVR_STREAM=1',
        'COARSE_ACTOR_ASSET_DIR='+str(kos),'SKIN_ADMISSION32=1','ACTOR_SKIN_RESERVE=1']
    def primary(extra):
        p=subprocess.run(['make','--no-print-directory','-f','Makefile','-n','KOS_BASE='+str(kos),*profile,*extra,
            *['obj/'+t+'.o' for t in targets]],cwd=host.DC/'game',capture_output=True,text=True)
        assert p.returncode==0,p.stderr
        return [line for line in p.stdout.splitlines() if line.startswith('kos-c++')]
    for recipe in (0,1):
        common=['SKIN_RECIPE32='+str(recipe)]
        absent=primary(common);zero=primary(common+['ACTOR_TABLE_REUSE14=0']);on=primary(common+['ACTOR_TABLE_REUSE14=1'])
        assert absent==zero and len(on)==4
        for i,line in enumerate(on):assert line.count('-DRE4DC_ACTOR_TABLE_REUSE14=1')==int(i==0),line
    report=dict(status='PASS',base=host.BASE,identity=identity,
        make='default0; exact expanded0/1, whitespace/dependencies; real Make only native_actor_fast; recipe0/1 PASS')
    (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))

if __name__=='__main__':main()
