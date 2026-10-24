#!/usr/bin/env python3
"""Read-only frozen-source/design checks. No diagnostic implementation or target proof."""
import ctypes as C, hashlib, json, pathlib, resource, subprocess
resource.setrlimit(resource.RLIMIT_AS,(128*1024*1024,128*1024*1024))
ROOT=pathlib.Path('/root/work/lanes/water-rain24')
OUT=pathlib.Path('/mnt/c/Game Dev/Emulators/codex-lanes/water-rain24/rain-diag-next')
BASE='bca44d58a1fa0a51fd87ba94deba8cba925c8998'
FILES=['src/game/filter06.cpp','src/game/espgen44.cpp','port/dreamcast/game/effects30.mk','src/game/espgen.cpp','src/game/espgen10.cpp','include/esp.h','include/espgen.h','src/game/filter.cpp','src/game/main.cpp','src/game/trans.cpp','src/game/main_sub.cpp','src/st1/r10c.cpp','src/st1/r10d.cpp','src/st1/r10e.cpp','port/dreamcast/game/platform/gx_stub.cpp','port/dreamcast/game/platform/native_ui.cpp','port/dreamcast/game/platform/native_effect.cpp','port/dreamcast/game/platform/include/native_effect_source.h','port/dreamcast/game/platform/kos_cache_p2_diag.cpp','port/dreamcast/tools/d367/qa20/mkqa.py','port/dreamcast/tools/d367/qa20/src/lake-scene5.txt','port/dreamcast/tools/d367/qa20/src/lake-scene4.txt','port/dreamcast/tools/d367/lake20/scenario/scene5-warp.txt','port/dreamcast/tools/d367/castgc/warps/r10c.txt','port/dreamcast/tools/d367/warp.py','port/dreamcast/tools/d367/stage_route.py']
sources={p:subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+p],timeout=15) for p in FILES}
def text(p):return sources[p].decode()
def sha(b):return hashlib.sha256(b).hexdigest()
def line(p,needle):
 lines=text(p).splitlines();hits=[i+1 for i,x in enumerate(lines) if needle in x]
 assert hits,(p,needle)
 return hits
