"""Four single-attempt FPS-limited current49ad still cases; no SDK/staging/assets."""
from pathlib import Path
import argparse,fcntl,hashlib,importlib.util,json,os,re,subprocess,sys
HERE=Path(__file__).resolve().parent;PINS=json.loads((HERE/'PINS.json').read_text());GATE=HERE.parent/'current-gates/current_gates.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(GATE)==PINS['frozen_gate_helper_sha256']
spec=importlib.util.spec_from_file_location('frozen_current_gates',GATE);cg=importlib.util.module_from_spec(spec);spec.loader.exec_module(cg)
E=cg.E/'current-stills';TEMPLATE=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/d367-harness-par')
def check_pins():
 for path,key in [(HERE/'force_limited.py','force_limited_sha256'),(HERE/'freeze_capture.py','freeze_capture_sha256'),(cg.HOST/'stat_owned_ram.py','ram_backend_sha256'),(TEMPLATE/'capture_ui_vram.py','capture_decoder_sha256'),(TEMPLATE/'emu.cfg','template_cfg_sha256')]:assert sha(path)==PINS[key],str(path)+' changed'
 assert {str(p.relative_to(TEMPLATE/'data')):sha(p) for p in (TEMPLATE/'data').rglob('*') if p.is_file()}==PINS['template_data'],'template VMU/data changed'
 for n,h in PINS['fixtures'].items():assert sha(HERE.parent/'fixtures'/n)==h,'fixture changed'
 assert sha(GATE)==PINS['frozen_gate_helper_sha256']
 assert sha(Path('/mnt/c/Flycast-Evidence/re4-dreamcast/flycast-console-bin/flycast-console.exe'))==PINS['console_executable_sha256'],'console binary changed'
