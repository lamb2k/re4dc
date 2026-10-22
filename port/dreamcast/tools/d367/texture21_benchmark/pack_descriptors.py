#!/usr/bin/env python3
"""Read selected immutable member descriptors from the actual frozen base pack; no extraction."""
import argparse,hashlib,json,struct,zlib
from pathlib import Path

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--pack',type=Path,required=True);a.add_argument('--plan',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a=a.parse_args();plan=json.loads((a.plan/'inputs-final/plan-inputs.json').read_text());h=hashlib.sha256()
 with a.pack.open('rb') as f:
  for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
 assert h.hexdigest()==plan['B']['pack']['sha256']
 with a.pack.open('rb') as f:
  header=f.read(2048);assert header[:8]==b'RE4PAK1\0';ver,n,at,data,crc=struct.unpack_from('<5I',header,8);assert ver==1 and at==2048 and n==6501;index=f.read(data-at);assert zlib.crc32(index)&0xffffffff==crc
  entries={('%08x-%08x'%(k0,k1)):(off,size) for k0,k1,off,size in struct.iter_unpack('<4I',index[:n*16])};out=[]
  for s in plan['selected']:
   key=s['original_key'];offset,size=entries[key];f.seek(offset);blob=f.read(size);assert len(blob)==size and blob[:8]==b'RE4DCTX\0';H=struct.unpack_from('<8s10I',blob);assert H[4]==1 and H[3]==96;T=struct.unpack_from('<64s8I',blob,H[5]);payload=blob[H[6]:H[6]+H[7]];body_crc=zlib.crc32(blob[H[2]:])&0xffffffff;data_crc=zlib.crc32(payload)&0xffffffff;assert H[8] in (body_crc,data_crc);crc_rule='full body' if H[8]==body_crc else 'legacy texel-only'
   out.append({'key':key,'pack_offset':offset,'member_bytes':size,'member_sha256':hashlib.sha256(blob).hexdigest(),'matches_earlier_source_receipt':hashlib.sha256(blob).hexdigest()==s['source_sha256'],'header_payload_crc32':H[8],'crc_rule':crc_rule,'material':T[0].split(b'\0')[0].decode('ascii'),'width':T[1],'height':T[2],'format':T[3],'data_size':T[5],'flags':T[6],'payload':T[7],'rounded_request':(T[5]+31)&~31})
 report={'pack_sha256':h.hexdigest(),'pack_bytes':a.pack.stat().st_size,'member_count':n,'index_crc32':crc,'selected':out,'scope':'Actual frozen current948 base member bytes/header/descriptors/material/payload CRC; not runtime residency or draw use'}
 with a.out.open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps({'keys':len(out),'matches_earlier_source':sum(x['matches_earlier_source_receipt'] for x in out),'physical_forms':sorted(set((x['width'],x['height'],x['format'],x['flags'],x['payload'],x['data_size']) for x in out))}))
if __name__=='__main__':main()
