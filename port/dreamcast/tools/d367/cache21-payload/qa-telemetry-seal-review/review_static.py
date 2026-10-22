"""Independent static seal review. Reads pinned git blobs; never imports QA or launches tests."""
import ast,copy,hashlib,json,subprocess
from pathlib import Path,PureWindowsPath
R=Path('/root/probe/codex-qa21-death-repair');T=Path(__file__).resolve().parent
BASE='85bac7a7113816d3e8c9564d0c301ed4c670aa94';REF='f63bb6de05630a4e06084baf769f2b4b364b3f0f';OLD='port/dreamcast/tools/d367/qa21_nontrace_guest/';NEW='port/dreamcast/tools/d367/qa21_nontrace_guest_telemetry_v1/';PREP='port/dreamcast/tools/d367/qa21_nontrace_run_preparation/telemetry-v1/'
sha=lambda b:hashlib.sha256(b).hexdigest()
def blob(name,ref=REF,prefix=NEW):return subprocess.check_output(['git','-C',str(R),'show',ref+':'+prefix+name])
def tree(name,old=False):return ast.parse(blob(name,BASE,OLD)if old else blob(name))
def func(n,name):return next(x for x in ast.walk(n)if isinstance(x,ast.FunctionDef)and x.name==name)
def equal(a,b):return ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
unchanged={}
for name in ['input-deadlines.py','inner-adapter.py','windows-backend.py','controller-core.py','policies.py','observe.py','observer-v2.py','capture-budget.py','layout-contract.py','r103-cold-keys.txt','empty-keys.txt','source-contract-v2.json','checkpoint-ABI.json','observer-v2-ABI.json']:
 a,b=blob(name,BASE,OLD),blob(name);assert a==b,name;assert blob(name,REF,OLD)==a,'old namespace changed:'+name;unchanged[name]={'bytes':len(b),'sha256':sha(b)}
controls={};a,b=tree('guest-supervisor-core.py',True),tree('guest-supervisor-core.py')
controls['core_constants_exact']=equal(ast.Module(body=[n for n in a.body if isinstance(n,ast.Assign)],type_ignores=[]),ast.Module(body=[n for n in b.body if isinstance(n,ast.Assign)],type_ignores=[]))
class RemoveFinalResources(ast.NodeTransformer):
 def visit_FunctionDef(self,n):
  return None if n.name=='retain_final_resources'else self.generic_visit(n)
 def visit_Expr(self,n):
  v=n.value
  if isinstance(v,ast.Call)and isinstance(v.func,ast.Name)and v.func.id=='cleanup'and v.args and isinstance(v.args[0],ast.Constant)and v.args[0].value=='final resource sample':return None
  return self.generic_visit(n)
controls['monitor_exact_except_added_final_resource_sample']=equal(func(a,'monitor'),RemoveFinalResources().visit(copy.deepcopy(func(b,'monitor'))))
a,b=tree('outer-driver.py',True),tree('outer-driver.py')
for name in ['validate_seed','output_paths','no_alias','hash_file','native_file_id']:
 controls['outer_'+name+'_AST_exact']=equal(func(a,name),func(b,name))
def arguments(node):return [ast.dump(n,include_attributes=False)for n in ast.walk(node)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='add_argument']
controls['parser_argument_definitions_exact']=arguments(func(a,'main'))==arguments(func(b,'parse_args'))
post_old,post_new=func(a,'postflight'),func(b,'postflight')
controls['postflight_acceptance_after_guard_exact']=all(equal(x,y)for x,y in zip(post_old.body[1:],post_new.body[1:]))and len(post_old.body)==len(post_new.body)
class Roots(ast.NodeTransformer):
 def visit_Constant(self,n):
  if n.value=='C:/Flycast-Evidence/re4-dreamcast/qa21-ganado-reader-telemetry-guests-20261022':n.value='C:/Flycast-Evidence/re4-dreamcast/qa21-ganado-reader-guests-20261021'
  return n
controls['fixed_profile_exact_except_owned_output_root']=equal(func(a,'fixed_profile'),Roots().visit(copy.deepcopy(func(b,'fixed_profile'))))
assert all(controls.values()),controls
profile=json.loads(blob('guest-profile-v2.json'));old_profile=json.loads(blob('guest-profile-v2.json',BASE,OLD))
for key in ['fixed_runtime','disc','template','retained_dependencies','limits','input_pulse_bounds','elf_path']:assert profile[key]==old_profile[key],key
observer=copy.deepcopy(profile['observer']);roles=copy.deepcopy(profile['roles'])
def oldpaths(v):
 if isinstance(v,str):return v.replace('qa21_nontrace_guest_telemetry_v1','qa21_nontrace_guest')
 if isinstance(v,list):return[oldpaths(x)for x in v]
 if isinstance(v,dict):return{k:oldpaths(x)for k,x in v.items()}
 return v
assert oldpaths(observer)==old_profile['observer']and oldpaths(roles)==old_profile['roles']
assert oldpaths(json.loads(blob('observer-binding-v2.json')))==json.loads(blob('observer-binding-v2.json',BASE,OLD))
manifest=json.loads(blob('source-manifest.json'));verified={}
for name,pin in manifest['files'].items():
 raw=blob(name);assert len(raw)==pin['bytes']and sha(raw)==pin['sha256'],name;verified[name]=pin
