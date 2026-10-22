"""Read-only ELF text/RE4O binding validation for the diagnostic build."""
import hashlib,struct
from pathlib import Path

def fnv_words(blob):
 assert len(blob)%4==0;h=2166136261
 for (word,) in struct.iter_unpack('<I',blob):h=((h^word)*16777619)&0xffffffff
 return h

def elf_text(path):
 blob=Path(path).read_bytes();assert blob[:6]==b'\x7fELF\x01\x01';at=struct.unpack_from('<I',blob,32)[0];step,count,names=struct.unpack_from('<3H',blob,46);heads=[struct.unpack_from('<10I',blob,at+i*step) for i in range(count)];table=heads[names];strings=blob[table[4]:table[4]+table[5]];found=[h for h in heads if strings[h[0]:].split(b'\0',1)[0]==b'.text'];assert len(found)==1;head=found[0];return blob[head[4]:head[4]+head[5]]

def overlay_bytes(blob,text):
 assert len(blob)>=64;h=struct.unpack_from('<16I',blob);assert h[0]==0x4f344552 and h[1]==1;size,relocs=h[2:4];assert len(blob)==64+size+relocs*4;image=blob[64:64+size];rel=blob[64+size:];assert fnv_words(image)==h[12] and fnv_words(rel)==h[13];trim=text[:len(text)&~3];assert [h[14],h[15]]==[fnv_words(trim),len(trim)],'Overlay main-image binding differs'
 return {'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest(),'image_bytes':size,'relocations':relocs,'image_fnv':h[12],'relocation_fnv':h[13],'main_text_fnv':h[14],'main_text_bytes':h[15]}