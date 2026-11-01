#include "stub/host.h"
#include <algorithm>
#include <cassert>
#include <tuple>
#include <vector>

struct Block { void* p; u32 bytes; bool free; };
static std::vector<Block> blocks;
static void (*on_push)(cObj*);
static void (*on_construct)(cObj*);
static void (*active_delete)(int, int, int);
static unsigned all_calls;
static std::vector<std::tuple<u32, u32, u16, u8> > effects;
static std::vector<std::tuple<u32, u32> > destroyed;

extern "C" { u32 re4dc_alive_gen[4]; u32 re4dc_frozen_pools; }
#if RE4DC_FX_SCAN == 2
enum { FXC_EFM_BUILD, FXC_EFM, FXC_MIS_EFM, FXC_FALLBACK };
u32 re4dc_fx_chk[4];
#endif
EfmHostGame game_state = {};
EfmHostGame* pG = &game_state;
EfmHostHeap Heap[16] = {};

void* Debug_alloc(u32 n, int) { return std::calloc(1, n); }
void Debug_free(void* p) { std::free(p); }
int MemGetCurrentHeap() { return 0; }
void memclr_asm(void* p, u32 n) { std::memset(p, 0, n); }
extern "C" void re4dc_log(const char*, ...) {}
extern "C" void re4dc_missing(const char*) { assert(false); }
void* mem_alloc(u32 n, const char*, int, int, int) {
    for (Block& b : blocks) if (b.free && b.bytes == n) { b.free = false; return b.p; }
    void* p = nullptr;
    assert(posix_memalign(&p, 32, n) == 0);
    blocks.push_back({p, n, false});
    return p;
}
extern "C" void OSFreeToHeap(int, void* p) {
    for (Block& b : blocks) if (b.p == p) { assert(!b.free); b.free = true; return; }
    assert(false);
}

cObjMgr ObjMgr;
cObjMgr::cObjMgr() : cManager<cObj>(sizeof(cObj), 2), fail_construct(false) { setName("cObjMgr"); }
void* cObjMgr::memAlloc(u32 n) { return std::calloc(1, n); }
void cObjMgr::memFree(void* p) { std::free(p); }
void cObjMgr::memClear(cObj* p, u32 n) { std::memset(p, 0, n); }
void cObjMgr::log(const char*, ...) {}
int cObjMgr::construct(cObj* p, u32 id) {
    new (p) cObj();
    p->id = id;
    if (on_construct) on_construct(p);
    if (fail_construct) { fail_construct = false; p->be_flag = 0; return 0; }
    return 1;
}
void cObj::push() {
    be_flag &= ~0x22;
    if (on_push) on_push(this);
}
void cObjMgr::destroy(cObj* p) {
    if ((p->be_flag & 0x201) != 1) return;
    p->push();
    destroyed.push_back({p->id, p->efm04.core.flg});
    cManager<cObj>::destroy(p);
}

u16 g_Core_flg;
u8 g_Core_kind;
cModel* g_Core_pEm;
void EfmDelete(int, int, int);
void EfmDeleteSub(cObj*);
static u32 slot_of(cObj* obj) {
    for (u32 i = 0; i < ObjMgr.nArray; ++i) if (ObjMgr.workAt(i) == obj) return i;
    return ULONG_MAX;
}
void fixture_visit(cObj* obj) {
    ++all_calls;
    if (obj->id == 4 || obj->id == 5 || obj->id == 9) {
        EfmCore* core = obj->id == 4 ? &obj->efm04.core : obj->id == 5 ? &obj->efm05.core : &obj->efm09.core;
        effects.push_back({slot_of(obj), obj->id, core->flg, core->kind});
    }
}

// The generated include is an unchanged source excerpt from esp_efm.cpp apart from
// one visit probe at EfmDeleteSub's opening brace. The 64-bit host uses bridge workAt;
// the target's 32-bit +64 inline lookup is separately represented by the flag gate.
#undef RE4DC_WORKAT_INLINE
#define RE4DC_WORKAT_INLINE 1
#include "efm_source_slice.inc"

