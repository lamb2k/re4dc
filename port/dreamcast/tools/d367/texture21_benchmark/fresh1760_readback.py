"""Independent relocated ISO readback. No writer buffer or guest dependency."""
import hashlib,json,mmap,struct
from pathlib import Path
from plan_fresh1760_disc import directory,LBA0,digest,require
from mipmap_pair_plan import local,sha

def expected_files(plan,arm):
 ref=plan['baseline'];require(sha(local(ref['path']))==ref['sha256'],'baseline fullreadback changed');files=json.loads(local(ref['path']).read_text())['files'];files={k:dict(v)for k,v in files.items()}
 require(len(files)==plan['file_count'],'baseline file count')
 for r in plan['arms'][arm]['append']:
  require(r['path']in files,'no added ISO paths');files[r['path']]=dict(extent=LBA0+r['start']//2048,bytes=r['bytes'],sha256=r['sha256'])
 return files

def verify_image(path,plan,arm,guard):
 """Reopen bytes, walk primary directories, hash every referenced member and image."""
 expected=expected_files(plan,arm);base=local(plan['base']['path']);require(sha(base)==plan['base']['sha256'],'independent base identity');need=plan['arms'][arm]['predicted'];guard.check(force=True);require(path.stat().st_size==need['bytes'],'image length')
 with path.open('rb')as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)as view,base.open('rb')as original,mmap.mmap(original.fileno(),0,access=mmap.ACCESS_READ)as old:
  actual,records,misc=directory(view);_,before,oldmisc=directory(old);require(len(actual)==plan['file_count']and len(records)==plan['record_count']and set(actual)==set(expected),'ISO file/directory census')
  image_sha=hashlib.sha256()
  for start in range(0,len(view),1048576):guard.check();image_sha.update(view[start:start+1048576])
  require(image_sha.hexdigest()==need['sha256'],'whole image expected SHA')
  checked={}
  for path_name,r in actual.items():
   e=expected[path_name];require((r['extent'],r['bytes'])==(e['extent'],e['bytes']),'relocated or unchanged file extent differs '+path_name);off=(r['extent']-LBA0)*2048;require(off>=0 and off+r['bytes']<=len(view),'file outside image');h=hashlib.sha256()
   for pos in range(off,off+r['bytes'],1048576):guard.check();h.update(view[pos:min(pos+1048576,off+r['bytes'])])
   require(h.hexdigest()==e['sha256'],'member SHA differs '+path_name);checked[path_name]=e
  changed=set(r['path']for r in plan['arms'][arm]['append']);require(len(records)==len(before),'directory rows changed')
  for a,b in zip(before,records):
   require(all(a[k]==b[k]for k in ['path','record_lba','record_offset','is_directory']),'directory identity/position changed');x=bytes.fromhex(a['record_hex']);y=bytes.fromhex(b['record_hex']);allow=set(range(2,18))if a['path']in changed else set();require(len(x)==len(y)and all(v==w or i in allow for i,(v,w)in enumerate(zip(x,y))),'unexpected directory byte changed')
  oldp=bytes(old[16*2048:17*2048]);newp=bytes(view[16*2048:17*2048]);require(all(a==b or 80<=i<88 for i,(a,b)in enumerate(zip(oldp,newp))),'unexpected PVD bytes');require(misc['PVD_blocks']==len(view)//2048 and len(view)%2048==0,'new complete PVD/track size');require(view[:32768]==old[:32768],'IP/boot prefix changed')
 for name,r in plan['smalltracks'].items():require(sha(path.parent/name)==r['sha256']and(path.parent/name).stat().st_size==r['bytes'],'smalltrack/GDI changed')
 guard.check(force=True)
 return dict(result='PASS_INDEPENDENT_RELOCATED_IMAGE_READBACK',arm=arm,bytes=need['bytes'],sha256=need['sha256'],all_file_SHA=True,files=checked,file_count=len(checked),directory_records=len(records),explicit_relocated_paths=sorted(changed),PVD_blocks=misc['PVD_blocks'],IP_and_smalltracks_exact=True,source=plan['source'],programme_sha256=plan['programme']['programme_sha256'],ELF_sha256=plan['programme']['ELF']['sha256'],held_originals=plan['held'],scope='Static image proof only; no boot, target format/look/phase/performance/hardware acceptance')
