from pathlib import Path
import json,hashlib
D=Path('/root/probe/codex-backface-sh4zam-review/port/dreamcast/tools/d367/backface_sh4zam_review')
ns={};exec((D/'dynamic-c-classifier-model.py').read_text().split("O=Path(")[0].replace("self.steps<50000","self.steps<200000"),ns)
k=ns['k'];CM=ns['CM'];loadfn=ns['loadfn'];price=ns['price'];obj=Path('/root/probe/lanes/route/out-bfasabcfc8a3pair01crW/obj/platform/native_static.o');text,ops=loadfn(obj,'walk_lean','.text._ZN5re4dc2vp9walk_lean');rows=[]
for batch in (1,2,4,8,16,32):
 n=64;stream=bytes([n,*range(n)])*batch;cache=k.generated_cache([(float(i),float(i&1))for i in range(n)])
 m=CM(text,ops,cache,stream,2);m.map(0x7000,bytes(256));m.reg[4:8]=[0x8000,0x8000+len(stream),0x7000,0x2000]
 for off,val in [(0,255),(4,0x9000),(8,0x9010),(12,0x901c)]:m.write(m.reg[15]+off,val,4)
 for addr,val in [(0x9000,0xe0000000),(0x9010,0),(0x901c,0)]:m.write(addr,val,4)
 stop=m.runC();cycles=price(m.events);assert stop==0x8000+len(stream) and len(m.output)==n*batch*32 and m.read(0x901c,4)==batch
 rows.append(dict(batch=batch,vertices_per_strip=n,function_cycles=cycles,per_strip=cycles/batch,per_input_triangle=round(cycles/(62*batch),3)))
result=dict(scope='MODELLED complete original OFF world walk, same multiple64-index accepted strips and one function lease',object_sha256=hashlib.sha256(obj.read_bytes()).hexdigest(),rows=rows,limitations=['Same existing issue-group/latency approximation; no caches/SQ/TA stalls.','Common transform/skin and RE4 adapter are outside both submission comparisons, not credited as savings.'])
(D/'DYNAMIC-OFF-WORLD-BATCH-MODEL.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

