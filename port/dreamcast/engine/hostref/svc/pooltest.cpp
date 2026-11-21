// pooltest (lane eng-e1h): the engine's record pool (services/model/pool.h, ENG_POOL / ENG_POOL_BACK) on a test record
// type, in a 32-bit program with the records in the guest address range (0x8C000000+, the pool's RAM test). It checks
// what the character and light tables rely on (SERVICES.md section 41):
//   overflow     a create, createBack or create-at-slot on a full or used slot gives 0 and counts eng_pool_full;
//   order        create takes the first free slot (list front), createBack the last (list back);
//   double free  a destroy of a record that is not alive (flag 0: destroyed; flag 2: marked, then swept) is refused,
//                counted in eng_pool_bad_free, and writes nothing: the slot stays free and the list intact;
//   sweep        a flag-2 record is destroyed by the second dieCheck after its destroy, once.
// RE4_POOL_CONTROL=1 (the refusal off) or 2 (the full-table test off) sets eng_pool_control: pooltest must FAIL.
// Exit 0 PASS, 1 FAIL.
#include "pool.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>

extern "C" void __cxa_pure_virtual() { fprintf(stderr, "pooltest: pure virtual call\n"); abort(); }
extern "C" void* Debug_alloc(u32, int) { return 0; }
extern "C" void Debug_free(void*) {}
void operator delete(void*, unsigned int) noexcept {}   // the managers' deleting destructors (no heap here)
void operator delete(void*) noexcept {}

static int dtors;
class TRec : public cUnit {
public:
    int v;
    TRec() { be_flag = 0x21; }   // alive, as cEm::initWork
    virtual ~TRec() { dtors++; }
};

static u8* arena;
static u32 arena_used;
static int logs;
class TMgr : public cManager<TRec> {
public:
    TMgr(u8 flag) : cManager<TRec>(sizeof(TRec), flag) { setName("TMgr"); }
    virtual void* memAlloc(u32 n) { void* p = arena + arena_used; arena_used += (n + 31) & ~31u; return p; }
    virtual void memFree(void*) {}
    virtual void memClear(TRec* p, u32 n) { memset((void*) p, 0, n); }
    virtual void log(const char*, ...) { logs++; }
    virtual int construct(TRec* p, u32 id) { new (p) TRec; p->v = (int) id; return 1; }
};
ENG_POOL(TRec)
ENG_POOL_BACK(TRec)

static int fails;
#define CHECK(c, ...) do { if (!(c)) { fails++; printf("FAIL %s:%d ", __FILE__, __LINE__); printf(__VA_ARGS__); printf("\n"); } } while (0)

// The alive list as slot numbers, front to back; -1 on a cycle or a record outside the table.
static int list_of(TMgr& m, int* out, int cap)
{
    int n = 0;
    for (TRec* p = m.pAlive; p; p = (TRec*) p->pNext) {
        const int i = (int) (((u8*) p - (u8*) m.pArray) / m.size);
        if (n >= cap || i < 0 || i >= (int) m.nArray) return -1;
        out[n++] = i;
    }
    return n;
}

