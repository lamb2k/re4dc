from pathlib import Path
import subprocess,re,json,hashlib
L=Path('/mnt/c/Game Dev/Emulators/codex-lanes/castle18');E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/castle18-20261018/Test21/builds/c21jmW/re4dc-game.elf')
p=subprocess.Popen(['/opt/toolchains/dc/sh-elf/bin/sh-elf-readelf','--debug-dump=info',str(E)],stdout=subprocess.PIPE,text=True)
targets={'Message','MessageControl','cCoord','cActionButton','ActBtnWork','SceAtSysWork','EmListData','GlobalWork','cEm','cUnit','cEmMgr','cManager<cEm>','MessageData'};out={};cur=None;die=[]
def flush(lines):
 global cur
 if not lines:return
 m=re.match(r'\s*<(\d+)><([^>]+)>:.*\((DW_TAG_\w+)\)',lines[0])
 if not m:return
 depth,off,tag=int(m[1]),m[2],m[3];nm=next((v.split(': ',1)[1].split('): ')[-1].strip()for v in lines[1:]if'DW_AT_name 'in v),None)
 if cur and depth<=cur['depth']:cur=None
 if tag in ['DW_TAG_class_type','DW_TAG_structure_type']and nm in targets:
  size=next((int(v.split(':')[-1])for v in lines if'DW_AT_byte_size'in v),None)
  if size:cur=dict(name=nm,depth=depth,die=off,byte_size=size,members={});out.setdefault(nm,cur)
 elif cur and depth==cur['depth']+1 and tag=='DW_TAG_member'and nm:
  loc=next((v.split(':')[-1].strip()for v in lines if'DW_AT_data_member_location'in v),None)
  typ=next((v.split(':')[-1].strip()for v in lines if'DW_AT_type 'in v),None)
  if loc is not None:cur['members'][nm]=dict(offset=loc,type_die=typ)
for line in p.stdout:
 if re.match(r'\s*<\d+><',line):flush(die);die=[line.rstrip()]
 else:die.append(line.rstrip())
flush(die);assert p.wait()==0
r=dict(scope='Exact frozen ELF DWARF member offsets only; type widths and executable sites additionally checked in ABI receipt.',elf_sha256=hashlib.sha256(E.read_bytes()).hexdigest(),classes=out)
f=L/'controlled-ch32-drain014-frozen-DWARF.json';f.write_text(json.dumps(r,indent=2)+'\n');print({k:(v['byte_size'],len(v['members']))for k,v in out.items()})
