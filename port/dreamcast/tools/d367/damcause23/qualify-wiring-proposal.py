"""Evaluate the actual diagnostic Make block plus proposed wiring IN MEMORY only."""
from pathlib import Path
import hashlib,json,subprocess
repo=Path('/root/probe/codex-damcause23')
base='64a28a7bdc44312924b14414501b7d4ff1d2d032'
text=subprocess.check_output(['git','-C',str(repo),'show',base+':port/dreamcast/game/game30.mk'],text=True)
start=text.index('# ISSUE52_ACTOR_DIAG=1:')
end=text.index('# MOTION_MISS_LOG=1',start)
block=text[start:end]
anchor='$(OBJDIR)/mod/st1_2/src/st1/r10c.o: GAME_CPPFLAGS += -DRE4DC_ISSUE52_ACTOR_DIAG=1\n'
added='$(OBJDIR)/src/game/em_set.o $(OBJDIR)/src/game/em.o $(OBJDIR)/src/game/read.o: GAME_CPPFLAGS += -DRE4DC_ISSUE52_ACTOR_DIAG=1\n'
assert block.count(anchor)==1 and added not in block
proposed=block.replace(anchor,anchor+added)
targets=['obj/src/game/em_set.o','obj/src/game/em.o','obj/src/game/read.o']
harness='OBJDIR := obj\n.DEFAULT_GOAL := report\n'+proposed+'\n.PHONY: report '+' '.join(targets)+'\nreport: '+' '.join(targets)+'\n'+' '.join(targets)+':\n\t@echo $@ $(GAME_CPPFLAGS)\n'
results=[]
for label,args,ok in [('default',[],True),('zero',['ISSUE52_ACTOR_DIAG=0'],True),
 ('one',['ISSUE52_ACTOR_DIAG=1'],True),('invalid',['ISSUE52_ACTOR_DIAG=2'],False),
 ('no_crash',['ISSUE52_ACTOR_DIAG=1','CRASH_SCREEN=0'],False),
 ('no_stage',['ISSUE52_ACTOR_DIAG=1','STAGE_OVL=0'],False),
 ('no_route',['ISSUE52_ACTOR_DIAG=1','ROUTE_OVL=0'],False)]:
 run=subprocess.run(['make','--no-print-directory','-rR','-f','-',
  'CRASH_SCREEN=1','STAGE_OVL=1','ROUTE_OVL=1',*args],input=harness,text=True,capture_output=True)
 assert (run.returncode==0)==ok,(label,run.stderr)
 if ok:
  rows=run.stdout.splitlines();assert len(rows)==3
  assert all(('-DRE4DC_ISSUE52_ACTOR_DIAG=1' in row)==(label=='one') for row in rows)
 results.append(dict(variant=label,exit=run.returncode,stdout=run.stdout,stderr=run.stderr))
out=Path('/mnt/c/Game Dev/Emulators/codex-lanes/damcause23/wiring-proposal01.json')
assert not out.exists()
out.write_text(json.dumps(dict(base=base,applied=False,source_sha256=hashlib.sha256(text.encode()).hexdigest(),
 proposal='One three-target GAME_CPPFLAGS line inside existing diagnostic block only',
 results=results,limits='Actual Make block evaluated with proposed line in memory; no shared file edit, object build or target acceptance'),indent=2)+'\n')
print(out)