static void source_delete(int a, int b, int c) {
    g_Core_flg = a; g_Core_kind = b; g_Core_pEm = (cModel*) c;
    for (u32 i = 0; i < ObjMgr.nArray; ++i) {
        cObj* obj = ObjMgr.workAt(i);
        if (obj) EfmDeleteSub(obj);
    }
}
static cObj* make_at(u32 no, u32 id, u16 flg, u8 kind = 1) {
    cObj* p = ObjMgr.create(id, no);
    if (!p) std::fprintf(stderr, "create failed: slot=%lu id=%lu n=%lu array=%p push=%lu\n",
                         no, id, ObjMgr.nArray, (void*)ObjMgr.pArray, ObjMgr.pArrayPush);
    assert(p);
    EfmCore* core = id == 4 ? &p->efm04.core : id == 5 ? &p->efm05.core : &p->efm09.core;
    core->flg = flg; core->kind = kind;
    return p;
}
static void reset(u32 n) {
    on_push = nullptr; on_construct = nullptr;
    re4dc_frozen_pools = 0;
    ObjMgr.arrayFree(); ObjMgr.roomInit(); assert(ObjMgr.arrayAlloc(n));
    all_calls = 0; effects.clear(); destroyed.clear();
}
static void clear_trace() { all_calls = 0; effects.clear(); destroyed.clear(); }
typedef std::tuple<u32, u32, u16, u8> Effect;
typedef std::tuple<bool, u32, u32, u16, u8> State;
struct Outcome {
    std::vector<Effect> effects;
    std::vector<std::tuple<u32,u32> > destroyed;
    std::vector<State> state;
    unsigned all_calls;
    u32 builds;
};
static Outcome outcome(u32 build0) {
    Outcome r;
    r.effects = effects; r.destroyed = destroyed; r.all_calls = all_calls;
    r.builds = fxEfmBuildSerial - build0;
    for (u32 i = 0; i < ObjMgr.nArray; ++i) {
        cObj* p = ObjMgr.workAt(i);
        if (!p) { r.state.push_back({false,0,0,0,0}); continue; }
        EfmCore* core = p->id == 4 ? &p->efm04.core : p->id == 5 ? &p->efm05.core : &p->efm09.core;
        r.state.push_back({true,p->id,p->be_flag,core->flg,core->kind});
    }
    return r;
}
static void same(const Outcome& a, const Outcome& b) {
    assert(a.effects == b.effects);
    assert(a.destroyed == b.destroyed);
    assert(a.state == b.state);
}
static void execute(bool fast, int a, int b = 0, int c = 0) {
    active_delete = fast ? EfmDelete : source_delete;
    active_delete(a,b,c);
}

