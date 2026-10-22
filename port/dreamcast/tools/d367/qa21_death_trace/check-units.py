#!/usr/bin/env python3
"""Bounded three-unit SH4 trace check. No full build/link/stage or asset writes."""
from pathlib import Path
import argparse,hashlib,json,os,shlex,shutil,signal,subprocess,time
BASE=Path('/root/probe/codex-qa21-combined-regression');TRACE=Path('/root/probe/codex-qa21-death-trace');p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();OUT=a.out;assert OUT.parent==Path('/root/probe') and OUT.name.startswith('qa21-death-trace-check-20261021');R=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/qa21-combined-regression-20261021');FLOOR=18*1024**3+64*1024**2;BUDGET=20*1024**2
assert not OUT.exists();assert shutil.disk_usage('/mnt/c').free>=FLOOR+BUDGET
assert not subprocess.check_output(['git','status','--porcelain'],cwd=BASE,text=True).strip()
OUT.mkdir();(OUT/'headers').mkdir();(OUT/'logs').mkdir()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def size():return sum(p.stat().st_size for root in (TRACE,*OUT.parent.glob('qa21-death-trace-check-20261021*')) for p in root.rglob('*') if p.is_file() and p.name!='.git')
knobs=dict(line.split('=',1) for line in (R/'builds/qa-control/resolved-knobs.txt').read_text().splitlines() if '=' in line)
headers={'route-movies.h':{'RE4DC_ROUTE_MOVIES':'ROUTE_MOVIES','RE4DC_ROUTE_MOVIE_YUV':'ROUTE_MOVIE_YUV','RE4DC_ROUTE_MOVIE_TEXHASH':'ROUTE_MOVIE_TEXHASH','RE4DC_ROUTE_MOVIE_DIAG':'ROUTE_MOVIE_DIAG','RE4DC_ROUTE_QTE_FRAMES':'ROUTE_QTE_FRAMES','RE4DC_ROUTE_CH13':'ROUTE_CH13'},'subscreen.h':{'RE4DC_SUBSCREEN':'SUBSCREEN','RE4DC_W11_FIXTURE':'W11_FIXTURE','RE4DC_SUBSCREEN_OVL':'SUBSCREEN_OVL','RE4DC_SS_POOL_HIGH':'SS_POOL_HIGH','RE4DC_SS_UI_ORDER':'SS_UI_ORDER','RE4DC_SS_PACK':'SS_PACK','RE4DC_SS_BG_BLACK':'SS_BG_BLACK'}}
for name,defs in headers.items():(OUT/'headers'/name).write_text(''.join('#define '+macro+' '+knobs[key]+'\n' for macro,key in defs.items()))
make=(TRACE/'port/dreamcast/game/Makefile').read_text();start=make.index('# Diagnostic only: exact player life/damage/death callers.');end=make.index('# UI_POLY_ORDER:',start);guard=make[start:end]
mini='OBJDIR=out\nGAME_CPPFLAGS=BASE\n'+guard+'\n.PHONY: all out/src/game/em_sub.o out/src/game/pl_dmg.o out/src/game/game.o out/platform/unrelated.o\nall: out/src/game/em_sub.o out/src/game/pl_dmg.o out/src/game/game.o out/platform/unrelated.o\nout/src/game/em_sub.o out/src/game/pl_dmg.o out/src/game/game.o out/platform/unrelated.o:\n\t@printf "%s=%s\\n" "$@" "$(GAME_CPPFLAGS)"\n';(OUT/'guard.mk').write_text(mini)
checks=[]
for value in (None,'0','1','2',''):
 cmd=['make','--no-print-directory','-f',str(OUT/'guard.mk')]+([] if value is None else ['DEATH_TRACE='+value]);run=subprocess.run(cmd,text=True,capture_output=True);valid=value in (None,'0','1');assert (run.returncode==0)==valid,(value,run.stdout,run.stderr)
 if valid:
  lines=run.stdout.splitlines();assert len(lines)==4
  for line in lines:
   target,flags=line.split('=',1);assert ('-DRE4DC_DEATH_TRACE=1' in flags)==(value=='1' and '/src/game/' in target)
 checks.append({'value':value,'returncode':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
log=(R/'builds/qa-control/build.log').read_text();compiler='/opt/toolchains/dc/sh-elf/bin/sh-elf-g++';rows=[];source_hashes={str(BASE/'src/game'/x):sha(BASE/'src/game'/x) for x in ('em_sub.cpp','pl_dmg.cpp','game.cpp')}
for unit in ('em_sub','pl_dmg','game'):
 lines=[x for x in log.splitlines() if x.startswith('kos-c++ ') and ' -c ../../../src/game/'+unit+'.cpp -o ' in x];assert len(lines)==1,unit;template=shlex.split(lines[0]);template[0]=compiler
 for arm,root,define in (('baseline',BASE,None),('off-default',TRACE,None),('off-zero',TRACE,'0'),('on',TRACE,'1')):
  target=OUT/(arm+'-'+unit+'.o');cmd=template.copy();cmd[cmd.index('-c')+1]=str(root/'src/game'/(unit+'.cpp'));cmd[cmd.index('-o')+1]=str(target)
  for i,arg in enumerate(cmd):
   if arg.endswith('/obj/route-movies.h') or arg.endswith('/obj/subscreen.h'):cmd[i]=str(OUT/'headers'/Path(arg).name)
  cmd+=['-g0','-fmacro-prefix-map='+str(BASE)+'=../../..','-fmacro-prefix-map='+str(TRACE)+'=../../..']
  if define is not None:cmd+=['-DRE4DC_DEATH_TRACE='+define]
  assert size()<BUDGET and shutil.disk_usage('/mnt/c').free>=FLOOR
  receipt={'unit':unit,'arm':arm,'argv':cmd,'source_sha256':sha(root/'src/game'/(unit+'.cpp'))};stamp=time.monotonic();logpath=OUT/'logs'/(arm+'-'+unit+'.log')
  with logpath.open('xb') as stream:
   child=subprocess.Popen(cmd,cwd=BASE/'port/dreamcast/game',stdout=stream,stderr=subprocess.STDOUT,start_new_session=True);proc_start=Path('/proc/'+str(child.pid)+'/stat').read_text().split()[21];receipt.update(pid=child.pid,pgid=os.getpgid(child.pid),proc_start=proc_start)
   while child.poll() is None:
    reason=None
    if time.monotonic()-stamp>45:reason='45s unit cap'
    elif size()>=BUDGET:reason='20MiB total source/output cap'
    elif shutil.disk_usage('/mnt/c').free<FLOOR:reason='C18GiB+64MiB floor'
    if reason:
     assert Path('/proc/'+str(child.pid)+'/stat').read_text().split()[21]==proc_start;os.killpg(child.pid,signal.SIGKILL);child.wait();raise AssertionError(reason)
    time.sleep(.15)
   rc=child.wait()
  receipt.update(returncode=rc,seconds=round(time.monotonic()-stamp,4),log_sha256=sha(logpath));rows.append(receipt)
  if rc:print(logpath.read_text()[-5000:]);raise AssertionError('compile '+arm+' '+unit)
  receipt.update(object_sha256=sha(target),object_bytes=target.stat().st_size)
  if arm=='baseline':baseline=receipt['object_sha256']
  elif arm.startswith('off'):assert receipt['object_sha256']==baseline,('OFF binary identity failed',unit,arm)
  else:assert b'death trace:' in target.read_bytes(),('ON trace missing',unit)
 assert size()<BUDGET
for path,digest in source_hashes.items():assert sha(path)==digest
result={'scope':'SH4 source-unit compile only; debug disabled and macro paths normalized equally for object identity. No full ELF/link/staging/runtime/release/hardware proof. Generated forced headers reconstructed from exact retained Make recipes and resolved knobs.','baseline_source':subprocess.check_output(['git','rev-parse','HEAD'],cwd=BASE,text=True).strip(),'trace_files':{name:sha(TRACE/name) for name in ('src/game/em_sub.cpp','src/game/pl_dmg.cpp','src/game/game.cpp','port/dreamcast/game/Makefile')},'check_tool_sha256':sha(__file__),'recipe_log_sha256':sha(R/'builds/qa-control/build.log'),'resolved_knobs_sha256':sha(R/'builds/qa-control/resolved-knobs.txt'),'compiler_sha256':sha(compiler),'headers':{name:sha(OUT/'headers'/name) for name in headers},'guard_tests':checks,'compiles':rows,'all_three_OFF_default_and_explicit_zero_objects_identical':True,'all_three_ON_compile':True,'source_output_logical_bytes':size(),'cap_bytes':BUDGET,'free_c_after':shutil.disk_usage('/mnt/c').free};(OUT/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'OFF_identity':True,'ON_compile':True,'bytes':size(),'receipt':str(OUT/'receipt.json')}))