// garmenttest.cpp (lane eng-svc5): the native garment service (services/cloth/garment.cpp) against the original unit
// pl_cloth.cpp, side by side in one program (the original object's global symbols renamed orig_<symbol>; svc.mk
// garmenttest). Every set-up and step function of every character and costume is called with the same inputs on both
// sides; the cloth service's entry points (PenClothSet / PenClothMove / PenClothMove3) and the chain object's
// (SetChain, setChain, setParent) are stubs here that log each call with the full content of the chain work handed
// in (every table's values, not its address), so the two sides' logs must be equal entry for entry. Ashley's lapel
// pose runs on a synthetic 160-part model (random matrices and positions), which no fixture's model has: every part's
// matrices and positions must be bit-identical afterwards.
//
//   garmenttest [count]   RE4_SVC_CONTROL=garmenthair|garmentskirt|lapelrate sets the native control (must FAIL)
// Exit 0 PASS; 1 when anything differs; 2 when a function was never exercised.
#include "types.h"
#include "global.h"
#include "model.h"
#include "pl_cloth.h"
#include "pendulum.h"
#include "../../services/cloth/garment.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

void girlLapelMove(cModel* pl);
// the original unit under its renamed symbols
void o_PlClothSetLeon(cModel*, PlCloth*, PlCloth*, PlCloth*) asm("orig__Z14PlClothSetLeonP6cModelP7PlClothS2_S2_");
void o_PlClothMoveLeon(cModel*, PlCloth*, PlCloth*, PlCloth*) asm("orig__Z15PlClothMoveLeonP6cModelP7PlClothS2_S2_");
void o_PlClothSetGirl(cModel*, PlCloth*, PlCloth*, PlCloth*, int) asm("orig__Z14PlClothSetGirlP6cModelP7PlClothS2_S2_i");
void o_PlClothMoveGirl(cModel*, PlCloth*, PlCloth*, PlCloth*) asm("orig__Z15PlClothMoveGirlP6cModelP7PlClothS2_S2_");
void o_PlClothSetLuis(cModel*, PlCloth*) asm("orig__Z14PlClothSetLuisP6cModelP7PlCloth");
void o_PlClothMoveLuis(cModel*, PlCloth*) asm("orig__Z15PlClothMoveLuisP6cModelP7PlCloth");
void o_PlClothSetAda(cModel*, PlCloth*, PlCloth*, PlCloth*, int) asm("orig__Z13PlClothSetAdaP6cModelP7PlClothS2_S2_i");
void o_PlClothMoveAda(cModel*, PlCloth*, PlCloth*, PlCloth*) asm("orig__Z14PlClothMoveAdaP6cModelP7PlClothS2_S2_");
cObjChain* o_AdaRibbonSet(cModel*, PlCloth*, void*, void*) asm("orig__Z12AdaRibbonSetP6cModelP7PlClothPvS3_");
void o_girlLapelMove(cModel*) asm("orig__Z13girlLapelMoveP6cModel");

// ---- the game around the unit ----
static u8 g_global[sizeof(GlobalWork)];
GlobalWork* pG = (GlobalWork*) g_global;
const int kParts = 160;
cModel* cModel::getPartsPtr(int no)
{
    if (no < 0) return this;
    return (cModel*) ((cParts*) pParts + no);
}

