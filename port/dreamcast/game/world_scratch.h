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
extern "C" int re4dc_world_scratch_admit(unsigned receipt_version);
extern "C" int re4dc_world_scratch_request(unsigned arm,unsigned iterations,unsigned room);
extern "C" void re4dc_world_scratch_begin(unsigned room);
extern "C" unsigned re4dc_world_scratch_frame_token();
extern "C" void re4dc_world_scratch_end(unsigned token,int aborted);
extern "C" void re4dc_world_scratch_cancel();
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
