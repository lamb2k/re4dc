#!/usr/bin/env python3
"""Bound independent OFF arms, full trans PP, exact hosted objects and Make."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import actor_presentation32 as present
from actor_joint32 import BASE,ROOT,GAME,INC,HERE

def run(cmd,**kw):
    p=subprocess.run(cmd,capture_output=True,**kw)
    if p.returncode:raise RuntimeError(p.stderr.decode()[-15000:])
    return p.stdout
def fixture(baseline=False):
    original=present.read
    if baseline:
        present.read=lambda path,base=False:subprocess.check_output(['git','show',f'{BASE}:{path.relative_to(ROOT)}'],cwd=ROOT,text=True)
    try:return present.fixture()
    finally:present.read=original
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    flags=['-std=c++20','-O2','-fpermissive','-I'+str(INC),'-I'+str(GAME),'-I'+str(GAME/'platform'),
        '-DRE4DC_ACTOR_TRANSACTION=1','-DRE4DC_ACTOR_SKIN_RESERVE=1','-DRE4DC_NATIVE_ACTOR_FAST=1',
        '-DRE4DC_NATIVE_ACTOR_SKIN_LAZY=1','-DRE4DC_NATIVE_ACTOR_SKIN=1','-DRE4DC_NATIVE_MODEL_REGISTRY=1',
        '-DRE4DC_NATIVE_MODEL_REGISTRY_PACK=1','-DRE4DC_ROUTE_CH22=1','-DRE4DC_ACTOR_SKIN_OWNER_POOL=0',
        '-DRE4DC_COARSE_SOURCE_ACTORS=1','-DRE4DC_SKIN_ADMISSION32=1','-DRE4DC_NMR_BONES=96',
        '-DRE4DC_SKIN_PALETTE_LAZY=1','-DRE4DC_LEON_NO_GC_FRONT=2']
    bodies=[fixture(True),fixture()];rows={}
    # New joint behavior must not change either independent supported feature.
    arms={'presentation-absent-recipe1':['-DRE4DC_SKIN_RECIPE32=1'],
          'presentation-zero-recipe1':['-DRE4DC_ACTOR_PRESENTATION32=0','-DRE4DC_SKIN_RECIPE32=1'],
          'presentation1-recipe-absent':['-DRE4DC_ACTOR_PRESENTATION32=1'],
          'presentation1-recipe-zero':['-DRE4DC_ACTOR_PRESENTATION32=1','-DRE4DC_SKIN_RECIPE32=0'],
          'both-absent':[], 'both-zero':['-DRE4DC_ACTOR_PRESENTATION32=0','-DRE4DC_SKIN_RECIPE32=0']}
    for name,extra in arms.items():
        pp=[];objects=[]
        for label,body in zip(('base','current'),bodies):
            text=run(['g++',*flags,*extra,'-E','-P','-x','c++','-'],input=body.encode());pp.append(text)
            (out/f'{name}-{label}.cpp').write_bytes(text)
            path=out/f'{name}-{label}.o'
            run(['g++','-std=c++20','-O2','-fpermissive','-fno-ident','-x','c++','-c','-','-o',str(path)],input=text)
            objects.append(path.read_bytes())
        assert pp[0]==pp[1] and objects[0]==objects[1],name
        rows[name]={'exact_pp':True,'exact_host_object':True,'object_sha256':hashlib.sha256(objects[0]).hexdigest()}
    # Full actual trans, SH-conditioned; old include overlay retains old source
    # presentation guards. No SDK/header policy or target compiler invoked.
    overlay=out/'base-include';overlay.mkdir()
    for name in ('source_actor_owner_hooks.inc','source_actor_presentation32.inc'):
        (overlay/name).write_bytes(subprocess.check_output(['git','show',f'{BASE}:port/dreamcast/game/platform/include/{name}'],cwd=ROOT))
    base_trans=out/'base-trans.cpp';base_trans.write_bytes(subprocess.check_output(['git','show',f'{BASE}:src/game/trans.cpp'],cwd=ROOT))
    pp_flags=['g++','-E','-P','-std=gnu++20','-fpermissive','-w','-I'+str(ROOT/'include'),
        '-I'+str(ROOT/'src'),'-I'+str(ROOT/'src/game'),'-D__sh__','-U__PPC__','-DRE4DC_GAME=1',
        '-DRE4DC_FRONT_NATIVE=1','-DRE4DC_FRONT_TEXOBJ=1','-DRE4DC_COARSE=1',
        '-DRE4DC_PACE_CATCHUP=2','-DRE4DC_PACE_TRANS_SKIP=4063','-DRE4DC_ATCHK_LIST=1',*flags[3:]]
    full={}
    for name,extra in arms.items():
        old=run([*pp_flags,'-I'+str(overlay),'-I'+str(INC),*extra,str(base_trans)])
        new=run([*pp_flags,'-I'+str(INC),*extra,str(ROOT/'src/game/trans.cpp')])
        assert old==new,name
        full[name]={'exact':True,'bytes':len(new),'sha256':hashlib.sha256(new).hexdigest()}
    joint=run([*pp_flags,'-I'+str(INC),'-DRE4DC_ACTOR_PRESENTATION32=1','-DRE4DC_SKIN_RECIPE32=1',str(ROOT/'src/game/trans.cpp')])
    for marker in (b'partnerPresentation32Identity',b're4dc_actor_skin_recipe_claim',b're4dc_prim_recipe_claim',b're4dc_skin_recipe_materialize'):
        assert marker in joint,marker
    halts=lambda data:[x.strip() for x in data.decode().splitlines() if 're4dc_halt("D:/Bio4/Prog/trans.cpp",' in x]
    reference=run([*pp_flags,'-I'+str(INC),'-DRE4DC_SKIN_RECIPE32=1',str(ROOT/'src/game/trans.cpp')])
    assert len(halts(joint))==2 and halts(joint)==halts(reference)
    spec=importlib.util.spec_from_file_location('joint32_profile',HERE.parent/'build18/build_profile.py')
    profile=importlib.util.module_from_spec(spec);sys.modules[spec.name]=profile;spec.loader.exec_module(profile)
    kos=out/'kos';kos.mkdir();(kos/'Makefile.rules').write_text('')
    sdk=out/'sdk';(sdk/'include/sh4zam').mkdir(parents=True);(sdk/'include/sh4zam/shz_xmtrx.h').write_text('// make -n only\n')
    common=[*present.PROFILE,'NATIVE_ACTOR=1','NATIVE_ACTOR_SKIN=1','SKIN_PALETTE_LAZY=1','SKIN_ADMISSION32=1',
        'QA_MENU=0','QA_LINK=0','NMR_POOL_LOD=0']
    make={}
    for pval,rval in ((0,0),(0,1),(1,0),(1,1)):
        name=f'p{pval}-r{rval}';dest=out/name;dest.mkdir()
        cmd,recipe=profile.make_command(dest,ROOT,kos,sdk,[*common,f'ACTOR_PRESENTATION32={pval}',f'SKIN_RECIPE32={rval}'],dest/'obj/src/game/trans.o')
        cmd.extend(str(dest/'obj'/x) for x in ('coarse_actor.o','platform/native_actor_fast.o','platform/native_ui.o'))
        result=subprocess.run(cmd,cwd=GAME,capture_output=True,text=True)
        (out/f'{name}-make.log').write_text(result.stdout+result.stderr);assert not result.returncode,result.stderr
        commands=[x for x in result.stdout.splitlines() if x.startswith('kos-c++ ') and ' -c ' in x]
        assert len(commands)==4
        for i,line in enumerate(commands):
            args=shlex.split(line)
            assert args.count('-DRE4DC_ACTOR_PRESENTATION32=1')==int(pval and i<3),line
            assert args.count('-DRE4DC_SKIN_RECIPE32=1')==int(rval and i<3),line
        make[name]={'command':cmd,'recipe':recipe,'source_commands':commands}
    # Each previous non-joint prerequisite still refuses actual primary Make.
    rejected={}
    for assignment in ('ACTOR_SKIN_OWNER_POOL=1','NATIVE_MODEL_REGISTRY_BONES=80','SKIN_ADMISSION32=0',
                       'NATIVE_ACTOR_SKIN_LAZY=0','SKIN_PALETTE_LAZY=2','ACTOR_SKIN_RESERVE=0'):
        dest=out/'negative';cmd,_=profile.make_command(dest,ROOT,kos,sdk,[*common,'ACTOR_PRESENTATION32=1','SKIN_RECIPE32=1',assignment],dest/'obj/coarse_actor.o')
        result=subprocess.run(cmd,cwd=GAME,capture_output=True,text=True);assert result.returncode,assignment
        rejected[assignment]=result.stderr
    receipt={'verdict':'PASS','baseline':BASE,'host_identity':rows,'full_trans_identity':full,
        'joint_full_trans':{'bytes':len(joint),'halting_diagnostics_equal':True,'all_source_contracts_selected':True},
        'primary_make':make,'preserved_refusals':rejected,'sdk_used':False,
        'limits':'hosted object/source PP identity; target full object/programme/overlay gates remain separate'}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'verdict':'PASS','off_arms':list(rows),'make_arms':list(make),'refusals':list(rejected)},indent=2))
if __name__=='__main__':main()
