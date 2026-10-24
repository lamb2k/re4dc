#!/usr/bin/env python3
"""Source-pinned world49ad private QA programme planning and byte receipts only.

Never stages assets, a QA package, disc, private destination or emulator run.
"""
import argparse, hashlib, json, re, shutil, subprocess
from pathlib import Path

SOURCE='49ad20f9932d638ddb7becf5db6f86b92e0a76a2'
RECIPE='92e2322daecde3e50699bd28303d177379418d8c3ba3b76ab7260836777ae898'
TREE=Path('/root/work/lanes/interior-world49ad-qa')
WORK=Path('/root/work/lanes/interior-world49ad-qa-scratch')
EV=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/interior-vis23-20261023/world49ad-qa-programmes')
TOOLS=TREE/'port/dreamcast/tools/d367'
PREFIX=dict(reference='ivwe49adrefq',off='ivwe49adoffq',both='ivwe49adbothq')
BIN=Path('/opt/toolchains/dc/sh-elf/bin')
QA='PC_SAMPLER=0 QA_MENU=1 WARP_AFTER_RESET=1 QA_TEST=23 QA_SRC=49ad20f9 WORLD_METER=1 GAME_TICK_LOG=60 PHASE_METER=1 DISC_READ_METER=1 KOS_WATCH=0 KOS_SQUEEZE=0'
REQUIRED=dict(SCENERY_SELECT_ONLY='1',SCENERY_REPLAY_LEAN='1',SCENERY_SUBMIT_BATCH='1',VRAM_ROOM_ARENA='0',CPU_BACKFACE='0',ACTOR_BACKFACE='0',SCENERY_DEDUP='0',ACTOR_SETUP_LEAN='0',SCENERY_UV_SNAPSHOT='0',PS2_PVS='0',STAT_ROUTINE_BYTES='1',STAT_DIAG='0',ESP_POOL_RECYCLE='1',R117_EFFECT_FAILURE_SAFE='1',KOS_CACHE_P2='1',KOS_CACHE_P2_DIAG='0',R10C_SPAWN_LIVE_GUARD='1',EM_READ_RETRY='1',QUALITY_LOD_PX='5',SCENERY_FAR_LOD='4',SCENERY_EMIT_CENSUS='0')
REQUIRED.update(x.split('=',1) for x in QA.split())
OVERLAYS=set('em22 em2b em2f em35 em3b pl0f pl11 pl14 sscrn st1_0 st1_1 st1_2 st1_3 st2_0'.split())

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def identity(p):
 p=Path(p);return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p))
def run(*args):return subprocess.check_output(list(map(str,args)),text=True).strip()
def write(p,data):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(data,f,indent=2);f.write('\n')
def source_check():
 assert run('git','-C',TREE,'rev-parse','HEAD')==SOURCE
 assert not run('git','-C',TREE,'status','--porcelain')
 assert sha(TOOLS/'rr/recipe.conf')==RECIPE
 return dict(source=SOURCE,tree=str(TREE),recipe=identity(TOOLS/'rr/recipe.conf'),submodules=run('git','-C',TREE,'submodule','status'))
def recipe_ch2():
 text=(TOOLS/'rr/recipe.conf').read_text();value=re.search(r'^CH2="([^"\n]*)"$',text,re.M)[1]
 assert '$' not in value and '`' not in value
 return value

def plan():
 source=source_check();EV.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
 presets=WORK/'preset-plan';assert not presets.exists()
 sr=WORK/'stage1-route-plan.json'
 subprocess.run(['python3',str(TOOLS/'stage_route.py'),'--stage','1','--json',str(sr)],check=True,stdout=subprocess.DEVNULL)
 subprocess.run(['python3',str(TOOLS/'qa20/mkqa.py'),str(presets),'--sr1',str(sr)],check=True)
 menu=(presets/'menu.txt').read_text();assert sum(l.startswith('p ') for l in menu.splitlines())==33
 all_presets={p.name:identity(p) for p in sorted(presets.iterdir()) if p.is_file()}
 commands={}
 for arm,lp in PREFIX.items():
  extra='' if arm=='reference' else ' SCENERY_SELECT_LEAN2='+str(int(arm=='both'))+' SCENERY_EMIT_PREFETCH='+str(int(arm=='both'))
  out=Path('/root/probe/lanes/route')/('out-'+lp+'rW');assert not out.exists()
  commands[arm]=dict(prefix=lp,output=str(out),arm='rW',CH2=recipe_ch2()+extra,XON=QA)
 source_files=['ch2/ch2-build.sh','test15/t15-build.sh','route/route-build.sh','build-r21.sh','qa20/mkqa.py','stage_route.py','rr/recipe.conf']
 data=dict(kind='PROGRAMME ONLY; private pair NOT READY',**source,planner=identity(Path(__file__)),
           commands=commands,qa_presets=all_presets,qa_preset_count=33,
           tool_sources={p:identity(TOOLS/p) for p in source_files},required_resolved=REQUIRED,
           effective_lod_divisor=20,production_performance_switches='OFF; no Dreamcast hardware gain established',
           hair_repair='private candidate is not production approved; no asset included',
           scope_excluded=['assets','QA package','disc','private destination','guest','recipe/runtime edits'],
           reference='Fresh unchanged recipe with matched normal QA/menu/meter overrides; not a production binary')
 write(EV/'plan.json',data);shutil.copy2(TOOLS/'rr/recipe.conf',EV/'recipe.conf')
 shutil.copy2(WORK/'SDK-PREPARED.txt',EV/'SDK-PREPARED.txt')
 print(json.dumps(dict(plan=str(EV/'plan.json'),source=SOURCE,presets=33,labels=PREFIX)))

