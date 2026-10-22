from pathlib import Path
import json,collections
D=Path('/root/probe/codex-backface-sh4zam-review/port/dreamcast/tools/d367/backface_sh4zam_review');ns={};exec((Path('/mnt/c/Game Dev/Emulators/codex-lanes/backface-sh4zam-review/dynamic-sdk-caller-fused12-model.py')).read_text().split('oracle=base.oracle_load')[0],ns)
base=ns['base'];Trace=ns['Trace'];text=ns['text'];obj=ns['obj'];decode=ns['ns']['decode']
cache=base.generated_cache([(float(i),float(i&1))for i in range(64)]);m=Trace(text,cache,bytes([64,*range(64)]),bytes(256),255,2);m.pc=int.from_bytes(obj.read_bytes()[24:28],'little');m.run()
ready={};prev_t=0;paired=True;prev_g='CO';prev_defs=set();floor=0;last_branch=None;timed=[]
for pc,op,nextpc in m.events:
 g,lat,defs,uses,kind,d2=decode(op);dep=max([ready.get(u,0)for u in uses]+[0]);can=(not paired)and prev_g!='CO'and g!='CO'and(g!=prev_g or g=='MT')and not(set(defs)&prev_defs)
 waiting=[u for u in uses if ready.get(u,0)>prev_t+1]
 if can and dep<=prev_t and floor<=prev_t:t=prev_t;paired=True
 else:t=max(prev_t+1,dep,floor);paired=False
 stall=max(0,t-(prev_t+1));timed.append(dict(pc=hex(pc),instruction=op,cycle=t,extra_wait_cycles=stall,waiting_registers=waiting,paired=paired))
 floor=0
 for d in defs:ready[d]=t+lat
 for d in d2:
  if d not in defs:ready[d]=t+1
 if last_branch is not None:floor=max(last_branch+2,t+1);last_branch=None
 if 'bru'in kind or('brcd'in kind and nextpc!=pc+4):last_branch=t
 elif 'brc'in kind and nextpc!=pc+2:floor=t+2
 prev_t=t;prev_g=g;prev_defs=set(defs)
positions=[i for i,e in enumerate(timed)if e['instruction'].split()==['rotcl','r5']];assert len(positions)==62
phase=timed[positions[1]+2:positions[2]+2];origin=phase[0]['cycle']
for row in phase:row['cycle']-=origin
counts=collections.Counter()
for row in phase:
 if row['extra_wait_cycles']:counts[row['instruction']]+=row['extra_wait_cycles']
result=dict(scope='MODELLED actual compile12 one representative fused phase, default no cache/memory/TA model',phase_cycles=phase[-1]['cycle']+1,phase=phase,extra_wait_by_instruction=dict(counts),limitations=['This explains the existing AVK approximation; no hardware scheduling proof.','Seven FE arithmetic/compare issues and fixed opcode serial dependencies remain; all regs and branch outcomes from actual interpreter path.'])
(D/'FUSED12-HOT-PHASE-SCHEDULE.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))



