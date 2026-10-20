from pathlib import Path
import hashlib,json,re,struct,sys
oldmeta=json.loads(Path(sys.argv[1]).read_text());elf=Path(sys.argv[2]);src=Path(sys.argv[3]);dest=Path(sys.argv[4]);b=elf.read_bytes();assert b[:7]==b'\x7fELF\x01\x01\x01'
shoff=struct.unpack_from('<I',b,32)[0];ss,n=struct.unpack_from('<HH',b,46);assert ss==40
sections=[struct.unpack_from('<10I',b,shoff+i*ss)for i in range(n)];rows=[]
for sh in sections:
    if sh[1]!=2:continue
    st=sections[sh[6]];strings=b[st[4]:st[4]+st[5]];file=None
    for off in range(sh[4],sh[4]+sh[5],sh[9]):
        no,val,size,info,other,idx=struct.unpack_from('<IIIBBH',b,off);name=strings[no:strings.find(b'\0',no)].decode('utf8','replace')
        if info&15==4:file=name
        if val>=0x8c000000:rows.append(dict(file=file,name=name,address=val,size=size,kind=info&15,bind=info>>4))
old=oldmeta['symbols'];changes={};fixed={0x8c000000,0x8d000000,0x8cfff000,0x8cfffff0}
def mapped(addr):
    if addr in fixed:return addr
    choices=[r for r in old if r['kind']==1 and r['size']>0 and r['address']<=addr<r['address']+r['size']]
    assert choices,f'Unmapped original address {addr:08x}'
    choices.sort(key=lambda r:(r['size'],r['bind'],r['name']))
    o=choices[0];matches=[r for r in rows if (r['file'],r['name'],r['kind'])==(o['file'],o['name'],o['kind'])]
    assert len(matches)==1,(o,matches)
    nr=matches[0];assert nr['size']==o['size'],('Observed object ABI changed',o,nr)
    delta=addr-o['address'];new=nr['address']+delta
    changes[f'0x{addr:08x}']=dict(new=f'0x{new:08x}',file=o['file'],symbol=o['name'],offset=delta,size=o['size'])
    return new
text=src.read_text();text=re.sub(r'0x8[cCdD][0-9a-fA-F]{6}',lambda m:f'0x{mapped(int(m[0],16)):08x}',text)
# Existing observer counter blocks must retain their exact internal layout.
for base,count,stride in [(0x8c2dcc40,13,4)]:
    assert all(mapped(base+i*stride)==mapped(base)+i*stride for i in range(count))
elfsha=hashlib.sha256(b).hexdigest()
text=text.replace("and (cap/'flycast.log').exists():","and (cap/'flycast.log').exists() and (cap/'run-start.json').exists():")
text=text.replace("owner=json.loads((cap/'owned-process.json').read_text());",f"assert json.loads((cap/'run-start.json').read_text())['elf_sha256']=='{elfsha}', 'Exact candidate ELF identity required'\nowner=json.loads((cap/'owned-process.json').read_text());")
assert not dest.exists();dest.write_text(text)
receipt=dict(old_elf_sha256=oldmeta['sha256'],new_elf_sha256=elfsha,new_elf=str(elf),source=str(src),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),output=str(dest),output_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),addresses=changes)
dest.with_suffix('.symbols.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(mapped=len(changes),elf=elfsha,same_addresses=all(k==v['new']for k,v in changes.items()))))
