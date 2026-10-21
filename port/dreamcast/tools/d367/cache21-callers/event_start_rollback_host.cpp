// Actual caller, manager-create and data-unit release bodies; host boundaries below.
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <sys/mman.h>
using u8 = std::uint8_t; using u32 = std::uint32_t; using s32 = std::int32_t;
struct EvtHeader;
struct Event {
    u32 be_flag{}, StatusFlag{}; char Name[32]{};
    EvtHeader* pData{};
    int isAlive() { return (be_flag & 0x201) == 1; }
    int init(char*, EvtHeader*);
};
struct Global { u32 Stop_flg{}, Debug_flg[4]{}, Status_flg[4]{}, System_flg{}; int dev_mode{}; } global, *pG = &global;
static unsigned init_calls, pool_logs, release_calls, debug_release_calls, sleep_calls, read_calls;
static bool retire_on_sleep;
static void* released;
static unsigned char* arena;
static bool debug_transport;
static std::vector<void*> debug_frees;
static void host_before_clear(void*, unsigned) {}
static void Debug_free(void* p) { debug_frees.push_back(p); }
static void Mem_free(void*) { std::abort(); }
#if defined(RE4DC_ARAM_ACTUAL)
static void* aram_actual_alloc(unsigned,int,int);
static void aram_actual_free_boundary(void*,int);
static void* host_table_alloc(unsigned bytes,int flag,int heap){return aram_actual_alloc(bytes,flag,heap);}
#else
static void* host_table_alloc(unsigned, int, int) { std::abort(); }
#endif
#define MEM_ALLOC host_table_alloc
#define RE4DC_EVENT_FILE_FLAG 4
#define CMND_CLEAR_DATA 3
#define CMND_MRAM_LOAD 1
#define CMND_ARAM_LOAD 2
#define BitOn(v, bits) ((v) |= (bits))
#define BitOff(v, bits) ((v) &= ~(bits))
#define EvtChk(value, bits) (((value) & (bits)) != 0)
static void OSReport(const char*, ...) {}
static void retire_prior_event();
static void SceSleep(int) { ++sleep_calls; if (retire_on_sleep) retire_prior_event(); }
static int SceCheckEventStart() { return 1; }
static unsigned camera_calls;
struct Camera { void Comeback(int) { ++camera_calls; } void LowerBinocular() {} } CamCtrl;
#if defined(RE4DC_EXEC_REAL_SCENARIO)
#include "exec_scenario_boundary.inc"
#else
static void SceEventStart(int) {}
static void SceEventEnd(int) {}
#endif
static void FadeSetW(u32, int, int, int) {}
class cDataUnit;
struct Controller { int m_nblock_read_stop{}, dbgHeap{}; cDataUnit* m_DataUnit{};void* m_DummyDataMem{};void setDummyId(int){std::abort();}cDataUnit* setData(char*);cDataUnit* getNewUnit(); } DC;
struct AramBoundary { void DmaCancel(int) { std::abort(); } int DmaTransReq(int,u32,u32,u32,int){std::abort();} } Aram;
struct DvdBoundary {
#if defined(RE4DC_READ_ADMISSION_CHARACTERIZE)
    int FileExistCheck(char*,u32* bytes){*bytes=27456;return 0;}
#endif
    void ReadCancel(int, int) { std::abort(); }
    void ReadCheck(int, void*, void*, void*) { std::abort(); }
} Dvd;
static void Mem_free_h(void* p, int heap) {
#if defined(RE4DC_ARAM_ACTUAL)
    aram_actual_free_boundary(p,heap);
#endif
    assert(heap == 4); ++release_calls; released = p;
    assert(mprotect(p, 4096, PROT_NONE) == 0);
}
static void Debug_free_h(void* p, int heap) { ++debug_release_calls; Mem_free_h(p, heap); }
#include "caller_dataunit_types.inc"
#if defined(RE4DC_ARAM_ACTUAL)
static cDataUnit actual_units[32];
#define loaded actual_units[0]
#else
static cDataUnit loaded;
#endif
#if defined(RE4DC_EXEC_REAL_TRANSPORT)
#include "exec_transport_boundary.inc"
#include "exec_cabin_boundary.inc"
#else
void cDataUnit::setLoadToMram() { std::abort(); }
#endif
void cDataUnit::setLoadToAram() { std::abort(); }
#if !defined(RE4DC_READ_ADMISSION_CHARACTERIZE)
int cDataUnit::setDelete() { std::abort(); }
#endif
#if defined(RE4DC_ARAM_ACTUAL)
// The actual checkCondition body is exported into caller_dataunit_methods.inc.
#elif defined(RE4DC_EXEC_REAL_TRANSPORT)
void cDataUnit::checkCondition() {} // External transport progress; injected m_err is checked by actual wait.
#else
void cDataUnit::checkCondition() { std::abort(); }
#endif
#if defined(RE4DC_READ_ADMISSION_CHARACTERIZE)
#define pLog (&admission_logger)
#elif defined(RE4DC_ARAM_ACTUAL)
struct AramDataLogger{void err(int,int,const char*,...){std::abort();}} aram_data_logger;
#define pLog (&aram_data_logger)
#endif
#include "caller_dataunit_methods.inc"
#if defined(RE4DC_ARAM_ACTUAL) || defined(RE4DC_READ_ADMISSION_CHARACTERIZE)
#undef pLog
#endif
struct ReadModule { void* pArc; u32 size; };
#if defined(RE4DC_EXEC_REAL_TRANSPORT)
static ReadModule exchange_module;
static unsigned swap_pushes,swap_pops,swap_calls;
#if defined(RE4DC_READ_ADMISSION_CHARACTERIZE)
static bool module_missing,swap_refuse;
static ReadModule* SearchEmModule(int em){assert(em==1);return module_missing?nullptr:&exchange_module;}
#else
static ReadModule* SearchEmModule(int em){assert(em==1);return &exchange_module;}
#endif
static void MemorySwap(void* dst,u32 src,u32 bytes){
#if defined(RE4DC_READ_ADMISSION_CHARACTERIZE)
    if(swap_refuse){++swap_calls;return;}
#endif
    ++swap_calls;auto*source=reinterpret_cast<u8*>(std::uintptr_t(src));auto*target=static_cast<u8*>(dst);
    for(u32 i=0;i<bytes;++i)std::swap(source[i],target[i]);
}
static void EspEmDataSwapPop(int em){assert(em==1);++swap_pops;}
static void EspEmDataSwapPush(int em){assert(em==1);++swap_pushes;}
static void* EmReadSearch(int em,void*,u32){return SearchEmModule(em)->pArc;}
#else
static ReadModule* SearchEmModule(int) { std::abort(); }
static void MemorySwap(void*, u32, u32) { std::abort(); }
static void EspEmDataSwapPop(int) { std::abort(); }
static void EspEmDataSwapPush(int) { std::abort(); }
static void* EmReadSearch(int,void*,u32){std::abort();}
#endif
static int HDReadDebugAlloc(char*, void**, int);

