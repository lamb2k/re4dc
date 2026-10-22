#!/usr/bin/env python3
"""Allocated standalone trace stage: copy image, patch15 files, preserve1728 exactly."""
from pathlib import Path
import hashlib,json,os,shutil,struct,sys,time,types
BASE=Path('/root/probe/codex-qa21-combined-regression');T=Path('/root/probe/codex-qa21-death-trace');R0=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/qa21-combined-regression-20261021');R=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/qa21-death-trace-runtime-20261021');S=R0/'combined-input/gdemu';D=R/'trace-input/gdemu';OFF=Path('/root/probe/qa21-death-trace-full-off-20261021');FAILED_ON=Path('/root/probe/qa21-death-trace-full-on-20261021');ON=Path('/root/probe/qa21-death-trace-full-on-retry-20261021');CAP=int(2.3*1024**3);FLOOR=18*1024**3+64*1024**2
sys.path.insert(0,str(BASE/'port/dreamcast/tools/d367/fullplay'));import fp_iso
from overlay_identity import elf_text,overlay_bytes

def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def footprint():
 total=0
 for root in (T,OFF,FAILED_ON,ON,R):
  if not root.exists():continue
  for folder,dirs,files in os.walk(root,followlinks=False):
   for name in dirs+files:
    try:st=(Path(folder)/name).lstat()
    except FileNotFoundError:continue
    total+=max(st.st_size,st.st_blocks*512)
 return total
peak=footprint();minimum=shutil.disk_usage('/mnt/c').free

def guard():
 global peak,minimum
 used=footprint();free=shutil.disk_usage('/mnt/c').free;peak=max(peak,used);minimum=min(minimum,free);assert used<CAP,'2.3GiB total fresh footprint';assert free>=FLOOR,'C18GiB+64MiB runtime floor'
