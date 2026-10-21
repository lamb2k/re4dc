#!/usr/bin/env python3
'Bounded exact macro host/Make/SH4 unit gates; no link, stage or guest.'
from pathlib import Path
import hashlib,json,os,re,shlex,shutil,signal,subprocess,time
ROOT=Path(__file__).resolve().parents[5];BASE=Path('/root/probe/codex-qa21-combined-regression');OUT=Path('/root/probe/death-stall21-unit-20261021-v2');R=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/death-stall21-20261021');CAP=20*1024**2;FLOOR=18*1024**3+64*1024**2
assert not OUT.exists();assert shutil.disk_usage('/mnt/c').free>=FLOOR+CAP;OUT.mkdir()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def size():return sum(p.stat().st_size for r in (ROOT,OUT) for p in r.rglob('*') if p.is_file() and p.name!='.git')
def run(cmd,name,cwd=BASE/'port/dreamcast/game',data=None):
 assert size()<CAP and shutil.disk_usage('/mnt/c').free>=FLOOR
 log=OUT/(name+'.log');start=time.monotonic()
 with log.open('wb') as stream:
  child=subprocess.Popen(cmd,cwd=cwd,stdin=subprocess.PIPE if data else None,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True);identity=Path('/proc/'+str(child.pid)+'/stat').read_text().split()[21]
  if data:child.stdin.write(data.encode());child.stdin.close()
  while child.poll() is None:
   reason='45s cap' if time.monotonic()-start>45 else '20MiB cap' if size()>=CAP else 'C floor' if shutil.disk_usage('/mnt/c').free<FLOOR else None
   if reason:
    assert Path('/proc/'+str(child.pid)+'/stat').read_text().split()[21]==identity;os.killpg(child.pid,signal.SIGKILL);child.wait();raise AssertionError(reason)
   time.sleep(.15)
  rc=child.wait()
 return {'argv':cmd,'returncode':rc,'seconds':time.monotonic()-start,'log_sha256':sha(log),'stdout':log.read_text()}
src=(ROOT/'src/em10/em10.cpp').read_text();start=src.index('#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_GANADO_ROUTINE_BYTES)');end=src.index('\n#endif',start)+len('\n#endif');guard=src[start:end]
cases=sorted(set((int(a),int(b,16)) for a,b in re.findall(r'EM_RTN_SET\(em,\s*(\d+),\s*0x([0-9A-Fa-f]+)\)',src)));assert len(cases)>=8
host='''#include <cstdint>
#include <cassert>
using u8=uint8_t;using u32=uint32_t;
struct cEm10 {union {u32 stat;struct {u8 r_no_0,r_no_1,r_no_2,r_no_3;};};};
'''+guard+'\nint main(){cEm10 em;\n'
for a,b in cases:
 host+='em.stat=0xaabbccdd;EM_RTN_SET(&em,%d,%d);\n'%(a,b)
 host+='''#if defined(RE4DC_GANADO_ROUTINE_BYTES) && RE4DC_GANADO_ROUTINE_BYTES && !defined(__PPC__)
assert(em.r_no_0==%d&&em.r_no_1==%d&&em.r_no_2==0&&em.r_no_3==0);
#else
assert(em.stat==((%du<<24)|(%du<<16)));assert(em.r_no_0==0&&em.r_no_1==0);
#endif
'''%(a,b,a,b)
host+='}\n';(OUT/'macro-host.cpp').write_text(host);rows=[]
for arm,defs in [('default',[]),('zero',['-DRE4DC_GANADO_ROUTINE_BYTES=0']),('one',['-DRE4DC_GANADO_ROUTINE_BYTES=1']),('ppc-preprocessor-control',['-DRE4DC_GANADO_ROUTINE_BYTES=1','-D__PPC__'])]:
 binary=OUT/('host-'+arm);r=run(['g++','-std=c++17','-O1','-fsanitize=undefined','-DRE4DC_GAME',*defs,str(OUT/'macro-host.cpp'),'-o',str(binary)],'host-compile-'+arm);assert r['returncode']==0,r;rows.append(r);r=run([str(binary)],'host-run-'+arm);assert r['returncode']==0,r;rows.append(r)
