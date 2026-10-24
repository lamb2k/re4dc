"""Pure extracted ELF32LE/SH metadata functions; no CLI, build, SDK or write path."""
from pathlib import Path
import hashlib,struct
cache={};fresh_bytes=0

def sha(path):
 global fresh_bytes
 p=Path(path);before=p.stat();key=(str(p),before.st_size,before.st_mtime_ns,before.st_ino)
 if key in cache:return cache[key]
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b);fresh_bytes+=len(b)
 after=p.stat();assert (before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino),str(p)+' changed during hash'
 cache[key]=h.hexdigest();return cache[key]


def elf(path,raw=False):
 """ELF32LE parser; extracts metadata/hash only, never executes a provider tool."""
 p=Path(path);b=p.read_bytes();assert b[:7]==b'\x7fELF\x01\x01\x01'
 h=struct.unpack_from('<16sHHIIIIIHHHHHH',b);assert h[2]==42 and h[8]==52 and h[11]==40
 typ,machine,entry,phoff,shoff,phents,phnum,shnum,namesidx=h[1],h[2],h[4],h[5],h[6],h[9],h[10],h[12],h[13]
 sections=[struct.unpack_from('<IIIIIIIIII',b,shoff+i*40) for i in range(shnum)];ss=sections[namesidx];names=b[ss[4]:ss[4]+ss[5]]
 def string(buf,at):return buf[at:].split(b'\0',1)[0].decode('utf-8')
 rows=[]
 for s in sections:rows.append(dict(name=string(names,s[0]),type=s[1],flags=s[2],addr=s[3],offset=s[4],bytes=s[5],link=s[6],align=s[8],entsize=s[9]))
 symbols=[]
 for s in rows:
  if s['type']!=2:continue
  st=rows[s['link']];strings=b[st['offset']:st['offset']+st['bytes']];assert s['entsize']==16
  for at in range(s['offset'],s['offset']+s['bytes'],16):
   name,value,size,info,other,index=struct.unpack_from('<IIIBBH',b,at);n=string(strings,name)
   if n and info&15 not in (3,4):symbols.append(dict(name=n,value=value,bytes=size,info=info,index=index))
 allocated=[s for s in rows if s['flags']&2]
 sizes={'text':sum(s['bytes'] for s in allocated if s['type']!=8 and not s['flags']&1),'data':sum(s['bytes'] for s in allocated if s['type']!=8 and s['flags']&1),'bss':sum(s['bytes'] for s in allocated if s['type']==8)}
 result=dict(type=typ,machine=machine,entry=entry,sha256=sha(p),allocated_bytes=sum(s['bytes'] for s in allocated),sizes=sizes,allocated_sections=[{k:s[k] for k in ['name','type','flags','addr','bytes','align']} for s in allocated],addresses={s['name']:s['value'] for s in symbols if s['name'] in ['_end','_edata','_etext','__bss_start','__bss_end']},meaningful_symbols=len(symbols),undefined_gc_symbols=[s['name'] for s in symbols if s['index']==0 and ('gcasset' in s['name'] or 'motion_unknown' in s['name'])],defined_gc_symbols=[s['name'] for s in symbols if s['index'] and ('gcasset' in s['name'] or 'motion_unknown' in s['name'])])
 if typ==1:result['meaningful_symbol_rows']=symbols
 if raw:
  ph=[struct.unpack_from('<IIIIIIII',b,phoff+i*phents) for i in range(phnum)];spans=[]
  for s in allocated:
   if not s['bytes'] or s['type']==8 or s['name']=='.stack':continue
   load=[v for v in ph if v[0]==1 and s['addr']>=v[2] and s['addr']+s['bytes']<=v[2]+v[4] and s['offset']>=v[1] and s['offset']+s['bytes']<=v[1]+v[4]]
   assert len(load)==1,(p,s['name'],'no unique load segment');v=load[0];assert s['addr']-v[2]==s['offset']-v[1]
   spans.append((v[3]+s['addr']-v[2],s['offset'],s['bytes'],s['name']))
  spans.sort();assert spans;cursor=spans[0][0];base=cursor;digest=hashlib.sha256();zeros=bytes(4096)
  for addr,off,n,name in spans:
   assert addr>=cursor,(p,name,'overlap')
   while cursor<addr:take=min(addr-cursor,len(zeros));digest.update(zeros[:take]);cursor+=take
   digest.update(memoryview(b)[off:off+n]);cursor+=n
  result['raw_from_ELF']={'base':base,'end':cursor,'bytes':cursor-base,'sha256':digest.hexdigest(),'sections':[s[3] for s in spans]}
 return result


def nm_addresses(path):
 wanted=['_end','_edata','_etext','__bss_start','__bss_end'];out={}
 for line in Path(path).read_text().splitlines():
  a=line.split()
  if len(a)>=3 and a[-1] in wanted:out[a[-1]]=int(a[0],16)
 return out


def size_default(text):
 for line in text.splitlines():
  a=line.split()
  if len(a)>=6 and all(x.isdigit() for x in a[:4]):return dict(zip(['text','data','bss'],map(int,a[:3])))
 raise AssertionError('no default size row')


def section_text(path):
 out={}
 for line in Path(path).read_text().splitlines():
  a=line.split()
  if len(a)==3 and a[0].startswith('.') and a[1].isdigit() and a[2].isdigit():out[a[0]]=(int(a[1]),int(a[2]))
 return out
