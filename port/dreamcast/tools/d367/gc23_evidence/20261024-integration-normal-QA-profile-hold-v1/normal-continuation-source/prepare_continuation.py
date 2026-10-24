"""Pure host validation and ON-only continuation generation. No SDK execution."""
from pathlib import Path
import copy,hashlib,json,shlex,struct,subprocess
HERE=Path(__file__).resolve().parent
PREP=HERE.parent/'full-link-prep'
SOURCE='aab201ceac0e18107f64a3212398afe916793327'
TREE=Path('/root/work/lanes/gc-motion24')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def pins(root):
 return {str(q):dict(bytes=q.stat().st_size,sha256=sha(q)) for q in sorted(root.rglob('*')) if q.is_file() and not q.is_symlink()}
def verify(rows):
 for p,r in rows.items():
  q=Path(p);assert q.stat().st_size==r['bytes'] and sha(q)==r['sha256'],p

def empty_elf(p):
 b=Path(p).read_bytes();assert b[:7]==b'\x7fELF\x01\x01\x01'
 h=struct.unpack_from('<16sHHIIIIIHHHHHH',b);assert h[1]==1 and h[2]==42
 sh=[struct.unpack_from('<IIIIIIIIII',b,h[6]+i*h[11]) for i in range(h[12])]
 allocated=sum(x[5] for x in sh if x[2]&2)
 meaningful=[]
 for s in sh:
  if s[1]!=2:continue
  strings=sh[s[6]];names=b[strings[4]:strings[4]+strings[5]]
  for at in range(s[4],s[4]+s[5],s[9]):
   name,value,size,info,other,index=struct.unpack_from('<IIIBBH',b,at)
   n=names[name:].split(b'\0',1)[0].decode()
   if n and (info&15) not in (3,4):meaningful.append([n,value,size,info,index])
 return dict(allocated_bytes=allocated,meaningful_symbols=meaningful,machine=42,sha256=sha(p))

def semantic_check(r):
 assert r['raw_object_count']==448 and not r['linked_motion_objects']
 assert len(r['compiled_motion'])==1
 argv=shlex.split(r['compiled_motion'][0])
 assert not any(x.startswith('-DRE4DC_GC_ASSET_MOTION_UNKNOWN') or x.startswith('-DRE4DC_GC_ASSET_GATE') for x in argv)
 assert r['helper']['allocated_bytes']==0 and r['helper']['meaningful_symbols']==[]
 assert r['raw_sha256']=='49a4173a1792823ff5e275b0681b2c354c4e45140b7078d87c1253f2e926090b'
 assert len(r['OFF_overlay_identity'])==14 and all(r['OFF_overlay_identity'].values())
 assert r['missing_bytes']==0 and r['addresses']['_end']==0x8c4320b4
 return True