// The actual create/full decision uses a projected pool. Allocation, constructor
// and list attachment are explicit boundaries, never reached by full-pool cases.
template <class T> struct cManager {
    T* pArray{}; u32 nArray{}, size{sizeof(T)}, maxAlive{}, warnDiv{8}; const char* name{"fixture"};
    T* workAt(u32 no) { return reinterpret_cast<T*>(reinterpret_cast<u8*>(pArray) + size * no); }
    bool prepareWork(u32 no, u32 count) { return no < nArray && count <= nArray - no; }
    void memClear(T* p, u32 n) { std::memset(p, 0, n); }
    int construct(T* p, u32) { p->be_flag = 1; return 1; }
    void addListFront(T*) {}
    void log(const char*, ...) { ++pool_logs; }
    T* create(int); u32 countActiveWork();
};
#include "caller_manager_methods.inc"
static cManager<Event> event_pool;
#define main h064_original_main
#include "h064_event_caller_adapted.cpp"
#undef main

EventMgr EvtMgr{};
#if defined(RE4DC_EXEC_REAL_TRANSPORT)
static void exec_create_boundary();
#endif
Event* EventMgr::create(int id) {
#if defined(RE4DC_EXEC_REAL_TRANSPORT)
    exec_create_boundary();
#endif
    return event_pool.create(id);
}
void EventMgr::destroyNow(Event*) { std::abort(); } // init succeeds in this focused create/full suite.
int EventMgr::DelEvt(void*, int) { std::abort(); }
int Event::init(char* name, EvtHeader* data) { ++init_calls; std::strcpy(Name, name); pData=data; return 1; }
int EventMgr::GetRead(void** out, int* slot, char* name) {
    // ABI adapter: recovered GetRead stores a pointer through a 32-bit int local.
    // The actual table lookup/slot identity is retained with host-width storage.
    u8 type = 0;
    return ReadTbl.GetDat(out, &type, name, nullptr) && ReadTbl.GetWkNo(slot, name);
}
#if !defined(RE4DC_EXEC_REAL_TRANSPORT)
int EventMgr::EvtReadMram(char*, int em, int* out, int, u32) {
    assert(em == 0); ++read_calls; *out = static_cast<int>(reinterpret_cast<std::uintptr_t>(loaded.m_addr)); return 1;
}
#endif
static int HDReadDebugAlloc(char*, void** out, int) {
    assert(debug_transport); ++read_calls; *out = arena; return 1;
}

