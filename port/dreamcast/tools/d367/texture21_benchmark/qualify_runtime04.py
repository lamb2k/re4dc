#!/usr/bin/env python3
"""Record source and actual-bound mock/API tests; never attach to a game guest."""
import argparse,hashlib,json,os,platform,unittest
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--plan',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a=a.parse_args();os.environ['RE4_RUNTIME04_PLAN']=str(a.plan)
 from fixture04 import Fixture
 from observer04 import Coverage,collect_one,load_contract
 binding,plan,audit=load_contract(a.plan);f=Fixture(a.plan);c=Coverage(10,10);scalar=collect_one(f.t,f.l,c);table=collect_one(f.t,f.l,c,True)
 logfile=a.out.with_suffix('.txt');suite=unittest.TestLoader().discover(str(Path(__file__).parent),pattern='test_*.py')
 with logfile.open('x',encoding='utf8') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
 report={'result':'PASS' if result.wasSuccessful() else 'FAIL','platform':platform.platform(),'python':platform.python_version(),'tests_run':result.testsRun,'skipped':[{'test':t.id(),'reason':reason} for t,reason in result.skipped],'failures':len(result.failures),'errors':len(result.errors),'binding_sha256':sha(a.plan/'observer-runtime-04/binding.json'),'phase_audit_sha256':sha(a.plan/'observer-runtime-04/phase-contract.json'),'path_audit_sha256':sha(a.plan/'observer-runtime-04/runtime04-path-width-report.json'),'test_log_sha256':sha(logfile),'runtime_dependencies':binding['source_sha256'],'actual_bound_scalar_mock':scalar,'actual_bound_table_mock':table,'coverage_mock':c.summary(),'scope':'Synthetic RAM follows actual e08c ELF CU/type/address bindings. Windows API tests read own Python process only, not Flycast. No programme/image/guest/replay/state writes. Live end-frame coverage remains UNQUALIFIED.'}
 with a.out.open('x',encoding='utf8') as out:json.dump(report,out,indent=2);out.write('\n')
 print(json.dumps({k:report[k] for k in ('result','platform','tests_run','skipped','failures','errors','binding_sha256')}))
 if not result.wasSuccessful():raise SystemExit(1)
if __name__=='__main__':main()
