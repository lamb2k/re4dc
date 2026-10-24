#pragma once
#ifndef RE4DC_WORLD_SCRATCH
#define RE4DC_WORLD_SCRATCH 0
#endif
#if RE4DC_WORLD_SCRATCH
#include <cstddef>
#include <cstdint>
namespace re4dc { namespace world_scratch {
constexpr unsigned kVertexBytes=8192,kOutcodeBytes=256,kReservedBytes=8448,kMaxWindow=600;
enum Arm : unsigned { A=0,B=1,C=2 };
// Single use per boot, including rejected/OFF fixtures. No reopening after cancel.
struct LateChoice {
    bool consumed=false;
    int take(bool open,unsigned mask){
        if(!open || consumed)return -1;
        consumed=true;
        return mask==0x80U?int(A):mask==0x100U?int(B):mask==0x200U?int(C):mask==0U?-2:-3;
    }
};
// Fixed 25-word little-endian regular-RAM ABI. seq odd while publishing.
// phase:0 dormant/OFF,1 selected,2 active,3 ended,4 refused/fault.
struct Snapshot {
    unsigned seq,version,phase,window_serial,mask,room,selected,requested,actual;
    unsigned remaining,frames,borrows,entries,exits,faults,last_fault,epoch;
    unsigned ccr,completed,restored,enter_us_lo,enter_us_hi,exit_us_lo,exit_us_hi,iterations;
};
static_assert(sizeof(Snapshot)==100,"scratch snapshot ABI");
inline void snapshot_write_begin(volatile Snapshot& s){++s.seq;asm volatile("" ::: "memory");}
inline void snapshot_write_end(volatile Snapshot& s){asm volatile("" ::: "memory");++s.seq;}

enum Fault : unsigned { None,NotAdmitted,BadRequest,WrongOwner,BadMode,BadLayout,LiveConsumer,StaleRoom,BadFrame };
// Hardware operations are injected into the exact same engine in the host tests.
struct Ops {
    std::uintptr_t (*owner)();
    unsigned (*ccr)();
    void (*toggle)(bool);
    std::uint64_t (*clock)();
    void (*reset_prime)();
    void* ocram;
    bool layout;
};
struct Stats {
    unsigned requested=A,actual=A,remaining=0,frames=0,borrows=0,entries=0,exits=0;
    unsigned faults=0,last_fault=None,epoch=0;
    std::uint64_t enter_us=0,exit_us=0;
};
// Separate ABI: the original 25-word Snapshot above remains unchanged.
// phase:0 dormant,1 measuring,2 final period awaits next begin,3 complete,4 invalid.
// kind=1: whole UI-begin-to-next-UI-begin WALL periods, INCLUDING waits.
struct MeterSnapshot {
    unsigned seq,version,phase,window_serial,arm,room,periods,drawn,skipped;
    unsigned engine_frames,borrows,entries,exits,faults,last_fault,ccr,restored;
    unsigned wall_us_lo,wall_us_hi,draw_us_lo,draw_us_hi,skip_us_lo,skip_us_hi;
    unsigned max_us_lo,max_us_hi,enter_us_lo,enter_us_hi,exit_us_lo,exit_us_hi;
    unsigned target,kind,complete;
};
static_assert(sizeof(MeterSnapshot)==128,"separate whole-period measurement ABI");
struct MeterTotals {
    unsigned phase=0,arm=A,room=0,periods=0,drawn=0,skipped=0;
    std::uint64_t wall_us=0,draw_us=0,skip_us=0,max_us=0;
};
class FrameMeter {
    MeterTotals out{};
    std::uint64_t candidate_us=0,start_us=0;
    unsigned candidate_room=0,last_token=0;
    bool candidate=false,open=false,candidate_skip=false,skip=false;
public:
    MeterTotals totals() const {return out;}
    void invalidate(){if(out.phase!=3){out.phase=4;open=false;candidate=false;}}
    void cancel(){if(out.phase==1 || out.phase==2)invalidate();}
    void boundary(std::uint64_t now,bool skipped,unsigned room,const Stats& st,unsigned token,bool restored){
        if(out.phase>=3)return; // completed results are immutable, invalid never rearms
        if(open){
            if(token || room!=out.room || st.faults || st.frames!=out.periods+1 || now<start_us){invalidate();return;}
            const auto elapsed=now-start_us;
            if(elapsed>~std::uint64_t(0)-out.wall_us){invalidate();return;}
            out.wall_us+=elapsed;
            if(skip){++out.skipped;out.skip_us+=elapsed;}else{++out.drawn;out.draw_us+=elapsed;}
            if(elapsed>out.max_us)out.max_us=elapsed;
            ++out.periods;open=false;
            if(out.periods==kMaxWindow){
                if(st.remaining || !restored)invalidate();else out.phase=3;
                return;
            }
            if(st.remaining!=kMaxWindow-out.periods || st.actual!=out.arm){invalidate();return;}
        }else if(out.phase){invalidate();return;} // a begin/end pair was missing
        candidate=true;candidate_us=now;candidate_skip=skipped;candidate_room=room;
    }
    void attach(unsigned token,unsigned arm,unsigned room,const Stats& st){
        if(!token || out.phase>=3)return;
        if(!candidate || open || arm>C || room!=candidate_room || !room || token==last_token || st.faults ||
           st.frames!=out.periods || st.remaining!=kMaxWindow-out.periods || st.actual!=arm){invalidate();return;}
        if(out.phase && (out.arm!=arm || out.room!=room)){invalidate();return;}
        out.arm=arm;out.room=room;out.phase=1;last_token=token;
        start_us=candidate_us;skip=candidate_skip;candidate=false;open=true;
    }
    void observe(const Stats& st){
        if(out.phase==1 || out.phase==2){
            if(st.faults || (!st.remaining && st.frames!=kMaxWindow))invalidate();
            else if(!st.remaining)out.phase=2; // restore is not the end of the whole period
        }
    }
};
class Engine {
    Ops op;
    Stats st{};
    std::uintptr_t thread=0;
    unsigned saved=0,room=0,pending_room=0,pending_arm=A,pending_frames=0,users=0,serial=0,frame_id=0;
    bool admitted=false,window=false,frame=false,closing=false,changed=false,pending=false;
    void* last_storage=nullptr;
    bool reject(Fault);
    bool expected() const;
    void finish();
public:
    explicit Engine(Ops ops):op(ops){}
    // The final ELF / module / KOS audit is a separate mandatory admission gate.
    bool admit(unsigned receipt_version);
    bool request(unsigned arm,unsigned iterations,unsigned room);
    bool begin(unsigned room);
    unsigned token() const {return frame?frame_id:0;}
    void end(unsigned token=0,bool aborted=false);
    void cancel();
    // +1 acquired; 0 no admitted experiment (ordinary RAM path); -1 unsafe active lease.
    int acquire(void* ram,void*& projected);
    void release();
    Stats stats() const { return st; }
};
}}
extern "C" volatile re4dc::world_scratch::Snapshot re4dc_world_scratch_snapshot;
extern "C" volatile re4dc::world_scratch::MeterSnapshot re4dc_world_scratch_meter_snapshot;
extern "C" int re4dc_world_scratch_meter_read(re4dc::world_scratch::MeterSnapshot* out);
extern "C" void re4dc_world_scratch_boundary(int skipped,unsigned room);
extern "C" int re4dc_world_scratch_admit(unsigned receipt_version);
extern "C" int re4dc_world_scratch_request(unsigned arm,unsigned iterations,unsigned room);
extern "C" void re4dc_world_scratch_begin(unsigned room);
extern "C" unsigned re4dc_world_scratch_frame_token();
extern "C" void re4dc_world_scratch_end(unsigned token,int aborted);
extern "C" void re4dc_world_scratch_cancel();
// Live arm for play (QA row / warp line `wscratch`): 0 A, 1 B, 2 C; held across rooms and windows.
extern "C" volatile unsigned re4dc_world_scratch_live;
extern "C" int re4dc_world_scratch_acquire(void* ram,void** projected);
extern "C" void re4dc_world_scratch_release();
extern "C" re4dc::world_scratch::Stats re4dc_world_scratch_stats();
// Frame guard covers every early return in native_ui_end_frame.
struct Re4dcWorldScratchFrameEnd {
    const bool* aborted=nullptr;
    unsigned token=re4dc_world_scratch_frame_token();
    ~Re4dcWorldScratchFrameEnd(){re4dc_world_scratch_end(token,aborted && *aborted);}
};
#endif
