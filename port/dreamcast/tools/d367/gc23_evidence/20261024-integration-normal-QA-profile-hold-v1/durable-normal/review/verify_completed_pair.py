"""Independent terminal full-link readback. No SDK, Make, compiler, linker or guest execution."""
from pathlib import Path
import hashlib,json,struct,shlex,re,subprocess,resource,time
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
HERE=Path(__file__).resolve().parent
LANE=HERE.parent
CONT=LANE/'full-link-continuation';PREP=LANE/'full-link-prep'
SOURCE='aab201ceac0e18107f64a3212398afe916793327'
BASELINE='49a4173a1792823ff5e275b0681b2c354c4e45140b7078d87c1253f2e926090b'
ON_EXPECTED='33e382bd836c1abeeb2d6b5cfbd414c258191ba8335a44f9ef3afb5b5ac9bd3f'
PROFILE=Path('/root/probe/lanes/route/out-rrfb254e8rP')
TREE=Path('/root/work/lanes/gc-motion24')
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

def verify(rows):
 for name,row in rows.items():
  p=Path(name);assert p.is_file() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256'],name
 return len(rows)

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

def main():
 start=time.monotonic();plan=json.loads((PREP/'PREPARATION.json').read_text());contract=json.loads((CONT/'CONTINUATION.json').read_text());root=Path(plan['root']);result=Path(contract['result']);initial_receipt_sha=sha(result);r=json.loads(result.read_text())
 assert r.get('complete') is True and not r.get('failure') and r['source']==plan['source']==contract['source']==SOURCE,'terminal completed receipt required'
 assert set(r['arms'])=={'off','on'} and all(r['arms'][a]['complete'] is True for a in ('off','on'))
 # Only read-only Git is executed by this verifier. All SDK analysis evidence is parsed as files.
 assert subprocess.check_output(['git','--no-optional-locks','-c','index.threads=1','-c','core.preloadIndex=false','-C',str(TREE),'rev-parse','HEAD'],text=True).strip()==SOURCE
 assert not subprocess.check_output(['git','--no-optional-locks','-c','index.threads=1','-c','core.preloadIndex=false','-C',str(TREE),'status','--porcelain'],text=True).strip()
 assert r['preparation_sha256']==sha(PREP/'PREPARATION.json')==contract['preparation_sha256']
 assert r['runner_sha256']==sha(CONT/'continue_full_pair.py') and r['continuation_sha256']==sha(CONT/'CONTINUATION.json')
 assert r['original_failed_receipt_sha256']==contract['original_failed_receipt_sha256']==sha(root/'receipt.json')
 assert contract['original_runner_sha256']==sha(PREP/'run_full_pair.py')
 failed=json.loads((root/'receipt.json').read_text());assert failed['source']==SOURCE and failed['complete'] is False and failed['failure']=='AssertionError()'
 assert set(failed['arms'])=={'off'} and not failed['arms']['off'].get('complete')
 counts={'completed_OFF_files':verify(contract['off_preservation_pins']),'pinned_inputs':verify(plan['input_pins']),'old_full_pair_files':verify(plan['original_old_full_manifest'])}
 assert counts['completed_OFF_files']==9013
 actual_off={str(q) for q in (root/'off').rglob('*') if q.is_file() and not q.is_symlink()};assert actual_off==set(contract['off_preservation_pins'])
 for arm in ('off','on'):counts[arm+'_source_files']=verify({str(root/arm/'source'/p):row for p,row in plan['source_manifest'].items()})
 assert hashlib.sha256(json.dumps(plan['source_manifest'],sort_keys=True).encode()).hexdigest()==r['source_manifest_sha256']
 original_flags={'STAT_ROUTINE_BYTES':'1','KOS_CACHE_P2':'1','KOS_CACHE_P2_DIAG':'0','SCENERY_DEDUP':'0','SCENERY_EMIT_PREFETCH':'0','SCENERY_SELECT_LEAN2':'0','CPU_BACKFACE':'0','ACTOR_BACKFACE':'0','VRAM_ROOM_ARENA':'0','PC_SAMPLER':'0','DBG_WARP':'0','GC_ASSET_CATALOG_SHA256':'0'}
 arms={};overlay_rows=[]
 for name in ('off','on'):
  arm=root/name;out=arm/'out';saved=r['arms'][name];raw=arm/'program.bin';binary=out/'re4dc-game.elf';log=(arm/'build.log').read_text();command=json.loads((arm/'command.json').read_text())
  assert command==plan['commands'][name]
  assert sha(arm/'build.log')==saved['build_log_sha256'] and sha(out/'resolved-knobs.txt')==saved['resolved_sha256']
  if name=='on':assert saved['command_sha256']==sha(arm/'command.json') and saved['environment']==plan['environment'][name]
  else:assert sha(arm/'command.json')==failed['arms']['off']['command_sha256']
  resolved=dict(x.split('=',1) for x in (out/'resolved-knobs.txt').read_text().splitlines() if '=' in x and not x.startswith('#'))
  expect=dict(original_flags,GC_ASSET_GATE='1' if name=='on' else '0',GC_ASSET_MOTION_UNKNOWN='1' if name=='on' else '0');assert all(resolved.get(k)==v for k,v in expect.items())
  scratch=arm/'source/port/dreamcast/game/obj';assert (scratch/'missing.txt').stat().st_size==saved['missing_bytes']==0
  for q in [scratch/'aliases.ld',scratch/'missing.cpp']:
   text=q.read_text();assert 'gcasset' not in text and 'motion_unknown' not in text
  links=[l for l in log.splitlines() if 'bash tools/link.sh ' in l];assert len(links)==1;objects=[x for x in shlex.split(links[0]) if x.endswith('.o')];assert len(objects)==plan['expected_current_raw_object_counts'][name]==saved['raw_object_count']
  helpers=[x for x in objects if x.endswith('/gc_asset_motion_unknown.o')];compiled=[l for l in log.splitlines() if '-c platform/gc_asset_motion_unknown.cpp ' in l];assert len(compiled)==1
  flags=[x for x in shlex.split(compiled[0]) if x.startswith('-DRE4DC_GC_ASSET')]
  helper=elf(out/'obj/platform/gc_asset_motion_unknown.o');assert helper['type']==1 and helper['machine']==42
  if name=='off':assert not helpers and not flags and helper['allocated_bytes']==0 and helper['meaningful_symbol_rows']==[] and helper['sha256']==contract['off']['helper']['sha256']
  else:
   assert len(helpers)==1 and '-DRE4DC_GC_ASSET_GATE=1' in flags and '-DRE4DC_GC_ASSET_MOTION_UNKNOWN=1' in flags
   at=objects.index(helpers[0]);assert objects[at-1].endswith('/gc_asset_audio.o') and objects[at+1].endswith('/mtx.o');assert helper['allocated_bytes']>0 and helper['defined_gc_symbols']
  e=elf(binary,True);assert e['type']==2 and not e['undefined_gc_symbols'];assert e['addresses']==saved['addresses']==nm_addresses(arm/'symbols.txt')
  assert e['sizes']==size_default((arm/'size.txt').read_text())==size_default(saved['size'])
  section_rows=section_text(arm/'sections.txt');assert all(section_rows[s['name']]==(s['bytes'],s['addr']) for s in e['allocated_sections'] if s['name'] in section_rows)
  image=e['raw_from_ELF'];assert image['sha256']==sha(raw)==saved['raw_sha256'] and image['bytes']==raw.stat().st_size
  expected_names={'re4dc-game.elf','program.bin'}|{x.lower()+'.ovl' for x in plan['expected_overlays']};assert set(saved['files'])==expected_names
  overlays=sorted(out.glob('*.ovl'));assert {p.name for p in overlays}==expected_names-{'re4dc-game.elf','program.bin'}
  paths={q.name:q for q in [binary,raw,*overlays]}
  for n,row in saved['files'].items():assert paths[n].stat().st_size==row['bytes'] and sha(paths[n])==row['sha256']
  if name=='off':
   assert sha(raw)==BASELINE and e['addresses']['_end']==0x8c4320b4
   assert saved==contract['off']
   for q in overlays:assert sha(q)==sha(PROFILE/q.name)
  else:assert sha(raw)==ON_EXPECTED
  arms[name]={'raw_sha256':sha(raw),'raw_bytes':raw.stat().st_size,'ELF_sha256':sha(binary),'sizes':e['sizes'],'addresses':e['addresses'],'allocated_sections':e['allocated_sections'],'raw_reconstructed_from_ELF':image,'raw_object_count':len(objects),'link_line_sha256':hashlib.sha256(links[0].encode()).hexdigest(),'compiled_motion_flags':flags,'helper':{k:helper[k] for k in ['sha256','allocated_bytes','meaningful_symbols','defined_gc_symbols']},'defined_GC_symbols':len(e['defined_gc_symbols']),'missing_bytes':0,'resolved_expected_flags':expect}
 for n in sorted(x.lower()+'.ovl' for x in plan['expected_overlays']):
  off=root/'off/out'/n;on=root/'on/out'/n;overlay_rows.append({'name':n,'off':{'bytes':off.stat().st_size,'sha256':sha(off)},'on':{'bytes':on.stat().st_size,'sha256':sha(on)},'byte_delta':on.stat().st_size-off.stat().st_size,'same_bytes':sha(off)==sha(on),'OFF_current_baseline_equal':sha(off)==sha(PROFILE/n)})
 off,on=arms['off'],arms['on'];delta={k:on['sizes'][k]-off['sizes'][k] for k in ['text','data','bss']};delta['section_total']=sum(delta.values());delta['linked_end']=on['addresses']['_end']-off['addresses']['_end'];delta['end_vs_old_ON']=on['addresses']['_end']-plan['old_graph']['on']['addresses']['_end'];delta['raw_bytes']=on['raw_bytes']-off['raw_bytes'];delta['alignment_and_gap_residual']=delta['linked_end']-delta['section_total']
 assert delta['linked_end']==r['end_delta_vs_fresh_OFF']==63072 and delta['end_vs_old_ON']==r['end_delta_vs_old_ON']==2688
 assert delta['section_total']==63720
 # Re-hash terminal receipt uncached to ensure it did not change during inspection.
 assert hashlib.sha256(result.read_bytes()).hexdigest()==initial_receipt_sha
 summary={'source':SOURCE,'terminal_receipt':str(result),'terminal_receipt_sha256':initial_receipt_sha,'status':'INDEPENDENT_FULL_LINK_READBACK_PASS','scope':'fresh programme/ELF/overlays/source/input/log-graph readback only; no SDK/Make/compiler/linker/guest execution; not heap, coverage, hardware or provenance acceptance','verified_manifests':counts,'fresh_unique_files_hashed':len(cache),'fresh_bytes_hashed':fresh_bytes,'original_failed_receipt_sha256':contract['original_failed_receipt_sha256'],'original_runner_sha256':contract['original_runner_sha256'],'continuation_runner_sha256':sha(CONT/'continue_full_pair.py'),'continuation_contract_sha256':sha(CONT/'CONTINUATION.json'),'arms':arms,'all14_overlays':overlay_rows,'deltas':delta,'seconds':time.monotonic()-start,'RLIMIT_AS_bytes':256*1024*1024,'execution':'read-only Python and git rev-parse/status only'}
 (HERE/'INDEPENDENT-READBACK.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({'status':summary['status'],'source':SOURCE,'OFF':off['raw_sha256'],'ON':on['raw_sha256'],'all14':len(overlay_rows),'manifests':counts,'deltas':delta,'seconds':summary['seconds']},indent=2))

if __name__=='__main__':main()