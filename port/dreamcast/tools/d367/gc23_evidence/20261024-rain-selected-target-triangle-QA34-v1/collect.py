"""Frozen rain target tools, generic triangle tools, and QA preparation evidence."""
from pathlib import Path
from collections import Counter
import ast, datetime, hashlib, json, os, subprocess
T=Path('/root/work/lanes/gc23-evidence-tools')
C=Path('/mnt/c/Game Dev/Emulators/codex-lanes')
HERE=Path(__file__).resolve().parent
PARENT='6a7783ae2e7407eff23124b844d3b39ec1993f79'
BASE='port/dreamcast/tools/d367/gc23_evidence'
DEST=T/BASE/'20261024-rain-selected-target-triangle-QA34-v1'
sha=lambda b:hashlib.sha256(b).hexdigest()
read=lambda p:json.loads(p.read_text())
git=lambda tree,*a:subprocess.check_output(['git','-C',str(tree),*a])
def raw(p):
 a=p.stat();b=p.read_bytes();z=p.stat();assert (a.st_size,a.st_mtime_ns)==(z.st_size,z.st_mtime_ns) and not p.is_symlink(),p
 return b,a.st_mtime_ns
def identity(p):
 a=p.stat()
 with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
 z=p.stat();assert (a.st_size,a.st_mtime_ns)==(z.st_size,z.st_mtime_ns)
 return {'source':str(p),'bytes':a.st_size,'sha256':h,'source_mtime_ns':a.st_mtime_ns}
def text(b,n):
 try:return b.decode('utf-8'),'utf-8'
 except UnicodeDecodeError:
  assert n.endswith('.md');return b.decode('cp1252'),'non-UTF8 original; cp1252-compatible diagnostic only'