def bind_base(arm,unit):
 if arm=='B':return cg.E/'_discs/B-g',cg.check_base(cg.E/'_discs/B-g',unit),{'actual_build_source':cg.SOURCE,'reused_old_build':False}
 proofpath=cg.E/'reuse/R-g-5e4d.json';proof=cg.jsonread(proofpath);assert proof['source']==cg.SOURCE and proof['old_source']==cg.PRIOR and proof['eligible']
 assert proof['current']['programme']['main']==unit['programme']['main'] and proof['current']['programme']['overlays']==unit['programme']['overlays']
 base=Path(proof['old_base']);meta=cg.jsonread(base/'base.json');assert meta['elf']==str(Path(proof['old_output'])/'re4dc-game.elf')
 cg.validate_stage_manifest(cg.jsonread(base/'base-manifest.json'),cg.jsonread(cg.REL/'manifest.json'),unit['programme']);actual=sha(base/'track03.iso');assert actual==proof['old_track03_sha256']==(base/'track03.sha256').read_text().strip()
 return base,{'base':str(base),'base_json_sha256':sha(base/'base.json'),'base_manifest_sha256':sha(base/'base-manifest.json'),'track03_sha256':actual},{'actual_build_source':cg.PRIOR,'reused_old_build':True,'requested_source':cg.SOURCE,'proof':str(proofpath),'proof_sha256':sha(proofpath),'actual_old_programme':proof['old_programme'],'limitation':'Current R identity is by raw main+all14overlay byte proof; actual old5e build/ELF/base explicitly reused.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('arm',choices=['R','B']);ap.add_argument('scene',choices=['f1','f2']);ap.add_argument('tag');a=ap.parse_args();assert re.fullmatch('[A-Za-z0-9_-]+',a.tag)
 E.mkdir(parents=True,exist_ok=True)
 with (E/'worker.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX);cg.floor();check_pins();unit=cg.inspect(a.arm,'g');base,binding,reuse=bind_base(a.arm,unit);fixture=HERE.parent/'fixtures'/(a.scene+'.txt');expected='101' if a.scene=='f1' else '100';text=fixture.read_text();assert text.count('freeze 330')==1 and 'room 0x'+expected in text
  cap=E/'captures'/a.tag;assert not cap.exists(),'capture exists; no blind rerun';ledgerpath=E/'attempts.json';ledger=cg.jsonread(ledgerpath) if ledgerpath.exists() else [];assert not any(r['arm']==a.arm and r['scene']==a.scene for r in ledger),'single initial case attempt already allocated';assert len(ledger)<4
  env=dict(os.environ,RE4DC_EMU='console',FP_NOLIMIT='0',RE4DC_MAX_FLYCASTS='16',TRACE_SLOTS='16',TRACE_LOCK_OWNER='world-current-stills-'+a.tag,RE4DC_CONSOLE_EXE=r'C:\Flycast-Evidence\re4-dreamcast\flycast-console-bin\flycast-console.exe');
  for key in ['RE4DC_GD_PROFILE','RE4DC_GD_JITTER','RE4DC_GD_SEED','RE4DC_CONSOLE_DYNAREC']:env.pop(key,None)
  env['WSLENV']=':'.join(filter(None,[env.get('WSLENV',''),'RE4DC_EMU','FP_NOLIMIT','RE4DC_MAX_FLYCASTS','RE4DC_CONSOLE_EXE']))
  subprocess.run([cg.WINPY,'-c','import os;assert os.environ.get("FP_NOLIMIT")=="0";assert os.environ.get("RE4DC_EMU")=="console";print("EXPLICIT_LIMIT_ENV0_VERIFIED")'],env=env,check=True)
  cmd=['bash',str(cg.HOST/'stat-guest-slot.sh'),'bash',str(cg.tools(a.arm)/'trace_lock.sh'),cg.WINPY,cg.win(cg.HOST/'census-bound-run.py'),cg.win(HERE/'freeze_capture.py'),cg.win(cg.tools(a.arm)/'fullplay/fp_run.py'),expected,'--base',cg.win(base),'--cap',cg.win(cap),'--syms',unit['syms'],'--warp',cg.win(fixture),'--seconds','45','--period','0','--stop','warp: frozen at tick 330','--grace','2','--name','world-still-'+a.tag]
  record={'arm':a.arm,'scene':a.scene,'tag':a.tag,'source':cg.SOURCE,'unit':unit,'base':binding,'actual_build_binding':reuse,'fixture':{'path':str(fixture),'sha256':sha(fixture)},'pins_sha256':sha(HERE/'PINS.json'),'PINS':PINS,'command':cmd,'FPS_control':{'FP_NOLIMIT':'0','required_actual_owned_config':'aica.LimitFPS = yes before guest spawn'},'scope':'Visible corresponding-buffer comparison only; no withdrawn49ad observer, no strict completed actor/viewport/full-runtime-pose qualification'}
  ledger.append({'arm':a.arm,'scene':a.scene,'tag':a.tag});ledgerpath.write_text(json.dumps(ledger,indent=2)+'\n');launch=E/(a.tag+'-launch.json');cg.fresh_json(launch,record)
  with (E/(a.tag+'-launcher.log')).open('x') as out:proc=subprocess.run(cmd,env=env,stdout=out,stderr=subprocess.STDOUT)
  if cap.exists():cg.fresh_json(cap/'current-still-launch.json',record)
  result={'launcher_rc':proc.returncode,'capture':str(cap),'source':cg.SOURCE,'scope':record['scope'],'automatic_visual_match_claim':False}
  if (cap/'freeze330-capture.json').exists():result['capture_receipt']=cg.jsonread(cap/'freeze330-capture.json')
  if (cap/'run-result.json').exists():result['run']=cg.jsonread(cap/'run-result.json')
  if (cap/'bounded-launch.json').exists():result['bound']=cg.jsonread(cap/'bounded-launch.json')
  cg.fresh_json(E/(a.tag+'-result.json'),result);print(json.dumps({'tag':a.tag,'rc':proc.returncode,'captured':result.get('capture_receipt',{}).get('capture_completed',False),'marker':result.get('capture_receipt',{}).get('marker'),'stable':result.get('capture_receipt',{}).get('buffer_stable_between_reads'),'errors':result.get('capture_receipt',{}).get('errors'),'run_errors':result.get('run',{}).get('errors'),'deadline':result.get('bound',{}).get('deadline_fired')},indent=2))
if __name__=='__main__':main()
