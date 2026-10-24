#!/usr/bin/env python3
"""Review frozen isolated source integration; never writes the reviewed tree."""
import argparse,hashlib,importlib.util,json,resource,subprocess,tempfile,time
from pathlib import Path
SOURCE='8ce5ee2d00027268c3e69c9c300b819c1b14c63f'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--tree',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
 if a.out.exists():raise ValueError('Preserve prior review')
 resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));resource.setrlimit(resource.RLIMIT_CORE,(0,0));a.out.mkdir(parents=True);start=time.monotonic()
 assert subprocess.check_output(['git','-C',str(a.tree),'rev-parse','HEAD'],text=True).strip()==SOURCE
 assert not subprocess.check_output(['git','-c','core.preloadIndex=false','-C',str(a.tree),'status','--porcelain'])
 game=a.tree/'port/dreamcast/game';path=a.tree/'port/dreamcast/tools/d367/composition_int24/test_compose_integrated.py'
 spec=importlib.util.spec_from_file_location('integrated_controls',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 def old(ref,rel):return subprocess.check_output(['git','-C',str(a.tree),'show',ref+':port/dreamcast/game/'+rel],text=True)
 exact=[]
 for rel,ref in [('platform/include/pvs23_runtime.inc','7eb109ea1'),('platform/include/pvs23_proof.hpp','7eb109ea1'),('t2exact.mk','7eb109ea1'),('platform/include/native_ui_source_world.inc','b6b4fa7a3')]:
  assert (game/rel).read_text()==old(ref,rel);exact.append(dict(path=rel,reference=ref,sha256=sha(game/rel)))
 for rel,ref,anchors in [('platform/native_static.cpp','7eb109ea1',['void pvs_finish(bool success)','void pvs_observed(','void chunk_restart()']),('platform/native_static.cpp','b6b4fa7a3',['auto chunk_flush=[&]()->int']),('platform/native_ui.cpp','7eb109ea1',['extern "C" int re4dc_pvs23_opaque_ready'])]:
  for anchor in anchors:
   body=m.function((game/rel).read_text(),anchor);assert body==m.function(old(ref,rel),anchor);exact.append(dict(path=rel,anchor=anchor,reference=ref,sha256=hashlib.sha256(body.encode()).hexdigest()))
 current=(game/'platform/native_static.cpp').read_text();prior=old('7eb109ea1','platform/native_static.cpp')
 for s in (current,prior):assert s.count('pvs_source_placement')==4
 assert [x for x in current.splitlines() if 'pvs_source_placement' in x]==[x for x in prior.splitlines() if 'pvs_source_placement' in x]
 # Bind actual affine selection region, not only the later assignment strings.
 def affine(s):
  end=s.index('        const unsigned pvs_source_placement=');begin=s.rfind('#undef RE4DC_PASS_HIT',0,end);return s[begin:s.index('\n#endif',end)+len('\n#endif')]
 assert affine(current)==affine(prior)
 r=subprocess.run(['python3','-B',str(path),'-v'],capture_output=True,text=True,cwd=a.tree);assert not r.returncode,r.stdout+r.stderr;(a.out/'HOST.log').write_text(r.stdout+r.stderr)
 records=[]
 class Review(m.Controls):
  def build(self,src,expected=True):
   with tempfile.TemporaryDirectory(prefix='iv23-int24-ubsan-',dir='/dev/shm') as tmp:
    tmp=Path(tmp);(tmp/'unit.cpp').write_text(src)
    c=subprocess.run(['g++','-std=c++17','-O1','-fsanitize=undefined','-fno-sanitize-recover=all',str(tmp/'unit.cpp'),'-o',str(tmp/'run')],capture_output=True,text=True);assert not c.returncode,c.stderr
    run=subprocess.run([str(tmp/'run')],capture_output=True,text=True);assert (run.returncode==0)==expected,run.stderr
    if not expected:assert 'Assertion' in run.stderr and 'failed' in run.stderr,run.stderr
    records.append(dict(expected_success=expected,returncode=run.returncode,stderr=run.stderr))
 t=Review();t.test_actual_hot_cold_queue_snapshot0_and1();t.test_receipt_only_dispatch_and_mutant();t.test_semantic_mutants()
 # Independent copies/memory projections only: the reviewed tree stays frozen.
 block='#if (defined(RE4DC_GC_ASSET_GATE) && RE4DC_GC_ASSET_GATE != 0) || (defined(RE4DC_GC_ASSET_MOTION_UNKNOWN) && RE4DC_GC_ASSET_MOTION_UNKNOWN != 0)\n#error PS2_PVS_BATCH_COMPOSE does not yet qualify GC asset diagnostics\n#endif\n'
 mutants=[];original_text=m.text;original_game=m.GAME
 for label,rel,anchor in [('Make','scenery19.mk',' $(GC_ASSET_GATE) $(GC_ASSET_MOTION_UNKNOWN)'),('Static','platform/native_static.cpp',block),('UI','platform/native_ui.cpp',block)]:
  source=original_text(rel);assert source.count(anchor)==1;changed=source.replace(anchor,'')
  try:
   with tempfile.TemporaryDirectory(prefix='iv23-int24-guard-',dir='/dev/shm') as tmp:
    if label=='Make':
     tmp=Path(tmp);(tmp/'scenery19.mk').write_text(changed);m.GAME=tmp
    else:m.text=lambda name:changed if name==rel else original_text(name)
    try:
     (t.test_make_prerequisites_and_original_guard if label=='Make' else t.test_source_guards)()
    except AssertionError as e:
     assert '0 == 0' in str(e),str(e);mutants.append(dict(label=label,intended_failure=str(e)))
    else:raise AssertionError('Removed admission guard escaped '+label)
  finally:m.text=original_text;m.GAME=original_game
 assert not subprocess.check_output(['git','-c','core.preloadIndex=false','-C',str(a.tree),'status','--porcelain'])
 members=['port/dreamcast/game/scenery19.mk','port/dreamcast/game/platform/native_static.cpp','port/dreamcast/game/platform/native_ui.cpp','port/dreamcast/tools/d367/composition_int24/test_compose_integrated.py','port/dreamcast/tools/d367/composition_int24/README.md']
 out=dict(source=SOURCE,scope='Independent SOURCE/HOST only; actual material/numeric/scene/renderer services remain unqualified',source_members={p:sha(a.tree/p) for p in members},exact_component_bindings=exact,actual_affine_region_and_all4_propagations_identical=True,methods=7,off_CPP_pairs=18,extracted_host_object_identity=True,compiled_ubsan_controls=records,assertion_mutants=sum(not x['expected_success'] for x in records),admission_guard_mutants=mutants,review_tool_sha256=sha(__file__),elapsed_seconds=time.monotonic()-start,limits=dict(address_space_bytes=268435456,peak_child_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,jobs=1),reviewed_tree_unchanged=True,SDK_run=False,actual_new_cuts=0,actual_source_receipts_admitted=False)
 (a.out/'RECEIPT.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps(dict(source=SOURCE,methods=7,assertion_mutants=out['assertion_mutants'],admission_mutants=len(mutants),receipt_sha256=sha(a.out/'RECEIPT.json'))))
if __name__=='__main__':main()
