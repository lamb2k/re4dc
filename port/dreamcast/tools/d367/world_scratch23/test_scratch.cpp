#include "world_scratch.h"
#include "mesh_fastpath.hpp"
#include <cassert>
#include <cstdio>
#include <cstring>
using namespace re4dc::world_scratch;
static Engine* guard_engine=nullptr;
extern "C" unsigned re4dc_world_scratch_frame_token(){return guard_engine?guard_engine->token():0;}
extern "C" void re4dc_world_scratch_end(unsigned token,int aborted){if(token)guard_engine->end(token,aborted!=0);}
float vp_host_xmtrx[4][4]={{1,0,0,0},{0,1,0,0},{0,0,1,0},{0,0,0,1}};
namespace {
unsigned reg=0x105,tid=1,toggles=0,resets=0; bool ignore_toggle=false;
std::uint64_t ticks=0;
alignas(32) unsigned char local[kVertexBytes];
struct alignas(32) Packet { unsigned char before[32],tail[kReservedBytes],after[32]; } packet;
std::uintptr_t owner(){return tid;} unsigned ccr(){return reg;}
void toggle(bool v){++toggles;ticks+=7;if(!ignore_toggle)reg=v?reg|32U:reg&~32U;std::memset(local,0xa5,sizeof(local));}
std::uint64_t clock_us(){return ticks;}
void prime_reset(){++resets;}
Ops ops(){return {owner,ccr,toggle,clock_us,prime_reset,local,true};}
void fresh(){reg=0x105;tid=1;toggles=resets=0;ticks=0;ignore_toggle=false;std::memset(&packet,0xcd,sizeof(packet));}
void* take(Engine& e){void* p=nullptr;assert(e.acquire(packet.tail,p)==1);return p;}
void off_and_admission(){
    fresh();Engine e(ops());void* p=nullptr;
    assert(e.acquire(packet.tail,p)==0 && p==packet.tail);
    assert(!e.request(C,2,0x109));assert(!e.begin(0x109));assert(toggles==0);
    assert(!e.admit(0));reg|=32;assert(!e.admit(1));reg=0x105|128;assert(!e.admit(1));
    reg=0x105;assert(e.admit(1));assert(!e.request(3,1,0x109));assert(!e.request(C,0,0x109));
    assert(!e.request(C,601,0x109));assert(!e.request(C,1,0));
    Ops bad=ops();bad.layout=false;Engine a(bad);assert(!a.admit(1));
    bad=ops();bad.ocram=local+1;Engine b(bad);assert(!b.admit(1));
    tid=0;Engine c(ops());assert(!c.admit(1));assert(toggles==0);
}
void windows_and_requests(){
    fresh();Engine e(ops());assert(e.admit(1));assert(e.request(B,3,0x109));
    assert(toggles==0);assert(e.begin(0x109));assert(toggles==1 && reg==0x125);
    assert(take(e)==packet.tail);e.release();e.end(); // draw
    assert(e.stats().remaining==2 && toggles==1);
    assert(e.begin(0x109));e.end(); // skip: bounded even without any world borrow
    assert(e.stats().remaining==1 && toggles==1);
    assert(e.begin(0x109));assert(take(e)==packet.tail);e.release();e.end();
    assert(reg==0x105 && toggles==2 && e.stats().actual==A);
    assert(e.stats().frames==3 && e.stats().entries==1 && e.stats().exits==1);
    assert(e.stats().enter_us==7 && e.stats().exit_us==7);
    assert(e.request(C,8,0x109));assert(e.begin(0x109));assert(take(e)==local);
    assert(e.request(A,1,0x109));assert(toggles==3);e.release();e.end();assert(toggles==3);
    assert(e.begin(0x109));assert(toggles==4 && reg==0x105);assert(take(e)==packet.tail);e.release();e.end();
    assert(e.stats().remaining==0 && e.stats().actual==A);
}
void cancellation_and_lifetime(){
    fresh();Engine e(ops());assert(e.admit(1));assert(e.request(C,6,0x109));assert(e.begin(0x109));
    take(e);void* p=nullptr;assert(e.acquire(packet.tail,p)==-1); // nested borrower rejected
    e.cancel();assert(toggles==1); // movie / room / abort: cannot disable live records
    assert(e.acquire(packet.tail,p)==-1);e.release();assert(toggles==2 && reg==0x105);
    e.end();assert(toggles==2); // late end after cancel is harmless
    assert(e.request(B,5,0x109));assert(e.begin(0x109));e.end();
    assert(!e.begin(0x100));assert(reg==0x105 && toggles==4); // room changed between frames
    assert(e.request(C,5,0x109));assert(!e.begin(0x100));assert(toggles==4); // stale request
    assert(e.request(C,5,0x109));assert(e.begin(0x109));
    assert(!e.begin(0x109));assert(reg==0x105); // missing end / failed begin closes admission
    assert(e.request(C,1,0x109));assert(e.begin(0x109));take(e);e.end();assert(reg==0x125);
    e.release();assert(reg==0x105); // end with live borrower defers restore
}
void ownership_and_modes(){
    fresh();Engine e(ops());assert(e.admit(1));assert(e.request(C,3,0x109));assert(e.begin(0x109));take(e);
    tid=2;assert(!e.request(A,1,0x109));e.release();assert(toggles==1); // foreign release cannot unpin
    assert(!e.begin(0x109));assert(toggles==1);tid=1;e.release();assert(toggles==2 && reg==0x105);
    assert(e.request(B,2,0x109));assert(e.begin(0x109));e.end();tid=2;
    assert(!e.begin(0x109));assert(reg==0x125);tid=1;e.end();assert(reg==0x105);
    assert(e.request(C,2,0x109));assert(e.begin(0x109));e.end();reg|=128;
    const unsigned before=toggles;assert(!e.begin(0x109));assert(toggles==before); // never overwrite foreign CCR
    assert(e.stats().actual==3 && !e.request(B,1,0x109));
    reg=0x105;assert(e.admit(1));assert(e.request(A,1,0x109));assert(e.begin(0x109));reg|=128;e.end();assert(e.stats().actual==3);
    reg=0x105;assert(e.admit(1));assert(e.request(C,1,0x109));ignore_toggle=true;
    assert(!e.begin(0x109));assert(e.stats().actual==3); // failed hardware switch never lends OCRAM
}
void stale_guard_and_late_abort(){
    fresh();Engine e(ops());guard_engine=&e;assert(e.admit(1));assert(e.request(C,4,0x109));assert(e.begin(0x109));
    const unsigned old=e.token();e.cancel();assert(e.request(B,4,0x109));assert(e.begin(0x109));
    const unsigned current=e.token();assert(current!=old);e.end(old,true);
    assert(e.token()==current && e.stats().remaining==4 && reg==0x125);
    bool aborted=false;
    {Re4dcWorldScratchFrameEnd guard{&aborted};take(e);e.release();aborted=true;}
    assert(reg==0x105 && e.stats().actual==A && e.token()==0);
    {Re4dcWorldScratchFrameEnd guard{&aborted};} // token0 cannot cancel a future arm
    assert(e.request(C,1,0x109));assert(e.begin(0x109));
    {aborted=false;Re4dcWorldScratchFrameEnd guard{&aborted};}
    assert(reg==0x105 && e.stats().remaining==0);guard_engine=nullptr;
}
void exact_records(){
    // Use the actual portable transform/prime/indexed emit, including 256 entries,
    // all outcodes, canaries, flags/oargb and a repeated/reversed indexed strip.
    alignas(32) pvr_vertex_t expected[256],emitted[256],reference_emit[256];
    std::uint8_t expected_codes[256],indices[256];re4dc::vp::Vertex12 in[256];
    std::uint32_t lut[512];re4dc::vp::build_lut(lut);
    re4dc::vp::Constants k{.001f,.25f,.125f,1,.002f,.5f,.25f,1,.1f,50,0x00ffffff,0xff000000,lut,{}};k.finish();
    for(unsigned n=0;n<256;++n){in[n]={std::uint16_t(n*5),std::uint16_t(n*3),std::uint16_t(n),std::uint16_t(n*7),std::uint16_t(n*11),std::uint16_t(n*251)};indices[n]=std::uint8_t(255-(n*13)%256);}
    std::memset(expected,0xa5,sizeof(expected));re4dc::vp::prime(expected,256);
    re4dc::vp::transform_c<3>(in,256,expected,expected_codes,k);re4dc::vp::emit(reference_emit,expected,indices,256);
    for(unsigned arm=A;arm<=C;++arm){fresh();Engine e(ops());assert(e.admit(1));assert(e.request(arm,1,0x109));assert(e.begin(0x109));
        auto* cache=static_cast<pvr_vertex_t*>(take(e));auto* codes=packet.tail+kVertexBytes;
        re4dc::vp::prime(cache,256);re4dc::vp::transform_c<3>(in,256,cache,codes,k);
        assert(!std::memcmp(cache,expected,kVertexBytes));assert(!std::memcmp(codes,expected_codes,256));
        re4dc::vp::emit(emitted,cache,indices,256);assert(!std::memcmp(emitted,reference_emit,kVertexBytes));
        const auto a=re4dc::vp::codes(codes,indices,256),b=re4dc::vp::codes(expected_codes,indices,256);
        assert(a.all==b.all && a.any==b.any);
        for(auto x:packet.before)assert(x==0xcd);
        for(auto x:packet.after)assert(x==0xcd);
        if(arm==C)for(unsigned i=0;i<kVertexBytes;++i)assert(packet.tail[i]==0xcd);
        e.release();e.end();
        // A delayed presenter has copied words; retirement destroys the OCRAM
        // pool but cannot alter its retained TA packet. No pointer is enqueued.
        std::memset(local,0x77,kVertexBytes);assert(!std::memcmp(emitted,reference_emit,kVertexBytes));
    }
}
}
int main(){off_and_admission();windows_and_requests();cancellation_and_lifetime();ownership_and_modes();stale_guard_and_late_abort();exact_records();puts("PASS: admission, bounded A/B/C, draw/skip, owner/CCR, cancel and exact 8192+256-byte records");}
