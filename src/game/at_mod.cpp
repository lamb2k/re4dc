#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
#include "fallback_audit35.h"
#endif
#line 1
// game/at_mod.cpp: character-to-character collision and the hit box ("yarare") setup. EmAtCheck
// pushes a character's cAtariInfo body (cylinder or yaw-aligned box) out of every other
// character's and object's body by push priority; EmHitCheck / ObjHitCheck trace a line against
// those bodies (camera, aiming). The Yarare* functions build the YARARE_INFO chain of hit boxes
// weapons test (em_sub.cpp).

#include "atari.h"
#include "re4dc_xm.h" // GAME_SH4ZAM_LOGIC (lane sh4zam-direct)
#include "at_mod.h"
#include "at_sub.h"
#include "emhit.h"
#include "obj.h"
#include "player.h"
#include "global.h"
#include "math_sub.h"
#include "motion.h"
#include "db_log.h"

extern "C" {
void yarareInit0(YARARE_INFO* y, f32 x, f32 yy, f32 z, f32 w, f32 h, s16 no, u16 flags);
static int priorityCheck(cEm* pMod, cEm* pMod2);
static int sphereRectCk(cAtariInfo* info, Vec* p, f32 rad);
// game/em_sub.cpp
int emLineCubeCrossCk(Vec* a, Vec* b, Mtx m, f32 sx, f32 sy, f32 sz, cAtariInfo* info, Vec* hit);
}

// Matrix copy written out as loops. The row counter is a do-while starting at 2 (`i_-- != 0`): the
// original's counter of ComnHitCheck's first copy is live across the getPartsPtr call (callee-saved
// r30), which a `while (i_--)` from 3 cannot give (cse folds the peeled test and re-materialises
// `li 2` after the call). The row pointers step destination first (`d_++; s_++;`): that LUID order
// gives the target's `addi d; addi s` pairs and keeps the second copy's `sp_ = *s_` a separate
// register copy (s_ r0, sp_ r9) -- ComnHitCheck is byte-identical with it.
// ObaLineHitChk (matching): one PSVECMag call squared (`mag * mag`), tc/s clamped with ternaries (s in
// place: its temporary is copied back into f30), den anchored in f0 (anchor gated by `de * ef` so the
// hoisted `mr r3,r27` keeps its slot), and the getPartsPtr `if` written with an explicit `else pm = m`
// so cse's extended block ends at the join and the `&p0` argument after the call stays a fresh
// `addi r4,r1,8` (with `pm = m` hoisted before the `if`, cse skips the arm and folds `&p0` into the
// copy's address pseudo).
#define MTX_COPY(src, dst)               \
    {                                    \
        MtxPtr d_ = (dst);               \
        int i_ = 2;                      \
        MtxPtr s_ = (src);               \
        int j_;                          \
        f32* sp_;                        \
        f32* dp_;                        \
        do {                             \
            dp_ = *d_;                   \
            sp_ = *s_;                   \
            for (j_ = 0; j_ < 4; j_++) { \
                *dp_++ = *sp_++;         \
            }                            \
            d_++;                        \
            s_++;                        \
        } while (i_-- != 0);             \
    }

// Fills one hit box: offset, width (radius) / height, the parts it follows (1-based, 0 = model),
// flags; not linked.
void yarareInit0(YARARE_INFO* y, f32 x, f32 yy, f32 z, f32 w, f32 h, s16 no, u16 flags)
{
    y->ofs.x = x;
    y->ofs.y = yy;
    y->ofs.z = z;
    y->width = w;
    y->height = h;
    y->partsNo = no;
    y->flags = flags;
    y->next = 0;
}

// Sets the character's primary hit box (cEm::hitInfo) as a cylinder of radius w / height h.
void YarareInit(cEm* em, f32 x, f32 y, f32 z, f32 w, f32 h, s16 no, u16 flags)
{
    yarareInit0(&em->hitInfo, x, y, z, w, h, no, flags);
}

// Sets the primary hit box as a box (flags bit3): half sizes w (x) / h (y) / extent (z).
void YarareInitCube(cEm* em, f32 x, f32 y, f32 z, f32 w, f32 h, f32 extent, s16 no, u16 flags)
{
    yarareInit0(&em->hitInfo, x, y, z, w, h, no, flags);
    em->hitInfo.depth = extent;
    em->hitInfo.flags |= 8;
}

// Appends a cylinder hit box to the character's hit box chain (error when already linked).
void YarareAdd(cEm* em, YARARE_INFO* box, f32 x, f32 y, f32 z, f32 w, f32 h, s16 no, u16 flags)
{
    YARARE_INFO* p = &em->hitInfo;

    yarareInit0(box, x, y, z, w, h, no, flags);
    for (; p->next != 0; p = p->next) {
        if (p == box) {
            pLog->err(0, 0, "YarareAdd() Add same pointer, EM%02x", em->id);
            return;
        }
    }
    if (p == box) {
        pLog->err(0, 0, "YarareAdd() Add same pointer, EM%02x", em->id);
        return;
    }
    p->next = box;
}

// Appends a box hit box to the chain.
void YarareAddCube(cEm* em, YARARE_INFO* box, f32 x, f32 y, f32 z, f32 w, f32 h, f32 extent, s16 no, u16 flags)
{
    YARARE_INFO* p;

    yarareInit0(box, x, y, z, w, h, no, flags);
    box->depth = extent;
    box->flags |= 8;
    p = &em->hitInfo;
    while (p->next != 0) {
        if (p == box) {
            pLog->err(0, 0, "YarareAdd() Add same pointer, EM%02x", em->id);
        }
        p = p->next;
    }
    if (p->next != box) {
        p->next = box;
    }
}

