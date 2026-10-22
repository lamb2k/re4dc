#include "world_scratch.h"
#if RE4DC_WORLD_SCRATCH
namespace re4dc { namespace world_scratch {
// CCR stable bits. OCI/ICI self-clearing invalidate commands are not state.
constexpr unsigned kOra=1U<<5,kOix=1U<<7,kNormal=(1U<<0)|(1U<<2)|(1U<<8);
constexpr unsigned kStable=(1U<<0)|(1U<<1)|(1U<<2)|kOra|kOix|(1U<<8)|(1U<<15);
bool Engine::reject(Fault why){++st.faults;st.last_fault=why;return false;}
bool Engine::expected() const {return (op.ccr()&kStable)==(saved|(changed?kOra:0));}
bool Engine::admit(unsigned receipt_version){
    if(window || frame || users)return reject(LiveConsumer);
    if(receipt_version!=1)return reject(NotAdmitted);
    if(!op.layout || !op.ocram || (reinterpret_cast<std::uintptr_t>(op.ocram)&31U))return reject(BadLayout);
    if((op.ccr()&kStable)!=kNormal)return reject(BadMode);
    thread=op.owner();if(!thread)return reject(WrongOwner);
    admitted=true;return true;
}
bool Engine::request(unsigned arm,unsigned iterations,unsigned target_room){
    if(!admitted)return reject(NotAdmitted);
    if(op.owner()!=thread)return reject(WrongOwner);
    if(arm>C || !iterations || iterations>kMaxWindow || !target_room)return reject(BadRequest);
    pending=true;pending_arm=arm;pending_frames=iterations;pending_room=target_room;st.requested=arm;
    return true; // no cache transition, even inside a live consumer
}
void Engine::finish(){
    if(!closing || users || frame || op.owner()!=thread)return;
    // Never overwrite a foreign CCR change, in any arm. Revoke admission.
    if(!expected()){reject(BadMode);admitted=false;}
    else if(changed){
        const auto t=op.clock();op.toggle(false);st.exit_us+=op.clock()-t;++st.exits;
        if((op.ccr()&kStable)!=saved){reject(BadMode);admitted=false;}
    }
    changed=false;window=false;closing=false;st.actual=admitted?A:3U;st.remaining=0;
    last_storage=nullptr;++st.epoch;op.reset_prime();
}
bool Engine::begin(unsigned current_room){
    if(!admitted)return false;
    if(op.owner()!=thread){reject(WrongOwner);cancel();return false;}
    if(frame){reject(BadFrame);cancel();return false;}
    if(closing){finish();if(!admitted)return false;}
    if(window && (!expected() || room!=current_room)){
        reject(room!=current_room?StaleRoom:BadMode);cancel();return false;
    }
    if(pending){
        if(users){reject(LiveConsumer);return false;}
        closing=window;finish();
        if(!admitted)return false;
        if(pending_room!=current_room){pending=false;return reject(StaleRoom);}
        if((op.ccr()&kStable)!=kNormal){pending=false;return reject(BadMode);}
        saved=op.ccr()&kStable;room=current_room;window=true;closing=false;
        st.actual=pending_arm;st.remaining=pending_frames;pending=false;
        if(st.actual!=A){const auto t=op.clock();op.toggle(true);st.enter_us+=op.clock()-t;++st.entries;changed=true;
            if(!expected()){reject(BadMode);cancel();return false;}}
        last_storage=nullptr;++st.epoch;op.reset_prime();
    }
    if(!window || closing)return false;
    frame=true;if(!++serial)++serial;frame_id=serial;return true;
}
void Engine::end(unsigned token,bool aborted){
    if(token && (!frame || frame_id!=token)){if(frame)reject(BadFrame);return;}
    if(aborted){cancel();return;}
    if(!frame){finish();return;}
    if(op.owner()!=thread){reject(WrongOwner);return;}
    frame=false;++st.frames;
    if(users){reject(LiveConsumer);closing=true;pending=false;}
    if(st.remaining && !--st.remaining)closing=true;
    finish();
}
void Engine::cancel(){
    pending=false;
    if(window){closing=true;frame=false;finish();}
}
int Engine::acquire(void* ram,void*& projected){
    projected=ram;
    if(!window)return 0;
    if(op.owner()!=thread){reject(WrongOwner);return -1;}
    if(!frame || closing){reject(BadFrame);return -1;}
    if(!expected()){reject(BadMode);closing=true;return -1;}
    if(users){reject(LiveConsumer);return -1;} // no nested or reentrant OCRAM / tail alias
    if(!ram || (reinterpret_cast<std::uintptr_t>(ram)&31U)){reject(BadLayout);return -1;}
    projected=st.actual==C?op.ocram:ram;
    if(projected!=last_storage){last_storage=projected;++st.epoch;op.reset_prime();}
    ++users;++st.borrows;return 1;
}
void Engine::release(){
    if(!users){reject(LiveConsumer);return;}
    if(op.owner()!=thread){reject(WrongOwner);return;}
    --users;finish();
}
}}
#ifndef RE4DC_WORLD_SCRATCH_HOST
#include <kos/thread.h>
#include <kos/irq.h>
#include <dc/cache.h>
#include <arch/timer.h>
extern "C" void re4dc_world_scratch_prime_reset();
namespace {
// Occupy the complete KOS section. Another linked OCRAM allocation overflows
// its 8192-byte linker bound instead of silently sharing this array.
__ocram alignas(32) unsigned char projected_records[re4dc::world_scratch::kVertexBytes];
std::uintptr_t owner(){return irq_inside_int()?0:reinterpret_cast<std::uintptr_t>(thd_get_current());}
unsigned ccr(){return *reinterpret_cast<volatile unsigned*>(0xff00001cU);}
void toggle(bool on){dcache_toggle_ocram(on);}
std::uint64_t clock_us(){return timer_us_gettime64();}
re4dc::world_scratch::Engine engine({owner,ccr,toggle,clock_us,re4dc_world_scratch_prime_reset,projected_records,
    reinterpret_cast<std::uintptr_t>(projected_records)==0x7c001000U && sizeof(projected_records)==8192});
}
extern "C" int re4dc_world_scratch_admit(unsigned v){return engine.admit(v);}
extern "C" int re4dc_world_scratch_request(unsigned a,unsigned n,unsigned r){return engine.request(a,n,r);}
extern "C" void re4dc_world_scratch_begin(unsigned r){engine.begin(r);}
extern "C" unsigned re4dc_world_scratch_frame_token(){return engine.token();}
extern "C" void re4dc_world_scratch_end(unsigned token,int aborted){if(token)engine.end(token,aborted!=0);}
extern "C" void re4dc_world_scratch_cancel(){engine.cancel();}
extern "C" int re4dc_world_scratch_acquire(void* ram,void** out){return engine.acquire(ram,*out);}
extern "C" void re4dc_world_scratch_release(){engine.release();}
extern "C" re4dc::world_scratch::Stats re4dc_world_scratch_stats(){return engine.stats();}
#endif
#endif
