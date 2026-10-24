#!/usr/bin/env python3
"""Plan ONLY the private SDO3 QA pair. No build/stage/guest execution path.

The root lane must first accept its matched full-H2 memory gate. A separate,
clean exact-source build tree is required; live next/OFF control trees stay put.
"""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess

SOURCE='5be38f009f9ae4d42daff69dacc537e8230bcfca'
DIAGNOSTIC_ZERO=('PC_SAMPLER','KOS_WATCH','KOS_SQUEEZE','NATIVE_MODEL_REGISTRY_CENSUS')
QA={'QA_MENU':'1','WARP_AFTER_RESET':'1','GAME_TICK_LOG':'60','PHASE_METER':'1',
    'DISC_READ_METER':'1','QA_TEST':'23','QA_SRC':SOURCE[:8],'PC_SAMPLER':'0'}
DEST_ROOT=Path('/mnt/c/Game Dev/Emulators')


def sha(data):return hashlib.sha256(data).hexdigest()


def git(repo,*args):
    return subprocess.check_output(['git','-C',str(repo),*args])


def remap(value,old,new):
    if isinstance(value,str):return value.replace(old,new)
    if isinstance(value,list):return [remap(x,old,new) for x in value]
    if isinstance(value,dict):return {k:remap(x,old,new) for k,x in value.items()}
    return value


def validate_plan(plan,expected_source=SOURCE):
    if not re.fullmatch('[0-9a-f]{40}',expected_source) or plan['source']!=expected_source:
        raise ValueError('Expected exact frozen source')
    data=plan['data_sets'].split(',')
    if len(data)!=29 or len(set(data))!=29:raise ValueError('Expected unchanged DATA29')
    sets=plan['alternates']
    expected={'dc/native/'+r+'/ps2-dd3.re4mesh' for r in ('r100','r101','r103')}
    expected.add('dc/native/r101/ps2-dd3.r4sg')
    if {x['destination'] for x in sets}!=expected or len(sets)!=4:raise ValueError('Only frozen four alternate filenames allowed')
    for p in sets:
        b=Path(p['path']).read_bytes()
        if len(b)!=p['bytes'] or sha(b)!=p['sha256']:raise ValueError('Alternate pin changed: '+p['path'])
    for p in plan['baseline_packages'].values():
        b=Path(p['path']).read_bytes()
        if len(b)!=p['bytes'] or sha(b)!=p['sha256']:raise ValueError('Original package pin changed')


def resolved_qa(knobs,mode,source=SOURCE):
    expected={**QA,'QA_SRC':source[:8],'SCENERY_DEDUP':str(mode)}
    for name,value in expected.items():
        if knobs.get(name)!=value:raise ValueError('Resolved QA mismatch: '+name)
    for name in DIAGNOSTIC_ZERO:
        if knobs.get(name)!='0':raise ValueError('Nonstandard diagnostic enabled or absent: '+name)
    # TEX_CHECK / MCHECK / VRAM logs inherit the release recipe; do not turn
    # its standard checks into a different diagnostic or stripped recipe.
    return True