// Character-vs-character collision for `em` (called from its move): refreshes every collidable
// body's world position (m_flag 0x200, non-zero radius), pushes `em` against every other
// character and then every object (__em_at_core), stores the old positions and recomputes the
// parts world positions. A body without collision only marks m_stat bit0.
#if defined(RE4DC_ATCHK) && RE4DC_ATCHK
// GAME_ATCHK (game30.mk, design-logic P2): each list is walked once per call and its collidable
// bodies (m_flag 0x200, m_radius2 != 0) are collected in list order; the three passes then run over
// that array. Exact: nothing the passes execute (getPos, __em_at_core -> At_em_*_ck, RotVector,
// PSMTX/PSVEC, getPartsPtr) writes m_flag, m_radius2, pNext or a manager's pAlive -- they only move
// pos / m_Pos -- so every pass sees the same bodies in the same order as the three list walks. The
// walk prefetches the next body's cAtariInfo line while testing the current one. More bodies than
// the array holds: the original code runs.
#define ATCHK_MAX 96
static int atchkCollect(cEm* head, cEm** out)
{
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
    re4dc::fa35::hit(re4dc::fa35::CollisionCollectSource, 1);
#endif
#line 140
    int n = 0;
    for (cEm* m = head; m != 0; m = (cEm*) m->pNext) {
        cEm* nx = (cEm*) m->pNext;
        if (nx) {
            __builtin_prefetch(__builtin_addressof(nx->atari.m_flag));
        }
        if ((m->atari.m_flag & 0x200) && m->atari.m_radius2 != 0.0f) {
            if (n == ATCHK_MAX) {
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
                re4dc::fa35::hit(re4dc::fa35::CollisionCandidateOverflow, 1);
#endif
#line 148
                return -1;
            }
            out[n++] = m;
        }
    }
    return n;
}
#if defined(RE4DC_ATCHK_LIST) && RE4DC_ATCHK_LIST
// GAME_ATCHK_LIST (game30.mk, square plan step 1): the alive lists of EmMgr and ObjMgr are kept
// in list order in an array, rebuilt only when the list changed since the last call (the
// generation cManager.h bumps on every list and work-array change, plus the head
// pointer). The collidable test still reads each body's live m_flag / m_radius2, in the same
// order, so the candidates are the ones the list walk finds. What changes: the walk no longer
// chases pNext (a load that waits for the previous one); the array lets the bodies' cAtariInfo
// lines be prefetched ATLIST_PF ahead. More works than ATLIST_MAX: the list walk runs.
// =2 (diagnostic): every cached use is also checked against a list walk (a mismatch is counted
// and rebuilt), with an "ATL" summary line every 8192 syncs.
// GAME_ATLIST_512 changes only the existing ordered alive-array capacity. The
// 96-candidate limit, dirty-note reuse and complete overflow fallback stay intact.
#if defined(RE4DC_ATLIST_512) && RE4DC_ATLIST_512
#define ATLIST_MAX 512
#else
#define ATLIST_MAX 320
#endif
#define ATLIST_PF 6
struct AtList {
    cEm* head;
    u32 gen;
    int n;   /* -1: not built (or longer than ATLIST_MAX) */
#if defined(RE4DC_ATCHK_CACHE) && RE4DC_ATCHK_CACHE
    u32 lo;     /* lowest body info address (GAME_ATCHK_CACHE) */
    u32 span;   /* highest - lowest */
#endif
    cEm* v[ATLIST_MAX];
};
static AtList atListEm = { 0, 0, -1 }, atListObj = { 0, 0, -1 };
extern "C" {
u32 re4dc_alive_gen[4];   /* cManager.h RE4DC_ALIVE_BUMP */
}
#if RE4DC_ATCHK_LIST == 2
extern "C" void re4dc_log(const char* fmt, ...);
static u32 atlSync, atlRebuild, atlOvf, atlMis, atlMaxN, atlVisits;
#endif
static int atListBuild(AtList* L, cEm* head, u32 gen)
{
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
    re4dc::fa35::hit(re4dc::fa35::CollisionAliveBuild, 1);
#endif
#line 193
    int n = 0;
#if defined(RE4DC_ATCHK_CACHE) && RE4DC_ATCHK_CACHE
    u32 lo = 0xFFFFFFFFu;
    u32 hi = 0;
#endif
    L->head = head;
    L->gen = gen;
    for (cEm* m = head; m != 0; m = (cEm*) m->pNext) {
        if (n == ATLIST_MAX) {
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
            re4dc::fa35::hit(re4dc::fa35::CollisionAliveOverflow, 1);
#endif
#line 202
            L->n = -1;
#if !defined(RE4DC_ATLIST_OVERFLOW) || !RE4DC_ATLIST_OVERFLOW
            L->head = 0;
#endif
#if RE4DC_ATCHK_LIST == 2
            atlOvf++;
#endif
            return -1;
        }
        L->v[n++] = m;
#if defined(RE4DC_ATCHK_CACHE) && RE4DC_ATCHK_CACHE
        const u32 p = (u32) &m->atari;
        lo = p < lo ? p : lo;
        hi = p > hi ? p : hi;
#endif
    }
    L->n = n;
#if defined(RE4DC_ATCHK_CACHE) && RE4DC_ATCHK_CACHE
    L->lo = n != 0 ? lo : 0;
    L->span = n != 0 ? hi - lo : 0;
#endif
#if RE4DC_ATCHK_LIST == 2
    atlRebuild++;
    if ((u32) n > atlMaxN) {
        atlMaxN = n;
    }
#endif
    return n;
}
static inline int atListSync(AtList* L, cEm* head, u32 gen)
{
#if defined(RE4DC_ATLIST_OVERFLOW) && RE4DC_ATLIST_OVERFLOW
    // A failed build is also valid until the manager changes. Keep using the
    // complete source walk; only avoid retrying its same oversized prefix.
    if (L->n < 0 && L->head != 0 && L->head == head && L->gen == gen) {
#if RE4DC_ATCHK_LIST == 2
        // Check mode verifies the negative result too: an unreported shrink
        // is a mismatch and rebuild, rather than a silently retained overflow.
        cEm* m = head;
        int n = 0;
        for (; m != 0 && n < ATLIST_MAX; m = (cEm*) m->pNext) {
            n++;
        }
        if (m == 0) {
            ++atlMis;
            return atListBuild(L, head, gen);
        }
#endif
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
        re4dc::fa35::hit(re4dc::fa35::CollisionCachedOverflow, 1);
#endif
#line 250
        return -1;
    }
#endif
#if RE4DC_ATCHK_LIST == 2
    if (++atlSync % 8192 == 0) {
        re4dc_log("ATL sync=%u rebuild=%u ovf=%u mismatch=%u maxn=%u visits=%u\n", atlSync, atlRebuild, atlOvf,
                  atlMis, atlMaxN, atlVisits);
    }
    if (L->n >= 0 && L->gen == gen && L->head == head) {
        int i = 0;
        cEm* m;
        for (m = head; m != 0 && i < L->n && L->v[i] == m; m = (cEm*) m->pNext) {
            i++;
        }
        if (m != 0 || i != L->n) {
            atlMis++;
            return atListBuild(L, head, gen);
        }
        atlVisits += L->n;
        return L->n;
    }
    return atListBuild(L, head, gen);
#else
    if (L->n >= 0 && L->gen == gen && L->head == head) {
        return L->n;
    }
    return atListBuild(L, head, gen);
#endif
}
static int atchkCollectList(const AtList* L, int N, cEm** out)
{
    cEm* const* a = L->v;
    int n = 0;
    int i;
    for (i = 0; i < N && i < ATLIST_PF; i++) {
        __builtin_prefetch(__builtin_addressof(a[i]->atari.m_flag));
    }
    for (i = 0; i < N; i++) {
        cEm* m = a[i];
        if (i + ATLIST_PF < N) {
            __builtin_prefetch(__builtin_addressof(a[i + ATLIST_PF]->atari.m_flag));
        }
        if ((m->atari.m_flag & 0x200) && m->atari.m_radius2 != 0.0f) {
            if (n == ATCHK_MAX) {
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
                re4dc::fa35::hit(re4dc::fa35::CollisionCandidateOverflow, 1);
#endif
#line 294
                return -1;
            }
            out[n++] = m;
        }
    }
    return n;
}
#if defined(RE4DC_ATCHK_CACHE) && RE4DC_ATCHK_CACHE
// GAME_ATCHK_CACHE (game30.mk; G, collision traversal; exact): each list's collected bodies are kept and
// reused while the list (its generation, head and length) is unchanged. Every write that changes a body's
// test is noted (atariInfo.h); a reuse first applies each info noted since the last one: a kept body whose
// test now fails is removed, a list body whose test now passes is inserted at its list position (the kept
// bodies before it in list order). The list is unchanged and every other body's test is what it was, so
// the kept bodies are the list's bodies that pass their test, in list order: what a fresh collection
// returns. A noted info outside the list's body info addresses (atListBuild: lowest .. highest) is no
// body of the list and is skipped. Dead Ganados leave the enemy alive list but keep running their move,
// and em10SlopeMove / atari.move flip their m_radius2 test twice a tick. The optional distinct-note
// path coalesces those writes and checks exact list membership before reading a body. A kept list that
// would overflow is collected afresh. The default ring path retains its
// own absent set per list generation and recollects after more than 64 historical writes.
// =2 (check build): every reuse is also collected afresh and compared, the fresh one used ("ATC" lines:
// skip = notes outside the range, ins / del = bodies applied, list / ring / full = collections afresh by
// reason; known is default-ring absent reuse, and distinct_overflow is a distinct-reader refusal).
#if defined(RE4DC_ATCHK_DISTINCT29) && RE4DC_ATCHK_DISTINCT29
// One entry per distinct info since either reader's last successful query. A reader's
// pending bit is never cleared by the other reader. If the fixed table fills, only
// readers represented by the selected victim are invalidated; their next query
// recollects from the current source list. No sequence counter can wrap here.
#define ATC_DIRTY_MAX 64
#define ATC_EM 1
#define ATC_OBJ 2
static const void* atcDirtyInfo[ATC_DIRTY_MAX];
static u8 atcDirtyPending[ATC_DIRTY_MAX];
static u8 atcDirtyN;
static u8 atcDirtyInvalid;
static void atcDirtyDrop(u8 readers)
{
    atcDirtyInvalid |= readers;
    int kept = 0;
    for (int i = 0; i < atcDirtyN; i++) {
        const u8 pending = atcDirtyPending[i] & ~readers;
        if (pending != 0) {
            atcDirtyInfo[kept] = atcDirtyInfo[i];
            atcDirtyPending[kept++] = pending;
        }
    }
    atcDirtyN = kept;
}
static void atcDirtyConsumed(u8 reader)
{
    int kept = 0;
    for (int i = 0; i < atcDirtyN; i++) {
        const u8 pending = atcDirtyPending[i] & ~reader;
        if (pending != 0) {
            atcDirtyInfo[kept] = atcDirtyInfo[i];
            atcDirtyPending[kept++] = pending;
        }
    }
    atcDirtyN = kept;
    atcDirtyInvalid &= ~reader;
}
extern "C" void re4dcAtariNoteDistinct29(const void* info)
{
    u8 readers = (u8) (3 & ~atcDirtyInvalid);
    if (readers == 0) {
        return;  // both readers must recollect; later writes are included there
    }
    for (int i = 0; i < atcDirtyN; i++) {
        if (atcDirtyInfo[i] == info) {
            atcDirtyPending[i] |= readers;
            return;
        }
    }
    if (atcDirtyN == ATC_DIRTY_MAX) {
        // Prefer evicting one reader's history. A victim pending for both
        // requires both to recollect; no old state is applied after refusal.
        u8 victim = atcDirtyPending[0];
        for (int i = 1; i < atcDirtyN; i++) {
            if (atcDirtyPending[i] != 3) {
                victim = atcDirtyPending[i];
                break;
            }
        }
        atcDirtyDrop(victim);
        readers = (u8) (3 & ~atcDirtyInvalid);
        if (readers == 0) {
            return;
        }
    }
    atcDirtyInfo[atcDirtyN] = info;
    atcDirtyPending[atcDirtyN++] = readers;
}
#else
extern "C" {
u32 re4dc_atari_seq;
const void* re4dc_atari_dirty[64];
}
#endif
#if !defined(RE4DC_ATCHK_DISTINCT29) || !RE4DC_ATCHK_DISTINCT29
#define ATC_ABSENT 8
#endif
struct AtCand {
    u32 listGen;
#if !defined(RE4DC_ATCHK_DISTINCT29) || !RE4DC_ATCHK_DISTINCT29
    u32 seq;
#endif
    cEm* head;
    int N;
    int n;   /* -1: nothing kept */
#if defined(RE4DC_ATCHK_DISTINCT29) && RE4DC_ATCHK_DISTINCT29
    u8 consumer;
#else
    int nAbsent;
    const cAtariInfo* absent[ATC_ABSENT];   /* noted infos of the range found absent from the list */
#endif
    cEm* v[ATCHK_MAX];
};
#if defined(RE4DC_ATCHK_DISTINCT29) && RE4DC_ATCHK_DISTINCT29
static AtCand atCandEm = { 0, 0, 0, -1, ATC_EM }, atCandObj = { 0, 0, 0, -1, ATC_OBJ };
static_assert(sizeof(void*) != 4 || (sizeof(u32) == 4 && sizeof(AtCand) == 404),
              "distinct candidate cache footprint on a 32-bit target");
#else
static AtCand atCandEm = { 0, 0, 0, 0, -1 }, atCandObj = { 0, 0, 0, 0, -1 };
#endif
#if RE4DC_ATCHK_CACHE == 2
extern "C" void re4dc_log(const char* fmt, ...);
#if defined(RE4DC_ATCHK_DISTINCT29) && RE4DC_ATCHK_DISTINCT29
static u32 atcHit, atcMiss, atcMis, atcNoted, atcSkip, atcList, atcRing, atcFull, atcIns, atcDel, atcAbsent;
#else
static u32 atcHit, atcMiss, atcMis, atcNoted, atcSkip, atcList, atcRing, atcFull, atcIns, atcDel, atcAbsent,
    atcKnown;
