from pathlib import Path
import json,re,subprocess,hashlib,sys
D=Path('/root/probe/codex-backface-sh4zam-review/port/dreamcast/tools/d367/backface_sh4zam_review');R=Path('/root/probe/codex-backface-sh4zam-fused');O=R/'.fused-objects/compile10';F=R/'port/dreamcast/tools/d367/backface_sh4zam_fused'
ns={};exec((D/'dynamic-kernel-model-sdk.py').read_text().split('rows=[]')[0],ns);price=ns['price'];olddecode=ns['decode']
def decode(op):
 if op.split()[0] in ('jmp','braf'):return ('BR',2,[],[op.split('@')[-1]],{'bru'},[])
 if op.split()[0]=='jsr':return ('BR',2,['pr'],[op.split('@')[1]],{'bru'},[])
 return olddecode(op)
ns['decode']=decode
callerns={'__file__':str(F/'caller_test.py')};exec((F/'caller_test.py').read_text().split('p=argparse.ArgumentParser')[0],callerns)
Walk=callerns['WalkMachine'];base=callerns['base'];expected=callerns['expected']
obj=O/'walk-trace0.elf';before=hashlib.sha256(obj.read_bytes()).hexdigest();text=base.text_section(obj)
dis=subprocess.check_output(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objdump','-d',str(obj)],text=True)
ops={}
for line in dis.splitlines():
 m=re.match(r'\s*([0-9a-f]+):\s+[0-9a-f]{2} [0-9a-f]{2}\s+(.+)',line)
 if m:ops[int(m[1],16)]=re.sub(r'\b(bt|bf)\.s\b',r'\1/s',m[2].split('!')[0].strip())
class Trace(Walk):
 def __init__(self,*a,**kw):super().__init__(*a,**kw);self.events=[]
 def step(self,pc,delay=False):
  i=len(self.events);self.events.append([pc,ops[pc],None]);result=super().step(pc,delay);self.events[i][2]=result;return result
oracle=base.oracle_load(O/'oracle.so');rows=[]
for n in (4,8,16,32,64,128):
 for pattern in ('front','back','mixed'):
  pts=[(float(i),float(i&1)*(1 if pattern=='front'else-1))for i in range(n)]
  if pattern=='mixed':pts=[(float(i),float(((i//8)&1)*2-1)*(i&1))for i in range(n)]
  cache=base.generated_cache(pts);stream=bytes([n,*range(n)]);oc=bytes(256)
  m=Trace(text,cache,stream,oc,255,2);m.pc=int.from_bytes(obj.read_bytes()[24:28],'little');got=m.run();want=expected(oracle,cache,stream,oc,255,2);assert got==want
  cycles=price(m.events);rows.append(dict(vertices=n,triangles=n-2,pattern=pattern,emitted=len(got[0])//32,full_sdk_caller_modelled_cycles=cycles,per_input_triangle=round(cycles/(n-2),3),instructions=len(m.events)))
# Extra accepted first-outcode cases, with code4 on only the first index.
for pattern in ('front','back','mixed'):
 for batch in (1,32):
  n=64;pts=[(float(i),float(i&1)*(1 if pattern=='front'else-1))for i in range(n)]
  if pattern=='mixed':pts=[(float(i),float(((i//8)&1)*2-1)*(i&1))for i in range(n)]
  cache=base.generated_cache(pts);stream=bytes([n,*range(n)])*batch;oc=bytes([4])+bytes(255)
  m=Trace(text,cache,stream,oc,255,2);m.pc=int.from_bytes(obj.read_bytes()[24:28],'little');got=m.run();assert got==expected(oracle,cache,stream,oc,255,2)
  cycles=price(m.events);rows.append(dict(vertices=64,triangles=62,batch=batch,pattern=pattern,first_outcode=4,all_other_outcodes=0,emitted=len(got[0])//32,full_sdk_caller_modelled_cycles=cycles,per_strip=round(cycles/batch,3),per_input_triangle=round(cycles/(62*batch),3),instructions=len(m.events)))
# Interior depth crossing with first outcode zero remains a separate cost.
for position in (1,31,32,63):
 n=64;cache=base.generated_cache([(float(i),float(i&1))for i in range(n)]);stream=bytes([n,*range(n)]);oc=bytearray(256);oc[position]=1;oc=bytes(oc)
 m=Trace(text,cache,stream,oc,255,2);m.pc=int.from_bytes(obj.read_bytes()[24:28],'little');got=m.run();assert got==expected(oracle,cache,stream,oc,255,2)
 rows.append(dict(vertices=64,pattern='depth-cross',depth_position=position,emitted=len(got[0])//32,stop_offset=got[1],full_sdk_caller_modelled_cycles=price(m.events),instructions=len(m.events)))
# Oversize with first depth1 must preserve all-depth-before-limit order.
for name,oc in [('limit-first1-all1',bytes([1])*256),('limit-first1-rest0',bytes([1])+bytes(255))]:
 n=64;cache=base.generated_cache([(float(i),float(i&1))for i in range(n)]);stream=bytes([n,*range(n)])
 m=Trace(text,cache,stream,oc,63,2);m.pc=int.from_bytes(obj.read_bytes()[24:28],'little');got=m.run();assert got==expected(oracle,cache,stream,oc,63,2)
 rows.append(dict(vertices=64,pattern=name,emitted=len(got[0])//32,stop_offset=got[1],full_sdk_caller_modelled_cycles=price(m.events),instructions=len(m.events)))
# Include complete rejection/clip decisions with no SQ output.
for name,oc,limit in [('depth-all',bytes([1])*256,255),('screen-all',bytes([4])*256,255),('limit-stop',bytes(256),63),('depth-cross',bytes([1])+bytes(255),255)]:
 n=64;cache=base.generated_cache([(float(i),float(i&1))for i in range(n)]);stream=bytes([n,*range(n)]);m=Trace(text,cache,stream,oc,limit,2);m.pc=int.from_bytes(obj.read_bytes()[24:28],'little');got=m.run();assert got==expected(oracle,cache,stream,oc,limit,2)
 rows.append(dict(vertices=n,pattern=name,emitted=len(got[0])//32,stop_offset=got[1],full_sdk_caller_modelled_cycles=price(m.events),instructions=len(m.events)))
for batch in (2,4,8,16,32):
 for pattern in ('front','back','mixed'):
  n=64;pts=[(float(i),float(i&1)*(1 if pattern=='front'else-1))for i in range(n)]
  if pattern=='mixed':pts=[(float(i),float(((i//8)&1)*2-1)*(i&1))for i in range(n)]
  cache=base.generated_cache(pts);stream=bytes([n,*range(n)])*batch;oc=bytes(256)
  m=Trace(text,cache,stream,oc,255,2);m.pc=int.from_bytes(obj.read_bytes()[24:28],'little');got=m.run();assert got==expected(oracle,cache,stream,oc,255,2)
  cycles=price(m.events);rows.append(dict(vertices=64,triangles=62,batch=batch,pattern=pattern,emitted=len(got[0])//32,full_sdk_caller_modelled_cycles=cycles,per_strip=round(cycles/batch,3),per_input_triangle=round(cycles/(62*batch),3),instructions=len(m.events)))
assert hashlib.sha256(obj.read_bytes()).hexdigest()==before
files=[obj,O/'sdk-walk.o',O/'caller-gate-controls.json',O/'kernel-trace0.o',R/'.fused-objects/sdk-dev10/source/shz_strip.cpp',R/'.fused-objects/sdk-dev10/source/shz_strip.S',R/'.fused-objects/sdk-dev10/source/shz_strip_fused.inc',R/'.fused-objects/sdk-dev10/source/shz_strip_area.inc',R/'.fused-objects/sdk-dev10/include/sh4zam/shz_strip.h',F/'0001-strip-sq-api.patch',F/'manifest.json',F/'materialize.py',F/'caller_test.py']
result=dict(scope='MODELLED actual trace-off linked SDK world caller AND kernel, full function paths, no compiler/guest',working_head=subprocess.check_output(['git','-C',str(R),'rev-parse','HEAD'],text=True).strip(),source_state='Immutable compile10/dev06 inputs; repository patch is not updated yet and is not source proof for these new objects',files={str(f):dict(sha256=hashlib.sha256(f.read_bytes()).hexdigest(),bytes=f.stat().st_size)for f in files},rows=rows,limitations=['Existing AVK issue/latency/group approximation, actualbranchoutcomes; no cache/SQ/TA stalls or FPU exceptions.','Includes count stream/outcode/clip decisions, struct setup, calls, kernel, counters and returns. Excludes RE4 thin adapter above SDKAPI.','World count stream only; actors strip/whole use separately priced core and need adapter integration binding.','OFF reference is actual original world leanwalk from pairedCobject; same projected input patterns, outcodes and limits.','No stage1 speed acceptance, rendered-frame, scene-weighted or physical claim.'])
(D/'DYNAMIC-SDK-CALLER-FUSED10-MODEL.json').write_text(json.dumps(result,indent=2)+'\n')
for row in rows:
 if row['vertices']==64:print(row)