COUNTERS=['setter_calls','causal44_set','destruct44','room_init','alloc_failure','trans_enter','trans_zero','trans_indoor','trans_stopped','callback_enter','callback_candidate','callback_wrong_signature','callback_zero_alpha','ticket_queued','cancel_setter','cancel_room_init','cancel_callback_replace','flush_stale_frame','flush_state_reject','ticket_consumed','stopped_flush','return_zero','return_positive','binding_reject']
WORDS=['seq','abi_flags','setter_generation','callback_generation','controller','record','head','observed_owner','setter_frame','callback_frame','queue_frame','event_frame','rooms','event_reason','state_flags','particle_count','alpha_ids','native_requested','native_accepted','accepted_total']
class Proposed(C.LittleEndianStructure):_fields_=[(x,C.c_uint32) for x in WORDS]+[('counts',C.c_uint16*24)]
assert C.sizeof(Proposed)==128
assert Proposed.counts.offset==80
layout=[{'offset':getattr(Proposed,n).offset,'bytes':4,'name':n} for n in WORDS]+[{'offset':80+2*i,'bytes':2,'name':n} for i,n in enumerate(COUNTERS)]
passed=[]
def check(name,condition):assert condition,name;passed.append(name)
f=text('src/game/filter06.cpp');e=text('src/game/espgen44.cpp');dispatch=text('src/game/espgen.cpp');outer=text('src/game/filter.cpp');main=text('src/game/main.cpp');render=text('src/game/trans.cpp');gx=text('port/dreamcast/game/platform/gx_stub.cpp');native=text('port/dreamcast/game/platform/native_ui.cpp')
check('only-two-current-setter-call-sites',sum(text(p).count('Filter06SetParam(') for p in ['src/game/espgen44.cpp'])==2)
check('actual-44-set-and-destruct-consume-existing-call',e.count('Filter06SetParam(')==2 and 'rec->Id == 0' in e and 'case 1:' in e)
check('actual-record-reference-not-assumed-contiguous', 'rec = reference;' in dispatch and 're4dc_effect_ref(head, no)' in dispatch)
check('owner-copy-is-runtime-attribution', 'w->info.owner = e;' in text('src/game/espgen10.cpp'))
check('outer-gates-outside-owned-three-files','Screen.width == 512.0f && Screen.height == 448.0f && !Filter09GetbUse()' in outer)
check('actual-stale-rejection-and-draw-stop-branch', 's_raindc_queued_frame != pG->Frame_cnt' in f and 'dt = 0; // source Stop freezes motion/alpha but still draws' in f)
loop=main[main.index('            Render();'):main.index('            TaskScheduler();')]
check('render-before-source-frame-increment',loop.index('Render();')<loop.index('pG->Frame_cnt++;'))
check('actual-OT-before-ADEB',render.rindex('ExecOt(OT_TYPE_MAX);')<render.rindex('GXSetDrawSync(0xADEB);'))
check('actual-finish-before-rain',gx.index('if(token==0xADEB)re4dc_model_finish_source_draws();')<gx.index('if(token==0xADEB)re4dc_rain_flush();'))
check('renderer-return-not-request', 's_raindc_sent += re4dc_rain_dc_streaks(s_raindc_out, n);' in f and 'if(!s || !n || !frame_ready || stream_aborted || draining_parts || !source_draws_finished)return 0;' in native)
check('qa-dam-is-existing-passage-seed', 'fixture(\'qa20/src/lake-scene5.txt\')' in text('port/dreamcast/tools/d367/qa20/mkqa.py') and 'pos -843 0 -605' in text('port/dreamcast/tools/d367/qa20/src/lake-scene5.txt'))
check('distinct-existing-lower-bank-source-seed','pos 27865 -15316 43935' in text('port/dreamcast/tools/d367/castgc/warps/r10c.txt'))
check('natural-ladder-stop-ten-source-ticks','U32Set(pG->Stop_flg, 0xFFFFFFFF);' in text('src/st1/r10c.cpp') and 'SceSleep(10);' in text('src/st1/r10c.cpp'))
# Publication/binding proposal model ONLY: this is not extracted runtime or target implementation.
def accepted(s1,blob,s2):return s1==s2==int.from_bytes(blob[:4],'little') and s1%2==0 and not(int.from_bytes(blob[4:8],'little')&0x80000000)
r=Proposed();r.seq=2;r.abi_flags=1
check('design-stable-even-accepted',accepted(2,bytes(r),2))
check('design-odd-torn-rejected',not accepted(1,bytes(r),2))
check('design-sequence-drift-rejected',not accepted(2,bytes(r),4))
r.abi_flags|=0x80000000
check('design-exhaustion-rejected',not accepted(2,bytes(r),2))
def bind(before,after,kind,gid,rid,ok):return before<0xffffffff and after==before+1 and kind==1 and gid==0x44 and rid!=0 and ok
check('design-causal-setter-bind',bind(4,5,1,0x44,1,True))
check('design-pointer-reuse-not-generation',not bind(4,6,1,0x44,1,True))
check('design-wrong-controller-rejected',not bind(4,5,1,0x43,1,True))
check('design-failed-setter-rejected',not bind(4,5,1,0x44,1,False))
check('design-generation-wrap-rejected',not bind(0xffffffff,0,1,0x44,1,True))
check('design-unknown-archive-owner-explicit',r.observed_owner==0 and not(r.state_flags&0x80000000))
pins={'source':BASE,'source_files':{p:{'bytes':len(b),'sha256':sha(b),'blob':subprocess.check_output(['git','-C',str(ROOT),'rev-parse',BASE+':'+p],timeout=10).decode().strip()} for p,b in sources.items()},'layout':layout,'counter_names':COUNTERS,'persistent_bytes':128,'proposal_only':True,'actual_runtime_implemented':False,'target_tested':False,'source_checks_and_design_model_controls':passed,'model_limit':'No C++ diagnostic exists; proposed publication/binding model is not source-extracted implementation proof.'}
(OUT/'SOURCE-PINS-AND-DESIGN-CONTROLS.json').write_text(json.dumps(pins,indent=2)+'\n')
print(json.dumps({'source':BASE,'checks':len(passed),'persistent_bytes':C.sizeof(Proposed),'sdk':False,'guests':False,'runtime_edits':False}))