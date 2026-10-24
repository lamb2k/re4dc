"""Read-only full input admission; never mkdir/stage/retry/acquire a slot."""
from pathlib import Path
import argparse,hashlib,json,sys,types
HERE=Path(__file__).resolve().parent
COMMON_SHA='ccef49c9b29f2b4877d56cd058e4fe5fb9fb7772cb1bbf898584582298758f39'
def main():
 if not (__debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):raise RuntimeError('Use canonical Python -I -S -B')
 a=argparse.ArgumentParser();a.add_argument('--expected-seal',required=True);args=a.parse_args();seal=HERE/'TOOLCHAIN-SEAL.json'
 if hashlib.sha256(seal.read_bytes()).hexdigest()!=args.expected_seal:raise RuntimeError('Exact frozen tool seal required')
 raw=(HERE/'common.py').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=COMMON_SHA:raise RuntimeError('Common source changed')
 c=types.ModuleType('common');c.__file__=str(HERE/'common.py');sys.modules['common']=c;exec(compile(raw,c.__file__,'exec',dont_inherit=True),c.__dict__)
 for n,pin in c.read(seal)['members'].items():c.verify(HERE/n,pin)
 plan=c.read(HERE/'PLAN.json');result=c.verify_inputs(plan)
 c.need(len(plan['input_pins'])==58,'exact58 inputs')
 paths={}
 for group in ['base_paths','work_paths','captures']:
  paths[group]={}
  for arm,p in plan[group].items():
   q=Path(p);c.need(q.is_absolute() and q==q.resolve() and not q.exists(),'Nonfresh or escaped proposed output '+str(q));paths[group][arm]={'path':str(q),'exists':False}
 print(json.dumps({'status':'ACTUAL_FULL_INPUT_VERIFY_PASS_READ_ONLY_NO_WRITE','inputs':result,'output_paths':paths,'source':plan['source'],'SDK_stage_guest_retry':False},indent=2))
if __name__=='__main__':main()