namespace {
// ---- the log: one side's calls, each with the content of what it was handed ----
struct Log {
    u32 w[1 << 16];
    unsigned n;
    void put(u32 v) { if (n < sizeof w / sizeof w[0]) w[n++] = v; }
};
Log g_log[2];
int g_side;
PlCloth* g_works[2];   // the side's three works
cModel* g_model[2];
u32 fnv(u32 h, const void* p, unsigned n)
{
    const u8* b = (const u8*) p;
    for (unsigned i = 0; i < n; i++) h = (h ^ b[i]) * 16777619u;
    return h;
}
int work_index(void* c)
{
    for (int i = 0; i < 3; i++)
        if ((void*) &g_works[g_side][i] == c) return i;
    return -1;
}
u32 content(const PlCloth* c)
{
    u32 h = 2166136261u;
    const int n = c->Num;
    h = fnv(h, &n, 4);
    const u8* tabs[] = {c->pCloth, c->pLeft, c->pRight, c->pUpLeft, c->pParent, c->pChild};
    for (const u8* t : tabs) {
        if (t) h = fnv(h, t, n);
        else h = fnv(h, "\xff\xff\xff\xfe", 4);
    }
    const f32* ftabs[] = {c->pRate, c->pMax, c->pWindSin, c->pWindRate};
    for (const f32* t : ftabs) {
        if (t) h = fnv(h, t, 4 * n);
        else h = fnv(h, "\xff\xff\xff\xfd", 4);
    }
    if (c->pAtset) h = fnv(h, c->pAtset, sizeof(CLOTH_AT_SET) * c->At_num);
    const u32 m = c->pModel == g_model[g_side] ? 1 : c->pModel ? 2 : 0;
    const u32 sc[] = {c->pUpRight, c->pGravity, (u32) c->At_num, (u32) c->Bundle_num, c->pPtbl, m, c->Flag};
    h = fnv(h, sc, sizeof sc);
    const f32 fs[] = {c->Gravity, c->Rate, c->WindSin, c->Stretchy, c->Move_rate};
    return fnv(h, fs, sizeof fs);
}
void logcall(u32 kind, cModel* m, void* c, f32 len = 0.0f)
{
    Log& L = g_log[g_side];
    L.put(kind);
    L.put(m == g_model[g_side] ? 1 : 0);
    L.put((u32) work_index(c));
    L.put(c ? content((PlCloth*) c) : 0);
    u32 lb;
    memcpy(&lb, &len, 4);
    L.put(lb);
}
}   // namespace

extern "C" {
void PenClothSet(cModel* m, PenCloth* c, f32 len) { logcall(1, m, c, len); }
void PenClothMove(cModel* m, PenCloth* c) { logcall(2, m, c); }
void PenClothMove3(cModel* m, PenCloth* c) { logcall(3, m, c); }
}
static u8 g_chain[2][64];
cObjChain* SetChain(void* bin, void* tpl, Vec* pos, Vec* rot)
{
    logcall(4, 0, 0);
    g_log[g_side].put((u32) (uintptr_t) bin), g_log[g_side].put((u32) (uintptr_t) tpl);
    g_log[g_side].put(fnv(fnv(2166136261u, pos, 12), rot, 12));
    return (cObjChain*) g_chain[g_side];
}
void cObjChain::setChain(PenCloth* c) { logcall(5, 0, c); g_log[g_side].put((u8*) this == g_chain[g_side]); }
void cObjChain::setParent(cModel* parent, int parts, Vec* ofs, int flag)
{
    logcall(6, parent, 0);
    g_log[g_side].put((u32) parts), g_log[g_side].put(fnv(2166136261u, ofs, 12)), g_log[g_side].put((u32) flag);
}