#endif
#endif
// Applies each currently relevant note to the kept list (1), or requests fresh
// collection (0) after a bounded-storage refusal or a full candidate list.
static int atchkNotedApply(AtCand* C, const AtList* L)
{
#if defined(RE4DC_ATCHK_DISTINCT29) && RE4DC_ATCHK_DISTINCT29
    if (atcDirtyInvalid & C->consumer) {
#if RE4DC_ATCHK_CACHE == 2
        ++atcRing;
#endif
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
        re4dc::fa35::hit(re4dc::fa35::CollisionDirtyOverflow, 1);
#endif
        return 0;
    }
    for (int d = 0; d < atcDirtyN; d++) {
        if (!(atcDirtyPending[d] & C->consumer)) {
            continue;
        }
        const cAtariInfo* a = (const cAtariInfo*) atcDirtyInfo[d];
        if ((u32) a - L->lo > L->span) {
#if RE4DC_ATCHK_CACHE == 2
            ++atcSkip;
#endif
            continue;
        }
        // A range is only a filter. Do not dereference a retired or unowned
        // address until an exact member of this list supplies its live owner.
        int i = 0;
        while (i < L->n && &L->v[i]->atari != a) {
            i++;
        }
        if (i == L->n) {
#if RE4DC_ATCHK_CACHE == 2
            ++atcAbsent;
#endif
            // The current AtList is bound to the same manager generation,
            // head and length as C. This address is proven absent until that
            // identity changes; never dereference an unowned info.
            continue;
        }
        cEm* m = L->v[i];
        int k = 0;
        while (k < C->n && C->v[k] != m) {
            k++;
        }
        const int live = (m->atari.m_flag & 0x200) && m->atari.m_radius2 != 0.0f;
        if (live == (k < C->n)) {
#if RE4DC_ATCHK_CACHE == 2
            ++atcNoted;
#endif
            continue;
        }
        if (!live) {
            C->n--;
            for (; k < C->n; k++) {
                C->v[k] = C->v[k + 1];
            }
#if RE4DC_ATCHK_CACHE == 2
            ++atcDel;
#endif
            continue;
        }
        if (C->n == ATCHK_MAX) {
#if RE4DC_ATCHK_CACHE == 2
            ++atcFull;
#endif
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
            re4dc::fa35::hit(re4dc::fa35::CollisionCandidateOverflow, 1);
#endif
            return 0;
        }
        // Count cached candidates before the newly eligible body in source
        // order, then insert at that position. Equality and ties stay exact.
        k = 0;
        for (int j = 0; j < i; j++) {
            if (k < C->n && L->v[j] == C->v[k]) {
                k++;
            }
        }
        for (int j = C->n; j > k; j--) {
            C->v[j] = C->v[j - 1];
        }
        C->v[k] = m;
        C->n++;
#if RE4DC_ATCHK_CACHE == 2
        ++atcIns;
#endif
    }
    return 1;
#else
    const u32 e = re4dc_atari_seq;
    u32 s = C->seq;
    if (e - s > 64) {
#if RE4DC_ATCHK_CACHE == 2
        ++atcRing;
#endif
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
        re4dc::fa35::hit(re4dc::fa35::CollisionDirtyOverflow, 1);
#endif
#line 348
        return 0;
    }
    const u32 lo = L->lo;
    const u32 span = L->span;
    for (; s != e; s++) {
        const cAtariInfo* a = (const cAtariInfo*) re4dc_atari_dirty[s & 63];
        if ((u32) a - lo > span) {
#if RE4DC_ATCHK_CACHE == 2
            ++atcSkip;
#endif
            continue;
        }
        int k = 0;
        while (k < C->n && &C->v[k]->atari != a) {
            k++;
        }
        if (k == C->n) {
            int x = 0;
            while (x < C->nAbsent && C->absent[x] != a) {
                x++;
            }
            if (x < C->nAbsent) {   // absent from the list
#if RE4DC_ATCHK_CACHE == 2
                ++atcKnown;
#endif
                continue;
            }
        }
        const int live = (a->m_flag & 0x200) && a->m_radius2 != 0.0f;
        if (live == (k < C->n)) {
#if RE4DC_ATCHK_CACHE == 2
            ++atcNoted;
#endif
            continue;
        }
        if (!live) {   // kept, its test now fails: remove it
            C->n--;
            for (; k < C->n; k++) {
                C->v[k] = C->v[k + 1];
            }
#if RE4DC_ATCHK_CACHE == 2
            ++atcDel;
#endif
            continue;
        }
        // not kept, its test now passes: insert it after the kept bodies that precede it in the list
        if (C->n == ATCHK_MAX) {
#if RE4DC_ATCHK_CACHE == 2
            ++atcFull;
#endif
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
            re4dc::fa35::hit(re4dc::fa35::CollisionCandidateOverflow, 1);
#endif
#line 398
            return 0;
        }
        cEm* const* v = L->v;
        const int N = L->n;
        int i = 0;
        k = 0;
        for (; i < N && &v[i]->atari != a; i++) {
            if (k < C->n && v[i] == C->v[k]) {
                k++;
            }
        }
        if (i == N) {   // in the range, not in the list: remembered for this list
            if (C->nAbsent < ATC_ABSENT) {
                C->absent[C->nAbsent++] = a;
            }
#if RE4DC_ATCHK_CACHE == 2
            ++atcAbsent;
#endif
            continue;
        }
        for (int j = C->n; j > k; j--) {
            C->v[j] = C->v[j - 1];
        }
        C->v[k] = v[i];
        C->n++;
#if RE4DC_ATCHK_CACHE == 2
        ++atcIns;
#endif
    }
    C->seq = e;
    return 1;
#endif
}
static int atchkCandidates(AtCand* C, AtList* L, cEm* head, u32 gen, cEm** out)
{
    const int N = atListSync(L, head, gen);
    if (N < 0) {
        C->n = -1;
        return atchkCollect(head, out);
    }
    const int same = C->n >= 0 && C->listGen == gen && C->head == head && C->N == N;
#if RE4DC_ATCHK_CACHE == 2
    if (!same) {
        ++atcList;
    }
#endif
    if (same && atchkNotedApply(C, L)) {
#if RE4DC_ATCHK_CACHE == 2
        const int f = atchkCollectList(L, N, out);
        ++atcHit;
        if (f != C->n || __builtin_memcmp(out, C->v, (f > 0 ? f : 0) * sizeof(cEm*)) != 0) {
            ++atcMis;
            C->n = -1;
        }
#if defined(RE4DC_ATCHK_DISTINCT29) && RE4DC_ATCHK_DISTINCT29
        if (C->n >= 0) {
            atcDirtyConsumed(C->consumer);
        }
#endif
        if ((atcHit + atcMiss) % 8192 == 0) {
#if defined(RE4DC_ATCHK_DISTINCT29) && RE4DC_ATCHK_DISTINCT29
            re4dc_log("ATC hit=%u miss=%u mismatch=%u noted=%u skip=%u ins=%u del=%u absent=%u "
                      "list=%u distinct_overflow=%u full=%u pending=%u invalid=%u\n", atcHit, atcMiss, atcMis,
                      atcNoted, atcSkip, atcIns, atcDel, atcAbsent, atcList, atcRing, atcFull,
                      (u32) atcDirtyN, (u32) atcDirtyInvalid);
#else
            re4dc_log("ATC hit=%u miss=%u mismatch=%u noted=%u skip=%u ins=%u del=%u absent=%u known=%u list=%u "
                      "ring=%u full=%u seq=%u\n", atcHit, atcMiss, atcMis, atcNoted, atcSkip, atcIns, atcDel,
                      atcAbsent, atcKnown, atcList, atcRing, atcFull, re4dc_atari_seq);
#endif
        }
        return f;
#else
        __builtin_memcpy(out, C->v, C->n * sizeof(cEm*));
#if defined(RE4DC_ATCHK_DISTINCT29) && RE4DC_ATCHK_DISTINCT29
        atcDirtyConsumed(C->consumer);
#endif
        return C->n;
#endif
    }
    const int n = atchkCollectList(L, N, out);
#if RE4DC_ATCHK_CACHE == 2
    ++atcMiss;
#endif
    C->n = n;
    if (n >= 0) {
        C->listGen = gen;
#if defined(RE4DC_ATCHK_DISTINCT29) && RE4DC_ATCHK_DISTINCT29
        atcDirtyConsumed(C->consumer);
#else
        C->seq = re4dc_atari_seq;
#endif
        C->head = head;
        C->N = N;
#if !defined(RE4DC_ATCHK_DISTINCT29) || !RE4DC_ATCHK_DISTINCT29
        C->nAbsent = 0;
#endif
        __builtin_memcpy(C->v, out, n * sizeof(cEm*));
    }
    return n;
}
static int atchkCollectEm(cEm** out)
{
    return atchkCandidates(&atCandEm, &atListEm, EmMgr.pAlive, re4dc_alive_gen[1], out);
}
static int atchkCollectObj(cEm** out)
{
    return atchkCandidates(&atCandObj, &atListObj, (cEm*) ObjMgr.pAlive, re4dc_alive_gen[2], out);
}
#else
static int atchkCollectEm(cEm** out)
{
    int N = atListSync(&atListEm, EmMgr.pAlive, re4dc_alive_gen[1]);
    return N < 0 ? atchkCollect(EmMgr.pAlive, out) : atchkCollectList(&atListEm, N, out);
}
static int atchkCollectObj(cEm** out)
{
    int N = atListSync(&atListObj, (cEm*) ObjMgr.pAlive, re4dc_alive_gen[2]);
    return N < 0 ? atchkCollect((cEm*) ObjMgr.pAlive, out) : atchkCollectList(&atListObj, N, out);
}
#endif
#else
#define atchkCollectEm(v) atchkCollect(EmMgr.pAlive, v)
#define atchkCollectObj(v) atchkCollect((cEm*) ObjMgr.pAlive, v)
#endif
static void atchkPasses(cEm* em, cEm** v, int n)
{
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
    re4dc::fa35::hit(re4dc::fa35::CollisionFast, 1);
#endif
#line 503
    int i;
    for (i = 0; i < n; i++) {
        v[i]->atari.getPos(v[i], &v[i]->atari.m_Pos);
    }
    for (i = 0; i < n; i++) {
        if (v[i] != em) {
            __em_at_core(em, v[i]);
        }
    }
    for (i = 0; i < n; i++) {
        v[i]->atari.m_oldPos = v[i]->atari.m_Pos;
    }
}
#endif
void EmAtCheck(cEm* em)
{
    cEm* m;

    if (!(em->atari.m_flag & 0x200) || em->atari.m_radius2 == 0.0f) {
        em->atari.m_stat |= 1;
        return;
    }
    em->atari.getPos(em, &em->atari.m_Pos);
#if defined(RE4DC_ATCHK) && RE4DC_ATCHK
    {
        cEm* v[ATCHK_MAX];
        int n = atchkCollectEm(v);
        if (n >= 0) {
            atchkPasses(em, v, n);
            n = atchkCollectObj(v);
            if (n >= 0) {
                atchkPasses(em, v, n);
                PartsWorldPosCalc(em);
                em->atari.m_stat &= ~1;
                return;
            }
            goto objects;   /* ems done; objects overflow the array: original object passes */
        }
    }
#endif
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
    re4dc::fa35::hit(re4dc::fa35::CollisionSource, 1);
#endif
#line 543
    for (m = EmMgr.pAlive; m != 0; m = (cEm*) m->pNext) {
        if ((m->atari.m_flag & 0x200) && m->atari.m_radius2 != 0.0f) {
            m->atari.getPos(m, &m->atari.m_Pos);
        }
    }
    for (m = EmMgr.pAlive; m != 0; m = (cEm*) m->pNext) {
        if ((m->atari.m_flag & 0x200) && m != em && m->atari.m_radius2 != 0.0f) {
            __em_at_core(em, m);
        }
    }
    for (m = EmMgr.pAlive; m != 0; m = (cEm*) m->pNext) {
        if ((m->atari.m_flag & 0x200) && m->atari.m_radius2 != 0.0f) {
            m->atari.m_oldPos = m->atari.m_Pos;
        }
    }
#if defined(RE4DC_ATCHK) && RE4DC_ATCHK
objects:
#endif
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
    re4dc::fa35::hit(re4dc::fa35::CollisionSource, 1);
#endif
#line 561
    for (m = (cEm*) ObjMgr.pAlive; m != 0; m = (cEm*) m->pNext) {
        if ((m->atari.m_flag & 0x200) && m->atari.m_radius2 != 0.0f) {
            m->atari.getPos(m, &m->atari.m_Pos);
        }
    }
    for (m = (cEm*) ObjMgr.pAlive; m != 0; m = (cEm*) m->pNext) {
        if ((m->atari.m_flag & 0x200) && m != em && m->atari.m_radius2 != 0.0f) {
            __em_at_core(em, m);
        }
    }
    for (m = (cEm*) ObjMgr.pAlive; m != 0; m = (cEm*) m->pNext) {
        if ((m->atari.m_flag & 0x200) && m->atari.m_radius2 != 0.0f) {
            m->atari.m_oldPos = m->atari.m_Pos;
        }
    }
    PartsWorldPosCalc(em);
    em->atari.m_stat &= ~1;
}

