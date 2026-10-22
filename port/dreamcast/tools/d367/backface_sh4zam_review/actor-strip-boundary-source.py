"""Pure source producer bound test; no compiler, package/image or ASM execution."""
import ast,hashlib,json,subprocess
from pathlib import Path
T=Path('/root/probe/codex-backface-sh4zam-review');P='port/dreamcast/tools/strip64_build_blob.py'
b=subprocess.check_output(['git','-C',str(T),'show','64a28a7b:'+P]);tree=ast.parse(b)
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='split_strips')
G={'STRIP_MAX':64};exec(compile(ast.Module(body=[fn],type_ignores=[]),P,'exec'),G)
def runs(s):
 out=[];a=[]
 for v in s:
  a.append(v&127)
  if v&128:out.append(a);a=[]
 assert not a
 return out
def tris(rs):
 out=[]
 for r in rs:
  for j in range(len(r)-2):
   x=(r[j],r[j+1],r[j+2])
   out.append(x if not(j&1) else(x[1],x[0],x[2]))
 return out
cases=[]
for n in [3,64,65,255,256,512]:
 raw=[i&127 for i in range(n)];raw[-1]|=128
 got=G['split_strips'](raw);rr=runs(got)
 assert max(map(len,rr))<=64
 assert tris(rr)==tris(runs(raw))
 cases.append({'input_single_strip':n,'output_lengths':list(map(len,rr)),'same_ordered_winding_triangles':True,'owned_source_bound_before_runtime':64,'C_reference_classification':('comment_contract_stress_array_safe'if n<=256 else'OUTSIDE_C_PLAIN256_ARRAY_NOT_EXECUTED')})
raw=[]
for k in range(8):
 r=[(j+k)&127 for j in range(64)];r[-1]|=128;raw.extend(r)
got=G['split_strips'](raw);assert len(got)==512 and runs(got)==runs(raw)
out={'base':'64a28a7bdc44312924b14414501b7d4ff1d2d032','source_path':P,'source_sha256':hashlib.sha256(b).hexdigest(),'scope':'actual Python producer split function only, no C/ASM oracle or data/target run','cases':cases,'whole_stream512_eight_valid64_strips_preserved':True,'actual_C_guard_correction':'backface_emit.hpp only n<3 guard; n>255 is documented precondition, not runtime refusal. n256 fits arrays but exceeds comment. n257+ plain[256] overflow.','owned_accepted_source_proof':'coarse_actor_preflight.h ++len>64 refuses; package/geometry preflight beforepublication; runtimeConverter andLODstripify cap64. Genericblob_of signature alone is not arbitraryblobvalidation.'}
D=T/'port/dreamcast/tools/d367/backface_sh4zam_review';O=D/'ACTOR-STRIP-BOUNDARY-SOURCE.json';assert not O.exists();O.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'cases':len(cases),'whole_stream512':True,'source_only':True,'receipt_sha256':hashlib.sha256(O.read_bytes()).hexdigest()}))

