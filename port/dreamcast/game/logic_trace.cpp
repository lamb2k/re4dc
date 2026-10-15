// Determinism trace (LOGIC_TRACE=1 in game30.mk; never in a product image).
//
// Proves that a build or code change leaves the game logic bit-identical: once per frame-loop
// iteration (src/game/main.cpp, top of the loop, i.e. after the previous iteration's complete
// logic + render pass) it logs one fingerprint line of the logic state through the existing RAM
// log ring (re4dc_log -> re4dc_logbuf, read by the evidence read_log.py; serial on hardware).
// tools/logic_trace_diff.py compares two runs. Read-only: nothing here writes game state, and
// no pointer value is hashed (heap addresses legitimately move with the image size).
//
//   LT t=<Frame_cnt> n=<sample> r=<rng16> sy=<System_flg> sp=<Stop_flg> st=<H Status_flg[4]>
//      rf=<H Room_flg[4]> sc=<H Scenario_flg,Item_find_flg> rm=<stage<<8|room>
//      p=<player pos bits> a=<player ang bits> m=<Mot_frame bits>/<Mot_state>
//      ps=<H player discrete> pf=<H player coords> pm=<H player parts>
//   LU t=<Frame_cnt> n=<sample> e=<alive enemies> es=<H discrete> ef=<H coords> em=<H parts>
//      o=<alive objects> os=<H discrete> of=<H coords> om=<H parts> c=<H camera>
// discrete = be_flag, r_no_0..3, id/type, hp (enemies), Motion.Mot_state: sequencing / AI state.
// coords   = cCoord 0x0C..0xF4 without pParent: mat, l_mat, world, world_old(2), pos, ang, scale,
//            r_scale, prevMat, plus pos_old, speed and Motion.Mot_frame: where collision lands.
// parts    = the same coordinate block of every cParts on the model's pParts chain (world
//            matrices from partsWorldCalc: the MTXConcat/MultVec consumers).
//
// The trace also reports fixture state "room" = <stage<<8|room>/<player placed> for the pad
// script (fixtures/padscript-trace.txt), so gameplay inputs are keyed to the room anchor.
//
// RE4DC_LOGIC_TRACE_DELAY_US=N burns N microseconds per record: the timing-perturbation control.
// A run of the reference build with N > 0 must be STRICT against the same build with N = 0
// before any A/B verdict is trusted (it proves the fixture is insensitive to CPU speed).
#include "global.h"
#include "player.h"
#include "em.h"
#include "obj.h"
#include "re4dc_platform.h"
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
#include "esp.h"
#include "espgen.h"
#include "logic_trace_effects.h"
extern EspgenWork* EspgenArray;   // espgen.cpp
extern u32 nEspgen;
#endif
#include <string.h>
#ifndef RE4DC_LOGIC_TRACE_SWAPPED
#define RE4DC_LOGIC_TRACE_SWAPPED 0
#endif
// LOGIC_TRACE_OWNERSHIP=1 (schema 5): the room lists (player, enemies, objects, effects, effect generators) are
// read only while the current room owns them. main_mem.h RE4DC_TRACE_OWNER_RELEASE marks all of them released
// where the source hands their memory back to a heap (StageSet heap reload / REL relink, gameRoomMemInit), and
// RE4DC_TRACE_OWNER_PUBLISH marks each one owned again right after gameRoomInit resets its head. A released
// domain is logged as "-" with the owner mask "ow=" instead of hashing freed memory; the globals, camera and
// decision hashes are recorded every tick. Off: the records are exactly as before.
#ifndef RE4DC_LOGIC_TRACE_OWNERSHIP
#define RE4DC_LOGIC_TRACE_OWNERSHIP 0
#endif
#if RE4DC_LOGIC_TRACE_OWNERSHIP
#include "main_mem.h"
#include <stdio.h>
#endif
#if RE4DC_LOGIC_TRACE_SWAPPED
#include "trace_region_view.hpp"
extern "C" int re4dc_ssb_trace_begin(unsigned);
extern "C" int re4dc_ssb_trace_append(const void*,unsigned,unsigned*);
extern "C" int re4dc_ssb_trace_read(void*,unsigned,unsigned);
extern "C" int re4dc_ssb_trace_index_push(const void*);
extern "C" int re4dc_ssb_trace_index_read(unsigned,void*);
extern "C" int re4dc_ssb_trace_index_write(unsigned,const void*);
extern "C" void re4dc_ssb_trace_layout(unsigned*);
#endif

#ifndef RE4DC_LOGIC_TRACE_DELAY_US
#define RE4DC_LOGIC_TRACE_DELAY_US 0
#endif
// LOGIC_TRACE_MASK_RENDER=1 (opt-in; frame pacing gates): be_flag 0x08000000 is left out of the
// discrete hash. It is the ot_type-7 first-pass draw marker, set at the end of the model draw
// (trans.cpp commonModelTrans / frontNativeRender), cleared by ModelTrans and read only by the
// draw walk; a skipped draw changes it and nothing else. tools/d367/be_flag_render_bit.py fails
// when any other reader appears. 0 (default): every hash is exactly as before.
#ifndef RE4DC_LOGIC_TRACE_MASK_RENDER
#define RE4DC_LOGIC_TRACE_MASK_RENDER 0
#endif

extern "C" unsigned short re4dc_rnd_state(void);   // src/game/rnd.cpp (trace builds only)
#if RE4DC_LOGIC_TRACE_DELAY_US
#include <kos/timer.h>   // timer_us_gettime64 (static inline)
#endif