// 1 when pMod's push priority (m_flag bits 3-4) is non-zero and not below pMod2's, i.e. pMod is
// not the one to be pushed.
static int priorityCheck(cEm* pMod, cEm* pMod2)
{
    u8 pa = pMod->atari.m_flag & 0x18;
    u8 pb = pMod2->atari.m_flag & 0x18;

    if (pa != 0 && pa >= pb) {
        return 1;
    }
    return 0;
}

// Pushes pMod out of pMod2 unless priority says otherwise, choosing the box-box, sphere-box or
// sphere-sphere test by the bodies' m_flag bit1.
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
// GAME_DECISION_TRACE (test builds): every em-em collision result, in call order (logic_trace.cpp).
extern "C" unsigned re4dc_dt_note(unsigned kind, unsigned a, unsigned b);
#define DT_EM(a, b, r) re4dc_dt_note(0, ((u32) (a)->id << 8) | (b)->id, (u32) (r))
#else
#define DT_EM(a, b, r) (r)
#endif
void __em_at_core(cEm* pMod, cEm* pMod2)
{
    if (priorityCheck(pMod, pMod2) == 1) {
        DT_EM(pMod, pMod2, 0x10000);
        return;
    }
    if (pMod->atari.m_flag & 2) {
        if (pMod2->atari.m_flag & 2) {
            DT_EM(pMod, pMod2, At_em_rect_rect_ck(pMod, pMod2));
        } else {
            DT_EM(pMod2, pMod, At_em_sphere_rect_ck(pMod2, pMod));
        }
    } else {
        if (pMod2->atari.m_flag & 2) {
            DT_EM(pMod, pMod2, At_em_sphere_rect_ck(pMod, pMod2));
        } else {
            DT_EM(pMod, pMod2, At_em_sphere_sphere_ck(pMod, pMod2));
        }
    }
}

// Box vs box (both yaw-aligned): when the XZ boxes overlap, the moving one is pushed out along
// the axis it moved on (x or z), the other when pMod has priority. 1 when pMod moved >= 1 unit.
int At_em_rect_rect_ck(cEm* pMod, cEm* pMod2)
{
    Vec ra;
    Vec rb;
    Vec posA;
    f32 aw;
    f32 ad;
    f32 bw;
    f32 bd;
    u8 pa;
    u8 pb;
    int ret;

    ret = em_rect2_ck_sub(pMod, pMod2);
    if (ret != 0) {
    posA = pMod->pos;
    if (!(Get_ang_dir(pMod->ang.y) & 1)) {
        aw = pMod->atari.m_radius;
        ad = pMod->atari.m_radius2;
    } else {
        aw = pMod->atari.m_radius2;
        ad = pMod->atari.m_radius;
    }
    RotVector(&pMod->atari.m_offset, &pMod->ang, &ra);
    if (!(Get_ang_dir(pMod2->ang.y) & 1)) {
        bw = pMod2->atari.m_radius;
        bd = pMod2->atari.m_radius2;
    } else {
        bw = pMod2->atari.m_radius2;
        bd = pMod2->atari.m_radius;
    }
    RotVector(&pMod2->atari.m_offset, &pMod2->ang, &rb);
    pa = pMod->atari.m_flag & 0x18;
    pb = pMod2->atari.m_flag & 0x18;
    if (pa > pb || (pa == 0 && pb == 0)) {
        if (pMod->pos.x != pMod->pos_old.x) {
            f32 ax = pMod->pos.x + ra.x;
            f32 bx = pMod2->pos.x + rb.x;
            if (ax < bx) {
                pMod2->pos.x = ax + aw + bw + 1.0f - rb.x;
            } else {
                pMod2->pos.x = ax - aw - bw - 1.0f - rb.x;
            }
        } else if (pMod->pos.z != pMod->pos_old.z) {
            f32 az = pMod->pos.z + ra.z;
            f32 bz = pMod2->pos.z + rb.z;
            if (az > bz) {
                pMod2->pos.z = pMod->pos.z + rb.z + ad + bd + 1.0f - rb.z;
            } else {
                pMod2->pos.z = pMod->pos.z + rb.z - ad - bd - 1.0f - rb.z;
            }
        }
    } else if (pa != pb) {
        if (pMod->pos.x != pMod->pos_old.x) {
            f32 ax = pMod->pos.x + ra.x;
            f32 bx = pMod2->pos.x + rb.x;
            if (ax > bx) {
                pMod->pos.x = bx + bw + aw + 1.0f - ra.x;
            } else {
                pMod->pos.x = bx - bw - aw - 1.0f - ra.x;
            }
        } else if (pMod->pos.z != pMod->pos_old.z) {
            f32 az = pMod->pos.z + ra.z;
            f32 bz = pMod2->pos.z + rb.z;
            if (az > bz) {
                pMod->pos.z = bz + bd + ad + 1.0f - ra.z;
            } else {
                pMod->pos.z = bz - bd - ad - 1.0f - ra.z;
            }
        }
    }
    if (fabsf(pMod->pos.x - posA.x) >= 1.0f || fabsf(pMod->pos.z - posA.z) >= 1.0f) {
        ret = 1;
    } else {
        ret = 0;
    }
    }
    return ret;
}

