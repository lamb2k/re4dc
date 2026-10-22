from pathlib import Path
import subprocess,re,json,hashlib
L=Path('/mnt/c/Game Dev/Emulators/codex-lanes/castle18');E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/castle18-20261018/Test21/builds/c21jmW/re4dc-game.elf');out={};stack={};die=[];vars=[]
def flush(lines):
 if not lines:return
 m=re.match(r'\s*<(\d+)><([^>]+)>:.*\((DW_TAG_\w+)\)',lines[0])
 if not m:return
 dep,off,tag=int(m[1]),m[2],m[3];nm=next((v.split(': ',1)[1].split('): ')[-1].strip()for v in lines[1:]if'DW_AT_name 'in v),None)
 for d in list(stack):
  if d>=dep:del stack[d]
 if tag in ['DW_TAG_class_type','DW_TAG_structure_type']and nm in ['Warp','Goto']:
  sz=next((int(v.split(':')[-1])for v in lines if'DW_AT_byte_size'in v),None)
  if sz:
   q=dict(name=nm,depth=dep,die=off,size=sz,members={});out.setdefault(nm,[]).append(q);stack[dep]=q
 elif tag=='DW_TAG_member'and dep-1 in stack and nm:
  loc=next((v.split(':')[-1].strip()for v in lines if'DW_AT_data_member_location'in v),None)
  typ=next((v.split(':')[-1].strip()for v in lines if'DW_AT_type 'in v),None)
  if loc is not None:stack[dep-1]['members'][nm]=dict(offset=loc,type_die=typ)
 if tag=='DW_TAG_variable'and nm=='wp'and any('8c47fb58'in v for v in lines):vars.append(lines)
p=subprocess.Popen(['/opt/toolchains/dc/sh-elf/bin/sh-elf-readelf','--debug-dump=info',str(E)],stdout=subprocess.PIPE,text=True)
for line in p.stdout:
 if re.match(r'\s*<\d+><',line):flush(die);die=[line.rstrip()]
 else:die.append(line.rstrip())
flush(die);assert p.wait()==0;r=dict(ELF_sha256=hashlib.sha256(E.read_bytes()).hexdigest(),types=out,variables=vars);(L/'controlled016-frozen-Warp-DWARF.json').write_text(json.dumps(r,indent=2)+'\n');print({k:[(q['size'],q['members'])for q in v]for k,v in out.items()if k in ['Warp','Goto']});print('Global selected', [{n:q['members'].get(n)for n in ['Part','room_id','room_id_prev','NextRoom','NextPart','NextPos','NextY','pRoom','pArc']}for q in out.get('GlobalWork',[])][:1]);print('SceAtData',out.get('SceAtData'))