static std::array<DatTblEntry, 32> parents;
static std::array<DatTblEntry, 320> bins;
static std::array<DatTblEntry, 8> reads;
static Event pool[2];
static void retire_prior_event() { pool[1].be_flag = 0; retire_on_sleep = false; }
static char file_name[] = "event/evd/synthetic.evd";
static char header_name[] = "event";
static void setup() {
    assert(mprotect(arena, 0x20000, PROT_READ | PROT_WRITE) == 0);
    event_at(arena); event_at(arena + 0x10000);
    parents = {}; bins = {}; reads = {}; EvtMgr = {}; global = {}; loaded = {};
    EvtMgr.EvdTbl = {32, parents.data()}; EvtMgr.BinTbl = {320, bins.data()}; EvtMgr.ReadTbl = {8, reads.data()};
    for (unsigned i = 0; i < 2; ++i) {
        pool[i] = {}; pool[i].be_flag = 1; std::snprintf(pool[i].Name, sizeof(pool[i].Name), "occupied%u", i);
    }
    event_pool = {}; event_pool.pArray = pool; event_pool.nArray = 2;
    EvtMgr.pArray = pool; EvtMgr.nArray = 2; EvtMgr.size = sizeof(Event);
    std::memset(EvtMgr.NowExeEvtName, 0, sizeof(EvtMgr.NowExeEvtName));
    init_calls = pool_logs = release_calls = debug_release_calls = sleep_calls = read_calls = errors = 0;
    released = nullptr; debug_transport = false; debug_frees.clear(); DC = {};
    retire_on_sleep = false;
    loaded.m_addr = loaded.m_malloc_addr = arena; loaded.m_size = 4096;
    loaded.m_malloc_heap = 4; loaded.m_be_flag = 3; loaded.m_condition = 2;
    std::strcpy(loaded.m_name, file_name);
    assert(EvtMgr.ReadTbl.SetDat(file_name, &loaded, 0, nullptr, 2, nullptr) == 1);
}
static void verify_registered(void* owner) {
    void* out = nullptr;
    assert(EvtMgr.EvdTbl.ChkDat(header_name));
    assert(EvtMgr.GetEvd(&out, header_name, 1) == 1 && out == owner);
    assert(EvtMgr.BinTbl.ChkDat("first.bin") && EvtMgr.BinTbl.ChkDat("second.bin"));
    assert(parents[0].Count == 1 && bins[0].Count == 1 && bins[1].Count == 1);
}
static void verify_failed_admission() {
#if RE4DC_EVD_START_ROLLBACK
    assert(!EvtMgr.EvdTbl.ChkDat(header_name));
    assert(!EvtMgr.BinTbl.ChkDat("first.bin") && !EvtMgr.BinTbl.ChkDat("second.bin"));
#else
    verify_registered(arena);
#endif
}
static void verify_debug_failure_free() {
    assert(debug_frees.size()==unsigned(RE4DC_EVD_DEBUG_READ_CLEANUP));
    if(!debug_frees.empty())assert(debug_frees[0]==arena);
}

