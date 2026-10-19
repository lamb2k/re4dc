#!/usr/bin/env python3
"""Append verified, relocated runtime overlays to an ELF input for unchanged hwsim.
Requires one stable observed load per module; refuses overlaps or releases.
"""
import argparse,hashlib,json,re,struct
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--elf',type=Path,required=True);p.add_argument('--boot',type=Path,required=True)
p.add_argument('--program',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args();assert not a.out.exists()
raw=a.elf.read_bytes();assert raw[:6]==b'\x7fELF\x01\x01';b=bytearray(raw)
phoff=struct.unpack_from('<I',b,28)[0];phsize,phnum=struct.unpack_from('<HH',b,42);assert phsize==32
headers=[struct.unpack_from('<8I',b,phoff+i*phsize) for i in range(phnum)]
shoff=struct.unpack_from('<I',b,32)[0];shsize,shnum,shstr=struct.unpack_from('<HHH',b,46)
sections=[struct.unpack_from('<10I',b,shoff+i*shsize) for i in range(shnum)]
ss=sections[shstr];strings=b[ss[4]:ss[4]+ss[5]]
textsec=next(s for s in sections if strings[s[0]:].split(b'\0',1)[0]==b'.text')
text=raw[textsec[4]:textsec[4]+(textsec[5]&~3)]
def fnv(data):
 assert len(data)%4==0
 h=2166136261
 for (v,) in struct.iter_unpack('<I',data):h=((h^v)*16777619)&0xffffffff
 return h
ident=(fnv(text),len(text))
lograw=a.boot.read_bytes();log=lograw.decode('utf-16' if lograw[:2] in [b'\xff\xfe',b'\xfe\xff'] else 'utf-8',errors='replace')
loads=re.findall(r'route overlay: (\w+) load (\d+) (\d+) B \((\d+) relocs\) at ([0-9a-fA-F]{8})',log)
assert loads,'no exact runtime overlay loads found'
assert not re.search(r'route overlay: .* (?:release|free|unlink)',log),'overlay lifetime changed; interval-specific image needed'
ranges=[(h[2],h[2]+h[4],'main ELF') for h in headers if h[0]==1 and h[4]]
seen=set();proof=[]
for name,load,size,nrel,addr in loads:
 assert name not in seen and int(load)==1,'multiple observed loads require interval qualification'
 seen.add(name);vaddr=int(addr,16);ovl=a.program/(name+'.ovl');d=ovl.read_bytes();h=struct.unpack_from('<16I',d)
 assert h[:2]==(0x4f344552,1)
 assert h[2]==int(size) and h[3]==int(nrel) and len(d)==64+h[2]+h[3]*4
 assert h[14:16]==ident, f'{name}: wrong main image identity'
 image=bytearray(d[64:64+h[2]]);rel=d[64+h[2]:]
 assert fnv(image)==h[12] and fnv(rel)==h[13],f'{name}: checksum mismatch'
 delta=(vaddr-h[4])&0xffffffff
 for (at,) in struct.iter_unpack('<I',rel):
  assert at%4==0 and at+4<=len(image)
  value=struct.unpack_from('<I',image,at)[0];assert h[4]<=value<=h[4]+h[2]
  struct.pack_into('<I',image,at,(value+delta)&0xffffffff)
 assert 0x8c000000<=vaddr and vaddr+len(image)<=0x8d000000
 assert not any(vaddr<end and start<vaddr+len(image) for start,end,_ in ranges),'overlapping loaded images'
 while len(b)%4:b.append(0)
 offset=len(b);b.extend(image);headers.append((1,offset,vaddr,vaddr,len(image),len(image),5,4));ranges.append((vaddr,vaddr+len(image),name))
 proof.append(dict(module=name,program_sha256=hashlib.sha256(d).hexdigest(),runtime_base=hex(vaddr),link_base=hex(h[4]),image_bytes=len(image),relocations=h[3],relocated_sha256=hashlib.sha256(image).hexdigest()))
while len(b)%4:b.append(0)
newph=len(b)
for h in headers:b.extend(struct.pack('<8I',*h))
struct.pack_into('<I',b,28,newph);struct.pack_into('<H',b,44,len(headers))
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes(b)
manifest=dict(source_elf_sha256=hashlib.sha256(raw).hexdigest(),boot_sha256=hashlib.sha256(lograw).hexdigest(),augmented_elf_sha256=hashlib.sha256(b).hexdigest(),main_image_id=ident,overlays=proof,limitations=['Overlay mutable data are initial relocated bytes, not runtime data; simulator only reads instruction bytes.','BIOS/trampoline instructions outside both main ELF and verified overlays remain uncovered.','One stable load per module required; no timing-model code was changed.'])
a.out.with_suffix('.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))
