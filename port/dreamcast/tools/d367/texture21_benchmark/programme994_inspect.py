#!/usr/bin/env python3
"""Independent read-only new programme/14 overlay/slot/retained macro binding."""
import argparse,gzip,hashlib,json,struct
from pathlib import Path
from mipmap_pair_plan import sha,local
SOURCE='845abb1f4ad3a2721d17f64899b6dc59d4bce66c'
def fnv(b):
 if len(b)%4:raise ValueError('word FNV width')
 h=2166136261
 for (w,) in struct.iter_unpack('<I',b):h=((h^w)*16777619)&0xffffffff
 return h
def elf_tables(b):
 if b[:6]!=b'\x7fELF\x01\x01':raise ValueError('ELF32LE required')
 shoff=struct.unpack_from('<I',b,32)[0];ents,n,strings=struct.unpack_from('<HHH',b,46)
 if ents!=40:raise ValueError('section width')
 rows=[struct.unpack_from('<10I',b,shoff+40*i)for i in range(n)]
 s=rows[strings];names=b[s[4]:s[4]+s[5]]
 def name(ns,o):return ns[o:ns.index(0,o)].decode()
 sections={name(names,r[0]):r for r in rows};symbols={}
 for r in rows:
  if r[1]!=2:continue
  if r[9]!=16:raise ValueError('symbol width')
  s=rows[r[6]];ns=b[s[4]:s[4]+s[5]]
  for o in range(r[4],r[4]+r[5],16):
   no,v,size,info,other,idx=struct.unpack_from('<IIIBBH',b,o)
   if idx:symbols.setdefault(name(ns,no),[]).append((v,size,idx))
 return sections,symbols
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--unit',type=Path,required=True);ap.add_argument('--mirror',type=Path,required=True);ap.add_argument('--layout',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 result=json.loads((a.mirror/'result.json').read_text());assert result['source']==SOURCE
 b=(a.unit/'out/re4dc-game.elf').read_bytes();sec,sym=elf_tables(b);text=sec['.text'];tb=b[text[4]:text[4]+(text[5]&~3)];identity=(fnv(tb),len(tb))
 hits=sym['_re4dc_image_id'];assert len(hits)==1
 v=hits[0][0];owners=[r for r in sec.values()if r[1]==1 and r[3]<=v and v+8<=r[3]+r[5]];assert len(owners)==1
 r=owners[0];assert struct.unpack_from('<2I',b,r[4]+v-r[3])==identity
 layout=json.loads(a.layout.read_text());selected=layout['selected_paths'];files={};proof=[]
 names={Path(r['path']).name for r in result['overlays']};expected={Path(p).name for p in selected if p.endswith('.ovl')};assert names==expected and len(names)==14
 for row in result['overlays']:
  p=local(row['path']);data=p.read_bytes();n=p.name;disc='/dc/'+n;s=selected[disc];h=struct.unpack_from('<16I',data)
  assert sha(p)==row['sha256']==sha(a.mirror/n) and len(data)==row['bytes']
  assert h[:2]==(0x4f344552,1) and len(data)==64+h[2]+h[3]*4 and tuple(h[14:])==identity
  image=data[64:64+h[2]];rel=data[64+h[2]:]
  # The final ELF deliberately strips overlay sections after sealing. Do not
  # claim a comparison against absent sections or the discarded shifted ELF.
  assert row['section'] not in sec
  assert fnv(image)==h[12] and fnv(rel)==h[13] and all(o<=h[2] for o in h[5:12])
  rr=[x[0]for x in struct.iter_unpack('<I',rel)];assert rr==sorted(set(rr))
  assert all(o%4==0 and o+4<=h[2] and h[4]<=struct.unpack_from('<I',image,o)[0]<=h[4]+h[2] for o in rr)
  cap=(s['before']['bytes']+2047)//2048*2048;assert len(data)<=cap and s['after_extent']==s['before']['extent']
  files[disc]={'source_path':str(p),'bytes':len(data),'sha256':sha(p)}
  proof.append(dict(path=disc,extent=s['after_extent'],capacity=cap,bytes=len(data),sha256=sha(p),header=list(h),final_ELF_overlay_section_stripped=True,payload_word_FNV_exact=True,relocations_checked=len(rr),image_id_exact=True,mirror_exact=True))
 raw=a.unit/'out/program.bin';assert sha(raw)==result['programme_sha256']==sha(a.mirror/'program.bin') and sha(a.unit/'out/re4dc-game.elf')==result['ELF_sha256']==sha(a.mirror/'re4dc-game.elf')
 files['/1ST_READ.BIN']={'source_path':str(raw),'bytes':raw.stat().st_size,'sha256':sha(raw)}
 macros={};inputs={}
 for tu in ['native_ui','native_static']:
  for arm in ['default','off','on']:
   name=tu+'-'+arm;task=a.unit/(name+'-task.json');t=json.loads(task.read_text());r=result['objects'][name];obj=local(r['path']);assert sha(obj)==r['raw_sha256']
   macrofile=local(t['prefix']+'-macros.txt.gz');data=gzip.decompress(macrofile.read_bytes());assert hashlib.sha256(data).hexdigest()==r['preprocess']['macro_sha256']
   mm={l.split(maxsplit=2)[1]:l.split(maxsplit=2)[2]if len(l.split(maxsplit=2))>2 else ''for l in data.decode().splitlines()if l.startswith('#define ')}
   assert mm['RE4DC_WORLD_RECT21']==('1'if arm=='on'else'0')
   macros[name]={'task_sha256':sha(task),'object_sha256':sha(obj),'macro_sha256':r['preprocess']['macro_sha256'],'preprocess':r['preprocess'],'selected_definitions':{k:v for k,v in mm.items()if k.startswith('RE4DC_')and any(x in k for x in ['MIPMAP','LOD','UV16','HAND','HEAD','CHARBAKE','ANIMAL','CAP','WORLD_RECT21'])}}
   inputs[str(task)]=sha(task)
 knobs=a.mirror/'inherited-resolved-knobs.txt';actual=dict(l.split('=',1)for l in knobs.read_text().splitlines()if '='in l and not l.startswith('#'))
 chosen={k:actual[k]for k in ['CAST_MIPMAP','WORLD_RECT21','LEON_LOD','NATIVE_ACTOR_LOD','ACTOR_UV16','LEON_HEADLESS','CHARBAKE_VARIANT','ANIMALS_OFF','ALIVE_CAP_N']if k in actual}
 # Inherited make knobs are not a replacement for newly compiled on-TU macro bytes.
 out={'schema':'independent-programme994-bindings1','source':SOURCE,'elf_sha256':sha(a.unit/'out/re4dc-game.elf'),'files':files,'image_id':list(identity),'all14':proof,'macro_object_bindings':macros,'inherited_resolved_knobs':chosen,'resolved_flags_sha256':sha(knobs),'compile_inputs_sha256':sha(a.mirror/'actual-complete-dependency-closure.json'),'actual_closure_path':str(a.mirror/'actual-complete-dependency-closure.json'),'input_refs':inputs,'new_ABI_reaudit_required':True,'scope':'Independent stored ELF/raw/overlay header/payload/wordFNV/relocation/imageID/slot/mirror and macro/object binding. Shift ELF outside-image equivalence remains producer receipt, not re-executed here. No runtime allocator/LOD/functional/performance acceptance.'}
 with a.out.open('x')as f:json.dump(out,f,indent=2);f.write('\n')
 print(json.dumps({'report_sha256':sha(a.out),'files':len(files),'overlay_count':len(proof),'image_id':identity,'selected_inherited_knobs':chosen}))
if __name__=='__main__':main()
