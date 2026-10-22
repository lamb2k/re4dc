"""At most four existing <=50s guests; inspect exact closed proofs before each next arm."""
from pathlib import Path
import sys,json,subprocess,hashlib,math,time,shutil
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021')
first=int(sys.argv[1]);assert 218<=first<=999;out=D/f'finite-combat-batch-{first}-{first+3}-20261021.json';assert not out.exists();stop=L/'STOP-FINITE-CASTLE-BATCH';assert not stop.exists()
elf='4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f';iso='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6'
prior=json.loads((D/f'route-walk{first-1}-exact-combat.json').read_text());baseline=prior['health'];assert baseline==[624,1200,90,600]
records=[];reason=None;began=time.monotonic()
def run_tool(name,args,log):
 with log.open('a',encoding='utf-8')as f:subprocess.run([sys.executable,str(L/name),*map(str,args)],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=100)
try:
 for i in range(4):
  n=first+i
  if stop.exists():reason='External stop requested; no next guest launched';break
  assert time.monotonic()-began<400,'Finite batch wall bound'
  assert shutil.disk_usage(D).free>=18*1024**3+128*1024**2,'Unchanged fresh18GiB+128MiB launch floor'
  p=prior['hero_pos'];assert math.hypot(p[0]-19000,p[2]+45000)<650 and abs(p[1]+2000)<100,'Only proven western firing line may seed next action'
  assert prior['elf_sha256']==elf and prior['image_sha256']==iso and prior['health']==baseline and prior['boss']['hp']>0
  combat=i%2==0;controller='owned-window-recovered-j-r201-sustained-activefront9000-deathfirst-still.py'if combat else'owned-window-recovered-j-r201-combined-escape-patrol-return-still.py';targets='19000,-45000'if combat else'23500,-45000;25000,-43750;19000,-45000'
  log=D/f'finite-batch-{first}-run{n}.log';assert not log.exists()
  scope=f'Finite max4guest batch {first}-{first+3}, action{i+1}: '+('source-qualified weakpoint combat'if combat else'full eastescape/original upperpatrol30ticks/fullwestreturn')+f'; exact previous{n-1}, health624/90 and original3396HP encounter lineage, no rollback/statewrites; each guest<=50s, all existing resource/injury guards unchanged'
  run_tool('prepare-recovered-j-bounded-arm.py',[n,controller,targets,180,'201',scope],log)
  run_tool('run-resume-with-resource-guard-v2.py',[n],log)
  run_tool('audit-recovered-j-checkpoint.py',[n],log);run_tool('audit-resume-exact-combat.py',[n],log)
  actual=json.loads((D/f'route-walk{n}-exact-combat.json').read_text());guard=json.loads((D/f'route-walk{n}/owned-resource-guard.json').read_text());control=json.loads((D/f'route-walk{n}/owned-window-current-stair-walk.json').read_text())
  row=dict(run=n,action='combat'if combat else'combined escape and return',before_hp=prior['boss']['hp'],after=actual,resource_closed=guard['closed'],host_log=str(log),controller_sha256=hashlib.sha256((L/controller).read_bytes()).hexdigest());records.append(row)
  print(json.dumps(dict(run=n,action=row['action'],boss_before=row['before_hp'],boss_after=actual['boss']['hp'],health=actual['health'],source=actual['source'],state_sha256=actual['state_sha256'])),flush=True)
  assert actual['elf_sha256']==elf and actual['image_sha256']==iso and actual['boss']['hp']<=prior['boss']['hp']
  if actual['health']!=baseline:reason='Original health changed; exact injury/death checkpoint preserved, no further guest';break
  if guard['closed']:reason='Resource guard closed; no further guest';break
  if any('abort'in e for e in control['events']):reason='Host guard or assertion needs review; no further guest';break
  if actual['boss']['hp']<=0:reason='Boss HP0 requires model review of original death/door callback certificate';break
  if not combat:
   assert any('original_upper_patrol16_and_far_separation_stable30ticks_before_full_west_return'in e for e in control['events']),'Original stable patrol certificate required'
   p=actual['hero_pos'];assert math.hypot(p[0]-19000,p[2]+45000)<650 and abs(p[1]+2000)<100,'Full return incomplete; no next combat'
  prior=actual
except Exception as e:reason=repr(e)
finally:
 record=dict(scope='Finite max4 existing bounded guests only; each next action admitted from exact closed state/program/image/health/position/source certificate. No guest memory/state writes or rollback, no builds/assets/recipes. External stop file honored between guests.',records=records,stopped=reason,elapsed_s=round(time.monotonic()-began,2),script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest());out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(dict(receipt=str(out),completed_guests=len(records),stopped=reason)),flush=True)
