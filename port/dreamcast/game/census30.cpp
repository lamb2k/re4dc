// CENSUS30 (census30.mk; lane perf30-census 2026-11-10; diagnostic, measurement builds only, log only). See census30.h.
// A tick = one TaskScheduler (pG->Frame_cnt). Tick k is opened before its TaskScheduler and closed before the next
// one, so it holds: tick k's logic (phase T), its Trans() after the pacer's v2 decision (phase R) and the next
// iteration's Render() that draws picture k (phase N). "drop" = re4dc_pace_drop_models after re4dc_pace_decide_image
// (picture k is never shown). Every CENSUS30_WIN ticks (and at a room change) one window is logged:
//   c30w:  window header (ticks drawn / dropped, room, Leon / Ashley construct ids)
//   c30e:  per effect id: live slot-ticks on drawn / dropped ticks, moved slot-ticks, and the outcome of every live slot
//          on drawn ticks (drawn, or the first cut / reason it was not)
//   c30o:  per effect owner: live and drawn slot-ticks (drawn ticks)
//   c30s:  per skeleton key (owner construct id, self / attached, phase): calls, parts, repeats (2nd+ pass of the same
//          model in the same tick), MotionMove, IK, pen cloth, models; drawn-tick and dropped-tick columns
//   c30r:  partsWorldCalc / getPartsPtr return addresses (callers) with phase and drawn / dropped counts
#include "types.h"
#include "global.h"
#include "model.h"
#include "em.h"
#include "espgen.h"
#include "esp.h"
#include "census30.h"

extern "C" void re4dc_log(const char* fmt, ...);
extern "C" int re4dc_pace_drop_models;
class cPlayer;
extern cPlayer* pPL;
extern cEm* pSubEm asm("pSUB");

#ifndef RE4DC_CENSUS30_WIN
#define RE4DC_CENSUS30_WIN 300
#endif

