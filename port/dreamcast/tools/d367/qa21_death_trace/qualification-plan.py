#!/usr/bin/env python3
"""Read-only exact image/cold-lineage plan. Never writes an image or launches a guest."""
from pathlib import Path
import argparse,hashlib,json,struct,sys
BASE=Path('/root/probe/codex-qa21-combined-regression');TRACE=Path('/root/probe/codex-qa21-death-trace');R=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/qa21-combined-regression-20261021');S=R/'combined-input/gdemu';p=argparse.ArgumentParser();p.add_argument('--build-receipt',type=Path);p.add_argument('--output',type=Path);a=p.parse_args();sys.path.insert(0,str(BASE/'port/dreamcast/tools/d367/fullplay'));import fp_iso
from overlay_identity import elf_text,overlay_bytes

def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
image=S/'track03.iso';assert sha(image)=='97a3219f2876783cd28c5250479882e0b7643fecbff7a9bbbfc5df0886fc0a18';tr=fp_iso.Track(str(image),45000);manifest=R/'combined-input/file-manifest.json';prior=json.loads(manifest.read_text());fs=fp_iso.files(tr);assert len(fs)==1743 and {x[0] for x in fs}==set(prior)
with image.open('rb') as source:
 for name,extent,n in fs:
  row=prior[name];assert extent==row['extent'] and n==row['bytes'];source.seek((extent-45000)*2048);h=hashlib.sha256();left=n
  while left:
   b=source.read(min(left,4*1024**2));assert b;h.update(b);left-=len(b)
  assert h.hexdigest()==row['sha256'],name
program=prior['/1ST_READ.BIN'];descriptors=[];lba=45016
while True:
 d=tr.read(lba);assert d[1:6]==b'CD001';kind=d[0]
 if kind in (1,2):
  le=struct.unpack_from('<I',d,80)[0];be=struct.unpack_from('>I',d,84)[0];assert le==be;descriptors.append({'lba':lba,'type':kind,'volume_blocks':le})
 if kind==255:break
 lba+=1
