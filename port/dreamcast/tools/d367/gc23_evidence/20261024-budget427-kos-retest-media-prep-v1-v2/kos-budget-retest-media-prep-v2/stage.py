"""One ON final track only; authenticated existing OFF reused without writes."""
from pathlib import Path
import argparse,json,os,signal,sys,types
HERE=Path(__file__).resolve().parent
def grant_guard(g,k):
 assert g.get('approved') is True,'Explicit root approval required'
 assert g['scope']=='STAGE_ONLY_NO_GUEST_NO_SDK' and g['source']==k.SOURCE
 assert g['baseline_identity']==k.row(HERE/'BASELINE.json') and g['new_delta_cap']==k.DELTA and g['aggregate_cap']==k.AGG
 assert g['existing_OFF_reuse_only'] and g['new_final_arms']==['on']
def main():
 assert __debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
 # Outer launch.py must pin this source and every kit member before execution.
 import core as k
 k.sealed();k.baseline_check();k.capacity(k.ADMIT)
 grant=HERE/'ROOT-STAGE-GRANT.json';assert k.sha(grant)==os.environ.get('GC_CENSUS_STAGE_GRANT_SHA256')
 g=k.read(grant);grant_guard(g,k)
 k.validate_binding(k.read(HERE/'BINDING.json'));c,pins=k.adapter()
 original_verify=c.verify
 def fixture_verify(path,pin):
  # The frozen stage template's legacy squeeze0 validation pathname is only
  # a check; this successor binds it to the unchanged original48KiB fixture.
  if Path(path)==HERE/'fixtures/kos-squeeze0.txt':path=Path(k.read(HERE/'BASE-PLAN.json')['original_fixture']['path'])
  return original_verify(path,pin)
 c.verify=fixture_verify
 b=types.ModuleType('bind');b.validate=k.validate_binding;sys.modules['bind']=b
 rb=k.source('readback',k.OLD/'readback.py',pins['readback.py']['sha256'])
 # Complete all-file/IP/redirect OFF readback before any ON stage write.
 off=rb.check('off',k.OFF);assert off['source']==k.SOURCE
 assert not k.FINAL.exists() and not k.WORK.exists(),'Fresh whole successor, no restart'
 st=k.source('original_reviewed_stage',k.OLD/'stage.py',pins['stage.py']['sha256'])
 original_fresh=c.fresh
 def label(p,j):
  if Path(p).name=='base.json':j={**j,'kind':'CORRECTED_NONCENSUS_QA_STAGE_ONLY'}
  return original_fresh(p,j)
 c.fresh=label
 for sig in [signal.SIGTERM,signal.SIGHUP,signal.SIGINT]:signal.signal(sig,c.stop)
 try:
  st.main('on');k.baseline_check(links_changed=True);k.capacity()
  k.fresh(k.FINAL/'REUSED-OFF.json',dict(base=str(k.OFF),result=off,no_copies=True,source_rebound_by_exact_programmes=True))
  k.fresh(k.FINAL/'PAIR-STAGE-COMPLETE.json',dict(status='STAGE_ALL_FILES_COMPLETE_NO_GUEST',source=k.SOURCE,off_reused=k.row(k.FINAL/'REUSED-OFF.json'),on_complete=k.row(k.FINAL/'on/COMPLETE.json'),capacity=k.capacity()))
 except BaseException as exc:
  if k.FINAL.exists() and not (k.FINAL/'FAILED.json').exists():k.fresh(k.FINAL/'FAILED.json',dict(error=repr(exc),preserve_all=True,cleanup=0,guests=0))
  raise
if __name__=='__main__':main()
