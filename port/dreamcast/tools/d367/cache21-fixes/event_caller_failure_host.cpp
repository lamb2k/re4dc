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
    int isAlive() { return (be_flag & 0x201) == 1; }
    int init(char*, EvtHeader*);
};
struct Global { u32 Stop_flg{}, Debug_flg[4]{}, Status_flg[3]{}, System_flg{}; } global, *pG = &global;
static unsigned init_calls, pool_logs, release_calls, debug_release_calls, sleep_calls, read_calls;
static bool retire_on_sleep;
static void* released;
static unsigned char* arena;
static bool debug_transport;
static std::vector<void*> debug_frees;
static void host_before_clear(void*, unsigned) {}
static void Debug_free(void* p) { debug_frees.push_back(p); }
static void Mem_free(void*) { std::abort(); }
static void* host_table_alloc(unsigned, int, int) { std::abort(); }
#define MEM_ALLOC host_table_alloc
#define RE4DC_EVENT_FILE_FLAG 4
#define CMND_CLEAR_DATA 3
#define BitOn(v, bits) ((v) |= (bits))
#define BitOff(v, bits) ((v) &= ~(bits))
#define EvtChk(value, bits) (((value) & (bits)) != 0)
static void OSReport(const char*, ...) {}
static void retire_prior_event();
static void SceSleep(int) { ++sleep_calls; if (retire_on_sleep) retire_prior_event(); }
static int SceCheckEventStart() { return 1; }
static void SceEventStart(int) {}
static void SceEventEnd(int) {}
static void FadeSetW(u32, int, int, int) {}
struct Camera { void Comeback(int) {} } CamCtrl;
struct Controller { int m_nblock_read_stop{}, dbgHeap{}; } DC;
struct AramBoundary { void DmaCancel(int) { std::abort(); } } Aram;
struct DvdBoundary {
    void ReadCancel(int, int) { std::abort(); }
    void ReadCheck(int, void*, void*, void*) { std::abort(); }
} Dvd;
static void Mem_free_h(void* p, int heap) {
    assert(heap == 4); ++release_calls; released = p;
    assert(mprotect(p, 4096, PROT_NONE) == 0);
}
static void Debug_free_h(void* p, int heap) { ++debug_release_calls; Mem_free_h(p, heap); }
#include "caller_dataunit_types.inc"
static cDataUnit loaded;
void cDataUnit::setLoadToMram() { std::abort(); }
void cDataUnit::setLoadToAram() { std::abort(); }
int cDataUnit::setDelete() { std::abort(); }
void cDataUnit::checkCondition() { std::abort(); }
#include "caller_dataunit_methods.inc"
struct ReadModule { void* pArc; };
static ReadModule* SearchEmModule(int) { std::abort(); }
static void MemorySwap(void*, u32, u32) { std::abort(); }
static void EspEmDataSwapPop(int) { std::abort(); }
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
Event* EventMgr::create(int id) { return event_pool.create(id); }
int EventMgr::DelEvt(void*, int) { std::abort(); }
int Event::init(char* name, EvtHeader*) { ++init_calls; std::strcpy(Name, name); return 1; }
int EventMgr::GetRead(void** out, int* slot, char* name) {
    // ABI adapter: recovered GetRead stores a pointer through a 32-bit int local.
    // The actual table lookup/slot identity is retained with host-width storage.
    u8 type = 0;
    return ReadTbl.GetDat(out, &type, name, nullptr) && ReadTbl.GetWkNo(slot, name);
}
int EventMgr::EvtReadMram(char*, int em, int* out, int, u32) {
    assert(em == 0); ++read_calls; *out = static_cast<int>(reinterpret_cast<std::uintptr_t>(loaded.m_addr)); return 1;
}
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

int main() {
    std::cout << std::unitbuf;
    arena = static_cast<unsigned char*>(mmap(reinterpret_cast<void*>(0x90000000), 0x20000,
        PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0));
    assert(arena == reinterpret_cast<void*>(0x90000000));
    unsigned cases = 0;
    for (u32 flags : {0U, 4U, 0x10U, 0x80U, 0x100U, 0x200U, 2U, 0x40U}) {
        setup(); ++cases;
        assert(EvtMgr.EvtReadExec(file_name, 0, flags) == 1); // False success is actual behavior.
        assert(pool_logs == 1 && init_calls == 0 && read_calls == 1 && errors == 2);
        verify_registered(arena);
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
    std::cout << "actual exhausted create -> SetEvt failure -> EvtReadExec success; ordinary flags release backing with live parent/bins; keep flags retain it PASS (defect characterized)\n";
    setup(); ++cases;
    std::strcpy(EvtMgr.NowExeEvtName, "occupied1"); retire_on_sleep = true;
    assert(EvtMgr.EvtReadExec(file_name, 0, 0) == 1 && sleep_calls == 1 && release_calls == 1 && !init_calls);
    verify_registered(arena);
    std::cout << "existing running-event key waits for prior completion, then failed new admission backing is still released with registrations PASS\n";
    setup(); ++cases;
    assert(EvtMgr.SetEvd(header_name, arena + 0x10000, nullptr, 2) == 1);
    assert(EvtMgr.EvtReadExec(file_name, 0, 0) == 1 && release_calls == 1);
    verify_registered(arena + 0x10000); // A repair must not delete this prior owner.
    std::cout << "pre-existing complete parent survives failed create/other input release PASS\n";
    setup(); ++cases;
    assert(EvtMgr.SetEvt(arena, static_cast<u32*>(nullptr)) == 0);
    verify_registered(arena); assert(!release_calls && !init_calls);
    pool[1].be_flag = 0;
    assert(EvtMgr.SetEvt(arena, static_cast<u32*>(nullptr)) == 1);
    assert(init_calls == 1 && parents[0].Count == 1 && bins[0].Count == 1);
    std::cout << "direct failed-create then free-slot retry, actual complete admission and constructor boundary PASS\n";
    setup(); ++cases; debug_transport = true; EvtMgr.BinTbl.NumDatTbl = 0;
    void* out = nullptr;
    assert(EvtMgr.GetEvd(&out, header_name, 0) == 0 && !out && read_calls == 1 && debug_frees.empty());
#if RE4DC_EVD_ADMISSION_TXN
    assert(!EvtMgr.EvdTbl.ChkDat(header_name)); // No owner took the debug input.
#else
    assert(EvtMgr.EvdTbl.ChkDat(header_name) && parents[0].dat2 == arena);
#endif
    std::cout << "actual tool GetEvd debug-read failure leaves input cleanup to caller PASS (cleanup absent)\n";
    std::cout << "EVENT_CALLER_CASES=" << cases << " txn=" << RE4DC_EVD_ADMISSION_TXN << " PASS\n";
    assert(mprotect(arena, 0x20000, PROT_READ | PROT_WRITE) == 0); munmap(arena, 0x20000);
}
