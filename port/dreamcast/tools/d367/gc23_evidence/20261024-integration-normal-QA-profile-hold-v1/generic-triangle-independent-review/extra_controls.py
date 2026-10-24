"""Independent generic implementation adversaries; no scene or runtime inputs."""
import ast,hashlib,importlib.util,json,os,resource,subprocess,sys,tempfile,time
from pathlib import Path
from fractions import Fraction as F

def main(tool,out):
 resource.setrlimit(resource.RLIMIT_AS,(268435456,)*2);start=time.monotonic();tool=Path(tool);out=Path(out)
 spec=importlib.util.spec_from_file_location('review_shadow',tool/'exact_shadow.py');m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
 S=((-1,-1,0),(1,-1,0),(0,1,0));E=((0,0,1),);T=((-1,-1,-1),(1,-1,-1),(0,1,-1));checks=[]
 def check(name,condition):
  assert condition,name
  checks.append(name)
 def yes(x):return isinstance(x,m.TriangleProof)
 # A dense invertible affine map exercises all cross-product coordinates.
 matrices=(((2,1,3),(1,2,1),(3,1,2)),((0,1,0),(0,0,1),(1,0,0)),((-2,-1,-3),(1,2,1),(3,1,2)))
 for i,a in enumerate(matrices):
  def transform(p):return tuple(sum(F(a[k][j])*p[j] for j in range(3))+F(k+1,7) for k in range(3))
  check('dense/permuted/reflected3D affine-'+str(i),yes(m.cover_triangle(tuple(map(transform,E)),tuple(map(transform,S)),tuple(map(transform,T)))))
 panel=m.Panel(1,(S,(S[0],S[2],S[1])));source=m.SourceFace(panel,0)
 # Actual unchanged default budget boundary, not a monkeypatched small constant.
 allowed=m.cover_assigned(E*64,(T,)*128,(source,)*128)
 check('default73728 edge budget boundary accepted',isinstance(allowed,m.AssignedProof) and len(allowed.triangles)==128)
 refused=m.cover_assigned(E*64,(T,)*129,(source,)*129)
 check('default73728 edge budget next face refused',isinstance(refused,m.Unknown) and refused.reason=='WORK_LIMIT')
 outside=((9,0,-1),(10,0,-1),(9,1,-1))
 check('last supplied target cannot be silently skipped',isinstance(m.cover_assigned(E,(T,outside),(source,source)),m.Unknown))
 check('one supplied face is only a subset proof not inventory authentication',isinstance(m.cover_assigned(E,(T,),(source,)),m.AssignedProof))
 sources=tuple(m.SourceFace(m.Panel(i,(S,S)),0) for i in range(17))
 check('same geometry distinct realID candidates still exceed16',isinstance(m.cover_assigned(E,(T,)*17,sources),m.Unknown))
 # Extremely different input denominators remain exact; no finite float conversion.
 tiny=F(1,1<<255);check('supported tiny exact separation',yes(m.cover_triangle(E,S,((0,0,-tiny),)*3)))
 check('oversize denominator UNKNOWN',isinstance(m.cover_triangle(E,S,((0,0,-F(1,1<<256)),)*3),m.Unknown))
 check('no mutable source list accepted',isinstance(m.cover_triangle(E,list(S),T),m.Unknown))
 # Extract only the frozen literal mutant recipes, run each independently, and
 # retain the intended test method plus exact assertion trace (not syntax/import).
 source_text=(tool/'test_exact_shadow.py').read_text();tree=ast.parse(source_text)
 fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='test_semantic_mutants')
 assignment=next(n for n in fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='mutants' for t in n.targets));mutants=ast.literal_eval(assignment.value);details=[]
 original=(tool/'exact_shadow.py').read_text()
 with tempfile.TemporaryDirectory(prefix='shadow-review-mutants-',dir='/dev/shm') as tmp:
  for name,replacements,method in mutants:
   code=original
   for before,after in replacements:
    assert before in code
    code=code.replace(before,after)
   compile(code,name,'exec');path=Path(tmp)/(name+'.py');path.write_text(code)
   run=subprocess.run([sys.executable,'-B',str(tool/'test_exact_shadow.py'),'Controls.'+method],env={**os.environ,'TRIANGLE_SHADOW_HELPER':str(path)},capture_output=True,text=True,timeout=30)
   assert run.returncode==1 and 'AssertionError' in run.stderr and 'FAILED (failures=' in run.stderr and method in run.stderr
   assert 'SyntaxError' not in run.stderr and 'ImportError' not in run.stderr
   (out/('mutant-'+name+'.log')).write_text(run.stdout+run.stderr)
   details.append({'mutant':name,'method':method,'returncode':run.returncode,'intended_assertion_trace_sha256':hashlib.sha256((run.stdout+run.stderr).encode()).hexdigest()})
 result={'classification':'EXACT_REAL_GENERIC_IMPLEMENTATION_ONLY','checks':checks,'mutants':details,'scene_queries':0,'runtime_admitted':False,'source_sha256':hashlib.sha256((tool/'exact_shadow.py').read_bytes()).hexdigest(),'limits':{'address_bytes':268435456,'jobs':1,'peak_self_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'peak_child_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'seconds':time.monotonic()-start}}
 (out/'extra-controls.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main(*sys.argv[1:])
