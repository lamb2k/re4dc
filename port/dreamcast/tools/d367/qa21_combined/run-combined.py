from pathlib import Path
import hashlib,json,shutil,subprocess,sys
R=Path('C:/Flycast-Evidence/re4-dreamcast/qa21-combined-regression-20261021'); D=R/'dependencies'; L=Path('C:/Game Dev/Emulators/codex-lanes/qa21-combined-regression')
name=sys.argv[1]; assert name in ('qa-cold01','pause-return01')
assert shutil.disk_usage('C:/').free>18*1024**3+64*1024**2
binding=R/'combined-binding.json';r=json.loads(binding.read_text());syms=' '.join(hex(int(r['symbols'][x],0)-0x8c000000) for x in ('logbuf','head','stage'))
keys=L/('qa-cold-keys.txt' if name=='qa-cold01' else 'pause-return-keys.txt')
cmd=[sys.executable,str(D/'run_unchanged.py'),'--runner',str(D/'fp_run.py'),'--runner-sha256','646bd4eb42ff2063d4e07dc3754ab0c0d61e3b75348b934a48e7f63a25a07747','--disc',str(R/'combined-input/gdemu'),'--cap',str(R/name),'--keys',str(keys),'--syms',syms,'--name','qa21-combined-'+name,'--binding',str(binding),'--layout',str(R/'builds/combined/dwarf-layout.json'),'--event-shots','--seconds','47','--no-limit','--save-checkpoint','--elf',str(R/'builds/combined/re4dc-game.elf')]
if name!='qa-cold01':cmd+=['--checkpoint-seed',str(R/'qa-cold01')]
assert not (R/name).exists();result=subprocess.run(cmd);raise SystemExit(result.returncode)