def main():
 plan=json.loads((PREP/'PREPARATION.json').read_text());root=Path(plan['root']);off=root/'off';old=root/'receipt.json'
 assert subprocess.check_output(['git','-C',str(TREE),'rev-parse','HEAD'],text=True).strip()==SOURCE
 assert not subprocess.check_output(['git','-C',str(TREE),'status','--porcelain'],text=True).strip()
 failed=json.loads(old.read_text());assert failed['source']==SOURCE and not failed['complete'] and failed['failure']=='AssertionError()'
 assert set(failed['arms'])=={'off'} and failed['arms']['off']['started'] and not failed['arms']['off'].get('complete')
 assert failed['preparation_sha256']==sha(PREP/'PREPARATION.json')
 assert failed['runner_sha256']==sha(PREP/'run_full_pair.py')
 verify(plan['input_pins']);verify(plan['original_old_full_manifest'])
 for arm in ('off','on'):
  for n,r in plan['source_manifest'].items():verify({str(root/arm/'source'/n):r})
 assert not (root/'on/out').exists() and not (root/'on/build.log').exists() and not (root/'on/source/port/dreamcast/game/obj').exists()
 command=json.loads((off/'command.json').read_text());assert command==plan['commands']['off'] and sha(off/'command.json')==failed['arms']['off']['command_sha256']
 log=(off/'build.log').read_text();linklines=[l for l in log.splitlines() if 'bash tools/link.sh ' in l];assert len(linklines)==1
 objects=[x for x in shlex.split(linklines[0]) if x.endswith('.o')]
 helper=off/'out/obj/platform/gc_asset_motion_unknown.o'
 scratch=off/'source/port/dreamcast/game/obj'
 assert (scratch/'missing.txt').is_file() and not (scratch/'missing.txt').stat().st_size
 for q in (scratch/'aliases.ld',scratch/'missing.cpp'):
  assert 'gcasset' not in q.read_text() and 'motion_unknown' not in q.read_text()
 resolved=dict(x.split('=',1) for x in (off/'out/resolved-knobs.txt').read_text().splitlines() if '=' in x and not x.startswith('#'))
 expect={'GC_ASSET_GATE':'0','GC_ASSET_MOTION_UNKNOWN':'0','GC_ASSET_CATALOG_SHA256':'0','STAT_ROUTINE_BYTES':'1','KOS_CACHE_P2':'1','KOS_CACHE_P2_DIAG':'0','SCENERY_DEDUP':'0','SCENERY_EMIT_PREFETCH':'0','SCENERY_SELECT_LEAN2':'0','CPU_BACKFACE':'0','ACTOR_BACKFACE':'0','VRAM_ROOM_ARENA':'0','PC_SAMPLER':'0','DBG_WARP':'0'}
 assert all(resolved.get(k)==v for k,v in expect.items())
 addresses={}
 for l in (off/'symbols.txt').read_text().splitlines():
  a=l.split()
  if len(a)>=3 and a[-1] in ('_end','_etext','_edata','__bss_start','__bss_end'):addresses[a[-1]]=int(a[0],16)
 overlays=sorted((off/'out').glob('*.ovl'));assert {q.name for q in overlays}=={x.lower()+'.ovl' for x in plan['expected_overlays']}
 files={q.name:dict(bytes=q.stat().st_size,sha256=sha(q)) for q in [off/'out/re4dc-game.elf',off/'program.bin',*overlays]}
 readback=dict(complete=True,completion_kind='VALIDATED_COMPLETED_OFF_NO_RECOMPILE',raw_object_count=len(objects),linked_motion_objects=[x for x in objects if x.endswith('/gc_asset_motion_unknown.o')],compiled_motion=[l for l in log.splitlines() if '-c platform/gc_asset_motion_unknown.cpp ' in l],helper=empty_elf(helper),raw_sha256=sha(off/'program.bin'),OFF_overlay_identity={q.name:sha(q)==sha(Path('/root/probe/lanes/route/out-rrfb254e8rP')/q.name) for q in overlays},missing_bytes=0,addresses=addresses,files=files,size=(off/'size.txt').read_text(),build_log_sha256=sha(off/'build.log'),resolved_sha256=sha(off/'out/resolved-knobs.txt'))
 semantic_check(readback)
 # Meaningful negative controls change the actual semantic readback, not checks.
 negatives=[]
 for label,change in [('nonempty-helper',lambda r:r['helper'].update(allocated_bytes=4)),('OFF-Motion-flag',lambda r:r['compiled_motion'].__setitem__(0,r['compiled_motion'][0]+' -DRE4DC_GC_ASSET_MOTION_UNKNOWN=1')),('helper-linked-OFF',lambda r:r['linked_motion_objects'].append(str(helper))),('OFF-wrong-main',lambda r:r.update(raw_sha256='0'*64)),('dropped-overlay',lambda r:r['OFF_overlay_identity'].pop(next(iter(r['OFF_overlay_identity']))))]:
  r=copy.deepcopy(readback);change(r)
  try:semantic_check(r)
  except AssertionError:negatives.append(label)
  else:raise AssertionError('Negative escaped '+label)
 continuation=root/'continuation-v1';assert not continuation.exists();continuation.mkdir()
 contract=dict(source=SOURCE,scope='OFF completed validation plus fresh ON-only normal full build; no stage/guest/catalog/provenance/coverage acceptance',original_failed_receipt_sha256=sha(old),original_runner_sha256=sha(PREP/'run_full_pair.py'),preparation_sha256=sha(PREP/'PREPARATION.json'),off=readback,off_preservation_pins=pins(off),negative_controls=negatives,result=str(continuation/'receipt.json'),no_execution=dict(SDK=0,Make_queries=0,links=0,compiles=0))
 (HERE/'CONTINUATION.json').write_text(json.dumps(contract,indent=2)+'\n')
 original=(PREP/'run_full_pair.py').read_text()
 transformed=original.replace("OWN=Path(__file__).resolve().parent", "OWN=Path(__file__).resolve().parent\nPREP=OWN.parent/'full-link-prep'")
 transformed=transformed.replace("plan=json.loads((OWN/'PREPARATION.json').read_text());root=Path(plan['root']);budget=plan['budget']", "plan=json.loads((PREP/'PREPARATION.json').read_text());root=Path(plan['root']);budget=plan['budget']\n contract=json.loads((OWN/'CONTINUATION.json').read_text());result=Path(contract['result'])\n if os.environ.get('GC_MOTION24_CONTINUATION_ALLOCATED')!=contract['original_failed_receipt_sha256']:raise RuntimeError('Root continuation allocation required')")
 transformed=transformed.replace("if (root/'receipt.json').exists():raise RuntimeError('No restart or overwrite of unique run')", "if result.exists():raise RuntimeError('No restart or overwrite of continuation')")
 transformed=transformed.replace("sha(OWN/'PREPARATION.json')", "sha(PREP/'PREPARATION.json')")
 transformed=transformed.replace("'arms':{},'complete':False", "'arms':{'off':contract['off']},'original_failed_receipt_sha256':contract['original_failed_receipt_sha256'],'continuation_sha256':sha(OWN/'CONTINUATION.json'),'complete':False")
 transformed=transformed.replace("def save():(root/'receipt.json').write_text", "def save():result.write_text")
 transformed=transformed.replace("def check():\n", "def check():\n  if sha(root/'receipt.json')!=contract['original_failed_receipt_sha256'] or sha(PREP/'run_full_pair.py')!=contract['original_runner_sha256']:raise RuntimeError('Original failure evidence changed')\n  for p,row in contract['off_preservation_pins'].items():\n   if Path(p).stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Completed OFF changed '+p)\n")
 transformed=transformed.replace("for name in ['off','on']:", "for name in ['on']:")
 transformed=transformed.replace("assert len(compiled_motion)==(name=='on')", "assert len(compiled_motion)==1")
 assert transformed!=original and "for name in ['off','on']:" not in transformed
 assert "def save():(root/'receipt.json')" not in transformed
 compile(transformed,str(HERE/'continue_full_pair.py'),'exec')
 (HERE/'continue_full_pair.py').write_text(transformed)
 print(json.dumps(dict(status='PREPARED_NOT_RUN',off_raw=readback['raw_sha256'],OFF_objects=len(objects),OFF_empty_helper=readback['helper'],OFF_overlays=len(overlays),negative_controls=negatives,OFF_preserved_files=len(contract['off_preservation_pins']),failed_receipt_sha256=contract['original_failed_receipt_sha256'],contract_sha256=sha(HERE/'CONTINUATION.json')),indent=2))
if __name__=='__main__':main()
