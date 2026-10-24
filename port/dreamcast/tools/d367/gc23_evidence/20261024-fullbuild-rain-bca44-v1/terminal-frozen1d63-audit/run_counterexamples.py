#!/usr/bin/env python3
from pathlib import Path
import sys,subprocess,json,hashlib,resource
resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
ROOT=Path('/dev/shm/gc-static-review1d63/source');GAME=ROOT/'port/dreamcast/game';OUT=Path(__file__).resolve().parent;RAM=Path('/dev/shm/gc-terminal-next1d63/controls');RAM.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'port/dreamcast/tools/d367/gc_port23'));from test_runtime_hooks import function
core=r'''
#include "gc_asset_static.h"
#include <cassert>
#include <cstdio>
#include <cstdarg>
#include <cstring>
#include <string>
using namespace re4dc_gcasset;bool protected_scope;std::string logs;
extern "C" void re4dc_log(const char*fmt,...){assert(!protected_scope);char s[256];va_list a;va_start(a,fmt);vsnprintf(s,sizeof s,fmt,a);va_end(a);logs+=s;}
int main(){assert(install(nullptr,0));
// A clean END does not prevent a later producer attempt. Closing diagnostic
// admission makes that future attempt a fault, but only a later pump logs it.
begin(0x111,1,Required);close_audio_admission();pump();end(1);assert(logs.find("errors=0")!=std::string::npos);logs.clear();protected_scope=true;auto invalid=audio_ticket();protected_scope=false;assert(invalid.slot==32&&logs.empty());pump();assert(logs.find("unowned-audio")!=std::string::npos);
// An empty observation queue can still have a captured uncompleted ticket.
logs.clear();begin(0x112,2,Required);auto outstanding=audio_ticket();assert(outstanding.slot<32);pump();close_audio_admission();end(2);assert(logs.find("errors=1")!=std::string::npos);logs.clear();protected_scope=true;queued_checked(outstanding,SoundBank,{});protected_scope=false;assert(logs.empty());pump();assert(logs.find("audio-room-lifetime")!=std::string::npos);
// Deferred geometry/payload latches intentionally have no visit stamp.
// If a draw is allowed after finish, it can remain silent then be flushed in
// another visit. A final fixture must stop that producer, not infer quiescence.
logs.clear();begin(0x113,3,Required);static PayloadProof proof;static int owner;unsigned char bytes[32]={17};assert(payload_capture(proof,&owner,bytes,sizeof bytes));const unsigned serial=proof.serial;payload_flush_all();end(3);assert(logs.find("errors=0")!=std::string::npos);logs.clear();protected_scope=true;payload_accept(&proof,serial,(1U<<SourceGeometry)|(1U<<Weapon));protected_scope=false;assert(logs.empty());begin(0x114,4,Required);payload_flush_all();end(4);assert(logs.find("room=0114 visit=4 kind=geometry")!=std::string::npos&&logs.find("source_geometry=1")!=std::string::npos&&logs.find("weapon=1")!=std::string::npos);payload_retire(proof);
}
'''
hand=(GAME/'coarse_actor_leon_hands.inc').read_text()
yield_control=r'''
#include <cassert>
using mutex_t=int;int lh_mutex;struct kthread_t{}thread;kthread_t*job_thd=&thread;unsigned char memory[64],*job_mem=memory;int job_blob=0,job_state=2;unsigned job_n=2,nblobs=2,aica=0,yields=0,refill[4],cell_blob[4],joins=0,frees=0;int job_queue[8],want[2];
void mutex_lock(int*){}void mutex_unlock(int*){}void thd_join(kthread_t*t,void*){assert(t==&thread);++joins;}void re4dc_motion_free(void*p){assert(p==memory);++frees;}void snd_mem_free(unsigned){}
namespace leon_hand_pack{}
''' + function(hand,'void job_enqueue(')+'\n'+function(hand,'extern "C" void re4dc_leon_hands_yield()')+r'''
int main(){re4dc_leon_hands_yield();assert(joins==1&&frees==1&&!job_thd&&!job_mem&&!job_n&&job_blob==-1);job_enqueue(1);assert(job_n==1&&job_queue[0]==1);}
'''
dvd=(GAME/'platform/dvd.cpp').read_text()
cancel=r'''
#include <cassert>
using s32=int;struct DVDCommandBlock{int state;};using DVDCBCallback=void(*)(s32,DVDCommandBlock*);constexpr int DVD_STATE_END=0;bool native_read_still_active=true;unsigned callbacks;
void callback(s32 result,DVDCommandBlock*b){assert(result==0&&b->state==DVD_STATE_END&&native_read_still_active);++callbacks;}
''' + function(dvd,'int DVDCancelAsync(')+'\n'+function(dvd,'s32 DVDCancelAll(')+r'''
int main(){DVDCommandBlock b{1};assert(DVDCancelAsync(&b,callback)==1);assert(callbacks==1&&native_read_still_active&&b.state==DVD_STATE_END);assert(DVDCancelAll()==0&&native_read_still_active);}
'''
results=[]
for name,source,link in [('actual-gate-end-late-ticket-payload-counterexamples',core,True),('actual-hand-yield-reopens-queue',yield_control,False),('actual-native-DVD-cancel-is-not-a-reader-fence',cancel,False)]:
 cpp=RAM/(name+'.cpp');exe=RAM/name;cpp.write_text(source);(OUT/(name+'.cpp')).write_text(source);cmd=['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror','-DRE4DC_GC_ASSET_GATE='+('1' if link else '0'),'-I',str(GAME/'platform/include'),str(cpp)]
 if link:cmd += [str(GAME/'platform'/f) for f in ['gc_asset_gate.cpp','gc_asset_members.cpp','gc_asset_payloads.cpp']]
 q=subprocess.run(cmd+['-o',str(exe)],capture_output=True,text=True);assert q.returncode==0,q.stderr;q=subprocess.run(['/lib64/ld-linux-x86-64.so.2',str(exe)],capture_output=True,text=True);assert q.returncode==0,q.stderr;results.append({'name':name,'pass':True,'returncode':q.returncode,'fixture_sha256':hashlib.sha256(source.encode()).hexdigest()})
(OUT/'independent-counterexamples.json').write_text(json.dumps({'source':'1d63cffe3a232c402418f2f2d919e7abae476957','scope':'actual gate/payload and source-extracted hand yield/native cancel; synthetic providers; single-thread deterministic interleavings, not concurrent target proof','groups':results,'no_terminal_quiescence_proved':True},indent=2)+'\n');print('PASS actual-source counterexamples: late audio faults require later pump; outstanding ticket despite empty queue; late payload can migrate without producer stop; hand yield allows reenqueuing; native cancel has no read fence')