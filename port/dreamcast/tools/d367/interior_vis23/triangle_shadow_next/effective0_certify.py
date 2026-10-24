#!/usr/bin/env python3
"""Owned opt-in effective0 source adapter; default validates facts ONLY.

Actual private candidate generation requires --execute-private-pipeline and
separate authorization. This implementation unit never invokes that mode.
No historical helper, target all-LOD bound, ABI or asset is modified.
"""
import argparse,hashlib,json,sys
from pathlib import Path
from effective0_source import produce,source_levels,CAPABILITY_GUARD
from effective0_verify import verify

WRAPPER_SHA='b1f082fc0dd78371f7bf985dc3fa73ba26c4d1c48d623f76668bf2df090e2248'
CERTIFIER_SHA='34ee229d52514405ac59c9454a9e3fbfce610f39a91bd87451d0573d3d709bf8'
VERIFIER_SHA='f552bbe815576863dd7d7b099f09c54db56cb3290884e1978baf57cc3742fb47'

def digest(source):return hashlib.sha256(source.encode()).hexdigest()
def replace_once(source,before,after):
 if source.count(before)!=1:raise ValueError('Pinned source anchor changed '+before)
 return source.replace(before,after)

def producer_levels(p,cl):
 c=p.clusters[cl];counts=[p.levels[c['first_level']+lv][1] for lv in range(c['level_count'])]
 return source_levels(counts,True,True)

def verifier_levels(p,cl):
 c=p.clusters[cl];counts=[p.levels[c['first_level']+lv][1] for lv in range(c['level_count'])]
 if len(counts)==1:return (0,)
 if not counts or not counts[0]:return ()
 mapped=[]
 for raw in range(len(counts)):
  result=raw
  while result and counts[result]==0:result-=1
  mapped.append(result)
 return (0,) if set(mapped)=={0} else ()

def adapt_private_certifier(source):
 if digest(source)!=CERTIFIER_SHA:raise ValueError('Private geometric certifier changed')
 target="levels=[p.cluster_tris_world(pi,cl,l) for l in range(cluster['level_count'])]"
 if source.count(target)!=1:raise ValueError('Target all-LOD bound anchor changed')
 source=replace_once(source,"if not pairs_only and cluster['level_count']==1 and area>2e6",'if not pairs_only and EFFECTIVE0_LEVELS(p,cl)==(0,) and area>2e6')
 source=replace_once(source,"for level in range(cluster['level_count']):\n            found={}",'for level in EFFECTIVE0_LEVELS(p,cl):\n            found={}')
 if source.count(target)!=1:raise ValueError('Target all-LOD bounds were changed')
 return source

def adapt_private_verifier(source):
 if digest(source)!=VERIFIER_SHA:raise ValueError('Private geometric verifier changed')
 source=replace_once(source,"assert len(panels)==p.clusters[cl]['level_count']",'assert EFFECTIVE0_LEVELS(p,cl)==(0,) and len(panels)==1')
 # Keep the exact enumerated base panel level0 and ALL target bound logic.
 if 'for level,Q in enumerate(panels):' not in source:raise ValueError('Base panel verifier loop changed')
 return source

def adapted_wrapper(source):
 if digest(source)!=WRAPPER_SHA:raise ValueError('Owned historical wrapper changed')
 source=replace_once(source,"source=(root/'helpers'/'pvs'/'pvs_certify.py').read_text()", "source=adapt_private_certifier((root/'helpers'/'pvs'/'pvs_certify.py').read_text())")
 source=replace_once(source,'module.SOURCE_KEYS=source_keys;module.SOURCE_LEVELS=source_levels','module.SOURCE_KEYS=source_keys;module.SOURCE_LEVELS=source_levels;module.EFFECTIVE0_LEVELS=producer_levels')
 source=replace_once(source,"if a.selected_source_lod_witnesses or p.clusters[cl]['level_count']==1:",'if producer_levels(p,cl)==(0,):')
 source=replace_once(source,"verifier=importlib.import_module('pvs_verify')", "verifier=importlib.import_module('pvs_verify')\n    verifier_source=adapt_private_verifier((root/'helpers'/'pvs'/'pvs_verify.py').read_text())\n    verifier=type(sys)('effective0_geometric_verifier')\n    verifier.__file__=str(root/'helpers'/'pvs'/'pvs_verify.py')\n    exec(compile(verifier_source,verifier.__file__,'exec'),verifier.__dict__)\n    verifier.EFFECTIVE0_LEVELS=verifier_levels")
 source=replace_once(source,"lines=['// Private generated descriptor; no public asset data.']", "lines=['// Private generated descriptor; no public asset data.']+CAPABILITY_GUARD.splitlines()")
 source=replace_once(source,"(root/'qualification.json').write_text(json.dumps(result,indent=1)+'\\n')", "VERIFY_FINAL_FACTS()\n    result['effective0_sources_capability_required']=True\n    result['effective0_final_facts_sha256']=FINAL_FACTS_SHA\n    result['certifier_adaptation']='Exact effective-only source LOD0, fallback required; target all-LOD bounds unchanged; static opaque sources; max16 dependencies'\n    (root/'qualification.json').write_text(json.dumps(result,indent=1)+'\\n')")
 compile(source,'effective0-owned-wrapper','exec')
 return source

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('private',type=Path);ap.add_argument('--source-tree',required=True,type=Path);ap.add_argument('--texture-pack',required=True,type=Path);ap.add_argument('--enable-effective0',action='store_true');ap.add_argument('--execute-private-pipeline',action='store_true');a,rest=ap.parse_known_args()
 forbidden=('--conditional-sources','--conditional-targets','--selected-source-lod-witnesses')
 if any(x.split('=')[0] in forbidden for x in rest):raise ValueError('Research/conditional modes cannot compose with effective0 source admission')
 facts=produce(a.private/'inputs',a.source_tree,a.texture_pack,a.enable_effective0,a.enable_effective0);checked=verify(facts,a.private/'inputs',a.source_tree,a.texture_pack)
 if not a.execute_private_pipeline:
  print(json.dumps(dict(source_facts=checked,enabled=a.enable_effective0,pipeline_executed=False,runtime_admitted_cuts=0)));return
 if not a.enable_effective0:raise ValueError('Private pipeline needs explicit effective0 capability')
 source=adapted_wrapper((Path(__file__).parent.parent/'certify.py').read_text())
 # Recheck final copied inputs independently immediately before and after use.
 def reverify():return verify(facts,a.private/'inputs',a.source_tree,a.texture_pack)
 module=type(sys)('effective0_owned_certifier');module.__file__=str(Path(__file__))
 module.__dict__.update(adapt_private_certifier=adapt_private_certifier,adapt_private_verifier=adapt_private_verifier,producer_levels=producer_levels,verifier_levels=verifier_levels,CAPABILITY_GUARD=CAPABILITY_GUARD,VERIFY_FINAL_FACTS=reverify,FINAL_FACTS_SHA=digest(json.dumps(facts,sort_keys=True,separators=(',',':'))))
 exec(compile(source,module.__file__,'exec'),module.__dict__);old=sys.argv[:]
 try:
  reverify();sys.argv=['effective0-certify',str(a.private)]+rest;module.main();reverify()
 finally:sys.argv=old

if __name__=='__main__':main()