#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
// Set by snd.cpp around the sound system's own line / area queries: how many run per tick follows
// audio playback time (end_check_tbl), so they go to bucket 6 ("sq") instead of the gameplay buckets.
// Global scope: an extern "C" name defined inside the unnamed namespace links to a silent stub.
extern "C" unsigned re4dc_dt_snd;
unsigned re4dc_dt_snd;
#if defined(RE4DC_DT_IK_APART) && RE4DC_DT_IK_APART
// DT_IK_APART=1 (game30.mk): set by MotionMove around the leg IK; its floor queries go to bucket 7 (not logged).
extern "C" unsigned re4dc_dt_ik;
unsigned re4dc_dt_ik;
#endif
#endif

namespace {
#if RE4DC_LOGIC_TRACE_SWAPPED
// Only the exact raw ranges consumed by the trace are retained. No game data is changed.
// The span index is kept in the same backing store's spare capacity, not in game RAM (trace_spare.hpp).
struct TraceVramBacking {
    static constexpr bool kIndexInBacking=true;
    bool append(const void* p,unsigned n,unsigned* offset) { return re4dc_ssb_trace_append(p,n,offset)!=0; }
    bool read(void* dst,unsigned offset,unsigned n) const { return re4dc_ssb_trace_read(dst,offset,n)!=0; }
    bool index_push(const void* e) { return re4dc_ssb_trace_index_push(e)!=0; }
    bool index_read(unsigned i,void* e) const { return re4dc_ssb_trace_index_read(i,e)!=0; }
    bool index_write(unsigned i,const void* e) { return re4dc_ssb_trace_index_write(i,e)!=0; }
};
// Span capacity: 6144 default, 16384 for the large-room diagnostic (8 B each, in the backing store;
// game RAM keeps one 4-byte fence per 32 spans).
#ifndef RE4DC_LOGIC_TRACE_SPANS
#define RE4DC_LOGIC_TRACE_SPANS 6144
#endif
TraceRegionView<RE4DC_LOGIC_TRACE_SPANS,TraceVramBacking> g_trace_region;
void trace_copy(void* dst,const void* src,unsigned bytes) {
    const bool captured=g_trace_region.capture(src,bytes);
    const bool copied=captured && g_trace_region.copy(dst,src,bytes);
    if (!copied) {
        re4dc_log("LTSFAIL src=%08x bytes=%u spans=%u used=%u capturing=%u active=%u captured=%u lo=%08x hi=%08x\n",unsigned(src),bytes,g_trace_region.count,g_trace_region.used,unsigned(g_trace_region.capturing),unsigned(g_trace_region.active),unsigned(captured),unsigned(g_trace_region.lo),unsigned(g_trace_region.hi));
        re4dc_missing("logic trace: uncaptured or overflowing borrowed-memory read");
    }
}
template<class T> T trace_value(const T* src) {
    T value; trace_copy(&value,src,sizeof(value)); return value;
}
#else
// Preserve the original access expressions and generated code when the diagnostic is off.
#define trace_copy(dst,src,bytes) memcpy(dst,src,bytes)
#define trace_value(src) (*(src))
#endif
struct Fnv {
    unsigned h = 2166136261u;
    void word(unsigned w) { h = (h ^ w) * 16777619u; }
    void words(const void* p, unsigned bytes) {
        const unsigned char* b = (const unsigned char*) p;
#if RE4DC_LOGIC_TRACE_SWAPPED
        if (!g_trace_region.capture(p,bytes & ~3U))
            re4dc_missing("logic trace: borrowed-memory range capacity");
#endif
        for (unsigned i = 0; i + 4 <= bytes; i += 4) {
            unsigned w;
            #if RE4DC_LOGIC_TRACE_SWAPPED
            if (!g_trace_region.copy(&w,b+i,4))
                re4dc_missing("logic trace: borrowed-memory word absent");
#else
            memcpy(&w,b+i,4);
#endif
            word(w);
        }
    }
    template <class T> void add(const T& v) {
        unsigned w = 0;
        trace_copy(&w, &v, sizeof(v) < 4 ? sizeof(v) : 4);
        word(w);
    }
};

#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
// GAME_DECISION_TRACE (test builds): decision results hashed per sample, in call order: 0 em-em
// collision (at_mod.cpp), 1 scenery line tests (at_sub.cpp), 2 area checks (sce_at.cpp), 3 damage hit
// tests (dmg.cpp), 4 line query answers and 5 their hit points (atari.cpp). Logged as "LX", with every alive enemy's position bits every 4th sample ("LP").
static Fnv g_dt[8];
static unsigned g_dtn[8];
#if RE4DC_DECISION_TRACE == 2
// Private diagnostic: frames around the tr18/tr19 line-query differences.
extern "C" int re4dc_dt_window(void)
{
    static const unsigned f[] = {644, 1087, 1287, 1729, 2417, 2814, 3183, 3530};
    const unsigned c = (unsigned) pG->Frame_cnt;
    for (unsigned k = 0; k < sizeof(f) / sizeof(f[0]); ++k)
        if (c + 2 >= f[k] && c <= f[k] + 1) return (int) c;
    return -1;
}
#endif
#if defined(RE4DC_LQ_MEMO) && RE4DC_LQ_MEMO
extern "C" void re4dc_lqm_note(unsigned kind, unsigned a, unsigned b);   // GAME_LQ_MEMO (atari.cpp): its recorder
#endif
extern "C" unsigned re4dc_dt_note(unsigned kind, unsigned a, unsigned b)
{
#if defined(RE4DC_LQ_MEMO) && RE4DC_LQ_MEMO
    re4dc_lqm_note(kind, a, b);
#endif
    if (re4dc_dt_snd) kind = 6;
#if defined(RE4DC_DT_IK_APART) && RE4DC_DT_IK_APART
    if (re4dc_dt_ik) kind = 7;
#endif
    g_dt[kind & 7].word(a);
    g_dt[kind & 7].word(b);
    ++g_dtn[kind & 7];
    return b;
}
#endif
inline unsigned bits(float f) { unsigned u; memcpy(&u, &f, 4); return u; }

// cCoord 0x0C..0x6C (mat, l_mat) and 0x70..0xF4 (world .. prevMat): skips the vptr and pParent.
void coord_block(Fnv& f, const void* unit)
{
    const unsigned char* b = (const unsigned char*) unit;
    f.words(b + 0x0C, 0x6C - 0x0C);
    f.words(b + 0x70, 0xF4 - 0x70);
}

void model_state(Fnv& discrete, Fnv& coords, Fnv& parts, cModel* m)
{
#if RE4DC_LOGIC_TRACE_MASK_RENDER
    discrete.add(trace_value(&m->be_flag) & ~0x08000000u);
#else
    discrete.add(m->be_flag);
#endif
    discrete.add(m->stat);
    discrete.add(m->id);
    discrete.add(m->type);
    discrete.add(m->Motion.Mot_state);
    coord_block(coords, m);
    coords.words(&m->speed, sizeof(Vec) * 2);   // speed 0x104, pos_old 0x110
    coords.add(m->Motion.Mot_frame);
    unsigned n = 0;
    for (cModel* p = trace_value(&m->pParts); p && n < 256;
         p = (cModel*) trace_value(&((cParts*) p)->pList), ++n)
        coord_block(parts, p);
    parts.word(n);
}

#if defined(RE4DC_LOGIC_TRACE_EM_TO) && RE4DC_LOGIC_TRACE_EM_TO
// LOGIC_TRACE_EM_FROM/TO (game30.mk; diagnostic, default off): every alive enemy's es inputs (be_flag, the r_no
// bytes, id, type, Mot_state, hp) with its Mot_frame and position bits, its address and first word (the vtable:
// the class), for Frame_cnt FROM..TO ("LE" lines), so an es difference names the enemy and the field.
template <class T> unsigned em_w4(const T& v)
{
    unsigned w = 0;
    memcpy(&w, &v, sizeof(v) < 4 ? sizeof(v) : 4);
    return w;
}
void em_diag(unsigned k, cEm* e)
{
    const unsigned t = (unsigned) pG->Frame_cnt;
    if (t < RE4DC_LOGIC_TRACE_EM_FROM || t > RE4DC_LOGIC_TRACE_EM_TO) return;
    unsigned vt;
    memcpy(&vt, (const void*) e, 4);
    re4dc_log("LE t=%u k=%u id=%x type=%x be=%08x stat=%08x ms=%x hp=%x mf=%08x pos=%08x,%08x,%08x a=%08x vt=%08x\n",
              t, k, em_w4(e->id), em_w4(e->type), em_w4(e->be_flag), em_w4(e->stat), em_w4(e->Motion.Mot_state),
              em_w4(e->hp), em_w4(e->Motion.Mot_frame), em_w4(e->pos.x), em_w4(e->pos.y), em_w4(e->pos.z),
              (unsigned) (unsigned long) e, vt);
}
#endif

unsigned samples;

// Room digest (hardware check without a serial link, see re4dc_logic_trace_digest).
constexpr unsigned kDigestEvery = 600;
unsigned g_digRoom = ~0u, g_digTicks;
bool g_digStarted;
Fnv g_dig;
unsigned g_latchRoom, g_latchTicks, g_latchDigest;
#if RE4DC_LOGIC_TRACE_OWNERSHIP
// Owned domains (RE4DC_OWN_*), release events so far, the room the player list was last published for, and
// the release generation the running room digest belongs to. Boot: every head is null, so all are owned.
unsigned g_own = RE4DC_OWN_ALL, g_ownGen, g_ownPubRoom = ~0u, g_digGen;
unsigned cur_room() { return pG ? (unsigned(pG->stage_no) << 8) | pG->room_no : 0xFFFFu; }
#endif
}  // namespace

