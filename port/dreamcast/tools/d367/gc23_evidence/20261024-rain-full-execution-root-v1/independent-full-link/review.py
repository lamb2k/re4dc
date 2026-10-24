"""Independent completed rain normal pair reader. No SDK/Make/query/stage/guest."""
from pathlib import Path
import collections,copy,hashlib,json,re,resource,shlex,signal,struct,time,types
HERE=Path(__file__).resolve().parent;LANE=HERE.parent;KIT=LANE/'full-normal-rain8ce-exec-v1';ROOT=Path('/dev/shm/rain8ce-full-normal-179r4a5c');RESULT=ROOT/'root-full-pair-v1';SOURCE='8ce5ee2d00027268c3e69c9c300b819c1b14c63f'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def identity(p):return dict(bytes=Path(p).stat().st_size,sha256=sha(p))
def require(x,reason):
 if not x:raise ValueError(reason)
def symbols(p):
 b=Path(p).read_bytes();h=struct.unpack_from('<16sHHIIIIIHHHHHH',b);sections=[struct.unpack_from('<IIIIIIIIII',b,h[6]+i*h[11]) for i in range(h[12])];out=[]
 for section in sections:
  if section[1]!=2:continue
  st=sections[section[6]];strings=b[st[4]:st[4]+st[5]]
  for at in range(section[4],section[4]+section[5],16):
   ni,value,size,info,other,index=struct.unpack_from('<IIIBBH',b,at);name=strings[ni:].split(b'\0',1)[0].decode()
   if name:out.append(dict(name=name,value=value,bytes=size,info=info,other=other,index=index))
 return out

def check_rain(record,sections,on):
 if not on:require(not record,'OFF rain record present');return
 require(len(record)==1,'Exactly one ON rain record');v=record[0]
 require(v['info']==0x11 and v['other']==0 and v['bytes']==128,'Rain binding/type/size')
 require(v['value']%32==0 and 0x8c000000<=v['value'] and v['value']+128<=0x8d000000,'Rain absolute cached P1 alignment/extent')
 require(any(s['name']=='.bss' and s['addr']<=v['value'] and v['value']+128<=s['addr']+s['bytes'] for s in sections),'Rain actual BSS placement')

def compile_graph(log,root):
 rows=[shlex.split(x) for x in log.splitlines() if ' -c ' in x and ' -o ' in x];out={}
 for a in rows:
  p=a[a.index('-o')+1];require(p.startswith(str(root/'out/obj')+'/'),'Compile output outside actual arm');key=p.split('/out/obj/',1)[1];require(key not in out,'Duplicate actual compile object');out[key]=a
 return out

