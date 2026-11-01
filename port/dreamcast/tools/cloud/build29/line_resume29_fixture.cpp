// Synthetic SAT owner/caller fixture. test_line_resume29.py inserts unmodified
// production consumers into line_resume29_production.inc before compiling this.
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <new>
#include <vector>

using u8 = unsigned char;
using u16 = unsigned short;
using u32 = uintptr_t; // target u32 holds a pointer; preserve that property on a 64-bit host
using f32 = float;
struct Vec { f32 x, y, z; };
struct AtPoly { u16 n; u16 id; f32 t; u32 attr; };
struct AtPolyData {};

struct cSatBlock {
    Vec min, m_Size;
    u16 m_nFloor, m_nSlope, m_nWall, m_Flag;
    cSatBlock* next;
    u16 idx[0];
    int lineOverlap(Vec*, Vec*, Vec*);
    int hitCheckSphere(Vec*, Vec*, f32) { return 0; }
};
struct cSat {
    Vec* vtx;
    Vec* norm_p;
    Vec* edge_p;
    AtPoly* poly_p;
    u16 polygon_num;
    cSatBlock* block_p;
    f32 mat[3][4], imat[3][4];
    int testIndex;
    bool alive;
    int isAlive() const { return alive; }
};
struct cSatMgr {
    cSat* pArray;
    u32 nArray, size;
    int hitCheck2(Vec*, Vec*, Vec*, u32*, int, int);
};
struct SEckView { u32 v; };
static u32 SEck, seCk;
static cSat* pBypassAt;
static u8 polyBit[8192];
static int overlapCalls, fullTransforms;
static std::vector<int> visits;

static void PSVECAdd(const Vec* a, const Vec* b, Vec* out)
{
    const Vec t = {a->x + b->x, a->y + b->y, a->z + b->z};
    *out = t;
}
static void PSVECScale(const Vec* a, Vec* out, f32 s)
{
    const Vec t = {a->x * s, a->y * s, a->z * s};
    *out = t;
}
static void PSVECSubtract(const Vec* a, const Vec* b, Vec* out)
{
    const Vec t = {a->x - b->x, a->y - b->y, a->z - b->z};
    *out = t;
}
static void PSMTXMultVec(f32 (*m)[4], const Vec* p, Vec* out)
{
    ++fullTransforms;
    const Vec t = {
        ((p->x * m[0][0] + p->y * m[0][1]) + p->z * m[0][2]) + m[0][3],
        m[1][3] + ((m[1][2] * p->z) + ((m[1][0] * p->x) + (m[1][1] * p->y))),
        ((m[2][0] * p->x + m[2][1] * p->y) + m[2][2] * p->z) + m[2][3],
    };
    *out = t;
}
static f32 GetDistance(const Vec* a, const Vec* b)
{
    const f32 x = a->x - b->x, y = a->y - b->y, z = a->z - b->z;
    return std::sqrt(x * x + y * y + z * z);
}
static void memclr_asm(void* p, u32 n) { std::memset(p, 0, n); }
static u32 At_poly_line_ck(AtPolyData* pd, Vec* out, AtPoly* poly, Vec* a, Vec* b, u32, u32 mask)
{
    cSat* sat = reinterpret_cast<cSat*>(pd);
    visits.push_back(sat->testIndex * 1000 + poly->id);
    if ((poly->attr & mask) || !poly->attr) return 0;
    out->x = a->x + (b->x - a->x) * poly->t;
    out->y = a->y + (b->y - a->y) * poly->t;
    out->z = a->z + (b->z - a->z) * poly->t;
    return poly->attr;
}

#define RE4DC_XM_LOAD(m) ((void)0)
#define RE4DC_XM_POINT(m, in, out) PSMTXMultVec((m), (in), (out))
#define COL_PREFETCH(p) ((void)0)
#define colPrefetchPoly(sat, idx, end) ((void)0)
int blkPolyLineCk(cSat*, cSatBlock*, Vec*, Vec*, int, int, Vec*, u32*);
int blkPolyLineCkCore(cSat*, cSatBlock*, Vec*, Vec*, int, int, Vec*, u32*);

#include "line_resume29_production.inc"

extern "C" void re4dc_log(const char*, ...) {}

