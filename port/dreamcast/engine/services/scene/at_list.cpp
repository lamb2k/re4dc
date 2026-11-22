// at_list.cpp (lane eng-e2d): the scene attachments' list, the engine's.
//
// The room's scene attachments (doors, item spots, ladders, message points: SceAtWork records, sce_at's decisions) sit in
// 16 bucket lists the scenario layer keeps in pS->ot[16]. The original keeps them with the PlayStation library's
// ordering-table calls (libgpu: ClearOTagR, AddPrim, DelPrim) and walks them with sceAtSetOtStart / sceAtGetOtAddr.
// Those are a list container, not drawing; the fight image no longer hosts libgpu (game/fight.mk) and sce_at's two
// walkers are made weak, so these bodies serve the hosted decisions.
//
// The layout is the records' (the hosted decisions read it): a link word is 0xFFFFFFFF at the end, a record's address
// with the top bit set, or the next bucket's slot with the top bit clear. The buckets are chained from the last (15)
// down to the first, so a walk from slot 15 meets every record, newest first within a bucket.
#include <stdint.h>
#include "types.h"
#include "libgpu.h"   // the container's entry points under the names the hosted units call
#include "sce_at.h"
#include "e1_engine.h"

namespace {
constexpr u32 kEnd = 0xFFFFFFFFu;
constexpr u32 kRecord = 0x80000000u;

inline bool is_record(u32 link) { return (link & kRecord) != 0 && link != kEnd; }
inline u32* at(u32 link) { return reinterpret_cast<u32*>(link | kRecord); }
inline u32 record_link(const void* p) { return static_cast<u32>(reinterpret_cast<uintptr_t>(p)); }
// The scene attachments' table, as its set-up made it (SceAtInit clears its 16 buckets, sce_at's own static storage):
// the walk starts at its last bucket. Before any set-up, an empty chain.
u32 g_empty = kEnd;
u32* g_table = 0;
int g_buckets = 0;
}   // namespace

// n buckets, the first the end of the chain, each later one chained to the one before it
// (In the fight image sce_at is the container's only caller; the other units that use it, act_btn, block, datactrl and
// debug, are not hosted. A second table cleared is counted, "E1 STUBCOUNT at_list: another table", so an image that
// hosts one of them shows it: the walk's start would then need sce_at's table by name.)
void ClearOTagR(u32* ot, int n)
{
    if (g_table != 0 && g_table != ot) e1_stub_hit("at_list: another table", n);
    g_table = ot, g_buckets = n;
    ot[0] = kEnd;
    for (int i = 1; i < n; i++) ot[i] = record_link(&ot[i - 1]) & ~kRecord;
}

// a record at the head of its bucket
void AddPrim(u32* ot, u32* prim)
{
    prim[0] = ot[0];
    ot[0] = record_link(prim);
}

// a record off the chain that starts at its bucket (a record not on it: nothing)
void DelPrim(u32* ot, u32* prim)
{
    for (u32* link = ot; *link != kEnd; link = at(*link)) {
        if (is_record(*link) && at(*link) == prim) {
            *link = *prim;
            return;
        }
    }
}

// the walk's start: the last bucket's slot
SceAtWork* sceAtSetOtStart()
{
    return reinterpret_cast<SceAtWork*>(g_buckets > 0 ? &g_table[g_buckets - 1] : &g_empty);
}

// the next record after p, past the buckets' own slots; 0 at the end
SceAtWork* sceAtGetOtAddr(SceAtWork* p)
{
    for (u32 link = p->next; link != kEnd; link = reinterpret_cast<SceAtWork*>(at(link))->next) {
        if (link & kRecord) return reinterpret_cast<SceAtWork*>(at(link));
    }
    return 0;
}