// TRACE_ALLOC=1 (Phase 2 D5, needs LOGIC_TRACE=1): every failed required heap-4 allocation (main_mem.cpp mem_alloc
// with flag 1, the "alloc[..]:free[..]" log; the native parts run in parts_bridge.cpp) is counted and hashed with its
// size and site tag, and the LU record ends "af=<count>/<hash>", a must-match field. A layout-dependent spawn then
// shows up as an allocation event on the tick it happens ("LA" line) instead of as later enemy-count drift.
// TRACE_SS_MASK=1 (D5): while the sub screen backing has the room's memory swapped out (sscrn_bridge.cpp), the player,
// enemy and object fields read swapped memory (layout-dependent garbage in both arms): they are printed as "~" and
// the enemy / object lists are not walked. Globals, flags, RNG and camera are still recorded. The pad fixture feed
// keeps its exact old reads. Both off: records and code exactly as before.
#ifndef RE4DC_TRACE_ALLOC
#define RE4DC_TRACE_ALLOC 0
#endif
#ifndef RE4DC_TRACE_SS_MASK
#define RE4DC_TRACE_SS_MASK 0
#endif
#if RE4DC_TRACE_ALLOC
#include <stdio.h>
namespace { unsigned g_af; Fnv g_afh; }
void re4dc_logic_trace_alloc_fail(unsigned size, const char* site)
{
    ++g_af;
    g_afh.word(size);
    for (const char* c = site ? site : ""; *c; ++c) g_afh.word((unsigned char) *c);
    re4dc_log("LA t=%u n=%u size=%x site=%s af=%u/%08x\n", pG ? (unsigned) pG->Frame_cnt : 0u, samples, size,
              site ? site : "", g_af, g_afh.h);
}
#endif
#if RE4DC_TRACE_SS_MASK
namespace { volatile int g_ssOpen; }
extern "C" void re4dc_logic_trace_ss_mask(int open)  // sscrn_bridge.cpp declares it in C linkage
{
    g_ssOpen = open;
    re4dc_log("LSS t=%u n=%u open=%d\n", pG ? (unsigned) pG->Frame_cnt : 0u, samples, open);
}
#define RE4DC_SS_MASKED (g_ssOpen != 0)
#else
#define RE4DC_SS_MASKED false
#endif

