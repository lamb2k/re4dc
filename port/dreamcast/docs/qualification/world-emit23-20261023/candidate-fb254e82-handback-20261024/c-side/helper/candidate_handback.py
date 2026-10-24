"""Read-only fb254e82 candidate audit, then explicit metadata-only refresh under RR lock."""
import argparse,datetime,fcntl,hashlib,importlib.util,json,pathlib,re,subprocess,sys,tempfile,zipfile
sys.dont_write_bytecode=True
SOURCE='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2';CYCLE='1023-2350-fb254e82';RAW='49a4173a1792823ff5e275b0681b2c354c4e45140b7078d87c1253f2e926090b'
C=pathlib.Path('/mnt/c/Game Dev/Emulators/RE4DC-RR/cand-fb254e82');W=pathlib.Path('/root/rr/work')/CYCLE;T=pathlib.Path('/root/work/lanes/rr');O=pathlib.Path('/root/probe/lanes/route/out-rrfb254e8rP');Q=pathlib.Path('/root/probe/lanes/route/out-rrfb254e8qrW');BASE=pathlib.Path('/root/work/lanes/stat-bytes23-takeover-scratch/release/manifest.json');PRIOR=pathlib.Path('/root/probe/lanes/route/out-au23ld5c1rP');E=pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast/rr-candidate-handback/fb254e82-20261024');RR=pathlib.Path('/root/rr/bin/rr.sh')
ZIP='qa/RE4DC-QA-TestRR-fb254e82-20261023-GDEMU.zip'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def row(p):return {'size':p.stat().st_size,'sha256':sha(p)}
def read(p):return json.loads(p.read_bytes())
def fresh(p,value):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
def terminal():
 s=subprocess.check_output([str(RR),'status'],text=True);assert 'cycle running: no' in s and 'last good: sha fb254e82' in s
 assert (W/'verdict.txt').read_text().strip()==(W/'qa-verdict.txt').read_text().strip()=='PASS';assert 'sha='+SOURCE in (W/'cycle.env').read_text();return s
class Lease:
 def __enter__(self):self.f=pathlib.Path('/root/rr/rr.lock').open('rb');fcntl.flock(self.f,fcntl.LOCK_EX|fcntl.LOCK_NB);return self
 def __exit__(self,*args):self.f.close()
