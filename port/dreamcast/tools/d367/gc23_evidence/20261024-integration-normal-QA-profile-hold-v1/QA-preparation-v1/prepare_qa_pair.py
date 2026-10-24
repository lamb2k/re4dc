"""Source-only fresh combined standard H2/KOS twin preparation. No SDK/Make."""
from pathlib import Path
import hashlib,importlib.util,json,shlex,shutil,tempfile,subprocess
HERE=Path(__file__).resolve().parent
ORIGINAL=HERE.parents[1]/'full-link-prep'
spec=importlib.util.spec_from_file_location('source_export_helpers',ORIGINAL/'prepare_full_pair.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
SOURCE=base.SOURCE
DIAGNOSTIC=['DBG_WARP=1','WARP_JUMP=1','PC_SAMPLER=0','TEX_CHECK=1','MCHECK_LEONGC=1','KOS_WATCH=1','KOS_SQUEEZE=1','W11_FIXTURE=1','QA_MENU=0','WORLD_METER=0','KOS_CACHE_P2_DIAG=0','KOS_SQUEEZE_BYTES=0','KOS_SQUEEZE_FRAG=0']
def verify(rows):
 for n,r in rows.items():
  q=Path(n);assert q.stat().st_size==r['bytes'] and base.sha(q)==r['sha256'],n

def main():
 assert base.git(base.TREE,'rev-parse','HEAD').strip()==SOURCE
 assert not base.git(base.TREE,'status','--porcelain').strip()
 old=json.loads((ORIGINAL/'PREPARATION.json').read_text());verify(old['input_pins'])
 full=Path(old['root']);receipt=full/'continuation-v1/receipt.json';done=json.loads(receipt.read_text());assert done['complete'] and done['source']==SOURCE
 frozen={str(q):dict(bytes=q.stat().st_size,sha256=base.sha(q)) for q in sorted(full.rglob('*')) if q.is_file() and not q.is_symlink()}
 args=shlex.split((base.PROFILE/'candidate.txt').read_text());assert all('=' in x for x in args)
 assert base.git(base.SUBMODULE,'rev-parse','HEAD').strip()==base.SUBCOMMIT and not base.git(base.SUBMODULE,'status','--porcelain').strip()
 root=Path(tempfile.mkdtemp(prefix='gc-motion24-qa-memory-',dir='/dev/shm'))
 source=root/'off/source';base.export(base.TREE,SOURCE,source)
 sub=source/'port/dreamcast/game/third_party/sh4zam';sub.rmdir();base.export(base.SUBMODULE,base.SUBCOMMIT,sub)
 shutil.copytree(source,root/'on/source',symlinks=True)
 manifest={str(q.relative_to(source)):dict(bytes=q.stat().st_size,sha256=base.sha(q)) for q in sorted(source.rglob('*')) if q.is_file()}
 commands={};env={};resolved={}
 for name,on in [('off',False),('on',True)]:
  arm=root/name;flags=args+DIAGNOSTIC+['GC_ASSET_GATE='+str(int(on)),'GC_ASSET_CATALOG_SHA256=0','GC_ASSET_MOTION_UNKNOWN='+str(int(on))]
  commands[name]=['bash',str(arm/'source/port/dreamcast/tools/d367/build-r21.sh'),*flags]
  resolved[name]=dict(x.split('=',1) for x in flags)
  env[name]=dict(ASSETS=str(base.ASSETS),OUT=str(arm/'out'),OBJDIR=str(arm/'out/obj'),JOBS='1',SOURCE_DATE_EPOCH='1760000000',PYTHONDONTWRITEBYTECODE='1',RE4DC_KOS_BASE=str(base.SDK))
 inputs=dict(old['input_pins'])
 for q in [Path(__file__),ORIGINAL/'PREPARATION.json',receipt,Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/memory-qualification-prep/PROPOSAL.json')]:inputs[str(q)]=dict(bytes=q.stat().st_size,sha256=base.sha(q))
 plan=dict(status='PREPARED_NOT_RUN',source=SOURCE,root=str(root),source_manifest=manifest,source_files_per_arm=len(manifest),source_export_bytes_per_arm=base.used(source),commands=commands,environment=env,resolved_expected=resolved,diagnostic_overrides=DIAGNOSTIC,input_pins=inputs,original_normal_pair_manifest=frozen,original_normal_pair_receipt_sha256=base.sha(receipt),normal_programmes={n:dict(raw=done['arms'][n]['raw_sha256'],addresses=done['arms'][n]['addresses']) for n in ('off','on')},expected_overlays=base.OVERLAYS,object_graph=dict(no_reuse=True,OFF_helper='May compile exactly once without either diagnostic macro; must be empty and excluded actual link',ON_helper='Compile once Motion1; link exactly once between gc_asset_audio.o and SDK mtx.o',counts='QA additions dbgwarp_bridge.o and w11_fixture.o must be inventoried from actual link; do not reuse normal448/454 counts blindly'),OFF_identity=dict(status='PENDING_EXACT_SAME_QA_BASELINE',production49a4_is_wrong_profile=True,requirement='Exact same QA flags/source control/SDK/data baseline to be chosen by root. No raw identity claimed before concrete baseline is pinned.'),budget=dict(owned_bytes_cap=2*1024**3,C_admission_bytes=26*1024**3,C_floor_bytes=24*1024**3,RAM_admission_bytes=3*1024**3,RAM_floor_bytes=512*1024**2,per_arm_seconds=1800,jobs=1,shared_slots=1,canonical_tree_lease=str(base.TREE),release_priority=True,normal_pair_is_immutable_not_rebuilt=True,estimated_owned_peak_bytes=1000*1024**2),no_execution=dict(SDK=0,Make_queries=0,compiles=0,links=0,staging=0,guest=0),limits=['Combined standard/KOS diagnostic profile, not the exact normal programme','No configured catalog, positive Motion or complete coverage','Current normal pair and old failed receipts unchanged','No runner execution/root allocation/exception implied'])
 assert all(resolved[n][k]==v for n in ('off','on') for k,v in [x.split('=',1) for x in DIAGNOSTIC])
 assert base.used(root)<plan['budget']['owned_bytes_cap']
 for n in ('off','on'):assert not (root/n/'out').exists()
 verify(inputs);verify(frozen)
 (HERE/'PREPARATION.json').write_text(json.dumps(plan,indent=2)+'\n');(root/'PREPARATION.json').write_text(json.dumps(plan,indent=2)+'\n')
 print(json.dumps(dict(status=plan['status'],root=str(root),source_files_per_arm=len(manifest),source_bytes_per_arm=base.used(source),input_pins=len(inputs),normal_preserved_files=len(frozen),SDK_commands=0,baseline=plan['OFF_identity']['status'],plan_sha256=base.sha(HERE/'PREPARATION.json')),indent=2))
if __name__=='__main__':main()
