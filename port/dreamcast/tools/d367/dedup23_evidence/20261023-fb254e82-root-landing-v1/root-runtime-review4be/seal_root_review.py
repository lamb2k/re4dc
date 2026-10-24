from pathlib import Path
import hashlib,json,subprocess
T=Path('/root/work/lanes/dedup-offline23-current-d5c');F=Path('/root/probe/dedup-prefetch-context23')
L=Path('/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23/root-review4be');E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
sha=lambda b:hashlib.sha256(b).hexdigest()
parent='4be08e0110592510e3630c01fa9f49b3ac2fed3d';fix='0d30bd83098af2bcd5e9ca2197ffd4cd926e73c4'
for tree,head in [(T,parent),(F,fix)]:
 assert subprocess.check_output(['git','-C',str(tree),'rev-parse','HEAD'],text=True).strip()==head
 assert not subprocess.check_output(['git','-C',str(tree),'status','--porcelain'])
paths=['port/dreamcast/game/platform/native_static.cpp','port/dreamcast/game/scenery19.mk','port/dreamcast/room/instanced_mesh.hpp','port/dreamcast/tools/d367/dedup_offline23/offline_dedup.py','port/dreamcast/tools/d367/dedup_offline23/strip_share.py']
source={p:dict(bytes=(T/p).stat().st_size,sha256=sha((T/p).read_bytes())) for p in paths}
receipts={};loaded={}
for n in ['host-binding.json','host-composition.json','current-off-identity.json','reproduction-identity.json','current4be-matched-h2-r1.json','kos-48k-gates-r1.json','gdemu10-gates-r1.json','frozen-look-comparison-explicit-r4.json']:
 b=(E/n).read_bytes();j=json.loads(b);assert j['source']==parent
 receipts[n]=dict(path=str(E/n),sha256=sha(b),status=j.get('status',j.get('kind')),limits=j.get('limits',j.get('scope')));loaded[n]=j
h=loaded['host-binding.json'];assert h['source_sha256']==sha((T/paths[0]).read_text().encode());assert h['reader_sha256']==sha((T/paths[2]).read_bytes())
for p,d in loaded['host-composition.json']['source_sha256'].items():assert sha((T/p).read_bytes())==d
ident=loaded['current-off-identity.json'];assert ident['resolved_differences']=={}
programmes=list(ident['programmes'].values());assert len(programmes)==2
assert programmes[0]['raw_sha256']==programmes[1]['raw_sha256'] and programmes[0]['overlays']==programmes[1]['overlays'] and len(programmes[0]['overlays'])==14
host=Path('/dev/shm/dedup-prefetch-context23-controls-v1/prefetch-context-controls.json');hb=host.read_bytes();j=json.loads(hb)
assert j['comparisons']==96 and j['prefetch0_changed_region_preprocessed_identical'] and all(x['returncode']!=0 for x in j['mutants'].values())
assert j['native_source_sha256']==sha((F/paths[0]).read_text().encode())
(L/'FIX-HOST-CONTROLS.json').write_bytes(hb)
fixpaths=subprocess.check_output(['git','-C',str(F),'diff-tree','--no-commit-id','--name-only','-r','HEAD'],text=True).splitlines();fixed={}
for p in fixpaths:
 b=subprocess.check_output(['git','-C',str(F),'show','HEAD:'+p]);working=(F/p).read_bytes()
 assert working.replace(b'\r\n',b'\n')==b
 fixed[p]=dict(git_blob_sha256=sha(b),working_sha256=sha(working))
note=L/'ROOT-RUNTIME-REVIEW.md';r=dict(schema='ROOT_DEDUP_RUNTIME_REVIEW_4BE_V1',
 status='CLEAR_SOURCE_PREFETCH0_WITH_CONFIRMED_PREFETCH1_DEFECT_REPAIRED_SUCCESSOR',baseline='d5c1ceab9e06461462669b3ce1d28a379747a74a',reviewed_source=parent,source=source,qualification_receipts=receipts,
 confirmed_finding=dict(condition='SCENERY_DEDUP3+SCENERY_EMIT_PREFETCH1',counterexample_receipt_sha256=sha((L/'PREFETCH-CONTROL.json').read_bytes()),failed_cases=[100,101,102]),
 repair=dict(source=fix,parent=parent,branch='wip/dedup-prefetch-context23-20261023',files=fixed,host_receipt_sha256=sha(hb),comparisons=96,context_configurations=8,mutants_detected=2,
 root_independent_rerun='/dev/shm/root-dedup-prefetch-review-0d30; parent reported96PASS/two mutants; reviewer author did not certify own repair independently'),
 bounds_findings=dict(offline_groups_base_c='Safe after adopt strip/index/repeat validation',unsigned_repeat_subtraction='Early rejection before any wrapped value use',cross_part_alias='Existing part_pool covers plain and indexed ranges',empty_group_prev='No consumption; selectors skip before span use'),
 remaining_gates=['Normal integrated OFF main/all14 identity','Final independent QA media review','Any future DEDUP3+PREFETCH1 target/guest/pixel qualification'],
 note=dict(path=str(note),bytes=note.stat().st_size,sha256=sha(note.read_bytes())),no_target_build_or_guest=True)
o=L/'ROOT-RUNTIME-REVIEW.json';o.write_text(json.dumps(r,indent=2)+'\n');print('note',r['note']['sha256']);print('receipt',sha(o.read_bytes()));print('bytes',sum(p.stat().st_size for p in L.iterdir() if p.is_file()))
