"""Check source metadata only; does not execute any target command or materialize a view."""
from pathlib import Path
import ast,gzip,hashlib,json,os,subprocess
P=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def load(p):p=Path(p);return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def pin(r):
 p=Path(r['path']);assert p.is_file()and p.stat().st_size==r['bytes']and sha(p.read_bytes())==r['sha256']and str(p.resolve())==r['resolved_path'],p
plan=load(P/'plan.json');assert not any(plan['runs'].values());assert plan['task_order']==['em10-off','em10-on']
reuse=load(P/'provenance-reuse.json')
for r in reuse['references']+reuse['extra_tool_pins']:pin(r)
for n in ['system-header-pins.json.gz','toolchain-pins.json']:
 r=next(r for r in reuse['references']if r['path'].endswith('/'+n))
 for x in load(r['path']):pin(x)
r=next(r for r in reuse['references']if r['path'].endswith('/tool-extra-pins.json'))
for x in load(r['path']):pin(x)
source=load(P/'source-inputs.json.gz');view=load(P/'source-view.json');V=Path(view['destination']);assert len(source)==85
assert not V.exists(),'source-only packet expects no materialized view'
header=gzip.decompress((P/'historical-cManager.h.gz').read_bytes());assert sha(header)==view['C57_header_sha256']
for r in source:
 pin(r['candidate']);assert Path(r['view_path']).is_relative_to(V)
 if r['origin'].startswith('historical'):assert r['relative']=='include/cManager.h'and sha(header)==r['view_sha256']and len(header)==r['view_bytes']
 else:assert r['candidate']['sha256']==r['view_sha256']and r['candidate']['bytes']==r['view_bytes']
assert sum(r['view_bytes']for r in source)==view['raw_copied_payload_bytes']
tasks=load(P/'planned-tasks.json.gz');macro=load(P/'critical-macros.json')
ref=load(P/'reference-control.json');pin(ref['original_QA_object']);assert ref['reference_strip_not_executed']and len(ref['ordered_unchanged_13'])==13
for r in ref['ordered_unchanged_13']:
 x=r['object'];p=Path(x['path']);assert p.stat().st_size==x['bytes']and sha(p.read_bytes())==x['sha256']
for n,val in [('em10-off',0),('em10-on',1)]:
 t=tasks[n];assert t['expected_guard']==val and t['cwd']==view['cwd']and t['command'][t['command'].index('-c')+1]=='../../../src/em10/em10.cpp'
 defs={s[2:].split('=',1)[0]:(s[2:].split('=',1)[1]if'='in s else'1')for s in t['command']if s.startswith('-D')}
 assert defs['RE4DC_GANADO_ROUTINE_BYTES']==str(val)
 for k,v in macro['fixed'].items():assert defs[k]==v,(k,defs.get(k),v)
 for k in macro['guards_must_be_undefined_or_zero']:assert defs.get(k,'0')=='0',k
 assert all(str(Path(t['output_prefix'])).startswith(plan['future_output']+'/')for _ in[0])
 a=t['command'];k=a.index('-fstack-usage');prefix=a[:k];assert t['macro_command']==prefix+['-dM','-E','../../../src/em10/em10.cpp']
a=tasks['em10-off']['command'];b=tasks['em10-on']['command'];assert [s.replace('=0','=1').replace('em10-off','em10-on')if s.startswith('-DRE4DC_GANADO_ROUTINE_BYTES=')or'em10-off'in s else s for s in a]==b
run=Path(plan['existing_object_runner']['path']);pin(plan['existing_object_runner']);text=run.read_text();f={n.name:n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
for n,r in plan['pure_helpers'].items():assert sha(ast.get_source_segment(text,f[n]).encode())==r['sha256']
common=load(P/'common-runner04-reference.json')
for r in common['files']+[common['qualification'],common['seal']]:pin(r)

host=load(P/'compiler-host-tool-reuse.json')
pin(host['framework']);pin(host['source_snapshot_container'])
import lzma
snapshot=json.loads(lzma.decompress(Path(host['source_snapshot_container']['path']).read_bytes()))['source_tool_snapshot']
for r in snapshot['pins']:
 p=Path(r['path']);assert p.is_file()and p.stat().st_size==r['bytes']and sha(p.read_bytes())==r['sha256']and str(p.resolve())==r['resolved']
assert len(snapshot['pins'])==host['pin_count']==51
qa=load(P/'qa-tree-disposition.json');assert not qa['usable_direct_C57_tree']and qa['source_or_header_writes']==0 and qa['git_mutations']==0
# QA snapshot is disposition evidence only. The unused peer tree may advance its tools HEAD; no future compiler input resolves there.

print(json.dumps({'state':'SOURCE_CONTRACTS_PASS_NO_TARGET_TOOLS','tasks':list(tasks),'sources':85,'system_headers':reuse['verified_system_count'],'tools':reuse['verified_tool_count'],'QA_sparse_tree_preserved':True,'source_view_materialized':False,'old13_exact':True,'Event1':'HOLD','programme_OFF52190_all14_ELF_BSS':'UNEXECUTED_MANDATORY','runner_framework_duplicated':False}))
