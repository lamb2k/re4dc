"""Run the pre-existing payload/index controls against an exact candidate snapshot."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,signal,subprocess,time
T=Path(__file__).resolve().parent;P=T.parent
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--ref',required=True);p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
assert not a.out.exists();assert shutil.disk_usage('/mnt/c').free>=18*1024**3+128*1024**2;a.out.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['texpack_index.inc','texpack_payload_retry.inc']:(a.out/name).write_bytes((a.snapshot/name).read_bytes())
s=subprocess.check_output(['git','-C',str(a.source),'show',a.ref+':port/dreamcast/game/platform/native_ui.cpp'],text=True)
body=s[s.index('Entry* load(const Re4dcUiImage&'):s.index('#undef RE4DC_OPEN_PACKAGE\n')]
(a.out/'actual_load.inc').write_text(body)
marker='    const bool in_pack=pack==texpack::kFound;';assert body.count(marker)==1
(a.out/'actual_load_interleaved.inc').write_text(body.replace(marker,marker+'\n    if(after_find){auto callback=after_find;after_find=nullptr;callback();}'))
def run(cmd,name):
 log=a.out/(name+'.log');start=time.time()
 with log.open('xb')as f:
  child=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);proc_start=Path(f'/proc/{child.pid}/stat').read_text().split()[21]
  (a.out/(name+'-owned-process.json')).write_text(json.dumps({'pid':child.pid,'pgid':os.getpgid(child.pid),'proc_start':proc_start,'command':cmd},indent=2)+'\n')
  while child.poll()is None:
   if shutil.disk_usage('/mnt/c').free<18*1024**3+64*1024**2 or log.stat().st_size>1024**2 or time.time()-start>55 or sum(p.stat().st_size for p in a.out.rglob('*')if p.is_file())>20*1024**2:
    assert os.getpgid(child.pid)==child.pid and Path(f'/proc/{child.pid}/stat').read_text().split()[21]==proc_start
    os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=5);raise RuntimeError('owned regression host resource guard')
   time.sleep(.1)
 assert child.returncode==0,(name,log.read_text()[-3500:])
 return log.read_text()
runs=[]
for name,guards in [('policy',[1]),('load',[0,1]),('index',[0,1]),('interleaved',[0,1])]:
 for guard in guards:
  unit=name+str(guard);exe=a.out/unit;source=P/(name+'_probe.cpp')
  command=['bash','/root/probe/d367-buildslot.sh','g++','-std=c++17','-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all','-Wno-int-to-pointer-cast','-DRE4DC_TEX_PAYLOAD_RETRY='+str(guard),'-I'+str(a.out),str(source),'-o',str(exe)]
  run(command,unit+'-compile');output=run([str(exe)],unit+'-run');runs.append({'name':name,'guard':guard,'fixture_sha256':sha(source),'command':command,'output':output})
record={'scope':'Existing source-host controls on exact candidate index snapshot. No new runtime edits or program/guest qualification.','source_ref':a.ref,'native_ui_sha256':hashlib.sha256(s.encode()).hexdigest(),'snapshot_source':str(a.snapshot),'inputs':{n:sha(a.out/n)for n in ['texpack_index.inc','texpack_payload_retry.inc','actual_load.inc','actual_load_interleaved.inc']},'runs':runs,'runner_sha256':sha(Path(__file__)),'output_bytes_before_receipt':sum(p.stat().st_size for p in a.out.rglob('*')if p.is_file()),'C_end':shutil.disk_usage('/mnt/c').free}
(a.out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'runs':[{'name':r['name'],'guard':r['guard'],'output':r['output']}for r in runs],'output_bytes':record['output_bytes_before_receipt']},indent=2))
