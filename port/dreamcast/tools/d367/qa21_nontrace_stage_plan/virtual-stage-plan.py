#!/usr/bin/env python3
"""Read-only program+14 virtual patch planner. Creates JSON metadata only.
No output image/copy/extraction/save-state/input API exists in this planner.
"""
import argparse,hashlib,importlib.util,json,os,struct,sys,time
from pathlib import Path

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
ISO=load('iso_independent',Path(__file__).with_name('iso-independent.py')).ISO
BASE=45000;BLOCK=2048;CHUNK=1024*1024

def digest_file(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(CHUNK),b''):h.update(b)
 return h.hexdigest()

def digest_range(read,start,length):
 h=hashlib.sha256()
 for offset in range(start,start+length,CHUNK):h.update(read(offset,min(CHUNK,start+length-offset)))
 return h.hexdigest()

class Virtual:
 def __init__(self,source,patches):
  self.source=source;self.patches=sorted(patches,key=lambda p:p['offset'])
  for left,right in zip(self.patches,self.patches[1:]):
   if left['offset']+len(left['data'])>right['offset']:raise ValueError('overlapping declared patches')
 def read(self,start,length):
  b=bytearray(self.source(start,length))
  for p in self.patches:
   begin=max(start,p['offset']);end=min(start+length,p['offset']+len(p['data']))
   if begin<end:b[begin-start:end-start]=p['data'][begin-p['offset']:end-p['offset']]
  return bytes(b)