// Host equivalents of the documented old SH-4 list ABI. These only stand in
// for the unavailable target assembly; the consumers above are production.
static int listWalk(cSatBlock* root, Vec* mid, Vec* dir, Vec* adir, cSatBlock** out, int max)
{
    int count = 0;
    bool full = false;
    auto walk = [&](auto&& self, cSatBlock* blk, int depth) -> void {
        for (; blk && !full; blk = blk->next) {
            if (!blk->lineOverlap(mid, dir, adir)) continue;
            if (blk->m_Flag & 1) {
                if (depth == 16) { full = true; return; }
                self(self, reinterpret_cast<cSatBlock*>(blk->idx), depth + 1);
            } else {
                if (count == max) { full = true; return; }
                out[count++] = blk;
            }
        }
    };
    walk(walk, root, 0);
    return full ? -1 : count;
}
extern "C" int re4dc_line_walk(const LineWalkQ* q, cSatBlock* blk, cSatBlock** out, int max)
{
    Vec mid = {q->mx, 0, q->mz}, dir = {q->dx, 0, q->dz}, adir = {q->ax, 0, q->az};
    return listWalk(blk, &mid, &dir, &adir, out, max);
}
extern "C" int re4dc_line_walk2(const LineWalkQ* q, cSatBlock* blk, cSatBlock** out, int max)
{
    return re4dc_line_walk(q, blk, out, max);
}
#if RE4DC_LINE_PIECE
static void pieceXZ(f32 (*m)[4], const Vec* p, f32* x, f32* z)
{
    *x = ((p->x * m[0][0] + p->y * m[0][1]) + p->z * m[0][2]) + m[0][3];
    *z = ((m[2][0] * p->x + m[2][1] * p->y) + m[2][2] * p->z) + m[2][3];
}
extern "C" int re4dc_line_piece(LinePieceQ* q, cSatBlock* blk, cSatBlock** out, int max)
{
    pieceXZ(q->m, q->p0, &q->lax, &q->laz);
    pieceXZ(q->m, q->p1, &q->lbx, &q->lbz);
    Vec a = {q->lax, 0, q->laz}, b = {q->lbx, 0, q->lbz};
    Vec mid, dir, adir;
    PSVECAdd(&a, &b, &mid);
    PSVECScale(&mid, &mid, 0.5f);
    PSVECSubtract(&a, &mid, &dir);
    adir = {std::fabs(dir.x), 0, std::fabs(dir.z)};
    dir.y = mid.y = 0;
    return listWalk(blk, &mid, &dir, &adir, out, max);
}
extern "C" int re4dc_line_piece2(LinePieceQ* q, cSatBlock* blk, cSatBlock** out, int max)
{
    return re4dc_line_piece(q, blk, out, max);
}
#endif

struct Blocks {
    std::vector<void*> allocations;
    ~Blocks() { for (void* p : allocations) ::operator delete(p); }
    cSatBlock* leaf(u16 id, bool far = false, bool wall = false)
    {
        void* storage = ::operator new(sizeof(cSatBlock) + sizeof(u16));
        allocations.push_back(storage);
        auto* b = new (storage) cSatBlock{};
        init(b, far);
        if (wall) b->m_nWall = 1;
        else b->m_nFloor = 1;
        b->idx[0] = id;
        return b;
    }
    static void init(cSatBlock* b, bool far = false)
    {
        b->min = {far ? 1000.0f : -100.0f, -100.0f, -100.0f};
        b->m_Size = {200, 200, 200};
    }
    cSatBlock* chain(int n, bool far = false, bool repeat = false)
    {
        cSatBlock* first = nullptr;
        cSatBlock** tail = &first;
        for (int i = 0; i < n; ++i) {
            cSatBlock* b = leaf(repeat ? u16(i % 60) : u16(i), far);
            *tail = b;
            tail = &b->next;
        }
        return first;
    }
    cSatBlock* nested(int depth, u16 id)
    {
        assert(offsetof(cSatBlock, idx) == sizeof(cSatBlock));
        void* storage = ::operator new((depth + 1) * sizeof(cSatBlock) + sizeof(u16));
        allocations.push_back(storage);
        auto* b = reinterpret_cast<cSatBlock*>(storage);
        for (int i = 0; i <= depth; ++i) {
            auto* p = new (b) cSatBlock{};
            init(p);
            p->m_Flag = i < depth ? 1 : 0;
            if (i == depth) {
                p->m_nFloor = 1;
                p->idx[0] = id;
            }
            b = reinterpret_cast<cSatBlock*>(p->idx);
        }
        return reinterpret_cast<cSatBlock*>(storage);
    }
};

