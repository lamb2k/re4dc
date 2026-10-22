from pathlib import Path
import hashlib,json,shutil,struct,subprocess,sys,types
T=Path('/root/probe/codex-qa21-combined-regression'); B=Path('/root/probe/qa21-combined-build-20261021'); R=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/qa21-combined-regression-20261021')
S=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/feedback21-runtime-20261021/qa-aafc10f3-input/gdemu'); D=R/'combined-input/gdemu'
sys.path.insert(0,str(T/'port/dreamcast/tools/d367/fullplay')); import fp_iso
assert not D.exists(); assert shutil.disk_usage('/mnt/c').free>18*1024**3+1400*1024**2
receipts={arm:json.loads((B/arm/'receipt.json').read_text()) for arm in ('default-off','qa-control','combined')}
assert len({r['source'] for r in receipts.values()})==1
assert all(receipts[a]['control_program_and_14_overlays_exact'] for a in ('default-off','qa-control'))
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert sha(S/'track03.bin')=='5ae451a0cb1e5c6e6db9b68d27335a09a00d27abd83e9c838c66ef2f8b69cfa8'
tr=fp_iso.Track(S/'track03.bin',45000); fs=fp_iso.files(tr); patches={}; ov=[]
for path,e,n in fs:
 if path.upper()=='/1ST_READ.BIN' or path.lower().endswith('.ovl'):
  f=B/'combined'/('program.bin' if path.upper()=='/1ST_READ.BIN' else Path(path).name)
  assert f.is_file(); data=f.read_bytes()
  if path.upper()=='/1ST_READ.BIN':assert hashlib.sha256(tr.read_bytes(e,n)).hexdigest()=='8942ad7e90d9adab56873d0738d76c274b98c28c35587e52fc93e2091f13300d'
  else:ov.append(path)
  patches[path]=(e,n,data)
assert len(ov)==14 and len(patches)==15
D.mkdir(parents=True); out=D/'track03.iso'
with (S/'track03.bin').open('rb') as rd,out.open('xb') as wr:
 while chunk:=rd.read(2352*512):
  assert len(chunk)%2352==0
  wr.write(b''.join(chunk[i+16:i+2064] for i in range(0,len(chunk),2352)))
  assert shutil.disk_usage('/mnt/c').free>18*1024**3+64*1024**2
locations={}
with out.open('r+b') as wr:
 for path,(e,n,data) in patches.items():
  if len(data)<=((n+2047)//2048)*2048:
   target=e; wr.seek((e-45000)*2048); wr.write(data); wr.write(b'\0'*((((n+2047)//2048)*2048)-len(data)))
  else:
   wr.seek(0,2); pos=wr.tell(); assert pos%2048==0
   target=45000+pos//2048; wr.write(data); wr.write(b'\0'*((-len(data))%2048))
  locations[path]=target
# Preserve each unrelated file's extent and bytes. Existing directory redirect tool handles both ISO and Joliet.
for path,(e,n,data) in patches.items():
 if locations[path]!=e or len(data)!=n:fp_iso.cmd_redirect(types.SimpleNamespace(track=str(out),lba=45000,path=path,to=locations[path],bytes=len(data)))
assert all(locations[p]==patches[p][0] for p in patches), 'This frozen candidate must fit existing allocations; preserve metadata'
new=fp_iso.Track(out,45000); lookup={p:(e,n) for p,e,n in fp_iso.files(new)}; assert set(lookup)=={p for p,e,n in fs}
manifest={}; unchanged=[]
for path,e,n in fs:
 ee,nn=lookup[path]; original=tr.read_bytes(e,n); current=new.read_bytes(ee,nn)
 if path in patches:assert current==patches[path][2]
 else:assert e==ee and n==nn and original==current,path;unchanged.append(path)
 manifest[path]={'bytes':nn,'sha256':hashlib.sha256(current).hexdigest(),'extent':ee,'changed':path in patches}
assert len(unchanged)==1728
for name in ('track01.bin','track02.raw'):shutil.copy2(S/name,D/name)
gdi=(S/'disc.gdi').read_text(); assert '3 45000 4 2352 track03.bin 0' in gdi
(D/'disc.gdi').write_text(gdi.replace('3 45000 4 2352 track03.bin 0','3 45000 4 2048 track03.iso 0'))
for arm in receipts:
 dst=R/'builds'/arm; dst.mkdir(parents=True)
 for f in (B/arm).iterdir():
  if f.is_file():shutil.copy2(f,dst/f.name)
 (dst/'KEEP.txt').write_text('Active combined qualification ELF/program/overlays/receipts. Preserve identity.\n')
receipt={'source':receipts['combined']['source'],'program_sha256':sha(B/'combined/program.bin'),'elf_sha256':sha(B/'combined/re4dc-game.elf'),'input_track03_sha256':sha(out),'disc_track03_name':'track03.iso','controls':receipts,'candidate_overlays':ov,'unchanged_file_count':len(unchanged),'relocated_files':{p:e for p,e in locations.items() if e!=patches[p][0]},'scope':'Private combined QA plus pause candidate; no release, asset, state or production recipe change'}
(R/'combined-input/candidate-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');(R/'combined-input/file-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'program':receipt['program_sha256'],'elf':receipt['elf_sha256'],'track':receipt['input_track03_sha256'],'unchanged':len(unchanged),'relocated_files':receipt['relocated_files']}))