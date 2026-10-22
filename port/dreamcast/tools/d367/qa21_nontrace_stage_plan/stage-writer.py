#!/usr/bin/env python3
"""Narrow reviewed standalone writer. Only main-approved supervisor may invoke.
No ELF/build copy, extraction, intermediate image, memory/input/state or release API.
"""
import argparse,hashlib,importlib.util,io,json,os,struct,sys,time
from pathlib import Path

def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
budget=load('budget',Path(__file__).with_name('stage-budget.py'))
CHUNK=4*1024**2;BASE=45000;BLOCK=2048

def hash_file(path,guard=lambda **kw:None):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  while b:=f.read(CHUNK):guard();h.update(b)
 return h.hexdigest()

def sync(dst):
 dst.flush()
 try:fileno=dst.fileno()
 except (AttributeError,io.UnsupportedOperation):return # in-memory test fixture only
 os.fsync(fileno)

def copy_stream(src,dst,guard,chunk=CHUNK):
 h=hashlib.sha256();total=0
 while b:=src.read(chunk):
  guard(extra=len(b));written=dst.write(b)
  if written!=len(b):raise RuntimeError('short copy write')
  dst.flush();guard();h.update(b);total+=len(b)
 sync(dst);guard()
 return total,h.hexdigest()

def identity(path):
 st=path.stat()
 if st.st_nlink!=1:raise ValueError('input/output hardlink forbidden')
 return dict(device=st.st_dev,inode=st.st_ino,bytes=st.st_size,mtime_ns=st.st_mtime_ns,links=st.st_nlink)

def require_source_identity(path,plan):
 current=identity(path)
 reviewed={'device':plan['source_device'],'inode':plan['source_inode'],'bytes':plan['track_bytes'],'mtime_ns':plan['source_mtime_ns'],'links':1}
 if current!=reviewed:raise ValueError('source image replacement/identity differs from reviewed plan')
 return current

def write_json(path,value,guard):
 data=(json.dumps(value,indent=2)+'\n').encode();guard(extra=len(data))
 with path.open('xb') as f:f.write(data);sync(f)
 guard()

