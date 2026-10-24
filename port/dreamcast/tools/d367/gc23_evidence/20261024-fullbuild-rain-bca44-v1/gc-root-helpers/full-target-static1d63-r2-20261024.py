from pathlib import Path
import hashlib,json,os,shlex,signal,subprocess,time
TREE=Path('/root/work/lanes/gc-port23')
PROFILE=Path('/root/probe/lanes/route/out-rrfb254e8rP')
ROOT=Path('/root/work/lanes/gc-port23-full-target2-scratch')
SOURCE='1d63cffe3a232c402418f2f2d919e7abae476957'
FLOOR=24*1024**3
CAP=6*1024**3

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(TREE),*args],text=True).strip()
def space():
 s=os.statvfs('/mnt/c');return s.f_bavail*s.f_frsize

def main():
 if ROOT.exists():raise RuntimeError('Preserve existing root; no restart/overwrite')
 if git('rev-parse','HEAD')!=SOURCE or git('status','--porcelain'):raise RuntimeError('Source not frozen')
 module=TREE/'port/dreamcast/game/third_party/sh4zam'
 if subprocess.check_output(['git','-C',str(module),'rev-parse','HEAD'],text=True).strip()!='33fa4850cacb30dd0ad35485ef035526ec4ce782':raise RuntimeError('SH4ZAM source pin mismatch')
 if subprocess.check_output(['git','-C',str(module),'status','--porcelain'],text=True).strip() or not(module/'include/sh4zam/shz_xmtrx.h').is_file():raise RuntimeError('SH4ZAM dirty/missing')
 scratch=TREE/'port/dreamcast/game/obj'
 if scratch.exists():raise RuntimeError('Pre-existing linker scratch must be preserved separately')
 if space()<30*1024**3:raise RuntimeError('Need30GiB admission,24GiB floor')
 args=shlex.split((PROFILE/'candidate.txt').read_text())
 if any(not(a.split('=',1)[0].replace('_','').isalnum() and '=' in a) for a in args):raise RuntimeError('Unexpected actual candidate grammar')
 if any(a.startswith(('GC_ASSET_GATE=','GC_ASSET_CATALOG_SHA256=')) for a in args):raise RuntimeError('Unexpected baseline GC knob')
 pins={str(p):sha(p) for p in [PROFILE/'candidate.txt',PROFILE/'resolved-knobs.txt',PROFILE/'re4dc-game.elf',*(sorted(PROFILE.glob('*.ovl'))),Path('/root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a'),TREE/'port/dreamcast/game/third_party/sh4zam/lib/libsh4zam.a'] if p.is_file()}
 pins.update({str(p):sha(p) for p in module.rglob('*') if p.is_file() and p.suffix in ('.h','.hpp','.inc')})
 if len(list(PROFILE.glob('*.ovl')))!=14:raise RuntimeError('Baseline overlay inventory')
 ROOT.mkdir()
 report=dict(source=SOURCE,baseline='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2',profile=str(PROFILE),pins=pins,scope='Fresh actual normal full source rP builds using exact retained candidate overrides, catalog0. No media/stage/guest, installed catalog or I001 pass.',arms={},allocated_cap=CAP,floor=FLOOR,source_script_sha256=sha(__file__))
 (ROOT/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
 env=os.environ.copy();env.update(ASSETS='/root/probe/lanes/play-actor-bundle',JOBS='4',SOURCE_DATE_EPOCH='1760000000',PYTHONDONTWRITEBYTECODE='1',RE4DC_KOS_BASE='/root/work/kos-re4dc-d367')
 tool='/opt/toolchains/dc/sh-elf/bin/'
 baseline_raw=ROOT/'baseline-program.bin'
 subprocess.run([tool+'sh-elf-objcopy','-R','.stack','-O','binary',str(PROFILE/'re4dc-game.elf'),str(baseline_raw)],check=True)
 if sha(baseline_raw)!='49a4173a1792823ff5e275b0681b2c354c4e45140b7078d87c1253f2e926090b':raise RuntimeError('Actual production raw no longer matches')
 for name,value in [('off','0'),('on','1')]:
  if any(sha(Path(p))!=h for p,h in pins.items()) or git('rev-parse','HEAD')!=SOURCE or git('status','--porcelain'):raise RuntimeError('Frozen inputs changed')
  arm=ROOT/name;arm.mkdir();out=arm/'out';out.mkdir()
  env.update(OUT=str(out),OBJDIR=str(out/'obj'))
  command=['bash',str(TREE/'port/dreamcast/tools/d367/build-r21.sh'),*args,'GC_ASSET_GATE='+value,'GC_ASSET_CATALOG_SHA256=0']
  (arm/'command.json').write_text(json.dumps(command,indent=2)+'\n')
  started=time.monotonic()
  with (arm/'build.log').open('w') as log:
   child=subprocess.Popen(command,cwd=TREE,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   while child.poll() is None:
    elapsed=time.monotonic()-started
    used=sum(p.stat().st_size for r in [ROOT,scratch] if r.exists() for p in r.rglob('*') if p.is_file() and not p.is_symlink())
    if space()<FLOOR or used>CAP or elapsed>1200:
     reason=dict(pid=child.pid,free=space(),used=used,elapsed=elapsed)
     (arm/'owned-termination.json').write_text(json.dumps(reason,indent=2)+'\n')
     os.killpg(child.pid,signal.SIGTERM)
     try:child.wait(timeout=5)
     except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
     raise RuntimeError('Owned process terminated at allocation/time boundary: '+str(reason))
    time.sleep(2)
   if child.returncode:raise RuntimeError('Build failed '+name+' rc='+str(child.returncode)+'; preserve build.log')
  subprocess.run(['cp','-a',str(scratch),str(arm/'link-scratch')],check=True)
  if not(scratch/'missing.txt').is_file() or (scratch/'missing.txt').stat().st_size:raise RuntimeError('Missing symbol inventory not empty')
  elf=out/'re4dc-game.elf'
  subprocess.run([tool+'sh-elf-objcopy','-R','.stack','-O','binary',str(elf),str(arm/'program.bin')],check=True)
  symbols=subprocess.check_output([tool+'sh-elf-nm','-S',str(elf)],text=True)
  (arm/'symbols.txt').write_text(symbols)
  size=subprocess.check_output([tool+'sh-elf-size',str(elf)],text=True)
  actual=dict(x.split('=',1) for x in (out/'resolved-knobs.txt').read_text().splitlines() if '=' in x and not x.startswith('#'))
  expected=dict(GC_ASSET_GATE=value,GC_ASSET_CATALOG_SHA256='0',STAT_ROUTINE_BYTES='1',KOS_CACHE_P2='1',KOS_CACHE_P2_DIAG='0',SCENERY_DEDUP='0',SCENERY_EMIT_PREFETCH='0',SCENERY_SELECT_LEAN2='0',CPU_BACKFACE='0',ACTOR_BACKFACE='0',VRAM_ROOM_ARENA='0',PC_SAMPLER='0',DBG_WARP='0')
  bad={k:[v,actual.get(k)] for k,v in expected.items() if actual.get(k)!=v}
  if bad:raise RuntimeError('Resolved profile mismatch '+str(bad))
  overlays=sorted(out.glob('*.ovl'))
  if len(overlays)!=14:raise RuntimeError('New overlay inventory')
  files={p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in [elf,*overlays]}
  if name=='off':
   if sha(arm/'program.bin')!=sha(baseline_raw):raise RuntimeError('OFF full programme differs')
   for p in overlays:
    if sha(p)!=sha(PROFILE/p.name):raise RuntimeError('OFF overlay differs '+p.name)
  if any(sha(Path(p))!=h for p,h in pins.items()) or git('rev-parse','HEAD')!=SOURCE or git('status','--porcelain'):raise RuntimeError('Post-build frozen source/SDK/profile changed')
  report['arms'][name]=dict(seconds=time.monotonic()-started,files=files,raw_sha256=sha(arm/'program.bin'),resolved_sha256=sha(out/'resolved-knobs.txt'),buildlog_sha256=sha(arm/'build.log'),missing_bytes=0,size=size,off_programme_and14_identical=name=='off',catalog_pin='0',free_after=space())
  (ROOT/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
  print(name+' FULL NORMAL LINK COMPLETE '+size.strip()+'; no runtime/GC-ASSET acceptance',flush=True)
 report['complete']=True
 (ROOT/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
 print('BOTH NORMAL LINKS COMPLETE; OFF production image+14 identity; catalog0 budget only',flush=True)
if __name__=='__main__':main()