static Outcome repeated(bool fast) {
    reset(80);
    make_at(1,4,1); make_at(20,5,2); make_at(40,9,1); make_at(60,3,1);
    execute(fast,99); clear_trace();
    const u32 build0 = fxEfmBuildSerial;
    const u32 class0 = re4dc_obj_class_gen, alive0 = re4dc_alive_gen[2];
    execute(fast,1); execute(fast,1); execute(fast,2);
    assert(re4dc_obj_class_gen == class0);
    assert(re4dc_alive_gen[2] > alive0);
    Outcome r = outcome(build0);
    if (fast) assert(r.builds == 0);
    return r;
}
static Outcome reconstruct(bool fast) {
    reset(24);
    cObj* old = make_at(1,4,1);
    execute(fast,99); clear_trace(); const u32 build0 = fxEfmBuildSerial;
    ObjMgr.destroy(old);
    ObjMgr.dieCheck(); ObjMgr.dieCheck();
    cObj* next = make_at(1,5,2);
    assert(next == old);
    clear_trace(); execute(fast,2);
    Outcome r = outcome(build0);
    if (fast) assert(r.builds == 1);
    return r;
}
static Outcome failed_and_back(bool fast) {
    reset(24);
    execute(fast,99); clear_trace(); const u32 build0 = fxEfmBuildSerial;
    ObjMgr.fail_construct = true;
    assert(!ObjMgr.create(4));
    ObjMgr.fail_construct = true;
    assert(!ObjMgr.createBack(9));
    clear_trace(); execute(fast,99);
    Outcome r = outcome(build0);
    if (fast) { assert(r.builds == 1); assert(r.effects.size() == 2); }
    return r;
}
static void construct_reenter(cObj*) {
    on_construct = nullptr;
    active_delete(99,0,0); // observe the new class before construct returns
}
static Outcome constructor_reentry(bool fast, bool failed) {
    reset(24);
    make_at(1,4,1);
    execute(fast,99); clear_trace(); const u32 build0 = fxEfmBuildSerial;
    active_delete = fast ? EfmDelete : source_delete;
    ObjMgr.fail_construct = failed;
    on_construct = construct_reenter;
    cObj* made = failed ? ObjMgr.create(5) : ObjMgr.create(5,9);
    on_construct = nullptr;
    if (failed) assert(!made);
    else {assert(made); made->efm05.core.flg = 2;}
    execute(fast,99);
    Outcome r = outcome(build0);
    assert(r.effects.size() == 4);
    const unsigned at = failed ? 0 : 1;
    assert(std::get<0>(r.effects[at]) == (failed ? 0 : 9) &&
           std::get<1>(r.effects[at]) == 5 && std::get<2>(r.effects[at]) == 0);
    assert(std::get<0>(r.effects[at+2]) == (failed ? 0 : 9) &&
           std::get<2>(r.effects[at+2]) == (failed ? 0 : 2));
    if (fast) assert(r.builds == 2); // inside constructor and after its final publication
    return r;
}
static Outcome pool_reuse(bool fast) {
    reset(24);
    make_at(1,4,1);
    execute(fast,99); clear_trace(); const u32 build0 = fxEfmBuildSerial;
    cObj* old_array = ObjMgr.pArray;
    ObjMgr.arrayFree(); assert(ObjMgr.arrayAlloc(24));
    assert(ObjMgr.pArray == old_array);
    make_at(17,5,2);
    clear_trace(); execute(fast,2);
    Outcome r = outcome(build0);
    if (fast) assert(r.builds == 1);
    return r;
}
static Outcome map_new_page(bool fast) {
    reset(24);
    make_at(1,4,1);
    execute(fast,99); clear_trace(); const u32 build0 = fxEfmBuildSerial;
    const u32 g0 = re4dc_obj_class_gen;
    cObj* pinned = ObjMgr.workAt(1);
    assert(ObjMgr.prepareWork(1,1));
    assert(ObjMgr.workAt(1) == pinned && re4dc_obj_class_gen == g0);
    assert(ObjMgr.prepareWork(17,1));
    assert(re4dc_obj_class_gen > g0);
    clear_trace(); execute(fast,1);
    Outcome r = outcome(build0);
    if (fast) assert(r.builds == 1);
    return r;
}
static Outcome create_variants(bool fast) {
    reset(24);
    execute(fast,99); clear_trace(); const u32 build0 = fxEfmBuildSerial;
    cObj* front = ObjMgr.create(4);
    cObj* back = ObjMgr.createBack(5);
    assert(front && back && slot_of(front) == 0 && slot_of(back) == 23);
    front->efm04.core.flg = 1;
    back->efm05.core.flg = 1;
    clear_trace(); execute(fast,1);
    Outcome r = outcome(build0);
    if (fast) assert(r.builds == 1);
    return r;
}
static Outcome pushed(bool fast) {
    reset(24);
    make_at(1,4,1);
    execute(fast,99); clear_trace(); const u32 build0 = fxEfmBuildSerial;
    assert(ObjMgr.arrayPush(16));
    make_at(4,5,2);
    execute(fast,2);
    assert(ObjMgr.arrayPop());
    execute(fast,1);
    Outcome r = outcome(build0);
    if (fast) assert(r.builds == 1);
    return r;
}
static Outcome frozen(bool fast) {
    reset(24);
    make_at(1,4,1);
    execute(fast,99); clear_trace(); const u32 build0 = fxEfmBuildSerial;
    re4dc_frozen_pools = 1;
    execute(fast,1);
    re4dc_frozen_pools = 0;
    Outcome r = outcome(build0);
    if (fast) assert(r.builds == 0);
    return r;
}
static Outcome too_many(bool fast) {
    reset(80);
    for (u32 i = 0; i < 65; ++i) make_at(i,4,1);
    clear_trace(); const u32 build0 = fxEfmBuildSerial;
    execute(fast,99);
    Outcome r = outcome(build0);
    if (fast) { assert(fxEfmCnt == -1); assert(r.builds == 1); assert(r.effects.size() == 65); }
    return r;
}
static void nested_push(cObj*) {
    on_push = nullptr;
    active_delete(7,0,0);  // the source filter globals remain 7 after this call
    make_at(6,4,7);
}
static Outcome nested(bool fast) {
    reset(24);
    make_at(1,4,1); make_at(9,5,8);
    execute(fast,99); clear_trace(); const u32 build0 = fxEfmBuildSerial;
    active_delete = fast ? EfmDelete : source_delete;
    on_push = nested_push;
    active_delete(1,0,0);
    on_push = nullptr;
    execute(fast,99);
    Outcome r = outcome(build0);
    if (fast) assert(r.builds == 1);
    return r;
}
static void rebuild_before_resume(cObj*) {
    on_push = nullptr;
    make_at(6,4,7);
    active_delete(7,0,0); // rebuilds the index before the outer callback returns
}
static Outcome nested_rebuild(bool fast) {
    reset(24);
    make_at(1,4,1); make_at(9,5,7); make_at(18,9,1);
    execute(fast,99); clear_trace(); const u32 build0 = fxEfmBuildSerial;
    active_delete = fast ? EfmDelete : source_delete;
    on_push = rebuild_before_resume;
    active_delete(1,0,0);
    on_push = nullptr;
    Outcome r = outcome(build0);
    std::vector<u32> slots;
    for (const Effect& e : r.effects) slots.push_back(std::get<0>(e));
    assert((slots == std::vector<u32>{1,1,6,9,18,6,9,18}));
    // The first 1 is the outer visit, the second the nested visit. The outer
    // continuation starts at source slot 2 even after the nested index rebuild.
    if (fast) assert(r.builds == 1);
    return r;
}
static void swap_pool_on_push(cObj*) {
    on_push = nullptr;
    assert(ObjMgr.arrayPush(16));
    make_at(6,4,1);
}
static Outcome callback_pool_swap(bool fast) {
    reset(24);
    make_at(1,4,1); make_at(9,5,1);
    execute(fast,99); clear_trace(); const u32 build0 = fxEfmBuildSerial;
    active_delete = fast ? EfmDelete : source_delete;
    on_push = swap_pool_on_push;
    active_delete(1,0,0);
    on_push = nullptr;
    Outcome r = outcome(build0);
    assert(ObjMgr.arrayPop());
    if (fast) assert(r.builds == 0);
    return r;
}
static Outcome class_exhaustion(bool fast) {
    reset(24);
    make_at(1,4,1);
    execute(fast,99); clear_trace(); const u32 build0 = fxEfmBuildSerial;
    re4dc_obj_class_gen = ~u32(0) - 1;
    make_at(9,5,2);
    assert(re4dc_obj_class_gen == ~u32(0));
    execute(fast,1);
    make_at(17,4,1);
    assert(re4dc_obj_class_gen == ~u32(0));
    execute(fast,1);
    Outcome r = outcome(build0);
    if (fast) assert(r.builds == 0);
    return r;
}
static Outcome serial_exhaustion(bool fast) {
    reset(24);
    // The preceding case pinned the class token; restore a finite test value to
    // isolate exhaustion of the independent build incarnation counter.
    re4dc_obj_class_gen = 100;
    make_at(1,4,1);
    execute(fast,99); clear_trace();
    fxEfmBuildSerial = ~u32(0) - 1;
    const u32 build0 = fxEfmBuildSerial;
    make_at(9,5,2);
    execute(fast,1);
    assert(fxEfmBuildSerial == (fast ? ~u32(0) : build0));
    make_at(17,4,1);
    execute(fast,1);
    assert(fxEfmBuildSerial == (fast ? ~u32(0) : build0));
    Outcome r = outcome(build0);
    if (fast) assert(r.builds == 1);
    return r;
}
static Outcome unrepresentable_slot(bool fast) {
    reset(65537);
    make_at(65536,4,1);
    clear_trace(); const u32 build0 = fxEfmBuildSerial;
    execute(fast,99);
    execute(fast,1);
    Outcome r = outcome(build0);
    assert(r.effects.size() == 2);
    assert(std::get<0>(r.effects[0]) == 65536 && std::get<0>(r.effects[1]) == 65536);
    if (fast) {assert(fxEfmCnt == -1); assert(r.builds == 1);}
    return r;
}