namespace {
u32 g_seed = 0x9E3779B9u;
u32 rnd() { g_seed ^= g_seed << 13, g_seed ^= g_seed >> 17, g_seed ^= g_seed << 5; return g_seed; }
f32 uni(f32 lo, f32 hi) { return lo + (hi - lo) * ((rnd() >> 8) * (1.0f / 16777216.0f)); }

// a model record and its parts: random rigid matrices (rotation by Euler angles, translation), positions, worlds;
// each part's parent the model or an earlier part
alignas(16) u8 g_mbuf[2][0x400];
alignas(16) u8 g_pbuf[2][kParts * sizeof(cParts)];
void make_model()
{
    cModel* m = (cModel*) g_mbuf[0];
    memset(g_mbuf[0], 0, sizeof g_mbuf[0]);
    memset(g_pbuf[0], 0, sizeof g_pbuf[0]);
    m->be_flag = 0x2000 | (rnd() % 2 ? 0x00E00000 : 0);
    cParts* parts = (cParts*) g_pbuf[0];
    m->pParts = (cModel*) parts;
    auto rigid = [](Mtx mt) {
        Vec r = {uni(-3.2f, 3.2f), uni(-3.2f, 3.2f), uni(-3.2f, 3.2f)};
        RotMatrix(mt, &r);
        mt[0][3] = uni(-5000.0f, 5000.0f), mt[1][3] = uni(-500.0f, 2000.0f), mt[2][3] = uni(-5000.0f, 5000.0f);
    };
    rigid(m->mat);
    for (int i = 0; i < kParts; i++) {
        cParts* p = &parts[i];
        rigid(p->mat);
        rigid(p->l_mat);
        p->pParent = i == 0 || rnd() % 3 == 0 ? (cCoord*) m : (cCoord*) &parts[rnd() % i];
        p->pos = Vec{uni(-80.0f, 80.0f), uni(-80.0f, 80.0f), uni(-80.0f, 80.0f)};
        p->world = Vec{p->mat[0][3], p->mat[1][3], p->mat[2][3]};
    }
    // the second side's copy, its pointers moved to its own buffers
    memcpy(g_mbuf[1], g_mbuf[0], sizeof g_mbuf[0]);
    memcpy(g_pbuf[1], g_pbuf[0], sizeof g_pbuf[0]);
    cModel* m1 = (cModel*) g_mbuf[1];
    cParts* p1 = (cParts*) g_pbuf[1];
    m1->pParts = (cModel*) p1;
    for (int i = 0; i < kParts; i++) {
        const uintptr_t par = (uintptr_t) parts[i].pParent;
        p1[i].pParent = par == (uintptr_t) m ? (cCoord*) m1 : (cCoord*) ((u8*) p1 + (par - (uintptr_t) parts));
    }
    g_model[0] = m, g_model[1] = m1;
}

struct Row { const char* name; unsigned calls, diff; };
Row rows[32];
int nrows;
unsigned g_models_differ;
Row& row(const char* name)
{
    for (int i = 0; i < nrows; i++)
        if (!strcmp(rows[i].name, name)) return rows[i];
    rows[nrows] = {name, 0, 0};
    return rows[nrows++];
}
PlCloth g_w[2][3];
// one call on both sides with the same inputs; then the logs, the works and the models must be equal
template <class F> void both(const char* name, F f)
{
    Row& r = row(name);
    r.calls++;
    const GlobalWork saved = *pG;
    for (int s = 0; s < 2; s++) {
        g_side = s;
        g_log[s].n = 0;
        if (s) *pG = saved;
        f(s, g_model[s], g_w[s]);
    }
    bool same = g_log[0].n == g_log[1].n && !memcmp(g_log[0].w, g_log[1].w, 4 * g_log[0].n);
    for (int i = 0; i < 3 && same; i++) {
        g_side = 0;
        const u32 a = content(&g_w[0][i]);
        g_side = 1;
        same = a == content(&g_w[1][i]);
    }
    const cModel* m0 = g_model[0];
    const cModel* m1 = g_model[1];
    if (m0->be_flag != m1->be_flag) same = false;
    if (memcmp(m0->mat, m1->mat, sizeof(Mtx))) same = false;
    const cParts* p0 = (const cParts*) g_pbuf[0];
    const cParts* p1 = (const cParts*) g_pbuf[1];
    for (int i = 0; i < kParts; i++)
        if (memcmp(p0[i].mat, p1[i].mat, sizeof(Mtx)) || memcmp(p0[i].l_mat, p1[i].l_mat, sizeof(Mtx)) ||
            memcmp(&p0[i].world, &p1[i].world, 12) || memcmp(&p0[i].pos, &p1[i].pos, 12)) {
            same = false;
            g_models_differ++;
            break;
        }
    if (!same) r.diff++;
}
}   // namespace

