"""Read-only ELF32 SH evidence; no native actions or file access at import."""
import hashlib,struct
class ELF:
 def __init__(self,data):
  self.data=data
  if data[:6]!=b'\x7fELF\x01\x01':raise ValueError('ELF32 little-endian required')
  h=struct.unpack_from('<16sHHIIIIIHHHHHH',data);self.type=h[1];self.machine=h[2]
  if(self.type,self.machine)!=(2,42):raise ValueError('actual final SH EXEC ELF required')
  self.sections=[];raw=[struct.unpack_from('<IIIIIIIIII',data,h[6]+i*h[11])for i in range(h[12])];names=raw[h[13]];strings=data[names[4]:names[4]+names[5]]
  for row in raw:
   end=strings.find(b'\0',row[0]);name=strings[row[0]:end].decode();self.sections.append(dict(name=name,type=row[1],flags=row[2],address=row[3],offset=row[4],size=row[5],link=row[6],entry_size=row[9]))
  self.symbols={}
  for section in self.sections:
   if section['type']!=2:continue
   table=self.sections[section['link']];strings=data[table['offset']:table['offset']+table['size']]
   for offset in range(section['offset'],section['offset']+section['size'],section['entry_size']):
    n,v,size,info,other,shndx=struct.unpack_from('<IIIBBH',data,offset)
    if n:
     end=strings.find(b'\0',n);name=strings[n:end].decode();self.symbols[name]=dict(address=v,size=size,section=shndx)
 def section(self,name):
  rows=[s for s in self.sections if s['name']==name]
  if len(rows)!=1:raise ValueError('unique ELF section required: '+name)
  row=rows[0];return row,self.data[row['offset']:row['offset']+row['size']]

def fnv(data):
 value=2166136261
 if len(data)%4:raise ValueError('whole words required')
 for offset in range(0,len(data),4):value=((value^struct.unpack_from('<I',data,offset)[0])*16777619)&0xffffffff
 return value

def initialized_raw(elf):
 alloc=[s for s in elf.sections if s['flags']&2 and s['type']!=8 and s['size']and s['name']!='.stack']
 if not alloc:raise ValueError('initialized allocated sections absent')
 alloc.sort(key=lambda s:s['address']);low=alloc[0]['address'];high=max(s['address']+s['size']for s in alloc)
 if not 0x8c000000<=low<high<=0x8d000000:raise ValueError('raw initialized image outside16MiB main RAM')
 previous=low;rebuilt=bytearray(high-low)
 for section in alloc:
  if section['address']<previous:raise ValueError('overlapping initialized sections')
  data=elf.data[section['offset']:section['offset']+section['size']]
  if len(data)!=section['size']:raise ValueError('truncated initialized section')
  rebuilt[section['address']-low:section['address']-low+section['size']]=data;previous=section['address']+section['size']
 return bytes(rebuilt),dict(image_format='unscrambled-gdrom',address_low=hex(low),address_high=hex(high),bytes=len(rebuilt),exact_allocated_initialized_sections_equal=True,excluded_NOBITS=True,excluded_stack=True,byte_order='little-endian',gap_fill=0,sections=[dict(name=x['name'],address=hex(x['address']),size=x['size'],file_offset=x['offset'],flags=x['flags'],type=x['type'])for x in alloc])

def verify_raw(elf_bytes,raw_bytes):
 image,evidence=initialized_raw(ELF(elf_bytes))
 if image!=raw_bytes:raise ValueError('unscrambled raw bytes differ from actual ELF initialized image')
 evidence.update(elf_sha256=hashlib.sha256(elf_bytes).hexdigest(),raw_sha256=hashlib.sha256(raw_bytes).hexdigest())
 return evidence
