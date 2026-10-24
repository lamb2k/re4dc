"""Execute reviewed current4be QA media plan only; no SDK or guests."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
C=Path('/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23')
T=Path('/root/work/lanes/dedup-offline23-qa-4be08e01')
S='4be08e0110592510e3630c01fa9f49b3ac2fed3d'
PLAN=E/'private-qa-plan-prelink.json'
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
def floor(initial=False):
 n=shutil.disk_usage('/mnt/c').free;assert n>=(28.5 if initial else 24)*1024**3,('C floor',n)
 return n
def call(argv,log,extra=None,cwd=None):
 floor();env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PRUNE_AUTO='0',SOURCE_DATE_EPOCH='1760000000');env.update(extra or {})
 with log.open('w') as f:subprocess.run(argv,env=env,cwd=cwd,stdout=f,stderr=subprocess.STDOUT,check=True)
 floor()
def main():
 free=floor(True);assert sha(PLAN)=='a05bfbf69967716c26cdfcab07b025679899c5630267ce71564b54b00a147148'
 plan=json.loads(PLAN.read_text());pins=json.loads((E/'qa-programme-pins-r1.json').read_text());assert plan['source']==pins['source']==S
 assert json.loads((E/'gdemu10-gates-r1.json').read_text())['status']=='PASS_TEN_ACTUAL_CURRENT_GDEMU_SEEDS'
 assert subprocess.check_output(['git','-C',str(T),'rev-parse','HEAD'],text=True).strip()==S
 assert not subprocess.check_output(['git','-C',str(T),'status','--porcelain'],text=True)
 for arm in ('off','on'):
  x=plan['arms'][arm];p=pins['arms'][arm];assert sha(Path(x['program_out'])/'re4dc-game.elf')==p['elf_sha256']
  assert sha(Path(x['program_out'])/'resolved-knobs.txt')==p['resolved_sha256']
  for n,h in p['overlays'].items():assert sha(Path(x['program_out'])/n)==h
  assert not Path(plan['private_destinations'][arm]).exists()
  assert not Path(x['pkgtree']['environment']['PKG_K']).exists()
 for a in plan['alternates']:assert Path(a['path']).stat().st_size==a['bytes'] and sha(Path(a['path']))==a['sha256']
 media=E/'qa-media-r1';assert not media.exists();media.mkdir()
 (media/'admission.json').write_text(json.dumps(dict(source=S,initial_c_free=free,reserved_bytes=int(4.5*1024**3),initial_floor_bytes=int(28.5*1024**3),stage_floor_bytes=24*1024**3,authority='Root explicit4.5GiB reserve; no SDK/ZIP/recipe changes',plan_sha256=sha(PLAN),programmes_sha256=sha(E/'qa-programme-pins-r1.json')),indent=2)+'\n')
 rows={}
 for arm in ('off','on'):
  x=plan['arms'][arm];p=pins['arms'][arm];r=Path(x['pkgtree']['environment']['PKG_K']);r.mkdir(parents=True);logs=r/'logs';logs.mkdir();(r/'fix').mkdir()
  dest=Path(plan['private_destinations'][arm]);dest.mkdir()
  (dest/'QUALIFICATION-PENDING.txt').write_text('Private source4be normal QA candidate; gates/root review pending. No SD/publication.\n')
  call(x['stage']['argv'],logs/'t11-fix.txt',x['stage']['environment'])
  call(x['pkgtree']['argv'],logs/'pkgtree.txt',x['pkgtree']['environment'])
  assert 'PKGTREE_OK' in (logs/'pkgtree.txt').read_text()
  for i,argv in enumerate(x['presets']):call(argv,logs/f'presets-{i}.txt')
  src=Path(x['preset_copy']['source']);dst=Path(x['preset_copy']['destination']);assert not dst.exists();shutil.copytree(src,dst)
  tree=r/'pkgtree'
  for n in ('warp.txt','padscript.txt','w11.txt','crashtest.txt'):assert not (tree/'dc'/n).exists()
  for n,h in p['overlays'].items():assert sha(tree/'dc'/n)==h
  for a in plan['alternates']:assert sha(tree/a['destination'])==a['sha256']
  argv=x['master']['argv'][:];argv[-1]=str(dest/'gdemu');call(argv,logs/'mkgdi.txt',x['master']['environment'],x['master']['cwd'])
  for profile in ('loader','standard'):call(['python3',str(T/'port/dreamcast/tools/d367/disc_lint.py'),'--profile',profile,str(dest/'gdemu/disc.gdi')],logs/f'lint-{profile}.txt')
  manifest=media/(arm+'-final-manifest.json')
  call(['python3',str(T/'port/dreamcast/tools/d367/fullplay/fp_iso.py'),'manifest',str(dest/'gdemu/track03.bin'),'-o',str(manifest)],logs/'final-readback.txt')
  m=json.loads(manifest.read_text());assert m['1ST_READ.BIN']['sha256']==p['raw_sha256']
  for n,h in p['overlays'].items():assert m['dc/'+n]['sha256']==h
  for a in plan['alternates']:assert m[a['destination']]['sha256']==a['sha256']
  reference=json.loads(Path('/root/work/lanes/dedup-offline23-current-d5c-scratch/standard/on/manifest.json').read_text())
  allowed={'1ST_READ.BIN'}|{'dc/'+n for n in p['overlays']}
  for n,v in reference.items():
   if n not in allowed:assert m.get(n,{}).get('sha256')==v['sha256'],('baseline asset changed',arm,n)
  assert all(n in reference or n.startswith('dc/qa/') for n in m),('unrelated extra file',arm)
  tracks={n:dict(bytes=(dest/'gdemu'/n).stat().st_size,sha256=sha(dest/'gdemu'/n)) for n in ('disc.gdi','track01.bin','track02.raw','track03.bin','IP.BIN')}
  rows[arm]=dict(path=str(dest),work=str(r),programme=p,tracks=tracks,manifest=str(manifest),manifest_sha256=sha(manifest),baseline_nonprogramme_assets_equal=True,exact4_alternates_on_both_arms=True,c_free_after=floor())
  (dest/'MEDIA-IDENTITY.json').write_text(json.dumps(dict(source=S,status='FINAL_MEDIA_READBACK_PASS_QA_GUEST_GATES_PENDING',**rows[arm]),indent=2)+'\n')
  print('FINAL_QA_GDI_READY',arm,tracks['track03.bin']['sha256'],flush=True)
 a=json.loads(Path(rows['off']['manifest']).read_text());b=json.loads(Path(rows['on']['manifest']).read_text());allowed={'1ST_READ.BIN'}|{'dc/'+n for n in pins['arms']['off']['overlays']}
 diff=[n for n in a.keys()|b.keys() if a.get(n,{}).get('sha256')!=b.get(n,{}).get('sha256')]
 assert set(diff)<=allowed,diff
 (media/'pair-media-identity.json').write_text(json.dumps(dict(status='PASS_FINAL_STANDARD_LOADER_READBACK_COMMON_DATA_QA_GATES_PENDING',source=S,arms=rows,only_programme_differences=diff,limits='FinalGDI actual file/fulltrack readback, originals+fouralternates/common QA data retained. No guest/physical/performance acceptance from mastering.'),indent=2)+'\n')
 print('QA_FINAL_PAIR_MASTERED',flush=True)
if __name__=='__main__':main()