qualification=json.loads(blob('source-qualification.json'));coverage=[]
for row in qualification['coverage']:
 raw=blob(row['receipt']);assert sha(raw)==row['receipt_sha256'];receipt=json.loads(raw)
 result=next(x for x in receipt['results']if x['module']==row['module']);assert result['returncode']==0
 for name in row['dependencies']:assert receipt['sources'][name]==sha(blob(name)),(row['receipt'],name)
 coverage.append({'platform':row['platform'],'module':row['module'],'receipt':row['receipt'],'sha256':sha(raw),'module_returncode':0,'receipt_overall_pass':receipt['pass'],'stderr':result['stderr']})
prep_manifest=json.loads(blob('manifest.json',prefix=PREP))
for name,pin in prep_manifest.items():raw=blob(name,prefix=PREP);assert sha(raw)==pin['sha256']and len(raw)==pin['bytes'],name
request_raw=blob('LAUNCH-REQUEST.json',prefix=PREP);request=json.loads(request_raw);profile_sha=sha(blob('guest-profile-v2.json'));tools_sha=sha(blob('source-manifest.json'))
assert profile_sha==request['profile_sha256']=='4c386fa2fd826d2b04f7bf5b8696dca3e339dd92485c11b8ec91b863d21ce99b'
assert tools_sha==request['tools_sha256']=='0b12c09410599ee55c96d49875dadf5236b210ef8d8267cc0d7aaa82ad921bfd'
assert sha(request_raw)=='a6f4c5fbeeda607712df3317665a6f5c7786f0a8d6b08e4a99ffdeee105ba9da'
argv=request['argv'];assert len(argv)==10 and argv[2::2]==['--profile','--profile-sha256','--tools-sha256','--mode']and argv[-1]=='cold-shoot01'
assert argv[5]==profile_sha and argv[7]==tools_sha and request['seed']is None and request['automatic_retry']is False and request['later_role_allocation']is False
assert PureWindowsPath(argv[1]).name=='outer-driver.py'and PureWindowsPath(argv[1]).parent.name=='qa21_nontrace_guest_telemetry_v1'and PureWindowsPath(argv[3]).parent==PureWindowsPath(argv[1]).parent
assert request['fixed_program']==profile['fixed_runtime']and request['output_root']==profile['evidence_root']
preflight=json.loads(blob('readonly-preflight.json',prefix=PREP));assert preflight['pass']and sha(blob('readonly-preflight.json',prefix=PREP))==request['readonly_fullpreflight_sha256']
refs=profile['retained_source_references'];image=refs['files']['track03.iso'];assert image['expected_source_links']==2 and image['sha256']==profile['disc']['files']['track03.iso']['sha256']and int(image['source_native_id'],16)==int(profile['disc']['files']['track03.iso']['native_id'],16)
for name in ['track01.bin','track02.raw','track03.iso']:
 pin,observed=refs['files'][name],preflight['native_source'][name];assert int(pin['source_native_id'],16)==int(observed['native_file_id'],16)and pin['source_mtime_ns']==observed['mtime_ns']and observed['samefile_failed_reference']
 assert observed['links']==(2 if name=='track03.iso'else 13)
record={'scope':'Independent pinned source/AST/hash review only. No QA imports/tests/native child/guest/build/image writer or seal mutation. Retained live preflight is not refreshed allocation.','base':BASE,'reviewed':REF,'unchanged85bac_modules':unchanged,'static_controls':controls,'manifest_files_verified':len(verified),'manifest_pins':verified,'source_qualification_coverage':coverage,'profile_sha256':profile_sha,'tools_sha256':tools_sha,'launch_request_sha256':sha(request_raw),'launch_argv':argv,'retained_preflight_sha256':sha(blob('readonly-preflight.json',prefix=PREP)),'retained_preflight_utc':preflight['utc'],'retained_native_source':preflight['native_source'],'track03_strict_expected_identity':image,'fixed_program':profile['fixed_runtime'],'limits':profile['limits'],'new_final_resource_policy':'Sample after owned stop/waits/job-empty attempt and before handle close; exceptions/violations veto qualification through existing cleanup; live hardguard stays armed until proven emptiness.','disposition':'No blocking defect found in bounded immutable telemetry-v1 seal changes. Source-review clear; main alone owns launch review/allocation/fresh resource and identity admission.','limitations':['No new live preflight/full image hash or resource snapshot','No rerun of portable or native host-process tests','Tiny native host tests are not Flycast acceptance','Prior failed shooting stays failed; no lost timing reconstructed; no deadline repair or guaranteed next-shot success','Normal launch requires exact pins and fresh peer reservations; no automatic retry/later role allocation']}
(T/'review.json').write_text(json.dumps(record,indent=2)+'\n');assert sum(p.stat().st_size for p in T.iterdir()if p.is_file())<2*1024**2
print(json.dumps({'commit':REF,'controls':len(controls),'manifest_files':len(verified),'coverage_modules':len(coverage),'request_sha256':sha(request_raw),'review_bytes':(T/'review.json').stat().st_size},indent=2))
