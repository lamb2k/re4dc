from pathlib import Path
import hashlib,json,math,shlex,struct,sys
T=Path('/root/probe/codex-texture-rect21');sys.path.insert(0,str(T/'port/dreamcast/tools/d367/fullplay'));import fp_iso
import argparse
ap=argparse.ArgumentParser(description='Read-only standalone image qualification plan; creates metadata only.');ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();E=a.out;assert not E.exists();E.mkdir(parents=True)
S=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/feedback21-runtime-20261021/qa-aafc10f3-input/gdemu');B=Path('/root/probe/texture-rect21-program-pair-20261021-01/out-on');D=Path('/root/re4data/private/texture-rect21-current948-scoped17-20261021');F=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture-rect21-20261021/native-bindings-01/inputs');BASE=Path('/root/re4data/private/mipmap21-world-efm-masked-vq-v2-20261021/tex.pak')
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def emit(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
assert sha(B/'program.bin')=='a58579b87da0c45267cb93efe29feea2438da9ddab62d0fe31c47a1c6ff32c71'
assert sha(B/'re4dc-game.elf')=='e08c9abc8f6bb44bb2a94642fc9a2e664d22039659cea7fcce311cb9989d7433'
assert sha(D/'tex.pak')=='bbcef25f0090fa4004e03331a33c84f8f89fd3582704e4a08945a8f6a15d5026'
assert sha(BASE)=='e19cfc464e789e97ca96864adfc2a4cd44443a9f4775bebd842c3e184a65559b'
selected=json.loads((B/'receipt.json').read_text());assert selected['source']=='004cf224674fa60cf08dc10e641c723de238a0fd'
for row in selected['files']:
 path=Path(row['path']);assert path.is_file() and sha(path)==row['sha256'] and path.stat().st_size==row['bytes']
track=S/'track03.bin';assert sha(track)=='5ae451a0cb1e5c6e6db9b68d27335a09a00d27abd83e9c838c66ef2f8b69cfa8';tr=fp_iso.Track(track,45000)
def filehash(e,n):
 h=hashlib.sha256();left=n;lba=e
 while left:
  blocks=min(256,(left+2047)//2048);tr.f.seek((lba-tr.base)*tr.ss+16);raw=tr.f.read(blocks*tr.ss);assert len(raw)==blocks*tr.ss
  buf=b''.join(raw[i*tr.ss:i*tr.ss+2048] for i in range(blocks));chunk=buf[:left];h.update(chunk);left-=len(chunk);lba+=blocks
 return h.hexdigest()
roots=fp_iso.volume_roots(tr);tree={};files={};directories={}
for root,joliet in zip(roots,(False,True)):
 if root is None: continue
 rows=[]
 for p,e,n,isdir,dlba,off in fp_iso.walk(tr,root,joliet):
  record=tr.read(dlba+off//2048)[off%2048:];record=record[:record[0]]
  rows.append(dict(path=p,extent=e,bytes=n,is_directory=isdir,record_lba=dlba,record_offset=off,record_hex=record.hex()))
  if not joliet:
   if isdir:directories[p]=dict(extent=e,bytes=n,sha256=filehash(e,n))
   else:files[p]=dict(extent=e,bytes=n,sha256=filehash(e,n))
 tree['joliet' if joliet else 'iso9660_rockridge']=rows
assert len(files)==1743
expected=json.loads(Path('/mnt/c/Flycast-Evidence/re4-dreamcast/texture21-benchmark-20261021/retained-qa-staged01.json').read_text())['files']
assert set(p.lstrip('/') for p in files)==set(expected)
for p,r in files.items():assert r['sha256']==expected[p.lstrip('/')]['sha256'] and r['bytes']==expected[p.lstrip('/')]['size'],p
mapping={'/1ST_READ.BIN':B/'program.bin','/dc/tex.pak':D/'tex.pak'}
for p in files:
 if p.lower().endswith('.ovl'):mapping[p]=B/Path(p).name
for room in ('r100','r103'):mapping['/dc/native/'+room+'/ps2-world.r4pw']=D/'dc/native'/room/'ps2-world.r4pw'
assert len(mapping)==18 and sum(p.endswith('.ovl') for p in mapping)==14
for room in ('r100','r103'):
 p='/dc/native/'+room+'/ps2-world.r4pw';assert sha(F/p.lstrip('/'))==files[p]['sha256']
# Compare each tree by directory-record aliases, not guessed case-folded primary names.
iso_by_extent={(r['extent'],r['bytes']):r['path'] for r in tree['iso9660_rockridge'] if not r['is_directory']}
for key,rows in tree.items():
 for r in rows:
  if not r['is_directory']:assert (r['extent'],r['bytes']) in iso_by_extent
last_file_end=max(r['extent']+(r['bytes']+2047)//2048 for r in files.values())
assert files['/1ST_READ.BIN']['extent']==547365 and last_file_end==549000
assert all(r['extent']+(r['bytes']+2047)//2048<=549000 for r in directories.values())
tail=tr.read(549000,150);assert len(tail)==307200 and not any(tail)
base_cooked=tr.count*2048;arms={}
for arm in ('base948','scoped17'):
 sources=dict(mapping)
 if arm=='base948':
  sources['/dc/tex.pak']=BASE
  for room in ('r100','r103'):sources['/dc/native/'+room+'/ps2-world.r4pw']=F/'dc/native'/room/'ps2-world.r4pw'
 pos=base_cooked;changes={};unchanged={}
 for p,r in files.items():
  if p not in sources:unchanged[p]=r;continue
  src=sources[p];size=src.stat().st_size;digest=sha(src);alloc=(r['bytes']+2047)//2048*2048
  if size<=alloc:target=r['extent'];padding=alloc-size
  elif p=='/1ST_READ.BIN' and size<=alloc+len(tail):
   target=r['extent'];padding=(-size)%2048
  else:raise AssertionError('Frozen layout cannot fit selected file without moving an unrelated extent: '+p)
  records=[]
  for tree_name,rows in tree.items():
   for row in rows:
    if not row['is_directory'] and (row['extent'],row['bytes'])==(r['extent'],r['bytes']):records.append(dict(tree=tree_name,path=row['path'],record_lba=row['record_lba'],record_offset=row['record_offset']))
  assert {v['tree'] for v in records}==set(tree)
  changes[p]=dict(before=r,source_path=str(src),after_bytes=size,after_sha256=digest,after_extent=target,padding_bytes=padding,relocated=target!=r['extent'],payload_changes=digest!=r['sha256'] or size!=r['bytes'],directory_records=records)
 tracks=[dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in (S/'track01.bin',S/'track02.raw',S/'disc.gdi')]
 output=pos+sum(r['bytes'] for r in tracks)+128 # GDI content changes only sector width/filename, conservative
 arms[arm]=dict(selected_paths=changes,preserved_files=unchanged,preserved_count=len(unchanged),payload_changed_paths=[p for p,r in changes.items() if r['payload_changes']],cooked_track_bytes=pos,source_cooked_bytes=base_cooked,append_bytes=pos-base_cooked,other_track_identities=tracks,stage_byte_bound=output)
 emit(E/(arm+'-file-plan.json'),arms[arm])
# Descriptor edits required by appended absolute LBAs. No timestamp or path-table edit.
desc=[];lba=45016
while True:
 d=tr.read(lba);typ=d[0]
 if typ in (1,2):
  oldle=struct.unpack_from('<I',d,80)[0];oldbe=struct.unpack_from('>I',d,84)[0];assert oldle==oldbe
  assert oldle==tr.count-150,(oldle,tr.count) # baseline has150 trailing sectors beyond declared volume
  desc.append(dict(lba=lba,type=typ,sha256=hashlib.sha256(d).hexdigest(),old_volume_space_blocks=oldle,baseline_trailing_sectors=tr.count-oldle,absolute_count=False,field_offset=80,field_bytes=8,new_counts={a:max(r['after_extent']+(r['after_bytes']+2047)//2048 for r in v['selected_paths'].values())-45000 for a,v in arms.items()}))
 if typ==255:break
 lba+=1
emit(E/'directory-records.json',tree);emit(E/'baseline-file-identities.json',dict(files=files,directories=directories));emit(E/'volume-descriptor-plan.json',desc)
trackids=[dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(S.iterdir()) if p.is_file()]
pair=sum(v['stage_byte_bound'] for v in arms.values());assert pair<=int(2.3*1024**3)
report=dict(schema='rect21-standalone-image-plan-1',runtime_source='004cf224674fa60cf08dc10e641c723de238a0fd',program_sha256=sha(B/'program.bin'),elf_sha256=sha(B/'re4dc-game.elf'),baseline_source='b21116ec0cf2c984e9f49769a148373553bff00d',baseline_gdi_root=str(S),baseline_tracks=trackids,baseline_files_verified=1743,iso_tree_complete=True,joliet_present=roots[1] is not None,joliet_contract='Update all records if present; this baseline has no Joliet SVD/tree. Do not invent a new tree.',selected_allowlist_count=18,selected_allowlist=list(mapping),preserved_file_count=1725,descriptors=desc,standalone_scoped_stage_bound=arms['scoped17']['stage_byte_bound'],optional_same_program_base948_control_stage_bound=arms['base948']['stage_byte_bound'],pair_stage_bound=pair,pair_limit_bytes=int(2.3*1024**3),asset_pack_sha256=sha(D/'tex.pak'),base948_pack_sha256=sha(BASE),no_stage_no_guest=True,approach='Stream raw2352 sectors to one cooked2048 track per arm. Preserve all1743 file LBAs. Expand only final program into two verified zero tail sectors; both packs and overlays/sidecars fit original allocations. Patch all matching ISO/RockRidge and Joliet directory-record extent/size fields, both-endian volume-space counts. Preserve every unrelated file extent/size/hash, directory positions, path tables, IP.BIN/system data and other tracks. No full extraction/rebuild or intermediate duplicate track.',resource='Plan metadata/tools <=20MiB. Future stage requires main allocation,freshC>=18GiB+2.3GiB+all outstanding capture/build reservations,runtimeC18GiB+64MiB; no allocation implied. One output per arm, no mirrored fulltrack, no guest capture within stagebound.')
report['zero_tail_slack']=dict(lba=549000,sectors=150,bytes=307200,sha256=hashlib.sha256(tail).hexdigest(),consumed_program_sectors=2,preserved_tail_sectors=148);report['pair_stage_bound_with_16MiB_metadata_reserve']=pair+16*1024**2;report['single_stage_bound_with_8MiB_metadata_reserve']=arms['scoped17']['stage_byte_bound']+8*1024**2
emit(E/'image-plan.json',report);used=sum(p.stat().st_size for p in E.rglob('*') if p.is_file());assert used<=20*1024**2
print(json.dumps(dict(files=len(files),tree_rows={k:len(v) for k,v in tree.items()},descriptors=desc,arms={k:dict(stage_bound=v['stage_byte_bound'],cooked=v['cooked_track_bytes'],relocations=[p for p,r in v['selected_paths'].items() if r['relocated']],actual_payload_changes=v['payload_changed_paths']) for k,v in arms.items()},pair_bytes=pair,metadata_bytes=used)))