class AdapterTrack:
 def __init__(self,read,size):self.get=read;self.base=BASE;self.count=size//BLOCK
 def read(self,lba,n=1):return self.get((lba-BASE)*BLOCK,n*BLOCK)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-disc',type=Path,required=True);ap.add_argument('--source-manifest',type=Path,required=True);ap.add_argument('--build',type=Path,required=True);ap.add_argument('--expected',type=Path,required=True);ap.add_argument('--fp-iso',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 if a.output.exists():raise ValueError('refusing overwrite')
 track=a.source_disc/'track03.iso';evidence=a.source_disc.parent.parent;provenance_paths=[a.source_manifest,evidence/'stage-receipt.json',evidence/'builds/trace/KEEP.txt'];provenance_before={str(p):digest_file(p) for p in provenance_paths};before=track.stat();expected=json.loads(a.expected.read_text());oldmanifest=json.loads(a.source_manifest.read_text());sourcehash=digest_file(track)
 if sourcehash!='3c216e5ae8e8c9716906eace0ac98bc1b0712c8540f053359438d32ba77a9238':raise ValueError('source image identity mismatch')
 files={'program.bin':expected['program_sha256'],**expected['overlays']}
 actual={n:digest_file(a.build/n) for n in files}
 if actual!=files or len(expected['overlays'])!=14:raise ValueError('new payload identities mismatch')
 fp=load('fp_iso',a.fp_iso);source_handles=[]
 with track.open('rb') as f:
  def original(offset,length):
   if offset<0 or length<0 or offset+length>before.st_size:raise ValueError('read outside source')
   f.seek(offset);b=f.read(length)
   if len(b)!=length:raise ValueError('short source read')
   return b
  iso=ISO(original,before.st_size);primary=[r for r in iso.entries() if not r['directory']];lookup={r['path']:r for r in primary}
  conventional={p:(e,n) for p,e,n in fp.files(AdapterTrack(original,before.st_size))}
  if conventional!={r['path']:(r['extent'],r['bytes']) for r in primary} or len(primary)!=1743:raise ValueError('independent primary parser mismatch')
  if set(lookup)!=set(oldmanifest):raise ValueError('sealed source manifest file set mismatch')
  for p,r in lookup.items():
   old=oldmanifest[p]
   if (r['extent'],r['bytes'])!=(old['extent'],old['bytes']):raise ValueError('source manifest extent/size mismatch')
  patchfiles={p:('program.bin' if p=='/1ST_READ.BIN' else Path(p).name) for p in lookup if p=='/1ST_READ.BIN' or p.lower().endswith('.ovl')}
  if len(patchfiles)!=15 or set(patchfiles.values())!=set(files):raise ValueError('exact declared payload set mismatch')
  program=lookup['/1ST_READ.BIN'];volume=[v['blocks'] for v in iso.descriptors if v['kind']==1][0]
  if program['extent']+(program['bytes']+BLOCK-1)//BLOCK!=BASE+volume:raise ValueError('program is not final volume file')
  if any(original(volume*BLOCK,before.st_size-volume*BLOCK)):raise ValueError('nonzero reserved track tail')
  patches=[];metadata=[]
  for path,name in patchfiles.items():
   r=lookup[path];data=(a.build/name).read_bytes();offset=(r['extent']-BASE)*BLOCK
   reserve=before.st_size-offset if path=='/1ST_READ.BIN' else (r['bytes']+BLOCK-1)//BLOCK*BLOCK
   if len(data)>reserve:raise ValueError('payload exceeds retained extent allocation')
   patches.append(dict(path=path,kind='payload/reserved-zero-tail',offset=offset,data=data+b'\0'*(reserve-len(data)),old_file_bytes=r['bytes'],new_file_bytes=len(data),extent=r['extent'],input=name))
  for kind,_,_ in iso.roots:
   for rec in iso.entries(kind):
    matching=[p for p in patchfiles if p.lower()==rec['path'].lower()]
    if not matching:continue
    if len(matching)!=1 or rec['directory']:raise ValueError('ambiguous metadata target')
    path=matching[0];size=(a.build/patchfiles[path]).stat().st_size
    if rec['extent']!=lookup[path]['extent']:raise ValueError('supplementary tree extent mismatch')
    if rec['bytes']!=size:
     patch=dict(path=path,kind='directory-size-both-endian',offset=rec['record_offset']+10,data=struct.pack('<I',size)+struct.pack('>I',size),old_file_bytes=rec['bytes'],new_file_bytes=size,tree=kind)
     patches.append(patch);metadata.append({k:v for k,v in patch.items() if k!='data'})
  newvolume=max(volume,program['extent']-BASE+((a.build/'program.bin').stat().st_size+BLOCK-1)//BLOCK)
  if newvolume*BLOCK>before.st_size:raise ValueError('new volume exceeds fixed track')
  for d in iso.descriptors:
   if d['blocks']!=newvolume:
    patch=dict(kind='volume-blocks-both-endian',offset=d['offset']+80,data=struct.pack('<I',newvolume)+struct.pack('>I',newvolume),old_blocks=d['blocks'],new_blocks=newvolume)
    patches.append(patch);metadata.append({k:v for k,v in patch.items() if k!='data'})
  virtual=Virtual(original,patches);newiso=ISO(virtual.read,before.st_size);newfiles={r['path']:r for r in newiso.entries() if not r['directory']}
  newconventional={p:(e,n) for p,e,n in fp.files(AdapterTrack(virtual.read,before.st_size))}
  if newconventional!={p:(r['extent'],r['bytes']) for p,r in newfiles.items()} or set(newfiles)!=set(lookup):raise ValueError('virtual independent parser mismatch')
  manifest={};unrelated=0
  for path,old in lookup.items():
   new=newfiles[path]
   if old['extent']!=new['extent']:raise ValueError('file extent changed')
   oldsha=digest_range(original,(old['extent']-BASE)*BLOCK,old['bytes'])
   if oldsha!=oldmanifest[path]['sha256']:raise ValueError('sealed original asset hash mismatch '+path)
   newsha=digest_range(virtual.read,(new['extent']-BASE)*BLOCK,new['bytes'])
   if path in patchfiles:
    if newsha!=files[patchfiles[path]]:raise ValueError('virtual staged payload mismatch')
   else:
    if (old['bytes'],oldsha)!=(new['bytes'],newsha):raise ValueError('unrelated file mutation')
    unrelated+=1
   manifest[path]=dict(extent=new['extent'],bytes=new['bytes'],sha256=newsha,declared_patch=path in patchfiles)
  if unrelated!=1728:raise ValueError('unrelated count mismatch')
  ip=original(0,32768)
  if virtual.read(0,32768)!=ip or ip[0x60:0x70].strip(b' \0')!=b'1ST_READ.BIN':raise ValueError('fixed IP/boot entry changed or unexpected')
  targethash=digest_range(virtual.read,0,before.st_size)
  patch_receipts=[{**{k:v for k,v in p.items() if k!='data'},'bytes':len(p['data']),'old_sha256':digest_range(original,p['offset'],len(p['data'])),'new_sha256':hashlib.sha256(p['data']).hexdigest()} for p in patches]
 sourceafter=digest_file(track);after=track.stat()
 if sourceafter!=sourcehash or (before.st_ino,before.st_dev,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_dev,after.st_size,after.st_mtime_ns):raise ValueError('source file identity changed')
 if {n:digest_file(a.build/n) for n in files}!=actual:raise ValueError('payload source changed')
 provenance_after={str(p):digest_file(p) for p in provenance_paths}
 if provenance_after!=provenance_before:raise ValueError('source KEEP/evidence metadata mutated')
 companions={n:dict(bytes=(a.source_disc/n).stat().st_size,sha256=digest_file(a.source_disc/n)) for n in ('disc.gdi','track01.bin','track02.raw')}
 cap=int(1.2*1024**3);metadata_budget=20*1024**2;newbytes=before.st_size+sum(v['bytes'] for v in companions.values())+metadata_budget
 if newbytes>cap:raise ValueError('future stage worst-case estimate exceeds1.2GiB')
 result={'scope':'Read-only virtual stage plan; NO image/copy/stage/guest produced','source':expected['source'],'ELF':expected['elf_sha256'],'program':expected['program_sha256'],'input_image_sha256_before':sourcehash,'input_image_sha256_after':sourceafter,'expected_standalone_track03_sha256':targethash,'track_bytes':before.st_size,'source_inode':before.st_ino,'source_device':before.st_dev,'source_mtime_ns':before.st_mtime_ns,'old_volume_blocks':volume,'new_volume_blocks':newvolume,'fixed_IP_sha256':hashlib.sha256(ip).hexdigest(),'fixed_boot_entry':'1ST_READ.BIN','all15_payloads_exact':True,'unrelated_exact_files':unrelated,'independent_primary_and_virtual_parser_agreement':True,'metadata_deltas':metadata,'patches':patch_receipts,'files':manifest,'companions':companions,'future_stage_cap_bytes_including_failures':cap,'future_peak_estimate_image_companions_plus20MiB':newbytes,'source_KEEP_and_evidence_hashes_before':provenance_before,'source_KEEP_and_evidence_hashes_after':provenance_after,'source_manifest_sha256':digest_file(a.source_manifest),'expected_manifest_sha256':digest_file(a.expected),'fp_iso_sha256':digest_file(a.fp_iso),'planner_sha256':digest_file(Path(__file__)),'independent_parser_sha256':digest_file(Path(__file__).with_name('iso-independent.py'))}
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('expected_standalone_track03_sha256','track_bytes','unrelated_exact_files','future_peak_estimate_image_companions_plus20MiB')}))
if __name__=='__main__':main()
