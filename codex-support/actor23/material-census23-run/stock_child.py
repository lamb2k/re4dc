"""Unchanged stock runpy observer, no capture/input/game-memory hooks."""
from pathlib import Path
import json,os,runpy,sys
from contain import sha
from policy import fixed_stock_contract
from actor_log import EvidenceFailure
from material_census import census

def finish_proof(p,result,text):
 fixed_stock_contract(p)
 proof=census(result,text)
 proof.update(status='BOUND_PROGRAMME_CENSUS_LOG_COMPLETE',programme_binding='EXACT_MAIN_REVIEWED_SOURCE_AND_STAGED_IMAGE',bounded_census_complete=True,source=p['source'],programme_receipt_sha256=p['programme_receipt_sha256'],elf_sha256=p['elf_sha256'],raw_sha256=p['raw_sha256'],fixture_sha256=p['fixture_sha256'])
 return proof

def main():
 p=json.loads(Path(sys.argv[1]).read_text());fixed_stock_contract(p)
 if sha(p['stock_runner'])!=p['stock_sha256']or p['environment']!={k:v for k,v in os.environ.items()if k.startswith(('RE4DC_','FP_NOLIMIT'))}:raise ValueError('stock source/inherited environment changed')
 sys.argv=[p['stock_runner'],*p['stock_argv']];runpy.run_path(p['stock_runner'],run_name='__main__')
 cap=Path(p['capture']);result=json.loads((cap/'run-result.json').read_text());text=(cap/'run-output.txt').read_text(errors='replace')
 try:proof=finish_proof(p,result,text)
 except EvidenceFailure as error:
  (cap/'actor-census-result.json').write_text(json.dumps(dict(status='MODE1_CENSUS_NOT_QUALIFIED',observation_only=True,actual_cut_acceptance=False,error=str(error)),indent=2)+'\n');raise
 proof.update(stock_result_sha256=sha(cap/'run-result.json'),stock_log_sha256=sha(cap/'run-output.txt'));(cap/'actor-census-result.json').write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
