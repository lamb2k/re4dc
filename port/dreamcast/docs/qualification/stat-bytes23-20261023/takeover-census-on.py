#!/usr/bin/env python3
import concurrent.futures,hashlib,json,os,pathlib,re,subprocess,time
T=pathlib.Path('/root/work/lanes/stat-bytes23-complete');PIN='2a14662d4b025031cd93f64eed6a5d8159d473b7'
D=pathlib.Path('/mnt/c/Game Dev/Emulators/codex-lanes/stat-bytes23');TOOLS=T/'port/dreamcast/tools/d367'
E=pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d');ROOT=E/'census-on';BASE=E/'_discs/on-c'
EW=r'C:\Flycast-Evidence\re4-dreamcast\stat-bytes23\takeover-2a14662d';P='/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe'
assert subprocess.check_output(['git','-C',str(T),'rev-parse','HEAD'],text=True).strip()==PIN
assert not subprocess.check_output(['git','-C',str(T),'status','--short'],text=True).strip()
assert not ROOT.exists(),ROOT
ROOT.mkdir();FIX=ROOT/'_fixtures';FIX.mkdir()
rooms='r100 r101 r102 r103 r104 r105 r106 r107 r108 r109 r10a r10b r10f r111 r112 r113 r117 r118 r119 r11a r11b r11c r11d r11e r11f r200 r10c'.split()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def win(p):return subprocess.check_output(['wslpath','-w',str(p)],text=True).strip()
receipt={'source':PIN,'source_tree':str(T),'rooms':rooms,'actual_seconds':40,'guest_deadline_seconds':55,'max_stat_guests':3,'wrapper_order':['stat-guest-slot.sh','trace_lock.sh','census-bound-run.py','fp_run.py'],'fixture_edits':{},'fixtures':{},'scripts':{str(D/n):sha(D/n) for n in ['stat-guest-slot.sh','census-bound-run.py','takeover-census-on.py']},'status':'WAITING_BASE'}
for r in rooms:
    src=TOOLS/'castgc/warps'/f'{r}.txt';data=src.read_bytes().replace(b'\r',b'');edits=[]
    if r=='r11b':data+=b'\nrsf 0x11b 0\n';edits.append('rr r11b reset flag')
    if not re.search(rb'(?m)^alivelog\s+',data):data+=b'\nalivelog 150\n';edits.append('enable read-only alive census every150 frames')
    dst=FIX/f'{r}.txt';dst.write_bytes(data)
    receipt['fixtures'][r]={'source':str(src),'source_sha256':sha(src),'run_sha256':sha(dst)}
    if edits:receipt['fixture_edits'][r]=edits
(ROOT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
for _ in range(900):
    if (BASE/'base.json').exists() and (E/'identities/on-c-master.log').exists():
        # fp_master last creates base.json; stage caller additionally records readiness on stdout.
        break
    time.sleep(2)
else:raise RuntimeError('ON-c base not ready')
knobs=(E/'identities/on-c-knobs.txt').read_text();assert 'STAT_ROUTINE_BYTES=1' in knobs
for k in ['NATIVE_MODEL_REGISTRY_CENSUS=1','NATIVE_MODEL_REGISTRY_CENSUS_PERIOD=150','TEX_CHECK=1','MCHECK_LEONGC=1']:
    assert k in knobs,k
receipt.update(status='RUNNING',base=str(BASE),base_meta_sha256=sha(BASE/'base.json'),data_manifest_sha256=sha(E/'identities/release-data-manifest.json'),programmes_sha256=sha(E/'identities/on-c-programmes.sha256'),knobs_sha256=sha(E/'identities/on-c-knobs.txt'))
(ROOT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
syms=(E/'identities/on-c-syms.txt').read_text().strip();env=dict(os.environ,RE4DC_EMU='console',RE4DC_MAX_FLYCASTS='16',FP_NOLIMIT='1',TRACE_SLOTS='16')
keys=['RE4DC_EMU','RE4DC_MAX_FLYCASTS','FP_NOLIMIT'];env['WSLENV']=':'.join(filter(None,[env.get('WSLENV',''),*keys]))
def run(r):
    cap=ROOT/f'cg-{r}';cmd=['bash',str(D/'stat-guest-slot.sh'),'bash',str(TOOLS/'trace_lock.sh'),P,win(D/'census-bound-run.py'),win(TOOLS/'fullplay/fp_run.py'),'--base',EW+r'\_discs\on-c','--cap',EW+r'\census-on\cg-'+r,'--syms',syms,'--warp',win(FIX/f'{r}.txt'),'--seconds','40','--period','15','--name','stat23-on-'+r]
    e=dict(env,TRACE_LOCK_OWNER='codex-stat23-census-'+r)
    start=time.time()
    with (ROOT/f'{r}-launcher.log').open('w') as log:p=subprocess.run(cmd,env=e,stdout=log,stderr=subprocess.STDOUT)
    row={'room':r,'rc':p.returncode,'host_s_including_slot_wait':round(time.time()-start,2),'command':cmd}
    (ROOT/f'{r}-command.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row),flush=True)
    return row
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(run,rooms))
receipt.update(status='CAPTURES_FINISHED',results=results)
(ROOT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')