namespace {

enum { O_DRAWN, O_TCAP, O_HAZE, O_ESS, O_TRIM, O_LEVEL, O_NONE, O_EMITNP, O_STRIPNP, O_TRANSNE, O_CUSTOM, O_NQINACT, O_NQMODEL,
       O_NQNOTRANS, O_NQGHOST, O_NQCORE, O_NQTOOL, O_NOTQ, NO };
const char* const kOut[NO] = {"drawn", "tcap", "haze", "ess", "trim", "level", "none", "emit_np", "strip_np",
                              "trans_ne", "custom", "nq_inact", "nq_model", "nq_notrans", "nq_ghost", "nq_core", "nq_tool",
                              "notq"};
struct EId {
    u16 id, used;
    u32 liveD, liveX, moved, out[NO];
};
const int NE = 72;
EId eid[NE];
struct EOwn {
    u16 own, used;
    u32 live, drawn;
};
const int NOWN = 40;
EOwn eown[NOWN];
const u32 NSLOT = 1536;
u32 slotBits[NSLOT];

enum { S_CALL, S_PARTS, S_REP, S_MOT, S_IK, S_PEN, S_PENSKIP, S_CLOTH, S_MODELS, NS };
const char* const kSk[NS] = {"calls", "parts", "rep", "mot", "ik", "pen", "penskip", "cloth", "models"};
struct SK {
    u8 own, self, ph, used;
    u32 c[2][NS];
    u32 t[NS];   // this tick, moved into c[drop] at the tick's close
};
const int NSK = 64;
SK sk[NSK];
struct MR {   // one model's passes this tick
    void* m;
    u32 tick;
    u16 n;
    u8 key;
};
const int NMR = 160;
MR mr[NMR];
struct RA {
    u32 ra;
    u8 kind, ph;   // kind 0 partsWorldCalc, 1 getPartsPtr
    u32 n[2];
    u32 t;
};
const int NRA = 128;
RA ra[NRA];
u32 tickNo;              // ticks since boot (open count)
int curDrop;             // the open tick's picture is dropped
int phase;               // 1 T (TaskScheduler), 2 R (after decide: Trans...), 3 N (next iteration's Render)
void* curEm;
const void* curEsp;
u32 winTicks[2];
u32 winFirstFrame;
u16 winRoom = 0xFFFF;
u32 totLive[2], totDrawn, totQueued, maxLive, totEmit;
u32 tickLive;            // live slots counted this tick
u32 tickSkelMissed;      // keys / models that did not fit

inline u32 slotOf(const void* esp)
{
    const cEspSystem* sys = g_pEspSys;
    if (!sys || !sys->pEspBuf) {
        return ~0u;
    }
    const u32 off = (u32) ((const u8*) esp - sys->pEspBuf);
    const u32 i = off / 0x150u;
    if (off % 0x150u || i >= sys->nEsp || i >= NSLOT) {
        return ~0u;
    }
    return i;
}

EId* idEntry(u32 id)
{
    for (int i = 0; i < NE - 1; i++) {
        if (eid[i].used && eid[i].id == id) return &eid[i];
        if (!eid[i].used) {
            eid[i].used = 1;
            eid[i].id = (u16) id;
            return &eid[i];
        }
    }
    eid[NE - 1].used = 1;
    eid[NE - 1].id = 0xFFFF;   // other
    return &eid[NE - 1];
}

EOwn* ownEntry(u32 own)
{
    for (int i = 0; i < NOWN - 1; i++) {
        if (eown[i].used && eown[i].own == own) return &eown[i];
        if (!eown[i].used) {
            eown[i].used = 1;
            eown[i].own = (u16) own;
            return &eown[i];
        }
    }
    eown[NOWN - 1].used = 1;
    eown[NOWN - 1].own = 0xFFFF;
    return &eown[NOWN - 1];
}

int outcome(u32 b)
{
    if (b & C30_DRAWN) return O_DRAWN;
    if (b & C30_TCAP) return O_TCAP;
    if (b & C30_HAZE) return O_HAZE;
    if (b & C30_ESS) return O_ESS;
    if (b & C30_TRIM) return O_TRIM;
    if (b & C30_LEVEL) return O_LEVEL;
    if (b & C30_NONE) return O_NONE;
    if (b & C30_EMIT) return O_EMITNP;    // reached the sprite emit, not published (culled / alpha 0 / refused)
    if (b & C30_STRIP) return O_STRIPNP;  // strip path, not published
    if (b & C30_TRANS) return O_TRANSNE;  // EspCommonTrans ran, no emit (ineligible / shimmer / nega / early return)
    if (b & C30_CUSTOM) return O_CUSTOM;  // queued with its own trans (models, lines, special draws): not classified
    if (b & C30_NQ_INACT) return O_NQINACT;
    if (b & C30_NQ_MODEL) return O_NQMODEL;
    if (b & C30_NQ_NOTRANS) return O_NQNOTRANS;
    if (b & C30_NQ_GHOST) return O_NQGHOST;
    if (b & C30_NQ_CORE) return O_NQCORE;
    if (b & C30_NQ_TOOL) return O_NQTOOL;
    return O_NOTQ;                        // never queued (hidden flags, release time, no trans, pause)
}

u8 ownId(void* em)
{
    if (!em) return 0xFF;
    return ((cModel*) em)->id;
}

SK* skEntry(u8 own, u8 self, u8 ph)
{
    for (int i = 0; i < NSK; i++) {
        SK& s = sk[i];
        if (s.used && s.own == own && s.self == self && s.ph == ph) return &s;
        if (!s.used) {
            s.used = 1;
            s.own = own;
            s.self = self;
            s.ph = ph;
            return &s;
        }
    }
    ++tickSkelMissed;
    return 0;
}

// key of the model m in the current scope: owner = the enemy whose move runs (EmMgr.move), else the model itself if
// it is Leon / Ashley, else 0xFE (objects, effects, Trans / Render callers)
SK* skFor(void* m)
{
    u8 own, self;
    if (curEm) {
        own = ownId(curEm);
        self = m == curEm;
    } else if (m == (void*) pPL || m == (void*) pSubEm) {
        own = ownId(m);
        self = 1;
    } else {
        own = 0xFE;
        self = 0;
    }
    return skEntry(own, self, (u8) phase);
}

void raNote(void* r, u8 kind)
{
    const u32 a = (u32) r;
    for (int i = 0; i < NRA; i++) {
        RA& e = ra[i];
        if (e.n[0] + e.n[1] + e.t && e.ra == a && e.kind == kind && e.ph == phase) {
            e.t++;
            return;
        }
        if (!(e.n[0] + e.n[1] + e.t)) {
            e.ra = a;
            e.kind = kind;
            e.ph = (u8) phase;
            e.t = 1;
            return;
        }
    }
}

void clearWords(void* p, u32 bytes)
{
    volatile u32* w = (volatile u32*) p;   // volatile: no memset call
    for (u32 i = 0; i < bytes / 4; i++) w[i] = 0;
}

void flushWindow()
{
    const u32 t = winTicks[0] + winTicks[1];
    if (t) {
        re4dc_log("c30w: f=%u..%u room=%03x ticks=%u drawn=%u dropped=%u leon=%02x ash=%02x nesp=%u live/tick d=%u x=%u max=%u "
                  "queued/tick=%u emit/tick=%u drawn/tick=%u skelmiss=%u\n",
                  (unsigned) winFirstFrame, (unsigned) pG->Frame_cnt, (unsigned) winRoom, (unsigned) t,
                  (unsigned) winTicks[0], (unsigned) winTicks[1], (unsigned) (pPL ? ((cModel*) pPL)->id : 0xFF),
                  (unsigned) (pSubEm ? ((cModel*) pSubEm)->id : 0xFF), (unsigned) (g_pEspSys ? g_pEspSys->nEsp : 0),
                  (unsigned) (winTicks[0] ? totLive[0] / winTicks[0] : 0),
                  (unsigned) (winTicks[1] ? totLive[1] / winTicks[1] : 0), (unsigned) maxLive,
                  (unsigned) (winTicks[0] ? totQueued / winTicks[0] : 0), (unsigned) (winTicks[0] ? totEmit / winTicks[0] : 0),
                  (unsigned) (winTicks[0] ? totDrawn / winTicks[0] : 0), (unsigned) tickSkelMissed);
        for (int i = 0; i < NE; i++) {
            const EId& e = eid[i];
            if (!e.used) continue;
            char buf[200];
            int n = 0;
            for (int o = 0; o < NO; o++) {
                if (e.out[o]) n += __builtin_snprintf(buf + n, sizeof(buf) - n, " %s=%u", kOut[o], (unsigned) e.out[o]);
            }
            buf[n] = 0;
            re4dc_log("c30e: id=%02x liveD=%u liveX=%u moved=%u%s\n", (unsigned) e.id, (unsigned) e.liveD, (unsigned) e.liveX,
                      (unsigned) e.moved, buf);
        }
        for (int i = 0; i < NOWN; i++) {
            const EOwn& e = eown[i];
            if (!e.used) continue;
            re4dc_log("c30o: own=%02x live=%u drawn=%u\n", (unsigned) e.own, (unsigned) e.live, (unsigned) e.drawn);
        }
        for (int i = 0; i < NSK; i++) {
            const SK& s = sk[i];
            if (!s.used) continue;
            char buf[220];
            int n = 0;
            for (int d = 0; d < 2; d++) {
                n += __builtin_snprintf(buf + n, sizeof(buf) - n, " %c", d ? 'X' : 'D');
                for (int k = 0; k < NS; k++) {
                    n += __builtin_snprintf(buf + n, sizeof(buf) - n, " %s=%u", kSk[k], (unsigned) s.c[d][k]);
                }
            }
            buf[n] = 0;
            re4dc_log("c30s: own=%02x self=%u ph=%c%s\n", (unsigned) s.own, (unsigned) s.self, " TRN"[s.ph & 3], buf);
        }
        for (int i = 0; i < NRA; i++) {
            const RA& e = ra[i];
            if (!(e.n[0] + e.n[1])) continue;
            re4dc_log("c30r: k=%c ra=%08x ph=%c d=%u x=%u\n", e.kind ? 'P' : 'W', (unsigned) e.ra, " TRN"[e.ph & 3],
                      (unsigned) e.n[0], (unsigned) e.n[1]);
        }
    }
    clearWords(eid, sizeof(eid));
    clearWords(eown, sizeof(eown));
    clearWords(sk, sizeof(sk));
    clearWords(ra, sizeof(ra));
    winTicks[0] = winTicks[1] = 0;
    totLive[0] = totLive[1] = totDrawn = totQueued = maxLive = totEmit = 0;
    tickSkelMissed = 0;
    winFirstFrame = pG->Frame_cnt;
    winRoom = G_ROOM_ID;
}

void closeTick()
{
    const int d = curDrop;
    // effects: every slot touched this tick
    const cEspSystem* sys = g_pEspSys;
    const u32 n = sys && sys->pEspBuf ? (sys->nEsp < NSLOT ? sys->nEsp : NSLOT) : 0;
    u32 live = 0;
    for (u32 i = 0; i < n; i++) {
        const u32 b = slotBits[i];
        if (!b) continue;
        slotBits[i] = 0;
        if (!(b & C30_LIVE)) continue;
        const cEsp* esp = (const cEsp*) (sys->pEspBuf + i * 0x150);
        EId* e = idEntry(esp->m_Id);
        ++live;
        if (b & C30_MOVED) e->moved++;
        if (d) {
            e->liveX++;
            continue;
        }
        e->liveD++;
        const int o = outcome(b);
        e->out[o]++;
        EOwn* w = ownEntry(esp->info.owner);
        w->live++;
        if (o == O_DRAWN) {
            w->drawn++;
            ++totDrawn;
        }
        if (b & C30_QUEUED) ++totQueued;
        if (b & C30_EMIT) ++totEmit;
    }
    totLive[d] += live;
    if (live > maxLive) maxLive = live;
    // skeleton: this tick's counts go to the drawn / dropped columns now that the pacer has decided
    for (int i = 0; i < NSK; i++) {
        SK& k = sk[i];
        if (!k.used) continue;
        for (int j = 0; j < NS; j++) {
            k.c[d][j] += k.t[j];
            k.t[j] = 0;
        }
    }
    for (int i = 0; i < NRA; i++) {
        ra[i].n[d] += ra[i].t;
        ra[i].t = 0;
    }
    // skeleton: distinct models this tick, per key
    for (int i = 0; i < NMR; i++) {
        MR& r = mr[i];
        if (r.m && r.tick == tickNo) {
            if (r.key < NSK) sk[r.key].c[d][S_MODELS]++;
        }
    }
    winTicks[d]++;
}

}   // namespace

