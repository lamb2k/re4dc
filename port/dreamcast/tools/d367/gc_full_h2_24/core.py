"""One fixed diagnostic H2 pair; importing this file never starts work."""
from pathlib import Path,PurePosixPath
import hashlib,json,os,re,sys,types
HERE=Path(__file__).resolve().parent
SOURCE='427784b1f48aa30742850bb5025925ab619b740e'
OFF_SOURCE='8ce5ee2d00027268c3e69c9c300b819c1b14c63f'
RAW={'off':'e0168b780b102356c9bc3ee785753a659be6a020b1d1d3f8db92f14a90c16de5','on':'9e3758b23940ab1ce88fcd37eae3dff28efb19086bd044f8552ff81350e33876'}
ELF={'off':'270be61f74ea99b039c474860dcc612ff52fc1ac1fe8a1c0060c1a9b13a82397','on':'972ae22c49230765d077449c2bcff4bc6ddbb22d439d373fdddd22d434898160'}
STOP='route movie terminal=1 id=10030'
FINAL=PurePosixPath('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/full-h2-427-v1')
LIMIT=300;TIMER=297;SECONDS=290;GRACE=5
BOOT="import pathlib,hashlib,sys,types;p=pathlib.Path(sys.argv.pop(1));s=sys.argv.pop(1);b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==s;m=types.ModuleType('__main__');m.__file__=str(p);sys.modules['__main__']=m;sys.argv[0]=str(p);exec(compile(b,str(p),'exec',dont_inherit=True),m.__dict__)"
def need(v,s):
 if not v:raise RuntimeError(s)
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def row(p):return dict(size=Path(p).stat().st_size,sha256=sha(p))
def read(p):return json.loads(Path(p).read_text())
def verify(p,pin):need(row(p)==dict(size=pin.get('size',pin.get('bytes')),sha256=pin['sha256']),'Input changed '+str(p))
def fresh(p,j):
 with Path(p).open('x') as f:json.dump(j,f,indent=2);f.write('\n')
def module(name,p,expected):
 b=Path(p).read_bytes();need(hashlib.sha256(b).hexdigest()==expected,'Source changed '+str(p));m=types.ModuleType(name);m.__file__=str(p);sys.modules[name]=m;exec(compile(b,str(p),'exec',dont_inherit=True),m.__dict__);return m
def win(p):
 s=str(p);return 'C:\\'+s[7:].replace('/','\\') if s.startswith('/mnt/c/') else '\\\\wsl.localhost\\Ubuntu-24.04'+s.replace('/','\\')
def own_seal(expected):
 need(sha(HERE/'SOURCE-SEAL.json')==expected,'Wrong H2 source seal')
 for n,p in read(HERE/'SOURCE-SEAL.json')['members'].items():verify(HERE/n,p)
def grant(g):
 need(g.get('approved') is True and g['authorization']=='ONE_DIAGNOSTIC_427_FULL_H2_PAIR','No fresh H2 grant')
 need(g['source']==SOURCE and g['off_actual_producer_source']==OFF_SOURCE and g['raw']==RAW,'Different source/programme pair')
 need(g['arm_order']==['off','on'] and g['actual_child_seconds']==LIMIT and g['harness_seconds']==SECONDS and g['grace']==GRACE,'Changed route/time allowance')
 need(g['user_allowance_question']=='call_893faf52f48b4286ba0eb3333782ea2c' and g['KOS_first'] is True,'Wrong allowance/order')
 need(g['final']==str(FINAL) and g['root_slots']==3 and g['global_slots']==16,'Wrong ownership limits')
 need(len(g['KOS_results']) in [1,2,4],'All four earlier KOS results required')
 need(g['parent_kit']['path'].startswith('/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/kos-budget-retest-guest-exec-v'),'Wrong parent kit family')
 need(os.name=='nt' or Path(g['parent_kit']['path']).resolve()==Path(g['parent_kit']['path']),'Noncanonical parent')
 need(g['parent_independent_CLEAR']['status']=='CLEAR_SOURCE_AND_BINDING','Reviewed/bound successor required')
 for n in ['poststage','parent_independent_CLEAR']:need('path' in g[n] and 'identity' in g[n],'Unbound proof')
 for a in ['off','on']:
  need(set(g['arms'][a])=={'base','syms','raw','elf'},'Unbound arm')
  need(g['arms'][a]['raw']['identity']['sha256']==RAW[a] and g['arms'][a]['elf']['identity']['sha256']==ELF[a],'Arm is not frozen 8ce/427 programme')
 need(g['arms']['off']['base']=='/mnt/c/Flycast-Evidence/re4-dreamcast/rain-diag24-20261024/_qa-media-8ce-recovery-v4/base-off','Wrong OFF base')
 need(g['arms']['on']['base']=='/mnt/c/Flycast-Evidence/re4-dreamcast/gc-motion24-20261024/kos-budget-retest-media-v2/on','Wrong ON base')
 return True
