// Actual registration/release/lookup/Push/Pop/MemorySwap bodies are generated.
// Synthetic EFF archives and software ARAM are explicit service boundaries.
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <sys/mman.h>
using u8=std::uint8_t;using u16=std::uint16_t;using u32=std::uint32_t;
struct TEXPalette{};struct EspAnmData{};struct EspSeqData;
#include "effect_types.inc"
struct cEspSystem{u32 ownerCnt[0xd3];SstTbl estTbl[0xd3];} system_work,*g_pEspSys=&system_work;
struct Global{u32 Debug_flg[4];}global,*pG=&global;
static unsigned errors,warnings,registrations[5],releases[5],load_calls;
struct Logger{void err(int,int,const char*,...){++errors;}}logger,*pLog=&logger;
#define OWNER_ERR(owner,a,b) (++errors)
#define OWNER_ERR2(owner,a,b,arg) (++errors)
#define OWNER_WARN2(owner,a,b,arg) (++warnings)
#define EFF_OWNER_MAX 0xd3
static int espTexRegist(TEXPalette*,EspAnmData*,u8,u32){std::abort();}
static int efmRegist(void*,void*,void*,void*,u8,u32){std::abort();}
static int sstRegist(void*,void*,u32){++registrations[2];return 1;}
static int pathRegist(void*,void*,u32){++registrations[3];return 1;}
static int espTexRelease(u32){++releases[0];return 1;}
static int sstRelease(u32){++releases[2];return 1;}
static int pathRelease(u32){++releases[3];return 1;}
static int efmRelease(u32){++releases[4];return 1;}
int estRegist(void*,void*,u32);int estRelease(u32);
#include "effect_actual_methods.inc"
struct EmModule{void*pArc;};static EmModule current_module;
static bool module_present=true,eff_present=true;
static EmModule*SearchEmModule(int){return module_present?&current_module:nullptr;}
static void*GetDataExt(void*arc,const char*tag,int no){assert(!std::strcmp(tag,"EFF")&&!no);return eff_present?arc:nullptr;}
static void EspDataLoad(void*data,int owner,int flag){++load_calls;actual_EspDataLoad(u32(std::uintptr_t(data)),owner,flag);}
#include "effect_actual_swap_methods.inc"
static u8*arena;static u8*swap_save;static u8*swap_read;static u8*aram_bytes;
struct Queue{int chk(int){std::abort();}void Read(){std::abort();}};
struct DvdBoundary{Queue*pCur_queue;}Dvd;
struct AramBoundary{int DmaTransReq(int type,u32 src,u32 dst,u32 bytes,int wait){
    assert(wait==1);if(type==1){assert(src==0x1000);std::memcpy(reinterpret_cast<void*>(std::uintptr_t(dst)),aram_bytes,bytes);}
    else{assert(type==0&&dst==0x1000);std::memcpy(aram_bytes,reinterpret_cast<void*>(std::uintptr_t(src)),bytes);}return 1;
}}Aram;
static void OSReport(const char*,...){}
static void DCFlushRange(void*,u32){}
static int re4dc_event_file_range(u32,u32){return 0;}
static void re4dc_event_file_reject_swap(){std::abort();}
#define ALIGN32(n) (((n)+31U)&~31U)
#define DVD_BUFF swap_save
#define DVD_BUFF2 swap_read
#include "effect_actual_memoryswap.inc"
static void reset(){
    system_work={};global={};for(auto&t:system_work.estTbl)t.owner=0xd2;
    errors=warnings=load_calls=0;std::memset(registrations,0,sizeof(registrations));std::memset(releases,0,sizeof(releases));
    module_present=eff_present=true;current_module.pArc=arena;
}
static void seed(u8*base,u32 marker=0x11223344){
    std::memset(base,0,0x1000);auto*d=reinterpret_cast<EffData*>(base);d->version=0xb;
    d->ofsTexId=0x80;d->ofsEfmId=0xa0;d->ofsTpl=0xc0;d->ofsAnm=0xe0;
    d->ofsEstList=0x100;d->ofsEstData=0x180;d->ofsSstList=d->ofsPathList=0x200;d->ofsSstData=d->ofsPathData=0x240;d->ofsEfm=0x280;
    auto*l=reinterpret_cast<SstList*>(base+0x100);l->num=1;l->ent[0].no=7;
    auto*t=reinterpret_cast<SstData*>(base+0x180);t->Num=1;t->ofs[0]=0x20;
    std::memcpy(base+0x1a0,&marker,4);
}
static u32 marker(void*p){assert(p);u32 n;std::memcpy(&n,p,4);return n;}
int main(){
    arena=static_cast<u8*>(mmap(reinterpret_cast<void*>(0x90000000),0x80000,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0));
    assert(arena==reinterpret_cast<void*>(0x90000000));swap_save=arena+0x20000;swap_read=arena+0x30000;aram_bytes=arena+0x40000;
    unsigned cases=0;
    for(bool first_inside:{false,true})for(unsigned refs:{1U,2U,200U}){
        reset();seed(arena);seed(arena+0x10000,0x55667788);seed(aram_bytes,0xdeadbeef);
        u8*registered=first_inside?arena:arena+0x10000;
        assert(actual_EspDataLoad(u32(std::uintptr_t(registered)),0x10,0)==1);
        for(unsigned i=1;i<refs;++i)assert(actual_EspDataLoad(u32(std::uintptr_t(arena)),0x10,0)==1);
        assert(system_work.ownerCnt[0x10]==refs);
        auto*before=EspGetEstAddr(0x10,7,1);assert(before==reinterpret_cast<EspSeqData*>(registered+0x1a0));
        const u32 original=marker(before);
        EspEmDataSwapPush(0x13);assert(system_work.ownerCnt[0x10]==refs-1);
        MemorySwap(arena,0x1000,0x1000);
        auto*after=EspGetEstAddr(0x10,7,1);
        if(refs==1){assert(!after&&system_work.estTbl[0x10].owner==0xd2);}
        else{assert(after==before);assert(marker(after)==(first_inside?0xdeadbeefU:original));}
        // A reverse exchange plus actual Pop re-registers on final release,
        // or increments the retained registration after a non-final release.
        MemorySwap(arena,0x1000,0x1000);EspEmDataSwapPop(0x13);
        assert(system_work.ownerCnt[0x10]==refs);
        auto*restored=EspGetEstAddr(0x10,7,1);
        assert(restored==(refs==1?reinterpret_cast<EspSeqData*>(arena+0x1a0):before));
        assert(marker(restored)==(refs==1?0x11223344U:original));
        assert(!errors);++cases;
        std::cout<<"EFFECT_ARCHIVE first_inside="<<first_inside<<" refs="<<refs<<" live_after_swap="<<(refs>1)<<" PASS\n";
    }
    reset();seed(arena);auto*d=reinterpret_cast<EffData*>(arena);d->version=0xa;
    assert(actual_EspDataLoad(u32(std::uintptr_t(arena)),0x10,0)==0);
    assert(system_work.ownerCnt[0x10]==(RE4DC_EFFECT_ADMISSION_GUARD?0U:1U)&&system_work.estTbl[0x10].owner==0xd2&&errors==1);
    d->version=0xb;
    assert(actual_EspDataLoad(u32(std::uintptr_t(arena)),0x10,0)==1);
    assert(system_work.ownerCnt[0x10]==(RE4DC_EFFECT_ADMISSION_GUARD?1U:2U));
    assert(bool(EspGetEstAddr(0x10,7,1))==bool(RE4DC_EFFECT_ADMISSION_GUARD));++cases;
    std::cout<<"EFFECT_INVALID_VERSION source_control_corrected_retry PASS\n";
    for(unsigned refs:{1U,2U,200U}){
        reset();seed(arena);
        for(unsigned i=0;i<refs;++i)assert(actual_EspDataLoad(u32(std::uintptr_t(arena)),0x10,0)==1);
        auto*before=EspGetEstAddr(0x10,7,1);reinterpret_cast<EffData*>(arena)->version=0xa;
        assert(actual_EspDataLoad(u32(std::uintptr_t(arena)),0x10,0)==1);
        assert(system_work.ownerCnt[0x10]==(refs<200?refs+1:200));
        assert(EspGetEstAddr(0x10,7,1)==before&&!errors);++cases;
        // Existing explicit duplicate-error behavior is outside this repair:
        // a valid repeated flag1 call still acquires a count before returning0.
        reset();seed(arena);
        for(unsigned i=0;i<refs;++i)assert(actual_EspDataLoad(u32(std::uintptr_t(arena)),0x10,0)==1);
        before=EspGetEstAddr(0x10,7,1);assert(actual_EspDataLoad(u32(std::uintptr_t(arena)),0x10,1)==0);
        assert(system_work.ownerCnt[0x10]==(refs<200?refs+1:200)&&EspGetEstAddr(0x10,7,1)==before&&errors==1);++cases;
    }
    reset();seed(arena);assert(actual_EspDataLoad(u32(std::uintptr_t(arena)),0x10,0)==1);EspEmDataSwapPush(0x13);
    eff_present=false;EspEmDataSwapPop(0x13);
    assert(!system_work.ownerCnt[0x10]&&!load_calls&&!EspGetEstAddr(0x10,7,1)&&errors==1);++cases;
    std::cout<<"EFFECT_POP_MISSING_EFF void_failure_keeps_owner_unregistered PASS\n";
    reset();seed(arena);assert(actual_EspDataLoad(u32(std::uintptr_t(arena)),0x10,0)==1);EspEmDataSwapPush(0x13);
    reinterpret_cast<EffData*>(arena)->version=0xa;EspEmDataSwapPop(0x13);
    assert(system_work.ownerCnt[0x10]==(RE4DC_EFFECT_ADMISSION_GUARD?0U:1U)&&load_calls==1&&!EspGetEstAddr(0x10,7,1)&&errors==1);++cases;
    std::cout<<"EFFECT_POP_INVALID_VERSION void_failure_count_control PASS\n";
    reset();assert(actual_EspDataLoad(0,0x10,0)==0&&!system_work.ownerCnt[0x10]);++cases;
    std::cout<<"EFFECT_NULL_DATA preserves_zero_count PASS\n";
    std::cout<<"EFFECT_LIFETIME_CHARACTERIZATION_CASES="<<cases<<" enabled="<<RE4DC_EFFECT_ADMISSION_GUARD<<" PASS\n";
    munmap(arena,0x80000);
}