make=(ROOT/'port/dreamcast/game/Makefile').read_text();a=make.index('# Native Ganado routine-byte repair;');b=make.index('# UI_POLY_ORDER:',a);block=make[a:b]
targets=['out/mod/em10g/shared/src/em10/em10.o','out/src/game/em_sub.o','out/platform/native_actor.o']
mini='OBJDIR=out\nGAME_CPPFLAGS=BASE\n'+block+'all: '+' '.join(targets)+'\n.PHONY: all '+' '.join(targets)+'\n'+' '.join(targets)+':\n\t@printf "%s=%s\\n" "$@" "$(GAME_CPPFLAGS)"\n';(OUT/'guard.mk').write_text(mini);mk=[]
for v in [None,'0','1','2','', 'yes']:
 r=run(['make','--no-print-directory','-f',str(OUT/'guard.mk'),'all']+([] if v is None else ['GANADO_ROUTINE_BYTES='+v]),'make-'+str(v));assert (r['returncode']==0)==(v in [None,'0','1']),r
 if r['returncode']==0:
  for line in r['stdout'].splitlines():assert ('-DRE4DC_GANADO_ROUTINE_BYTES=1' in line)==(v=='1' and line.startswith(targets[0]+'='))
 mk.append({'value':v,**r})
log=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/qa21-combined-regression-20261021/builds/qa-control/build.log');lines=[x for x in log.read_text().splitlines() if x.startswith('kos-c++ ') and ' -c ../../../src/em10/em10.cpp -o ' in x];assert len(lines)==1
cmd0=shlex.split(lines[0]);cmd0[0]='/opt/toolchains/dc/sh-elf/bin/sh-elf-g++';obj=[]
for arm,root,define in [('baseline',BASE,None),('off-default',ROOT,None),('off-zero',ROOT,'0'),('on',ROOT,'1')]:
 target=OUT/(arm+'-em10.o');cmd=cmd0.copy();cmd[cmd.index('-c')+1]=str(root/'src/em10/em10.cpp');cmd[cmd.index('-o')+1]=str(target);cmd+=['-g0','-fmacro-prefix-map='+str(BASE)+'=../../..','-fmacro-prefix-map='+str(ROOT)+'=../../..']
 if define is not None:cmd+=['-DRE4DC_GANADO_ROUTINE_BYTES='+define]
 r=run(cmd,'compile-'+arm);assert r['returncode']==0,r;r.update(arm=arm,object_sha256=sha(target),object_bytes=target.stat().st_size,source_sha256=sha(root/'src/em10/em10.cpp'));obj.append(r)
 if arm=='baseline':expected=sha(target)
 elif arm.startswith('off'):assert sha(target)==expected
 else:assert sha(target)!=expected
result={'scope':'Exact macro host UBSan and SH4 object tests only; no full link or Flycast/release/physical acceptance','base_head':subprocess.check_output(['git','-C',str(BASE),'rev-parse','HEAD'],text=True).strip(),'candidate_head':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),'macro_call_pairs':cases,'source_sha256':sha(ROOT/'src/em10/em10.cpp'),'makefile_sha256':sha(ROOT/'port/dreamcast/game/Makefile'),'tool_sha256':sha(__file__),'recipe_log_sha256':sha(log),'host_tests':rows,'make_tests':mk,'objects':obj,'OFF_default_and_zero_exact':True,'ON_compile':True,'source_output_bytes':size(),'cap_bytes':CAP,'free_c':shutil.disk_usage('/mnt/c').free};(OUT/'receipt.json').write_text(json.dumps(result,indent=2));(R/'routine-byte-unit-receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps({'call_pairs':len(cases),'OFFidentity':True,'ONcompile':True,'bytes':size()}))
