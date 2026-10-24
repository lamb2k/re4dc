from pathlib import Path
import subprocess,json,re,hashlib,struct,shutil,sys
sys.dont_write_bytecode=True
TR=Path('/root/work/lanes/dedup-offline23-current-d5c');SHA='4be08e0110592510e3630c01fa9f49b3ac2fed3d';BASE='d5c1ceab9e06461462669b3ce1d28a379747a74a';CURRENT='d5c1ceab9e06461462669b3ce1d28a379747a74a'
EV=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01');R=Path('/root/work/lanes/dedup-offline23-current-d5c-scratch/standard')
def git(*a):return subprocess.check_output(['git','-C',str(TR),*a])
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024**2),b''):h.update(b)
 return h.hexdigest()
def pin(p):return dict(path=str(p),bytes=Path(p).stat().st_size,sha256=sha(p))
assert git('rev-parse','HEAD').decode().strip()==SHA
assert not git('status','--porcelain')
assert shutil.disk_usage('/mnt/c').free>=22*1024**3
assert not R.exists()
recipes={}
for label,ref in [('source712',SHA),('base82d',BASE),('current933',CURRENT)]:
 b=git('show',ref+':port/dreamcast/tools/d367/rr/recipe.conf');data=re.search(rb'^DATA="([^"]+)"$',b,re.M)[1].decode().split(',');recipes[label]=dict(source=ref,sha256=hashlib.sha256(b).hexdigest(),data=data)
assert len(recipes['source712']['data'])==29
assert recipes['source712']['data']==recipes['base82d']['data']==recipes['current933']['data']
manifest=TR/'port/dreamcast/tools/d367/dedup_offline23/strip-share-private-pins.json'
assert sha(manifest)=='af246116c7d408c9b44b52a9400e1255122b62502ae0018b2808fcc4d47a5b10'
pins=json.loads(manifest.read_text());alts=[]
for row in pins['variants']:
 for name,x in row['files'].items():
  p=Path(row['output_directory'])/name;assert p.stat().st_size==x['bytes'] and sha(p)==x['sha256'];alts.append(pin(p))
bases={}
for room,expected in {'r100':'130bac7969255f0bf31d5f9226cee21a33415103f044f0fdc7dda3607ffc89bb','r101':'500d17dac6279aa1ca71c8698ac31292cb2d3452befacfbef2d25069f9f7bff3','r103':'96d2382299065c6ab48f7696a88e37de7020fd0a21e37507d4bb87a0a739fdd3'}.items():
 p=Path('/root/re4payload/t164-20261018/tree/dc/native')/room/'ps2-world.re4mesh';assert sha(p)==expected;bases[room]=pin(p)
programs={}
for arm,mode in [('off',0),('on',3)]:
 label='fpdd23cur4be08e01'+arm+'gW';o=Path('/root/probe/lanes/route')/('out-'+label)
 assert (o/'stack.txt').read_text().splitlines()==[SHA]
 assert (o/'missing.txt').stat().st_size==0
 k=dict(l.split('=',1) for l in (o/'resolved-knobs.txt').read_text().splitlines() if '=' in l)
 expected=dict(ESP_POOL_RECYCLE='1',R117_EFFECT_FAILURE_SAFE='1',KOS_CACHE_P2='1',R10C_SPAWN_LIVE_GUARD='1',EM_READ_RETRY='1',STAT_ROUTINE_BYTES='1',STAT_DIAG='0',KOS_CACHE_P2_DIAG='0',VRAM_ROOM_ARENA='0',SCENERY_DEDUP=str(mode),SCENERY_SELECT_ONLY='1',SCENERY_REPLAY_LEAN='1',SCENERY_SUBMIT_BATCH='1',FX_LEVEL='3',FX_TRIM='1',QA_MENU='0',WORLD_METER='0',PC_SAMPLER='0',DBG_WARP='1',WARP_JUMP='1',TEX_CHECK='1',MCHECK_LEONGC='1',KOS_WATCH='0',NATIVE_MODEL_REGISTRY_CENSUS='0')
 assert all(k.get(n)==v for n,v in expected.items()),(arm,{n:k.get(n) for n in expected})
 overlays=sorted(o.glob('*.ovl'));assert len(overlays)==14
 raw=Path('/dev/shm')/('dedup-current4be-'+arm+'-raw.bin');assert not raw.exists()
 subprocess.run(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy','-R','.stack','-O','binary',str(o/'re4dc-game.elf'),str(raw)],check=True)
 dest=EV/('base-standard-current4be-'+arm+'-r1');capture=EV/('full-h2-standard-current4be-'+arm+'-console-r1')
 assert not dest.exists() and not capture.exists()
 programs[arm]=dict(label=label,source=SHA,resolved=expected,files={n:pin(o/n) for n in ('re4dc-game.elf','stack.txt','resolved-knobs.txt','syms.txt')},overlays={p.name:pin(p) for p in overlays},main_raw=pin(raw),base=str(dest),capture=str(capture))
tools={}
for n in ('test11/t11-fix.py','test8/t8-pkgtree.py','mkgdi.sh','disc_lint.py','fullplay/fp_iso.py','fullplay/fp_master.sh','fullplay/fp_run.py','fullplay/segments/h2-warp.txt','fullplay/segments/h2-pad.txt','trace_lock.sh'):
 p=TR/'port/dreamcast/tools/d367'/n;b=git('show',SHA+':port/dreamcast/tools/d367/'+n);assert sha(p)==hashlib.sha256(b).hexdigest();tools[n]=pin(p)
report=dict(kind='READ_ONLY_SOURCE_PROGRAM_ASSET_PREFLIGHT_NO_GUEST_YET',source=SHA,tree=str(TR),recipes=recipes,compact_manifest=pin(manifest),compact_alternates=alts,original_packages=bases,programs=programs,tools=tools,work=str(R),off_data='Original DATA29 only; no SDO3 alternate set',on_data='Same original DATA29 plus exact4 compact alternatives; original baseline files retained',host_free_bytes=shutil.disk_usage('/mnt/c').free)
out=EV/'current4be-preflight-r1.json';assert not out.exists();out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'source':SHA,'data29_equal_82d_933':True,'programmes':{a:p['label'] for a,p in programs.items()},'manifest_sha256':sha(manifest),'free_GiB':report['host_free_bytes']/1024**3,'receipt':str(out)}))