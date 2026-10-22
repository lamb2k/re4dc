#!/usr/bin/env python3
"""Read-only exact SH4 ELF/load/raw-disc-tail admission; no programme creation."""
import argparse,hashlib,json,struct
from pathlib import Path
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inspect(blob,rawbytes,layout):
 if len(blob)<52 or blob[:6]!=b'\x7fELF\x01\x01':raise ValueError('requires ELF32 little endian')
 typ,machine,ver,entry,phoff,shoff,flags,eh,phsize,phn,shsize,shn,shstr=struct.unpack_from('<HHIIIIIHHHHHH',blob,16)
 if machine!=42 or typ!=2 or eh!=52 or phsize!=32 or shsize!=40:raise ValueError('requires linked SH4 executable/header widths')
 if phoff+phsize*phn>len(blob) or shoff+shsize*shn>len(blob):raise ValueError('ELF table truncated')
 loads=[]
 for i in range(phn):
  t,off,va,pa,fs,ms,fl,al=struct.unpack_from('<8I',blob,phoff+32*i)
  if t!=1:continue
  if not 0<=fs<=ms or off+fs>len(blob) or not 0x8c000000<=va<=va+ms<=0x8d000000:raise ValueError('PT_LOAD outside file/mainRAM or filesz>memsz')
  loads.append({'index':i,'offset':off,'vaddr':va,'paddr':pa,'file_bytes':fs,'memory_bytes':ms,'flags':fl,'align':al,'virtual_file_end':va+fs,'virtual_memory_end':va+ms})
 if not loads or not any(r['flags']&1 and r['vaddr']<=entry<r['virtual_memory_end'] for r in loads):raise ValueError('entry outside executable load')
 sections=[struct.unpack_from('<10I',blob,shoff+40*i) for i in range(shn)];symbols={}
 for s in sections:
  if s[1]!=2:continue
  if s[9]!=16 or s[6]>=len(sections):raise ValueError('bad symbol width/string link')
  strings=sections[s[6]];names=blob[strings[4]:strings[4]+strings[5]]
  if len(names)!=strings[5] or s[4]+s[5]>len(blob):raise ValueError('symbol/string table truncated')
  for pos in range(s[4],s[4]+s[5],16):
   no,value,size,info,other,index=struct.unpack_from('<IIIBBH',blob,pos)
   if no>=len(names):raise ValueError('symbol name outside strings')
   name=names[no:names.find(b'\0',no)].decode('utf8','replace')
   if name in ('_end','__end','end','_pG','_pPL') and index:symbols.setdefault(name,[]).append({'value':value,'bytes':size,'binding':info>>4,'type':info&15,'section':index})
 endhits=symbols.get('_end',[])
 if len(endhits)!=1:raise ValueError('exact _end symbol missing/ambiguous')
 end=endhits[0]['value']
 if not 0x8c000000<end<=0x8d000000:raise ValueError('_end outside main RAM')
 boot=layout['selected_paths']['/1ST_READ.BIN'];start=boot['after_extent'];maxbytes=layout['cooked_track_bytes']-(start-45000)*2048;sectors=(rawbytes+2047)//2048;newvol=max(504000,start-45000+sectors)
 if not 0<rawbytes<=maxbytes or newvol>504150:raise ValueError('programme exceeds allocated verified zero-tail capacity')
 return {'ELF32_little_SH4':True,'entry':entry,'PT_LOAD':loads,'selected_symbols':symbols,'_end':end,'mainRAM_static_span_end':max(end,max(r['virtual_memory_end'] for r in loads)),'raw_programme_bytes':rawbytes,'programme_LBA':start,'maximum_tail_capacity_bytes':maxbytes,'programme_rounded_sectors':sectors,'PVD_volume_blocks':newvol,'original150_tail_sectors_consumed':max(0,newvol-504000),'remaining_fulltrack_tail_sectors':504150-newvol,'all1743_LBAs_preserved_if_other_payloads_fit':True,'scope':'Linked static load ranges/raw-tail fit only. Not arena free/largest/contiguous/stack/high-water/runtime resource acceptance.'}
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--elf',type=Path,required=True);ap.add_argument('--raw',type=Path,required=True);ap.add_argument('--layout',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();blob=a.elf.read_bytes();result=inspect(blob,a.raw.stat().st_size,json.loads(a.layout.read_text()));lo=min(r['vaddr'] for r in result['PT_LOAD'] if r['file_bytes']);hi=max(r['virtual_file_end'] for r in result['PT_LOAD']);flat=bytearray(hi-lo)
 for r in result['PT_LOAD']:flat[r['vaddr']-lo:r['virtual_file_end']-lo]=blob[r['offset']:r['offset']+r['file_bytes']]
 if len(flat)!=a.raw.stat().st_size or hashlib.sha256(flat).hexdigest()!=digest(a.raw):raise ValueError('raw programme differs from exact PT_LOAD file bytes/zero holes')
 result.update(ELF_sha256=digest(a.elf),raw_sha256=digest(a.raw),raw_exact_ELF_PT_LOAD=True,raw_load_base=lo,layout_sha256=digest(a.layout),source='REQUIRES independent current source/compile-input/flags receipt; no inferred source from ELF filename')
 with a.out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({k:result[k] for k in ('ELF_sha256','raw_sha256','_end','raw_programme_bytes','PVD_volume_blocks','remaining_fulltrack_tail_sectors')}))
if __name__=='__main__':main()