#if RE4DC_LOGIC_TRACE_OWNERSHIP
// Source room lifetime sites (main_mem.h). "n" is the last logged sample: the change applies from sample n+1.
// A publish of a domain that is already owned is an invalid sequence; it is logged ("again"), not hidden.
extern "C" void re4dc_trace_owner_release(unsigned site)
{
    const unsigned was = g_own;
    g_own = 0;
    ++g_ownGen;
    re4dc_log("LO release n=%u t=%u site=%u g=%u was=%02x rm=%04x\n", samples, pG ? (unsigned) pG->Frame_cnt : 0,
              site, g_ownGen, was, cur_room());
}
extern "C" void re4dc_trace_owner_publish(unsigned domains)
{
    const unsigned again = g_own & domains;
    g_own |= domains & RE4DC_OWN_ALL;
    if (domains & RE4DC_OWN_PL) g_ownPubRoom = cur_room();
    re4dc_log("LO publish n=%u t=%u d=%02x own=%02x g=%u again=%02x rm=%04x\n", samples,
              pG ? (unsigned) pG->Frame_cnt : 0, domains, g_own, g_ownGen, again, cur_room());
}
#endif

#if RE4DC_LOGIC_TRACE_SWAPPED
// Called after backing save but before the owner swap, and after complete restoration, respectively.
// Global C linkage is required by the source bridge.
extern "C" void re4dc_logic_trace_swap_open(void* base,unsigned bytes,unsigned saved_end) {
    if(!re4dc_ssb_trace_begin(saved_end))re4dc_missing("logic trace: backing store not ready");
    if (!g_trace_region.begin(base,bytes)) re4dc_missing("logic trace: nested memory borrow");
    Fnv d,c,p;
#if RE4DC_LOGIC_TRACE_OWNERSHIP
    // Capture what the tick will read: owned lists only, plus the fixture feed's three position words.
    if(pPL && (g_own&RE4DC_OWN_PL)) model_state(d,c,p,pPL);
    else if(pPL && !g_trace_region.capture(&pPL->pos,sizeof(pPL->pos)))
        re4dc_missing("logic trace: fixture position capture");
    unsigned n=0;
    cUnit* u=(g_own&RE4DC_OWN_EM)?(cUnit*)EmMgr.pAlive:0;
#else
    if(pPL) model_state(d,c,p,pPL);
    unsigned n=0;
    cUnit* u=(cUnit*)EmMgr.pAlive;
#endif
    for(;u && n<1024;u=trace_value(&u->pNext),++n) {
        cEm* e=(cEm*)u; model_state(d,c,p,e);d.add(e->hp);
    }
    if(u)re4dc_missing("logic trace: enemy capture walk limit");
#if RE4DC_LOGIC_TRACE_OWNERSHIP
    n=0;u=(g_own&RE4DC_OWN_OB)?(cUnit*)ObjMgr.pAlive:0;
#else
    n=0;u=(cUnit*)ObjMgr.pAlive;
#endif
    for(;u && n<1024;u=trace_value(&u->pNext),++n) model_state(d,c,p,(cModel*)u);
    if(u)re4dc_missing("logic trace: object capture walk limit");
    if(!g_trace_region.seal())re4dc_missing("logic trace: memory borrow seal");
    re4dc_log("LTS open t=%u lo=%08x size=%u spans=%u bytes=%u\n",
        pG?(unsigned)pG->Frame_cnt:0,unsigned(base),bytes,g_trace_region.count,g_trace_region.used);
    unsigned layout[5];
    re4dc_ssb_trace_layout(layout);
    re4dc_log("LTSMETA saved_end=%u data_end=%u index_low=%u index_top=%u capacity=%u index_bytes=%u spare_left=%u\n",
        layout[0],layout[1],layout[2],layout[3],layout[4],layout[3]-layout[2],layout[2]-layout[1]);
}
extern "C" void re4dc_logic_trace_swap_close() {
    const bool restored=g_trace_region.restored();
    re4dc_log("LTS close t=%u restored=%u spans=%u bytes=%u\n",
        pG?(unsigned)pG->Frame_cnt:0,unsigned(restored),g_trace_region.count,g_trace_region.used);
    if(!restored)re4dc_missing("logic trace: borrowed game bytes were not restored");
    g_trace_region.end();
}
#endif

// Last latched room digest: FNV over every LT/LU field of every tick since the room anchor (the
// first tick of the current room with the player placed, the anchor logic_trace_diff.py
// --align room uses), latched every 600 anchor ticks and logged as
//   LD t=<Frame_cnt> rm=<room> k=<ticks since anchor> d=<digest>
// On a console without a serial link (GDEMU) an on-screen readout (PERF_HUD) shows the latched
// triple; equal (rm, k, d) on hardware and in Flycast under the same pad fixture means the whole
// room run was bit-identical, which checks Flycast's FPU (fmac) against the SH-4. Returns 0 until
// the first latch. Kept by --gc-sections through the shared input section.
extern "C" __attribute__((section(".text.re4dc_logic_trace"))) int re4dc_logic_trace_digest(unsigned* room,
                                                                                           unsigned* ticks,
                                                                                           unsigned* digest)
{
    if (!g_latchTicks) return 0;
    if (room) *room = g_latchRoom;
    if (ticks) *ticks = g_latchTicks;
    if (digest) *digest = g_latchDigest;
    return 1;
}