static void matrix(cSat* sat, float tx)
{
    std::memset(sat->mat, 0, sizeof(sat->mat));
    std::memset(sat->imat, 0, sizeof(sat->imat));
    for (int i = 0; i < 3; ++i) sat->mat[i][i] = sat->imat[i][i] = 1;
    sat->mat[0][3] = tx;
    sat->imat[0][3] = -tx;
}
static uint32_t bits(float f)
{
    uint32_t v;
    std::memcpy(&v, &f, 4);
    return v;
}
static int caseRun(const char* name, cSatBlock* root0, cSatBlock* root1, int attrMode, int flag,
                   bool direct, bool fractional = false)
{
    std::vector<AtPoly> polys0(256), polys1(256);
    std::vector<Vec> norm0(256), norm1(256);
    for (int i = 0; i < 256; ++i) {
        const u32 attr = attrMode == 0 ? 0 : attrMode == 2 ?
            (i == 63 || i == 64 ? u32(i + 1) : 0) :
            (i == 7 || i == 63 || i == 64 || i == 70 || i == 100 || i == 135 ? u32(i + 1) : 0);
        const u32 attr1 = attrMode == 2 ? (i == 7 ? 1008U : 0U) : attr;
        const f32 t0 = attrMode == 2 && (i == 63 || i == 64) ? 0.25f :
            i == 7 ? 0.7f : (i == 64 ? 0.2f : (i == 100 ? 0.4f : 0.9f));
        const f32 t1 = attrMode == 2 && i == 7 ? 0.25f : i == 7 ? 0.1f : 0.5f;
        polys0[i] = {u16(i), u16(i), t0, attr};
        polys1[i] = {u16(i), u16(i), t1, attr1};
        norm0[i] = {float(i), 1, 0};
        norm1[i] = {float(i), 2, 0};
    }
    cSat sats[2]{};
    sats[0].poly_p = polys0.data(); sats[0].norm_p = norm0.data(); sats[0].polygon_num = 256;
    sats[0].block_p = root0; sats[0].testIndex = 0; sats[0].alive = true; matrix(&sats[0], 0);
    sats[1].poly_p = polys1.data(); sats[1].norm_p = norm1.data(); sats[1].polygon_num = 256;
    sats[1].block_p = root1; sats[1].testIndex = 1; sats[1].alive = root1 != nullptr; matrix(&sats[1], 2);
    if (fractional) {
        sats[0].imat[0][0] = 1.25f; sats[0].imat[0][1] = 0.125f;
        sats[0].imat[0][2] = -0.5f; sats[0].imat[0][3] = 2.75f;
        sats[0].imat[1][0] = 0.25f; sats[0].imat[1][2] = 0.5f;
        sats[0].imat[2][0] = -0.25f; sats[0].imat[2][1] = 0.0625f;
        sats[0].imat[2][2] = 0.75f; sats[0].imat[2][3] = -1.125f;
    }
    cSatMgr mgr{sats, 2, sizeof(cSat)};
    Vec a = {0, 1, 0}, b = {10, 1, 0}, hit = {-999, -999, -999};
    u32 attr = 0;
    pBypassAt = nullptr;
    visits.clear(); overlapCalls = fullTransforms = 0;
    int ret;
    if (direct) {
        std::memset(polyBit, 0, sizeof(polyBit));
        hit = b;
        ret = blkPolyLineCk(&sats[0], root0, &a, &b, flag, 0, &hit, &attr);
    } else {
        ret = mgr.hitCheck2(&a, &b, &hit, &attr, flag, 0);
    }
    int normIndex = -1;
    if (attr) {
        Vec* norm = reinterpret_cast<Vec*>(attr);
        for (int i = 0; i < 256; ++i) {
            if (norm == &norm0[i]) normIndex = i;
            if (norm == &norm1[i]) normIndex = 1000 + i;
        }
    }
    if (attrMode == 2) {
        // Equal nearest intersections at leaves 64/65 and again in piece 2:
        // the source's strict '<' retains the first polygon and first piece.
        assert(!direct && root1 && ret == 64 && normIndex == 63 && pBypassAt == &sats[0]);
        assert(bits(hit.x) == bits(2.5f) && bits(hit.y) == bits(1.0f) && bits(hit.z) == bits(0.0f));
        assert(visits.size() == 73 && visits[63] == 63 && visits[64] == 64 && visits[65] == 1000);
    }
#if RE4DC_LINE_RESUME && RE4DC_LINE_PIECE
    if (!root0 && !root1 && fullTransforms != 0) std::abort();
#endif
    std::printf("%s ret=%d hit=%08x,%08x,%08x end=%08x,%08x,%08x owner=%d norm=%d visits=",
                name, ret, bits(hit.x), bits(hit.y), bits(hit.z), bits(b.x), bits(b.y), bits(b.z),
                pBypassAt == &sats[0] ? 0 : pBypassAt == &sats[1] ? 1 : -1, normIndex);
    for (int v : visits) std::printf("%d,", v);
    std::printf(" bits=");
    for (int i = 0; i < 32; ++i) std::printf("%02x", polyBit[i]);
    std::printf("\n");
    return overlapCalls;
}

