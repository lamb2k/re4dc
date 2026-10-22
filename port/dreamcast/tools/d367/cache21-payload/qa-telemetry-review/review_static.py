"""Static AST/hash review only: never imports or invokes QA tools/tests/backends."""
import ast,copy,hashlib,json,subprocess
from pathlib import Path
R=Path('/root/probe/codex-qa21-death-repair');T=Path(__file__).resolve().parent
BASE='1bcbc5df33ed2f3b3dfaf376e06416b34f7176bb';FIRST='368b92fab4fcfdc48c98061611a872fb5ec693f7';FINAL='85bac7a7113816d3e8c9564d0c301ed4c670aa94';P='port/dreamcast/tools/d367/qa21_nontrace_guest/'
def blob(name,ref=FINAL):return subprocess.check_output(['git','-C',str(R),'show',ref+':'+P+name])
sha=lambda b:hashlib.sha256(b).hexdigest()
def tree(name,ref=FINAL):return ast.parse(blob(name,ref))
def func(node,name):return next(n for n in ast.walk(node)if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))and n.name==name)
def equal(a,b):return ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
controls={}
a,b=tree('input-deadlines.py',BASE),tree('input-deadlines.py')
for name in ['__init__','down','up','expire','release_all','close','release_before_capture']:
 controls['Inputs.'+name+'_AST_unchanged']=equal(func(a,name),func(b,name))
controls['late_bound_comparison_unchanged']=equal(next(n.test for n in ast.walk(func(a,'_up'))if isinstance(n,ast.If)and isinstance(n.test,ast.Compare)and isinstance(n.test.left,ast.Subscript)and isinstance(n.test.left.slice,ast.Constant)and n.test.left.slice.value=='queue_hold_upper_seconds'),next(n.test for n in ast.walk(func(b,'_up'))if isinstance(n,ast.If)and isinstance(n.test,ast.Compare)and isinstance(n.test.left,ast.Subscript)and isinstance(n.test.left.slice,ast.Constant)and n.test.left.slice.value=='queue_hold_upper_seconds'))
a,b=tree('guest-supervisor-core.py',BASE),tree('guest-supervisor-core.py')
controls['supervisor_constant_assignments_unchanged']=equal(ast.Module(body=[n for n in a.body if isinstance(n,ast.Assign)],type_ignores=[]),ast.Module(body=[n for n in b.body if isinstance(n,ast.Assign)],type_ignores=[]))
class RemoveNewTelemetry(ast.NodeTransformer):
 def visit_FunctionDef(self,n):
  if n.name=='retain_exit_telemetry':return None
  return self.generic_visit(n)
 def visit_Expr(self,n):
  if isinstance(n.value,ast.Call)and isinstance(n.value.func,ast.Name)and n.value.func.id=='cleanup'and n.value.args and isinstance(n.value.args[0],ast.Constant)and n.value.args[0].value=='retained exit telemetry':return None
  return self.generic_visit(n)
controls['monitor_AST_identical_after_removing_new_telemetry']=equal(func(a,'monitor'),RemoveNewTelemetry().visit(copy.deepcopy(func(b,'monitor'))))
a,b=tree('windows-backend.py',BASE),tree('windows-backend.py')
for n in b.body:
 if isinstance(n,ast.ClassDef)and n.name=='WindowsBackend':n.body=[x for x in n.body if not(isinstance(x,ast.FunctionDef)and x.name=='final_process_telemetry')]
controls['backend_AST_identical_except_added_final_reporter']=equal(a,b)
a,b=tree('inner-adapter.py',BASE),tree('inner-adapter.py')
for name in ['validate_role','input_allowed','elapsed','synchronize','post','release_all','qa_press','capture_work','capture','watch']:
 controls['inner.'+name+'_AST_unchanged']=equal(func(a,name),func(b,name))
assert all(controls.values()),controls
unchanged={}
for name in ['controller-core.py','policies.py','observe.py','observer-v2.py','outer-driver.py','guest-profile-v2.json','source-manifest.json','PLAN.md']:
 before,after=blob(name,BASE),blob(name);assert before==after,name;unchanged[name]={'sha256':sha(after),'bytes':len(after)}
manifest=json.loads(blob('failure-telemetry-manifest.json'));verified={}
for name,row in {**manifest['sources'],**manifest['receipts']}.items():
 actual=blob(name);assert len(actual)==row['bytes']and sha(actual)==row['sha256'],name;verified[name]=row
old=json.loads(blob('source-manifest.json'));mismatches={name:{'sealed_sha256':old['files'][name]['sha256'],'candidate_sha256':sha(blob(name))}for name in ['input-deadlines.py','inner-adapter.py','windows-backend.py','guest-supervisor-core.py']};assert all(r['sealed_sha256']!=r['candidate_sha256']for r in mismatches.values())
receipts={}
for name in manifest['receipts']:
 v=json.loads(blob(name));assert v['returncode']==0;receipts[name]={'sha256':sha(blob(name)),'platform':v['platform'],'returncode':0,'stderr':v['stderr'],'guest_qualified':v['guest_qualified']}
record={'scope':'Independent static AST/hash/source review only; no QA module imported, test rerun, native process test child or guest/build/stage/reseal; subprocesses perform git source reads only.','base':BASE,'first_candidate':FIRST,'reviewed_successor':FINAL,'static_controls':controls,'unchanged_sources':unchanged,'manifest_verified':verified,'retained_receipts_not_rerun':receipts,'old_launch_manifest_mismatches':mismatches,'review_finding':{'first_candidate':'Numeric pulse record could be lost by direct engine-up/release_all exception aggregation/stringification.','successor':'_up now calls existing fail callback after attaching pulse in both native-post and elapsed exception handlers, before wrappers;3 focused cases added,16 per platform retained.','disposition':'No remaining blocking defect found in the bounded telemetry change. Diagnostic failures remain fail-closed; cleanup and hard deadline paths remain independent.','limits':'No timing repair, reconstructed historical measurements, new allocation or runtime/target qualification. New tools remain rejected by unchanged old launch manifest.'}}
(T/'review.json').write_text(json.dumps(record,indent=2)+'\n');assert sum(p.stat().st_size for p in T.iterdir()if p.is_file())<1024**2
print(json.dumps({'successor':FINAL,'static_controls':len(controls),'controls_pass':all(controls.values()),'old_manifest_mismatches':list(mismatches),'review_bytes':(T/'review.json').stat().st_size},indent=2))
