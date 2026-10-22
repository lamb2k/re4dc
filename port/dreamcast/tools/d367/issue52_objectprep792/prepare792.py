"""NEXT792 source-only plan creation. No compiler, macro, preprocessor, lease or link invocation."""
from pathlib import Path
import gzip,hashlib,json,os,subprocess
OWN=Path('/root/probe/codex-issue52-objects');M=OWN/'port/dreamcast/tools/d367/issue52_objectprep792'
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/issue52-792-objectprep-20261022');L=Path('/mnt/c/Game Dev/Emulators/codex-lanes/issue52-792-objectprep')
T=Path('/root/probe/codex-mipmap21-next792');OLD=Path('/root/probe/codex-mipmap21-next650')
P=OWN/'port/dreamcast/tools/d367/issue52_objectprep650';G=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/issue52-650-sh4-20261022-01')
ROOT=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/mipmap21-next792-integration-20261022/ROOT-selected792-20261022.json')
ROOT_SHA='a8e5a20512639e775e8f31415cbcf72957236204caf11a96045dbc0e13949339';SOURCE='63644457a2251a398de174f47be650e1b2b4c791';BASE='33504b9df434b82cd92e7bab3bb4630663a72ddd'
FUTURE=Path('/root/probe/issue52-792-sh4-objects-20261022-01');OLDOUT='/root/probe/issue52-650-sh4-objects-20261022-01'
def req(x,msg):
 if not x:raise RuntimeError(msg)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()
def row(p):return dict(path=str(p),resolved_path=str(p.resolve()),bytes=p.stat().st_size,sha256=sha(p))
def load(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_text())
def git(*a,cwd=T):return subprocess.check_output(['git',*a],cwd=cwd,text=True).strip()
def emit(name,v,compressed=False):
 b=(json.dumps(v,indent=2)+'\n').encode();b=gzip.compress(b,mtime=0) if compressed else b
 for root in (M,E):(root/name).write_bytes(b)
req(git('rev-parse','HEAD')==SOURCE and not git('status','--porcelain'),'root792 not clean frozen636444')
req(sha(ROOT)==ROOT_SHA,'root selected792 receipt mismatch')
r=load(ROOT);req(r['base_source']==BASE and r['descriptors']==792 and r['prior_descriptors_unchanged']==650 and r['additions']==142 and r['world_rect21_default']==0,'root source selection mismatch')
req(sha(P/'SHA256SUMS')=='6017b58466453cb84a1f77e6099c2f68e36a79fd4e2c27de7ed42e03b3e6046e','immutable650 prep seal mismatch')
for line in (P/'SHA256SUMS').read_text().splitlines():
 h,name=line.split('  ',1);req(sha(P/name)==h,'650 metadata drift '+name)
req(not M.exists() and not E.exists() and not FUTURE.exists(),'preserve existing namespace/output')
M.mkdir();E.mkdir()
changed={'scoped_representations.inc':'99c792ef','provenance_certificates.inc':'cf71b6e5','world_rect_bind.h':'489fde44','world_rect_provenance.h':'962e4f8e'}
folder=Path('port/dreamcast/tools/d367/texture_rect21');deltas=[]
for name,prefix in changed.items():
 p=T/folder/name;old=OLD/folder/name;req(sha(p).startswith(prefix),'selected runtime hash mismatch '+name)
 deltas.append(dict(relative_path=str(folder/name),candidate=row(p),prior650=row(old)))
req(sha(T/folder/'scoped_representations.inc')==r['table_sha256'] and sha(T/folder/'provenance_certificates.inc')==r['certificate_sha256'],'root table/certificate binding mismatch')
for name in ('native_ui','native_static'):
 p=Path('port/dreamcast/game/platform')/(name+'.cpp');req((T/p).read_bytes()==(OLD/p).read_bytes(),'unexpected TU source change '+name)
# All prior candidate inputs are remapped and freshly hashed; only four approved transitive inputs may differ.
inputs=[];prior650=load(P/'candidate-input-pins.json.gz')
for v in prior650:
 q=Path(v['path']);req(q.is_file() and sha(q)==v['sha256'],'immutable650 input drift '+str(q))
 try:rel=q.relative_to(OLD);new=T/rel
 except ValueError:rel=None;new=q
 req(new.is_file(),'792 dependency missing '+str(new))
 ischange=rel is not None and rel.parent==folder and rel.name in changed
 req(ischange or sha(new)==v['sha256'],'unexpected792 input delta '+str(new));inputs.append(row(new))
