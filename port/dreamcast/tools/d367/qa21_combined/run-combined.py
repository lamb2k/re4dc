from pathlib import Path
import hashlib,json,shutil,subprocess,sys
R=Path('C:/Flycast-Evidence/re4-dreamcast/qa21-combined-regression-20261021'); D=R/'dependencies'; L=Path('C:/Game Dev/Emulators/codex-lanes/qa21-combined-regression')
name=sys.argv[1]; assert name in ('qa-cold01','pause-cold01','pause-return01','inventory01','inventory02')
assert shutil.disk_usage('C:/').free>18*1024**3+64*1024**2
binding=R/'combined-binding.json';r=json.loads(binding.read_text());syms=' '.join(hex(int(r['symbols'][x],0)-0x8c000000) for x in ('logbuf','head','stage'))
keys=L/({'qa-cold01':'qa-cold-keys.txt','pause-cold01':'pause-cold-keys.txt','pause-return01':'pause-return-keys.txt','inventory01':'inventory-keys.txt','inventory02':'inventory2-keys.txt'}[name])
cmd=[sys.executable,str(D/'run_unchanged.py'),'--runner',str(D/'checkpoint_runner.py'),'--runner-sha256','b1bf7235eed65f757ebb765ccaaefd3108ce935ff6bd80fe3c0a2e425ef0d394','--disc',str(R/'combined-input/gdemu'),'--cap',str(R/name),'--keys',str(keys),'--syms',syms,'--name','qa21-combined-'+name,'--binding',str(binding),'--layout',str(R/'builds/combined/dwarf-layout.json'),'--event-shots','--seconds','47','--no-limit','--save-checkpoint','--elf',str(R/'builds/combined/re4dc-game.elf')]
if name=='pause-return01':cmd+=['--checkpoint-seed',str(R/'pause-cold01')]
if name=='inventory01':cmd+=['--checkpoint-seed',str(R/'pause-return01')]
if name=='inventory02':cmd+=['--checkpoint-seed',str(R/'inventory01')]
assert not (R/name).exists();result=subprocess.run(cmd);raise SystemExit(result.returncode)