// Box vs box with rotation: tests pMod's four corners against pMod2's box and pushes it out of
// the deepest one.
int em_rect2_ck_sub(cEm* pMod, cEm* pMod2)
{
    Vec v;
    Vec ra[4];
    Vec rb[4];
    cAtariInfo* ia = &pMod->atari;
    cAtariInfo* ib = &pMod2->atari;
    int ret;

    {
        f32 rx = ia->m_radius;
        f32 rz = ia->m_radius2;
        v.x = rx;
        v.y = 0.0f;
        v.z = rz;
        PSVECAdd(&v, &ia->m_offset, &v);
        RotVector(&v, &pMod->ang, &v);
        PSVECAdd(&v, &pMod->pos, &ra[0]);
        v.x = rx;
        v.y = 0.0f;
        v.z = -rz;
        PSVECAdd(&v, &ia->m_offset, &v);
        RotVector(&v, &pMod->ang, &v);
        PSVECAdd(&v, &pMod->pos, &ra[1]);
        v.x = -rx;
        v.y = 0.0f;
        v.z = -rz;
        PSVECAdd(&v, &ia->m_offset, &v);
        RotVector(&v, &pMod->ang, &v);
        PSVECAdd(&v, &pMod->pos, &ra[2]);
        v.x = -rx;
        v.y = 0.0f;
        v.z = rz;
        PSVECAdd(&v, &ia->m_offset, &v);
        RotVector(&v, &pMod->ang, &v);
        PSVECAdd(&v, &pMod->pos, &ra[3]);
    }
    {
        f32 rx = ib->m_radius;
        f32 rz = ib->m_radius2;
        v.x = rx;
        v.y = 0.0f;
        v.z = rz;
        PSVECAdd(&v, &ib->m_offset, &v);
        RotVector(&v, &pMod2->ang, &v);
        PSVECAdd(&v, &pMod2->pos, &rb[0]);
        v.x = rx;
        v.y = 0.0f;
        v.z = -rz;
        PSVECAdd(&v, &ib->m_offset, &v);
        RotVector(&v, &pMod2->ang, &v);
        PSVECAdd(&v, &pMod2->pos, &rb[1]);
        v.x = -rx;
        v.y = 0.0f;
        v.z = -rz;
        PSVECAdd(&v, &ib->m_offset, &v);
        RotVector(&v, &pMod2->ang, &v);
        PSVECAdd(&v, &pMod2->pos, &rb[2]);
        v.x = -rx;
        v.y = 0.0f;
        v.z = rz;
        PSVECAdd(&v, &ib->m_offset, &v);
        RotVector(&v, &pMod2->ang, &v);
        PSVECAdd(&v, &pMod2->pos, &rb[3]);
    }
    if (fabsf(ra[0].y - rb[0].y) > ia->m_height + ib->m_height) {
        ret = 0;
    } else if (At_rect_rect_ck(ra, rb) != 0) {
        ret = 1;
    } else {
        ret = 0;
    }
    return ret;
}

#if defined(RE4DC_ATRECT_FAR) && RE4DC_ATRECT_FAR
// GAME_ATRECT_FAR (game30.mk; G, em-em collision; decision-exact): __em_at_core has no distance test, so
// At_em_sphere_rect_ck builds the box frame (RotRad, MultVec, PSMTXInverse) for every sphere / box pair
// whose heights overlap, however far apart. A hit needs a step point p (local xz, on the segment from
// the old to the new position, n accumulated steps) with |p.x| < rx + rad and |p.z| < rz (or the swap),
// or within |rad| of a corner (GetDistance is squared): |p.x|, |p.z| <= |rx| + |rz| + |rad| = h. The
// frame is a y rotation about c = R off + c0 (c0 the parts / model position), so a hit point lies within
// |off.x| + |off.z| + 2h of c0 in x and in z (world). When both ends of the segment are further than that
// plus a margin (64 + 1/1024 of the coordinates' magnitude: ~1000x the rotation, inverse and n-step
// rounding, n <= 5001 as a move over 1e6 units is not rejected) on one side in x or z, the original
// returns 0 with no write: the call returns 0 before building the frame. NaN / inf anywhere: no reject.
// =2 (check build): the original runs every time; a rejected call that hits is counted ("ARF" lines).
static inline int arfFar(cEm* sph, cEm* rect, const Vec* pr)
{
    const cAtariInfo* ir = &rect->atari;
    const Vec* c0 = ir->m_parts_no != 0 ? pr : &rect->pos;
    const Vec* p = &sph->atari.m_Pos;
    const Vec* o = &sph->atari.m_oldPos;
    const f32 h = fabsf(ir->m_radius) + fabsf(ir->m_radius2) + fabsf(sph->atari.m_radius);
    const f32 mag = fabsf(c0->x) + fabsf(c0->z) + fabsf(p->x) + fabsf(p->z) + fabsf(o->x) + fabsf(o->z);
    const f32 mv = fabsf(p->x - o->x) + fabsf(p->y - o->y) + fabsf(p->z - o->z);
    const f32 b = fabsf(ir->m_offset.x) + fabsf(ir->m_offset.z) + 2.0f * h + 64.0f + mag * (1.0f / 1024.0f);
    const f32 xl = c0->x - b;
    const f32 xh = c0->x + b;
    const f32 zl = c0->z - b;
    const f32 zh = c0->z + b;

    if (!(mv < 1.0e6f)) {
        return 0;
    }
    return (p->x < xl && o->x < xl) || (p->x > xh && o->x > xh) || (p->z < zl && o->z < zl) || (p->z > zh && o->z > zh);
}
#if RE4DC_ATRECT_FAR == 2
extern "C" void re4dc_log(const char* fmt, ...);
static u32 arfCalls, arfFarN, arfMis;
#endif
#endif
// Sphere (character) vs box (object): with overlapping heights pushes the sphere out of the box
// along the nearest face (sphereRectCk in the box's yaw frame); 1 on contact.
int At_em_sphere_rect_ck(cEm* sph, cEm* rect)
{
    Vec ps;
    Vec pr;
    Mtx m;
    Mtx inv;
    Vec c;
    Vec step;
    Vec p;
    Vec q;
    cAtariInfo* ir;
    f32 rad;
    int n;
    int i;
    int hit;

    ps = sph->atari.m_Pos;
    pr = rect->atari.m_Pos;
    if (ps.y + sph->atari.m_height < pr.y - rect->atari.m_height) {
        return 0;
    }
    if (ps.y - sph->atari.m_height > pr.y + rect->atari.m_height) {
        return 0;
    }
#if defined(RE4DC_ATRECT_FAR) && RE4DC_ATRECT_FAR
#if RE4DC_ATRECT_FAR == 2
    const int arfF = arfFar(sph, rect, &pr);
#else
    if (arfFar(sph, rect, &pr)) {
        return 0;
    }
#endif
#endif
    ir = &rect->atari;
    if (ir->m_parts_no != 0) {
        cModel* pm = rect->getPartsPtr(ir->m_parts_no - 1);
        PSMTXRotRad(m, 'y', pm->ang.y);
        PSMTXMultVecSR(m, &ir->m_offset, &c);
        PSVECAdd(&c, &pr, &c);
        TransMatrix(m, &c);
    } else {
        PSMTXRotRad(m, 'y', rect->ang.y);
        TransMatrix(m, &rect->pos);
        PSMTXMultVec(m, &ir->m_offset, &c);
        m[0][3] = c.x;
        m[1][3] = c.y;
        m[2][3] = c.z;
    }
    PSMTXInverse(m, inv);
    c = sph->atari.m_Pos;
    rad = sph->atari.m_radius;
    if (!(sph->atari.m_stat & 1)) {
        RE4DC_XM_LOAD(inv);
        RE4DC_XM_POINT(inv, &sph->atari.m_Pos, &step);
        RE4DC_XM_POINT(inv, &sph->atari.m_oldPos, &p);
        if (rad >= 200.0f) {
            n = (int) (GetDistance3(&step, &p) / rad) + 1;
        } else {
            n = 1;
        }
        PSVECSubtract(&step, &p, &step);
        PSVECScale(&step, &step, 1.0f / (f32) n);
    } else {
        PSMTXMultVec(inv, &sph->atari.m_Pos, &p);
        n = 1;
        step.x = 0.0f;
        step.y = 0.0f;
        step.z = 0.0f;
    }
    hit = 0;
    for (i = 0; i < n; i++) {
        PSVECAdd(&p, &step, &p);
        hit = sphereRectCk(ir, &p, rad);
        if (hit != 0) {
            break;
        }
    }
    if (hit != 0) {
        p.y = c.y;
        PSMTXMultVec(m, &p, &q);
        PSVECSubtract(&q, &c, &q);
        q.y = 0.0f;
        PSVECAdd(&sph->pos, &q, &sph->pos);
        sph->atari.getPos(sph, &sph->atari.m_Pos);
    }
#if defined(RE4DC_ATRECT_FAR) && RE4DC_ATRECT_FAR == 2
    if (arfF) {
        ++arfFarN;
        if (hit != 0) {
            ++arfMis;
        }
    }
    if (++arfCalls % 4096 == 0) {
        re4dc_log("ARF calls=%u far=%u mismatch=%u\n", arfCalls, arfFarN, arfMis);
    }
#endif
    return hit;
}

// Sphere of radius `rad` at box-space point `p` against the box `info`: moves *p to the nearest
// face; 1 when it was inside.
static int sphereRectCk(cAtariInfo* info, Vec* p, f32 rad)
{
    Vec corner;
    Vec d;
    f32 rx = info->m_radius;
    f32 rz = info->m_radius2;
    f32 rr;
    int hit = 0;

    if (p->z > -rz && p->z < rz) {
        if (p->x > 0.0f) {
            if (p->x < rx + rad) {
                p->x = rx + rad;
                hit = 1;
            }
        } else {
            if (p->x > -(rx + rad)) {
                p->x = -(rx + rad);
                hit = 1;
            }
        }
    }
    if (p->x > -rx && p->x < rx) {
        if (p->z > 0.0f) {
            if (p->z < rz + rad) {
                p->z = rz + rad;
                hit = 1;
            }
        } else {
            if (p->z > -(rz + rad)) {
                p->z = -(rz + rad);
                hit = 1;
            }
        }
    }
    if (hit == 0) {
        corner.x = rx;
        corner.y = 0.0f;
        corner.z = rz;
        p->y = 0.0f;
        rr = rad * rad;
        if (GetDistance(&corner, p) < rr) {
            PSVECSubtract(p, &corner, &d);
#line 788 "D:/Bio4/Prog/at_mod.cpp"
            VECNormalize(&d, &d);
            PSVECScale(&d, &d, rad);
            hit = 1;
            PSVECAdd(&corner, &d, p);
        } else {
            corner.x = -rx;
            corner.y = 0.0f;
            corner.z = rz;
            if (GetDistance(&corner, p) < rr) {
                PSVECSubtract(p, &corner, &d);
#line 797 "D:/Bio4/Prog/at_mod.cpp"
                VECNormalize(&d, &d);
                PSVECScale(&d, &d, rad);
                hit = 1;
                PSVECAdd(&corner, &d, p);
            } else {
                corner.x = rx;
                corner.y = 0.0f;
                corner.z = -rz;
                if (GetDistance(&corner, p) < rr) {
                    PSVECSubtract(p, &corner, &d);
#line 806 "D:/Bio4/Prog/at_mod.cpp"
                    VECNormalize(&d, &d);
                    PSVECScale(&d, &d, rad);
                    hit = 1;
                    PSVECAdd(&corner, &d, p);
                } else {
                    corner.x = -rx;
                    corner.y = 0.0f;
                    corner.z = -rz;
                    if (GetDistance(&corner, p) < rr) {
                        PSVECSubtract(p, &corner, &d);
#line 815 "D:/Bio4/Prog/at_mod.cpp"
                        VECNormalize(&d, &d);
                        PSVECScale(&d, &d, rad);
                        hit = 1;
                        PSVECAdd(&corner, &d, p);
                    }
                }
            }
        }
    }
    return hit;
}

