"""Read-only exact frozen-source/hash receipt for the bounded fd lifetime audit."""
from pathlib import Path
import datetime,hashlib,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=Path('/root/work/lanes/gc-motion24')
SOURCE='aab201ceac0e18107f64a3212398afe916793327'
def digest(data):return hashlib.sha256(data).hexdigest()
def row(p):
 with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
 return {'size':p.stat().st_size,'sha256':h}
def fresh(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
assert subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()==SOURCE
status=subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True);assert not status
names=['port/dreamcast/game/platform/'+n for n in ['gc_asset_disc.cpp','gc_asset_gate.cpp','gc_asset_audio.cpp','gc_asset_motion_unknown.cpp','gc_asset_members.cpp','gc_asset_payloads.cpp','native_ui.cpp','native_movie.cpp','native_movie_stream.c','native_motion.cpp','native_static.cpp','room_file.c','dvd.cpp','include/gc_asset_hand_source.inc','include/gc_asset_actor_compiled.inc','include/gc_asset_lifecycle.h','include/texpack_index.inc']]
names+=['port/dreamcast/game/'+n for n in ['ui_bridge.cpp','motion_bridge.cpp','coarse_actor.cpp','coarse_actor_leon_hands.inc','coarse_actor_pl08_pack.inc','coarse_actor_registry_pack.inc','gc_asset_gate.mk','Makefile','game30.mk','crowd.mk']]
names+=['src/game/game.cpp','port/dreamcast/room/texture_package.cpp','port/dreamcast/tools/d367/build-r21.sh']
files={}
for name in names:
 data=(ROOT/name).read_bytes();frozen=subprocess.check_output(['git','-C',str(ROOT),'show',SOURCE+':'+name]);assert data==frozen,name
 files[name]={'working_bytes':row(ROOT/name),'git_blob_sha256':digest(frozen),'exact_git_source':True}
terminal=Path('/dev/shm/gc-motion24-kos-census-v1-2g7teq3g/root-continuation-v1/receipt.json')
assert row(terminal)['sha256']=='584ecc6dd664e35f8ba044eeaecb7d0a4cd4066b2cbe2d073a93151b742150e0'
t=json.loads(terminal.read_text());resolved={}
keys=['AICA_AUDIO','AICA_STREAMS','DVD_FDCACHE','COARSE_LEON','ACTOR_TRANSACTION','LEON_HAND_PACK','LEON_HAND_RETAIN','GC_ASSET_GATE','GC_ASSET_MOTION_UNKNOWN','GC_ASSET_CATALOG_SHA256','MOTION_FAST_READ','TEX_PACK_WINDOW','KOS_CENSUS']
for arm in ['off','on']:
 p=terminal.parents[1]/arm/'out/resolved-knobs.txt';assert row(p)['sha256']==t['arms'][arm]['resolved_sha256']
 pairs=dict(line.split('=',1) for line in p.read_text().splitlines() if '=' in line)
 resolved[arm]={'path':str(p),'identity':row(p),'selected_exact_values':{k:pairs.get(k,'UNRECORDED') for k in keys}}
sdk=Path('/root/work/kos-re4dc-d367')
sdk_paths=['include/kos/fs.h','kernel/fs/fs.c','kernel/arch/dreamcast/fs/fs_iso9660.c']
root_review=HERE.parent/'kos-census-media-root-review-v1'
references={}
for n in ['ROOT-CALLER-PAIR-RESULT.json','caller-off-PROCESS.json','caller-on-PROCESS.json','ROOT-STAGE-PAIR-RESULT.json']:
 p=root_review/n
 if p.exists():references[str(p)]=row(p)
result={'status':'SOURCE_AUDIT_COMPLETE_NO_CONFIRMED_PERSISTENT_DIAGNOSTIC_FD','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'source':SOURCE,'clean_frozen_tree_before_and_after':not subprocess.check_output(['git','-C',str(ROOT),'status','--porcelain'],text=True),
 'source_files':files,'terminal':{'path':str(terminal),'identity':row(terminal)},'resolved':resolved,
 'SDK_API_source_inspection_only':{'root':str(sdk),'git_HEAD':subprocess.check_output(['git','-C',str(sdk),'rev-parse','HEAD'],text=True).strip(),'files':{n:row(sdk/n) for n in sdk_paths},'historical_object_identity_not_inferred':True},
 'existing_root_metadata_hash_references_only':references,'findings':{'GC_direct_open_sites':5,'pin0_catalog_opens':0,'motion_unknown_file_opens':0,'confirmed_audio_diagnostic_extra_open_path':True,'confirmed_extra_permanently_retained_fd':False,'sampled_extra_fd_owner':'UNKNOWN','allocator_coverage':'UNKNOWN','original_memory_cause':'UNKNOWN'},
 'reported_not_independently_recomputed_guest_difference':{'iso_open_requested_delta':352,'fs_hnd_open_requested_delta':16,'scope':'Root-reported enter census only; separate ledger readback ongoing'},
 'no_runtime_changes_or_handle_closes_or_build_or_stage_or_guest':True}
fresh(HERE/'READBACK.json',result)
fresh(HERE/'SEAL.json',{'source':SOURCE,'status':result['status'],'members':{p.name:row(p) for p in sorted(HERE.iterdir()) if p.is_file()},'no_runtime_acceptance':True})
print(json.dumps({'seal':row(HERE/'SEAL.json'),'readback':row(HERE/'READBACK.json'),'resolved':resolved},indent=2))
