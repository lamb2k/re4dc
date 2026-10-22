"""Read-only compact programme plan revalidation. Never invokes target tools."""
from pathlib import Path
import gzip,hashlib,json,subprocess,shlex
M=Path(__file__).resolve().parent
def load(p):
 p=Path(p)
 if not p.exists() and p.parent==M:
  r=json.loads((M/'BULK-REFERENCES.json').read_text())[p.name];p=Path(r['path']);req(hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],'external compact table drift')
 return json.loads(gzip.decompress(p.read_bytes()) if str(p).endswith('.gz') else p.read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def req(c,s):
 if not c:raise RuntimeError(s)
def check(r):
 p=Path(r['path']);req(p.is_file() and sha(p)==r['sha256'],'input drift '+str(p))
for line in (M/'SHA256SUMS').read_text().splitlines():
 h,n=line.split('  ',1);req(sha(M/n)==h,'packet drift '+n)
p=load(M/'plan.json');T=Path(p['source_tree']);G=lambda *a:subprocess.check_output(['git',*a],cwd=T)
req(G('rev-parse','HEAD').decode().strip()==p['source'] and not G('status','--porcelain').strip(),'source drift/dirty')
req(not G('diff',p['runtime'],p['source'],'--','include','src','port/dreamcast/game','port/dreamcast/room').strip(),'runtime differs frombabfaa')
req(not Path(p['future_output']).exists(),'future output exists; preserve')
refs=load(M/'references.json')
for r in refs:check(r)
for r in load(M/'candidate-source-pins.json'):check(r)
P=next(Path(r['path']) for r in refs if r['path'].endswith('/plan02.json'));old=load(P)
for r in old['unchanged_library_pins']+old['link_support_pins']:check(r)
for r in old['frozen_overlay_derived_objects']:check(r['derived'])
O=Path('/root/probe/texture-rect21-program-pair-20261021-01');inventory=load(O/'out-off/object-file-identities.json');inv={r['path']:r for r in inventory};lines=(O/'out-off/build.log').read_text().splitlines()
drec=load(M/'native-ui-OFF-d-recovery.json');raw=Path(drec['source']).read_bytes();req(sha(Path(drec['source']))==drec['source_sha256'],'OFF dep source drift');raw=raw.replace(drec['single_substitution'][0].encode(),drec['single_substitution'][1].encode(),1);req(hashlib.sha256(raw).hexdigest()==drec['reconstructed_sha256'] and len(raw)==drec['reconstructed_bytes'],'OFF exact dependency recovery failed')
x=load(M/'object-matrix.json.gz');req(len(x['rows'])==446 and len(x['changes'])==15 and len(x['module_rows'])==32,'object census drift')
for r in x['rows']:
 logical=Path(x['prefix'])/r['r'];actual=O/r['override'] if r['override'] else logical
 req(sha(actual)==r['sha']==inv[str(logical)]['sha256'],'QA selected object mismatch '+r['r'])
 if r['dsha']:
  d=logical.with_suffix('.d');h=hashlib.sha256(raw).hexdigest() if r.get('dep_override') else sha(d);req(h==r['dsha']==inv[str(d)]['sha256'],'recorded dependency mismatch '+r['r'])
 if r['cl']:
  a=shlex.split(lines[r['cl']-1]);req(a[a.index('-o')+1]==str(logical),'compile reference mismatch')
for r in x['module_rows']:
 for i in r['inventory_indices']:check(inventory[i])
 for no in r['build_log_steps']:req(str(O/'obj'/x['rows'][r['object_id']]['r']) in lines[no-1],'module producer step mismatch')
req(x['counts']['direct_affected']==258 and x['module_affected_count']==32 and x['module_cManager_count']==32,'affected counts drift')
a=load(M/'link-plan.json.gz');req(len(a['all_final_linked_object_pins'])==447,'final link census')
for r in a['all_final_linked_object_pins']:check(r)
for arm,repls in a['replacements'].items():
 for i,r in repls.items():check(r);req('/'+('default' if arm=='off' else 'on')+'.o' not in r['path'],'ambiguous object naming')
 # Exact paths are derived from the two known source-unit names and arm.
 req({Path(r['path']).name for r in repls.values()}=={'sscrn-'+('default' if arm=='off' else 'on')+'.o','reset-'+('default' if arm=='off' else 'on')+'.o'},'replacement arm drift')
consumer=Path('/root/probe/codex-mipmap21-alpha-reader')
for r in load(M/'tool-closure-reuse.json')['immutable_consumer_helpers']:
 b=subprocess.check_output(['git','show',r['commit']+':port/dreamcast/tools/d367/link_closure21/'+r['file']],cwd=consumer);req(hashlib.sha256(b).hexdigest()==r['Git_blob_sha256'],'sealed consumer Git helper drift')
qa=load(M/'QA-control.json');check(qa['program']);check(qa['ELF'])
for r in qa['files']:check(r)
req(qa['program']['sha256']=='8942ad7e90d9adab56873d0738d76c274b98c28c35587e52fc93e2091f13300d','QA basis mismatch')
req(p['compiler_runs']==p['preprocessor_runs']==p['linker_runs']==0 and not p['lease'],'not source-only')
print(json.dumps(dict(state='COMPACT_SOURCE_PLAN_REVALIDATED_NO_COMPILER_LINKER_LEASE',source=p['source'],ordered_original_objects=446,ordered_final_objects=447,affected_current_objects=290,cManager_consumers=284,module_provenance=32,hard_OFF_gate_not_executed=True)))
