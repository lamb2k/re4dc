"""Actual staged game30 block configuration gate, no target object build."""
from pathlib import Path
import hashlib,json,subprocess
r=Path('/root/probe/codex-damcause23')
g=lambda *a:subprocess.check_output(['git','-C',str(r),*a])
p='port/dreamcast/game/game30.mk'
old=g('show','64a28a7bdc44312924b14414501b7d4ff1d2d032:'+p).decode()
actual=g('show',':'+p).decode()
makefile=g('show','HEAD:port/dreamcast/game/Makefile').decode()
compile_rule='$(OBJDIR)/%.o: $(ROOT)/%.cpp'
rule=makefile[makefile.index(compile_rule):].splitlines()[:3]
assert '$(GAME_CPPFLAGS)' in rule[2] and '-c $<' in rule[2]
added='$(OBJDIR)/src/game/em_set.o $(OBJDIR)/src/game/em.o $(OBJDIR)/src/game/read.o: GAME_CPPFLAGS += -DRE4DC_ISSUE52_ACTOR_DIAG=1\n'
assert actual.count(added)==1 and actual.replace(added,'')==old
block=actual[actual.index('# ISSUE52_ACTOR_DIAG=1:'):actual.index('# MOTION_MISS_LOG=1')]
targets=['obj/src/game/em_set.o','obj/src/game/em.o','obj/src/game/read.o',
         'obj/mod/st1_2/src/st1/r10c.o','obj/platform/modules.o','obj/platform/crash_screen.o','obj/src/game/em_sub.o']
harness='OBJDIR := obj\n.DEFAULT_GOAL := report\n'+block+'\n.PHONY: report '+' '.join(targets)+'\nreport: '+' '.join(targets)+'\n'+' '.join(targets)+':\n\t@echo $@ $(GAME_CPPFLAGS) $(PLATFORM_CPPFLAGS)\n'
results=[]
for label,args,ok in [('default',[],True),('zero',['ISSUE52_ACTOR_DIAG=0'],True),
 ('one',['ISSUE52_ACTOR_DIAG=1'],True),('invalid',['ISSUE52_ACTOR_DIAG=2'],False),
 ('no_crash',['ISSUE52_ACTOR_DIAG=1','CRASH_SCREEN=0'],False),
 ('no_stage',['ISSUE52_ACTOR_DIAG=1','STAGE_OVL=0'],False),
 ('no_route',['ISSUE52_ACTOR_DIAG=1','ROUTE_OVL=0'],False)]:
 run=subprocess.run(['make','--no-print-directory','-rR','-f','-','CRASH_SCREEN=1','STAGE_OVL=1','ROUTE_OVL=1',*args],input=harness,text=True,capture_output=True)
 assert (run.returncode==0)==ok,(label,run.stderr)
 if ok:
  rows=run.stdout.splitlines();assert len(rows)==7
  for target,row in zip(targets,rows):
   assert row.split()[0]==target
   assert ('-DRE4DC_ISSUE52_ACTOR_DIAG=1' in row)==(label=='one' and target!=targets[-1])
 results.append(dict(variant=label,exit=run.returncode,stdout=run.stdout,stderr=run.stderr))
host=Path('/mnt/c/Game Dev/Emulators/codex-lanes/damcause23/host04/receipt.json')
previous=json.loads(host.read_text())
for pin in previous['source_pins']:
 assert hashlib.sha256((r/pin['path']).read_bytes()).hexdigest()==pin['after_sha256']
out=Path('/mnt/c/Game Dev/Emulators/codex-lanes/damcause23/actual-wiring02.json')
assert not out.exists()
out.write_text(json.dumps(dict(applied=True,game30_blob=g('rev-parse',':'+p).decode().strip(),
 game30_sha256=hashlib.sha256(actual.encode()).hexdigest(),only_change=added.strip(),results=results,
 actual_compile_rule=rule,makefile_sha256=hashlib.sha256(makefile.encode()).hexdigest(),
 prior_host_receipt_sha256=hashlib.sha256(host.read_bytes()).hexdigest(),
 prior_host_source_pins_all_match=True,disabled_parity_controls=previous['disabled_preprocessor_controls'],
 limits='Actual edited Make block evaluated; source unchanged from host04/OFF/PPC controls; no target object or full Makefile/recipe execution'),indent=2)+'\n')
print(out)