int main() {
    const Outcome fast_repeat = repeated(true), source_repeat = repeated(false);
    same(fast_repeat, source_repeat);
    assert(fast_repeat.all_calls == 9 && source_repeat.all_calls == 96);
    same(reconstruct(true), reconstruct(false));
    same(failed_and_back(true), failed_and_back(false));
    same(constructor_reentry(true,false), constructor_reentry(false,false));
    same(constructor_reentry(true,true), constructor_reentry(false,true));
    same(pool_reuse(true), pool_reuse(false));
    same(map_new_page(true), map_new_page(false));
    same(create_variants(true), create_variants(false));
    same(pushed(true), pushed(false));
    same(frozen(true), frozen(false));
    same(too_many(true), too_many(false));
    same(nested(true), nested(false));
    same(nested_rebuild(true), nested_rebuild(false));
    same(callback_pool_swap(true), callback_pool_swap(false));
    same(unrepresentable_slot(true), unrepresentable_slot(false));
    same(class_exhaustion(true), class_exhaustion(false));
    same(serial_exhaustion(true), serial_exhaustion(false));
    ObjMgr.arrayFree();
    for (const Block& b : blocks) std::free(b.p);
    std::puts("EFM identity: 17 source/accelerated cases pass");
    std::puts("Synthetic repeated sweep: 9 indexed / 96 source EfmDeleteSub calls");
}