// Cylinder vs cylinder: with overlapping heights and XZ distance below the radii sum, pushes
// pMod (and its m_pMod companion, or pMod2's) apart by the overlap; 1 on contact.
int At_em_sphere_sphere_ck(cEm* pMod, cEm* pMod2)
{
    Vec pa;
    Vec pb;
    Vec d;
    const f32 rate = 0.3f;
    f32 hh;
    f32 dist;
    f32 rr;
    cModel* m;

    pa = pMod->atari.m_Pos;
    pb = pMod2->atari.m_Pos;
    hh = pMod->atari.m_height + pMod2->atari.m_height;
    if (pa.y < pb.y - hh) {
        return 0;
    }
    if (pa.y > pb.y + hh) {
        return 0;
    }
    PSVECSubtract(&pb, &pa, &d);
    d.y = 0.0f;
    dist = RootSumSquare3(&d);
    rr = pMod->atari.m_radius2 + pMod2->atari.m_radius2;
    if (dist < rr) {
        if (dist < 0.1f) {
            d.x += 0.1f;
        }
#line 869 "D:/Bio4/Prog/at_mod.cpp"
        VECNormalize(&d, &d);
        PSVECScale(&d, &d, rr - dist);
        PSVECSubtract(&pMod->pos, &d, &pMod->pos);
        pMod->atari.getPos(pMod, &pMod->atari.m_Pos);
        if (pMod->atari.m_pMod != 0) {
            m = pMod->atari.m_pMod;
            PSVECSubtract(&m->pos, &d, &m->pos);
            ((cEm*) m)->atari.getPos(m, &((cEm*) m)->atari.m_Pos);
        }
        if ((pMod2->atari.m_flag & 0x18) == 0 && (u32) pMod2 > (u32) pMod) {
            PSVECScale(&d, &d, rate);
            PSVECAdd(&pMod2->pos, &d, &pMod2->pos);
            pMod2->atari.getPos(pMod2, &pMod2->atari.m_Pos);
            if (pMod2->atari.m_pMod != 0) {
                m = pMod2->atari.m_pMod;
                PSVECAdd(&m->pos, &d, &m->pos);
                ((cEm*) m)->atari.getPos(m, &((cEm*) m)->atari.m_Pos);
            }
        }
        return 1;
    }
    return 0;
}

// Dead-stripped by the original linker: only its constant pool (a double 0.0) survives in .rodata
// between At_em_sphere_sphere_ck's and EmHitCheck's pools. Body unknown.
static int atModIsZero(f32 x)
{
    return x == 0.0;
}

// Line pos0 -> pos1 against every collidable character body (the player only with flag bit2):
// nearest hit and normal; 1 when hit. The camera uses it to keep characters in view.
#if defined(RE4DC_EMHIT_LIST) && RE4DC_EMHIT_LIST
// GAME_EMHIT_LIST (game30.mk; G, camera line vs characters; exact; needs GAME_ATCHK_LIST=1): EmHitCheck walks
// GAME_ATCHK_LIST's array of EmMgr's alive list (same bodies, same order: the nearest-hit ties resolve as
// before) with the bodies' cAtariInfo lines prefetched ahead instead of chasing pNext, and skips the
// ComnHitCheck call for a body without a box (m_flag bit 1) when the caller's flag has no bit 1: there
// ComnHitCheck only writes its own local hit point and returns 0. =2 (check build): the array is compared
// with the list and every skipped call is made and must return 0 ("EHL" lines).
#if RE4DC_EMHIT_LIST == 2
extern "C" void re4dc_log(const char* fmt, ...);
static u32 ehlCalls, ehlSkip, ehlMis;
#endif
#endif
int EmHitCheck(Vec* hit, Vec* nrm, Vec* pos0, Vec* pos1, int flag)
{
    Vec h;
    Vec n;
    f32 dist = 100000.0f;
    f32 d;
    int ret = 0;
    cEm* m;

    if (hit != 0) {
        *hit = *pos1;
    }
#if defined(RE4DC_EMHIT_LIST) && RE4DC_EMHIT_LIST
    const int N = atListSync(&atListEm, EmMgr.pAlive, re4dc_alive_gen[1]);
    if (N >= 0) {
        cEm* const* a = atListEm.v;
#if RE4DC_EMHIT_LIST == 2
        {
            int k = 0;
            cEm* q = EmMgr.pAlive;
            for (; q != 0 && k < N && q == a[k]; q = (cEm*) q->pNext) {
                k++;
            }
            if (q != 0 || k != N) {
                ++ehlMis;
            }
            if (++ehlCalls % 1024 == 0) {
                re4dc_log("EHL calls=%u skip=%u mismatch=%u n=%d\n", ehlCalls, ehlSkip, ehlMis, N);
            }
        }
#endif
        for (int i = 0; i < N && i < ATLIST_PF; i++) {
            __builtin_prefetch(__builtin_addressof(a[i]->atari.m_flag));
        }
        for (int i = 0; i < N; i++) {
            if (i + ATLIST_PF < N) {
                __builtin_prefetch(__builtin_addressof(a[i + ATLIST_PF]->atari.m_flag));
            }
            m = a[i];
            if (!(m->atari.m_flag & 0x200)) {
                continue;
            }
            if (!(flag & 4) && m == pPL) {
                continue;
            }
            if (!(m->atari.m_flag & 2) && !(flag & 2)) {
#if RE4DC_EMHIT_LIST == 2
                ++ehlSkip;
                if (ComnHitCheck(&h, &n, m, pos0, pos1, flag) != 0) {
                    ++ehlMis;
                }
#endif
                continue;
            }
            if (ComnHitCheck(&h, &n, m, pos0, pos1, flag) == 0) {
                continue;
            }
            d = GetDistance3(pos0, &h);
            if (d < dist) {
                dist = d;
                if (hit != 0) {
                    *hit = h;
                }
                if (nrm != 0) {
                    *nrm = n;
                }
                ret = 1;
            }
        }
        return ret;
    }
#endif
    for (m = EmMgr.pAlive; m != 0; m = (cEm*) m->pNext) {
        if (!(m->atari.m_flag & 0x200)) {
            continue;
        }
        if (!(flag & 4) && m == pPL) {
            continue;
        }
        if (ComnHitCheck(&h, &n, m, pos0, pos1, flag) == 0) {
            continue;
        }
        d = GetDistance3(pos0, &h);
        if (d < dist) {
            dist = d;
            if (hit != 0) {
                *hit = h;
            }
            if (nrm != 0) {
                *nrm = n;
            }
            ret = 1;
        }
    }
    return ret;
}

