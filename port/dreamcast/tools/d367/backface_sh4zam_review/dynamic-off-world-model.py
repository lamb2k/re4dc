from pathlib import Path
import json,hashlib
D=Path('/root/probe/codex-backface-sh4zam-review/port/dreamcast/tools/d367/backface_sh4zam_review')
ns={};src=(D/'dynamic-c-classifier-model.py').read_text();exec(src.split("O=Path(")[0],ns)
k=ns['k'];CM=ns['CM'];loadfn=ns['loadfn'];price=ns['price']
obj=Path('/root/probe/lanes/route/out-bfasabcfc8a3pair01crW/obj/platform/native_static.o')
text,ops=loadfn(obj,'walk_lean','.text._ZN5re4dc2vp9walk_lean')
rows=[]
for n in [4,8,16,32,64,128]:
 # Same outcodes all zero and one strip, ignoring facing (OFF).
 cache=k.generated_cache([(float(i),float(i&1)) for i in range(n)])
 m=CM(text,ops,cache,bytes([n,*range(n)]),2)
 m.map(0x7000,bytes(256));m.reg[4:8]=[0x8000,0x8000+n+1,0x7000,0x2000]
 m.write(m.reg[15],255,4);m.write(m.reg[15]+4,0x9000,4);m.write(m.reg[15]+8,0x9010,4);m.write(m.reg[15]+12,0x901c,4)
 m.write(0x9000,0xe0000000,4);m.write(0x9010,0,4);m.write(0x901c,0,4)
 try:stop=m.runC();cycles=price(m.events)
 except Exception as e:print('FAIL',n,e,[(hex(x[0]),x[1]) for x in m.events[-5:]]);raise
 assert stop==0x8000+n+1 and len(m.output)==n*32 and m.read(0x901c,4)==1
 rows.append(dict(vertices=n,emitted=n,function_cycles=cycles,per_input_triangle=round(cycles/(n-2),3),per_vertex=round(cycles/n,3)))
result=dict(scope='MODELLED actual original world walk_lean entire function; zero outcodes, one accepted strip, no caller',object_sha256=hashlib.sha256(obj.read_bytes()).hexdigest(),rows=rows,limitations=['No cache, memory, TA stalls; existing AVK issue-group/latency approximation.','Includes outcode scan/decisions and exact SQ copy plus function setup/exit; culling tests not in OFF.'])
(D/'DYNAMIC-OFF-WORLD-MODEL.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
