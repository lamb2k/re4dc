from pathlib import Path
import json,hashlib,sys,shutil
R=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/castle18-20261018/Test21');D=R/'recovered-j-content-20261021';O=D/'exact-reconstruction';assert not O.exists();assert shutil.disk_usage('/mnt/c').free>=18*1024**3+64*1024**2;O.mkdir();iso=D/'master/track03.iso';root=Path('/root/probe/castle21-recovered-j-content-20261021/tree');want=json.loads((D/'master/base-manifest.json').read_text());sys.path.insert(0,'/root/probe/codex-castle18/port/dreamcast/tools/d367/fullplay');import fp_iso
tr=fp_iso.Track(iso,45000);rows=[]
for path,ext,size in fp_iso.files(tr):
 k=path.lstrip('/')
 if ext<45000:assert k in ['dc/warp.txt','dc/padscript.txt','dc/w11.txt'];continue
 assert size==want[k]['size'];rows.append({'offset':(ext-45000)*2048,'size':size,'path':k,'sha256':want[k]['sha256']})
rows.sort(key=lambda r:r['offset']);last=0;gaps=[];stream=hashlib.sha256();gapfile=O/'metadata-and-padding.bin';gap_pos=0
with iso.open('rb')as image,gapfile.open('xb')as g:
 for row in rows:
  pos=row['offset'];assert pos>=last,('Overlapping file extents require separate handling',row)
  if pos>last:
   image.seek(last);b=image.read(pos-last);assert len(b)==pos-last;g.write(b);stream.update(b);gaps.append({'iso_offset':last,'bytes':len(b),'metadata_offset':gap_pos});gap_pos+=len(b)
  p=root/row['path'];assert p.stat().st_size==row['size'];h=hashlib.sha256()
  with p.open('rb')as f:
   while b:=f.read(1024*1024):h.update(b);stream.update(b)
  assert h.hexdigest()==row['sha256'];last=pos+row['size']
 if last<iso.stat().st_size:
  image.seek(last);b=image.read();g.write(b);stream.update(b);gaps.append({'iso_offset':last,'bytes':len(b),'metadata_offset':gap_pos});gap_pos+=len(b)
expected=(D/'master/track03.sha256').read_text().strip();assert stream.hexdigest()==expected;proof={'scope':'Exact byte reconstruction metadata and padding for recovered-J NEW image. Read-only image/source, no additional image copy, master, guest, source change or old-J state retarget.','image_sha256':expected,'image_bytes':iso.stat().st_size,'content_files':len(rows),'metadata_padding_bytes':gapfile.stat().st_size,'metadata_padding_sha256':hashlib.file_digest(gapfile.open('rb'),'sha256').hexdigest(),'stream_reconstruction_sha256':stream.hexdigest(),'stream_reconstruction_PASS':True,'file_extents':rows,'metadata_padding_ranges':gaps,'source_tree':str(root),'original_J_iso_recovered':False}
(O/'receipt.json').write_text(json.dumps(proof,indent=1)+'\n');print({k:v for k,v in proof.items()if k not in ['file_extents','metadata_padding_ranges']})