#if defined(RE4DC_H2_EXTERNAL_DELAY) && RE4DC_H2_EXTERNAL_DELAY
#include "main.h"
#include <kos/fs.h>
#include <kos/timer.h>
#include <fcntl.h>
namespace {
unsigned h2_delay;
bool h2_delay_read;
void h2_probe_delay() {
    if (!h2_delay_read) {
        h2_delay_read=true;
        const file_t f=fs_open("/cd/dc/h2_delay.bin",O_RDONLY);
        unsigned value=0;
        if(f<0) re4dc_missing("H2 delay file missing");
        const int got=fs_read(f,&value,sizeof(value));
        fs_close(f);
        if(got!=sizeof(value) || value>20000) re4dc_missing("H2 delay file invalid");
        h2_delay=value;
        re4dc_log("H2CFG delay_us=%u raw=%u\n",h2_delay,value);
    }
    if(pG->Frame_cnt>=1668 && pG->Frame_cnt<=1675)
        re4dc_log("H2STATUS t=%u sf=%08x/%08x/%08x/%08x key_on=%08x key_trg=%08x\n",
            (unsigned)pG->Frame_cnt, (unsigned)pG->Status_flg[0], (unsigned)pG->Status_flg[1],
            (unsigned)pG->Status_flg[2], (unsigned)pG->Status_flg[3], (unsigned)Key.on, (unsigned)Key.trg);
    if(h2_delay && pG->Frame_cnt<1800) {
        const unsigned long long end=timer_us_gettime64()+h2_delay;
        while(timer_us_gettime64()<end) {}
    }
}
}
#endif

