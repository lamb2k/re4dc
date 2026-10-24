#!/usr/bin/env python3
"""Read-only frozen-source/design checks. No diagnostic implementation or target proof."""
import ctypes as C, hashlib, json, pathlib, resource, subprocess
resource.setrlimit(resource.RLIMIT_AS,(128*1024*1024,128*1024*1024))
ROOT=pathlib.Path('/root/work/lanes/water-rain24')
OUT=pathlib.Path('/mnt/c/Game Dev/Emulators/codex-lanes/water-rain24/rain-diag-next-v3')
BASE='bca44d58a1fa0a51fd87ba94deba8cba925c8998'
FILES=['src/game/filter06.cpp','src/game/espgen44.cpp','port/dreamcast/game/effects30.mk','src/game/espgen.cpp','src/game/espgen10.cpp','include/esp.h','include/espgen.h','src/game/filter.cpp','src/game/main.cpp','src/game/trans.cpp','src/game/main_sub.cpp','src/st1/r10c.cpp','src/st1/r10d.cpp','src/st1/r10e.cpp','port/dreamcast/game/platform/gx_stub.cpp','port/dreamcast/game/platform/native_ui.cpp','port/dreamcast/room/pvr_geometry.hpp','port/dreamcast/room/pvr_geometry.cpp','port/dreamcast/game/platform/native_effect.cpp','port/dreamcast/game/platform/include/native_effect_source.h','port/dreamcast/game/platform/kos_cache_p2_diag.cpp','port/dreamcast/tools/d367/qa20/mkqa.py','port/dreamcast/tools/d367/qa20/src/lake-scene5.txt','port/dreamcast/tools/d367/qa20/src/lake-scene4.txt','port/dreamcast/tools/d367/lake20/scenario/scene5-warp.txt','port/dreamcast/tools/d367/castgc/warps/r10c.txt','port/dreamcast/tools/d367/warp.py','port/dreamcast/tools/d367/stage_route.py']
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
# Publication/binding proposal model ONLY: not extracted runtime/target implementation.
ABI1=1; TERMINAL_EVEN=0xfffffffe; FAULT=0x80000000
FEATURE_ON=1<<0; CAUSAL44=1<<1; NATIVE_SAMPLE_VALID=1<<13; QUEUE_KEY_VALID=1<<14
EVENT_RETURN=8

def accepted(s1,blob,s2):
 seq=int.from_bytes(blob[:4],'little');abi=int.from_bytes(blob[4:8],'little')
 return s1==seq==s2 and 0<=seq<TERMINAL_EVEN and not(seq&1) and abi==ABI1

def publication(seq):
 # At fffffffc reserve the final bounded odd/even transition for exhaustion only.
 if seq&1 or seq>=TERMINAL_EVEN:return None
 return (seq+1,seq+2,FAULT if seq>=TERMINAL_EVEN-2 else 0)

r=Proposed();r.seq=2;r.abi_flags=ABI1
check('design-stable-even-ABI1-accepted',accepted(2,bytes(r),2))
for badabi in [0,2,0x10001,ABI1|FAULT]:
 r.abi_flags=badabi
 check('design-ABI-rejected-'+hex(badabi),not accepted(2,bytes(r),2))
r.abi_flags=ABI1
check('design-odd-torn-rejected',not accepted(1,bytes(r),2))
check('design-sequence-drift-rejected',not accepted(2,bytes(r),4))
r.seq=TERMINAL_EVEN
check('design-reserved-terminal-even-rejected-even-without-flag',not accepted(r.seq,bytes(r),r.seq))
check('design-last-normal-publication',publication(TERMINAL_EVEN-4)==(0xfffffffb,0xfffffffc,0))
check('design-final-publication-is-exhaustion-only',publication(TERMINAL_EVEN-2)==(0xfffffffd,0xfffffffe,FAULT))
check('design-never-publish-odd-max',publication(TERMINAL_EVEN) is None and publication(0xffffffff) is None)

def bind(before,after,kind,gid,rid,ok):return before<0xffffffff and after<0xffffffff and after==before+1 and kind==1 and gid==0x44 and rid!=0 and ok
check('design-causal-setter-bind',bind(4,5,1,0x44,1,True))
check('design-pointer-reuse-not-generation',not bind(4,6,1,0x44,1,True))
check('design-wrong-controller-rejected',not bind(4,5,1,0x43,1,True))
check('design-failed-setter-rejected',not bind(4,5,1,0x44,1,False))
check('design-generation-wrap-rejected',not bind(0xffffffff,0,1,0x44,1,True))