def materialize(spec,build):
 if spec['kind']=='payload/reserved-zero-tail':
  data=(build/spec['input']).read_bytes()
  if len(data)!=spec['new_file_bytes'] or len(data)>spec['bytes']:raise ValueError('payload size mismatch')
  data+=b'\0'*(spec['bytes']-len(data))
 elif spec['kind']=='directory-size-both-endian':
  if spec['offset']!=37128 or spec['old_file_bytes']!=3349284 or spec['new_file_bytes']!=3348196:raise ValueError('undeclared metadata delta')
  data=struct.pack('<I',spec['new_file_bytes'])+struct.pack('>I',spec['new_file_bytes'])
 else:raise ValueError('unreviewed patch kind')
 if len(data)!=spec['bytes'] or hashlib.sha256(data).hexdigest()!=spec['new_sha256']:raise ValueError('declared patch bytes mismatch')
 return data

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--config',type=Path,required=True);ap.add_argument('--reviewed-manifest-sha256',required=True);ap.add_argument('--attempt',type=Path,required=True);a=ap.parse_args()
 if sys.stdin.buffer.readline(128).strip().decode()!=a.reviewed_manifest_sha256:raise ValueError('supervisor release token missing')
 if hash_file(a.config)!=a.reviewed_manifest_sha256:raise ValueError('reviewed config changed')
 c=json.loads(a.config.read_text())
 for path,digest in c['reviewed_tools'].items():
  if hash_file(path)!=digest:raise ValueError('reviewed tool changed')
 root=Path(c['output_root']);attempt=a.attempt
 if root!=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/qa21-ganado-reader-runtime-20261021') or attempt.parent!=root/'attempts' or attempt.name[:6]!='stage-':raise ValueError('output ownership scope mismatch')
 if attempt.resolve()!=attempt.absolute() or not attempt.is_dir():raise ValueError('output alias or missing supervisor attempt')
 owned=json.loads((attempt/'owned-process.json').read_text());stat=Path('/proc/self/stat').read_text();tail=stat[stat.rfind(')')+2:].split()
 if owned!={'pid':os.getpid(),'pgid':int(tail[2]),'proc_start':tail[19]} or int(tail[2])!=os.getpid():raise ValueError('not exact supervisor-owned writer')
 guard=budget.Guard(root)
 if c['stage_cap']!=budget.CAP or c['admission_floor']!=budget.ADMISSION or c['runtime_floor']!=budget.RUNTIME:raise ValueError('resource policy changed')
 planpath=Path(c['virtual_plan']);expectedpath=Path(c['expected_manifest']);bindingpath=Path(c['main_binding_reference']);build=Path(c['build']);source=Path(c['source_disc']);track=source/'track03.iso'
 plan=json.loads(planpath.read_text());expected=json.loads(expectedpath.read_text());mainbinding=json.loads(bindingpath.read_text())
 if plan['expected_standalone_track03_sha256']!=c['expected_image'] or plan['input_image_sha256_before']!=c['source_image'] or plan['program']!=c['program'] or plan['ELF']!=c['ELF'] or plan['source']!=c['source']:raise ValueError('fixed fixture identity mismatch')
 if c['source']!='c57ff60f0f462fdd2c419883b0258963504d756a' or c['program']!='52190ed293d8e62238bcad40fd351d35a965b253ad5b59cda570d0de34187e45' or c['ELF']!='248dd4aac7c4e22a7a18a0183fc6409401fddf610d98881c90dd9664e342640b' or c['source_image']!='3c216e5ae8e8c9716906eace0ac98bc1b0712c8540f053359438d32ba77a9238' or c['expected_image']!='da10104f6d4e28c6e4509a9fb75182fc4612f89a411ed4c1efa85d8a6c8bde7f':raise ValueError('not fixed reviewed c57/521 fixture')
 begin=time.monotonic();source_identity=require_source_identity(track,plan);provenance=plan['source_KEEP_and_evidence_hashes_before'];guard.check()
 for path,digest in provenance.items():
  if hash_file(path,guard.check)!=digest:raise ValueError('source KEEP/evidence changed')
 if hash_file(track,guard.check)!=c['source_image']:raise ValueError('source image changed')
 companions=plan['companions']
 for name,record in companions.items():
  if hash_file(source/name,guard.check)!=record['sha256']:raise ValueError('source companion changed')
 expectedfiles={'program.bin':c['program'],'re4dc-game.elf':c['ELF'],**expected['overlays']}
 for name,digest in expectedfiles.items():
  if hash_file(build/name,guard.check)!=digest:raise ValueError('new build changed '+name)
 on=[r for r in mainbinding['rows'] if r['arm']=='on-01']
 if len(on)!=1 or on[0]['source']!=c['source'] or on[0]['program']!=c['program'] or on[0]['ELF']!=c['ELF'] or any(not(o['image_and_relocation_fnv_valid'] and o['main_text_binding_valid']) for o in on[0]['overlays']):raise ValueError('main fullpair binding receipt invalid')
 ov=load('overlay_identity',c['overlay_validator']);text=ov.elf_text(build/'re4dc-game.elf');guard.check();overlay_checks={}
 for name,digest in expected['overlays'].items():
  blob=(build/name).read_bytes();overlay_checks[name]=ov.overlay_bytes(blob,text);guard.check()
  if overlay_checks[name]['sha256']!=digest:raise ValueError('overlay blob changed')
 specs=plan['patches']
 if len(specs)!=16 or sum(s['kind']=='payload/reserved-zero-tail' for s in specs)!=15 or sum(s['kind']=='directory-size-both-endian' for s in specs)!=1:raise ValueError('patch count changed')
 patches=[(s,materialize(s,build)) for s in specs]
 for s,data in patches:guard.check()
 # Re-evaluate cumulative failures, peer envelope and actual C IMMEDIATELY before any image output.
 guard.check(extra=c['estimated_new_bytes'],admission=True)
 disc=attempt/'input/gdemu';disc.mkdir(parents=True,exist_ok=False);image=disc/'track03.iso'
 guard.check(extra=c['estimated_new_bytes'],admission=True)
 print('phase=copy source_image='+c['source_image'],flush=True)
 with track.open('rb') as src,image.open('xb') as dst:copied,copysha=copy_stream(src,dst,guard.check)
 if copied!=plan['track_bytes'] or copysha!=c['source_image']:raise ValueError('whole source-copy mismatch')
 if identity(track)!=source_identity or image.stat().st_ino==track.stat().st_ino:raise ValueError('source changed or output sharing')
 print('phase=patch declared_ranges=16',flush=True)
 with image.open('r+b') as dst:
  for spec,data in sorted(patches,key=lambda p:p[0]['offset']):
   guard.check();dst.seek(spec['offset']);old=dst.read(spec['bytes'])
   if hashlib.sha256(old).hexdigest()!=spec['old_sha256']:raise ValueError('prepatch source range mismatch')
   dst.seek(spec['offset'])
   for offset in range(0,len(data),CHUNK):
    guard.check();chunk=data[offset:offset+CHUNK]
    if dst.write(chunk)!=len(chunk):raise RuntimeError('short patch write')
    dst.flush();guard.check()
  sync(dst);guard.check()
 for name,record in companions.items():
  with (source/name).open('rb') as src,(disc/name).open('xb') as dst:n,digest=copy_stream(src,dst,guard.check)
  if n!=record['bytes'] or digest!=record['sha256']:raise ValueError('companion copy mismatch')
 print('phase=whole_hash_and_two_parsers',flush=True)
 if image.stat().st_size!=plan['track_bytes'] or hash_file(image,guard.check)!=c['expected_image']:raise ValueError('whole prospective track mismatch')
 independent=load('iso_independent',c['independent_parser']);fp=load('fp_iso',c['fp_iso']);manifest={}
 with image.open('rb') as f:
  def read(offset,length):
   guard.check()
   if offset<0 or length<0 or offset+length>plan['track_bytes']:raise ValueError('validation range outside image')
   f.seek(offset);data=f.read(length)
   if len(data)!=length:raise ValueError('short staged read')
   return data
  iso=independent.ISO(read,plan['track_bytes']);rows=[r for r in iso.entries() if not r['directory']]
  planner=load('virtual_stage_plan',c['virtual_planner']);conventional={p:(e,n) for p,e,n in fp.files(planner.AdapterTrack(read,plan['track_bytes']))}
  if conventional!={r['path']:(r['extent'],r['bytes']) for r in rows}:raise ValueError('staged independent parser disagreement')
  if any(kind!=1 for kind,_,_ in iso.roots):raise ValueError('unexpected supplementary tree')
  if iso.descriptors!=[{'offset':32768,'kind':1,'blocks':504001}]:raise ValueError('volume metadata changed')
  ip=read(0,32768)
  if hashlib.sha256(ip).hexdigest()!=plan['fixed_IP_sha256'] or ip[0x60:0x70].strip(b' \0')!=b'1ST_READ.BIN':raise ValueError('fixed IP/boot entry changed')
  for row in rows:
   digest=planner.digest_range(read,(row['extent']-BASE)*BLOCK,row['bytes']);path=row['path']
   wanted=plan['files'].get(path)
   actual=dict(extent=row['extent'],bytes=row['bytes'],sha256=digest,declared_patch=wanted['declared_patch'] if wanted else None)
   if actual!=wanted:raise ValueError('staged file/extent/SHA mismatch '+path)
   manifest[path]=actual
 if len(manifest)!=1743 or sum(not v['declared_patch'] for v in manifest.values())!=1728:raise ValueError('complete manifest count mismatch')
 print('phase=all_input_rehash_and_seal',flush=True)
 if hash_file(track,guard.check)!=c['source_image'] or identity(track)!=source_identity:raise ValueError('source image identity changed after stage')
 for path,digest in provenance.items():
  if hash_file(path,guard.check)!=digest:raise ValueError('source KEEP/evidence mutated')
 for name,digest in expectedfiles.items():
  if hash_file(build/name,guard.check)!=digest:raise ValueError('source build mutated')
 for name,record in companions.items():
  if hash_file(source/name,guard.check)!=record['sha256'] or hash_file(disc/name,guard.check)!=record['sha256']:raise ValueError('companion source/output mutated')
 output_identity=identity(image)
 if (output_identity['inode'],output_identity['device'])==(source_identity['inode'],source_identity['device']):raise ValueError('shared image identity')
 receipt={'scope':'Standalone experimental c57/521 stage only; no guest/release/hardware acceptance','config_sha256':a.reviewed_manifest_sha256,'source':c['source'],'program':c['program'],'ELF':c['ELF'],'image':c['expected_image'],'source_image_before_after':c['source_image'],'source_identity_before_after':source_identity,'new_image_identity':output_identity,'main_fullpair_docs':mainbinding['main_docs_commit'],'all14_new_ELF_bindings':overlay_checks,'unrelated_exact_files':1728,'complete_files':1743,'declared_patch_count':16,'fixed_IP_sha256':plan['fixed_IP_sha256'],'metadata_deltas':plan['metadata_deltas'],'minimum_C':guard.minimum,'peak_stage_bytes':guard.peak,'seconds':time.monotonic()-begin,'no_ELFcopy':True,'no_extraction':True,'no_input_mutation':True,'no_oldstate_transfer':True,'disc_path':str(disc)}
 write_json(attempt/'file-manifest.json',manifest,guard.check);write_json(attempt/'stage-receipt.json',receipt,guard.check)
 keep=b'Experimental corrected-reader nontrace standalone fixture. Preserve exact image/program/14/assets. New-program cold lineage only; no release or hardware acceptance.\n';guard.check(extra=len(keep))
 with (attempt/'KEEP.txt').open('xb') as f:f.write(keep);sync(f)
 guard.check();print(json.dumps({'stage_complete':True,'image':c['expected_image'],'program':c['program'],'ELF':c['ELF'],'disc':str(disc)}),flush=True)
if __name__=='__main__':main()
