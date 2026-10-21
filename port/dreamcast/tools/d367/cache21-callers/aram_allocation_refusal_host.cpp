// Actual MRAM allocation/command/wait/clear bodies; allocation and I/O boundaries.
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <initializer_list>
using u8=std::uint8_t;using u32=std::uint32_t;using s32=std::int32_t;
struct {int dev_mode{};} global,*pG=&global;
struct Logger {void err(int,int,const char*,...){std::abort();}} logger,*pLog=&logger;
static unsigned allocations,installs,frees,progress;
static bool refuse_alloc=true;
static void* allocation=reinterpret_cast<void*>(0x90010000);
static void* allocate(unsigned size,int flag,int heap){assert(size==4096&&flag==1&&heap==13);++allocations;return refuse_alloc?nullptr:allocation;}
#define MEM_ALLOC allocate
#define RE4DC_EVENT_FILE_FLAG 4
static void* Debug_alloc(unsigned size,int flag){return allocate(size,flag,13);}
static void Mem_free_h(void* p,int heap){assert(p==allocation&&(heap==4||heap==7));++frees;}
static void Debug_free_h(void* p,int heap){Mem_free_h(p,heap);}
static int MemGetCurrentHeap(){return 4;}static int MemGetCurrentDbgHeap(){return 7;}
static void OSReport(const char*,...){}
static void DCFlushRange(void*,u32){std::abort();}
static int DvdReadN(const char*,void*,u32,u32,u32,int,const char*,int){std::abort();}
static int re4dc_event_file_install(const char*,u32,void* dst){assert(dst==allocation);++installs;return 1;}
static int re4dc_aram_file_read(const char*,void*,u32){std::abort();}
static void re4dc_missing(const char*){std::abort();}
static int re4dc_cabin_carrier_install(const void*,void*){return 0;}
static int re4dc_cabin_carrier_mram_move(const void*,void*){return 0;}
static int re4dc_cabin_carrier_clear(const void*){return 1;}
static int re4dc_cabin_carrier_before_free(const void*){return 1;}
struct Controller {int dbgHeap{},m_nblock_read_stop{};void* m_DummyDataMem{};void setDummyId(int){std::abort();}} DC;
struct AramBoundary {int DmaTransReq(int,u32,u32,u32,int){std::abort();}void DmaCancel(int){std::abort();}} Aram;
struct DvdBoundary {void ReadCancel(int,int){std::abort();}void ReadCheck(int,void*,void*,void*){std::abort();}} Dvd;
#include "aram_actual_unit_decl.inc"
void cDataUnit::setLoadToAram(){std::abort();}int cDataUnit::setDelete(){std::abort();}
void cDataUnit::checkLoadToMram(){std::abort();}void cDataUnit::checkLoadToAram(){std::abort();}
void cDataUnit::checkAramToMram(){std::abort();}void cDataUnit::checkMramToAram(){std::abort();}
void cDataUnit::checkAramToAram(){std::abort();}void cDataUnit::checkMramToMram(){std::abort();}
#include "aram_actual_unit_methods.inc"
static cDataUnit prepared(bool debug){
    DC={};DC.dbgHeap=debug;allocations=installs=frees=progress=0;refuse_alloc=true;
    cDataUnit unit;std::memset(&unit,0,sizeof(unit));
    unit.m_condition=4;unit.m_be_flag=5;unit.m_addr=reinterpret_cast<void*>(0x400000);
    unit.dest=0x400000;unit.m_size=4096;unit.m_id=-1;
    std::strcpy(unit.m_name,"evd/synthetic.evd");
    return unit;
}
int main(){
    unsigned cases=0;
    for(bool debug:{false,true}){
        auto unit=prepared(debug);const auto before=unit;++cases;
        unit.setCommand(1,0,1);
        auto expected=before;expected.m_command=1;expected.m_err=1;expected.wait=1;expected.dest=0;
        assert(!std::memcmp(&unit,&expected,sizeof(unit))&&allocations==1&&!installs&&!frees);
        assert(!unit.waitUseOk());expected.m_wait=1;
        assert(!std::memcmp(&unit,&expected,sizeof(unit))&&allocations==2&&!installs&&!frees);
        // Existing source cleanup erases the still-valid logical source identity.
        assert(unit.setClear());expected.m_command=0;expected.m_addr=nullptr;expected.dest=0;
        expected.m_condition=0;expected.m_be_flag=1;
        assert(!std::memcmp(&unit,&expected,sizeof(unit))&&!frees&&!installs);
        // A retained source can load on a retry, but its old error remains stale
        // unless this attempt's deltas are explicitly retired/restored.
        unit=prepared(debug);++cases;unit.setCommand(1,0,1);assert(!unit.waitUseOk());
        refuse_alloc=false;unit.setCommand(1,0,1);assert(unit.waitUseOk());
        assert(unit.m_condition==2&&unit.m_addr==allocation&&unit.m_err==1&&installs==1&&allocations==3);
        assert(unit.setClear()&&frees==1);
        // Positive first-load control goes through actual allocation metadata.
        unit=prepared(debug);++cases;refuse_alloc=false;unit.setCommand(1,0,1);
        assert(unit.waitUseOk()&&unit.m_err==0&&unit.m_addr==allocation&&unit.m_malloc_addr==allocation);
        assert(unit.m_malloc_heap==(debug?7:4)&&allocations==1&&installs==1&&!frees);
        assert(unit.setClear()&&frees==1);
        // Existing owned MRAM is an explicit exclusion for a narrow prior-ARAM
        // refusal repair, even when the current logical condition is four.
        unit=prepared(debug);++cases;unit.m_be_flag|=2;unit.m_malloc_addr=allocation;unit.m_malloc_heap=debug?7:4;
        const auto owned=unit;unit.setCommand(1,0,1);assert(!unit.waitUseOk());
        assert(unit.m_malloc_addr==owned.m_malloc_addr&&unit.m_be_flag==owned.m_be_flag&&!frees);
    }
    std::printf("ARAM_ALLOCATION_REFUSAL_CASES=%u cabin=%d PASS\n",cases,RE4DC_CABIN_SOURCE);
}
