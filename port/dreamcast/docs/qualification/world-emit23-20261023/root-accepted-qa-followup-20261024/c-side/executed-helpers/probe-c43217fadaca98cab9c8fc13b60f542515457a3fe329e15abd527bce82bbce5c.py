"""Six authorized sequential QA probes: actual final GDI boot, two labelled fixture proxies."""
from pathlib import Path
import argparse,fcntl,hashlib,importlib.util,json,os,re,shutil,subprocess,sys
import auto_menu
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('media',HERE/'media.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def main(arm,gate):
 m.sealed();m.check_inputs();assert (m.E/arm/'FINAL-READBACK.json').exists()
 cap=m.E/'captures'/(arm+'-'+gate);assert not cap.exists()
 fixtures=m.E/'fixtures';fixtures.mkdir(exist_ok=True)
 keys=fixtures/'boot-ordinary.keys';warp=fixtures/'menu-warp.txt'
 if not keys.exists():keys.write_text('presets in | 2 | down\n- | 1 | a\n- | 1 | a\n- | 1 | a\n')
 if not warp.exists():warp.write_text('name r101\nroom 0x101\npos -7914 0 -254\nang 2.9600\nfind 0x00002000\ninv default\nqa_menu 300 r103.txt 800\n')
 args=[m.win(m.TOOLS/'fullplay/fp_run.py'),'--cap',m.win(cap),'--syms',(m.P/arm/'syms.txt').read_text().strip(),'--seconds','45','--period','0','--name','world49ad-private-qa-'+arm+'-'+gate]
 fix={};mode='actual final standard raw2352 GDI; ordinary keys; no warp injection'
 if gate=='boot':args+=['--disc',m.win(m.FINAL[arm]/'gdemu'),'--keys',m.win(keys),'--stop','room enter|phase=enter','--grace','15'];fix={'keys':m.row(keys)}
 else:
  proxy=m.E/'probe-bases'/arm;assert m.sha(proxy/'track03.iso')==(proxy/'track03.sha256').read_text().strip()
  args+=['--base',m.win(proxy)];mode='fixture proxy; exact final QA programme/all14/full assets; not actual final GDI boot'
  if gate=='menu-warp':args+=['--warp',m.win(warp),'--stop','phase=enter room=103','--grace','10'];fix={'warp':m.row(warp)}
  else:
   w=m.TOOLS/'fullplay/segments/h2-warp.txt';p=m.TOOLS/'fullplay/segments/h2-pad.txt'
   args+=['--warp',m.win(w),'--pad',m.win(p),'--stop','route movie terminal=1 id=10030','--grace','2'];fix={'warp':m.row(w),'pad':m.row(p)}
 cmd=['bash',str(m.HOST/'stat-guest-slot.sh'),'bash',str(m.TOOLS/'trace_lock.sh'),m.WINPY,m.win(HERE/'post_slot.py'),*args]
 env=dict(os.environ,RE4DC_EMU='console',RE4DC_MAX_FLYCASTS='16',FP_NOLIMIT='1',TRACE_SLOTS='16',TRACE_LOCK_OWNER='world49ad-private-qa-'+arm+'-'+gate)
 for k in ['RE4DC_GD_PROFILE','RE4DC_GD_JITTER','RE4DC_GD_SEED']:env.pop(k,None)
 env['WSLENV']=':'.join(filter(None,[env.get('WSLENV',''),'RE4DC_EMU','RE4DC_MAX_FLYCASTS','FP_NOLIMIT']))
 launch=dict(arm=arm,gate=gate,source=m.SOURCE,programme_seal=m.SEAL,mode=mode,command=cmd,fixtures=fix,final_readback=m.row(m.E/arm/'FINAL-READBACK.json'),helper=m.row(Path(__file__)),post_slot=m.row(HERE/'post_slot.py'),max_child55=True)
 m.fresh(m.E/'launches'/(arm+'-'+gate+'.json'),launch)
 with (m.E/'own-guest.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  m.floor()
  with (m.E/'launches'/(arm+'-'+gate+'.log')).open('x') as log:rc=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
 assert cap.exists(),'No guest capture; preserve launch failure, no retry'
 text=(cap/'run-output.txt').read_text(errors='replace').replace('\0','');run=m.read(cap/'run-result.json');bound=m.read(cap/'bounded-launch.json')
 bad=[l for l in text.splitlines() if re.search(r'HALT|FAULT|MISSING|Out of memory|\[LOG OVERRUN|no contiguous|upload FAILED|package rejected',l)]
 ok=rc==0 and run.get('status')=='RUN_COMPLETE' and not run.get('errors') and bound.get('guest_exited') and not bound.get('deadline_fired') and bound.get('deadline_seconds')==55 and run.get('emu')=='console'
 ok=bool(ok and not bad and m.sha(cap/'flycast.exe')=='8e6c49871013c25b1a1c77c789167e3aaed8193e828adb7e2bbce9248d2add4a' and bound.get('harness_sha256')=='646bd4eb42ff2063d4e07dc3754ab0c0d61e3b75348b934a48e7f63a25a07747')
 observed={}
 if gate=='boot':
  observed=dict(menu33=bool(re.search(r'qa: 33 presets in 6 chapters',text)),room_enter=bool(re.search(r'room enter|phase=enter',text)),all_keys=not run.get('keys_pending') and len(run.get('key_log',[]))==4,owned_windows=all(r['windows']>0 for r in run.get('key_log',[])))
  ok=ok and all(observed.values()) and run.get('stopped')=='goal'
 elif gate=='menu-warp':
  observed=auto_menu.observe(text)
  ok=ok and observed['ordered_auto_menu_chain'] and run.get('stopped')=='goal'
  if observed['ordered_auto_menu_chain']:observed['negative_controls']=auto_menu.controls(text)
 else:
  term=re.search(r'route movie terminal=1 id=10030 frames=340/340 uploaded=340 presented=340[^\n]*heap_before=(\d+)',text);b=re.search(r'MOVIEARENA borrow id=10030 token=(\d+)\b',text)
  restored=bool(b and re.search(r'MOVIEARENA return token='+b[1]+r'\b[^\n]*restored=1',text))
  observed=dict(full340=bool(term),heap_before=int(term[1]) if term else None,matching_arena_return_restored=restored)
  ok=ok and bool(term and int(term[1])>0 and restored)
 result=dict(**launch,critical=bad,observed=observed,launcher_rc=rc,run_output=m.row(cap/'run-output.txt'),bounded=m.row(cap/'bounded-launch.json'),pass_=bool(ok),physical_console_acceptance=False,qa_mendez_tested=False,hardware_gain_claim=False)
 result['pass']=result.pop('pass_');m.fresh(cap/'QUALIFIED.json',result);print(json.dumps(dict(arm=arm,gate=gate,passed=bool(ok),observed=observed,critical=bad,run=run,bound=bound)))
 if not ok:raise SystemExit(1)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('arm',choices=['off','both']);p.add_argument('gate',choices=['boot','menu-warp','h2']);a=p.parse_args();main(a.arm,a.gate)

