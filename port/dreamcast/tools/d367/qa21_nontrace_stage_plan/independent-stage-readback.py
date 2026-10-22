#!/usr/bin/env python3
"""Post-supervisor independent read-only full image/file/overlay qualification.
Writes only one bounded JSON receipt; no copy, patch, source edit or guest API.
"""
import hashlib,importlib.util,json,time
from pathlib import Path
P=Path(__file__).parent

def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
 config=P/'reviewed-stage-config.json'
 if hashlib.sha256(config.read_bytes()).hexdigest()!='4c912017f8220dd431c6e0ec43e1bdffa592a6baa83f8cdf96c8ee2908cb7039':raise ValueError('reviewed config mismatch')
 c=json.loads(config.read_text())
 for path,digest in c['reviewed_tools'].items():
  if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest:raise ValueError('reviewed tool/data changed '+path)
 plan=json.loads(Path(c['virtual_plan']).read_text());root=Path(c['output_root']);a=root/'attempts/stage-001';disc=a/'input/gdemu';image=disc/'track03.iso';output=a/'independent-readback.json'
 if output.exists():raise ValueError('refusing overwrite')
 supervisor=json.loads((a/'supervisor-receipt.json').read_text());stage=json.loads((a/'stage-receipt.json').read_text())
 if not supervisor['qualified'] or not supervisor['child_exited'] or supervisor['returncode']!=0 or stage['image']!=c['expected_image']:raise ValueError('unqualified supervisor/stage')
 owned=supervisor['owned'];proc=Path('/proc/'+str(owned['pid']))
 if proc.exists():raise ValueError('stage PID not gone; close before readback')
 budget=load('budget',P/'stage-budget.py');guard=budget.Guard(root);guard.check()
 def sha(path):
  h=hashlib.sha256()
  with Path(path).open('rb') as f:
   while data:=f.read(1024**2):guard.check();h.update(data)
  return h.hexdigest()
 def ident(path):
  s=path.stat();return {'device':s.st_dev,'inode':s.st_ino,'bytes':s.st_size,'mtime_ns':s.st_mtime_ns,'links':s.st_nlink}
 expected_source={'device':plan['source_device'],'inode':plan['source_inode'],'bytes':plan['track_bytes'],'mtime_ns':plan['source_mtime_ns'],'links':1};source=Path(c['source_disc'])/'track03.iso';sourcebefore=ident(source);destbefore=ident(image)
 if sourcebefore!=expected_source or destbefore['links']!=1 or (sourcebefore['inode'],sourcebefore['device'])==(destbefore['inode'],destbefore['device']):raise ValueError('image identities/sharing mismatch')
 started=time.monotonic()
 if sha(image)!=c['expected_image'] or sha(source)!=c['source_image']:raise ValueError('full image/source SHA mismatch')
 independent=load('iso_independent',c['independent_parser']);fp=load('fp_iso',c['fp_iso']);ov=load('overlay_identity',c['overlay_validator']);elf=Path(c['build'])/'re4dc-game.elf'
 if sha(elf)!=c['ELF']:raise ValueError('exact new ELF mismatch')
 text=ov.elf_text(elf);guard.check();manifest={};overlay_checks={}
 with image.open('rb') as f:
  def read(offset,length):
   guard.check()
   if offset<0 or length<0 or offset+length>plan['track_bytes']:raise ValueError('read outside stage')
   f.seek(offset);b=f.read(length)
   if len(b)!=length:raise ValueError('short stage read')
   return b
  iso=independent.ISO(read,plan['track_bytes']);files=[r for r in iso.entries() if not r['directory']]
  tr=fp.Track(str(image),45000)
  try:second={p:(e,n) for p,e,n in fp.files(tr)}
  finally:tr.f.close()
  if second!={r['path']:(r['extent'],r['bytes']) for r in files}:raise ValueError('independent parser mismatch')
  if iso.roots!=[(1,45018,2048)] or iso.descriptors!=[{'offset':32768,'kind':1,'blocks':504001}]:raise ValueError('descriptor/root mismatch')
  ip=read(0,32768)
  if hashlib.sha256(ip).hexdigest()!=plan['fixed_IP_sha256'] or ip[0x60:0x70].strip(b' \0')!=b'1ST_READ.BIN':raise ValueError('fixed IP/boot mismatch')
  for row in files:
   path=row['path'];want=plan['files'].get(path);start=(row['extent']-45000)*2048;h=hashlib.sha256()
   for offset in range(0,row['bytes'],1024**2):h.update(read(start+offset,min(1024**2,row['bytes']-offset)))
   actual={'extent':row['extent'],'bytes':row['bytes'],'sha256':h.hexdigest(),'declared_patch':want['declared_patch'] if want else None}
   if actual!=want:raise ValueError('file/extent/SHA mismatch '+path)
   if path.lower().endswith('.ovl'):overlay_checks[path]=ov.overlay_bytes(read(start,row['bytes']),text)
   manifest[path]=actual
 if len(manifest)!=1743 or len(overlay_checks)!=14 or sum(not r['declared_patch'] for r in manifest.values())!=1728:raise ValueError('file/overlay count mismatch')
 for path,digest in plan['source_KEEP_and_evidence_hashes_before'].items():
  if sha(path)!=digest:raise ValueError('source KEEP/evidence changed')
 for name,expected in plan['companions'].items():
  if sha(disc/name)!=expected['sha256'] or sha(Path(c['source_disc'])/name)!=expected['sha256']:raise ValueError('companion mismatch')
 if ident(source)!=sourcebefore or ident(image)!=destbefore:raise ValueError('image identity changed during readback')
 receipt={'scope':'Independent post-supervisor full image readback only; no guest/release/hardware acceptance','source':c['source'],'program':c['program'],'ELF':c['ELF'],'image':c['expected_image'],'source_image':c['source_image'],'source_identity':sourcebefore,'new_image_identity':destbefore,'full_track_and_source_SHA_pass':True,'both_parser_file_maps_equal':True,'file_count':1743,'unrelated_extents_size_SHA_exact':1728,'all14_independent_new_ELF_bindings':overlay_checks,'fixed_IP_sha256':plan['fixed_IP_sha256'],'primary_only_no_Joliet':True,'supervisor_qualified':True,'owned_stage_PID_gone':owned,'reader_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'seconds':time.monotonic()-started,'minimum_C':guard.minimum,'peak_cumulative_stage_bytes':guard.peak,'output_metadata_bytes_only':True}
 data=(json.dumps(receipt,indent=2)+'\n').encode();guard.check(extra=len(data))
 with output.open('xb') as f:f.write(data)
 guard.check();print(json.dumps({k:receipt[k] for k in ['image','program','ELF','file_count','unrelated_extents_size_SHA_exact','seconds','minimum_C']}))
if __name__=='__main__':main()