int main()
{
    const char* ctl = getenv("RE4_POOL_CONTROL");
    eng_pool_control = ctl ? (u32) atoi(ctl) : 0;
    arena = (u8*) mmap((void*) 0x8C100000, 1 << 20, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED, -1, 0);
    if (arena != (u8*) 0x8C100000) { printf("pooltest: cannot map the guest range\n"); return 1; }
    int l[16];

    // ---- flag 0 (destroyed at once), four slots ----
    TMgr a(0);
    a.arrayAlloc(4);
    TRec* r0 = a.create(10);
    TRec* r3 = a.createBack(13);
    TRec* r1 = a.create(11);
    TRec* r2 = a.create(12);
    CHECK(r0 && r1 && r2 && r3, "four creates on four slots");
    CHECK(r0 == a.workAt(0) && r1 == a.workAt(1) && r2 == a.workAt(2) && r3 == a.workAt(3),
          "create takes the first free slot, createBack the last");
    int n = list_of(a, l, 16);
    CHECK(n == 4 && l[0] == 2 && l[1] == 1 && l[2] == 0 && l[3] == 3, "list front 2 1 0, createBack's 3 at the back (n %d)", n);
    const u32 full0 = eng_pool_full;
    TRec* x = a.create(20);
    CHECK(x == 0, "create on a full table refused (got slot %d)", x ? (int) (((u8*) x - (u8*) a.pArray) / a.size) : -1);
    x = a.createBack(21);
    CHECK(x == 0, "createBack on a full table refused");
    x = a.create(22, 1);
    CHECK(x == 0, "create at a used slot refused");
    CHECK(eng_pool_full - full0 == 3, "three full-table refusals counted (%u)", (unsigned) (eng_pool_full - full0));
    CHECK(r1->v == 11 && r2->v == 12, "the refused creates wrote nothing (%d %d)", r1->v, r2->v);

    const u32 bad0 = eng_pool_bad_free;
    a.destroy(r1);
    CHECK(dtors == 1 && r1->be_flag == 0, "destroy runs the destructor once and frees the slot");
    a.destroy(r1);
    CHECK(dtors == 1, "a second destroy runs no destructor (%d)", dtors);
    CHECK(eng_pool_bad_free - bad0 == 1, "the double free is counted (%u)", (unsigned) (eng_pool_bad_free - bad0));
    n = list_of(a, l, 16);
    CHECK(n == 3 && l[0] == 2 && l[1] == 0 && l[2] == 3, "the list keeps 2 0 3 (n %d)", n);
    CHECK(a.countActiveWork() == 3, "three in use");
    x = a.createBack(23);
    CHECK(x == r1, "the freed slot is taken again");

    // ---- flag 2 (marked, then swept by dieCheck), three slots ----
    TMgr b(2);
    b.arrayAlloc(3);
    TRec* s0 = b.create(30);
    TRec* s1 = b.create(31);
    TRec* s2 = b.create(32);
    CHECK(s0 && s1 && s2, "three creates");
    const int d0 = dtors;
    const u32 bad1 = eng_pool_bad_free;
    b.destroy(s1);
    CHECK(s1->be_flag & 0x200, "destroy marks the record");
    b.destroy(s1);                        // already marked: refused
    CHECK(eng_pool_bad_free - bad1 == 1, "destroy of a marked record refused (%u)", (unsigned) (eng_pool_bad_free - bad1));
    b.dieCheck();
    b.dieCheck();
    CHECK(dtors - d0 == 1 && s1->be_flag == 0, "swept once by the second dieCheck (dtors %d, flags %x)", dtors - d0,
          (unsigned) s1->be_flag);
    b.destroy(s1);                        // dead: refused, the slot stays free
    CHECK(s1->be_flag == 0, "a destroy of a dead record leaves it free (flags %x)", (unsigned) s1->be_flag);
    CHECK(eng_pool_bad_free - bad1 == 2, "and is counted (%u)", (unsigned) (eng_pool_bad_free - bad1));
    CHECK(b.countActiveWork() == 2, "two in use (%u)", (unsigned) b.countActiveWork());
    b.dieCheck();
    b.dieCheck();
    CHECK(dtors - d0 == 1, "no second destructor run (%d)", dtors - d0);
    n = list_of(b, l, 16);
    CHECK(n == 2 && l[0] == 2 && l[1] == 0, "the list keeps 2 0 (n %d)", n);

    printf("pooltest: control %u, full refusals %u, bad frees %u, destructors %d, logs %d: %s\n",
           (unsigned) eng_pool_control, (unsigned) eng_pool_full, (unsigned) eng_pool_bad_free, dtors, logs,
           fails ? "FAIL" : "PASS");
    return fails ? 1 : 0;
}