extern "C" void re4dc_c30_tick_open(void)
{
    if (tickNo) {
        closeTick();
    }
    if (winRoom != G_ROOM_ID || winTicks[0] + winTicks[1] >= RE4DC_CENSUS30_WIN) {
        flushWindow();
    }
    ++tickNo;
    curDrop = 0;
    phase = 1;
}

extern "C" void re4dc_c30_decided(int drop)
{
    curDrop = drop ? 1 : 0;
    phase = 2;
}

extern "C" void re4dc_c30_render(void)
{
    phase = 3;
}

extern "C" void re4dc_c30_em(void* em)
{
    curEm = em;
}

extern "C" void re4dc_c30_pwc(void* m, void* r)
{
    if (!tickNo) return;
    SK* s = skFor(m);
    raNote(r, 0);
    if (!s) return;
    s->t[S_CALL]++;
    s->t[S_PARTS] += ((cModel*) m)->nParts;
    // repeats: the model's 2nd+ pass this tick
    int fr = -1;
    for (int i = 0; i < NMR; i++) {
        MR& e = mr[i];
        if (e.m == m && e.tick == tickNo) {
            if (++e.n > 1) s->t[S_REP]++;
            return;
        }
        if (fr < 0 && (e.m == 0 || e.tick != tickNo)) fr = i;
    }
    if (fr < 0) {
        ++tickSkelMissed;
        return;
    }
    mr[fr].m = m;
    mr[fr].tick = tickNo;
    mr[fr].n = 1;
    mr[fr].key = (u8) (s - sk);
}

