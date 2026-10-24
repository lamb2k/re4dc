"""Current49ad host-only staging/gates. Import and plan do not launch a guest or build."""
from pathlib import Path
import argparse,contextlib,hashlib,json,os,re,shutil,subprocess,sys,tempfile
HERE=Path(__file__).resolve().parent
SOURCE='49ad20f9932d638ddb7becf5db6f86b92e0a76a2'
PRIOR='5e4de9a0262d3629c9833c959557de198b2e9f0c'
E=Path(os.environ.get('WE23_CURRENT_EVIDENCE','/mnt/c/Flycast-Evidence/re4-dreamcast/world-emit23-takeover/49ad20f9'))
OLD=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/audits23-takeover/5e4de9a0')
REL=Path('/root/work/lanes/stat-bytes23-takeover-scratch/release')
HOST=Path('/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23')
WINPY='/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe'
OBJCOPY='/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy'
FLOOR=24*1024**3
ARMS={'R':(0,0),'L':(1,0),'E':(0,1),'B':(1,1)}
GATES={'h2':'g','kos0':'c','kos1':'c','gd1':'g','bench100':'c','bench101':'c','bell':'t','mendez':'t'}
BASE_KNOBS=dict(STAT_ROUTINE_BYTES=1,STAT_DIAG=0,ESP_POOL_RECYCLE=1,R117_EFFECT_FAILURE_SAFE=1,KOS_CACHE_P2=1,R10C_SPAWN_LIVE_GUARD=1,EM_READ_RETRY=1,SCENERY_SELECT_ONLY=1,SCENERY_REPLAY_LEAN=1,SCENERY_SUBMIT_BATCH=1,ACTOR_SETUP_LEAN=0,SCENERY_UV_SNAPSHOT=0,SCENERY_DEDUP=0,PS2_PVS=0,CPU_BACKFACE=0,ACTOR_BACKFACE=0,PC_SAMPLER=0,VRAM_ROOM_ARENA=0,R101_ALIVE_CAP=4,QUALITY=1,QUALITY_LOD_PX=5,SCENERY_FAR_LOD=4,ARENA_FIT_KOS_BYTES=196608)
class Refused(ValueError):pass
def require(value,message):
 if not value:raise Refused(message)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1<<20),b''):h.update(block)
 return h.hexdigest()
def jsonread(p):return json.loads(Path(p).read_text())
def fresh_json(path,row):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x') as f:json.dump(row,f,indent=2);f.write('\n')
def win(path):return subprocess.check_output(['wslpath','-w',str(path)],text=True).strip()
def tree(arm):return Path('/root/work/lanes/world-emit23-current-'+arm)
def tools(arm):return tree(arm)/'port/dreamcast/tools/d367'
def output(arm,profile):
 require(arm in ARMS and profile in ['p','g','c','t','m','n'],'unknown arm/profile')
 require(profile!='n' or arm=='R','only current R has a census programme')
 label='we23'+arm+'49ad'
 return Path('/root/probe/lanes/route')/('out-'+label+'r'+profile.upper() if profile in ['p','t'] else 'out-fp'+label+profile+'W')
def knobs(text):
 rows={}
 for line in text.splitlines():
  if '=' not in line:continue
  key,value=line.split('=',1)
  if re.fullmatch('[A-Z][A-Z0-9_]*',key):
   require(key not in rows,'duplicate resolved knob '+key);rows[key]=value
 return rows
def expected(arm,profile):
 s,p=ARMS[arm];d=dict(BASE_KNOBS,SCENERY_SELECT_LEAN2=s,SCENERY_EMIT_PREFETCH=p,SCENERY_EMIT_CENSUS=1200 if profile=='n' else 0,WORLD_METER=int(profile=='m'),GAME_TICK_LOG=60 if profile=='m' else 0,PHASE_METER=int(profile=='m'),DBG_WARP=int(profile!='p'),WARP_JUMP=int(profile not in ['p','t']),TEX_CHECK=int(profile not in ['p','t']),MCHECK_LEONGC=int(profile not in ['p','t']),KOS_WATCH=int(profile in ['c','n']),KOS_SQUEEZE=int(profile=='c'),W11_FIXTURE=int(profile=='c'),NATIVE_MODEL_REGISTRY_CENSUS=int(profile=='c'),NATIVE_MODEL_REGISTRY_CENSUS_PERIOD=150 if profile=='c' else 600)
 return {k:str(v) for k,v in d.items()}
