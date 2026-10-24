"""Root-only continuation: preserve OFF/failure, verify it, build only fresh ON."""
from pathlib import Path
import importlib.util,sys,json,os,signal,time,hashlib
HERE=Path(__file__).resolve().parent;ORIGINAL=HERE.parent/'kos-census-preparation-v1'
sys.path.insert(0,str(HERE));sys.path.insert(1,str(ORIGINAL))
import graph,prepare as p,run as safety
support=HERE.parent/'full-link-review/verify_completed_pair.py'
s=importlib.util.spec_from_file_location('elf_support',support);elfreader=importlib.util.module_from_spec(s);s.loader.exec_module(elfreader)
def write(path,data):
 with path.open('x') as f:json.dump(data,f,indent=2);f.write('\n')
def main():
 for sig in [signal.SIGTERM,signal.SIGHUP,signal.SIGINT]:signal.signal(sig,safety.signal_stop)
 assert not {k for k in safety.INJECTION if os.environ.get(k)}
 contract=p.read(HERE/'CONTINUATION-CONTRACT.json')
 assert os.environ.get('GC_CENSUS_CONTINUATION')==p.sha(HERE/'CONTINUATION-CONTRACT.json')
 grant=Path(os.environ.get('GC_CENSUS_CONT_GRANT','/nonexistent'));assert p.sha(grant)==os.environ.get('GC_CENSUS_CONT_GRANT_SHA')
 g=p.read(grant);assert g['approved'] and g['contract_sha256']==p.sha(HERE/'CONTINUATION-CONTRACT.json') and g['source']==p.SOURCE and g['authorization']=='GC_CENSUS_OFF_RECHECK_ON_BUILD'
 p.verify(contract['pins']);safety.tool_integrity();locks=safety.actual_locks();plan=p.read(ORIGINAL/'PREPARATION.json');root=Path(plan['root']);budget=plan['budget']
 assert os.environ.get('GC_KOS_CENSUS_SOURCE')==p.SOURCE and os.environ.get('GC_KOS_CENSUS_PLAN')==p.sha(ORIGINAL/'PREPARATION.json')
 safety.integrity(plan);p.verify(p.read(HERE/'OFF-EXISTING-PINS.json'))
 assert p.sha(root/'census-receipt.json')==contract['original_failure_sha256']
 result=root/'root-continuation-v1';result.mkdir(exist_ok=False)
 def used():return safety.owned_bytes(root)+p.used(HERE)
 safety.check_capacity(budget,p.free('/mnt/c'),p.free('/dev/shm'),used(),admission=True)
 assert not safety.release_active()
 report={'source':p.SOURCE,'complete':False,'scope':'OFF fresh link preserved from prior reader failure and reverified; ON fresh link in this continuation. Diagnostic routes/bytes only, not guest/memory/coverage acceptance.','original_failure_sha256':contract['original_failure_sha256'],'contract_sha256':p.sha(HERE/'CONTINUATION-CONTRACT.json'),'locks':locks,'arms':{}}
 try:
  for arm in ['off','on']:
   started=time.monotonic();deadline=started+600;adir=result/arm;adir.mkdir();base=root/arm;out=base/'out';source=base/'source';scratch=source/'port/dreamcast/game/obj'
   def monitor():
    safety.actual_locks();safety.check_capacity(budget,p.free('/mnt/c'),p.free('/dev/shm'),used())
    assert not safety.release_active(),'Release priority'
    assert time.monotonic()<deadline,'Whole arm deadline600s'
   def integrity():
    p.verify(contract['pins']);safety.tool_integrity();safety.integrity(plan)
    assert p.sha(root/'census-receipt.json')==contract['original_failure_sha256']
    p.verify(p.read(HERE/'OFF-EXISTING-PINS.json'))
   integrity();monitor();env=dict(plan['environment'][arm],D367_SLOT_HELD='1',PYTHONPYCACHEPREFIX=str(adir/'child-cache'))
   if arm=='on':
    assert not out.exists() and not scratch.exists() and not(base/'build.log').exists() and not(base/'program.bin').exists()
    assert p.actual_preflight(source,plan['commands'][arm])['returncode']==0
    (base/'tmp').mkdir();p.emit(base/'command.json',plan['commands'][arm])
    with(base/'build.log').open('x') as log:safety.owned_child(plan['commands'][arm],log,deadline,monitor,cwd=source,env=env)
   assert p.read(base/'command.json')==plan['commands'][arm]
   assert (scratch/'missing.txt').is_file() and (scratch/'missing.txt').stat().st_size==0
   text=(scratch/'aliases.ld').read_text()+(scratch/'missing.cpp').read_text()
   assert not any(n in text for n in ['__wrap_malloc','__wrap_memalign','kos_census','motion_unknown','gcasset'])
   resolved=dict(x.split('=',1) for x in (out/'resolved-knobs.txt').read_text().splitlines() if '='in x and not x.startswith('#'))
   proposal=p.read(p.AUDIT/'NEXT-DIAGNOSTIC-PAIR.json');required=dict(proposal['common_required_resolved']);required.update(proposal['arm_required_resolved'][arm]);assert all(resolved.get(k)==v for k,v in required.items())
   elf=out/'re4dc-game.elf';raw=base/'program.bin';tools='/opt/toolchains/dc/sh-elf/bin/'
   if arm=='on':
    with(adir/'objcopy.log').open('x') as log:safety.owned_child([tools+'sh-elf-objcopy','-R','.stack','-O','binary',str(elf),str(raw)],log,deadline,monitor,env=env)
   proof=graph.verify(elf,base/'build.log',arm,plan['baseline_wraps'][arm]);assert len(proof['routes'])==13
   assert all(Path(x).resolve().is_relative_to((out/'obj').resolve()) for x in proof['graph']['ordered_objects'])
   parsed=elfreader.elf(elf,True);assert {k:parsed['raw_from_ELF'][k] for k in ['bytes','sha256']}==p.row(raw)
   overlays=sorted(out.glob('*.ovl'));assert {x.name for x in overlays}=={x.lower()+'.ovl' for x in plan['expected_overlays']}
   deps=safety.post_external_deps(root,arm,plan['input_pins'])
   for tool,flags,name in [('sh-elf-nm',['-S'],'symbols.txt'),('sh-elf-size',[],'size.txt'),('sh-elf-size',['-A'],'sections.txt')]:
    with(adir/name).open('x') as log:safety.owned_child([tools+tool,*flags,str(elf)],log,deadline,monitor,env=env)
   assert parsed['addresses']==elfreader.nm_addresses(adir/'symbols.txt') and parsed['sizes']==elfreader.size_default((adir/'size.txt').read_text())
   write(adir/'MODE1-GRAPH.json',proof);monitor();integrity()
   report['arms'][arm]={'complete':True,'seconds':time.monotonic()-started,'fresh_link_in_this_continuation':arm=='on','files':{x.name:p.row(x) for x in [elf,raw,*overlays]},'addresses':parsed['addresses'],'sizes':parsed['sizes'],'mode1_graph':str(adir/'MODE1-GRAPH.json'),'mode1_graph_sha256':p.sha(adir/'MODE1-GRAPH.json'),'actual_dependency_postcheck':deps,'build_log_sha256':p.sha(base/'build.log'),'resolved_sha256':p.sha(out/'resolved-knobs.txt')}
   print(arm+' graph13/ELF/raw/overlays complete',flush=True)
  integrity();report['complete']=True;report['owned_bytes']=used();report['delta']={k:report['arms']['on']['sizes'][k]-report['arms']['off']['sizes'][k] for k in ['text','data','bss']};report['linked_end_delta']=report['arms']['on']['addresses']['_end']-report['arms']['off']['addresses']['_end']
 except BaseException as e:report['failure']=repr(e);raise
 finally:write(result/'receipt.json',report)
if __name__=='__main__':main()