def make_plan(p,repo,tree,work,source=SOURCE):
    validate_plan(p,source)
    if tree==Path(p['tree']) or 'current-off5be' in tree.name:raise ValueError('Do not use live build/control tree')
    if not tree.is_absolute() or not work.is_absolute():raise ValueError('Absolute dedicated paths required')
    recipe=git(repo,'show',source+':port/dreamcast/tools/d367/rr/recipe.conf')
    if sha(recipe)!=p['recipe']['sha256']:raise ValueError('Recipe pin differs from frozen source')
    oldtree=p['tree'];steps={};destinations={};tools={}
    names=('ch2/ch2-build.sh','test11/t11-fix.py','test8/t8-pkgtree.py','stage_route.py','qa20/mkqa.py','mkgdi.sh','disc_lint.py','rr/rr-qa.sh','qa20/README-package.txt')
    for name in names:
        rel='port/dreamcast/tools/d367/'+name
        tools[rel]=sha(git(repo,'show',source+':'+rel))
    for arm,mode in [('off',0),('on',3)]:
        x=copy.deepcopy(p['qa']['arms'][arm]);oldwork=x['pkgtree']['environment']['PKG_K']
        x=remap(remap(x,oldtree,str(tree)),oldwork,str(work/arm))
        env=x['build']['environment'];env['JOBS']='1'
        env['XON']=' '.join(k+'='+v for k,v in {'SCENERY_DEDUP':str(mode),**QA,'QA_SRC':source[:8]}.items())
        env.update(ROUTE_PROGRAMS_DIR=str(work/'programs'),ROUTE_PROGRAMS_JSON='',ROUTE_REGISTRY_LOCK=str(work/'programs.lock'))
        x['build']['argv']=['bash','/root/probe/d367-buildslot.sh',*x['build']['argv']]
        x['required_resolved_knobs']={**QA,'QA_SRC':source[:8],'SCENERY_DEDUP':str(mode),**{k:'0' for k in DIAGNOSTIC_ZERO}}
        x['stage']['environment'].update(RE4DC_PAYLOAD_ROOT='/root/re4payload/t164-20261018',PKG_SRC='/root/re4payload/t164-20261018/tree')
        x['pkgtree']['environment'].update(RE4DC_PAYLOAD_ROOT='/root/re4payload/t164-20261018',PKG_SRC='/root/re4payload/t164-20261018/tree')
        x['program_out']='/root/probe/lanes/route/out-'+x['label']
        x['post_build_requirements']=['stack.txt is exactly source40 plus newline; missing.txt empty; all14 overlays present',
            'Verify required_resolved_knobs; pin ELF, objcopy-R.stack main image,14 overlays and resolved-knobs',
            'Pin programme candidate and fixture; retain original standard R4IM/R4SG filenames; no warp/padscript/crashtest on QA data']
        x['post_stage_requirements']=['PKGTREE_OK; every fixture replacement hashes equal; four alternates match frozen pins',
            'Retained base R4IMs match baseline_packages; all standard R4SGs retained and equal across arms',
            'Copy presets to pkgtree/dc/qa without overwriting source; inventory/pin data and QA assets before mastering']
        x['package_requirements']=['mkgdi LAYOUT=standard; loader and standard lint both PASS',
            'Private destination must not exist; retain gdemu/disc.gdi and all3 tracks',
            'Write README provenance then retained qa20 menu guide; SHA256SUMS pins all delivered files; no zip/SD/publication/guest required']
        steps[arm]=x
        destinations[arm]=str(DEST_ROOT/('RE4DC-QA23-Dedup-'+arm.title()+'-'+source[:8]))
    free=shutil.disk_usage('/mnt/c').free
    return dict(kind='PLAN_ONLY_NO_EXECUTION_PATH',source=source,input_plan_sha256=sha(json.dumps(p,sort_keys=True).encode()),
        helper_sha256=sha(Path(__file__).read_bytes()),source_repository=str(repo),tree=str(tree),work=str(work),
        source_tree_state='NOT_ALLOCATED' if not tree.exists() else 'ROOT MUST VERIFY EXACT CLEAN SOURCE BEFORE ANY ACTION',
        blocked='Current-source matched standard fullH2 acceptance is PENDING; historical712 success does not qualify this source. No execution authorized by this plan',
        preflight=['Root records matched fullH2 acceptance with actual source/programme/data/capture pins; ON heap_before >= OFF',
            'Dedicated exact frozen-source clean source tree and initialized pinned SDK/submodules; preserve next/current-off trees',
            'Acquire ONE nonblocking whole-pair tree lease; run arms serially; shared SDKslot wraps each build; JOBS1',
            'Before each build/master/private copy, recheck C free>=22GiB; require absent output labels/work/destinations',
            'Reject inherited extra XON/CH2/diagnostic environment; use exact pinned recipe CH2/exports plus these QA additions'],
        tree_lease=['flock','-n',str(tree)+'.build.lock'],c_free_bytes_observed=free,c_floor_bytes=22*1024**3,
        private_destinations=destinations,data_sets=p['data_sets'],alternates=p['alternates'],baseline_packages=p['baseline_packages'],
        tool_source_sha256=tools,arms=steps,
        readme_provenance={'title':'Private QA23 SDO3 Off/On pair','source':source,'mode':'0 or3 per arm',
            'required_pins':['ELF','main raw-R.stack','14 overlays','resolved-knobs','recipe/DATA29','fixture','QA assets','four alternates','standard retained data','GDI/tracks','lint receipts','helper/input plan'],
            'qualification':'Record actual root gates individually; never infer memory acceptance from matched QA-menu heap; physical console acceptance pending unless separately established',
            'menu_guide_source':'port/dreamcast/tools/d367/qa20/README-package.txt','guide_note':'Retained historical menu guide; package header/provenance must identify actual frozen source and QA23'},
        safety='No execution or emulator launcher is implemented. Root owns gate acceptance and every future mutation.')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','source-repo','tree','work'):ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--expected-source',default=SOURCE,help='Exact40 source from the fresh qualification plan; default retains the historical5be plan')
    ap.add_argument('--output',type=Path)
    a=ap.parse_args();p=json.loads(a.plan.read_text());result=make_plan(p,a.source_repo,a.tree,a.work,a.expected_source)
    result['input_plan_file_sha256']=sha(a.plan.read_bytes())
    text=json.dumps(result,indent=2)+'\n'
    if a.output:
        with a.output.open('x') as f:f.write(text)
    else:print(text,end='')


if __name__=='__main__':main()