# All interpreted fields are a logical frozen-key oracle here. The Python tuple is not a C++ stack allocation proposal; unchanged nonwrapping seq witnesses publication-only fields.
KEY=['setter_generation','callback_generation','controller','record','head','observed_owner','setter_frame','callback_frame','queue_frame','event_frame','rooms','state_flags','particle_count','alpha_ids']
def key(r):return tuple(getattr(r,n) for n in KEY)
def joinable(r,frame,room):
 return (accepted(r.seq,bytes(r),r.seq) and bool(r.state_flags&FEATURE_ON) and
         bool(r.state_flags&QUEUE_KEY_VALID) and not(r.state_flags&NATIVE_SAMPLE_VALID) and
         r.setter_generation!=0 and r.callback_generation==r.setter_generation and
         r.callback_frame==r.queue_frame==r.event_frame==frame and
         (r.rooms&0xffff)==(r.rooms>>16)==room==0x10c)
def capture(r,frame,room):return (r.seq,key(r),frame,room) if joinable(r,frame,room) else None
def returned(r,captured,frame,room,requested,reported):
 # Counts remain lifetime aggregates even if attribution fails; this model returns validity only.
 return (captured is not None and captured==(r.seq,key(r),frame,room) and
         joinable(r,frame,room) and 0<=reported<=requested)
def nonreturn(r,event):
 # No later publication can thaw any coherent non-ABI1/faulted record.
 if r.abi_flags!=ABI1:return
 # Every non-return publication clears validity even if it changes no other field.
 step=publication(r.seq)
 if step is None:return
 r.state_flags&=~NATIVE_SAMPLE_VALID;r.event_reason=event
 r.seq=step[1]
 if step[2]:r.abi_flags|=step[2]
def sample(r,claim_cause=False):
 return (accepted(r.seq,bytes(r),r.seq) and bool(r.state_flags&NATIVE_SAMPLE_VALID) and
         r.event_reason==EVENT_RETURN and bool(r.state_flags&FEATURE_ON) and r.native_accepted<=r.native_requested and r.callback_generation==r.setter_generation!=0 and
         r.callback_frame==r.queue_frame==r.event_frame and
         (r.rooms&0xffff)==(r.rooms>>16)==0x10c and bool(r.state_flags&QUEUE_KEY_VALID) and
         (not claim_cause or bool(r.state_flags&CAUSAL44)))
def ready():
 r=Proposed();r.seq=20;r.abi_flags=ABI1;r.setter_generation=r.callback_generation=5
 r.controller=0x8c001000;r.record=0x8c002000;r.head=0x8c003000;r.observed_owner=1
 r.setter_frame=10;r.callback_frame=r.queue_frame=r.event_frame=330;r.rooms=0x010c010c
 r.state_flags=FEATURE_ON|QUEUE_KEY_VALID|CAUSAL44;r.particle_count=1100;r.alpha_ids=0x01015050
 return r
r=ready();c=capture(r,330,0x10c)
check('design-captured-return-positive',returned(r,c,330,0x10c,320,320))
check('design-captured-return-zero-is-valid-observation',returned(r,c,330,0x10c,320,0))
check('design-captured-return-partial-contract-control',returned(r,c,330,0x10c,320,17))
check('design-return-exceeds-request-rejected',not returned(r,c,330,0x10c,320,321))
for name,value in [('setter_generation',6),('callback_generation',4),('callback_frame',329),('queue_frame',329),('event_frame',329),('rooms',0x010c011b),('controller',0x8c001100),('record',0x8c002100),('head',0x8c003100),('state_flags',FEATURE_ON|QUEUE_KEY_VALID),('particle_count',0),('alpha_ids',0)]:
 r=ready();c=capture(r,330,0x10c);setattr(r,name,value)
 check('design-return-during-key-change-rejected-'+name,not returned(r,c,330,0x10c,320,320))
