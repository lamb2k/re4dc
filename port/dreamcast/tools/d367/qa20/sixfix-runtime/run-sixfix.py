from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys
W=Path(__file__).parent;E=Path(r'C:\Flycast-Evidence\re4-dreamcast\qa21-r11e-20261020');D=E/'sixfix-master'
a=argparse.ArgumentParser();a.add_argument('mode',choices=['cold','weapons','route','inventory','resources','natural']);a.add_argument('name');a.add_argument('--seed');x=a.parse_args();assert x.name.startswith('sixfix-')and all(c.isalnum()or c=='-'for c in x.name)
sha=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest();assert shutil.disk_usage(E).free>=16*1024**3+128*1024**2
r=json.loads((D/'master-receipt.json').read_text());assert r['source']=='d4a3b31fac3362937a3f21eaa874e07be94fd061'and r['source_unchanged'];assert r['audio_recovery']==0
assert sha(D/'re4dc-game.elf')==r['elf_sha256']=='52a5d671203e22e9f20728a8fbc3b61e080f7ba44e06891df635248a374dd053';assert sha(D/'track03.iso')==r['track03_sha256'];assert sha(D/'program.bin')==r['program_sha256']=='8c26c048c3e7aec66f2ea6496b1c2ec03e0b2b6e2ce6ff1ae1308dac62958034'
cap=E/x.name;assert not cap.exists();env=os.environ.copy();env['RE4DC_MAX_FLYCASTS']='16';env['QA_TRACK_SHA256']=r['track03_sha256']
args=[sys.executable,str(W/'fp_run_qa_sixfix.py'),'--disc',str(D),'--cap',str(cap),'--syms',' '.join(hex(int(s,16)-0x8c000000)for s in (W/'sixfix-log-addresses.txt').read_text().split()),'--seconds','50','--period','10','--name','qa21-sixfix-'+x.mode]
control={'cold':'normal-sixfix-cold.py','weapons':'normal-sixfix-weapons.py','route':'normal-sixfix-route.py','inventory':'normal-sixfix-inventory.py','resources':'normal-sixfix-resources.py','natural':'normal-sixfix-natural.py'}[x.mode];ctrl=[sys.executable,str(W/control),str(cap)]
if x.mode=='cold':assert x.seed is None;args+=['--keys',str(W/'keys-pack-fresh.txt')]
else:
 assert x.seed is not None;seed=E/x.seed;prior=json.loads((seed/'run-start.json').read_text());assert prior['elf_sha256']==r['elf_sha256']and prior['disc_sha256']==r['track03_sha256'];assert (seed/'data/disc.state').exists();args+=['--state-seed',str(seed/'data')];ctrl+=[str(seed)]
logs=[];children=[]
try:
 for label,cmd in [('observer',[sys.executable,str(W/'sample-sixfix.py'),str(cap)]),('controller',ctrl)]:
  f=(E/(x.name+'-'+label+'.log')).open('xb');logs.append(f);children.append(subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW))
 subprocess.run(args,check=True,env=env)
finally:
 for child in children:child.wait(timeout=12)
 for f in logs:f.close()
 assert all(p.returncode==0 for p in children),'Inspect retained controller/observer logs'
