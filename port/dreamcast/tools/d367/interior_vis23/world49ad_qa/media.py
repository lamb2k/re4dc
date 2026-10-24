"""Owned 49ad private QA media staging. No recipe/runtime changes or old output deletion.
Default command only seals a plan; mutations require named stage/proxy actions.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json,os,re,shutil,subprocess,sys,time
SOURCE='49ad20f9932d638ddb7becf5db6f86b92e0a76a2'
TREE=Path('/root/work/lanes/interior-world49ad-qa')
TOOLS=TREE/'port/dreamcast/tools/d367'
BASE=Path('/root/work/lanes/stat-bytes23-takeover-scratch/release')
PKG=Path('/mnt/c/Game Dev/Emulators/re4-assets-private/worldemit-ui-pair23-20261023-v2')
KEY='dc/tex/7/7d4e1e92-052bdc2e.re4tex'
CSHA='18978dc1b97247dcd5fda5f5f1744b74e9d1b97c34dc5779977525b0a2dc477e'
P=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/interior-vis23-20261023/world49ad-qa-programmes')
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/world-emit23-takeover/49ad20f9/final-qa-stage')
WORK=Path('/root/work/lanes/interior-world49ad-qa-media')
HOST=Path('/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23')
WINPY='/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe'
FINAL={a:Path('/mnt/c/Game Dev/Emulators/RE4DC-QA23-WorldEmit-'+a.title()+'-49ad20f9') for a in ('off','both')}
SEAL='07c9bc1e180a70aa5a85fe7235a6a546881270971406d24f5ccbf9dcefc33c64'

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def row(p):return dict(size=Path(p).stat().st_size,sha256=sha(p))
def read(p):return json.loads(Path(p).read_text())
def fresh(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def run(cmd,log,env=None):
 with Path(log).open('x') as f:subprocess.run([str(x) for x in cmd],stdout=f,stderr=subprocess.STDOUT,env=env,check=True)
def win(p):return subprocess.check_output(['wslpath','-w',str(p)],text=True).strip()
def floor(admit=False):
 w=int(subprocess.check_output([WINPY,'-c',"import shutil;print(shutil.disk_usage('C:\\\\').free)"],text=True).strip())
 l=shutil.disk_usage('/mnt/c').free
 x=dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),windows_free=w,wsl_free=l,lower_free=min(w,l),required=int((28.5 if admit else 24)*1024**3))
 assert min(w,l)>=x['required'],x
 return x

def check_inputs():
 assert subprocess.check_output(['git','-C',str(TREE),'rev-parse','HEAD'],text=True).strip()==SOURCE
 assert not subprocess.check_output(['git','-C',str(TREE),'status','--porcelain'],text=True).strip()
 assert sha(P/'SHA256-MANIFEST.json')==SEAL
 for pin in read(P/'SHA256-MANIFEST.json')['files'].values():
  assert row(pin['path'])==dict(size=pin['bytes'],sha256=pin['sha256']),pin['path']
 assert sha(BASE/'manifest.json')=='a424cdc4f68460b0d5ea8f591c44c62eefeab85b67941410bc996680dce41547'
 assert sha(BASE/'IP.BIN')=='0e4e13d0b8df6477d9e43370591fd1a580c54b4df2209b944610d2a0b6b0062c'
 assert row(PKG/'files'/KEY)==dict(size=32912,sha256=CSHA)
 assert sha(PKG/'local-pack.json')=='06d07cc7dceedd84fbcf30e7d496f4e487551e59efce109f6f3da2550fbb3825'
 opt=read(PKG/'local-pack.json');assert opt['replace']=={KEY:str(PKG/'files'/KEY)} and opt['default']==0 and opt['production_enabled'] is False
 proof=Path('/mnt/c/Game Dev/Emulators/codex-lanes/worldemit-ui-pair23/PACK-ABSENCE.json')
 assert sha(proof)=='3c6d25c05314e584a57d01d53be6ab6209c2514803c8178c33b410a713a9a6fe'
 ab=read(proof);assert not ab['found'] and ab['source']==SOURCE
 assert sha(ab['pack']['path'])==ab['pack']['sha256']
 for rel,pin in ab['lookup_sources'].items():assert sha(TREE/rel)==pin['sha256']
 pins=read('/mnt/c/Game Dev/Emulators/codex-lanes/world-emit23/current-gates/pins.json')
 for rel,s in pins['tools'].items():assert sha(TOOLS/rel)==s,rel
 for rel,s in pins['host_tools'].items():assert sha(HOST/rel)==s,rel
 return pins

def plan():
 check_inputs();assert not WORK.exists() and not E.exists()
 for p in FINAL.values():assert not p.exists(),p
 base=read(BASE/'manifest.json');assert len(base)==1712 and KEY not in base
 actual={str(p.relative_to(BASE/'tree')):row(p) for p in (BASE/'tree').rglob('*') if p.is_file()};assert actual==base
 qa={str(p.relative_to(P/'preset-plan-snapshot')):row(p) for p in (P/'preset-plan-snapshot').glob('*.txt')}
 assert len(qa)==34 and 'menu.txt' in qa
 menu=(P/'preset-plan-snapshot/menu.txt').read_text();assert len([l for l in menu.splitlines() if l.startswith('p ')])==33
 common=dict(base);common[KEY]=row(PKG/'files'/KEY)
 for k,v in qa.items():common['dc/qa/'+k]=v
 pr=read(P/'PROGRAMME-HANDBACK.json')['programmes'];expected={}
 for arm in FINAL:
  m=dict(common);m['1ST_READ.BIN']=dict(size=pr[arm]['main']['bytes'],sha256=pr[arm]['main']['sha256'])
  for k,v in pr[arm]['overlays'].items():m['dc/'+k]=dict(size=v['bytes'],sha256=v['sha256'])
  assert len(pr[arm]['overlays'])==14;expected[arm]=m
 adm=floor(True)
 obj=dict(schema=1,source=SOURCE,programme_seal=SEAL,programme_handback=row(P/'PROGRAMME-HANDBACK.json'),recipe=row(TOOLS/'rr/recipe.conf'),admission=adm,admission_gib=28.5,stage_floor_gib=24,absolute_floor_gib=20,reservation_bytes=4831838208,peak_model=dict(final_pair_bytes=2376122880,one_active_iso_budget=1050000000,captures_metadata_budget=134217728,total=3560340608),asset_change=dict(path=KEY,identity=row(PKG/'files'/KEY),private_default=0,production_enabled=False,visible_use_proven=False,label='LOAD/UPLOAD REPAIR ONLY; production look unapproved'),preserved_tex_pak=base['dc/tex.pak'],original_files=len(base),original_bytes=sum(v['size'] for v in base.values()),qa_files=qa,final_paths={k:str(v) for k,v in FINAL.items()},probe_bases={k:str(E/'probe-bases'/k) for k in FINAL},programme_paths={k:str(P/k) for k in FINAL},guests=dict(total=6,sequential=True,console=True,exact_child_limit_s=55,requested_s=45,stat_slots=3,trace_slots=16,boot='actual final standard raw2352 GDI, ordinary keys, no warp injection',menu_warp='fixture proxy; full assets and14 overlays equal final media',h2='fixture proxy; same QA programme; normal KOS no watch/squeeze'),cleanup='Only newly owned proxy track03.iso may be removed after all three arm gates pass and final independent readback. Preserve all captures, manifests, IP, programme and fixture identities. fp_run removes its own hardlinks, not the source tracks.',scope='Private console request pending review. Both experimental performance switches OFF in production. No gain, QA Mendez or physical console acceptance implied.',tools={k:row(TOOLS/k) for k in ['mkgdi.sh','disc_lint.py','fullplay/fp_master.sh','fullplay/fp_iso.py','fullplay/fp_run.py','trace_lock.sh']},mkdcdisc=row('/root/work/tools/mkdcdisc/builddir/mkdcdisc'),helper=row(Path(__file__)))
 fresh(E/'PLAN.json',obj);fresh(E/'original-manifest.json',base);fresh(E/'common-manifest.json',common)
 for a,m in expected.items():fresh(E/(a+'-expected-manifest.json'),m)
 fresh(E/'PLAN-SEAL.json',dict(plan=row(E/'PLAN.json'),original=row(E/'original-manifest.json'),common=row(E/'common-manifest.json'),expected={a:row(E/(a+'-expected-manifest.json')) for a in FINAL}))
 print(json.dumps(dict(plan=str(E/'PLAN.json'),sha256=sha(E/'PLAN.json'),admission=adm,files=len(common))))

def sealed():
 z=read(E/'PLAN-SEAL.json');assert row(E/'PLAN.json')==z['plan'];assert row(E/'common-manifest.json')==z['common']
 for a in FINAL:assert row(E/(a+'-expected-manifest.json'))==z['expected'][a]
 assert read(E/'PLAN.json')['source']==SOURCE

def common():
 sealed();check_inputs();fresh(E/'COMMON-ADMISSION.json',floor(True));assert not WORK.exists();WORK.mkdir(parents=True)
 subprocess.run(['cp','-al',str(BASE/'tree'),str(WORK/'common')],check=True)
 d=WORK/'common'/KEY;d.parent.mkdir(parents=True,exist_ok=True)
 with d.open('xb') as f:f.write((PKG/'files'/KEY).read_bytes())
 q=WORK/'common/dc/qa';q.mkdir()
 for p in (P/'preset-plan-snapshot').glob('*.txt'):shutil.copyfile(p,q/p.name)
 got={str(p.relative_to(WORK/'common')):row(p) for p in (WORK/'common').rglob('*') if p.is_file()}
 assert got==read(E/'common-manifest.json');fresh(E/'COMMON-READY.json',dict(manifest=row(E/'common-manifest.json'),actual_files=len(got),floor=floor()))

def readback(arm):
 sealed();d=FINAL[arm]/'gdemu';out=E/arm;out.mkdir(exist_ok=True,parents=True)
 iso=load('qa_iso',TOOLS/'fullplay/fp_iso.py');tr=iso.Track(d/'track03.bin',45000);got={};extents={}
 for p,e,n in iso.files(tr):
  key=p.lstrip('/');assert key not in got
  h=hashlib.sha256();remain=n;lba=e
  while remain:
   b=tr.read_bytes(lba,min(remain,1<<20));h.update(b);remain-=len(b);lba+=len(b)//2048
  got[key]=dict(size=n,sha256=h.hexdigest());extents[key]=dict(lba=e,size=n)
 tr.f.close();assert got==read(E/(arm+'-expected-manifest.json')),'Actual final GDI file mismatch'
 fresh(out/'final-readback-manifest.json',got);fresh(out/'final-extents.json',extents)
 # Read raw main back from actual disc, independently scramble it and match sealed QA CD programme.
 tr=iso.Track(d/'track03.bin',45000);er=extents['1ST_READ.BIN'];raw=tr.read_bytes(er['lba'],er['size']);tr.f.close()
 r=out/'readback-main-raw.bin';r.write_bytes(raw);s=out/'readback-main-scrambled.bin'
 scramble=Path('/root/work/kos-re4dc-d367/utils/scramble/scramble');assert scramble.is_file()
 subprocess.run([str(scramble),str(r),str(s)],check=True);assert row(s)==row(P/arm/'1ST_READ.BIN')
 run(['python3',TOOLS/'disc_lint.py','--profile','loader',d/'disc.gdi'],out/'disc-lint-loader.txt')
 tracks={p.name:row(p) for p in d.iterdir() if p.is_file()}
 fresh(out/'FINAL-READBACK.json',dict(source=SOURCE,arm=arm,full_manifest=row(out/'final-readback-manifest.json'),files=len(got),raw_main=row(r),scrambled_readback=row(s),all14_exact=True,qa_presets=33,qa_menu_exact=True,candidate=got[KEY],tex_pak=got['dc/tex.pak'],all_original_assets_preserved=True,tracks=tracks,physical_console_acceptance=False,qa_mendez_tested=False))
 return got

def stage(arm):
 sealed();check_inputs();assert (E/'COMMON-READY.json').exists();assert not FINAL[arm].exists()
 fresh(E/(arm+'-STAGE-ADMISSION.json'),floor(True));d=WORK/arm;assert not d.exists()
 subprocess.run(['cp','-al',str(WORK/'common'),str(d)],check=True)
 for k,p in [('1ST_READ.BIN',P/arm/'main-no-stack.bin')]+[('dc/'+p.name,p) for p in (P/arm).glob('*.ovl')]:
  dest=d/k;dest.unlink();shutil.copyfile(p,dest)
 got={str(p.relative_to(d)):row(p) for p in d.rglob('*') if p.is_file()};assert got==read(E/(arm+'-expected-manifest.json'))
 FINAL[arm].mkdir();tmp=WORK/('tmp-'+arm);tmp.mkdir()
 env=dict(os.environ,LAYOUT='standard',SECTOR='2352',PRUNE_AUTO='0',PAD_1ST='0',KOS_TOOLS_BASE='/root/work/kos-re4dc-d367',TMPDIR=str(tmp),TITLE='RE4DCQA23-WORLD',PERIPHERALS='0799810',PRODUCT='T0000')
 run(['bash',TOOLS/'mkgdi.sh',P/arm/'re4dc-game.elf',d,FINAL[arm]/'gdemu'],E/(arm+'-mkgdi.log'),env)
 fresh(E/(arm+'-POST-STAGE-FLOOR.json'),floor());readback(arm)
 print(json.dumps(dict(arm=arm,gdi=str(FINAL[arm]/'gdemu/disc.gdi'),readback='PASS',floor=floor())))

def proxy(arm):
 sealed();assert (E/arm/'FINAL-READBACK.json').exists();fresh(E/(arm+'-PROXY-ADMISSION.json'),floor())
 dest=E/'probe-bases'/arm;assert not dest.exists()
 env=dict(os.environ,PRUNE_AUTO='0',RE4DC_STAGE_EXT4='0')
 # The original IP is appropriate for the fixture redirect harness; final standard GDI IP is independently retained.
 run(['bash',TOOLS/'fullplay/fp_master.sh',WORK/arm,E/(arm+'-expected-manifest.json'),BASE/'IP.BIN',dest,P/arm],E/(arm+'-proxy-master.log'),env)
 got=read(dest/'base-manifest.json');expected=read(E/(arm+'-expected-manifest.json'))
 delta={k for k in set(got)|set(expected) if got.get(k)!=expected.get(k)};assert delta=={'dc/warp.txt','dc/padscript.txt','dc/w11.txt'},delta
 assert sha(dest/'track03.iso')==(dest/'track03.sha256').read_text().strip()
 fresh(E/arm/'PROXY-IDENTITY.json',dict(label='QA fixture proxy; not actual final GDI boot/physical console',delta=sorted(delta),main_and14_equal=True,all_assets_equal=True,track03=row(dest/'track03.iso'),base_json=row(dest/'base.json'),base_manifest=row(dest/'base-manifest.json'),ip=row(dest/'IP.BIN') if (dest/'IP.BIN').exists() else row(BASE/'IP.BIN'),floor=floor()))
 print(json.dumps(dict(arm=arm,proxy=str(dest),delta=sorted(delta))))

def cleanup(arm):
 sealed();assert (E/arm/'FINAL-READBACK.json').exists()
 for gate in ['boot','menu-warp','h2']:
  assert read(E/'captures'/(arm+'-'+gate)/'QUALIFIED.json')['pass'] is True
 p=E/'probe-bases'/arm/'track03.iso';assert p.resolve()==p and str(p).startswith(str(E/'probe-bases')+'/')
 assert row(p)==read(E/arm/'PROXY-IDENTITY.json')['track03']
 fresh(E/arm/'DELETED-PROXY-ISO.json',dict(path=str(p.resolve()),identity=row(p),label='Disposable new owned fixture ISO cache only',reason='All three QA arm gates and independent actual final GDI file readback passed; all manifests/IP/diff/logs/programmes/fixtures/captures retained.'))
 p.unlink();print(json.dumps(dict(deleted=str(p),floor=floor())))

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('action',choices=['plan','common','stage','proxy','cleanup']);a.add_argument('--arm',choices=list(FINAL));v=a.parse_args()
 if v.action in ('plan','common'):globals()[v.action]()
 else:assert v.arm;globals()[v.action](v.arm)