r=ready();c=capture(r,330,0x10c)
check('design-return-source-frame-changes-rejected',not returned(r,c,331,0x10c,320,320))
check('design-return-source-room-changes-rejected',not returned(r,c,330,0x11b,320,320))
r=ready();c=capture(r,330,0x10c);nonreturn(r,5)
check('design-same-frame-replacement-event-rejected-by-seq',not returned(r,c,330,0x10c,320,320))
r=ready();r.setter_generation+=1
check('design-no-new-call-generation-change-invalidates-join',capture(r,330,0x10c) is None)
for event in [1,2,3,4,5,6,7,9]:
 r=ready();r.state_flags|=NATIVE_SAMPLE_VALID;r.event_reason=EVENT_RETURN
 r.native_requested=320;r.native_accepted=17;r.accepted_total=48000
 check('design-last-native-sample-valid-before-event-'+str(event),sample(r,True))
 nonreturn(r,event)
 check('design-old-return-new-event-no-false-join-'+str(event),not sample(r) and not(r.state_flags&NATIVE_SAMPLE_VALID) and r.accepted_total==48000)
r=ready();r.state_flags|=NATIVE_SAMPLE_VALID;r.state_flags&=~CAUSAL44;r.event_reason=EVENT_RETURN
check('design-native-sample-with-unknown-controller-cause',sample(r) and not sample(r,True))
r=ready();r.state_flags|=NATIVE_SAMPLE_VALID;r.event_reason=5
check('design-valid-bit-alone-not-return-event',not sample(r))
check('design-unknown-archive-owner-explicit',not(r.state_flags&0x80000000))
check('actual-outer-Disp-and-PTS-suppressions-unobserved','if (!(pG->Disp_flg & 0x00100000) && !PTS(32))' in render and 'if (PTSK(1024))' in render)
check('actual-native-api-does-not-forward-PVR-ack','void submit_pvr(const void* data, std::size_t byte_count)' in text('port/dreamcast/room/pvr_geometry.cpp') and 'pvr_prim(data, byte_count);' in text('port/dreamcast/room/pvr_geometry.cpp') and 'void submit_pvr(const void*, std::size_t);' in text('port/dreamcast/room/pvr_geometry.hpp'))
# Model the completed publication, not merely a join predicate.
def complete(r,captured,frame,room,requested,reported):
 if r.abi_flags!=ABI1:return False
 ok=returned(r,captured,frame,room,requested,reported)
 step=publication(r.seq)
 if step is None:return False
 r.state_flags&=~NATIVE_SAMPLE_VALID
 r.event_reason=EVENT_RETURN if ok else 9
 if reported>=0xffffffff-r.accepted_total:r.accepted_total=0xffffffff;r.abi_flags|=FAULT
 else:r.accepted_total+=reported
 r.native_requested=requested if ok else 0;r.native_accepted=reported if ok else 0
 r.seq=step[1]
 if step[2]:r.abi_flags|=step[2]
 if ok and r.abi_flags==ABI1:r.state_flags|=NATIVE_SAMPLE_VALID
 return sample(r)
r=ready();c=capture(r,330,0x10c)
check('design-complete-actual-return-publishes-valid',complete(r,c,330,0x10c,320,17) and r.native_accepted==17)
r=ready();c=capture(r,330,0x10c);nonreturn(r,5)
check('design-return-after-replaced-callback-publishes-invalid',not complete(r,c,330,0x10c,320,320) and not(r.state_flags&NATIVE_SAMPLE_VALID) and r.accepted_total==320)
r=ready();c=capture(r,330,0x10c);r.setter_generation+=1
check('design-generation-change-with-no-new-native-call-invalid',not complete(r,c,330,0x10c,320,320) and not(r.state_flags&NATIVE_SAMPLE_VALID))
r=ready();c=capture(r,330,0x10c);r.seq=TERMINAL_EVEN-2;c=capture(r,330,0x10c)
check('design-return-on-terminal-transition-invalid',not complete(r,c,330,0x10c,320,320) and r.seq==TERMINAL_EVEN and not(r.state_flags&NATIVE_SAMPLE_VALID))
r=ready();r.state_flags|=NATIVE_SAMPLE_VALID;r.state_flags&=~FEATURE_ON;r.event_reason=EVENT_RETURN
check('design-native-valid-cannot-be-feature-OFF',not sample(r))
r=ready();r.state_flags|=NATIVE_SAMPLE_VALID;r.event_reason=EVENT_RETURN;r.native_requested=1;r.native_accepted=2
check('design-published-reported-exceeds-request-rejected',not sample(r))
def saturated_add(value,increment,maxvalue):return (maxvalue,FAULT) if increment>=maxvalue-value else (value+increment,0)
check('design-u16-counter-exhaustion-no-wrap',saturated_add(0xffff,1,0xffff)==(0xffff,FAULT))
check('design-u32-aggregate-exhaustion-no-wrap',saturated_add(0xffffffff,320,0xffffffff)==(0xffffffff,FAULT))
check('design-generation-reaching-maximum-rejected',not bind(0xfffffffe,0xffffffff,1,0x44,1,True))
check('design-u16-reaching-maximum-terminal',saturated_add(0xfffe,1,0xffff)==(0xffff,FAULT))
check('design-u32-reaching-maximum-terminal',saturated_add(0xfffffffe,1,0xffffffff)==(0xffffffff,FAULT))
r=ready();r.seq=TERMINAL_EVEN;r.abi_flags|=FAULT;before=bytes(r);nonreturn(r,5)
check('design-terminal-record-frozen-after-exhaustion',bytes(r)==before)
# Exactly the current coherent publication may latch a newly encountered fault.
def exhaust_nonterminal(r,kind):
 if r.abi_flags!=ABI1:return
 step=publication(r.seq)
 if step is None:return
 if kind=='counter':r.counts[0]=0xffff
 elif kind=='generation':r.setter_generation=0xffffffff
 elif kind=='aggregate':r.accepted_total=0xffffffff
 else:raise AssertionError(kind)
 r.state_flags&=~NATIVE_SAMPLE_VALID;r.abi_flags|=FAULT;r.seq=step[1]
