from pathlib import Path
import json,struct,sys,hashlib
p=Path(sys.argv[1]);b=p.read_bytes();assert b[:7]==b'\x7fELF\x01\x01\x01'
shoff=struct.unpack_from('<I',b,32)[0];ss,n=struct.unpack_from('<HH',b,46);assert ss==40
sections=[struct.unpack_from('<10I',b,shoff+i*ss) for i in range(n)]
rows=[]
for sh in sections:
    if sh[1]!=2:continue
    st=sections[sh[6]];strings=b[st[4]:st[4]+st[5]];file=None
    for off in range(sh[4],sh[4]+sh[5],sh[9]):
        no,val,size,info,other,idx=struct.unpack_from('<IIIBBH',b,off);name=strings[no:strings.find(b'\0',no)].decode('utf8','replace')
        if info&15==4:file=name
        if val>=0x8c000000:rows.append(dict(file=file,name=name,address=val,size=size,kind=info&15,bind=info>>4))
out=dict(elf=str(p),sha256=hashlib.sha256(b).hexdigest(),symbols=rows)
Path(sys.argv[2]).write_text(json.dumps(out,indent=1)+'\n')
for r in rows:
    if ('stats' in r['name'] or 'bindings' in r['name']) and r['address']==0x8c3f004c or r['address'] in [0x8c3f018c,0x8c360558,0x8c353ec0,0x8c353b78]:print(json.dumps(r))