def validate_knobs(actual,arm,profile):
 for k,v in expected(arm,profile).items():require(actual.get(k)==v,'wrong/missing '+k+': '+str(actual.get(k))+' expected '+v)
def file_identity(path):return {'sha256':sha(path),'size':path.stat().st_size}
def assets(manifest):
 require(isinstance(manifest,dict),'manifest not object');out={}
 for raw,row in manifest.items():
  require(isinstance(raw,str) and not raw.startswith('/') and '..' not in raw.split('/'),'unsafe asset manifest path')
  require(set(row)=={'size','sha256'} and type(row['size']) is int and row['size']>=0 and re.fullmatch('[0-9a-f]{64}',row['sha256']),'invalid asset row')
  if raw=='1ST_READ.BIN' or re.fullmatch(r'dc/[^/]+\.ovl',raw) or raw in ['dc/warp.txt','dc/padscript.txt','dc/w11.txt']:continue
  out[raw]=row
 return out
def asset_hash(manifest):return hashlib.sha256(json.dumps(assets(manifest),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def pins(arm):
 pin=jsonread(HERE/'pins.json');t=tree(arm);d=tools(arm)
 require(subprocess.check_output(['git','-C',str(t),'rev-parse','HEAD'],text=True).strip()==SOURCE,'source tree moved')
 require(not subprocess.check_output(['git','-C',str(t),'status','--porcelain'],text=True).strip(),'source tree dirty; preserve and stop')
 require(sha(d/'rr/recipe.conf')==pin['recipe_sha256'],'recipe changed')
 require(sha(REL/'manifest.json')==pin['manifest_sha256'] and sha(REL/'IP.BIN')==pin['ip_sha256'],'baseline manifest/IP changed')
 for name,h in pin['tools'].items():require(sha(d/name)==h,'tool changed '+name)
 for name,h in pin['host_tools'].items():require(sha(HOST/name)==h,'host guard changed '+name)
 require(sha(d/'../game30/decision_cmp.py')==pin['decision_cmp_sha256'],'decision checker changed')
 return pin
def raw_main(elf):
 with tempfile.TemporaryDirectory(prefix='world-current-raw-',dir='/dev/shm') as tmp:
  raw=Path(tmp)/'main.bin';subprocess.run([OBJCOPY,'-R','.stack','-O','binary',str(elf),str(raw)],check=True)
  return file_identity(raw)
def programme(folder,source=None):
 require((folder/'re4dc-game.elf').is_file() and not (folder/'missing.txt').read_text().strip(),'missing/failed programme')
 if source:require((folder/'stack.txt').read_text().strip()==source,'programme source/dirty stack mismatch')
 ovls=sorted(folder.glob('*.ovl'));require(len(ovls)==14,'exactly14 overlays required')
 before={p.name:(p.stat().st_size,p.stat().st_mtime_ns) for p in [folder/'re4dc-game.elf',*ovls]}
 result={'elf':file_identity(folder/'re4dc-game.elf'),'main':raw_main(folder/'re4dc-game.elf'),'overlays':{p.name:file_identity(p) for p in ovls}}
 after={p.name:(p.stat().st_size,p.stat().st_mtime_ns) for p in [folder/'re4dc-game.elf',*ovls]};require(before==after,'programme changed during hashing')
 return result
def inspect(arm,profile):
 pin=pins(arm);out=output(arm,profile);validate_knobs(knobs((out/'resolved-knobs.txt').read_text()),arm,profile);prg=programme(out,SOURCE)
 syms=(out/'syms.txt').read_text().strip();require(re.fullmatch(r'0x[0-9a-f]+ 0x[0-9a-f]+ 0x[0-9a-f]+',syms),'invalid three harness symbols')
 return {'schema':1,'source':SOURCE,'arm':arm,'profile':profile,'output':str(out),'programme':prg,'syms':syms,'resolved_knobs_sha256':sha(out/'resolved-knobs.txt'),'stack_sha256':sha(out/'stack.txt'),'recipe_sha256':pin['recipe_sha256'],'release_manifest_sha256':pin['manifest_sha256'],'asset_manifest_sha256':asset_hash(jsonread(REL/'manifest.json')),'script_sha256':sha(Path(__file__))}
def validate_stage_manifest(base_manifest,baseline,prg):
 require(assets(base_manifest)==assets(baseline),'staged assets differ from baseline')
 require(base_manifest.get('1ST_READ.BIN')==prg['main'],'staged raw main differs from programme')
 staged={k[3:]:v for k,v in base_manifest.items() if re.fullmatch(r'dc/[^/]+\.ovl',k)}
 require(staged==prg['overlays'],'staged overlays not exact14 target set')
def check_base(base,unit):
 meta=jsonread(base/'base.json');require(meta['elf']==str(Path(unit['output'])/'re4dc-game.elf'),'base ELF path mismatch')
 validate_stage_manifest(jsonread(base/'base-manifest.json'),jsonread(REL/'manifest.json'),unit['programme'])
 actual=sha(base/'track03.iso');require(actual==(base/'track03.sha256').read_text().strip(),'track03 digest mismatch')
 return {'base':str(base),'base_json_sha256':sha(base/'base.json'),'base_manifest_sha256':sha(base/'base-manifest.json'),'track03_sha256':actual,'track01_template':file_identity(base/'track01-template.iso'),'track02':file_identity(base/'track02.raw')}
def floor():require(shutil.disk_usage('/mnt/c').free>=FLOOR,'C below24GiB floor; no stage/guest')
def stage(arm,profile):
 unit=inspect(arm,profile);floor();base=E/'_discs'/(arm+'-'+profile);require(not base.exists(),'stage exists; preserve')
 base.parent.mkdir(parents=True,exist_ok=True)
 log=E/'identities'/(arm+'-'+profile+'-master.log');log.parent.mkdir(parents=True,exist_ok=True)
 require(profile!='p','root stage supports diagnostic profiles only');require(E==Path('/mnt/c/Flycast-Evidence/re4-dreamcast/world-emit23-takeover/49ad20f9'),'parent stager has one fixed evidence root');parent=HERE.parent/'takeover-stage-current-v1.sh';require(sha(parent)==jsonread(HERE/'pins.json')['parent_stage_sha256'],'parent stage helper changed')
 with log.with_name(log.stem+'-caller.log').open('x') as f:subprocess.run(['bash',str(parent),arm,profile],env=dict(os.environ,PRUNE_AUTO='0',RE4DC_STAGE_EXT4='1'),stdout=f,stderr=subprocess.STDOUT,check=True)
 unit['staged']=check_base(base,unit);fresh_json(E/'identities'/(arm+'-'+profile+'.json'),unit);return unit
def fixture(arm,gate):
 d=tools(arm);pin=jsonread(HERE/'pins.json');pad=None;stop=None;seconds=45;grace=2
 if gate=='h2':warp=d/'fullplay/segments/h2-warp.txt';pad=d/'fullplay/segments/h2-pad.txt';stop='route movie terminal=1 id=10030'
 elif gate.startswith('kos'):
  src=d/'fullplay/segments/kos-fight-warp.txt';warp=E/'_fixtures'/(gate+'.txt');data=('squeeze 49152 '+gate[-1]+'\n').encode()+src.read_bytes().replace(b'\r',b'')
  if warp.exists():require(warp.read_bytes()==data,'KOS fixture changed')
  else:warp.parent.mkdir(parents=True,exist_ok=True);warp.write_bytes(data)
 elif gate=='gd1':warp=d/'fullplay/segments/door103-warp.txt';stop='phase=enter room=103';grace=5
 elif gate.startswith('bench'):
  name='s2.txt' if gate=='bench100' else 'b1.txt';warp=HERE.parent/'fixtures'/name;require(sha(warp)==pin['fixtures'][name],'benchmark fixture changed');seconds=40
 elif gate=='bell':warp=d/'fullplay/segments/bell-trg-warp.txt';stop='route movie terminal=1 id=10130';seconds=53
 else:
  f=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23-20261023/mendez-bounded-itemack-r3');warp=f/'mendez-bounded-warp.txt';pad=f/'mendez-bounded-pad.txt';seconds=53;stop='phase=enter room=10f'
  for p in [warp,pad]:require(sha(p)==pin['fixtures'][p.name],'Mendez fixture changed')
 return warp,pad,stop,seconds,grace

def command(arm,gate,tag,unit):
 require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,79}',tag),'unsafe capture tag')
 warp,pad,stop,seconds,grace=fixture(arm,gate);base=E/'_discs'/(arm+'-'+GATES[gate]);cap=E/'captures'/tag
 cmd=['bash',str(HOST/'stat-guest-slot.sh'),'bash',str(tools(arm)/'trace_lock.sh'),WINPY,win(HOST/'census-bound-run.py'),win(tools(arm)/'fullplay/fp_run.py'),'--base',win(base),'--cap',win(cap),'--syms',unit['syms'],'--warp',win(warp),'--seconds',str(seconds),'--period','0','--name','world-current-'+tag]
 if pad:cmd+=['--pad',win(pad)]
 if stop:cmd+=['--stop',stop,'--grace',str(grace)]
 return cmd,cap,{'warp':{'path':str(warp),**file_identity(warp)},'pad':{'path':str(pad),**file_identity(pad)} if pad else None,'stop':stop,'seconds':seconds,'grace':grace,'period':0}

def gate_evidence(gate,text,run,bound,extra=None):
 bad=[line for line in text.splitlines() if re.search(r'HALT|FAULT|MISSING|Out of memory|\[LOG OVERRUN|no contiguous|upload FAILED|package rejected',line)]
 ok=run.get('status')=='RUN_COMPLETE' and not run.get('errors') and bound.get('guest_exited') and not bound.get('deadline_fired') and bound.get('deadline_seconds')==55
 r={'critical':bad,'bounded_complete':bool(ok),'observed':{},'pass':False,'evidence_kind':'Flycast console current-profile regression; not hardware/performance acceptance'};ok=ok and not bad
 if gate=='h2':
  term=re.search(r'route movie terminal=1 id=10030 frames=340/340 uploaded=340 presented=340[^\n]*heap_before=(\d+)',text);borrow=re.search(r'MOVIEARENA borrow id=10030 token=(\d+)\b',text)
  restored=bool(borrow and re.search(r'MOVIEARENA return token='+borrow[1]+r'\b[^\n]*restored=1',text));r['observed']={'full340':bool(term),'heap_before':int(term[1]) if term else None,'matching_arena_return_restored':restored};ok=ok and bool(term and int(term[1])>0 and restored)
 elif gate.startswith('kos'):
  held=re.findall(r'kos squeeze: held=(\d+) requested=(\d+) frag=(\d+)',text);head=[int(x) for x in re.findall(r'kos watch:[^\n]*headroom=(\d+)',text)];end='warp: alert at room frame' in text;r['observed']={'squeeze_rows':held,'min_headroom':min(head) if head else None,'alert_reached':end};ok=ok and bool(held and all(x==('49152','49152',gate[-1]) for x in held) and head and min(head)>=4096 and end)
 elif gate=='gd1':
  badread=bool(re.search(r'DISC READ FAILED|short read|open failed|read failed|BAD-READ|DISCNOTE: (?:disc: .*?(?:busy|timeout|abort|not accepted|late|did not land|failed|reinit|pio)|snd: stream table (?:bad|still))',text));entry='phase=enter room=103' in text;env=run.get('emu_env',{});profile=(extra or {}).get('gdemu_profile_observed',False);r['observed']={'room103':entry,'bad_read':badread,'profile_gdemu_observed':profile,'emu_env':env};ok=ok and entry and not badread and profile
 elif gate.startswith('bench'):
  room=gate[-3:];entry=bool(re.search(r'warp: room enter 0*'+room+r'\b',text));nm=re.findall(r'NMRS f=\d+ room=0*'+room+r' id=[0-9a-f]+[^\n]*?native=(\d+) crowd=(\d+)',text);draw=any(int(a)+int(b)>0 for a,b in nm);alive=bool(re.search(r'warp: alivelist room 0*'+room+r' ',text));memory=bool(re.search(r'room lifecycle: phase=enter room=0*'+room+r'\b',text));vramrows=[line for line in text.splitlines() if 'native UI VRAM:' in line];vram=bool(vramrows);counters=[tuple(map(int,x)) for x in re.findall(r'native UI VRAM:[^\n]*rejects=(\d+) retries=(\d+) evicted=(\d+)',text)];heapbad=[line for line in text.splitlines() if 'heap_check=' in line and 'heap_check=ok' not in line];checks=(extra or {}).get('checks',{});r['observed']={'entry':entry,'nmrs_rows':len(nm),'draw_rows':draw,'alive_census':alive,'memory_entry':memory,'vram':vram,'vram_counter_rows':counters,'memory_tail':[line for line in text.splitlines() if 'room lifecycle:' in line or 'native UI VRAM:' in line][-8:],'heap_check_bad':heapbad,'checks':checks};ok=ok and entry and draw and alive and memory and vram and counters and all(not any(row) for row in counters) and not heapbad and set(checks)=={'castgc','leongc','texchk'} and all(v['rc']==0 for v in checks.values())
 else:
  goal=run.get('stopped')=='goal';term=('route movie terminal=1 id=10130' in text) if gate=='bell' else ('phase=enter room=10f' in text and all(re.search(r'route movie terminal=1 id='+id+r' frames='+str(n)+'/'+str(n)+r'\b',text) for id,n in [('11f02',1067),('11f10',265),('11f11',321)]) and len(re.findall('warp: kill 0x35 hp<=0',text))==2);comparison=(extra or {}).get('decision_comparison');r['observed']={'goal_stop':goal,'source_event_markers':bool(term),'comparison':comparison};ok=ok and goal and bool(term) and (comparison is None or comparison['rc']==0)
 r['pass']=bool(ok);return r

def judge(cap,gate,arm,reference=None,launcher_rc=0):
 text=(cap/'run-output.txt').read_text(errors='replace').replace('\0','');extra={};d=tools(arm)
 if gate.startswith('bench'):
  extra['checks']={}
  for name,args in [('castgc',['python3',str(d/'cast_gc.py'),str(cap/'run-output.txt'),'--not-drawn','--json',str(cap/'castgc.json')]),('leongc',['python3',str(d/'mcheck/leongc_check.py'),str(cap/'run-output.txt')]),('texchk',['bash',str(d/'texchk/texchk.sh'),str(cap/'run-output.txt')])]:
   p=subprocess.run(args,capture_output=True,text=True);out=cap/(name+'.txt');out.write_text(p.stdout+p.stderr);extra['checks'][name]={'rc':p.returncode,'sha256':sha(out)}
 if gate=='gd1':
  logs=''.join(p.read_text(errors='replace') for p in cap.glob('serial*.txt'))+(cap/'flycast.log').read_text(errors='replace');extra['gdemu_profile_observed']='GDCONSOLE profile=gdemu' in logs
 if reference:
  p=subprocess.run(['python3',str(d/'../game30/decision_cmp.py'),str(reference/'run-output.txt'),str(cap/'run-output.txt'),'--align','frame','--json',str(cap/'decision-comparison.json')],capture_output=True,text=True);out=cap/'decision-comparison.txt';out.write_text(p.stdout+p.stderr);extra['decision_comparison']={'rc':p.returncode,'sha256':sha(out),'reference_log_sha256':sha(reference/'run-output.txt')}
 r=gate_evidence(gate,text,jsonread(cap/'run-result.json'),jsonread(cap/'bounded-launch.json'),extra);r.update(run_output_sha256=sha(cap/'run-output.txt'),current_launch_sha256=sha(cap/'current-gate-launch.json'));pin=jsonread(HERE/'pins.json');bound=jsonread(cap/'bounded-launch.json');r['exact_console_image_verified']=bound.get('expected_executable_sha256')==pin['console_executable_sha256'] and sha(cap/'flycast.exe')==pin['console_executable_sha256'];r['exact_harness_verified']=bound.get('harness_sha256')==pin['tools']['fullplay/fp_run.py'];r['launcher_rc']=launcher_rc;r['pass']=r['pass'] and r['exact_console_image_verified'] and r['exact_harness_verified'] and launcher_rc==0;fresh_json(cap/'current-gate-result.json',r);return r

def prove_reuse(profile):
 require(profile in ['g','c','t'],'reuse only R g/c/t actual audit programmes')
 unit=inspect('R',profile);oldout=Path('/root/probe/lanes/route')/('out-au23on5e4drT' if profile=='t' else 'out-fpau23on5e4d'+profile+'W');oldprg=programme(oldout,PRIOR)
 require(unit['programme']['main']==oldprg['main'] and unit['programme']['overlays']==oldprg['overlays'],'current R differs: no reuse')
 oldbase=OLD/'_discs'/('on-'+profile);validate_stage_manifest(jsonread(oldbase/'base-manifest.json'),jsonread(REL/'manifest.json'),oldprg)
 oldtrack=sha(oldbase/'track03.iso');require(oldtrack==(oldbase/'track03.sha256').read_text().strip(),'old base track digest changed')
 row={'scope':'Programme/main+all14overlay byte equivalence and staged baseline assets only; individual capture must still pass exact gate/run identities','source':SOURCE,'old_source':PRIOR,'profile':profile,'current':unit,'old_output':str(oldout),'old_programme':oldprg,'old_base':str(oldbase),'old_base_manifest_sha256':sha(oldbase/'base-manifest.json'),'old_track03_sha256':oldtrack,'eligible':True}
 require(sha(Path(__file__))==unit['script_sha256'],'proof helper changed while hashing');version=E/'helpers'/(unit['script_sha256']+'.py');version.parent.mkdir(parents=True,exist_ok=True)
 if version.exists():require(sha(version)==unit['script_sha256'],'proof helper archive changed')
 else:shutil.copyfile(Path(__file__),version)
 fresh_json(E/'reuse'/('R-'+profile+'-5e4d.json'),row);return row

def recorded_track_matches(run,base,tracksha):
 return run.get('disc')==base and run.get('tracks',{}).get('base')==base and run.get('tracks',{}).get('track03_sha256')==tracksha

def validate_reference(reference,gate,unit):
 require(gate in ['bell','mendez'],'reference only for decisions')
 marker=reference/'current-gate-launch.json'
 if marker.exists():
  old=jsonread(marker);require(old['unit']['source']==SOURCE and old['unit']['arm']=='R' and old['unit']['profile']=='t' and old['gate']==gate,'reference is not current R matching decision control');require(old['unit']['asset_manifest_sha256']==unit['asset_manifest_sha256'],'reference assets differ');current=inspect('R','t');require(old['unit']['programme']['main']==current['programme']['main'] and old['unit']['programme']['overlays']==current['programme']['overlays'],'reference programme changed');require(jsonread(reference/'current-gate-result.json')['pass'],'reference control incomplete')
 else:
  proof=jsonread(E/'reuse/R-t-5e4d.json');require(proof['eligible'] and proof['current']['programme']['main']==inspect('R','t')['programme']['main'] and proof['current']['programme']['overlays']==inspect('R','t')['programme']['overlays'],'R reuse proof stale');require(reference.resolve()==(OLD/('decisions-'+gate+'-on-r1')).resolve(),'unregistered old source reference');oldrun=jsonread(reference/'run-result.json');oldbound=jsonread(reference/'bounded-launch.json');require(not oldbound['deadline_fired'] and oldbound['guest_exited'] and not oldrun['errors'] and oldrun['status']=='RUN_COMPLETE','old reference incomplete');require(oldrun['disc']==win(Path(proof['old_base'])),'old capture was not run from proved stage');expected_console=jsonread(HERE/'pins.json')['console_executable_sha256'];require(oldbound['expected_executable_sha256']==expected_console and sha(reference/'flycast.exe')==expected_console,'old reference console image mismatch')
  require(recorded_track_matches(oldrun,win(Path(proof['old_base'])),proof['old_track03_sha256']),'old reference recorded actual track/base mismatch')
  stage_track=Path(proof['old_base'])/'track03.iso';cap_track=reference/'track03.iso'
  if cap_track.exists():
   same=cap_track.stat().st_ino==stage_track.stat().st_ino and cap_track.stat().st_dev==stage_track.stat().st_dev;require(same or sha(cap_track)==proof['old_track03_sha256'],'old reference surviving track differs')
  warp,pad,stop,seconds,grace=fixture('R',gate);require(oldrun['fixtures']['warp']['sha256']==sha(warp),'old reference warp differs');require(oldrun['fixtures']['pad']['sha256']==(sha(pad) if pad else hashlib.sha256(b'').hexdigest()),'old reference pad differs')
 return {'path':str(reference),'log_sha256':sha(reference/'run-output.txt')}

def run(arm,gate,tag,reference=None):
 import fcntl
 E.mkdir(parents=True,exist_ok=True)
 with (E/'worker.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX) # one owned guest, before shared stat3 and trace16.
  # Do not admit a guest while root's composed B safety outputs are pending.
  for profile in ['p','g','c']:inspect('B',profile)
  floor();unit=inspect(arm,GATES[gate]);base=E/'_discs'/(arm+'-'+GATES[gate]);staged=check_base(base,unit);cmd,cap,fix=command(arm,gate,tag,unit);require(not cap.exists(),'capture exists; preserve')
  ref=validate_reference(Path(reference),gate,unit) if reference else None
  require(arm=='R' or gate not in ['bell','mendez'] or ref is not None,'ON decisions require current-source-bound R reference')
  receipt={'unit':unit,'staged':staged,'gate':gate,'tag':tag,'fixtures':fix,'command':cmd,'reference':ref,'guard_order':['own-worker','stat3','trace16','exact-child55'],'script_sha256':sha(Path(__file__))};fresh_json(E/'launches'/(tag+'.json'),receipt)
  env=dict(os.environ,RE4DC_EMU='console',RE4DC_MAX_FLYCASTS='16',FP_NOLIMIT='1',TRACE_SLOTS='16',TRACE_LOCK_OWNER='world-current-gates-'+tag)
  env['RE4DC_CONSOLE_EXE']=r'C:\Flycast-Evidence\re4-dreamcast\flycast-console-bin\flycast-console.exe'
  keys=['RE4DC_EMU','RE4DC_MAX_FLYCASTS','FP_NOLIMIT','RE4DC_CONSOLE_EXE']
  for k in ['RE4DC_GD_PROFILE','RE4DC_GD_JITTER','RE4DC_GD_SEED']:env.pop(k,None)
  if gate=='gd1':env.update(RE4DC_GD_PROFILE='gdemu',RE4DC_GD_JITTER='20000',RE4DC_GD_SEED='1');keys+=['RE4DC_GD_PROFILE','RE4DC_GD_JITTER','RE4DC_GD_SEED']
  env['WSLENV']=':'.join(filter(None,[env.get('WSLENV',''),*keys]))
  with (E/'launches'/(tag+'.log')).open('x') as log:proc=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
  if not cap.exists():raise Refused('launch produced no capture; inspect launcher log')
  fresh_json(cap/'current-gate-launch.json',receipt);result=judge(cap,gate,arm,Path(reference) if reference else None,proc.returncode)
  require(proc.returncode==0 and result['pass'],'gate failed/incomplete; evidence retained');return result

def main():
 ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='action',required=True)
 for name in ['inspect','stage']:
  q=sub.add_parser(name);q.add_argument('arm',choices=ARMS);q.add_argument('profile',choices=['p','g','c','t','m','n'])
 for name in ['plan','run']:
  q=sub.add_parser(name);q.add_argument('arm',choices=ARMS);q.add_argument('gate',choices=GATES);q.add_argument('tag');q.add_argument('--reference')
 q=sub.add_parser('prove-reuse');q.add_argument('profile',choices=['g','c','t'])
 a=ap.parse_args()
 require(E.resolve().is_relative_to(Path('/mnt/c/Flycast-Evidence/re4-dreamcast/world-emit23-takeover').resolve()),'evidence root escapes owned world-emit23 tree')
 if a.action=='inspect':result=inspect(a.arm,a.profile)
 elif a.action=='stage':result=stage(a.arm,a.profile)
 elif a.action=='prove-reuse':result=prove_reuse(a.profile)
 elif a.action=='plan':
  u=inspect(a.arm,GATES[a.gate]);cmd,cap,fix=command(a.arm,a.gate,a.tag,u);result={'command':cmd,'capture':str(cap),'fixture':fix,'profile':GATES[a.gate],'source':SOURCE,'executed':False,'reference':a.reference}
 else:result=run(a.arm,a.gate,a.tag,a.reference)
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
