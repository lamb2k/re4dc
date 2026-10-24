"""Independent completed QA readback; pure Python, no SDK/build/stage/guest."""
from pathlib import Path
import ast,hashlib,importlib.util,json,re,resource,shlex,struct,time
HERE=Path(__file__).resolve().parent
ROOT=Path('/dev/shm/gc-motion24-qa-memory-v2-dbqczoc8')
HELPER=HERE.parent/'full-link-review/verify_completed_pair.py'

def main():
 resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));resource.setrlimit(resource.RLIMIT_CORE,(0,0));start=time.monotonic()
 spec=importlib.util.spec_from_file_location('normal_readback',HELPER);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 sha=m.sha;rpath=ROOT/'qa-receipt.json';rsha=sha(rpath);r=json.loads(rpath.read_text());p=json.loads((ROOT/'PREPARATION.json').read_text())
 assert r['complete'] is True and not r.get('failure') and r['source']==p['source']=='aab201ceac0e18107f64a3212398afe916793327'
 assert r['preparation_sha256']==sha(ROOT/'PREPARATION.json')
 assert r['source_manifest_sha256']==hashlib.sha256(json.dumps(p['source_manifests'],sort_keys=True).encode()).hexdigest()
 runner=HERE.parent/'memory-qualification-prep/qa-pair-v2/run_qa_three_arm.py';assert sha(runner)==r['runner_sha256']
 counts={'input_pins':m.verify(p['input_pins']),'normal_pair_preserved':m.verify(p['original_normal_pair_manifest']),'failed_QA_preserved':m.verify(p['preserved_failed_root_manifest'])}
 assert counts['normal_pair_preserved']==18029 and counts['failed_QA_preserved']==22823
 arms={};graph={};symbols={}
 for name in ('baseline','off','on'):
  arm=ROOT/name;out=arm/'out';saved=r['arms'][name];assert saved['complete'] is True
  command=json.loads((arm/'command.json').read_text());assert command==p['commands'][name] and sha(arm/'command.json')==saved['command_sha256'] and saved['environment']==p['environment'][name]
  manifest=p['source_manifests'][name];counts[name+'_source_files']=m.verify({str(arm/'source'/k):v for k,v in manifest.items()});assert counts[name+'_source_files']==p['source_files_per_arm'][name]
  assert sha(arm/'build.log')==saved['build_log_sha256'] and sha(out/'resolved-knobs.txt')==saved['resolved_sha256']
  resolved=dict(x.split('=',1) for x in (out/'resolved-knobs.txt').read_text().splitlines() if '=' in x and not x.startswith('#'))
  assert all(resolved.get(k)==v for k,v in p['resolved_expected'][name].items())
  for k in ('GC_ASSET_GATE','GC_ASSET_MOTION_UNKNOWN','GC_ASSET_CATALOG_SHA256'):
   if name=='baseline':assert k not in resolved
  expect={'DBG_WARP':'1','WARP_JUMP':'1','PC_SAMPLER':'0','TEX_CHECK':'1','MCHECK_LEONGC':'1','KOS_WATCH':'1','KOS_SQUEEZE':'1','W11_FIXTURE':'1','QA_MENU':'0','WORLD_METER':'0','KOS_CACHE_P2_DIAG':'0','KOS_SQUEEZE_BYTES':'0','KOS_SQUEEZE_FRAG':'0'}
  assert all(resolved.get(k)==v for k,v in expect.items())
  scratch=arm/'source/port/dreamcast/game/obj';assert (scratch/'missing.txt').stat().st_size==saved['missing_bytes']==0
  for n in ('aliases.ld','missing.cpp'):assert not any(token in (scratch/n).read_text() for token in ('gcasset','motion_unknown'))
  links=[x for x in (arm/'build.log').read_text().splitlines() if 'bash tools/link.sh ' in x];assert len(links)==1;objects=[x for x in shlex.split(links[0]) if x.endswith('.o')];assert len(objects)==p['expected_current_raw_object_counts'][name]==saved['raw_object_count']==(455 if name=='on' else 449)
  assert len([x for x in objects if x.endswith('/dbgwarp_bridge.o')])==1
  motion=[x for x in objects if x.endswith('/gc_asset_motion_unknown.o')];compiled=[x for x in (arm/'build.log').read_text().splitlines() if '-c platform/gc_asset_motion_unknown.cpp ' in x]
  if name=='baseline':assert not motion and not compiled and not (out/'obj/platform/gc_asset_motion_unknown.o').exists()
  elif name=='off':
   assert not motion and len(compiled)==1 and '-DRE4DC_GC_ASSET' not in compiled[0];h=m.elf(out/'obj/platform/gc_asset_motion_unknown.o');assert not h['allocated_bytes'] and not h['meaningful_symbol_rows']
  else:
   assert len(motion)==len(compiled)==1 and '-DRE4DC_GC_ASSET_MOTION_UNKNOWN=1' in compiled[0];at=objects.index(motion[0]);assert objects[at-1].endswith('/gc_asset_audio.o') and objects[at+1].endswith('/mtx.o')
  binary=out/'re4dc-game.elf';e=m.elf(binary,True);assert e['type']==2 and not e['undefined_gc_symbols']
  assert e['addresses']==saved['addresses']==m.nm_addresses(arm/'symbols.txt') and e['sizes']==m.size_default((arm/'size.txt').read_text())==m.size_default(saved['size'])
  sections=m.section_text(arm/'sections.txt');assert all(sections[s['name']]==(s['bytes'],s['addr']) for s in e['allocated_sections'] if s['name'] in sections)
  raw=arm/'program.bin';assert e['raw_from_ELF']['sha256']==sha(raw)==saved['raw_sha256'] and e['raw_from_ELF']['bytes']==raw.stat().st_size
  overlays={q.name:q for q in out.glob('*.ovl')};assert set(overlays)=={q.lower()+'.ovl' for q in p['expected_overlays']} and len(overlays)==14
  paths={'re4dc-game.elf':binary,'program.bin':raw,**overlays};assert set(paths)==set(saved['files'])
  for n,row in saved['files'].items():assert paths[n].stat().st_size==row['bytes'] and sha(paths[n])==row['sha256']
  # Parse log addresses directly from actual ELF symbol table, not saved nm text.
  b=binary.read_bytes();eh=struct.unpack_from('<16sHHIIIIIHHHHHH',b);ss=[struct.unpack_from('<IIIIIIIIII',b,eh[6]+i*eh[11]) for i in range(eh[12])];vals={}
  for s in ss:
   if s[1]!=2:continue
   strings=ss[s[6]];strings=b[strings[4]:strings[4]+strings[5]]
   for at in range(s[4],s[4]+s[5],16):
    ni,value,size,info,other,index=struct.unpack_from('<IIIBBH',b,at);n=strings[ni:].split(b'\0',1)[0].decode()
    if n in ('_re4dc_logbuf','_re4dc_log_head','_re4dc_stage'):assert index and n not in vals;vals[n]=value
  del b
  sym=' '.join(hex(vals[k]-0x8c000000) for k in ('_re4dc_logbuf','_re4dc_log_head','_re4dc_stage'));assert sym==(arm/'syms.txt').read_text().strip()
  graph[name]=dict(object_count=len(objects),link_sha256=hashlib.sha256(links[0].encode()).hexdigest(),motion_links=motion,motion_compiles=len(compiled));symbols[name]=sym
  arms[name]=dict(source=p['sources'][name],main=saved['files']['program.bin'],ELF=saved['files']['re4dc-game.elf'],all14={n:saved['files'][n] for n in overlays},addresses=e['addresses'],sizes=e['sizes'],raw_reconstructed=e['raw_from_ELF'],symbol_arguments=sym,resolved_sha256=saved['resolved_sha256'])
 assert arms['baseline']['main']==arms['off']['main'] and arms['baseline']['all14']==arms['off']['all14'] and arms['baseline']['addresses']==arms['off']['addresses']
 assert arms['off']['main']['sha256']=='e0168b780b102356c9bc3ee785753a659be6a020b1d1d3f8db92f14a90c16de5' and arms['on']['main']['sha256']=='02a14f20f815607da8caa6b118e775a2f567b0f85a067f28c00c1cc6b14251ae'
 delta=arms['on']['addresses']['_end']-arms['off']['addresses']['_end'];assert delta==r['end_delta_vs_fresh_OFF']==63040
 assert hashlib.sha256(rpath.read_bytes()).hexdigest()==rsha
 result=dict(status='INDEPENDENT_QA_THREE_READBACK_PASS',scope='programme/source/profile/log graph only; no SDK/staging/guest/heap acceptance',QA_receipt_sha256=rsha,QA_preparation_sha256=sha(ROOT/'PREPARATION.json'),parser_helper=dict(path=str(HELPER),sha256=sha(HELPER)),review_tool_sha256=sha(__file__),verified_counts=counts,arms=arms,graphs=graph,end_delta=delta,QA_vs_normal_end=r['QA_vs_normal_end'],fresh_files_hashed=len(m.cache),fresh_bytes_hashed=m.fresh_bytes,elapsed_seconds=time.monotonic()-start)
 with (HERE/'QA-READBACK.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps(dict(status=result['status'],verified=counts,end_delta=delta,symbols=symbols,seconds=result['elapsed_seconds'])))
if __name__=='__main__':main()