def check(arm):
 source=source_check();plan=json.loads((EV/'plan.json').read_text());cfg=plan['commands'][arm];out=Path(cfg['output'])
 assert (out/'stack.txt').read_text().strip()==SOURCE
 assert (out/'missing.txt').stat().st_size==0
 knobs=dict(line.split('=',1) for line in (out/'resolved-knobs.txt').read_text().splitlines() if '=' in line)
 expected={**REQUIRED,'SCENERY_SELECT_LEAN2':str(int(arm=='both')),'SCENERY_EMIT_PREFETCH':str(int(arm=='both'))}
 for k,v in expected.items():assert knobs.get(k)==v,(arm,k,knobs.get(k),v)
 assert {p.stem for p in out.glob('*.ovl')}==OVERLAYS
 assert sha('/root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a')=='5e2d867fb5825e7825e1843f2542446288e18c383341a58426e452a0b620daaf'
 dest=EV/arm;dest.mkdir(exist_ok=False)
 raw=dest/'main-no-stack.bin'
 subprocess.run([str(BIN/'sh-elf-objcopy'),'-R','.stack','-O','binary',str(out/'re4dc-game.elf'),str(raw)],check=True)
 for p in out.iterdir():
  if p.is_file() and (p.suffix=='.ovl' or p.name in ('re4dc-game.elf','build.log','candidate.txt','resolved-knobs.txt','stack.txt','syms.txt','missing.txt','end.txt','elf.sha256')):shutil.copy2(p,dest/p.name)
 for command,name in [('sh-elf-nm','symbols-map.txt'),('sh-elf-size','sections-size.txt'),('sh-elf-objdump','sections-map.txt')]:
  flags=['-n','-S'] if command.endswith('-nm') else ['-A'] if command.endswith('-size') else ['-h']
  cp=subprocess.run([str(BIN/command),*flags,str(out/'re4dc-game.elf')],capture_output=True,text=True,check=True)
  (dest/name).write_text(cp.stdout)
 program=WORK/'programs'/('candidate-route'+cfg['prefix']+'rW')
 assert (program/'1ST_READ.BIN').exists();shutil.copy2(program/'1ST_READ.BIN',dest/'1ST_READ.BIN')
 result=dict(kind='PROGRAMME BUILD ONLY; no runtime/visual/hardware acceptance',arm=arm,**source,
             output=str(out),programme_files={p.name:identity(p) for p in sorted(dest.iterdir()) if p.is_file()},
             required_knobs=expected,symbol_map_kind='actual ELF nm/section maps; no new linker flags',
             qa_preset_plan_sha256=sha(EV/'plan.json'))
 write(dest/'receipt.json',result)
 print(json.dumps(dict(arm=arm,elf=sha(dest/'re4dc-game.elf'),main=sha(raw),overlays=14,missing=0)))

def normalized(arm):
 out=json.loads((EV/'plan.json').read_text())['commands'][arm]['output']
 values={}
 for line in (EV/arm/'resolved-knobs.txt').read_text().splitlines():
  if '=' in line:
   k,v=line.split('=',1);values[k]=v.replace(out,'@OUTPUT@')
 return values

def compare(pair):
 source_check();left,right=('reference','off') if pair=='off' else ('off','both')
 a,b=normalized(left),normalized(right);assert a.keys()==b.keys()
 diff={k:[a[k],b[k]] for k in a if a[k]!=b[k]}
 expected={} if pair=='off' else {'SCENERY_SELECT_LEAN2':['0','1'],'SCENERY_EMIT_PREFETCH':['0','1']}
 assert diff==expected,diff
 same={name:sha(EV/left/name)==sha(EV/right/name) for name in ['main-no-stack.bin',*(x+'.ovl' for x in sorted(OVERLAYS))]}
 if pair=='off':assert all(same.values()),same
 write(EV/('compare-'+pair+'.json'),dict(kind='fresh matched QA programme reproduction' if pair=='off' else 'exact two-switch QA composition',
       source=SOURCE,left=left,right=right,normalized_profile_differences=diff,programme_byte_equal=same,
       output_path_normalization_only=True,production_identity_claim=False,stage_or_guest=False))
 print(json.dumps(dict(pair=pair,profile_diff=diff,byte_equal=same)))

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('mode',choices=('plan','check','compare'));ap.add_argument('arm',nargs='?')
 a=ap.parse_args()
 if a.mode=='plan':plan()
 elif a.mode=='check':check(a.arm)
 else:compare(a.arm)