int main(int argc, char** argv)
{
    const unsigned N = argc > 1 ? (unsigned) atoi(argv[1]) : 3000;
    g_works[0] = g_w[0], g_works[1] = g_w[1];
    const char* c = getenv("RE4_SVC_CONTROL");
    if (c && !strcmp(c, "garmenthair")) garment_control = 1;
    if (c && !strcmp(c, "garmentskirt")) garment_control = 2;
    if (c && !strcmp(c, "lapelrate")) garment_control = 3;
    for (unsigned it = 0; it < N; it++) {
        make_model();
        pG->pl_costume = rnd() % 3;
        pG->game_costume = rnd() % 2;
        pG->Status_flg[1] = rnd() % 2 ? 0x200000 : 0;
        pG->Frame_cnt = rnd();
        const int evt = rnd() % 2;
        both("PlClothSetLeon", [](int s, cModel* m, PlCloth* w) {
            if (s == 0) o_PlClothSetLeon(m, &w[0], &w[1], &w[2]); else PlClothSetLeon(m, &w[0], &w[1], &w[2]); });
        both("PlClothMoveLeon", [](int s, cModel* m, PlCloth* w) {
            if (s == 0) o_PlClothMoveLeon(m, &w[0], &w[1], &w[2]); else PlClothMoveLeon(m, &w[0], &w[1], &w[2]); });
        both("PlClothSetGirl", [evt](int s, cModel* m, PlCloth* w) {
            if (s == 0) o_PlClothSetGirl(m, &w[0], &w[1], &w[2], evt); else PlClothSetGirl(m, &w[0], &w[1], &w[2], evt); });
        both(pG->game_costume == 1 ? "PlClothMoveGirl (costume 1: lapels)" : "PlClothMoveGirl", [](int s, cModel* m, PlCloth* w) {
            if (s == 0) o_PlClothMoveGirl(m, &w[0], &w[1], &w[2]); else PlClothMoveGirl(m, &w[0], &w[1], &w[2]); });
        both("PlClothSetLuis", [](int s, cModel* m, PlCloth* w) {
            if (s == 0) o_PlClothSetLuis(m, &w[0]); else PlClothSetLuis(m, &w[0]); });
        both("PlClothMoveLuis", [](int s, cModel* m, PlCloth* w) {
            if (s == 0) o_PlClothMoveLuis(m, &w[0]); else PlClothMoveLuis(m, &w[0]); });
        both("PlClothSetAda", [evt](int s, cModel* m, PlCloth* w) {
            if (s == 0) o_PlClothSetAda(m, &w[0], &w[1], &w[2], evt); else PlClothSetAda(m, &w[0], &w[1], &w[2], evt); });
        both("PlClothMoveAda", [](int s, cModel* m, PlCloth* w) {
            if (s == 0) o_PlClothMoveAda(m, &w[0], &w[1], &w[2]); else PlClothMoveAda(m, &w[0], &w[1], &w[2]); });
        void* bin = rnd() % 4 ? (void*) 0x1000 : 0;
        void* tpl = rnd() % 4 ? (void*) 0x2000 : 0;
        both("AdaRibbonSet", [bin, tpl](int s, cModel* m, PlCloth* w) {
            cObjChain* r = s == 0 ? o_AdaRibbonSet(m, &w[0], bin, tpl) : AdaRibbonSet(m, &w[0], bin, tpl);
            g_log[s].put(r == 0 ? 0 : (u8*) r == g_chain[s] ? 1 : 2); });
        both("girlLapelMove", [](int s, cModel* m, PlCloth*) { if (s == 0) o_girlLapelMove(m); else girlLapelMove(m); });
    }
    int bad = 0;
    for (int i = 0; i < nrows; i++) {
        printf("%-38s calls %6u differ %6u\n", rows[i].name, rows[i].calls, rows[i].diff);
        if (rows[i].diff) bad = 1;
        if (!rows[i].calls) bad = bad ? bad : 2;
    }
    printf("model differences (parts' matrices / positions) %u; native counters: sets %u moves %u lapels %u skipped %u; control %d\n",
           g_models_differ, garment_cnt.sets, garment_cnt.moves, garment_cnt.lapels, garment_cnt.skipped, garment_control);
    printf("%s\n", bad == 1 ? "FAIL: the two sides differ" : bad == 2 ? "FAIL: a function was never called" : "PASS: every call, work and part identical");
    return bad;
}
