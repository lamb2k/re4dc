from pathlib import Path
import subprocess,re,json,hashlib,importlib.util,collections
ROOT=Path('/root/probe/codex-backface-sh4zam-review/port/dreamcast/tools/d367/backface_sh4zam_review')
def mod(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
K=Path('/root/probe/codex-backface-sh4zam-kernel/port/dreamcast/tools/d367/backface_sh4_kernel')
S=Path('/root/probe/codex-backface-sh4zam/port/dreamcast/tools/game30/avk/sim.py')
k=mod('kerneltests',K/'object_test.py');sim=mod('avksim',S)
OBJ=Path('/root/probe/backface-sh4zam-sdk-objects-20261022/kernel-trace0.o')
dis=subprocess.check_output(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objdump','-d',str(OBJ)],text=True)
ops={}
for line in dis.splitlines():
 m=re.match(r'\s*([0-9a-f]+):\s+[0-9a-f]{2} [0-9a-f]{2}\s+(.+)',line)
 if m:
  op=m[2].split('!')[0].strip();op=re.sub(r'\b(bt|bf)\.s\b',r'\1/s',op);ops[int(m[1],16)+0x100000]=op

def decode(op):
 name=op.split()[0];args=op[len(name):].strip()
 if name in ('mov.l','mov.w') and '<' in args:
  return ('LS',2,[args.rsplit(',',1)[1]],[],{'load'},[])
 if name in ('sts','lds','fsts','flds'):
  a,b=[x.strip() for x in args.split(',')];return ('LS',1,[b],[a],set(),[])
 if name in ('sts.l','lds.l'):
  a,b=[x.strip() for x in args.split(',')]
  if name=='sts.l':return ('LS',1,[],[a,'r15'],{'store'},['r15'])
  return ('LS',2,[b],['r15'],{'load'},['r15'])
 if name=='rts':return ('BR',2,[],['pr'],{'bru'},[])
 if name=='mova':return ('EX',1,['r0'],[],set(),[])
 return sim.decode(op)

def price(events):
 ready={};prev_t=0;paired=True;prev_g='CO';prev_defs=set();floor=0;last_branch=None;times=[];unknown=collections.Counter()
 for pc,op,nextpc in events:
  try:g,lat,defs,uses,kind,d2=decode(op)
  except Exception:
   unknown[op]+=1;raise
  dep=max([ready.get(u,0) for u in uses]+[0]);can=(not paired) and prev_g!='CO' and g!='CO' and (g!=prev_g or g=='MT') and not(set(defs)&prev_defs)
  if can and dep<=prev_t and floor<=prev_t:t=prev_t;paired=True
  else:t=max(prev_t+1,dep,floor);paired=False
  floor=0
  for d in defs:ready[d]=t+lat
  for d in d2:
   if d not in defs:ready[d]=t+1
  if last_branch is not None:
   floor=max(last_branch+2,t+1);last_branch=None
  if 'bru' in kind or ('brcd' in kind and nextpc!=pc+4):last_branch=t
  elif 'brc' in kind and nextpc!=pc+2:floor=t+2
  times.append(t);prev_t=t;prev_g=g;prev_defs=set(defs)
 return times[-1]+1

class Trace(k.Machine):
 def __init__(self,*a,**kw):super().__init__(*a,**kw);self.events=[]
 def step(self,pc,delay=False):
  i=len(self.events);self.events.append([pc,ops[pc],None]);result=super().step(pc,delay);self.events[i][2]=result;return result
rows=[]
for mode,mask in [('world',255),('actor-strip',127),('actor-whole',383)]:
 for n in [4,8,16,32,64,128]:
  for kind in ['front','back','mixed']:
   pts=[(float(i),float(i&1)*(1 if kind=='front' else -1)) for i in range(n)]
   if kind=='mixed':pts=[(float(i),float(((i//8)&1)*2-1)*(i&1)) for i in range(n)]
   ix=bytearray(range(n))
   if mask==383:ix[-1]|=128
   cache=k.generated_cache(pts);m=Trace(k.text_section(OBJ),cache,bytes(ix),mask,2)
   try:output=m.run()
   except Exception as e:print('CASEFAIL',mode,n,kind,str(e));raise
   cycles=price(m.events)
   rows.append(dict(mode=mode,input_vertices=n,triangles=n-2,case=kind,emitted_vertices=len(output[0])//32,modelled_function_cycles=cycles,modelled_cycles_per_input_triangle=round(cycles/(n-2),3),instructions=len(m.events)))
result=dict(scope='MODELLED actual opcode executed paths, not target execution or hardware timing',object_sha256=hashlib.sha256(OBJ.read_bytes()).hexdigest(),test_source_sha256=hashlib.sha256((K/'object_test.py').read_bytes()).hexdigest(),sim_source_sha256=hashlib.sha256(S.read_bytes()).hexdigest(),rows=rows,limitations=['Existing SH4 issue/latency/group rules; no cache, external memory, SQ destination/TA stalls or FPU exceptions.','Includes kernel prologue, full classify/front/back/split/copy, terminal EOL and epilogue; excludes caller outcode scan and C call/walk overhead.','No scene cycle totals or actor class acceptance without actual runtime strip distributions.','Historical slow baseline receipts are retained separately.'])
(ROOT/'DYNAMIC-KERNEL-MODEL-sdk-0f022725b.json').write_text(json.dumps(result,indent=2)+'\n')
for row in rows:
 if row['input_vertices']==64:print(row)



