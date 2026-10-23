from pathlib import Path
import json,hashlib,re,struct,subprocess,sys,gzip
L=Path('/mnt/c/Game Dev/Emulators/codex-lanes/actor-visibility23');P=L/'native-normalize-f240r1'
sys.path.insert(0,str(P));from elf_image import ELF
O=Path('/root/probe/lanes/actor-visibility23-eligibility-witness-integration/on2');T=Path('/root/probe/codex-actor-visibility23-eligibility-witness-integration');E=ELF((O/'re4dc-game.elf').read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rec(p):return dict(path=str(p),bytes=Path(p).stat().st_size,sha256=sha(p))
symbols=(O/'main.symbols.txt').read_text();before=json.loads((L/'main-owner-scan10395/SCAN.json').read_text())[0]
def named(end):
 rows=[l for l in symbols.splitlines() if l.endswith(end)];assert len(rows)==1,(end,rows);return int(rows[0].split()[0],16)
def read(address,count):
 for s in E.sections:
  if s['flags']&2 and s['type']!=8 and s['address']<=address and address+count<=s['address']+s['size']:return E.data[s['offset']+address-s['address']:s['offset']+address-s['address']+count]
 raise ValueError('initialized bytes not mapped')
full=named('actor_visibility23::r119::full');needs=named('actor_visibility23::r119::needs');assert read(full,8)==struct.pack('<II',0xd80,0xd80)
expected=[(5,12,24,28,0x80),(5,12,24,62,0xd00),(7,17,65,75,0x80),(7,17,65,89,0xd00)]
assert read(needs,48)==b''.join(struct.pack('<4HI',*x)for x in expected)
cache=named(' T cache_write_ccr');cachehash=hashlib.sha256(read(cache,74)).hexdigest();assert cachehash=='91bfde106da3a3a2d4d87b9b17076b6c7292c9a25ff3248c5c7e658ed7465b88'
mode=E.symbols['_re4dc_actor_visibility23_mode'];assert mode['size']==4 and E.sections[mode['section']]['type']==8
witnesses=[(n,v)for n,v in E.symbols.items()if 'owner_witness23' in n];assert len(witnesses)==1;wn,wv=witnesses[0];assert 0<wv['size']<=4096 and E.sections[wv['section']]['type']==8
apis=['begin','bounds','end','identity','material','owner','potential','skip','world'];assert all('_re4dc_actor_visibility23_witness_'+n in E.symbols for n in apis)
assert not any('world_scratch' in n for n in E.symbols)
allpaths=[O/'re4dc-game.elf']+[O/'modules'/r['elf']for r in json.loads((O/'modules/roster.json').read_text())]
scans=[]
for path in allpaths:
 elf=ELF(path.read_bytes());dis=subprocess.check_output(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objdump','-d','-C',str(path)],text=True); funcs=[(int(m[1],16),m[2])for m in re.finditer(r'^([0-9a-f]+) <([^\n]+)>:',dis,re.M)];literals=[];alloc=[]
 for s in elf.sections:
  if not s['flags']&2 or not s['size']:continue
  assert not (s['address']<0x7c004000 and s['address']+s['size']>0x7c000000),s
  alloc.append(dict(name=s['name'],address=hex(s['address']),bytes=s['size'],type=s['type']))
  if s['type']==8:continue
  data=elf.data[s['offset']:s['offset']+s['size']]
  for off in range(0,len(data)-3,2):
   val=struct.unpack_from('<I',data,off)[0]
   if val!=0xff00001c and not 0x7c000000<=val<0x7c004000:continue
   addr=s['address']+off; prior=[f for f in funcs if f[0]<=addr];q=off&~3
   literals.append(dict(section=s['name'],address=hex(addr),value=hex(val),aligned4=addr%4==0,function=prior[-1][1]if prior and s['name']=='.text'else None,aligned_words=[hex(struct.unpack_from('<I',data,x)[0])for x in(q,q+4)if x+4<=len(data)]))
 scans.append(dict(elf=rec(path),allocated_sections=alloc,literals=literals))
keys=('section','value','aligned4','function','aligned_words');roles=lambda rows:[[r[k]for k in keys]for r in rows]
print('MAIN ROLES SAME',roles(scans[0]['literals'])==roles(before['literals']));print('NOW',json.dumps(scans[0]['literals']));print('OLD',json.dumps(before['literals']));print('MODULE_LITERAL_COUNTS',[(Path(s['elf']['path']).name,len(s['literals']))for s in scans[1:]])
# Save exact scan unconditionally for manual classification; never infer pointer roles from an address match alone.
(L/'main-audit-f240-on2/OWNER-SCAN.json').write_text(json.dumps(dict(source='f2405bb06ebaff6e2a7681479d5308ec5d3b988a',images=scans,historical_off_reference=rec(L/'main-owner-scan10395/SCAN.json'),main_literal_role_rows_identical=roles(scans[0]['literals'])==roles(before['literals']),runtime_admitted=False),indent=2)+'\n')
result=dict(status='LINKED_CERTIFICATE_MODE_WITNESS_CACHE_AND_SDK_READBACK_PASS_MANUAL_REVIEW_OPEN',source='f2405bb06ebaff6e2a7681479d5308ec5d3b988a',elf=rec(O/'re4dc-game.elf'),raw=rec(O/'prog.bin'),compiled_full_address=hex(full),full=[0xd80,0xd80],compiled_needs_address=hex(needs),needs=expected,mode=mode,zero_initialized_mode=True,witness_state=dict(symbol=wn,**wv),witness_API_symbols={n:E.symbols['_re4dc_actor_visibility23_witness_'+n]for n in apis},cache_write_ccr_address=hex(cache),cache_write_ccr_74bytes_sha256=cachehash,all15_images_no_allocated_OCRAM_section=True,no_world_scratch_symbols=True,owner_scan=rec(L/'main-audit-f240-on2/OWNER-SCAN.json'),fresh_off_identity=False,runtime_admitted=False,main_manual_review='PENDING')
# Actual SH4ZAM copied-input proof, all54 files at retained source and new destination.
R=O.parent;sdk=json.loads((L/'build-eligibility-witness23-r2/SDK-COPY-MANIFEST.json').read_text());actual=json.loads((R/'SDK-SOURCE-READBACK.json').read_text());bridge=json.loads((R/'SDK-COPY-READBACK.json').read_text());assert bridge['actual_copy']['sha256']==sha(R/'SDK-SOURCE-READBACK.json') and bridge['independent_manifest']['sha256']==sha(L/'build-eligibility-witness23-r2/SDK-COPY-MANIFEST.json');assert len(sdk['files'])==54
for row in sdk['files']:
 for root in ('source_root','destination_root'):
  p=Path(sdk[root])/row['relative'];assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes']
assert {(x['path'],x['bytes'],x['sha256'])for x in actual['files']}=={(x['relative'],x['bytes'],x['sha256'])for x in sdk['files']}
result['standard_SDK54_readback']=dict(files=54,bytes=sum(x['bytes']for x in sdk['files']),actual_copy=rec(R/'SDK-SOURCE-READBACK.json'),derived_bridge=rec(R/'SDK-COPY-READBACK.json'),manifest=rec(L/'build-eligibility-witness23-r2/SDK-COPY-MANIFEST.json'),gitlink=sdk['gitlink'],both_retained_source_and_current_destination_rehashed=True)
(L/'main-audit-f240-on2/COMPILED-CERTIFICATE-AND-OWNERS.json').write_text(json.dumps(result,indent=2)+'\n')
print('SUPPLEMENT',sha(L/'main-audit-f240-on2/COMPILED-CERTIFICATE-AND-OWNERS.json'))