def warm_init(r):
 # Cold initialization is a separate boot-only operation, not a warm thaw.
 if r.abi_flags!=ABI1:return
 nonreturn(r,3)
for kind in ['counter','generation','aggregate']:
 r=ready();exhaust_nonterminal(r,kind)
 check('design-'+kind+'-fault-final-coherent-at-nonterminal-seq',r.seq==22 and r.abi_flags==(ABI1|FAULT) and not accepted(r.seq,bytes(r),r.seq))
 for action in ['event','return','warm_init']:
  r=ready();c=capture(r,330,0x10c);exhaust_nonterminal(r,kind);before=bytes(r)
  if action=='event':nonreturn(r,5)
  elif action=='return':complete(r,c,330,0x10c,320,320)
  else:warm_init(r)
  check('design-'+kind+'-fault-frozen-through-'+action,bytes(r)==before)
for action in ['event','return','warm_init']:
 r=ready();c=capture(r,330,0x10c);r.abi_flags=0;before=bytes(r)
 if action=='event':nonreturn(r,5)
 elif action=='return':complete(r,c,330,0x10c,320,320)
 else:warm_init(r)
 check('design-unsupported-ABI-frozen-through-'+action,bytes(r)==before)
r=ready();r.accepted_total=0xffffffff-320;c=capture(r,330,0x10c)
check('design-actual-return-reaching-total-max-latches-fault',not complete(r,c,330,0x10c,320,320) and r.accepted_total==0xffffffff and r.abi_flags==(ABI1|FAULT))
for action in ['event','return','warm_init']:
 r=ready();r.accepted_total=0xffffffff-320;c=capture(r,330,0x10c);complete(r,c,330,0x10c,320,320);before=bytes(r)
 if action=='event':nonreturn(r,5)
 elif action=='return':complete(r,c,330,0x10c,320,320)
 else:warm_init(r)
 check('design-return-total-exhaustion-frozen-through-'+action,bytes(r)==before)

pins={'source':BASE,'source_files':{p:{'bytes':len(b),'sha256':sha(b),'blob':subprocess.check_output(['git','-C',str(ROOT),'rev-parse',BASE+':'+p],timeout=10).decode().strip()} for p,b in sources.items()},'layout':layout,'counter_names':COUNTERS,'persistent_bytes':128,'supersedes_design_commit':'e5f3b8faf4dfd81169de52cc2c16fc457edc92a0','native_sample_valid_bit':13,'queue_key_valid_bit':14,'terminal_even_sequence':0xfffffffe,'proposal_only':True,'actual_runtime_implemented':False,'target_tested':False,'source_checks_and_design_model_controls':passed,'model_limit':'No C++ diagnostic exists; proposed publication/binding model is not source-extracted implementation proof.'}
(OUT/'SOURCE-PINS-AND-DESIGN-CONTROLS.json').write_text(json.dumps(pins,indent=2)+'\n')
print(json.dumps({'source':BASE,'checks':len(passed),'persistent_bytes':C.sizeof(Proposed),'sdk':False,'guests':False,'runtime_edits':False}))