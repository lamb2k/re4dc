#!/usr/bin/env python3
"""Independent finished ISO readback, adapted from qualified rectangle verifier.

Reads ISO directory bytes itself; never trusts writer's in-memory stream digest.
No game/asset/state writes. Report output is exclusive-create.
"""
import argparse,hashlib,json,os,struct
from pathlib import Path
from mipmap_pair_plan import sha,local
def both(rec,off):
 le=struct.unpack_from('<I',rec,off)[0];be=struct.unpack_from('>I',rec,off+4)[0]
 if le!=be:raise ValueError('LE/BE disagreement')
 return le
def name_of(rec):
 n=rec[32];raw=rec[33:33+n];j=33+n+(0 if n%2 else 1);out=b''
 while j+4<=len(rec):
  ln=rec[j+2]
  if ln<4:break
  if rec[j:j+2]==b'NM':out+=rec[j+5:j+ln]
  j+=ln
 return os.fsdecode(out)if out else os.fsdecode(raw).split(';')[0].rstrip('.')
def read_iso(imagepath):
 with imagepath.open('rb')as f:
  def rd(e,n):
   if e<45000 or n<0 or (e-45000)*2048+n>imagepath.stat().st_size:raise ValueError('extent outside track')
   f.seek((e-45000)*2048);b=f.read(n)
   if len(b)!=n:raise ValueError('short extent')
   return b
  pvd=rd(45016,2048)
  if pvd[:7]!=b'\x01CD001\x01' or rd(45017,1)!=b'\xff':raise ValueError('primary-only/noJoliet contract')
  root=pvd[156:190];todo=[('',both(root,2),both(root,10))];seen=set();files={};records=[]
  while todo:
   prefix,e,n=todo.pop()
   if e in seen:raise ValueError('directory alias/cycle')
   seen.add(e);buf=rd(e,n);off=0
   while off<len(buf):
    ln=buf[off]
    if not ln:off=(off//2048+1)*2048;continue
    rec=buf[off:off+ln]
    if len(rec)!=ln or off%2048+ln>2048:raise ValueError('record boundary')
    raw=rec[33:33+rec[32]]
    if raw not in (b'\0',b'\1'):
     path=prefix+'/'+name_of(rec);ee=both(rec,2);nn=both(rec,10);isd=bool(rec[25]&2);records.append(dict(path=path,extent=ee,bytes=nn,is_directory=isd,record_lba=e,record_offset=off,record_hex=rec.hex()))
     if isd:todo.append((path,ee,nn))
     else:
      if path in files:raise ValueError('duplicate file path')
      h=hashlib.sha256();remaining=nn;f.seek((ee-45000)*2048)
      while remaining:
       b=f.read(min(1048576,remaining))
       if not b:raise ValueError('file truncated')
       h.update(b);remaining-=len(b)
      files[path]=dict(extent=ee,bytes=nn,sha256=h.hexdigest())
    off+=ln
  return files,records,{'PVD_blocks':both(pvd,80),'IP_sha256':hashlib.sha256(rd(45000,32768)).hexdigest(),'tail_sha256':hashlib.sha256(rd(45000+both(pvd,80),(504150-both(pvd,80))*2048)).hexdigest(),'tail_all_zero':not any(rd(45000+both(pvd,80),(504150-both(pvd,80))*2048))}
def verify(a):
 plan=json.loads(a.plan.read_text());assert sha(a.plan)==a.plan_sha256
 expected=json.loads(a.baseline_manifest.read_text())['files'];expected={('/'+k.lstrip('/')):{'bytes':v['size'],'extent':v['extent'],'sha256':v['sha256']}for k,v in expected.items()}
 source_refs=[]
 for r in plan['common_ranges']+plan['arms'][a.arm]['ranges']:
  assert sha(local(r['source_path']))==r['sha256'];expected[r['path']]={'extent':45000+r['start']//2048,'bytes':r['bytes'],'sha256':r['sha256']};source_refs.append(r['path'])
 assert a.image.stat().st_size==plan['track_bytes']and sha(a.image)==plan['arms'][a.arm]['predicted']['sha256']
 files,records,misc=read_iso(a.image);assert files==expected and len(files)==1743 and len(records)==1874
 baseline=json.loads(a.directory_records.read_text())['iso9660_rockridge'];assert len(baseline)==len(records);pairs=0
 for before,after in zip(baseline,records):
  assert all(before[k]==after[k]for k in ['path','record_lba','record_offset','extent','is_directory'])
  b=bytes.fromhex(before['record_hex']);c=bytes.fromhex(after['record_hex']);assert len(b)==len(c)
  allow=set(range(10,18))if before['path']in source_refs else set()
  assert all(x==y or i in allow for i,(x,y)in enumerate(zip(b,c)))
  if b!=c:pairs+=1
 assert misc['PVD_blocks']==plan['layout']['PVD_blocks']and misc['tail_all_zero']
 base=local(plan['base_path'])
 with base.open('rb')as f:assert hashlib.sha256(f.read(32768)).hexdigest()==misc['IP_sha256']
 # Same cooked GDI and small tracks; no new IP/TOC recipe.
 for name in ['track01.bin','track02.raw','disc.gdi']:
  assert sha(a.image.parent/name)==sha(base.parent/name)
 report={'result':'PASS','arm':a.arm,'plan_sha256':sha(a.plan),'source':plan['source'],'ELF_sha256':plan['elf_sha256'],'track':{'path':str(a.image),'bytes':a.image.stat().st_size,'sha256':sha(a.image)},'all1743_LBAs_sizes_hashes':True,'directory_record_count':len(records),'changed_size_field_pairs':pairs,'all15_programme_exact':True,'primary_only_noJoliet':True,'smalltracks_GDI_exact':True,'metadata':misc,'files':files,'scope':'Static image/layout/source binding only. Candidate Package integrity, target functional/phase/LOD/look/resources and performance require their own acceptance. No guest started.'}
 with a.out.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps({k:v for k,v in report.items()if k not in ['files']}))
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in ['plan','image','baseline-manifest','directory-records','out']:ap.add_argument('--'+n,type=Path,required=True)
 ap.add_argument('--plan-sha256',required=True);ap.add_argument('--arm',choices=['M0','M1'],required=True);verify(ap.parse_args())
if __name__=='__main__':main()