// Same against every live object (except id 2): nearest hit / normal.
#if defined(RE4DC_OBJHIT_LIST) && RE4DC_OBJHIT_LIST
// GAME_OBJHIT_LIST (game30.mk; G, collision traversal; exact): the objects come from GAME_ATCHK_LIST's
// array of ObjMgr's alive list (rebuilt whenever the list changes), in list order, each object's header
// (be_flag) and id lines prefetched ahead; every test reads the object's live fields as before. Longer
// lists than the array: the list walk. =2 (check build): the array is compared with the live list at
// every call, and a list change during the walk is counted ("OHL" lines).
#if RE4DC_OBJHIT_LIST == 2
extern "C" void re4dc_log(const char* fmt, ...);
static u32 ohlCalls, ohlMis, ohlChanged;
#endif
#if defined(RE4DC_OBJHIT_IDFIRST) && RE4DC_OBJHIT_IDFIRST
// GAME_OBJHIT_IDFIRST (game30.mk; G, camera line vs objects; exact; needs GAME_OBJHIT_LIST=1): the id test
// before be_flag (two plain loads, either failing skips the object). From the array the object's header
// line (be_flag, pNext) is then read only for the ~1 in 6 objects whose id is not 2, and only the id
// lines are prefetched. =2 (check build): both orders compared ("OID" lines).
#if RE4DC_OBJHIT_IDFIRST == 2
extern "C" void re4dc_log(const char* fmt, ...);
static u32 oidCalls, oidMis;
#endif
#endif
static inline int objHitOne(cObj* o, Vec* hit, Vec* nrm, Vec* pos0, Vec* pos1, int flag, f32* dist)
{
    Vec h;
    Vec n;
    f32 d;

#if defined(RE4DC_OBJHIT_IDFIRST) && RE4DC_OBJHIT_IDFIRST
#if RE4DC_OBJHIT_IDFIRST == 2
    {
        const int p0 = (o->be_flag & 0x201) == 1 && o->id != 2;
        const int p1 = o->id != 2 && (o->be_flag & 0x201) == 1;
        if (p0 != p1) {
            ++oidMis;
        }
        if (++oidCalls % 65536 == 0) {
            re4dc_log("OID calls=%u mismatch=%u\n", oidCalls, oidMis);
        }
    }
#endif
    if (o->id == 2) {
        return 0;
    }
    if ((o->be_flag & 0x201) != 1) {
        return 0;
    }
#else
    if ((o->be_flag & 0x201) != 1) {
        return 0;
    }
    if (o->id == 2) {
        return 0;
    }
#endif
    if (ComnHitCheck(&h, &n, (cEm*) o, pos0, pos1, flag) == 0) {
        return 0;
    }
    d = (pos0->x - h.x) * (pos0->x - h.x) + (pos0->y - h.y) * (pos0->y - h.y) + (pos0->z - h.z) * (pos0->z - h.z);
    if (d < *dist) {
        *dist = d;
        if (hit != 0) {
            *hit = h;
        }
        if (nrm != 0) {
            *nrm = n;
        }
        return 1;
    }
    return 0;
}
int ObjHitCheck(Vec* hit, Vec* nrm, Vec* pos0, Vec* pos1, int flag)
{
    f32 dist = 10000000000.0f;
    int ret = 0;

    if (hit != 0) {
        *hit = *pos1;
    }
    const int N = atListSync(&atListObj, (cEm*) ObjMgr.pAlive, re4dc_alive_gen[2]);
    if (N < 0) {
        for (cObj* o = ObjMgr.pAlive; o != 0; o = (cObj*) o->pNext) {
            ret |= objHitOne(o, hit, nrm, pos0, pos1, flag, &dist);
        }
        return ret;
    }
    cEm* const* a = atListObj.v;
#if RE4DC_OBJHIT_LIST == 2
    {
        int i = 0;
        cObj* o = ObjMgr.pAlive;
        for (; o != 0 && i < N && (cEm*) o == a[i]; o = (cObj*) o->pNext) {
            i++;
        }
        if (o != 0 || i != N) {
            ++ohlMis;
        }
    }
    const u32 gen = re4dc_alive_gen[2];
#endif
#if defined(RE4DC_OBJHIT_IDFIRST) && RE4DC_OBJHIT_IDFIRST
    for (int i = 0; i < N && i < ATLIST_PF; i++) {
        __builtin_prefetch(&a[i]->id);
    }
    for (int i = 0; i < N; i++) {
        if (i + ATLIST_PF < N) {
            __builtin_prefetch(&a[i + ATLIST_PF]->id);
        }
#else
    for (int i = 0; i < N && i < ATLIST_PF; i++) {
        __builtin_prefetch(&a[i]->be_flag);
        __builtin_prefetch(&a[i]->id);
    }
    for (int i = 0; i < N; i++) {
        if (i + ATLIST_PF < N) {
            __builtin_prefetch(&a[i + ATLIST_PF]->be_flag);
            __builtin_prefetch(&a[i + ATLIST_PF]->id);
        }
#endif
        ret |= objHitOne((cObj*) a[i], hit, nrm, pos0, pos1, flag, &dist);
    }
#if RE4DC_OBJHIT_LIST == 2
    if (re4dc_alive_gen[2] != gen) {
        ++ohlChanged;
    }
    if (++ohlCalls % 1024 == 0) {
        re4dc_log("OHL calls=%u mismatch=%u changed=%u n=%d\n", ohlCalls, ohlMis, ohlChanged, N);
    }
#endif
    return ret;
}
#else
int ObjHitCheck(Vec* hit, Vec* nrm, Vec* pos0, Vec* pos1, int flag)
{
    Vec h;
    Vec n;
    f32 dist = 10000000000.0f;
    f32 d;
    int ret = 0;
    cObj* o;

    if (hit != 0) {
        *hit = *pos1;
    }
    for (o = ObjMgr.pAlive; o != 0; o = (cObj*) o->pNext) {
        if ((o->be_flag & 0x201) != 1) {
            continue;
        }
        if (o->id == 2) {
            continue;
        }
        if (ComnHitCheck(&h, &n, (cEm*) o, pos0, pos1, flag) == 0) {
            continue;
        }
        d = (pos0->x - h.x) * (pos0->x - h.x) + (pos0->y - h.y) * (pos0->y - h.y) + (pos0->z - h.z) * (pos0->z - h.z);
        if (d < dist) {
            dist = d;
            if (hit != 0) {
                *hit = h;
            }
            if (nrm != 0) {
                *nrm = n;
            }
            ret = 1;
        }
    }
    return ret;
}
#endif

#if defined(RE4DC_CUBE_MEMO) && RE4DC_CUBE_MEMO
// GAME_CUBE_MEMO (game30.mk; G, camera line vs box bodies; exact): emLineCubeCrossCk (em_sub.cpp) builds
// the box's eight corners (nine MTXMultVec) and each face's unit normal (cross product + VECNormalize)
// on every call, and cameraHitCheck tests the same boxes five times a tick (static bodies: every tick).
// Those are a pure function of the matrix (12 words), the three sizes and the offset (3 words): a
// table indexed by the body keeps, per face, the unit normal (or "zero normal": emLinePolyCrossCk
// returns 0) and its dot with the face's first corner, computed by the same statements. A call then
// runs emLinePolyCrossCk's two plane tests, da = dot(n, a) - dot(n, poly[0]) <= 0 and
// db = dot(n, b) - dot(n, poly[0]) >= 0 (each face that fails one returns 0 there), with the kept
// values; when a face passes both, the original emLineCubeCrossCk runs (the faces before it return 0
// in it as well). =2 (check build): every call compared with emLineCubeCrossCk (result and hit
// point), every hit's entry compared with a fresh build ("CBM" lines).
#ifndef RE4DC_CBM_BITS
#define RE4DC_CBM_BITS 4
#endif
#define CBM_N (1 << RE4DC_CBM_BITS)
#define CBM_PROBE 4
typedef u32 __attribute__((may_alias)) CbmWord;
struct CbmEntry {
    u32 k[18];   // matrix (12 words), sx, sy, sz, offset x / y / z
    u32 zero;    // bit f: face f's normal is the zero vector
    u32 pad;
    f32 f[6][4]; // face f: unit normal, dot(normal, first corner)
};
static CbmEntry cbm[CBM_N] __attribute__((aligned(32)));
static Vec* cbmTag[CBM_N];
static u32 cbmNext;
static const u8 cbmFace[6][4] = {{0, 1, 2, 3}, {1, 5, 6, 2}, {5, 4, 7, 6}, {4, 0, 3, 7}, {3, 2, 6, 7}, {1, 0, 4, 5}};
#if RE4DC_CUBE_MEMO == 2
extern "C" void re4dc_log(const char* fmt, ...);
static u32 cbmCalls, cbmHits, cbmFull, cbmMis, cbmEntMis;
#endif
// emLineCubeCrossCk's corners and emLinePolyCrossCk's normal part, statement for statement.
static __attribute__((noinline)) void cbmBuild(CbmEntry* e, Mtx m, f32 sx, f32 sy, f32 sz, Vec* ofs)
{
    Mtx mat;
    Vec c;
    Vec v[8];
    int f;

    PSMTXMultVec(m, ofs, &c);
    PSMTXCopy(m, mat);
    TransMatrix(mat, &c);
    v[0].x = -sx;
    v[0].y = 0.0f;
    v[0].z = sz;
    v[1].x = sx;
    v[1].y = 0.0f;
    v[1].z = sz;
    v[2].x = sx;
    v[2].y = sy;
    v[2].z = sz;
    v[3].x = -sx;
    v[3].y = sy;
    v[3].z = sz;
    v[4].x = -sx;
    v[4].y = 0.0f;
    v[4].z = -sz;
    v[5].x = sx;
    v[5].y = 0.0f;
    v[5].z = -sz;
    v[6].x = sx;
    v[6].y = sy;
    v[6].z = -sz;
    v[7].x = -sx;
    v[7].y = sy;
    v[7].z = -sz;
    RE4DC_XM_LOAD(mat);
    RE4DC_XM_POINT(mat, &v[0], &v[0]);
    RE4DC_XM_POINT(mat, &v[1], &v[1]);
    RE4DC_XM_POINT(mat, &v[2], &v[2]);
    RE4DC_XM_POINT(mat, &v[3], &v[3]);
    RE4DC_XM_POINT(mat, &v[4], &v[4]);
    RE4DC_XM_POINT(mat, &v[5], &v[5]);
    RE4DC_XM_POINT(mat, &v[6], &v[6]);
    RE4DC_XM_POINT(mat, &v[7], &v[7]);
    e->zero = 0;
    for (f = 0; f < 6; f++) {
        Vec poly[4];
        Vec e1;
        Vec e2;
        Vec n;

        poly[0] = v[cbmFace[f][0]];
        poly[1] = v[cbmFace[f][1]];
        poly[2] = v[cbmFace[f][2]];
        poly[3] = v[cbmFace[f][3]];
        PSVECSubtract(&poly[2], &poly[1], &e1);
        PSVECSubtract(&poly[0], &poly[1], &e2);
        PSVECCrossProduct(&e1, &e2, &n);
        if (n.x == 0.0f && n.y == 0.0f && n.z == 0.0f) {
            e->zero |= 1u << f;
            e->f[f][0] = 0.0f;
            e->f[f][1] = 0.0f;
            e->f[f][2] = 0.0f;
            e->f[f][3] = 0.0f;
            continue;
        }
        VECNormalize(&n, &n);
        e->f[f][0] = n.x;
        e->f[f][1] = n.y;
        e->f[f][2] = n.z;
        e->f[f][3] = PSVECDotProduct(&n, &poly[0]);
    }
}
static __attribute__((noinline)) int cubeMemoCk(Vec* a, Vec* b, Mtx m, f32 sx, f32 sy, f32 sz, cAtariInfo* info, Vec* hit)
{
    Vec* ofs = (Vec*) info;
    const CbmWord* mw = (const CbmWord*) m;
    const CbmWord* ow = (const CbmWord*) ofs;
    const u32 ksx = *(const CbmWord*) &sx;
    const u32 ksy = *(const CbmWord*) &sy;
    const u32 ksz = *(const CbmWord*) &sz;
    const u32 h = ((u32) ofs * 0x9E3779B1u) >> (32 - RE4DC_CBM_BITS);
    CbmEntry* e = 0;
    u32 d = 1;
    int i;
    int f;

    for (i = 0; i < CBM_PROBE; i++) {
        const u32 j = (h + i) & (CBM_N - 1);
        if (cbmTag[j] == ofs) {
            e = &cbm[j];
            break;
        }
    }
    if (e != 0) {
        const u32* k = e->k;
        d = (k[0] ^ mw[0]) | (k[1] ^ mw[1]) | (k[2] ^ mw[2]) | (k[3] ^ mw[3]) | (k[4] ^ mw[4]) | (k[5] ^ mw[5]) |
            (k[6] ^ mw[6]) | (k[7] ^ mw[7]) | (k[8] ^ mw[8]) | (k[9] ^ mw[9]) | (k[10] ^ mw[10]) | (k[11] ^ mw[11]) |
            (k[12] ^ ksx) | (k[13] ^ ksy) | (k[14] ^ ksz) | (k[15] ^ ow[0]) | (k[16] ^ ow[1]) | (k[17] ^ ow[2]);
    } else {
        u32 j = (h + (cbmNext++ & (CBM_PROBE - 1))) & (CBM_N - 1);
        for (i = 0; i < CBM_PROBE; i++) {
            if (cbmTag[(h + i) & (CBM_N - 1)] == 0) {
                j = (h + i) & (CBM_N - 1);
                break;
            }
        }
        cbmTag[j] = ofs;
        e = &cbm[j];
    }
    if (d != 0) {
        for (i = 0; i < 12; i++) {
            e->k[i] = mw[i];
        }
        e->k[12] = ksx;
        e->k[13] = ksy;
        e->k[14] = ksz;
        e->k[15] = ow[0];
        e->k[16] = ow[1];
        e->k[17] = ow[2];
        cbmBuild(e, m, sx, sy, sz, ofs);
    }
#if RE4DC_CUBE_MEMO == 2
    else {
        CbmEntry t;
        ++cbmHits;
        cbmBuild(&t, m, sx, sy, sz, ofs);
        if (t.zero != e->zero || __builtin_memcmp(t.f, e->f, sizeof(t.f)) != 0) {
            ++cbmEntMis;
        }
    }
#endif
    for (f = 0; f < 6; f++) {
        Vec n;
        f32 d0;
        f32 da;
        f32 db;

        if (e->zero & (1u << f)) {
            continue;
        }
        n.x = e->f[f][0];
        n.y = e->f[f][1];
        n.z = e->f[f][2];
        d0 = e->f[f][3];
        da = PSVECDotProduct(&n, a) - d0;
        if (da <= 0.0f) {
            continue;
        }
        db = PSVECDotProduct(&n, b) - d0;
        if (db >= 0.0f) {
            continue;
        }
#if RE4DC_CUBE_MEMO == 2
        ++cbmFull;
#endif
        return emLineCubeCrossCk(a, b, m, sx, sy, sz, info, hit);
    }
    return 0;
}
static inline int cubeCk(Vec* a, Vec* b, Mtx m, f32 sx, f32 sy, f32 sz, cAtariInfo* info, Vec* hit)
{
#if RE4DC_CUBE_MEMO == 2
    Vec h0 = {0.0f, 0.0f, 0.0f};
    Vec h1 = {0.0f, 0.0f, 0.0f};
    if (hit != 0) {
        h0 = *hit;
        h1 = *hit;
    }
    int r0 = emLineCubeCrossCk(a, b, m, sx, sy, sz, info, &h0);
    int r1 = cubeMemoCk(a, b, m, sx, sy, sz, info, &h1);
    if (r0 != r1 || __builtin_memcmp(&h0, &h1, sizeof(Vec)) != 0) {
        ++cbmMis;
    }
    if (hit != 0) {
        *hit = h0;
    }
    if (++cbmCalls % 8192 == 0) {
        re4dc_log("CBM calls=%u hits=%u full=%u mismatch=%u entmis=%u\n", cbmCalls, cbmHits, cbmFull, cbmMis, cbmEntMis);
    }
    return r0;
#else
    return cubeMemoCk(a, b, m, sx, sy, sz, info, hit);
#endif
}
#define COMN_CUBE_CK cubeCk
#else
#define COMN_CUBE_CK emLineCubeCrossCk
#endif
// Line against one body: a box body (flag bit0 required) through emLineCubeCrossCk in its
// parts / model matrix, a cylinder body (flag bit1) through ObaLineHitChk. 1 on a hit.
int ComnHitCheck(Vec* hit, Vec* nrm, cEm* m, Vec* pos0, Vec* pos1, int flag)
{
    Mtx mat;
    int r;

    if (m->atari.m_flag & 2) {
        if (!(flag & 1)) {
            return 0;
        }
        if (m->atari.m_parts_no > 0) {
            MTX_COPY(m->getPartsPtr(m->atari.m_parts_no - 1)->mat, mat);
        } else {
            MTX_COPY(m->mat, mat);
        }
        r = COMN_CUBE_CK(pos0, pos1, mat, m->atari.m_radius, m->atari.m_height, m->atari.m_radius2, &m->atari, hit);
        if (r != 0) {
            return 1;
        }
    } else if (flag & 2) {
        r = ObaLineHitChk(m, &m->atari, pos0, pos1, hit, nrm);
        if (r != 0) {
            return 1;
        }
    }
    if (hit != 0) {
        *hit = *pos1;
    }
    return 0;
}

// Debug draw of the character's body and every chained info (Debug_flg[2] 0x10000000).
void DrawOba(cEm* m)
{
    cAtariInfo* info;

    if (m->atari.m_flag & 0x200) {
        info = &m->atari;
        do {
            info->disp(m);
            info = info->m_pList;
        } while (info != 0);
    }
}

// Line a -> b against the cylinder body treated as a sphere of radius m_radius2 at the body's
// position: nearest entry point in *hit, outward normal in *nrm; 1 on a hit.
int ObaLineHitChk(cEm* m, cAtariInfo* info, Vec* a, Vec* b, Vec* hit, Vec* nrm)
{
    Vec p0;
    Vec p1;
    Vec w0;
    Vec w1;
    Vec d;
    Vec e;
    Vec f;
    Vec g;
    Vec h;
    Vec q;
    Vec r;
    Vec n;
    cModel* pm;
    f32 rad;
    f32 dd;
    f32 ee;
    f32 df;
    f32 ef;
    f32 de;
    f32 den;
    f32 t;
    f32 s;
    f32 tc;
    f32 rr;
    f32 depth;
    int parts;

    p1 = info->m_offset;
    p0 = info->m_offset;
    p0.y += info->m_height;
    parts = info->m_parts_no;
    // COMPILER-DIFF: 12 (cse AROUND path): the target's `&p0` argument is a fresh `addi r4,r1,8` (the
    // copy's address pseudo dies at the copy). With `pm = m; if (parts) pm = ..;` cse skips the arm and
    // carries the copy pseudo into the join, folding `&p0` into it across the getPartsPtr call. The
    // explicit else arm is followed as a TAKEN branch and falls into the join label, which ends the
    // extended block: `&p0` stays a hard-reg argument set (never PRE'd, no longer cse-folded).
    if (parts != 0) {
        pm = m->getPartsPtr(parts - 1);
    } else {
        pm = m;
    }
    rad = info->m_radius * 0.75f;
    RE4DC_XM_LOAD(pm->mat);
    RE4DC_XM_POINT(pm->mat, &p0, &w0);
    RE4DC_XM_POINT(pm->mat, &p1, &w1);
    PSVECSubtract(&w1, &w0, &d);
    PSVECSubtract(b, a, &e);
    PSVECSubtract(a, &w0, &f);
    dd = PSVECSquareMag(&d);
    ee = PSVECSquareMag(&e);
    df = PSVECDotProduct(&d, &f);
    ef = PSVECDotProduct(&e, &f);
    de = PSVECDotProduct(&d, &e);
    den = dd * ee - de * de;
    // COMPILER-DIFF: 13 (FPR naming): den is settled in f0 before the t numerator is formed. The
    // `de * ef` input makes the anchor ready one cycle later in sched2 (the product's fmuls, not den,
    // gates it), so the `mr r3,r27` hoisted argument takes the slot the codeless anchor used to
    // occupy; the extra `"f"(den)` reference keeps den's local-alloc priority above the product's
    // (which gained a third reference) so den stays in f0 and the product in f13.
    asm("" : "+f"(den) : "f"(den), "f"(de * ef));
    t = (ee * df - de * ef) / den;
    s = (de * df - dd * ef) / den;
    tc = t < 0.0f ? 0.0f : (t > 1.0f ? 1.0f : t);
    // s is clamped in place: the ternary's temporary (f13) is copied back into s (f30) after the join.
    s = s < 0.0f ? 0.0f : (s > 1.0f ? 1.0f : s);
    PSVECScale(&w0, &g, 1.0f - tc);
    rr = rad * rad;
    PSVECScale(&w1, &h, tc);
    PSVECAdd(&g, &h, &q);
    PSVECScale(a, &g, 1.0f - s);
    PSVECScale(b, &h, s);
    PSVECAdd(&g, &h, &r);
    if (PSVECSquareDistance(&q, &r) <= rr) {
        PSVECSubtract(&q, &r, &n);
        {
            f32 mag = PSVECMag(&n);
            depth = SQRTF(rr - mag * mag);
        }
#line 1434 "D:/Bio4/Prog/at_mod.cpp"
        VECNormalize(&e, &n);
        PSVECScale(&n, &n, -depth);
        PSVECAdd(&r, &n, hit);
        PSVECSubtract(hit, &p1, nrm);
        nrm->y = 0.0f;
#line 1440 "D:/Bio4/Prog/at_mod.cpp"
        VECNormalize(nrm, nrm);
        return 1;
    }
    return 0;
}