extern "C" __attribute__((section(".text.re4dc_logic_trace"))) void re4dc_logic_trace_tick(void)
{
#if RE4DC_LOGIC_TRACE_DELAY_US
    {
        const unsigned long long until = timer_us_gettime64() + RE4DC_LOGIC_TRACE_DELAY_US;
        while (timer_us_gettime64() < until) {
        }
    }
#endif
    if (!pG) return;
#if defined(RE4DC_H2_EXTERNAL_DELAY) && RE4DC_H2_EXTERNAL_DELAY
    h2_probe_delay();
#endif
#if RE4DC_LOGIC_TRACE_OWNERSHIP
    if (!samples)
        re4dc_log("LTV version=5 model_memory=%s owners=pl,em,ob,ep,eg\n",
                  RE4DC_LOGIC_TRACE_SWAPPED ? "borrow-vram-all" : "direct");
#elif RE4DC_LOGIC_TRACE_SWAPPED
    if (!samples) re4dc_log("LTV version=4 model_memory=borrow-vram-all\n");
#endif
#if RE4DC_TRACE_ALLOC || RE4DC_TRACE_SS_MASK
    if (!samples) re4dc_log("LTV extras alloc=%d ss_mask=%d\n", RE4DC_TRACE_ALLOC, RE4DC_TRACE_SS_MASK);
    const bool ssm = RE4DC_SS_MASKED;
#endif
    ++samples;
    Fnv st, rf, sc, cam, ps, pf, pm, es, ef, em, os, of, om;
#if RE4DC_LOGIC_TRACE_MASK_RENDER
    {
        // Render-only bits (set / cleared by draw stages a dropped image skips; read only by draw
        // code): [1] 0x08000000 texture-render effects queued (EspTrans, CopyTexRenderMgr),
        // [1] 0x4000 shadow texture made (make_shadow_texture, ShadowTrans), [2] 0x00100000 shadow
        // lights exist (ShadowTrans), [3] 0x10000000 letterbox scissor (inside Render).
        u32 sf[sizeof(pG->Status_flg) / 4];
        memcpy(sf, pG->Status_flg, sizeof(sf));
        sf[1] &= ~0x08004000u;
        sf[2] &= ~0x00100000u;
        sf[3] &= ~0x10000000u;
        st.words(sf, sizeof(sf));
    }
#else
    st.words(pG->Status_flg, sizeof(pG->Status_flg));
#endif
    rf.words(pG->Room_flg, sizeof(pG->Room_flg));
    sc.words(pG->Scenario_flg, sizeof(pG->Scenario_flg));
    sc.add(pG->Item_find_flg);
    cam.words(&pG->Cam.param, 32);
    unsigned p[3] = {0, 0, 0}, a[3] = {0, 0, 0}, mf = 0, ms = 0;
#if RE4DC_LOGIC_TRACE_OWNERSHIP
    const unsigned own = g_own;
    if (pPL && (own & RE4DC_OWN_PL)) {
#else
    if (pPL) {
#endif
        model_state(ps, pf, pm, pPL);
        p[0] = bits(trace_value(&pPL->pos.x)); p[1] = bits(trace_value(&pPL->pos.y)); p[2] = bits(trace_value(&pPL->pos.z));
        a[0] = bits(trace_value(&pPL->ang.x)); a[1] = bits(trace_value(&pPL->ang.y)); a[2] = bits(trace_value(&pPL->ang.z));
        mf = bits(trace_value(&pPL->Motion.Mot_frame)); ms = trace_value(&pPL->Motion.Mot_state);
    }
    unsigned ne = 0, no = 0;
#if RE4DC_LOGIC_TRACE_OWNERSHIP
    for (cUnit* u = (own & RE4DC_OWN_EM) ? (cUnit*) EmMgr.pAlive : 0; u && ne < 1024; u = trace_value(&u->pNext), ++ne) {
#else
#if RE4DC_TRACE_SS_MASK
    for (cUnit* u = ssm ? 0 : (cUnit*) EmMgr.pAlive; u && ne < 1024; u = trace_value(&u->pNext), ++ne) {
#else
    for (cUnit* u = (cUnit*) EmMgr.pAlive; u && ne < 1024; u = trace_value(&u->pNext), ++ne) {
#endif
#endif
        cEm* e = (cEm*) u;
        model_state(es, ef, em, e);
        es.add(e->hp);
#if defined(RE4DC_LOGIC_TRACE_EM_TO) && RE4DC_LOGIC_TRACE_EM_TO
        em_diag(ne, e);
#endif
    }
#if RE4DC_LOGIC_TRACE_OWNERSHIP
    for (cUnit* u = (own & RE4DC_OWN_OB) ? (cUnit*) ObjMgr.pAlive : 0; u && no < 1024; u = trace_value(&u->pNext), ++no)
#elif RE4DC_TRACE_SS_MASK
    for (cUnit* u = ssm ? 0 : (cUnit*) ObjMgr.pAlive; u && no < 1024; u = trace_value(&u->pNext), ++no)
#else
    for (cUnit* u = (cUnit*) ObjMgr.pAlive; u && no < 1024; u = trace_value(&u->pNext), ++no)
#endif
        model_state(os, of, om, (cModel*) u);
    const unsigned rng = re4dc_rnd_state();
    const unsigned room = (unsigned(pG->stage_no) << 8) | pG->room_no;
    // Fixture sync state for the scripted pad input (platform/pad.cpp "room=<id>/<player>"): lets a
    // gameplay route start at the room's first tick with the player placed, the same anchor
    // logic_trace_diff.py --align room uses, so inputs land on the same room tick in A and B
    // even when loading took a different number of frames. Platform-side only.
#if RE4DC_LOGIC_TRACE_OWNERSHIP
    // The feed keeps its exact pre-schema-5 value. While the player list is released this still reads the
    // three position words at the stale pPL address (mapped main RAM, read only), exactly as before, so the
    // fixture clock cannot move; those words are not recorded as player state.
    unsigned placed = p[0] | p[1] | p[2];
    if (pPL && !(own & RE4DC_OWN_PL))
        placed = bits(trace_value(&pPL->pos.x)) | bits(trace_value(&pPL->pos.y)) | bits(trace_value(&pPL->pos.z));
    re4dc_fixture_state("room", (int) room, placed ? 1 : 0);
#else
    re4dc_fixture_state("room", (int) room, (p[0] | p[1] | p[2]) ? 1 : 0);
#endif
    // Two lines per sample: re4dc_log formats into a 256-byte buffer and one line would be ~300
    // characters (the enemy/object/camera fields would be cut off). logic_trace_diff.py joins the
    // LT and LU halves of a sample by (t, n) and drops a sample whose other half is missing.
#if RE4DC_LOGIC_TRACE_OWNERSHIP
    // A released domain prints "-" for each of its fields; "ow=<owned mask>/<release generation>" ends LT.
    char pl[160], el[64], ol[64];
    if (own & RE4DC_OWN_PL)
        snprintf(pl, sizeof(pl), "p=%08x,%08x,%08x a=%08x,%08x,%08x m=%08x/%x ps=%08x pf=%08x pm=%08x", p[0], p[1],
                 p[2], a[0], a[1], a[2], mf, ms, ps.h, pf.h, pm.h);
    else
        strcpy(pl, "p=- a=- m=- ps=- pf=- pm=-");
    if (own & RE4DC_OWN_EM) snprintf(el, sizeof(el), "e=%u es=%08x ef=%08x em=%08x", ne, es.h, ef.h, em.h);
    else strcpy(el, "e=- es=- ef=- em=-");
    if (own & RE4DC_OWN_OB) snprintf(ol, sizeof(ol), "o=%u os=%08x of=%08x om=%08x", no, os.h, of.h, om.h);
    else strcpy(ol, "o=- os=- of=- om=-");
    re4dc_log("LT t=%u n=%u r=%04x sy=%08x sp=%08x st=%08x rf=%08x sc=%08x rm=%04x %s ow=%02x/%u\n",
              (unsigned) pG->Frame_cnt, samples, rng, (unsigned) pG->System_flg, (unsigned) pG->Stop_flg, st.h,
              rf.h, sc.h, room, pl, own, g_ownGen);
    re4dc_log("LU t=%u n=%u %s %s c=%08x\n", (unsigned) pG->Frame_cnt, samples, el, ol, cam.h);
#else
#if RE4DC_TRACE_ALLOC
    char afl[24];
    snprintf(afl, sizeof(afl), " af=%u/%08x", g_af, g_afh.h);
#else
    const char* afl = "";
#endif
#if RE4DC_TRACE_SS_MASK
    if (ssm) {
        // Same layout, every player / enemy / object field "~"; values zeroed for the room digest below.
        re4dc_log("LT t=%u n=%u r=%04x sy=%08x sp=%08x st=%08x rf=%08x sc=%08x rm=%04x p=~,~,~ a=~,~,~ m=~/~ ps=~ pf=~ "
                  "pm=~\n", (unsigned) pG->Frame_cnt, samples, rng, (unsigned) pG->System_flg, (unsigned) pG->Stop_flg,
                  st.h, rf.h, sc.h, room);
        re4dc_log("LU t=%u n=%u e=~ es=~ ef=~ em=~ o=~ os=~ of=~ om=~ c=%08x%s\n", (unsigned) pG->Frame_cnt, samples,
                  cam.h, afl);
        p[0] = p[1] = p[2] = a[0] = a[1] = a[2] = mf = ms = 0;
        ps = pf = pm = Fnv();
    } else {
#endif
#if RE4DC_TRACE_ALLOC || RE4DC_TRACE_SS_MASK
    re4dc_log("LT t=%u n=%u r=%04x sy=%08x sp=%08x st=%08x rf=%08x sc=%08x rm=%04x p=%08x,%08x,%08x "
              "a=%08x,%08x,%08x m=%08x/%x ps=%08x pf=%08x pm=%08x\n",
              (unsigned) pG->Frame_cnt, samples, rng, (unsigned) pG->System_flg, (unsigned) pG->Stop_flg, st.h,
              rf.h, sc.h, room, p[0], p[1], p[2], a[0], a[1], a[2], mf, ms, ps.h, pf.h, pm.h);
    re4dc_log("LU t=%u n=%u e=%u es=%08x ef=%08x em=%08x o=%u os=%08x of=%08x om=%08x c=%08x%s\n",
              (unsigned) pG->Frame_cnt, samples, ne, es.h, ef.h, em.h, no, os.h, of.h, om.h, cam.h, afl);
#if RE4DC_TRACE_SS_MASK
    }
#endif
#else
    re4dc_log("LT t=%u n=%u r=%04x sy=%08x sp=%08x st=%08x rf=%08x sc=%08x rm=%04x p=%08x,%08x,%08x "
              "a=%08x,%08x,%08x m=%08x/%x ps=%08x pf=%08x pm=%08x\n",
              (unsigned) pG->Frame_cnt, samples, rng, (unsigned) pG->System_flg, (unsigned) pG->Stop_flg, st.h,
              rf.h, sc.h, room, p[0], p[1], p[2], a[0], a[1], a[2], mf, ms, ps.h, pf.h, pm.h);
    re4dc_log("LU t=%u n=%u e=%u es=%08x ef=%08x em=%08x o=%u os=%08x of=%08x om=%08x c=%08x\n",
              (unsigned) pG->Frame_cnt, samples, ne, es.h, ef.h, em.h, no, os.h, of.h, om.h, cam.h);
#endif
#endif
#if defined(RE4DC_DECISION_TRACE) && RE4DC_DECISION_TRACE
    // Effect schema 2: ep contains discrete state, epf contains float bits.
    // Typed field access fixes GCC's cEsp vptr layout (m_Be_flg is at 0x10).
    Fnv ep, epf, eg;
    unsigned nep = 0, neg = 0;
#if RE4DC_LOGIC_TRACE_OWNERSHIP
    if ((own & RE4DC_OWN_EP) && g_pEspSys && g_pEspSys->pEspBuf) {
#else
    if (g_pEspSys && g_pEspSys->pEspBuf) {
#endif
        for (u32 i = 0; i < g_pEspSys->nEsp; i++) {
            const cEsp* e = reinterpret_cast<const cEsp*>(g_pEspSys->pEspBuf + i * 0x150);
            if (re4dc_trace_effect(ep, epf, i, *e)) ++nep;
        }
    }
#if RE4DC_LOGIC_TRACE_OWNERSHIP
    for (u32 i = 0; (own & RE4DC_OWN_EG) && EspgenArray && i < nEspgen; i++) {
#else
    for (u32 i = 0; EspgenArray && i < nEspgen; i++) {
#endif
        const unsigned char* b = (const unsigned char*) &EspgenArray[i];
        if (!(b[0x0C] & 1)) {
            continue;
        }
        eg.word(i);
        eg.words(b + 0x00, 8);
        eg.words(b + 0x0C, 8);
        neg++;
    }
#if RE4DC_LOGIC_TRACE_OWNERSHIP
    char epl[40], egl[24];
    if (own & RE4DC_OWN_EP) snprintf(epl, sizeof(epl), "ep=%08x/%u epf=%08x", ep.h, nep, epf.h);
    else strcpy(epl, "ep=- epf=-");
    if (own & RE4DC_OWN_EG) snprintf(egl, sizeof(egl), "eg=%08x/%u", eg.h, neg);
    else strcpy(egl, "eg=-");
    re4dc_log("LX t=%u n=%u ec=%08x/%u sl=%08x/%u sa=%08x/%u dm=%08x/%u lq=%08x/%u lp=%08x sq=%08x/%u %s %s ev=2\n",
              (unsigned) pG->Frame_cnt, samples, g_dt[0].h, g_dtn[0], g_dt[1].h, g_dtn[1], g_dt[2].h, g_dtn[2],
              g_dt[3].h, g_dtn[3], g_dt[4].h, g_dtn[4], g_dt[5].h, g_dt[6].h, g_dtn[6], epl, egl);
#else
    re4dc_log("LX t=%u n=%u ec=%08x/%u sl=%08x/%u sa=%08x/%u dm=%08x/%u lq=%08x/%u lp=%08x sq=%08x/%u "
              "ep=%08x/%u eg=%08x/%u epf=%08x ev=2\n",
              (unsigned) pG->Frame_cnt, samples, g_dt[0].h, g_dtn[0], g_dt[1].h, g_dtn[1], g_dt[2].h, g_dtn[2],
              g_dt[3].h, g_dtn[3], g_dt[4].h, g_dtn[4], g_dt[5].h, g_dt[6].h, g_dtn[6], ep.h, nep, eg.h, neg, epf.h);
#endif
    for (int k = 0; k < 8; ++k) {
        g_dt[k] = Fnv();
        g_dtn[k] = 0;
    }
#if RE4DC_LOGIC_TRACE_OWNERSHIP
    if ((samples & 3) == 0 && !(own & RE4DC_OWN_EM)) re4dc_log("LP t=%u k=- unowned\n", (unsigned) pG->Frame_cnt);
    else
#endif
#if RE4DC_TRACE_SS_MASK
    if ((samples & 3) == 0 && !ssm) {
#else
    if ((samples & 3) == 0) {
#endif
        unsigned k = 0;
        for (cUnit* u = (cUnit*) EmMgr.pAlive; u && k < 40; u = trace_value(&u->pNext)) {
            const cEm* e = (const cEm*) u;
            unsigned q[3][4];
            unsigned m = 0;
            for (; u && m < 3; ++m) {
                const cEm* f = (const cEm*) u;
                q[m][0] = trace_value(&f->id);
                q[m][1] = bits(trace_value(&f->pos.x));
                q[m][2] = bits(trace_value(&f->pos.y));
                q[m][3] = bits(trace_value(&f->pos.z));
                if (m < 2) u = trace_value(&u->pNext);
            }
            (void) e;
            re4dc_log("LP t=%u k=%u %02x:%08x,%08x,%08x %02x:%08x,%08x,%08x %02x:%08x,%08x,%08x\n",
                      (unsigned) pG->Frame_cnt, k, q[0][0], q[0][1], q[0][2], q[0][3], m > 1 ? q[1][0] : 0xFFU,
                      m > 1 ? q[1][1] : 0U, m > 1 ? q[1][2] : 0U, m > 1 ? q[1][3] : 0U, m > 2 ? q[2][0] : 0xFFU,
                      m > 2 ? q[2][1] : 0U, m > 2 ? q[2][2] : 0U, m > 2 ? q[2][3] : 0U);
            k += m;
            if (!u) break;
        }
    }
#endif

#if RE4DC_LOGIC_TRACE_OWNERSHIP
    // A digest belongs to one room and one release generation. Its anchor is the first tick whose player list
    // was published for this room and holds a placed player: never the previous room's player, whose
    // position is still readable after the door changed the room number.
    if (room != g_digRoom || g_ownGen != g_digGen) {
        g_digRoom = room; g_digGen = g_ownGen; g_digTicks = 0; g_digStarted = false; g_dig = Fnv();
    }
    if (!g_digStarted && (own & RE4DC_OWN_PL) && g_ownPubRoom == room && (p[0] | p[1] | p[2])) g_digStarted = true;
#else
    if (room != g_digRoom) {
        g_digRoom = room; g_digTicks = 0; g_digStarted = false; g_dig = Fnv();
    }
    if (!g_digStarted && (p[0] | p[1] | p[2])) g_digStarted = true;
#endif
    if (g_digStarted) {
        const unsigned v[] = {rng, (unsigned) pG->System_flg, (unsigned) pG->Stop_flg, st.h, rf.h, sc.h, room,
                              p[0], p[1], p[2], a[0], a[1], a[2], mf, ms, ps.h, pf.h, pm.h, ne, es.h, ef.h, em.h,
                              no, os.h, of.h, om.h, cam.h
#if RE4DC_LOGIC_TRACE_OWNERSHIP
                              , own | (g_ownGen << 8)
#endif
                              };
        for (unsigned w : v) g_dig.word(w);
        if (++g_digTicks % kDigestEvery == 0) {
            g_latchRoom = room; g_latchTicks = g_digTicks; g_latchDigest = g_dig.h;
#if RE4DC_LOGIC_TRACE_OWNERSHIP
            re4dc_log("LD t=%u rm=%04x k=%u d=%08x g=%u\n", (unsigned) pG->Frame_cnt, room, g_digTicks, g_dig.h,
                      g_ownGen);
#else
            re4dc_log("LD t=%u rm=%04x k=%u d=%08x\n", (unsigned) pG->Frame_cnt, room, g_digTicks, g_dig.h);
#endif
        }
    }
}

#if defined(RE4DC_PACE_CHECK) && RE4DC_PACE_CHECK
// PACE_CHECK=2 (pace.cpp): one FNV over every field of an LT/LU record, without logging. Used
// around the ModelTrans of a dropped image to prove it leaves the logic state untouched.
extern "C" unsigned re4dc_logic_trace_hash(void)
{
    if (!pG) return 0;
    Fnv all, st, rf, sc, cam, ps, pf, pm, es, ef, em, os, of, om;
#if RE4DC_LOGIC_TRACE_MASK_RENDER
    {
        // Render-only bits (set / cleared by draw stages a dropped image skips; read only by draw
        // code): [1] 0x08000000 texture-render effects queued (EspTrans, CopyTexRenderMgr),
        // [1] 0x4000 shadow texture made (make_shadow_texture, ShadowTrans), [2] 0x00100000 shadow
        // lights exist (ShadowTrans), [3] 0x10000000 letterbox scissor (inside Render).
        u32 sf[sizeof(pG->Status_flg) / 4];
        memcpy(sf, pG->Status_flg, sizeof(sf));
        sf[1] &= ~0x08004000u;
        sf[2] &= ~0x00100000u;
        sf[3] &= ~0x10000000u;
        st.words(sf, sizeof(sf));
    }
#else
    st.words(pG->Status_flg, sizeof(pG->Status_flg));
#endif
    rf.words(pG->Room_flg, sizeof(pG->Room_flg));
    sc.words(pG->Scenario_flg, sizeof(pG->Scenario_flg));
    sc.add(pG->Item_find_flg);
    cam.words(&pG->Cam.param, 32);
    if (pPL) {
        model_state(ps, pf, pm, pPL);
        all.words(&pPL->pos, sizeof(pPL->pos)); all.words(&pPL->ang, sizeof(pPL->ang));
        all.add(pPL->Motion.Mot_frame); all.add(pPL->Motion.Mot_state);
    }
    unsigned ne = 0, no = 0;
    for (cUnit* u = (cUnit*) EmMgr.pAlive; u && ne < 1024; u = trace_value(&u->pNext), ++ne) {
        cEm* e = (cEm*) u;
        model_state(es, ef, em, e);
        es.add(e->hp);
    }
    for (cUnit* u = (cUnit*) ObjMgr.pAlive; u && no < 1024; u = trace_value(&u->pNext), ++no)
        model_state(os, of, om, (cModel*) u);
    const unsigned v[] = {re4dc_rnd_state(), (unsigned) pG->System_flg, (unsigned) pG->Stop_flg, st.h, rf.h, sc.h,
                          (unsigned(pG->stage_no) << 8) | pG->room_no, ps.h, pf.h, pm.h, ne, es.h, ef.h, em.h, no,
                          os.h, of.h, om.h, cam.h};
    for (unsigned w : v) all.word(w);
    return all.h;
}
#endif
