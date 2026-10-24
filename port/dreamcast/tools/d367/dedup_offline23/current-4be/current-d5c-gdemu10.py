"""Frozen current4be ten-seed GDEMU checks; no launch."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
S='4be08e0110592510e3630c01fa9f49b3ac2fed3d'
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
T=Path('/root/work/lanes/dedup-offline23-current-d5c')
O=Path('/root/probe/lanes/route/out-fpdd23cur4be08e01ongW')
OWN=Path('/mnt/c/Game Dev/Emulators/codex-lanes/dedup-offline23')
BASE=E/'base-standard-current4be-on-r1'
PLAN=E/'gdemu10-plan-r1.json'
BAD=re.compile(r'MISSING|DISC READ FAILED|short read|open failed|read failed|BAD-READ|DISCNOTE: (disc: .*(busy|timeout|abort|not accepted|late|did not land|failed|reinit|pio)|snd: stream table (bad|still))|\bHALT\b|\bFAULT\b|Out of memory')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()
def expected(seed):
 assert 1<=seed<=10
 return dict(RE4DC_GD_PROFILE='gdemu',RE4DC_GD_JITTER='20000',RE4DC_GD_SEED=str(seed))
def admission(source,seed,env):
 assert source==S,'wrong source'
 assert env==expected(seed),'missing/wrong exact seed/profile/jitter environment'
def source_guard():
 admission(subprocess.check_output(['git','-C',str(T),'rev-parse','HEAD'],text=True).strip(),1,expected(1))
 assert not subprocess.check_output(['git','-C',str(T),'status','--porcelain','--untracked-files=no'],text=True)
 assert (O/'stack.txt').read_text()==S+'\n' and not (O/'missing.txt').read_bytes()
 k=dict(x.split('=',1) for x in (O/'resolved-knobs.txt').read_text().splitlines() if '=' in x)
 for n,v in dict(SCENERY_DEDUP='3',QA_MENU='0',KOS_WATCH='0',KOS_SQUEEZE='0',NATIVE_MODEL_REGISTRY_CENSUS='0',PC_SAMPLER='0',WORLD_METER='0').items():assert k[n]==v,(n,k.get(n))
def check_record(seed,r,b,s,serial,track,fixture):
 admission(S,seed,r['emu_env'])
 assert r['status']=='RUN_COMPLETE' and r['emu']=='console' and r['stopped']=='goal' and not r['errors']
 assert b['deadline_seconds']==55 and not b['deadline_fired'] and b['guest_exited'] and b['guest_observed_elapsed_s']<=55
 assert r['tracks']['track03_sha256']==track and r['fixtures']['warp']['sha256']==fixture
 assert 'phase=enter room=103' in s and not BAD.search(s),'endpoint or bad-read/fault'
 headers=[x for x in serial.splitlines() if x.startswith('GDCONSOLE profile=')]
 assert len(headers)==1
 kv=dict(re.findall(r'(\w+)=(\w+)',headers[0]))
 assert kv.get('profile')=='gdemu' and kv.get('jitter')=='20000' and kv.get('seed')==str(seed),'serial profile'
 reads=[x for x in serial.splitlines() if re.match(r'GDCONSOLE #\d+ read fad=\d+ n=[1-9]\d* ',x)]
 races=[x for x in reads if re.search(r'earlyStat=[1-9]\d* landedAfterStat=[1-9]\d*',x)]
 assert reads and races,'no actual positive read/landing witness'
 return dict(read_witness_rows=len(reads),early_stat_landing_rows=len(races),serial_profile=headers[0])
def prepare():
 source_guard();assert not PLAN.exists()
 assert json.loads((BASE/'base.json').read_text())['elf']==str(O/'re4dc-game.elf')
 track=sha(BASE/'track03.iso');assert track==(BASE/'track03.sha256').read_text().strip()
 wf=T/'port/dreamcast/tools/d367/fullplay/segments/door103-warp.txt';wire=hashlib.sha256(wf.read_bytes().replace(b'\r',b'')).hexdigest()
 pins={str(p):sha(p) for p in [O/'re4dc-game.elf',O/'resolved-knobs.txt',BASE/'base.json',wf,OWN/'current-d5c-gdemu10.py',OWN/'current-d5c-run-gdemu10.sh']}
 inputs={}
 for seed in range(2,11):
  p=E/'fixtures'/f'gdemu10-seed-{seed}-r1.json';assert not p.exists()
  data=dict(source=S,seed=seed,environment=expected(seed),track03_sha256=track,fixture_wire_sha256=wire,capture=str(E/f'gdemu{seed}-console-r1'))
  p.write_text(json.dumps(data,indent=2)+'\n');inputs[str(seed)]=dict(path=str(p),sha256=sha(p))
 PLAN.write_text(json.dumps(dict(source=S,kind='FROZEN_NINE_INDEPENDENT_SEED_INPUTS_EXISTING_BASE',track03_sha256=track,fixture_wire_sha256=wire,source_pins=pins,inputs=inputs,existing_seed1=str(E/'gdemu1-console-r1'),limits='Ten actual seeds required; no pass from serial profile alone. One guest/stat3/trace16/exact55, console jitter20000, same door103 fixture. No SDK/media staging.'),indent=2)+'\n')
 print('FROZEN_GDEMU10_PLAN',sha(PLAN))
def plan_guard():
 p=json.loads(PLAN.read_text());assert p['source']==S;source_guard()
 for name,h in p['source_pins'].items():assert sha(Path(name))==h,('changed source/helper',name)
 for x in p['inputs'].values():assert sha(Path(x['path']))==x['sha256']
 assert (BASE/'track03.sha256').read_text().strip()==p['track03_sha256']
 return p
def check(seed):
 plan=plan_guard();p=E/f'gdemu{seed}-console-r1'
 r=json.loads((p/'run-result.json').read_text());b=json.loads((p/'bounded-launch.json').read_text())
 s=(p/'run-output.txt').read_text(errors='replace');serial=(p/'serial.txt').read_text(errors='replace')
 w=check_record(seed,r,b,s,serial,plan['track03_sha256'],plan['fixture_wire_sha256'])
 assert re.search(r'(?m)^aica\.LimitFPS\s*=\s*no\s*$',(p/'emu.cfg').read_text())
 return dict(seed=seed,source=S,**w,elapsed_host_s=b['guest_observed_elapsed_s'],capture=str(p),sha256={n:sha(p/n) for n in ['run-result.json','bounded-launch.json','run-output.txt','serial.txt','emu.cfg','fixture-warp.txt']})
def main():
 a=argparse.ArgumentParser();a.add_argument('mode',choices=['prepare','admit','check','summary']);a.add_argument('seed',nargs='?',type=int);x=a.parse_args()
 if x.mode=='prepare':prepare()
 elif x.mode=='admit':
  p=plan_guard();assert x.seed in range(2,11);d=json.loads(Path(p['inputs'][str(x.seed)]['path']).read_text());admission(d['source'],x.seed,d['environment']);assert not Path(d['capture']).exists();print('SEED_INPUT_ADMITTED',x.seed)
 elif x.mode=='check':
  row=check(x.seed);p=E/f'gdemu{x.seed}-judged-r1.json';assert not p.exists();p.write_text(json.dumps(row,indent=2)+'\n');print('GDEMU_SEED_PASS',x.seed,row['read_witness_rows'],row['early_stat_landing_rows'])
 else:
  rows=[check(n) for n in range(1,11)];out=E/'gdemu10-gates-r1.json';assert not out.exists();out.write_text(json.dumps(dict(status='PASS_TEN_ACTUAL_CURRENT_GDEMU_SEEDS',source=S,plan_sha256=sha(PLAN),runs=rows,limits='MODELLED console disc/DMA safety; exact env+serial profile+positive read/landing witness+door103/bad-read predicates per seed. Existing seed1 preserved/revalidated; no hardware/performance or private QA acceptance.'),indent=2)+'\n');print('GDEMU10_PASS')
if __name__=='__main__':main()

