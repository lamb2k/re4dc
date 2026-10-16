// Diagnostic snapshot rules copied from 76f40d95 src/game/trans.cpp.
// Only identifiers/visibility attributes differ; no live-list walk in Render.
// Othermark disc: which models are actors (members of EmMgr's alive list) and their list places, as a snapshot taken
// here in Trans (logic context, where the OT is built). Render code never walks the live list: Render draws the
// previous iteration's OT after the next tick's logic, when a listed unit may have been freed or re-linked (console
// fault 2026-10-15, 03a4813a: u->pNext read from a stale unit in OtherActorDraw). It compares a model's address
// against the last two snapshots by value only (the newest that holds it gives its place) and never dereferences them.
// While the sub screen window is swapped in (a radio call, the inventory: roomListsSwapped) the room's em works are
// sub screen bytes and EmMgr.pAlive is no list: no snapshot then (the game skips its own walks the same way; its
// actors are hidden by the Disp_flg bits meanwhile). Console faults 2026-10-15 (03a4813a in OtherActorDraw, c12f790a
// here, both at the r100 radio call: a "node" 0x4028e0c3, its pNext read at the odd 0x4028e0cb). Every step is
// also checked before it is followed (4-aligned, in main RAM, at most kOtherSnap hops); a rejected pointer ends the
// walk and is logged. While swapped the same checked walk runs once per swap as a probe (no snapshot kept) and logs
// the first pointer it rejects: the evidence that the swapped bytes are no list (Flycast performs odd reads silently).
namespace {
constexpr unsigned kOtherSnap = 256;
const void* g_otherSnap[2][kOtherSnap];
unsigned g_otherSnapN[2], g_otherSnapI, g_otherSwapSkips, g_otherRejects;
bool g_otherSwapped;
inline bool otherUnitPtrOk(const void* p)
{
    const uintptr_t a = (uintptr_t) p;
    return !(a & 3u) && (a & 0x1FFFFFFFu) >= 0x0C000000u && (a & 0x1FFFFFFFu) < 0x0D000000u - 0x40u;
}
// The checked walk: fills out (when given) and returns the units seen; *bad = the pointer that ended it, if rejected.
unsigned otherCheckedWalk(const void** out, const void** bad)
{
    unsigned n = 0;
    *bad = nullptr;
    const cUnit* u = EmMgr.pAlive;
    while (u && n < kOtherSnap) {
        if (!otherUnitPtrOk(u)) { *bad = u; break; }
        if (out) out[n] = u;
        ++n;
        u = u->pNext;
    }
    return n;
}
__attribute__((noinline,noclone)) void otherAliveSnapshot(int swapped)
{
    const void* bad = nullptr;
    if (swapped) {
        ++g_otherSwapSkips;
        if (!g_otherSwapped) {   // first Trans of this swap: the probe walk (nothing kept), then no more walks
            g_otherSwapped = true;
            const unsigned n = otherCheckedWalk(nullptr, &bad);
            re4dc_log("other: alive snapshot skipped: sub screen window swapped (em list %p; checked probe: %u hops, "
                      "%s %p; skips so far %u)\n", (void*) EmMgr.pAlive, n, bad ? "rejected" : "ended at", bad,
                      g_otherSwapSkips);
        }
        const unsigned k = g_otherSnapI ^ 1u;
        g_otherSnapN[k] = 0;
        g_otherSnapI = k;
        return;
    }
    if (g_otherSwapped) {
        g_otherSwapped = false;
        re4dc_log("other: alive snapshot resumed after the sub screen (%u Trans skipped)\n", g_otherSwapSkips);
    }
    const unsigned k = g_otherSnapI ^ 1u;
    const unsigned n = otherCheckedWalk(g_otherSnap[k], &bad);
    if (bad && g_otherRejects++ < 8)
        re4dc_log("other: alive snapshot: pointer %p rejected after %u units (list %p)\n", bad, n, (void*) EmMgr.pAlive);
    g_otherSnapN[k] = n;
    g_otherSnapI = k;
}
}  // namespace
extern "C" __attribute__((noinline,noclone)) int re4dc_other_actor_slot(const void* m)   // coarse.cpp too: the model's list place, -1 not an actor
{
    for (unsigned j = 0; j < 2; ++j) {
        const unsigned k = g_otherSnapI ^ j, n = g_otherSnapN[k] < kOtherSnap ? g_otherSnapN[k] : kOtherSnap;
        for (unsigned i = 0; i < n; ++i)
            if (g_otherSnap[k][i] == m) return (int) i;
    }
    return -1;
}
// The definitive benchmark pushes actor draw for snapshot members and restores
// the previous phase on every return. The offline marker stack supplies the
// previous phase; runtime stores only this invocation's membership result.
namespace {
struct OtherActorDraw {
    int member;
    explicit OtherActorDraw(cModel* m) {
        OTHER_INSTR_BEGIN();
        member = re4dc_other_actor_slot(m) >= 0;
        if (member) OTHER_MARK(push_actor);
        OTHER_INSTR_END_VALUE(member);
    }
    ~OtherActorDraw() {
        OTHER_INSTR_BEGIN();
        if (member) OTHER_MARK(pop_actor);
        OTHER_INSTR_END();
    }
};
}
