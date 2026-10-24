"""Final host controls and exclusive preparation seal. No target execution."""
from pathlib import Path
import ast,datetime,json,os,re,subprocess
import prepare
HERE=Path(__file__).resolve().parent
def main():
 assert not (HERE/'TOOLCHAIN-SEAL.json').exists()
 plan=prepare.read(HERE/'PREPARATION.json');root=Path(plan['root'])
 assert not (root/'census-receipt.json').exists() and all(not (root/a/'out').exists() for a in ['off','on'])
 command=['/usr/bin/python3','-B','-E','-X','pycache_prefix='+str(root/'host-final-cache'),str(HERE/'test_preparation.py')]
 env={'PATH':'/usr/bin:/bin','HOME':'/root','LANG':'C','PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(root)}
 result=subprocess.run(command,env=env,capture_output=True,timeout=60)
 output=result.stdout+result.stderr
 with (HERE/'HOST-CONTROLS.log').open('xb') as stream:stream.write(output)
 assert result.returncode==0 and re.search(rb'Ran 38 tests',output) and output.rstrip().endswith(b'OK'),output[-2000:]
 prepare.emit(HERE/'HOST-CONTROLS.json',{'status':'38_HOST_CONTROLS_PASS','returncode':result.returncode,'command':command,
  'log':prepare.row(HERE/'HOST-CONTROLS.log'),'actual_source_accounting':prepare.row(HERE/'ACTUAL-SOURCE-HOST-CONTROLS.json'),
  'SDK_or_Make_or_KOS_env_source_or_stage_or_guest':False,'host_compiler_only':True,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 names=['prepare.py','run.py','run.sh','graph.py','readback.py','test_preparation.py','seal.py','HANDBACK.md','ATTRIBUTION.md',
  'PREPARATION.json','PREPARATION-RECEIPT.json','HOST-CONTROLS.json','HOST-CONTROLS.log','ACTUAL-SOURCE-HOST-CONTROLS.json']
 for p in HERE.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
 subprocess.run(['/bin/bash','-n',str(HERE/'run.sh')],check=True)
 prepare.emit(HERE/'TOOLCHAIN-SEAL.json',{'status':'FROZEN_MODE1_ATTRIBUTION_PREPARATION_ROOT_REVIEW_REQUIRED_NO_TARGET_RUN',
  'source':prepare.SOURCE,'root':str(root),'plan_sha256':prepare.sha(HERE/'PREPARATION.json'),'members':{n:prepare.row(HERE/n) for n in names},
  'SDK_Make_envsource_stage_guest':False,'target_graph':'MANDATORY_FUTURE_CHECK_NOT_OBSERVED','memory_qualification':False,
  'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 print(json.dumps({'plan_sha256':prepare.sha(HERE/'PREPARATION.json'),'tool_seal_sha256':prepare.sha(HERE/'TOOLCHAIN-SEAL.json'),
  'members':len(names),'host_controls':38,'root':str(root)},indent=2))
if __name__=='__main__':main()
