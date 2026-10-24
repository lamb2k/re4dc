"""Read exact current canary ELF nm/DWARF only; no guest or runtime mutation."""
from pathlib import Path
import subprocess,re,json,hashlib,time
O=Path('/root/work/lanes/water-rain24-canary-bca44-20261024/programmes');E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/water-rain24/rain-bca44-console55-20261024/identities');TOOL='/opt/toolchains/dc/sh-elf/bin/'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def typename(attrs):return attrs.get('DW_AT_name','').split('): ',1)[-1]
def extract(elf):
 stack={};cur=None;kept={};roots=[];started=time.monotonic()
 def finish():
  if not cur:return
  name=typename(cur['attrs'])
  if cur['tag'] in ['DW_TAG_structure_type','DW_TAG_class_type'] and name in ['GlobalWork','Filter06Work'] and 'DW_AT_byte_size' in cur['attrs']:
   kept[cur['off']]=cur;roots.append(cur['off'])
  elif cur['parent'] in kept:kept[cur['off']]=cur
 p=subprocess.Popen([TOOL+'sh-elf-readelf','--debug-dump=info',str(elf)],stdout=subprocess.PIPE,text=True)
 try:
  for line in p.stdout:
   if time.monotonic()-started>50:raise TimeoutError('bounded DWARF extraction')
   m=re.match(r'\s*<(\d+)><([0-9a-f]+)>: Abbrev Number: \d+(?: \((DW_TAG_\w+)\))?',line)
   if m:
    finish();level=int(m[1]);off=int(m[2],16);cur={'off':off,'tag':m[3],'parent':stack.get(level-1),'attrs':{}} if m[3] else None;stack[level]=off
   else:
    m=re.match(r'\s*<[0-9a-f]+>\s+(DW_AT_\w+)\s*:\s*(.*)',line)
    if cur is not None and m:cur['attrs'][m[1]]=m[2]
  finish();assert p.wait(timeout=3)==0
 finally:
  if p.poll() is None:p.terminate();p.wait(timeout=3)
 children={}
 for d in kept.values():children.setdefault(d['parent'],[]).append(d)
 def fields(root,base=0,depth=0):
  assert depth<8;out={}
  for d in children.get(root,[]):
   if d['tag']!='DW_TAG_member':continue
   attr=d['attrs'];loc=attr.get('DW_AT_data_member_location','0');assert loc.isdigit(),'nonconstant offset';offset=base+int(loc);name=typename(attr)
   if name:out[name]={'offset':offset,'type_die':attr.get('DW_AT_type')}
   else:
    ref=re.fullmatch(r'<0x([0-9a-f]+)>',attr['DW_AT_type']);assert ref;target=int(ref[1],16);assert target in kept,'anonymous type missing';nested=fields(target,offset,depth+1)
    for k,v in nested.items():assert k not in out;out[k]=v
  return out
 wanted={'GlobalWork':['Frame_cnt','room_id'],'Filter06Work':['p','num','spd','col','cur','rate','scale','alphaMin']};result={}
 for typ,names in wanted.items():
  choices=[]
  for off in roots:
   d=kept[off]
   if typename(d['attrs'])!=typ:continue
   f=fields(off)
   if all(k in f for k in names):choices.append({'bytes':int(d['attrs']['DW_AT_byte_size'],0),'members':{k:f[k] for k in names}})
  assert choices,typ;sigs={(x['bytes'],tuple((k,x['members'][k]['offset']) for k in names)) for x in choices};assert len(sigs)==1,(typ,'conflicting DWARF');result[typ]=dict(choices[0],definition_count=len(choices))
 return result
for arm in ['off','on']:
 out=O/(arm+'-g/out');elf=out/'re4dc-game.elf';types=extract(elf);nm=subprocess.check_output([TOOL+'sh-elf-nm','-C','-S','--defined-only',str(elf)],text=True,timeout=20);syms={}
 needed={'pG','flt06','s_raindc_frames','s_raindc_sent','s_raindc_pending','s_raindc_queued_room','s_raindc_queued_frame'}
 for line in nm.splitlines():
  m=re.fullmatch(r'([0-9a-f]+) ([0-9a-f]+) ([bBdD]) (.+)',line)
  if m and m[4] in needed:
   assert m[4] not in syms;syms[m[4]]={'address':int(m[1],16),'bytes':int(m[2],16),'storage':m[3]}
 assert {'pG','flt06','s_raindc_frames','s_raindc_sent','s_raindc_pending'}<=syms.keys();assert syms['flt06']['bytes']==types['Filter06Work']['bytes'];assert syms['pG']['bytes']==4
 if arm=='on':assert {'s_raindc_queued_room','s_raindc_queued_frame'}<=syms.keys()
 else:assert 's_raindc_queued_room' not in syms
 result={'source':'bca44d58a1fa0a51fd87ba94deba8cba925c8998','arm':arm,'elf':str(elf),'elf_sha256':sha(elf),'symbols':syms,'types':types,'read_only':True,'no_old_addresses_reused':True,'scope':'live source scalar observation only; no completed scene/actors/viewport/present ownership'}
 (E/(arm+'-g-source-layout.json')).write_text(json.dumps(result,indent=2)+'\n');print(arm,types,syms,flush=True)