def main():
 resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));resource.setrlimit(resource.RLIMIT_CORE,(0,0));signal.alarm(120);start=time.monotonic();initial_receipt=sha(RESULT/'receipt.json');r=json.loads((RESULT/'receipt.json').read_text());plan=json.loads((ROOT/'PREPARATION.json').read_text());contract=json.loads((KIT/'CONTRACT.json').read_text());seal=json.loads((KIT/'ROOT-SEAL.json').read_text());grant=json.loads((KIT/'ROOT-GRANT.json').read_text())
 require(r['complete'] is True and not r.get('failure') and set(r['arms'])=={'off','on'} and r['source']==plan['source']==contract['source']==grant['source']==SOURCE,'Terminal/source identities')
 require(sha(KIT/'CONTRACT.json')==r['contract_sha256']==grant['contract_sha256']=='b85506bc72d43283ef6f741dec3196b1b75dc615868555b2cb559086a237950e','Contract pin')
 require(sha(ROOT/'PREPARATION.json')==r['preparation_sha256']==contract['preparation_sha256'],'Actual preparation pin')
 require(grant['approved'] is True and grant['authorization']=='SDK_FULL_NORMAL_OFF_ON' and sha(KIT/'ROOT-GRANT.json')==r['authorization']['sha256'],'Actual SDK-only allocation receipt')
 require(sha(KIT/'controller.py')==r['controller_sha256'],'Controller source pin')
 verified={};cache={}
 def verify_rows(label,rows):
  for name,row in rows.items():
   p=Path(name);stat=p.stat();key=(str(p),stat.st_size,stat.st_mtime_ns,stat.st_ino)
   if key not in cache:cache[key]=identity(p)
   require(cache[key]==row,'Pinned bytes changed '+str(p))
  verified[label]=len(rows)
 verify_rows('kit', {str(KIT/k):v for k,v in seal['files'].items()});verify_rows('SDK_compiler_headers_tools',contract['tool_pins']);verify_rows('external_and_recipe_inputs',plan['input_pins']);verify_rows('historic_dependency_files',plan['dependency_files'])
 for arm in ('off','on'):verify_rows(arm+'_source',{str(ROOT/arm/'source'/k):v for k,v in plan['source_manifest'].items()})
 support=LANE/'full-link-review/verify_completed_pair.py';module=types.ModuleType('independent_ELF_reader');module.__file__=str(support);exec(compile(support.read_text(),str(support),'exec'),module.__dict__)
 historic_root=Path('/dev/shm/gc-motion24-full-pair-wrf50x14/off');baseline=compile_graph((historic_root/'build.log').read_text(),historic_root);require(len(baseline)==567,'Pinned567 normal compile graph')
 expected_order=[x.rsplit('/obj/',1)[-1] for x in plan['historical_actual_graph']['off']['object_order']];require(len(expected_order)==448,'Historic448 link order')
 arms={};dependency_records={};object_prices={};helpers={'gc_asset_gate','gc_asset_disc','gc_asset_members','gc_asset_payloads','gc_asset_audio','gc_asset_motion_unknown'}
 for arm in ('off','on'):
  a=ROOT/arm;out=a/'out';saved=r['arms'][arm];require(saved['complete'] is True,'Incomplete arm');require(json.loads((a/'command.json').read_text())==plan['commands'][arm] and sha(a/'command.json')==saved['command_sha256'] and saved['environment']==plan['environment'][arm],'Actual command/environment')
  post=json.loads((RESULT/arm/'postbuild.json').read_text());require(post['complete'] is True and sha(RESULT/arm/'postbuild.json')==saved['postbuild_sha256'],'Postbuild receipt pin')
  log=(a/'build.log').read_text();require(sha(a/'build.log')==post['build_log_sha256'],'Actual complete log pin');now=compile_graph(log,a);require(len(now)==567 and set(now)==set(baseline),'Same567 actual compilation graph')
  rain_flags={}
  for key,av in now.items():
   flags=[x for x in av if x.startswith('-DRE4DC_RAIN_R10C')]
   if flags:rain_flags[av[av.index('-c')+1]]=sorted(flags)
   current=[x.replace(str(a),'<ARM>') for x in av if not x.startswith('-DRE4DC_RAIN_R10C')];before=[x.replace(str(historic_root),'<ARM>') for x in baseline[key]]
   require(current==before,'Non-rain actual compiler argument change '+key)
  expected={} if arm=='off' else {'../../../src/game/filter06.cpp':sorted(['-DRE4DC_RAIN_R10C_DC=1','-DRE4DC_RAIN_R10C_DIAG=1']),'../../../src/game/espgen44.cpp':['-DRE4DC_RAIN_R10C_DIAG=1']};require(rain_flags==expected,'Rain-only flags')
  lines=[x for x in log.splitlines() if 'bash tools/link.sh ' in x];require(len(lines)==1,'One actual raw link');link=[x for x in shlex.split(lines[0]) if x.endswith('.o')];require(len(link)==len(set(link))==448 and [x.rsplit('/obj/',1)[-1] for x in link]==expected_order,'Same448 ordered unique link')
  require(not any(Path(x).stem in helpers for x in link),'GC helper linked')
  helper_rows={}
  for key,av in now.items():
   if Path(av[av.index('-c')+1]).stem not in helpers:continue
   p=out/'obj'/key;e=module.elf(p);require(e['type']==1 and e['allocated_bytes']==0 and e['meaningful_symbol_rows']==[],'Default-off helper contains allocation/symbols');require(not any(x.startswith('-DRE4DC_GC_ASSET') for x in av),'Enabled helper compile flag');helper_rows[key]=identity(p)
  require(len(helper_rows)==6 and {str((out/'obj'/k).resolve()) for k in helper_rows}=={str(p.resolve()) for p in (out/'obj').rglob('gc_asset_*.o')},'Complete helper object inventory')
  resolved=dict(x.split('=',1) for x in (out/'resolved-knobs.txt').read_text().splitlines() if '=' in x and not x.startswith('#'));expected_resolved={'RAIN_R10C_DC':str(int(arm=='on')),'RAIN_R10C_DIAG':str(int(arm=='on')),'GC_ASSET_GATE':'0','GC_ASSET_MOTION_UNKNOWN':'0','GC_ASSET_CATALOG_SHA256':'0','PS2_PVS_BATCH_COMPOSE':'0','PS2_PVS_EFFECTIVE0_SOURCES':'0','KOS_CACHE_P2':'1','KOS_CACHE_P2_DIAG':'0','DBG_WARP':'0','PC_SAMPLER':'0'};require(all(resolved.get(k)==v for k,v in expected_resolved.items()),'Actual resolved qualification profile');require(sha(out/'resolved-knobs.txt')==post['resolved_sha256'],'Resolved pin')
  scratch=a/'source/port/dreamcast/game/obj';require((scratch/'missing.txt').stat().st_size==0,'Missing providers');aliases={n:identity(scratch/n) for n in ('aliases.ld','missing.cpp','missing.txt')}
  for n in ('aliases.ld','missing.cpp'):require(not any(token in (scratch/n).read_text().lower() for token in ('gcasset','gc_asset','motion_unknown','rain_r10c')),'Diagnostic aliases/stubs')
  binary=out/'re4dc-game.elf';e=module.elf(binary,True);syms=symbols(binary);undefined=[x for x in syms if x['index']==0 and x['info']>>4];require(not undefined and not e['defined_gc_symbols'],'No unresolved or retained GC provider')
  require(e['addresses']==saved['addresses']==module.nm_addresses(a/'symbols.txt'),'ELF/nm addresses');require(e['sizes']==saved['sizes']==module.size_default((a/'size.txt').read_text()),'ELF size readback');sections=module.section_text(a/'sections.txt');require(all(sections[x['name']]==(x['bytes'],x['addr']) for x in e['allocated_sections']),'Section readback')
  raw=a/'program.bin';require(e['raw_from_ELF']['sha256']==sha(raw) and e['raw_from_ELF']['bytes']==raw.stat().st_size,'ELF reconstructed raw')
  files={p.name:identity(p) for p in [binary,raw,*out.glob('*.ovl')]};require(files==saved['files']==post['files'],'Main/all14 actual bytes');require(set(files)=={'re4dc-game.elf','program.bin'}|{x.lower()+'.ovl' for x in plan['overlay_order']},'Complete14 overlay inventory')
  order=[x.split('gen_overlay: .ovl_',1)[1].split()[0] for x in log.splitlines() if 'gen_overlay: .ovl_' in x];require(order==plan['overlay_order'],'Actual regenerated overlay order')
  if arm=='off':
   require(all(files[k]==v for k,v in plan['OFF_expected'].items()),'OFF exact production main/all14');require(e['addresses']['_end']==0x8c4320b4,'OFF production linked end')
  record=[s for s in syms if s['name']=='_re4dc_rain_r10c_diag'];check_rain(record,e['allocated_sections'],arm=='on');require(record==post['rain_record'],'Actual rain metadata matches saved report')
  deps={};dfiles={};counts=collections.Counter()
  for d in sorted(out.rglob('*.d')):
   dfiles[str(d)]=identity(d);line=d.read_text().replace(chr(92)+chr(10),' ').splitlines()[0];_,items=line.split(':',1)
   for token in shlex.split(items):
    path=Path(token);path=(path if path.is_absolute() else a/'source/port/dreamcast/game'/path).resolve();name=str(path)
    if name in deps:continue
    if path.is_relative_to(a/'source'):
     rel=str(path.relative_to(a/'source'))
     if rel in plan['source_manifest']:require(identity(path)==plan['source_manifest'][rel],'Frozen source dependency');kind='exact-source';pin=identity(path)
     else:
      require(rel.startswith('port/dreamcast/game/platform/sdk/gen/') and path.suffix=='.c' and not path.exists(),'Unknown/missing source dependency');original=a/'source/src/lib'/path.name;driver=a/'source/port/dreamcast/game/platform/sdk/strip_cw_asm.py';require(identity(original)==plan['source_manifest'][str(original.relative_to(a/'source'))] and identity(driver)==plan['source_manifest'][str(driver.relative_to(a/'source'))],'Unretained SDK chain');kind='unretained-generated-SDK';pin=dict(source=identity(original),driver=identity(driver))
    elif path.is_relative_to(out):require(path.is_file(),'Missing generated output');kind='owned-generated';pin=identity(path)
    else:require(name in plan['input_pins'] and identity(path)==plan['input_pins'][name],'Unpinned external actual dependency '+name);kind='exact-external';pin=identity(path)
    deps[name]=dict(kind=kind,pin=pin);counts[kind]+=1
  require(dfiles==post['dependency_closure']['files'] and len(deps)==len(post['dependency_closure']['dependencies'])==987 and len(dfiles)==515,'Actual complete dependency graph')
  dependency_records[arm]=dict(files=dfiles,dependencies=deps,class_counts=dict(counts))
  object_prices[arm]={}
  for unit in ('filter06.o','espgen44.o'):
   p=out/'obj/src/game'/unit;obj=module.elf(p);object_prices[arm][unit]=dict(identity=identity(p),sections=obj['allocated_sections'],sizes=obj['sizes'],record=[s for s in symbols(p) if s['name']=='_re4dc_rain_r10c_diag'])
  arms[arm]=dict(files=files,ELF=e,rain_record=record,object_count=448,compile_count=567,rain_flags=rain_flags,helpers=helper_rows,resolved_expected=expected_resolved,dependencies_summary=dict(files=len(dfiles),unique=len(deps),classes=dict(counts)),aliases=aliases,raw_link_sha256=hashlib.sha256(lines[0].encode()).hexdigest())
 off,on=arms['off'],arms['on'];delta={k:on['ELF']['sizes'][k]-off['ELF']['sizes'][k] for k in ['text','data','bss']};require(delta==r['delta']==dict(text=3424,data=0,bss=160),'Linked section prices');end=on['ELF']['addresses']['_end']-off['ELF']['addresses']['_end'];require(end==r['linked_end_delta']==3584,'Linked end price')
 source_prices={n:object_prices['on'][n]['sizes']['bss']-object_prices['off'][n]['sizes']['bss'] for n in object_prices['off']}
 controls=[]
 for name,edit in [('size',lambda v:v.update(bytes=127)),('binding',lambda v:v.update(info=0x10)),('other',lambda v:v.update(other=1)),('alignment',lambda v:v.update(value=v['value']+4)),('uncachedP2',lambda v:v.update(value=0xac000000)),('outsideP1',lambda v:v.update(value=0x8d000000)),('outsideBSS',lambda v:v.update(value=0x8c000000))]:
  bad=copy.deepcopy(on['rain_record'][0]);edit(bad)
  try:check_rain([bad],on['ELF']['allocated_sections'],True)
  except ValueError as err:controls.append(dict(name=name,refused=True,reason=str(err)))
  else:raise ValueError('Reader accepted altered actual rain metadata '+name)
 require(sha(RESULT/'receipt.json')==initial_receipt,'Terminal receipt changed during review')
 result=dict(status='CLEAR_SOURCE_LINK_READBACK_ONLY',source=SOURCE,terminal_receipt=dict(path=str(RESULT/'receipt.json'),identity=identity(RESULT/'receipt.json')),kit_seal=identity(KIT/'ROOT-SEAL.json'),contract=identity(KIT/'CONTRACT.json'),grant=identity(KIT/'ROOT-GRANT.json'),preparation=identity(ROOT/'PREPARATION.json'),reader_helper=identity(support),verified_manifests=verified,arms=arms,object_prices=object_prices,dependencies=dependency_records,delta=delta,linked_end_delta=end,rain_record_object_BSS_deltas=source_prices,whole_link_BSS_residual_vs128=delta['bss']-128,reader_mutations=controls,scope='Pure read-only file/ELF/log/source/input evidence; no SDK/Make/query, no actual cache execution, heap, stage, guest or physical acceptance',review_tool=identity(__file__),elapsed_seconds=time.monotonic()-start,limit_bytes=268435456,deadline_seconds=120)
 with (HERE/'INDEPENDENT-READBACK.json').open('x') as f:json.dump(result,f,indent=1);f.write('\n')
 print(json.dumps(dict(status=result['status'],delta=delta,end_delta=end,record=on['rain_record'],manifests=verified,object_BSS_deltas=source_prices,controls=len(controls),seconds=result['elapsed_seconds'])))
if __name__=='__main__':main()