extern "C" void re4dc_c30_motion(void* m)
{
    if (!tickNo) return;
    if (SK* s = skFor(m)) s->t[S_MOT]++;
}

extern "C" void re4dc_c30_ik(void* m)
{
    if (!tickNo) return;
    if (SK* s = skFor(m)) s->t[S_IK]++;
}

extern "C" void re4dc_c30_pen(void* m)
{
    if (!tickNo) return;
    if (SK* s = skFor(m)) s->t[S_PEN]++;
}

extern "C" void re4dc_c30_penskip(void* m)
{
    if (!tickNo) return;
    if (SK* s = skFor(m)) s->t[S_PENSKIP]++;
}

extern "C" void re4dc_c30_trim(const void* esp, int why, int drawn)
{
    if (why == 5) {
        re4dc_c30_esp_mark(esp, C30_ESS);
    } else if (why) {
        re4dc_c30_esp_mark(esp, C30_TRIM);
    } else if (!drawn) {
        re4dc_c30_esp_mark(esp, C30_LEVEL);
    }
}

extern "C" void re4dc_c30_cloth(void* c)
{
    (void) c;
    if (!tickNo) return;
    if (SK* s = skEntry(curEm ? ownId(curEm) : 0xFE, 0, (u8) phase)) s->t[S_CLOTH]++;
}

extern "C" void re4dc_c30_ptr(void* r)
{
    if (!tickNo) return;
    raNote(r, 1);
}

extern "C" void re4dc_c30_esp_live(const void* esp, int moved)
{
    const u32 i = slotOf(esp);
    if (i == ~0u) return;
    slotBits[i] |= C30_LIVE | (moved ? C30_MOVED : 0u);
}

extern "C" void re4dc_c30_esp_mark(const void* esp, unsigned bit)
{
    if (!esp) return;
    const u32 i = slotOf(esp);
    if (i == ~0u) return;
    slotBits[i] |= (u16) bit;
}

extern "C" void re4dc_c30_esp_cur(const void* esp)
{
    curEsp = esp;
}

extern "C" void re4dc_c30_cut(unsigned bit)
{
    if (curEsp) re4dc_c30_esp_mark(curEsp, bit);
}