volume_blocks=descriptors[0]['volume_blocks'];file_blocks=image.stat().st_size//2048;assert all(d['volume_blocks']==volume_blocks for d in descriptors);old_end=program['extent']+((program['bytes']+2047)//2048);assert old_end==45000+volume_blocks;assert max(e+(n+2047)//2048 for _,e,n in fs)==old_end
with image.open('rb') as f:f.seek(volume_blocks*2048);tail=f.read()
assert len(tail)==(file_blocks-volume_blocks)*2048 and not any(tail)
max_program=(45000+file_blocks-program['extent'])*2048;overlay_paths=[name for name in prior if name.lower().endswith('.ovl')];assert len(overlay_paths)==14
text=elf_text(R/'builds/combined/re4dc-game.elf');input_overlays={name:overlay_bytes(tr.read_bytes(prior[name]['extent'],prior[name]['bytes']),text) for name in overlay_paths}
plan={'scope':'Exact read-only preparation. No build, stage, image sharing, extracted tree or runtime launch','trace_source':'f99dc69ad8bfeebcdb10913443543514dc40f9cc','image':{'path':str(image),'sha256':sha(image),'logical_bytes':image.stat().st_size,'track_base':45000,'file_blocks':file_blocks,'volume_descriptors':descriptors,'manifest_path':str(manifest),'manifest_sha256':sha(manifest),'all1743_file_hashes_reverified':True,'all14_input_overlays_bound_to_frozen_combined_ELF':True},'program':program,'verified_zero_tail_bytes':len(tail),'max_final_program_bytes_without_relocation':max_program,'stage_method':{'status':'UNALLOCATED; plan only','input_read_only':True,'new_standalone_track_copy':True,'image_hardlinks_or_shared_writable_extents':False,'extracted_asset_tree':False,'changes':'Stream immutable2048-byte track into a new standalone file, write final trace program at same final extent, zero its remaining reserved tail, patch all14 newly linked overlays in their existing allocations (refuse oversize), update changed program/overlay byte sizes in ISO/RockRidge+Joliet records and volume blocks in both-endian PVD/SVD fields only when needed. Keep track length and all unrelated extents exact. Copy tiny tracks independently.','refusal':'If raw exceeds verified final-program-plus-zero-tail bound, refuse. No automatic append, relocation, hardlinks or source-image patch.','unrelated_gate':'All1728 files outside program plus14 overlays must keep exact paths/extents/sizes/SHA; all14 staged overlays must match the new full-link outputs and ELF binding, never old headers. Reverify whole source SHA before/after and new staged program/full image SHA.','resource_budget':'Conservatively reserve full1,032,499,200B standalone logical image plus2,295,552B tiny tracks and64MiB metadata/scratch, preserving unchanged18GiB+64MiB runtime floor. Any compression savings are measured after staging, never assumed for admission.'},'overlay_paths':overlay_paths,'input_overlay_bindings':input_overlays,'tools':{'fp_iso_sha256':sha(BASE/'port/dreamcast/tools/d367/fullplay/fp_iso.py'),'cold_keys':{'path':str(BASE/'port/dreamcast/tools/d367/qa21_combined/r103-cold-keys.txt'),'sha256':sha(BASE/'port/dreamcast/tools/d367/qa21_combined/r103-cold-keys.txt')},'door_controller':{'path':str(BASE/'port/dreamcast/tools/d367/qa21_combined/normal-r103-door-v2.py'),'sha256':sha(BASE/'port/dreamcast/tools/d367/qa21_combined/normal-r103-door-v2.py')},'BB_keys':{'path':str(BASE/'port/dreamcast/tools/d367/qa21_combined/new-room-no-qa-keys.txt'),'sha256':sha(BASE/'port/dreamcast/tools/d367/qa21_combined/new-room-no-qa-keys.txt')}},'cold_lineage':{'status':'UNALLOCATED until exact new stage/binding/DWARF identities exist','episodes':[{'name':'deathtrace-cold-r10301','seed':None,'input':'Pinned original QA preset4 selection; cold first process, no.state file allowed'},{'name':'deathtrace-return-door01','seed':'deathtrace-cold-r10301','input':'Pinned ordinary PID-owned r103 door controller'},{'name':'deathtrace-BB-only01','seed':'deathtrace-return-door01','input':'Only pinned normalB/B, no QA chord atnew room; preserve all damage and exact trace output'}],'guards':'Global<=16, absolute47.5s own guest/inner41s, fresh18GiB+128MiB/runtime18GiB+64MiB, <=60MB new evidence perguest, PID/executable/start validated','identity':'Each new checkpoint uses only the exact new trace program/image/ELF/VMU ancestry and four immutable text anchors; old combined/control states prohibited. Screenshots and source frame/caller mappings retained.','acceptance':'Source/unit, full link, Flycast diagnostic reproduction, release checks and physical Dreamcast acceptance remain separate'}}
if a.build_receipt:
 build=json.loads(a.build_receipt.read_text());assert build['status']=='LINK_COMPLETE_ONLY' and not build['stage_performed'];raw=Path(build['source']['job'])/'enabled/program.bin';assert sha(raw)==build['files']['program.bin']['sha256'];size=raw.stat().st_size;assert size<=max_program,'Raw exceeds zero-tail stage plan'
 for name in overlay_paths:
  ovl=raw.parent/Path(name).name;assert sha(ovl)==build['files'][ovl.name]['sha256'];assert ovl.stat().st_size<=((prior[name]['bytes']+2047)//2048)*2048,'Overlay exceeds existing allocation: '+name
 plan['built_program']={'bytes':size,'sha256':sha(raw),'ELF':build['files']['re4dc-game.elf'],'all14_bound_to_new_ELF':build['all14_bound_to_new_ELF'],'required_new_volume_blocks':max(volume_blocks,program['extent']-45000+(size+2047)//2048),'source_receipt_sha256':sha(a.build_receipt)}
blob=json.dumps(plan,indent=2)+'\n'
if a.output:
 assert not a.output.exists();a.output.write_text(blob)
print(blob)