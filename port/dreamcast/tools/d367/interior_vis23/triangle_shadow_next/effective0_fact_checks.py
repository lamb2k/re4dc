#!/usr/bin/env python3
"""Final physical source facts and opt-in adapter controls; no visibility output."""
import argparse,copy,hashlib,json,resource,subprocess,tempfile
from pathlib import Path
import effective0_source as producer
import effective0_verify as verifier
import effective0_certify as adapter

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source-tree',required=True,type=Path);ap.add_argument('--inputs',required=True,type=Path);ap.add_argument('--texture-pack',required=True,type=Path);ap.add_argument('--private-helpers',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
 if a.out.exists():raise ValueError('Preserve previous receipt')
 resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));records=[]
 def check(name,fn,refuse=False):
  try:result=fn()
  except (ValueError,AssertionError) as e:
   if not refuse:raise
   records.append(dict(name=name,refused=True,reason=str(e)));return
  if refuse:raise AssertionError('Unsafe acceptance '+name)
  records.append(dict(name=name,passed=True));return result
 facts=check('actual-final-producer',lambda:producer.produce(a.inputs,a.source_tree,a.texture_pack,True,True))
 result=check('independent-actual-final-verifier',lambda:verifier.verify(facts,a.inputs,a.source_tree,a.texture_pack))
 assert result['physical_clusters']==95 and result['oriented_faces']==8168 and result['actual_raw_choices']==190
 # Cache the already independently decoded/material-authenticated descriptor census
 # for repeated metadata negatives only; final byte hashing remains live each call.
 real=producer.f.material_census;cache=real(a.source_tree,a.texture_pack,producer.f.Pkg(a.inputs/'ps2-world.re4mesh',a.inputs/'ps2-world.r4pw'))
 producer.f.material_census=lambda *args:cache
 try:
  off=check('default-off-producer',lambda:producer.produce(a.inputs,a.source_tree,a.texture_pack))
  assert not off['clusters'] and not off['capability_guard']
  check('default-off-verifier',lambda:verifier.verify(off,a.inputs,a.source_tree,a.texture_pack))
  check('enabled-without-fallback',lambda:producer.produce(a.inputs,a.source_tree,a.texture_pack,True,False),True)
  check('nonboolean-producer',lambda:producer.produce(a.inputs,a.source_tree,a.texture_pack,'1',True),True)
  edits=[('missing-capability',lambda x:x.update(capability_guard='')),('disabled-but-text-retained',lambda x:x.update(capability_guard='#if 0\n'+x['capability_guard']+'#endif\n')),('commented-guard',lambda x:x.update(capability_guard='/*'+x['capability_guard']+'*/')),('foreign-row',lambda x:x['clusters'][0].update(cluster=999)),('missing-row',lambda x:x['clusters'].pop()),('nonempty-higher',lambda x:x['clusters'][0]['meshlet_counts'].__setitem__(1,1)),('fake-face-count',lambda x:x.update(oriented_faces=8169)),('string-capability',lambda x:x.update(enabled='1')),('claimed-runtime-cut',lambda x:x.update(runtime_admitted_cuts=1))]
  for name,edit in edits:
   changed=copy.deepcopy(facts);edit(changed)
   check(name,lambda:verifier.verify(changed,a.inputs,a.source_tree,a.texture_pack),True)
  with tempfile.TemporaryDirectory(prefix='iv23-effective0-facts-',dir='/dev/shm') as tmp:
   tmp=Path(tmp)
   for name in producer.f.audit.FROZEN_INPUT_SHA256:(tmp/name).write_bytes((a.inputs/name).read_bytes())
   for name in producer.f.audit.FROZEN_INPUT_SHA256:
    path=tmp/name;old=path.read_bytes();path.write_bytes(bytes([old[0]^1])+old[1:])
    check('mutated-final-producer-'+name,lambda:producer.produce(tmp,a.source_tree,a.texture_pack,True,True),True)
    check('mutated-final-verifier-'+name,lambda:verifier.verify(facts,tmp,a.source_tree,a.texture_pack),True)
    path.write_bytes(old)
   # Compile the exact emitted canonical guard, including forged numeric macros.
   src=tmp/'cap.cpp';src.write_text(producer.CAPABILITY_GUARD+'int main(){return 0;}\n')
   for feature,fallback in [(1,1),(None,1),(0,1),(2,1),(1,None),(1,0),(1,2)]:
    flags=[]
    if feature is not None:flags+=['-DRE4DC_PS2_PVS_EFFECTIVE0_SOURCES='+str(feature)]
    if fallback is not None:flags+=['-DRE4DC_PS2_WORLD_NONEMPTY_LOD='+str(fallback)]
    run=subprocess.run(['g++','-fsyntax-only']+flags+[str(src)],capture_output=True,text=True)
    assert (run.returncode==0)==(feature==fallback==1)
    if run.returncode:assert '#error Effective-only0' in run.stderr
    records.append(dict(name='descriptor-capability-'+str(feature)+'-'+str(fallback),compile_returncode=run.returncode))
 finally:producer.f.material_census=real
 sources=[(adapter.adapt_private_certifier,a.private_helpers/'pvs_certify.py'),(adapter.adapt_private_verifier,a.private_helpers/'pvs_verify.py'),(adapter.adapted_wrapper,Path(__file__).parent.parent/'certify.py')]
 for fn,path in sources:
  text=path.read_text();adapted=check('pinned-adapter-'+path.name,lambda:fn(text));compile(adapted,path.name,'exec')
  check('foreign-adapter-'+path.name,lambda:fn(text+'\n'),True)
 # Independent fallback-enumerating verifier and producer must agree, including
 # higher-count/empty/null public count negatives, without target-bound changes.
 class P:pass
 for counts in ([1],[0],[2,0],[1,0,0,0],[0,0],[1,1],[1,0,1],[]):
  p=P();p.clusters=[dict(first_level=0,level_count=len(counts))];p.levels=[(0,n,0) for n in counts]
  assert adapter.producer_levels(p,0)==adapter.verifier_levels(p,0)
  records.append(dict(name='adapter-counts-'+str(counts),source_levels=list(adapter.producer_levels(p,0))))
 here=Path(__file__).parent;out=dict(kind='Source facts only; no geometric certificate or visibility data generated',controls=records,actual=result,source_facts=facts,tool_sha256=producer.f.digest(Path(__file__)),sources={p.name:producer.f.digest(p) for p in [here/'effective0_source.py',here/'effective0_verify.py',here/'effective0_certify.py']},runtime_admitted_cuts=0,pipeline_executed=False,limits=dict(address_space_bytes=268435456,jobs=1,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
 with a.out.open('x') as dst:json.dump(out,dst,indent=1);dst.write('\n')
 print(json.dumps(dict(controls=len(records),actual=result,out=str(a.out))))
if __name__=='__main__':main()
