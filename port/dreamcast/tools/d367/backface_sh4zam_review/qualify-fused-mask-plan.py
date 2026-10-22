from pathlib import Path
import itertools,json,random
D=Path('/root/probe/codex-backface-sh4zam-review/port/dreamcast/tools/d367/backface_sh4zam_review')
def runs(bits,n):
 out=[];i=0
 while i<n:
  if not(bits>>i&1):i+=1;continue
  a=i
  while i<n and(bits>>i&1):i+=1
  out.append((a,i))
 return out

def c_reference(F,n):
 keep=[bool(F>>i&1)for i in range(n)];i=0
 while i<n:
  if keep[i]:i+=1;continue
  a=i
  while i<n and not keep[i]:i+=1
  if a>0 and i<n and i-a<3:
   for j in range(a,i):keep[j]=True
 out=[];i=0
 while i<n:
  if not keep[i]:i+=1;continue
  a=i
  while i<n and keep[i]:i+=1
  if a&1:a-=1
  out.append((a,i))
 return out

def bit_parallel(F,n):
 valid=(1<<n)-1;F&=valid
 K=(F|((F<<1)&(F>>1))|((F<<1)&(F>>2))|((F<<2)&(F>>1)))&valid
 # bit i denotes original triangle i. Compute starts BEFORE repair.
 starts=K&~(K<<1)&valid
 odd=sum(1<<i for i in range(1,n,2))
 E=(K|((starts&odd)>>1))&valid
 return runs(E,n)
cases=0
for n in range(0,17):
 for F in range(1<<n):
  assert bit_parallel(F,n)==c_reference(F,n),(n,F,bit_parallel(F,n),c_reference(F,n));cases+=1
rng=random.Random(0xbace23)
for n in (30,31,32,33,34,60,61,62,63,64):
 for F in [0,(1<<n)-1,sum(1<<i for i in range(0,n,2)),sum(1<<i for i in range(1,n,2)),*[(1<<i)|(1<<j)for i in range(max(0,min(n-1,27)),min(n,36))for j in range(i+1,min(n,38))],*[rng.getrandbits(n)for _ in range(1000)]]:
  assert bit_parallel(F,n)==c_reference(F,n),(n,F);cases+=1
result=dict(scope='Host integer mask/formula design proof only; not SH4 opcodes or renderer execution',cases=cases,exhaustive_bits_through=16,boundaries=[30,31,32,33,34,60,61,62,63,64],orientation='bit i = original triangle i; all shifts logical64, mask to validbits',core='K=F|((F<<1)&(F>>1))|((F<<1)&(F>>2))|((F<<2)&(F>>1))',starts='R=K&~(K<<1)',repair='E=K|((R&odd_original_indices)>>1)',limitations=['Pure classification spans only. Actual emitted words/SQ/EOL/clip paths must retain target opcode differential tests.'])
(D/'FUSED-MASK-PLAN-CONTROLS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