# Retained references are immutable old results, never labelled as newly executed792 gates.
refs=[ROOT,P/'SHA256SUMS',P/'planned-tasks.json',P/'candidate-input-pins.json.gz',P/'system-header-pins.json.gz',P/'toolchain-pins.json',P/'compiler-environment.json',P/'canonical-controls.json',P/'canonical-references.json',P/'expected-critical-macros.json',G/'object-gates.json',G/'final-audit.json',G/'FINAL-RESOURCE.json',G/'extra-pins.json']
for name in ('system-header-pins.json.gz','toolchain-pins.json'):
 for v in load(P/name):
  p=Path(v['path']);req(p.is_file() and sha(p)==v['sha256'] and str(p.resolve())==v['resolved_path'],'real tool/header drift '+str(p))
env=load(P/'compiler-environment.json')
for p in env['absent_include_roots']+env.get('absent_tool_specs',[]):req(not Path(p).exists(),'absence invariant changed '+p)
for k,v in env['influencing_environment'].items():req(os.environ.get(k)==v,'compiler environment drift '+k)
# Pin every controlled source file added/modified by main, including review-only tools/docs.
changed_paths=git('diff','--name-only',BASE,SOURCE).splitlines();source_files=[row(T/p) for p in changed_paths]
flags_path=Path('port/dreamcast/game/game30.mk');req((T/flags_path).read_bytes()==(OLD/flags_path).read_bytes(),'make flags/default drift')
inputs.append(row(T/flags_path));inputs.append(row(T/'port/dreamcast/kos-env.sh'))
tasks=load(P/'planned-tasks.json');mapping={}
for name,t in tasks.items():
 out={}
 for k,v in t.items():
  if isinstance(v,list):out[k]=[s.replace(OLDOUT,str(FUTURE)) for s in v]
  elif isinstance(v,str):out[k]=v.replace(str(OLD),str(T)).replace(OLDOUT,str(FUTURE))
  else:out[k]=v
 for field in ('command','macro_command','preprocess_command','full_dependency_command'):
  reverse=[s.replace(str(FUTURE),OLDOUT) for s in out[field]];req(reverse==t[field],'code flags changed '+name+' '+field)
 req(out['cwd']==str(T/'port/dreamcast/game'),'wrong future792 cwd');mapping[name]=out
emit('planned-tasks.json.gz',mapping,True)
emit('candidate-input-pins.json.gz',inputs,True)
emit('references.json',[row(p) for p in refs])
emit('selected-source-delta.json',deltas)
emit('root-source-files.json',source_files)
emit('plan.json',dict(state='SOURCE_ONLY_PLAN_NO_COMPILER_OR_LEASE',source=SOURCE,base_source=BASE,source_branch=git('branch','--show-current'),root_receipt=ROOT_SHA,table_sha256=r['table_sha256'],certificate_sha256=r['certificate_sha256'],bind_sha256=sha(T/folder/'world_rect_bind.h'),provenance_sha256=sha(T/folder/'world_rect_provenance.h'),world_rect21_default=0,descriptor_count=792,prior_unchanged_descriptors=650,additions=142,held_rooms=sorted(r['held']),runtime_source_owned_by_main=True,actual_source_input_count=len(inputs),frozen_review_source_files=len(source_files),future_output=str(FUTURE),six_task_order=['native_ui-default','native_ui-off','native_static-default','native_static-off','native_ui-on','native_static-on'],no_build_allocation=True,object_control_policy='Fresh792 default/explicit0/ON macro/preprocess/full-dependency/object tasks under same flags; old650 outputs only comparison references, never fresh792 evidence',programme_policy='Any future programme requires fresh complete actual-resolved tool pre/post/subprocess/plugin closure. Consumer owns helper; old650 or failedprogramme closure cannot certify792.',fresh_object_request_proposal=dict(hard_bytes=32*1024**2,soft_abort_bytes=24*1024**2,one_shared_slot=True,no_make_link_programme_stage_image_guest=True),source_plan_limit_bytes=512*1024))
req(git('rev-parse','HEAD')==SOURCE and not git('status','--porcelain'),'root792 changed during preparation')
print(json.dumps(dict(source=SOURCE,source_inputs=len(inputs),changed_runtime_inputs=len(deltas),planned_tasks=len(mapping),no_compilation_or_lease=True,source_and_mirror_bytes=sum(p.stat().st_size for root in (M,E) for p in root.rglob('*') if p.is_file()))))
