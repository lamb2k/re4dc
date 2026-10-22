#!/usr/bin/env python3
"""Hash a texpack composition as a stream. No full pack or image is written."""
from pathlib import Path
import hashlib,json,struct,sys,zlib

def main():
 O=Path(sys.argv[1]);r=json.loads((O/'conversion-receipt.json').read_text());P=Path('/root/re4data/private/texture-canonical1004-20261021/tex.pak');source_sha=hashlib.sha256()
 with P.open('rb')as f:
  while b:=f.read(1024*1024):source_sha.update(b)
 assert source_sha.hexdigest()=='89ef27a767fcee529c3ac6ca07fef5a8f9a3e2515f38eda63b61c8929fb0be62'
 with P.open('rb')as f:
  head=f.read(2048);version,count,ioff,doff,crc=struct.unpack_from('<5I',head,8);assert count==6537;f.seek(ioff);idx=f.read(doff-ioff);assert zlib.crc32(idx)&0xffffffff==crc
  rows={tuple(struct.unpack_from('<4I',idx,16*i)[:2]):dict(offset=struct.unpack_from('<4I',idx,16*i)[2],bytes=struct.unpack_from('<4I',idx,16*i)[3],source='canonical1004')for i in range(count)}
  for x in r['selected']:
   key=tuple(int(y,16)for y in x['scoped_key'].split('-'));assert key not in rows;rows[key]=dict(bytes=x['package_bytes'],source=x['relative_path'],sha256=x['candidate_sha256'])
  keys=sorted(rows);assert len(keys)==6952 and len(keys)<=8192;indexbytes=(16*len(keys)+2047)//2048*2048;dataoff=2048+indexbytes;offset=dataoff;index=bytearray()
  for key in keys:
   row=rows[key];row['new_offset']=offset;index+=struct.pack('<4I',*key,offset,row['bytes']);offset+=(row['bytes']+2047)//2048*2048
  index+=bytes(indexbytes-len(index));header=b'RE4PAK1\0'+struct.pack('<5I',1,len(keys),2048,dataoff,zlib.crc32(index)&0xffffffff);header+=bytes(2048-len(header));digest=hashlib.sha256(header+index);manifest=[]
  for key in keys:
   row=rows[key]
   if row['source']=='canonical1004':f.seek(row['offset']);b=f.read(row['bytes']);assert len(b)==row['bytes']
   else:b=(O/row['source']).read_bytes();assert hashlib.sha256(b).hexdigest()==row['sha256']
   assert b[:8]==b'RE4DCTX\0';digest.update(b);digest.update(bytes((-len(b))%2048));manifest.append(dict(key='%08x-%08x'%key,offset=row['new_offset'],bytes=row['bytes'],sha256=hashlib.sha256(b).hexdigest(),source=row['source']))
 report=dict(status='VIRTUAL_ONLY_UNWRITTEN_PENDING_MAIN_SELECTION',base_pack_sha256=source_sha.hexdigest(),preserved_current_members_byteexact=6537,appended_members=415,members=6952,mips_if_all_selected=1419,index_sectors=indexbytes//2048,index_capacity=indexbytes//16,index_crc32=zlib.crc32(index)&0xffffffff,data_offset=dataoff,virtual_pack_bytes=offset,virtual_pack_sha256=digest.hexdigest(),archive_growth_bytes=offset-P.stat().st_size,manifest=manifest,limits=['No fullpack/image written; new415 data only.','Preserves all current6537 entries including existing36world/20actor, originals retained.','Cannot replace active1004 until parent selects cohort/source policy/lifecycle/appearance/resource gates; asset archive growth needs a fresh image extent plan.'])
 (O/'virtual-pack-manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in('members','index_sectors','virtual_pack_bytes','virtual_pack_sha256','archive_growth_bytes')}))
if __name__=='__main__':main()