from pathlib import Path
import json,hashlib,struct,subprocess,re
base=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-port23-20261023/full-target-static1d63-current')
manifest=json.loads((base/'SHA256-MANIFEST.json').read_text()); summary=json.loads((base/'SUMMARY.json').read_text()); receipt=json.loads((base/'receipt.json').read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
verified=[]
for n,pin in manifest.items():
 b=(base/n).read_bytes(); assert len(b)==pin['bytes'] and sha(b)==pin['sha256'],n;verified.append(n)
for name,pin in receipt['pins'].items():
 assert sha(Path(name).read_bytes())==pin,name

def elf(path):
 b=path.read_bytes(); assert b[:7]==b'\x7fELF\x01\x01\x01'
 h=struct.unpack_from('<16sHHIIIIIHHHHHH',b); shoff=h[6]; shentsize=h[11];shnum=h[12];namesidx=h[13]
 sections=[struct.unpack_from('<IIIIIIIIII',b,shoff+i*shentsize) for i in range(shnum)]
 names=sections[namesidx];strings=b[names[4]:names[4]+names[5]]
 z=lambda table,at:table[at:table.index(0,at)].decode()
 s={z(strings,x[0]):x for x in sections}; alloc=[x for x in sections if x[2]&2 and x[5]]
 progs=[x for x in alloc if x[1]!=8];first=min(x[3] for x in progs);end=max(x[3]+x[5] for x in progs)
 raw=bytearray(end-first)
 for x in progs:raw[x[3]-first:x[3]-first+x[5]]=b[x[4]:x[4]+x[5]]
 syms={}
 for x in sections:
  if x[1]!=2:continue
  st=sections[x[6]];st=b[st[4]:st[4]+st[5]]
  for at in range(x[4],x[4]+x[5],x[9]):
   no,value,size,info,other,idx=struct.unpack_from('<IIIBBH',b,at)
   if no: syms[z(st,no)]=(value,size,info,idx)
 sizes={'text':sum(x[5] for x in alloc if not x[2]&1),'data':sum(x[5] for x in alloc if x[2]&1 and x[1]!=8),'bss':sum(x[5] for x in alloc if x[1]==8)}
 return {'elf_sha256':sha(b),'raw_sha256':sha(raw),'raw_bytes':len(raw),'sections':sizes,'boundaries':{n:syms[n][0] for n in ['_end','_etext','_edata']},'symbols':syms}

arms={}
for arm in ['off','on']:
 out=Path('/root/work/lanes/gc-port23-full-target2-scratch')/arm/'out';r=receipt['arms'][arm]
 for n,pin in r['files'].items():
  b=(out/n).read_bytes();assert len(b)==pin['bytes'] and sha(b)==pin['sha256'],(arm,n)
 e=elf(out/'re4dc-game.elf');assert e['raw_sha256']==r['raw_sha256']==summary['raw_hashes'][arm]
 assert e['boundaries']==summary['boundary_symbols'][arm]
 assert sha((out/'resolved-knobs.txt').read_bytes())==r['resolved_sha256']
 for n in ['aliases.ld','aliases-all.ld','missing.cpp']:
  assert not re.search(r'gcasset|gc_asset',(base/arm/n).read_text(),re.I),(arm,n)
 assert not (base/arm/'missing.txt').read_bytes()
 undefined=[n for n,(_,_,_,idx) in e['symbols'].items() if idx==0 and 'gcasset' in n]
 assert not undefined
 gc=[n for n,(_,_,_,idx) in e['symbols'].items() if idx and ('re4dc_gcasset' in n)]
 e.pop('symbols');e['gc_named_defined_count']=len(gc);arms[arm]=e
baseline=Path(receipt['profile']);be=elf(baseline/'re4dc-game.elf');assert be['raw_sha256']==arms['off']['raw_sha256']
ovls=[n for n in receipt['arms']['off']['files'] if n.endswith('.ovl')];assert len(ovls)==14
for n in ovls:assert sha((baseline/n).read_bytes())==receipt['arms']['off']['files'][n]['sha256']
delta={n:arms['on']['sections'][n]-arms['off']['sections'][n] for n in ['text','data','bss']};assert delta==summary['linked_sections']
enddelta=arms['on']['boundaries']['_end']-arms['off']['boundaries']['_end'];assert enddelta==60384
src=Path('/root/work/lanes/gc-port23');assert subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()==receipt['source'];assert not subprocess.check_output(['git','-C',str(src),'status','--porcelain'])
commands={a:json.loads((base/a/'command.json').read_text()) for a in ['off','on']};diff=[(i,x,y) for i,(x,y) in enumerate(zip(commands['off'],commands['on'])) if x!=y];assert len(commands['off'])==len(commands['on']);assert len(diff)==1 and diff[0][1:] == ('GC_ASSET_GATE=0','GC_ASSET_GATE=1'),diff
result={'source':receipt['source'],'scope':'Independent read-only actual ELF parsing/hash verification; no SDK command/build/runtime tests','metadata_members_verified':len(verified),'immutable_input_pins_verified':len(receipt['pins']),'programme_arms':arms,'baseline_off_raw_and_all14_equal':True,'only_ordered_command_difference':diff,'linked_sections_delta':delta,'linked_total_delta':sum(delta.values()),'end_delta':enddelta,'missing_lists_empty':True,'no_gc_alias_or_generated_stub':True,'source_clean':True,'limits':'Catalog0 only; no configured pin/file install, runtime heap/high-water/H2/guest/I001 acceptance.'}
out=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-port23-20261023/full-link-readback1d63');out.mkdir(exist_ok=True);(out/'readback.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