#if defined(RE4DC_EXEC_REAL_TRANSPORT)
int rollback_previous_main() {
#else
int main() {
#endif
    std::cout << std::unitbuf;
    arena = static_cast<unsigned char*>(mmap(reinterpret_cast<void*>(0x90000000), 0x20000,
        PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0));
    assert(arena == reinterpret_cast<void*>(0x90000000));
    unsigned cases = 0;
    for (u32 flags : {0U, 4U, 0x10U, 0x80U, 0x100U, 0x200U, 2U, 0x40U}) {
        setup(); ++cases;
        assert(EvtMgr.EvtReadExec(file_name, 0, flags) == 1); // False success is actual behavior.
        assert(pool_logs == 1 && init_calls == 0 && read_calls == 1 && errors == 2);
        verify_failed_admission();
        if (flags & (2 | 0x40)) {
            assert(!release_calls && loaded.m_addr == arena && EvtMgr.ReadTbl.ChkDat(file_name));
            assert(global.System_flg & 0x400);
        } else {
            assert(release_calls == 1 && released == arena && !loaded.m_addr && loaded.m_condition == 0);
            assert(!EvtMgr.ReadTbl.ChkDat(file_name) && !(global.System_flg & 0x400));
            // Actual release sent the allocation to Mem_free_h and the host free
            // boundary protected it; GetEvd still advertised that exact address.
        }
    }
    std::cout << "actual failed-create rollback tested for eight outer flag cases; outer false-success/keep-read defect remains characterized PASS\n";
    setup(); ++cases;
    std::strcpy(EvtMgr.NowExeEvtName, "occupied1"); retire_on_sleep = true;
    assert(EvtMgr.EvtReadExec(file_name, 0, 0) == 1 && sleep_calls == 1 && release_calls == 1 && !init_calls);
    verify_failed_admission();
    std::cout << "existing running-event key still waits for prior completion after failed start; rollback state checked before outer release PASS\n";
    setup(); ++cases;
    assert(EvtMgr.SetEvd(header_name, arena + 0x10000, nullptr, 2) == 1);
    assert(EvtMgr.EvtReadExec(file_name, 0, 0) == 1 && release_calls == 1);
    verify_registered(arena + 0x10000); // A repair must not delete this prior owner.
    std::cout << "pre-existing complete parent survives failed create/other input release PASS\n";
    setup(); ++cases;
    assert(EvtMgr.SetEvt(arena, static_cast<u32*>(nullptr)) == 0);
    verify_failed_admission(); assert(!release_calls && !init_calls);
    pool[1].be_flag = 0;
    assert(EvtMgr.SetEvt(arena, static_cast<u32*>(nullptr)) == 1);
    assert(init_calls == 1 && parents[0].Count == 1 && bins[0].Count == 1);
    std::cout << "direct failed-create then free-slot retry, actual complete admission and constructor boundary PASS\n";
    setup(); ++cases;
    assert(EvtMgr.SetEvd(header_name, arena, nullptr, 2));
    const auto exact_parents = parents; const auto exact_bins = bins;
    assert(!EvtMgr.SetEvt(arena, static_cast<u32*>(nullptr)));
    assert(!std::memcmp(parents.data(), exact_parents.data(), sizeof(parents)));
    assert(!std::memcmp(bins.data(), exact_bins.data(), sizeof(bins)));
    std::cout << "pre-existing exact same-input owner preserved byte-for-byte on failed create PASS\n";
    for (int permanent : {0, 1}) {
        setup(); ++cases;
        assert(EvtMgr.SetBin(const_cast<char*>("first.bin"), arena + 0x11000, arena + 0x11000, permanent ? 0 : 2));
        assert(EvtMgr.SetBin(const_cast<char*>("first.bin"), arena + 0x11000, nullptr, 2));
        const auto before = bins;
        assert(!EvtMgr.SetEvt(arena, static_cast<u32*>(nullptr)));
#if RE4DC_EVD_START_ROLLBACK
        assert(!std::memcmp(bins.data(), before.data(), sizeof(bins)));
        assert(!EvtMgr.EvdTbl.ChkDat(header_name));
        assert(debug_frees.empty());
#else
        assert(bins[0].Count == 3 && EvtMgr.EvdTbl.ChkDat(header_name));
#endif
    }
    std::cout << "shared temporary/permanent bin owner and reference count preserved exactly by rollback PASS\n";
    setup(); ++cases; debug_transport = true; EvtMgr.BinTbl.NumDatTbl = 0;
    void* out = nullptr;
    assert(EvtMgr.GetEvd(&out, header_name, 0) == 0 && !out && read_calls == 1);
    verify_debug_failure_free();
#if RE4DC_EVD_ADMISSION_TXN
    assert(!EvtMgr.EvdTbl.ChkDat(header_name)); // No owner took the debug input.
#else
    assert(EvtMgr.EvdTbl.ChkDat(header_name) && parents[0].dat2 == arena);
#endif
    setup(); ++cases; debug_transport=true;EvtMgr.EvdTbl.NumDatTbl=0;
    assert(!EvtMgr.GetEvd(&out,header_name,0)&&!out&&read_calls==1);
    verify_debug_failure_free();
    assert(!EvtMgr.BinTbl.ChkDat("first.bin")&&!EvtMgr.BinTbl.ChkDat("second.bin"));
    setup(); ++cases; debug_transport=true;EvtMgr.BinTbl.NumDatTbl=0;
    assert(!EvtMgr.GetBin(&out,"fresh.bin",0)&&!out&&read_calls==1);
    verify_debug_failure_free();
    setup(); ++cases; debug_transport=true;
    assert(EvtMgr.GetEvd(&out,header_name,0)&&out==arena&&read_calls==1&&debug_frees.empty());
    assert(EvtMgr.DelEvd(header_name)&&debug_frees.size()==1&&debug_frees[0]==arena);
    setup(); ++cases; debug_transport=true;
    assert(EvtMgr.GetBin(&out,"fresh.bin",0)&&out==arena&&read_calls==1&&debug_frees.empty());
    assert(EvtMgr.GetBin(&out,"fresh.bin",0)&&out==arena&&read_calls==1&&debug_frees.empty());
    assert(EvtMgr.DelBin(const_cast<char*>("fresh.bin"))&&debug_frees.size()==1&&debug_frees[0]==arena);
    std::cout << "actual tool fresh debug-input failures and successful ownership transfer/final release verified PASS\n";
    setup();++cases;
    assert(EvtMgr.ReadTbl.SetDat(file_name,&loaded,0,nullptr,2,nullptr));
    const auto shared_reads=reads;const auto shared_unit=loaded;const auto shared_em=EvtMgr.readEm[0];
    assert(EvtMgr.EvtFree(file_name)&&reads[0].Count==1);
#if defined(RE4DC_EVD_READ_RELEASE_REFS) && RE4DC_EVD_READ_RELEASE_REFS
    assert(!release_calls&&!std::memcmp(&loaded,&shared_unit,sizeof(loaded)));
    assert(!std::memcmp(&EvtMgr.readEm[0],&shared_em,sizeof(shared_em)));
    auto expected_reads=shared_reads;expected_reads[0].Count--;
    assert(!std::memcmp(reads.data(),expected_reads.data(),sizeof(reads)));
    assert(EvtMgr.EvtFree(file_name)&&release_calls==1&&!EvtMgr.ReadTbl.ChkDat(file_name));
#else
    assert(release_calls==1&&!loaded.m_addr&&EvtMgr.ReadTbl.ChkDat(file_name));
#endif
    std::cout << "actual multiple-registration EvtFree source control verified; final-reader contract remains separate PASS\n";
#if defined(RE4DC_EVD_READ_RELEASE_REFS) && RE4DC_EVD_READ_RELEASE_REFS
    setup();++cases;reads[0].Count=2;EvtMgr.readEm[0]={0x20,1,{0x12,0x34}};
    const auto module_unit=loaded;const auto module_em=EvtMgr.readEm[0];
    assert(EvtMgr.EvtFree(file_name)&&!release_calls&&reads[0].Count==1);
    assert(!std::memcmp(&loaded,&module_unit,sizeof(loaded))&&!std::memcmp(&EvtMgr.readEm[0],&module_em,sizeof(module_em)));
#endif
    for(unsigned malformed=0;malformed<4;++malformed){
        setup();++cases;reads[0].Count=2;
        if(malformed==0)reads[0].Etc=1;
        if(malformed==1)reads[0].FlagBe8=1;
        if(malformed==2)reads[0].Count=0;
        if(malformed==3)reads[0].Count=0x8001;
        assert(EvtMgr.EvtFree(file_name)&&release_calls==1&&!loaded.m_addr);
    }
    std::cout << "exact registration row eligibility and non-final module metadata preservation verified PASS\n";
    std::cout << "EVENT_START_ROLLBACK_CASES=" << cases << " rollback=" << RE4DC_EVD_START_ROLLBACK << " PASS\n";
    assert(mprotect(arena, 0x20000, PROT_READ | PROT_WRITE) == 0); munmap(arena, 0x20000);
}