def main():
 assert git(T,'rev-parse','HEAD').decode().strip()==PARENT and not git(T,'status','--porcelain') and not DEST.exists()
 assert os.statvfs('/mnt/c').f_bavail*os.statvfs('/mnt/c').f_frsize>=24*1024**3
 selected=[];hashes=[];references=[];prior={};verified=[];extracts=[]
 for mp in (T/BASE).glob('*/SOURCE-MANIFEST.json'):
  for r in read(mp)['files']:prior.setdefault((r['bytes'],r['sha256']),(mp.parent/r['destination']).relative_to(T).as_posix())
 def add(p,rel,pin=None,dedup=True):
  b,stamp=raw(p);key=(len(b),sha(b))
  if pin:assert len(b)==pin.get('bytes',pin.get('size')) and sha(b)==pin['sha256'],p
  if dedup and key in prior:
   old=prior[key];assert (T/old).read_bytes()==b
   references.append({'source':str(p),'logical_destination':rel,'bytes':len(b),'sha256':sha(b),'prior_archive_path':old,'ancestor':PARENT});return
  assert b'\0' not in b and len(b)<12*1024**2;text(b,str(p));selected.append((str(p),rel,b,stamp))
 def hashonly(p,rel,pin=None,why='Excluded payload; source/metadata identity only.'):
  row=identity(p)
  if pin:assert row['bytes']==pin.get('bytes',pin.get('size')) and row['sha256']==pin['sha256'],p
  hashes.append(dict(row,logical_destination=rel,payload_copied=False,disclosure=why))
 def dictmanifest(root,label,name='SHA256-MANIFEST.json'):
  pins=read(root/name)
  for n,pin in pins.items():add(root/n,label+'/'+n,pin)
  add(root/name,label+'/'+name);verified.append({'source':str(root/name),'label':label,'name':name,'members':len(pins),'sha256':sha((root/name).read_bytes())})
 docs=read(HERE/'stable-dated-inputs/CAPTURED-DOCS.json')
 for r in docs['files']:add(HERE/'stable-dated-inputs'/r['snapshot'],'dated-root-docs/'+r['snapshot'],r,dedup=False)
 add(HERE/'stable-dated-inputs/CAPTURED-DOCS.json','dated-root-docs/CAPTURED-DOCS.json',dedup=False)
 rain=C/'rain-diag24';rtree=Path('/root/work/lanes/rain-diag24')
 for v,commit in [('v1','da4cf4518df491b1d26c8615a263ba0ff5911799'),('v2','a7bffa9e318aa4143e97a32a5fbe7ae8e52838a1')]:
  root=rain/('target-matrix-root-repair-'+v);seal=read(root/'SOURCE-SEAL.json');assert seal['head']==commit
  for n,pin in seal['members'].items():
   add(root/n,'rain-root-tool-'+v+'/'+n,pin)
   assert (root/n).read_bytes()==git(rtree,'show',commit+':port/dreamcast/tools/d367/rain_diag24/target_matrix/'+n)
  add(root/'SOURCE-SEAL.json','rain-root-tool-'+v+'/SOURCE-SEAL.json')
  n='port/dreamcast/tools/d367/rain_diag24/target_matrix/run-matrix.sh';b=git(rtree,'show',commit+':'+n)
  selected.append(('git:'+commit+':'+n,'rain-root-tool-'+v+'/run-matrix.sh',b,None))
  verified.append({'source':str(root/'SOURCE-SEAL.json'),'label':'rain-root-tool-'+v,'name':'SOURCE-SEAL.json','members':len(seal['members']),'sha256':sha((root/'SOURCE-SEAL.json').read_bytes())})
 for leaf in ['review-rain-targetda4','review-rain-targeta7']:
  dictmanifest(C/'gc-motion24'/leaf,leaf)
 for n in ['TARGET-READBACK-v1.json','ROOT-SELECTED-TARGET-GRANT-v1.json']:
  add(rain/n,'rain-selected-target/'+n)
 for n in ['TARGET-READBACK.json','record-reference-ledger.json']:
  add(C/'gc-motion24/review-rain-targetrun-a7'/n,'rain-selected-target-review/'+n)
 target=Path('/dev/shm/rain-diag24-target-root_a7_20261024_r1');matrix=read(target/'matrix-result.json')
 assert matrix['selected_compilation_complete'] and len(matrix['case_names'])==8
 for name,pin in matrix['artifacts'].items():
  p=target/name;rel='rain-target-matrix/'+name
  if p.suffix in {'.json','.d','.su'} and not p.name.endswith('disassembly.txt'):add(p,rel,pin)
  else:hashonly(p,rel,pin,'Selected target object, preprocessor/disassembly, log, or environment payload excluded.')
 for n in ['matrix-result.json','pins.json','grant.json','RESERVED.json']:
  if n not in matrix['artifacts']:add(target/n,'rain-target-matrix/'+n)
 for n in ['environment.nul','environment-bootstrap.log']:
  if n not in matrix['artifacts']:hashonly(target/n,'rain-target-matrix/'+n)

 # Generic importer/runner code only. Authenticated actual reports and per-target summaries remain private.
 tri=Path('/root/work/lanes/triangle-opportunity-prep24');rev='78cbd962ee0d98dc700d0fb452500a16ac35b14c'
 prefix='port/dreamcast/tools/d367/actual_triangle_audit24/'
 names=git(tri,'ls-tree','-r','--name-only',rev,prefix).decode().splitlines();assert len(names)==10
 for n in names:
  b=git(tri,'show',rev+':'+n)
  if n.endswith('PREPARATION-SUMMARY.json'):
   hashes.append({'source':'git:'+rev+':'+n,'bytes':len(b),'sha256':sha(b),'logical_destination':'generic-triangle/'+n,'payload_copied':False,'disclosure':'Per-target physical index arrays deliberately excluded.'});continue
  if Path(n).name in {'prepare.py','test_prepare.py','README.md','origin-before-checkpoint.txt'}:
   assert b==git(tri,'show','d8620e8b6a13706d89aa8415d3397f5f4d06c589:'+n)
  selected.append(('git:'+rev+':'+n,'generic-triangle/'+n,b,None))
 for root,label in [(C/'interior-discovery24/root-prep-readback-v1','triangle-root-prep-readback'),(C/'interior-discovery24/root-runner-review-v3','triangle-root-runner-review')]:
  for p in root.iterdir():
   assert p.is_file() and p.suffix in {'.json','.log'};add(p,label+'/'+p.name)
 tprep=C/'triangle-opportunity-prep24/PREPARATION-SUMMARY.json';tp=read(tprep);hashonly(tprep,'triangle-private-preparation/PREPARATION-SUMMARY.json',why='Per-target physical index arrays excluded; nonprivate aggregate extracted separately.')
 extracts.append({'source':str(tprep),'parent_sha256':sha(tprep.read_bytes()),'JSON_pointers':{'/classification':tp['classification'],'/summary':tp['summary'],'/limits':tp['limits'],'/actual_shadow_predicate_calls':tp['actual_shadow_predicate_calls'],'/new_rays':tp['new_rays'],'/ledger_accesses':tp['ledger_accesses']}})
 rootread=read(C/'interior-discovery24/root-prep-readback-v1/ROOT-READBACK.json')
 for k in ['original_report','fresh_report']:hashonly(Path(rootread[k]['path']),'triangle-private-reports/'+k+'.json',{'sha256':rootread[k]['sha256'],'bytes':Path(rootread[k]['path']).stat().st_size},'Actual geometry report; no payload archived.')
 actual=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/interior-vis23-20261023/actual-triangle-hut647-root-r1/report.json');ar=read(actual)
 assert sha(actual.read_bytes())=='7e301a48c99a46afc2397d9e823aab08c1b5b0c0e9add46af7ed80d3835afef8' and len(ar['results'])==75 and not ar['runtime_admitted']
 hashonly(actual,'triangle-private-reports/actual75-report.json',why='Actual geometry/case/results arrays excluded; only scalar result counters extracted.')
 safe=['classification','generic_source','limits','work','seconds','peak_rss_kib','new_rays','ledger_accesses','runtime_admitted']
 extracts.append({'source':str(actual),'parent_sha256':sha(actual.read_bytes()),'JSON_pointers':{'/'+k:ar[k] for k in safe},'derived_case_count':len(ar['results']),'derived_status_counts':dict(Counter(r['status'] for r in ar['results'])),'excluded':['plan','prepared','held_camera_cases','results','seal']})

 # Frozen 34-member preparation seal; IP and input fixtures are identities only, never copied.
 qa=C/'gc-motion24/qa-memory-media-prep';qseal=read(qa/'TOOLCHAIN-SEAL.json')
 assert sha((qa/'TOOLCHAIN-SEAL.json').read_bytes())=='130d48651e89216555a01f2f481eb76490494491e6a934acab1fd9094c75d786' and len(qseal['members'])==34
 for n,pin in qseal['members'].items():
  p=qa/n
  if n=='SOURCE-IP.BIN' or n.startswith('fixtures/') or n=='FUTURE-GUEST-COMMANDS.json':hashonly(p,'QA-sealed-preparation/'+n,pin,'Private input/fixture or future guest-command payload excluded; seal identity only.')
  else:add(p,'QA-sealed-preparation/'+n,pin)
 # Dependency metadata contains path/hash/extent records, no encoded private byte arrays.
 census=read(qa/'DEPENDENCY-CENSUS.json')
 def no_byte_arrays(v):
  if isinstance(v,list):
   assert not (len(v)>16 and all(isinstance(x,(int,float)) for x in v))
   for x in v:no_byte_arrays(x)
  elif isinstance(v,dict):
   for x in v.values():no_byte_arrays(x)
 no_byte_arrays(census)
 add(qa/'TOOLCHAIN-SEAL.json','QA-sealed-preparation/TOOLCHAIN-SEAL.json')
 add(qa/'ROOT-SUPPLEMENTAL-CLOSURE-v1.json','QA-root-review/ROOT-SUPPLEMENTAL-CLOSURE-v1.json')
 for n in ['ROOT-REVIEW.json','ROOT-CONTROLS.json','CONTROLS.log']:
  add(C/'gc-motion24/qa-memory-media-root-review-v1'/n,'QA-root-review/'+n)
 for label,row in qseal['external_tools'].items():
  p=Path(row['path'])
  if p.suffix in {'.py','.sh'}:add(p,'QA-external-generic-tools/'+label+p.suffix,row['identity'])
  else:hashonly(p,'QA-external-tool-identities/'+label,row['identity'],'External host binary identity only; never copied or executed.')
 add(Path(__file__).resolve(),'collect.py',dedup=False)
 counts=Counter(r for _,r,_,_ in selected)
 assert len(counts)==len(selected),[(n,c) for n,c in counts.items() if c>1]
 assert sum(len(b) for _,_,b,_ in selected)<24*1024**2
 DEST.mkdir(parents=True);(DEST/'.gitattributes').write_text('* -text\n** -text\n');rows=[];syntax=[]
 for source,rel,b,stamp in selected:
  assert b'\0' not in b;s,encoding=text(b,rel)
  if rel.endswith('.py'):ast.parse(s,filename=source);syntax.append(rel)
  if rel.endswith('.sh'):subprocess.run(['bash','-n'],input=b,check=True);syntax.append(rel)
  out=DEST/rel;out.parent.mkdir(parents=True,exist_ok=True);out.open('xb').write(b)
  rows.append({'source':source,'destination':rel,'bytes':len(b),'sha256':sha(b),'lf_sha256':sha(b.replace(b'\r\n',b'\n')),'crlf_count':b.count(b'\r\n'),'text_encoding':encoding,'source_mtime_ns':stamp})
 def emit(n,j):(DEST/n).write_text(json.dumps(j,indent=2)+'\n')
 emit('SOURCE-MANIFEST.json',{'parent_evidence_commit':PARENT,'captured_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'root_docs_frozen_utc':docs['captured_utc'],'files':rows})
 emit('HASH-ONLY-ARTIFACTS.json',{'files':hashes,'payload_copied':False})
 emit('PRIOR-ARCHIVE-REFERENCES.json',{'files':references,'policy':'Exact prior ancestor bytes referenced, no duplicate payload.'})
 emit('NONPRIVATE-TRIANGLE-SUMMARY-EXTRACTS.json',{'extracts':extracts,'policy':'Exact named JSON fields/scalar counters only; per-target physical IDs and geometry/result arrays excluded.'})
 emit('VALIDATION.json',{'verified_manifests':verified,'QA_seal_members':34,'syntax_only_checked':syntax,'rain_selected_cases':8,'triangle_actual_cases':75,'triangle_report_sha256':'7e301a48c99a46afc2397d9e823aab08c1b5b0c0e9add46af7ed80d3835afef8','SDK_or_guest_runs':0,'runtime_or_integration_mutation':False,'active_stage_outputs_or_plans_captured':False,'private_geometry_or_binary_payloads_copied':False,'limits':'Rain selected target metadata only, no full programme/guest/cache/look acceptance. Triangle exact-real opportunity only, no runtime/numeric-raster/continuous-view/cull certificate. QA preparation/root stage-only clear, no staging completion/media/guest/memory claim; frozen historical HOLD and EOL bridge remain separate dated records.'})
 (DEST/'README.md').write_text('''# Frozen rain selected-target, triangle opportunity and QA34 preparation checkpoint

Append-only successor to6a7783ae. Root STATUS/updater/CARRY frozen09:11:24.715521Z on2026-10-24. Live docs, active staging outputs and current mutable guest plans remain independent. No SDK, build, guest, active tree/source/runner change or integration push was performed by preservation.

Preserves exact da4cf4518/a7bffa9e3 root tool seals, source helpers/PINS and both independent reviews, plus allocated eight-case selected-target metadata and readbacks. Objects, preprocessed source, disassembly, logs and environment payloads are identities only. This records selected-object compile/relocation/provider evidence, not full-programme/stack/cache/guest/appearance acceptance.

Preserves generic importer d862 and runner78cbd tools and root source/host reviews. Actual geometry reports and per-target preparation summaries are hash-only. The75-case7e301a48 actual result has only nonprivate aggregate counters and scalar JSON fields extracted with source hash/pointers; physical IDs, geometry, case/plan/results arrays are excluded. Exact-real opportunity evidence does not establish runtime or raster/continuous-view/culling acceptance.

QA TOOLCHAIN-SEAL130d authenticates34 frozen preparation members. Safe scripts/profile/pin/dependency/EOL and root supplemental-stage-only review metadata are preserved; dependency census is paths/hashes metadata without numeric private-byte arrays. SOURCE-IP.BIN, all fixtures and future guest-command JSON are hash-only. Six external host tools are hashed; only the two generic source wrappers are copied, no external binaries executed. Root stage-only clearance is a dated preparation decision, not staging completion, media, guest, heap or memory acceptance. Original QA broad-map/HOLD and historical header mismatch remain unchanged in older records; later six-key/EOL bridge/root supplement records are kept separately. Active stage session/output/grant and current guest plans are excluded.

All originals retain exact bytes, including CRLF and non-UTF8 CARRY data; LF hashes are diagnostic. Compact host-control logs may be retained. Prior archive paths remain unchanged, and repeated exact metadata is referenced by ancestor path/hash. No objects/programmes/ELFs/SDK bytes, private assets/geometry, captures or raw game logs are copied.
''')
 files=sorted(p for p in DEST.rglob('*') if p.is_file());(DEST/'SHA256SUMS').write_text(''.join(sha(p.read_bytes())+'  '+p.relative_to(DEST).as_posix()+'\n' for p in files))
 print(json.dumps({'snapshot':str(DEST),'original_inputs':len(rows),'original_bytes':sum(r['bytes'] for r in rows),'files':len(files)+1,'hash_only_artifacts':len(hashes),'prior_references':len(references),'seal_sha256':sha((DEST/'SHA256SUMS').read_bytes()),'syntax_checks':len(syntax)},indent=2))
if __name__=='__main__':main()