int main()
{
    Blocks blocks;
    caseRun("zero", nullptr, nullptr, 0, 0x40, false);
    for (int n : {1, 63, 64, 65, 66, 127, 128, 129, 150}) {
        char name[40];
        std::snprintf(name, sizeof(name), "linear-%d", n);
        cSatBlock* root = blocks.chain(n);
        const int noHitSteps = caseRun(name, root, nullptr, 0, 0x40, false);
        const int hitSteps = caseRun(name, root, nullptr, 1, 0x40, false);
        const int directSteps = caseRun(name, root, nullptr, 1, 0x40, true);
#if RE4DC_LINE_RESUME
        if (noHitSteps != n || hitSteps != n || directSteps != n) std::abort();
#endif
    }
    caseRun("far", blocks.chain(130, true), nullptr, 1, 0x40, false);
    caseRun("repeat", blocks.chain(150, false, true), nullptr, 1, 0x40, false);
    for (int depth : {15, 16, 17, 18, 33}) {
        char name[40];
        std::snprintf(name, sizeof(name), "depth-%d", depth);
        cSatBlock* first = blocks.chain(65);
        cSatBlock* tail = first;
        while (tail->next) tail = tail->next;
        tail->next = blocks.nested(depth, 100);
        tail->next->next = blocks.leaf(135);
        const int hitSteps = caseRun(name, first, nullptr, 1, 0x40, false);
        const int directSteps = caseRun(name, first, nullptr, 1, 0x40, true);
#if RE4DC_LINE_RESUME
        if (hitSteps != 67 + depth || directSteps != 67 + depth) std::abort();
#endif
    }
    cSatBlock* moving0 = blocks.chain(70);
    cSatBlock* moving1 = blocks.chain(72);
    caseRun("moving-two", moving0, moving1, 1, 0x40, false);
    caseRun("equal-nearest-65-two-pieces", blocks.chain(65), blocks.chain(8), 2, 0x40, false);
    caseRun("fractional-xz", blocks.chain(129), nullptr, 1, 0x40, false, true);
    caseRun("wall-filter", blocks.leaf(7, false, true), nullptr, 1, 0x80, false);
    caseRun("floor-filter", blocks.leaf(7, false, true), nullptr, 1, 0x40, false);
#if RE4DC_LINE_WALK == 2
    if (lnwMis) { std::fprintf(stderr, "walk mismatches %zu\n", size_t(lnwMis)); std::abort(); }
#if RE4DC_LINE_RESUME
    if (lnwCalls) std::abort(); // the cursor never calls the old gather checker
#else
    if (!lnwCalls) std::abort(); // the reference arm really exercised it
#endif
#endif
#if RE4DC_LINE_WALK_PF == 2
    if (lwpMis) { std::fprintf(stderr, "prefetch mismatches %zu\n", size_t(lwpMis)); std::abort(); }
#if RE4DC_LINE_RESUME
    if (lwpCalls) std::abort();
#else
    if (!lwpCalls) std::abort();
#endif
#endif
#if RE4DC_LINE_PIECE == 2
    if (lnpMis || lnpLeafMis) { std::fprintf(stderr, "piece counters %zu %zu\n", size_t(lnpMis), size_t(lnpLeafMis)); std::abort(); }
#if RE4DC_LINE_RESUME
    if (lnpCalls) std::abort();
#else
    if (!lnpCalls) std::abort();
#endif
#endif
#if RE4DC_LINE_YROW == 2
    if (lyrMis || lyrCurMis || lyrTmpMis) { std::fprintf(stderr, "yrow counters %zu %zu %zu\n", size_t(lyrMis), size_t(lyrCurMis), size_t(lyrTmpMis)); std::abort(); }
    if (!lyrCalls) std::abort();
#endif
    return 0;
}