def authenticate(g):
 grant(g);pins=read(HERE/'INPUTS.json')
 for group in ['helpers','template','fixtures']:
  for item in pins[group].values():verify(item['path'],item['identity'])
 for name in ['pillow_launcher','pillow_manifest','pillow_seal']:verify(pins[name]['path'],pins[name]['identity'])
 pk=Path(g['parent_kit']['path']);verify(pk/'TOOLCHAIN-SEAL.json',g['parent_kit']['identity'])
 verify(pk/'common.py',pins['parent_common']);c=module('h2_parent_common',pk/'common.py',pins['parent_common']['sha256']);c.sealed(g['parent_kit']['identity']['sha256']);k=c.context()
 for n in ['poststage','parent_independent_CLEAR']:verify(g[n]['path'],g[n]['identity'])
 for n in ['off_programme_binding','on_programme_binding']:verify(pins[n]['path'],pins[n]['identity'])
 clear=read(g['parent_independent_CLEAR']['path']);need(clear['verdict']=='CLEAR' and clear['source']==SOURCE and clear['kit_sha256']==g['parent_kit']['identity']['sha256'],'Parent successor is not independently CLEAR')
 c.check_inputs(g,k);baseline=k.baseline_check(links_changed=True)
 results=[]
 for p in g['KOS_results']:
  verify(p['path'],p['identity']);results.append(read(p['path']))
 kos_guard(results,g['poststage'])
 for a in ['off','on']:
  c.check_poststage(g,k,a);need(g['arms'][a]['raw']['identity']['sha256']==RAW[a],'Wrong raw')
  for n in ['raw','elf']:verify(g['arms'][a][n]['path'],g['arms'][a][n]['identity'])
  need(g['arms'][a]['elf']['identity']['sha256']==ELF[a],'ELF is not the exact frozen 8ce/427 pair')
  elf=Path(g['arms'][a]['elf']['path']);need(elf.name=='re4dc-game.elf' and elf.suffix=='.elf','Need actual QA ELF')
  import struct
  b=elf.read_bytes();h=struct.unpack_from('<16sHHIIIIIHHHHHH',b);need(h[0][:7]==b'\x7fELF\x01\x01\x01' and h[2]==42,'Wrong ELF')
  sec=[struct.unpack_from('<IIIIIIIIII',b,h[6]+i*h[11]) for i in range(h[12])];vals={}
  for s in sec:
   if s[1]!=2:continue
   strings=sec[s[6]];names=b[strings[4]:strings[4]+strings[5]]
   for o in range(s[4],s[4]+s[5],s[9]):
    no,v,sz,info,other,idx=struct.unpack_from('<IIIBBH',b,o);name=names[no:names.find(b'\0',no)].decode(errors='replace')
    if name in ['_re4dc_logbuf','_re4dc_log_head','_re4dc_stage']:need(name not in vals,'Duplicate symbol');vals[name]=v
  need(len(vals)==3 and g['arms'][a]['syms']==' '.join(hex(vals[n]) for n in ['_re4dc_logbuf','_re4dc_log_head','_re4dc_stage']),'QA ELF syms mismatch')
 return c,k,baseline
def kos_guard(results,poststage):
 seen=set()
 for j in results:
  need(j['complete_captures'] is True and j['all_allocated_bounded_KOS_pass'] is True and j['source']==SOURCE and j['stage']==poststage,'KOS not complete for this pair')
  for v in j['cases'].values():
   i=v['index'];need(type(i) is int and 0<=i<4 and i not in seen,'Duplicate/missing KOS case');seen.add(i)
   need(v['complete_capture'] is True and v['actual_KOS_judge']['status']=='PASS_BOUNDED_KOS48' and not v['bounded']['deadline_fired'],'KOS failure')
 need(seen==set(range(4)),'Four KOS cases must precede H2')
 return True
def route(g,arm):
 need(arm in ['off','on'],'Wrong arm');p=read(HERE/'INPUTS.json');cap=FINAL/('h2-'+arm);cache=FINAL/('cache-'+arm)
 return [p['helpers']['harness']['windows_path'],'--base',win(g['arms'][arm]['base']),'--cap',win(cap),'--syms',g['arms'][arm]['syms'],'--warp',win(p['fixtures']['warp']['path']),'--pad',win(p['fixtures']['pad']['path']),'--seconds',str(SECONDS),'--period','12','--stop',STOP,'--grace',str(GRACE),'--name','gc427-full-h2-'+arm]
def judge(text,rr,bound):
 need(rr['status']=='RUN_COMPLETE' and rr['emu']=='console' and rr['seconds']==SECONDS and rr['stop']==STOP and rr.get('stopped')=='goal' and not rr['errors'],'Incomplete transport/route')
 need(bound['guest_exited'] is True and bound['deadline_fired'] is False and 0<bound['guest_observed_elapsed_s']<=LIMIT,'Child deadline/exit failure')
 pat=r'route movie terminal=(\d+) id=(\d+) frames=(\d+)/(\d+) uploaded=(\d+) presented=(\d+)[^\r\n]*heap_before=(\d+)'
 rows=[list(map(int,m.groups())) for m in re.finditer(pat,text)]
 need(len(rows)==3 and [v[1] for v in rows]==[10003,10020,10030],'Missing/duplicate/out-of-order movie')
 need(all(v[0]==1 and v[2]>0 and v[2]==v[3]==v[4]==v[5] and v[6]>=0 for v in rows),'Partial movie/upload/present')
 need(rows[-1][2]==340,'s30 must be340/340')
 borrow=list(re.finditer(r'MOVIEARENA borrow id=10030 token=(\d+)[^\r\n]*',text));need(len(borrow)==1,'Missing/duplicate s30 loan')
 returns=list(re.finditer(r'MOVIEARENA return token='+borrow[0].group(1)+r'\b[^\r\n]*\brestored=1\b',text))
 need(len(returns)==1 and borrow[0].end()<returns[0].start()<text.rfind('route movie terminal=1 id=10030'),'Unrestored/wrong-order s30 loan')
 need(not re.search(r'Out of memory|\b(?:OOM|HALT|FAULT|MISSING)\b|no contiguous block',text),'Fatal route observation')
 return dict(status='PASS_COMPLETE_H2_PLAYBACK_MEMORY_RECORDED_ONLY',movies=rows,s30_heap_before=rows[-1][-1],s30_frames=340,restored=True,memory_acceptance='ROOT_DECISION_REQUIRED',hardware_or_performance=False)