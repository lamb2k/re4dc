"""Reviewer schedules against actual extracted production bodies; no SDK/guest."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import time

TREE=Path('/root/work/lanes/gc-motion24')
HERE=Path(__file__).resolve().parent
TOOLS=TREE/'port/dreamcast/tools/d367/gc_port23'
GAME=TREE/'port/dreamcast/game'
HEAD='5e6b7d8c0f76e7431f1a7787459faa41fb0b507c'
RUNTIME='fce285ddd77ced898b40f49ae310b91a539b7b5d'
sys.path.insert(0,str(TOOLS))
spec=importlib.util.spec_from_file_location('author_motion_fixture',TOOLS/'test_motion_unknown.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def git(*args):return subprocess.check_output(['git','-C',str(TREE),*args])

def main():
    start=time.monotonic()
    observed_head=git('rev-parse','HEAD').decode().strip()
    subprocess.check_call(['git','-C',str(TREE),'merge-base','--is-ancestor',HEAD,observed_head])
    allowed_metadata={'port/dreamcast/tools/d367/gc_port23/MOTION-UNKNOWN24.md',
                      'port/dreamcast/tools/d367/gc_port23/motion24-host-summary.json'}
    assert set(git('diff','--name-only',HEAD,observed_head).decode().splitlines())<=allowed_metadata
    assert not git('status','--porcelain')
    assert not git('diff','--name-only',RUNTIME,HEAD,'--','port/dreamcast/game')
    source_files=git('diff','--name-only','870789095c4c14fbdbf22043447b249063d2ec3a',HEAD).decode().splitlines()
    pins=[]
    for p in source_files:
        raw=git('show',HEAD+':'+p)
        control_input=p not in allowed_metadata
        if control_input:assert (TREE/p).read_bytes()==raw
        pins.append({'path':p,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
                     'current_control_input':control_input})
    fixture=module.MotionUnknownTests().fixture()
    prefix=fixture[:fixture.index('int main(){')]
    schedules=r'''
int main(){
 // Nested caller state is restored; pending classification remains frozen.
 reset();
 {MotionUnknownScope a(MotionDelayedModel|MotionViewTrack);
  {MotionUnknownScope b(motion_model_reason());motion_prepare();
   {MotionUnknownScope invalid(MotionModelPose|0x80000000U);motion_accept_current(1);}
   protected_context=true;motion_accept_pending(2);protected_context=false;
  }
  motion_accept_current(3);
 }
 motion_accept_current(4);
 expected(4,10,MotionDelayedModel|MotionViewTrack|MotionModelPose|MotionMissingRoute);
 assert(!faults && logs.empty());reset();
 // A successful pipe switch after one counted chunk followed by a culled
 // chunk and repeated close must not duplicate the old interval or suppress
 // the next unprepared interval. This differs from a second positive chunk.
 Window w;chunk(w,5);material_switch(w);chunk(w,0);one_close(w);one_close(w);
 motion_accept_pending(2);
 expected(2,7,MotionModelPose|MotionViewTrack|MotionUnclassifiedWorld);reset();
 // Failed switch -> close consumes the internal marker once; repeated close
 // is a no-op and later unprepared accepted output reports MissingRoute.
 switch_ok=false;w=Window{};chunk(w,5);material_switch(w);one_close(w);
 motion_accept_pending(1);one_close(w);
 expected(2,6,MotionModelPose|MotionViewTrack|MotionMissingRoute);reset();switch_ok=true;
 // Empty close sets no suppression. Nonzero direct interval remains visible.
 w=Window{};one_close(w);{MotionUnknownScope a(MotionViewTrack);motion_prepare();}
 ordinary_interval(11);expected(1,11,MotionViewTrack);reset();
 // Zero-count acceptance does not consume a marker. A fresh preparation
 // replaces it, so only the explicitly counted old prefix can be suppressed.
 {MotionUnknownScope a(MotionModelPose);motion_accept_current(6);}
 motion_pending_accounted();motion_accept_pending(0);
 {MotionUnknownScope a(MotionDelayedModel|MotionViewTrack);motion_prepare();}
 motion_accept_pending(7);expected(2,13,MotionModelPose|MotionDelayedModel|MotionViewTrack);reset();
 // Invalid combinations containing the internal high bit cannot forge it.
 for(unsigned v: {0U,0x80000001U,0x80000010U,0xffffffffU,0x20U}){
  MotionUnknownScope bad(v);motion_prepare();motion_accept_pending(1);
 }
 expected(5,5,MotionMissingRoute);reset();
 // Exact maximum does not set overflow; the first excess does, and subsequent
 // accepted reasons remain visible even after both counters have saturated.
 {MotionUnknownScope a(MotionViewTrack);motion_accept_current(~0U);}
 expected(1,~0U,MotionViewTrack);assert(!motion.overflow);
 {MotionUnknownScope a(MotionDelayedModel);motion_accept_current(1);}
 assert(motion.records==~0U && motion.overflow==1);
 motion.events=~0U;{MotionUnknownScope a(MotionModelPose);motion_accept_current(1);}
 expected(~0U,~0U,MotionViewTrack|MotionDelayedModel|MotionModelPose);
 motion_unknown_flush();assert(faults==1);
 assert(logs.find("events=4294967295 accepted_records=4294967295 overflow=1")!=std::string::npos);
 assert(logs.size()<256);expected(0,0,0);reset();
 // Flush cannot erase the caller scope or reclassify its pending receipt.
 {MotionUnknownScope a(MotionDelayedModel|MotionViewTrack);motion_prepare();motion_accept_pending(3);
  motion_unknown_flush();logs.clear();faults=0;
  protected_context=true;motion_accept_pending(4);protected_context=false;
 }
 expected(1,4,MotionDelayedModel|MotionViewTrack);assert(!faults && logs.empty());reset();
}
'''
    test=module.MotionUnknownTests()
    test.compile_run(prefix+schedules)
    # Force the safety-critical marker to remain reusable. The above schedules
    # must defeat this compiling mutant, rather than merely checking its text.
    altered=(prefix+schedules).replace('if(motion.pending==Accounted){motion.pending=MotionMissingRoute;return;}',
                                     'if(motion.pending==Accounted){return;}')
    assert altered!=prefix+schedules
    test.compile_run(altered,True)
    # Exercise exact Make fragment under additional invalid option strings and
    # inherited prerequisite refusals; no full repo make/build is invoked.
    cases=[]
    with tempfile.TemporaryDirectory(prefix='review-motion24-make-',dir='/dev/shm') as temp:
        make=Path(temp)/'Makefile'
        make.write_text((GAME/'gc_asset_gate.mk').read_text()+'\nall:\n\t@echo P=$(PLATFORM_CPPFLAGS) G=$(GAME_CPPFLAGS) O=$(PLATFORM_OBJS)\n')
        base=['make','-s','-f',str(make),'all','OBJDIR=objects']
        ordinary={'GC_ASSET_GATE':'1','GC_ASSET_MOTION_UNKNOWN':'1','NATIVE_ACTOR':'1','NATIVE_ACTOR_FAST':'1','PVR_STREAM':'1','AICA_AUDIO':'1'}
        overrides=[({'GC_ASSET_MOTION_UNKNOWN':v},False) for v in ['', '01','true','-1','1 0','0 1']]
        overrides += [({'NATIVE_ACTOR':'0'},False),({'GC_ASSET_GATE':'0'},False),({'PVR_STREAM':'0'},False),({'AICA_AUDIO':'0'},False),({},True)]
        for changes,passed in overrides:
            opts=dict(ordinary);opts.update(changes)
            result=subprocess.run(base+[k+'='+v for k,v in opts.items()],capture_output=True,text=True)
            assert (result.returncode==0)==passed,(opts,result.stdout,result.stderr)
            if passed:
                assert result.stdout.count('-DRE4DC_GC_ASSET_MOTION_UNKNOWN=1')==2
                assert 'objects/platform/gc_asset_motion_unknown.o' in result.stdout
            cases.append({'options':changes,'accepted':passed})
    # Ensure no concurrent author changes invalidate the evidence.
    assert git('rev-parse','HEAD').decode().strip()==observed_head
    assert not git('status','--porcelain')
    for pin in pins:
        if pin['current_control_input']:
            assert hashlib.sha256((TREE/pin['path']).read_bytes()).hexdigest()==pin['sha256']
    result={'status':'PASS','source':HEAD,'observed_metadata_only_head':observed_head,
        'runtime_identical_to':RUNTIME,'source_pins':pins,
        'additional_extracted_schedules':8,'compiling_marker_reuse_mutant_rejected':True,
        'additional_make_cases':cases,'elapsed_seconds':round(time.monotonic()-start,3),
        'limits':'Actual extracted helper/chunk/close/pipe-switch/previous-UI-interval bodies; mocked surrounding renderer. Not SDK, actual Render/guest or route completeness.'}
    (HERE/'INDEPENDENT-CONTROLS.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_pins','additional_make_cases')}))

if __name__=='__main__':main()
