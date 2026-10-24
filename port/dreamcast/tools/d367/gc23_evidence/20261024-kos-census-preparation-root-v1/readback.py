"""Pure Python/Git source-preparation readback; never sources KOS or calls Make."""
from pathlib import Path
import ast,json,subprocess,datetime
import prepare,run
HERE=Path(__file__).resolve().parent
def main():
 plan=prepare.read(HERE/'PREPARATION.json');root=Path(plan['root'])
 assert not (root/'census-receipt.json').exists()
 run.integrity(plan)
 assert (root/'PREPARATION.json').read_bytes()==(HERE/'PREPARATION.json').read_bytes()
 for arm in ['off','on']:
  assert not (root/arm/'out').exists() and not (root/arm/'source/port/dreamcast/game/obj').exists()
  assert not list((root/arm/'source').rglob('*.o'))
  assert prepare.actual_preflight(root/arm/'source',plan['commands'][arm])['returncode']==0
 for p in HERE.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
 subprocess.run(['bash','-n',str(HERE/'run.sh')],check=True)
 seal=prepare.read(HERE/'TOOLCHAIN-SEAL.json')
 for n,pin in seal['members'].items():assert prepare.row(HERE/n)==pin,n
 receipt={'status':'PURE_PREPARATION_READBACK_PASS_NO_TARGET_RUN','source':prepare.SOURCE,'root':str(root),
  'plan_sha256':prepare.sha(HERE/'PREPARATION.json'),'tool_seal_sha256':prepare.sha(HERE/'TOOLCHAIN-SEAL.json'),
  'source_files_per_arm':{a:len(m) for a,m in plan['source_manifests'].items()},'current_input_pins':len(plan['input_pins']),
  'preserved_original_artifacts':len(plan['preserved_artifacts']),'original_d_files':len(plan['actual_existing_d_files']),
  'originals_unchanged':True,'owned_bytes_RAM_and_C_kit':run.owned_bytes(root),'owned_roots':[str(root),str(HERE)],
  'helper_preexisting_cache_paths_preserved':[str(p) for p in HERE.rglob('*.pyc')],
  'SDK_Make_envsource_stage_guest':False,
  'qualification':'Mode1 attribution preparation only. Target routes and live coverage UNKNOWN.',
  'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 with (HERE/'READBACK.json').open('x') as stream:stream.write(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
