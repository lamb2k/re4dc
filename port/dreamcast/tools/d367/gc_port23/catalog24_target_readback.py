from pathlib import Path
import hashlib,json,subprocess,shlex
ram=Path('/dev/shm/gc-catalog24-a132-avwm2i7d');r=json.loads((ram/'report.json').read_text());assert r['complete'] and len(r['objects'])==16
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
units=['coarse_actor.cpp','platform/native_actor_fast.cpp','platform/native_ui.cpp','platform/native_model.cpp','model_bridge.cpp','ui_bridge.cpp','platform/audio_aica.cpp','platform/native_movie.cpp','platform/native_movie_stream.c','../../../src/game/model.cpp','../../../src/game/read.cpp','../../../src/game/dvd.cpp','platform/native_static.cpp','platform/room_file.c']
old=Path('/root/work/lanes/gc-port23');cwd=old/'port/dreamcast/game';obj=Path('/root/work/lanes/gc-port23-full-target2-scratch/off/out/obj');diff=[(old/n).resolve() for n in r['runtime_diff']];retained=[]
for u in units:
 name=u.replace('../../../','');d=obj/Path(name).with_suffix('.d')
 if not d.exists():
  assert u=='platform/room_file.c'
  source=(cwd/u).resolve();retained.append({'unit':u,'scope':'Actual C full compile emits no .d; unchanged source/direct includes only, not transitive dependency readback','source_sha256':sha(source),'direct_includes':[l for l in source.read_text().splitlines() if l.startswith('#include')],'source_is_changed_runtime':source in diff});assert source not in diff;continue
 text=d.read_text();first=[]
 for line in text.splitlines():
  first.append(line)
  if not line.rstrip().endswith('\\'):break
 deps=shlex.split('\n'.join(first).split(':',1)[1].replace('\\\n',' '));paths=[(cwd/n).resolve() for n in deps];assert not set(paths).intersection(diff),u
 inventory={str(p):sha(p) for p in paths}
 retained.append({'unit':u,'historical_dep_file':str(d),'dep_sha256':sha(d),'dependency_count':len(paths),'dependency_inventory_sha256':hashlib.sha256(json.dumps(inventory,sort_keys=True).encode()).hexdigest(),'changed_runtime_dependency_intersection':[]})
(ram/'retained14-readback.json').write_text(json.dumps({'scope':'Historical OFF13 available full dep inventories plus unchanged room_file.C direct includes (no .d emitted). Runtime diff only3 helpers. Not a fresh14 compile/link proof or a retroactive before-build dependency hash claim.','units':retained},indent=2)+'\n')
frames={}
for label in ['parent','current']:
 for unit in ['gc_asset_gate','gc_asset_disc']:
  for arm in ['on-catalog0','on-synthetic-pin']:
   f=ram/(label+'-'+unit+'-'+arm+'.su');rows={}
   for line in f.read_text().splitlines():
    fields=line.split('\t')
    if len(fields)!=3:continue
    signature=fields[0].split(':',3)[-1];name=signature.split('(',1)[0].rsplit('::',1)[-1];rows[name]=int(fields[1])
   frames[label+' '+unit+' '+arm]=rows
summary={'source':r['source'],'parent':r['parent'],'scope':'16 fresh selected SH4 arms only; no link/stage/guest/fullchain/heap/catalog-file/I001 acceptance. All off helpers zero sections/no symbols, parent/current absent/zero stripped identity. Actual current full-normal commands and fixed epoch used.','target_profile':r['profile'],'sdk_sha256':r['pins']['/root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a'],'all16_complete':True,'off_identity':r['off_identity'],'selected_delta':{arm:{n:sum(v[n] for k,v in r['deltas'].items() if k.endswith(arm)) for n in ['text','data','bss']} for arm in ['on-catalog0','on-synthetic-pin']},'unit_deltas':r['deltas'],'self_frames':frames,'known_chains':r['stack_scope'],'provider_counts':{a:{'distinct_imports':len(c['imports']),'missing':c['missing'],'atomic_imports':[n for n in c['imports'] if 'atomic' in n]} for a,c in r['provider_closure'].items()},'runtime_diff':r['runtime_diff'],'retained14_proof':'Exact old full programme/OFF14 proof is historical plus unchanged runtime source diff and65fullinputpins. Readback checks13 available actualOFF dep inventories exclude changed helpers; room_file.C emits no .d and only its unchanged source/direct includes are checked here. No new fullprogramme or14 matrix.','owned_output_bytes':r['owned_output_bytes'],'initial_attempt':'Before compilation, git threaded lstat exceeded256MiB VM. Incomplete obkg9mte preserved; rerun git CLI index.threads1/core.preloadIndexfalse; same compiler/profile.','source_clean_after':not subprocess.check_output(['git','-c','index.threads=1','-c','core.preloadIndex=false','-C','/root/work/lanes/gc-catalog24','status','--porcelain'])}
(ram/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
out=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-catalog24-20261024/target-a132-current');out.mkdir(parents=True,exist_ok=True)
for p in ram.iterdir():
 if p.is_file() and p.suffix in ['.json','.su','.txt','.log','.d']:(out/p.name).write_bytes(p.read_bytes())
failed=Path('/dev/shm/gc-catalog24-a132-obkg9mte');failure=json.loads((failed/'report.json').read_text());assert not failure['objects'] and not list(failed.glob('*.o'))
(out/'initial-harness-attempt.json').write_text(json.dumps({'source':r['source'],'no_compiler_arms_started':True,'scope':'Harness resource failure before first compilation; not a source/target failure','error':'fatal: unable to create threaded lstat: Resource temporarily unavailable','fix':'git CLI index.threads1/preloadIndexfalse; compiler/profile unchanged','report_sha256':sha(failed/'report.json'),'ram':str(failed)},indent=2)+'\n')
(out/'initial-harness-report.json').write_bytes((failed/'report.json').read_bytes())
manifest={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in out.iterdir() if p.is_file() and p.name!='SHA256-MANIFEST.json'}
(out/'SHA256-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'metadata_files':len(manifest),'metadata_bytes':sum(x['bytes'] for x in manifest.values()),'manifest_sha256':sha(out/'SHA256-MANIFEST.json'),'delta':summary['selected_delta'],'retained14':len(retained)},indent=2))