assert shutil.disk_usage('/mnt/c').free>=18*1024**3+CAP,'Refuse before output: stage admission18GiB+2.3GiB';assert not R.exists(),'Preserve existing runtime/stage'
off=json.loads((OFF/'receipt.json').read_text());on=json.loads((ON/'receipt.json').read_text());assert off['full_OFF_control_identity'] and off['arm']=='off' and on['arm']=='on' and on['status']=='LINK_COMPLETE_ONLY' and on['all14_bound_to_new_ELF'];build=ON/'enabled';raw=build/'program.bin';elf=build/'re4dc-game.elf';assert sha(raw)==on['files']['program.bin']['sha256'] and sha(elf)==on['files']['re4dc-game.elf']['sha256'];assert sha(S/'track03.iso')=='97a3219f2876783cd28c5250479882e0b7643fecbff7a9bbbfc5df0886fc0a18'
tr=fp_iso.Track(str(S/'track03.iso'),45000);fs=fp_iso.files(tr);assert len(fs)==1743;old={p:(e,n) for p,e,n in fs};patches={p:(e,n,build/('program.bin' if p=='/1ST_READ.BIN' else Path(p).name)) for p,e,n in fs if p=='/1ST_READ.BIN' or p.lower().endswith('.ovl')};assert len(patches)==15
file_blocks=(S/'track03.iso').stat().st_size//2048;old_volume=struct.unpack_from('<I',tr.read(45016),80)[0];program=patches['/1ST_READ.BIN'];assert program[0]+(program[1]+2047)//2048==45000+old_volume;assert max(e+(n+2047)//2048 for _,e,n in fs)==45000+old_volume
with (S/'track03.iso').open('rb') as f:f.seek(old_volume*2048);tail=f.read()
assert len(tail)==307200 and not any(tail);assert raw.stat().st_size<=(45000+file_blocks-program[0])*2048
text=elf_text(elf)
for p,(e,n,f) in patches.items():
 assert sha(f)==on['files'][f.name]['sha256']
 if p!='/1ST_READ.BIN':assert f.stat().st_size<=((n+2047)//2048)*2048;overlay_bytes(f.read_bytes(),text)
assert shutil.disk_usage('/mnt/c').free>=18*1024**3+CAP,'Refuse before output after input hashing';D.mkdir(parents=True);(R/'builds/trace').mkdir(parents=True);started=time.monotonic();image=D/'track03.iso'
with (S/'track03.iso').open('rb') as src,image.open('xb') as dst:
 while b:=src.read(4*1024**2):dst.write(b);guard()
assert (S/'track03.iso').stat().st_ino!=image.stat().st_ino,'Image sharing prohibited'
with image.open('r+b') as dst:
 for p,(e,n,f) in patches.items():
  data=f.read_bytes();reserved=((n+2047)//2048)*2048 if p!='/1ST_READ.BIN' else (45000+file_blocks-e)*2048;dst.seek((e-45000)*2048);dst.write(data);dst.write(b'\0'*(reserved-len(data)));guard()
for p,(e,n,f) in patches.items():
 if f.stat().st_size!=n:fp_iso.cmd_redirect(types.SimpleNamespace(track=str(image),lba=45000,path=p,to=e,bytes=f.stat().st_size))
new_volume=max(old_volume,program[0]-45000+(raw.stat().st_size+2047)//2048);assert new_volume<=file_blocks;lba=45016
with image.open('r+b') as dst:
 while True:
  d=tr.read(lba);assert d[1:6]==b'CD001'
  if d[0] in (1,2):dst.seek((lba-45000)*2048+80);dst.write(struct.pack('<I',new_volume)+struct.pack('>I',new_volume))
  if d[0]==255:break
  lba+=1
new=fp_iso.Track(str(image),45000);lookup={p:(e,n) for p,e,n in fp_iso.files(new)};assert set(lookup)==set(old);manifest={};unchanged=0
with (S/'track03.iso').open('rb') as src,image.open('rb') as dst:
 for p,(e,n) in old.items():
  ee,nn=lookup[p];assert ee==e;dst.seek((ee-45000)*2048);h=hashlib.sha256();left=nn
  while left:b=dst.read(min(left,4*1024**2));assert b;h.update(b);left-=len(b)
  digest=h.hexdigest()
  if p in patches:assert digest==sha(patches[p][2])
  else:
   assert n==nn;src.seek((e-45000)*2048);h0=hashlib.sha256();left=n
   while left:b=src.read(min(left,4*1024**2));assert b;h0.update(b);left-=len(b)
   assert digest==h0.hexdigest(),p;unchanged+=1
  manifest[p]={'extent':ee,'bytes':nn,'sha256':digest,'declared_patch':p in patches};guard()
assert unchanged==1728;assert image.stat().st_size==(S/'track03.iso').stat().st_size
for name in ('track01.bin','track02.raw','disc.gdi'):shutil.copy2(S/name,D/name)
for f in build.iterdir():
 if f.is_file() and f.name!='build.log':shutil.copy2(f,R/'builds/trace'/f.name)
shutil.copy2(ON/'receipt.json',R/'build-receipt.json');shutil.copy2(OFF/'receipt.json',R/'OFF-build-receipt.json');(R/'builds/trace/KEEP.txt').write_text('Exact trace ELF/raw/14 overlays. Fresh cold trace lineage only; preserve identities.\n');assert sha(S/'track03.iso')=='97a3219f2876783cd28c5250479882e0b7643fecbff7a9bbbfc5df0886fc0a18';guard()
receipt={'scope':'Standalone diagnostic trace image only, no release/hardware acceptance','source':on['source']['trace_tools_HEAD'],'trace_runtime_source':on['source']['trace_runtime_source'],'program_sha256':sha(raw),'elf_sha256':sha(elf),'input_track03_sha256':'97a3219f2876783cd28c5250479882e0b7643fecbff7a9bbbfc5df0886fc0a18','input_track03_sha256_after':sha(S/'track03.iso'),'input_track03_name':'track03.iso','staged_track03_sha256':sha(image),'unrelated_exact_file_count':unchanged,'all14_staged_overlays_match_build':True,'source_image_mutated':False,'image_hardlinks_or_shared_writable_extents':False,'extracted_asset_tree':False,'program_extent_preserved':program[0],'old_volume_blocks':old_volume,'new_volume_blocks':new_volume,'track_length':image.stat().st_size,'peak_total_fresh_footprint_bytes':peak,'total_fresh_footprint_after':footprint(),'fresh_reservation_bytes':CAP,'minimum_free_C_bytes':minimum,'seconds':time.monotonic()-started,'files':{name:sha(D/name) for name in ('disc.gdi','track01.bin','track02.raw','track03.iso')}}
(R/'trace-input/file-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');(R/'stage-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'program':receipt['program_sha256'],'ELF':receipt['elf_sha256'],'image':receipt['staged_track03_sha256'],'unrelated':unchanged,'peak':peak,'free_min':minimum}))