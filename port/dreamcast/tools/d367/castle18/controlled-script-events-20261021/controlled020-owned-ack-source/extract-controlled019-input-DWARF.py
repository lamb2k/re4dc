from pathlib import Path
import subprocess,re,json,hashlib
L=Path('/mnt/c/Game Dev/Emulators/codex-lanes/castle18');E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/castle18-20261018/Test21/builds/c21jmW/re4dc-game.elf');blocks={};cur=None;die=[]
def flush(lines):
 global cur
 if not lines:return
 m=re.match(r'\s*<(\d+)><([^>]+)>:.*\((DW_TAG_\w+)\)',lines[0])
 if not m:return
 dep,off,tag=int(m[1]),m[2],m[3];nm=next((v.split(': ',1)[1].split('): ')[-1].strip()for v in lines[1:]if'DW_AT_name 'in v),None)
 if cur and dep<=cur['depth']:cur=None
 size=next((int(v.split(':')[-1].strip(),0)for v in lines if'DW_AT_byte_size'in v),None)
 if nm in ['KeyWork','Act']and size and tag in['DW_TAG_class_type','DW_TAG_structure_type']:
  cur=dict(name=nm,depth=dep,root=off,nodes={});blocks.setdefault(nm,cur)
 if cur:
  loc=next((v.split(':')[-1].strip()for v in lines if'DW_AT_data_member_location'in v),None);typ=next((re.search(r'<0x([0-9a-f]+)>',v).group(1)for v in lines if'DW_AT_type 'in v and re.search(r'<0x([0-9a-f]+)>',v)),None)
  cur['nodes'][off]=dict(depth=dep,tag=tag,name=nm,size=size,loc=loc,type=typ)
p=subprocess.Popen(['/opt/toolchains/dc/sh-elf/bin/sh-elf-readelf','--debug-dump=info',str(E)],stdout=subprocess.PIPE,text=True)
for line in p.stdout:
 if re.match(r'\s*<\d+><',line):flush(die);die=[line.rstrip()]
 else:die.append(line.rstrip())
flush(die);assert p.wait()==0
wanted={'KeyWork':['old','on','trg'],'Act':['frame','buttons','stick','hold','entry','ev','stickx']};result={}
for name,b in blocks.items():
 nodes=b['nodes'];children={};stack={}
 for off,v in nodes.items():
  for d in list(stack):
   if d>=v['depth']:del stack[d]
  par=stack.get(v['depth']-1)
  if par:children.setdefault(par,[]).append(off)
  stack[v['depth']]=off
 def members(t,base=0,seen=None):
  out={};seen=set()if seen is None else seen
  if t in seen:return out
  seen.add(t)
  for off in children.get(t,[]):
   v=nodes[off]
   if v['tag']!='DW_TAG_member':continue
   loc=int(v['loc'])if v['loc']is not None else 0
   if v['name']in wanted[name]:out[v['name']]=dict(offset=base+loc,type_die=v['type'],member_die=off)
   if v['name']is None and v['type']in nodes:out.update(members(v['type'],base+loc,seen.copy()))
  return out
 result[name]=dict(root_die=b['root'],size=nodes[b['root']]['size'],members=members(b['root']))
r=dict(ELF_sha256=hashlib.sha256(E.read_bytes()).hexdigest(),selected=result);(L/'controlled019-input-DWARF.json').write_text(json.dumps(r,indent=2)+'\n');print(result)