def knobs(p):return dict(x.split('=',1) for x in p.read_text().splitlines() if re.match(r'^[A-Z0-9_]+=',x))
def iso_module():
 p=T/'port/dreamcast/tools/d367/fullplay/fp_iso.py';s=importlib.util.spec_from_file_location('candidate_iso',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m,p

def inspect():
 status=terminal();assert not E.exists(),'Preserve prior evidence; no rerun overwrite'
 with Lease():
  assert C.is_dir() and O.is_dir();assert subprocess.check_output(['git','-C',str(T),'rev-parse','HEAD'],text=True).strip()==SOURCE
  assert not subprocess.check_output(['git','-C',str(T),'status','--porcelain'],text=True)
  assert (O/'stack.txt').read_text().strip()==SOURCE and not (O/'missing.txt').read_text().strip();assert (W/'image.sha256').read_text().strip()==RAW
  original=read(BASE);expected=read(W/'rel/manifest.json');assert len(original)==len(expected)==1712
  overlays=sorted(O.glob('*.ovl'));assert len(overlays)==14;program={'1ST_READ.BIN'}|{'dc/'+p.name for p in overlays}
  assert {k for k in set(original)|set(expected) if original.get(k)!=expected.get(k)}<=program and not set(original)^set(expected)
  for p in overlays:assert expected['dc/'+p.name]==row(p)==row(PRIOR/p.name)
  iso,reader=iso_module();tr=iso.Track(C/'gdemu/track03.bin',45000);got={};rawmain=None
  try:
   for n,extent,size in iso.files(tr):
    n=n.lstrip('/');assert n not in got;h=hashlib.sha256();left=size;at=extent
    while left:
     b=tr.read_bytes(at,min(left,1048576));assert b;h.update(b);left-=len(b);at+=len(b)//2048
    got[n]={'size':size,'sha256':h.hexdigest()}
    if n=='1ST_READ.BIN':rawmain=tr.read_bytes(extent,size)
  finally:tr.f.close()
  assert got==expected and got['1ST_READ.BIN']['sha256']==RAW
  with tempfile.TemporaryDirectory(prefix='rr-fb254-review-',dir='/dev/shm') as tmp:
   for label,p in [('current',O/'re4dc-game.elf'),('baseline',PRIOR/'re4dc-game.elf')]:
    out=pathlib.Path(tmp)/(label+'.bin');subprocess.run(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy','-R','.stack','-O','binary',str(p),str(out)],check=True);assert out.read_bytes()==rawmain and sha(out)==RAW
  # QA unpacked/proxy media has been retired; do not extract ZIP or imply disc readback.
  assert (Q/'stack.txt').read_text().strip()==SOURCE;qa_expected=read(W/'qa/man.json');qa_overlays=sorted(Q.glob('*.ovl'));assert len(qa_overlays)==14
  qa_programme={'disc_readback':False,'retained_ELF':row(Q/'re4dc-game.elf'),'all14_retained_programme_hashes':{p.name:row(p) for p in qa_overlays}}
  for p in qa_overlays:assert row(p)==qa_expected['dc/'+p.name]
  with tempfile.TemporaryDirectory(prefix='rr-qa-programme-review-',dir='/dev/shm') as tmp:
   out=pathlib.Path(tmp)/'qa.bin';subprocess.run(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy','-R','.stack','-O','binary',str(Q/'re4dc-game.elf'),str(out)],check=True);assert row(out)==qa_expected['1ST_READ.BIN'];qa_programme['retained_raw_main']=row(out)
  trackpins={}
  for line in (C/'SHA256SUMS.txt').read_text().splitlines():
   h,n=line.split(maxsplit=1);n=n.lstrip('*');assert n not in trackpins;assert sha(C/n)==h;trackpins[n]=row(C/n)
  assert len(trackpins)==4 and set(trackpins)=={'gdemu/disc.gdi','gdemu/track01.bin','gdemu/track02.raw','gdemu/track03.bin'}
  ziprow=row(C/ZIP)
  with zipfile.ZipFile(C/ZIP) as z:central=[{'name':i.filename,'size':i.file_size,'compressed':i.compress_size,'crc32':format(i.CRC,'08x')} for i in z.infolist()];assert len(central)>0
  modes=[]
  for root in [pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast/rr')/CYCLE,pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast/rr')/(CYCLE+'-qa')]:
   for p in sorted(root.rglob('run-result.json')):
    j=read(p);assert j['status']=='RUN_COMPLETE' and not j['errors'];modes.append({'path':str(p),'sha256':sha(p),'emu':j.get('emu'),'seconds':j.get('seconds'),'elapsed_s':j.get('elapsed_s'),'status':j['status'],'classification':'legacy RR pipeline; not current exact-child55 acceptance'})
  h2=next(r for r in modes if r['path'].endswith('/h2/run-result.json'));assert (h2['emu'],h2['seconds'],h2['elapsed_s'])==('harness',300,167.7)
  profile=knobs(O/'resolved-knobs.txt');assert all(profile[k]=='0' for k in ['SCENERY_DEDUP','SCENERY_SELECT_LEAN2','SCENERY_EMIT_PREFETCH','QA_MENU','PC_SAMPLER'])
  E.mkdir(parents=True);back=E/'original-metadata';back.mkdir()
  for p in C.iterdir():
   if p.is_file():b=p.read_bytes();(back/p.name).write_bytes(b);assert p.read_bytes()==b
  (E/'rr-status-before-inspection.txt').write_text(status)
  fresh(E/'full-readback-manifest.json',got);fresh(E/'original-release-manifest.json',original)
  result={'source':SOURCE,'cycle':CYCLE,'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'candidate':str(C),'rr_terminal_before_inspection':True,'rr_exclusive_lock_held':True,'raw_main_sha256':RAW,'elf':row(O/'re4dc-game.elf'),'all14_overlays':{p.name:row(p) for p in overlays},'same_raw_main_and_all14_as_prior_production_baseline':str(PRIOR),'full_independent_disc_files':1712,'original_release_files':1712,'all1697_nonprogramme_asset_rows_equal_original':True,'only_original_manifest_differences':sorted(k for k in got if got[k]!=original[k]),'tracks':trackpins,'original_sha256sums':row(C/'SHA256SUMS.txt'),'asset_release_manifest':{'path':str(BASE),**row(BASE)},'recipe':{'path':str(W/'recipe.conf'),**row(W/'recipe.conf')},'resolved_profile':{'path':str(O/'resolved-knobs.txt'),**row(O/'resolved-knobs.txt')},'effective_profile':{k:profile[k] for k in ['SCENERY_DEDUP','SCENERY_SELECT_LEAN2','SCENERY_EMIT_PREFETCH','SCENERY_SELECT_ONLY','SCENERY_REPLAY_LEAN','SCENERY_SUBMIT_BATCH','STAT_ROUTINE_BYTES','EM_READ_RETRY','QA_MENU','PC_SAMPLER','KOS_CACHE_P2','R10C_SPAWN_LIVE_GUARD','R117_EFFECT_FAILURE_SAFE']},'qa_zip':{'path':ZIP,**ziprow,'central_directory':central,'extracted_by_reviewer':False,'fresh_QA_asset_readback_claim':False,'retained_QA_programme_hashes_no_disc_readback':qa_programme,'RR_reported_testzip_pass':True},'legacy_RR':{'quick_result':row(W/'result.json'),'qa_verdict':row(W/'qa-verdict.txt'),'runs':modes,'h2':h2,'current_console55_qualification':False},'current_actual_candidate_console55_boot':'PENDING root bounded adapter','physical_full_route_performance_historical_causal_acceptance':False,'previous_candidate':{'path':'cand-d5c1ceab','removed_by_RR_at':'2026-10-23T23:56:56-04:00','fresh_postdelete_inventory_claim':False,'note':'Prior candidate was already removed by watcher; no zero/empty list is treated as proof. Historical source/programme/evidence proofs remain separate.'},'readback_helper':{'path':str(reader),**row(reader)},'media_fingerprints':{n:[(C/n).stat().st_size,(C/n).stat().st_mtime_ns] for n in [*trackpins,ZIP]},'original_metadata_fingerprints':{p.name:row(p) for p in back.iterdir()}}
  fresh(E/'INSPECTION.json',result)
  print(json.dumps({'status':'PASS_READBACK','files':1712,'raw':RAW,'legacy_runs':len(modes),'evidence':str(E),'inspection_sha256':sha(E/'INSPECTION.json')}))

def refresh():
 status=terminal()
 with Lease():
  r=read(E/'INSPECTION.json');assert r['source']==SOURCE and r['raw_main_sha256']==RAW
  for n,fp in r['media_fingerprints'].items():assert [(C/n).stat().st_size,(C/n).stat().st_mtime_ns]==fp,n
  for n,pin in r['original_metadata_fingerprints'].items():assert row(C/n)==pin,n
  assert row(C/'SHA256SUMS.txt')==r['original_sha256sums']
  title='PRIVATE CURRENT CANDIDATE — fb254e82 (metadata handback, not release acceptance)\n'
  readme=title+'''\nSource fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2; RR cycle 1023-2350-fb254e82 quick PASS and QA PASS. The actual production main SHA256 is 49a4173a1792823ff5e275b0681b2c354c4e45140b7078d87c1253f2e926090b. Fresh independent actual-disc readback matches all 1,712 file rows, main/all 14 and the unchanged 1,697 non-programme original asset rows. Raw main/all 14 equal the retained qualified production baseline. Recipe/assets remain unchanged. Offline dedup and both experimental world switches remain OFF.\n\nRR results are LEGACY RR PIPELINE EVIDENCE. H2 used emu=harness, requested 300 seconds, elapsed 167.7 seconds; census/KOS/QAboot/QAwarp also use legacy harness runs. Two GDEMU seed runs report console mode with 60-second requests and 59.0/58.8-second elapsed; they do not meet the current exact 55-second qualification contract. No RR PASS here is presented as current bounded-console, hardware, speed, full-route or historical dam-crash causal acceptance. Fresh actual-candidate console55 boot remains PENDING for root's bounded adapter. Separate source/profile identity-bound console gates are prior evidence, not a new candidate run.\n\nThe original generated Test22 README is backed up outside this candidate. Its historical fixed-crash wording is not a fresh candidate-specific finding. Ordinary manual boot/VMU/boat/dam/church/village/Mendez routes remain pending. No physical two-minute Arena challenge or QA Mendez pass is claimed.\n\nThe bundled qa/RE4DC-QA-TestRR-fb254e82-20261023-GDEMU.zip is retained unchanged. This handback hashed it and inspected its central directory, without extraction; retained QA raw main/all 14 compiler outputs were independently verified, but unpacked QA media is no longer retained. RR reported its ZIP integrity and QA checks, which remain legacy evidence. This handback does not claim fresh full-QA asset readback or current console QA execution.\n\nUse STEPS.txt for pending manual checks and IDENTITY.json for exact source/programme/assets/media and evidence limits. SHA256SUMS.txt remains the original four-disc-file list; QUALIFICATION-SHA256SUMS.txt additionally pins this metadata and the unchanged QA ZIP. No disc/asset/recipe bytes, ZIP, SD card or publication was changed.\n'''
  steps='''Pending manual observations for the CURRENT fb254e82 candidate\n\nNo step below was executed by this metadata handback. Root's fresh actual-disc console55 boot is pending. Use the normal production gdemu/disc.gdi for ordinary play; keep the separate QA ZIP unchanged unless separately asked to use it. No SD-copy or extraction operation is performed here.\n\n1. Boot normally to the title/menu and start a New Game. Record build/source and console/video/controller/VMU configuration. Do not count initialization alone as playable-route acceptance.\n2. At an ordinary save point, test VMU save, load, reset and resume. Record any failed write, changed state, missing audio or load problem; a legacy harness PASS is not a physical VMU result.\n3. Follow the ordinary opening village and bell progression, preserving fights, triggers and doors. Continue the normal route toward lake/boat; test boat entry, traversal and exit where reached.\n4. Follow the dam path to the first axe villager encounter. If it never triggers, report exact position/progression rather than PASS. Historical physical-crash cause/fix is not certified by this handback.\n5. Reach the church by normal progression. Record the starting puzzle state, solve using the normal controls and confirm the solved/disarmed result and ordinary exit. Source diagnostic placement fixtures are not a substitute for this manual traversal.\n6. Continue toward Mendez; record both deaths, movies, exit/window and the next room where actually reached. No QA Mendez or full-route physical acceptance is supplied in this candidate.\n7. Report freezes, read failures, missing geometry/textures, audio/state changes and reproducible view/steps. Speed/performance and any two-minute physical Arena challenge require separately matched profiles and observations; do not infer them from the legacy 300-second H2 harness request.\n\nThe QA ZIP contains a QA-menu build of the same source, with ordinary 33 presets. Its legacy boot/warp/seed results are recorded separately. Teleport/diagnostic fixtures do not prove manual route progression or hardware acceptance.\n'''
  identity={'status':'PRIVATE_CURRENT_CANDIDATE_METADATA_REVIEWED_CONSOLE55_PENDING','inspection':{'path':str(E/'INSPECTION.json'),**row(E/'INSPECTION.json')},'source':SOURCE,'cycle':CYCLE,'programme':{'raw_main':r['raw_main_sha256'],'elf':r['elf'],'overlays':r['all14_overlays'],'baseline_equal':r['same_raw_main_and_all14_as_prior_production_baseline']},'tracks':r['tracks'],'assets':{'full1712_independently_read':True,'nonprogramme1697_unchanged':True,'original_release_manifest':r['asset_release_manifest'],'readback_manifest':row(E/'full-readback-manifest.json')},'recipe':r['recipe'],'profile':r['resolved_profile'],'effective_profile':r['effective_profile'],'legacy_RR':r['legacy_RR'],'qa_zip':r['qa_zip'],'actual_candidate_console55_boot':'PENDING','physical_full_route_performance_historical_causal_acceptance':False,'previous_candidate':r['previous_candidate'],'metadata_only':True,'production_recipe_or_media_changed':False,'QA_ZIP_extracted':False,'SD_or_publication_performed':False}
  draft=E/'metadata-draft';draft.mkdir(exist_ok=False)
  (draft/'README.txt').write_text(readme);(draft/'STEPS.txt').write_text(steps);fresh(draft/'IDENTITY.json',identity)
  entries={'README.txt':row(draft/'README.txt'),'STEPS.txt':row(draft/'STEPS.txt'),'IDENTITY.json':row(draft/'IDENTITY.json'),'SHA256SUMS.txt':r['original_sha256sums'],**r['tracks'],ZIP:{'size':r['qa_zip']['size'],'sha256':r['qa_zip']['sha256']}}
  (draft/'QUALIFICATION-SHA256SUMS.txt').write_text(''.join(pin['sha256']+'  '+n+'\n' for n,pin in sorted(entries.items())))
  for n in ['README.txt','STEPS.txt','IDENTITY.json','QUALIFICATION-SHA256SUMS.txt']:(C/n).write_bytes((draft/n).read_bytes());assert (C/n).read_bytes()==(draft/n).read_bytes()
  assert (C/'SHA256SUMS.txt').read_bytes()==(E/'original-metadata/SHA256SUMS.txt').read_bytes()
  for n,fp in r['media_fingerprints'].items():assert [(C/n).stat().st_size,(C/n).stat().st_mtime_ns]==fp,n
  (E/'rr-status-before-metadata.txt').write_text(status)
  receipt={'source':SOURCE,'cycle':CYCLE,'metadata_refreshed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'RR_terminal_before_edit':True,'exclusive_RR_lock_during_edit':True,'inspection_sha256':sha(E/'INSPECTION.json'),'original_metadata_backed_up':str(E/'original-metadata'),'unchanged_original_four_track_sums':True,'media_ZIP_fingerprints_unchanged':True,'metadata_files':{n:row(C/n) for n in ['README.txt','STEPS.txt','IDENTITY.json','QUALIFICATION-SHA256SUMS.txt']},'helper_sha256':sha(pathlib.Path(__file__)),'source_programme_assets_tracks_ZIP_changed':False,'legacy_current_console55_distinction_explicit':True,'new_guest_build_or_cleanup':False,'current_actual_candidate_console55_boot':'PENDING'}
  fresh(E/'HANDBACK.json',receipt);(E/'HANDBACK.md').write_text('''Current fb254e82 candidate metadata handback complete. Actual production disc1712files and programme/all14 independently read; original1697asset rows preserved. RRterminal/lock checked before edits. Originalmetadata backed up outsidecandidate; four originaltrackSHA list unchanged. QA ZIP hashed/centraldirectory inspected, notextracted. All RRresults remainLEGACY: H2harness300s/167.7s; two console60sseed runs are notcurrent55sacceptance. Fresh actualcandidate console55boot, physical/fullroute/performance/historicalcausal acceptance remainPENDING. No oldd5c postdeleteinventory claimed; watcher removed it23:56:56. No SDK/guest/SD/ZIPextraction/media/asset/recipe/cleanup operation. SeeHANDBACK.json andINSPECTION.json.\n''')
  print(json.dumps({'status':'METADATA_REFRESHED_ONLY','handback':str(E/'HANDBACK.json'),'handback_sha256':sha(E/'HANDBACK.json'),'console55':'PENDING'}))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['inspect','refresh-metadata']);a=ap.parse_args();inspect() if a.mode=='inspect' else refresh()
