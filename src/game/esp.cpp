#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
#include "fallback_audit29.h"
#endif
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
extern "C" void re4dc_cloth_material_retire11();
#define RE4DC_CLOTH_POOL_RETIRE11() re4dc_cloth_material_retire11();
#define RE4DC_CLOTH_SLOT_RETIRE11(e) if((e)->m_Be_flg&1)re4dc_cloth_material_retire11();
#else
#define RE4DC_CLOTH_POOL_RETIRE11()
#define RE4DC_CLOTH_SLOT_RETIRE11(e)
#endif
#line 1
// game/esp.cpp: the effect sprite (cEsp) pool. A cEsp is one live effect particle/sprite; the pool
// (g_pEspSys->pEspBuf, nEsp slots of 0x150 bytes) is allocated per room from the cons value and
// handed out by cEsp::operator new / PullEsp, returned by PushEsp. EspMove (game loop, after
// EspgenMove) runs every active effect's move(); EspTrans (trans.cpp) sorts them into the ordering
// tables by Tool_flg / Parts_no / Core_flg. Per-id create and trans functions live in
// EspCreateTbl / EspTransTbl, filled by the esp??.cpp units through EspFuncTblSet.

#include "atari.h"
#include "light.h"
#include "global.h"
#include "main_mem.h"
#include "eprintf.h"
#include "math_sub.h"
#include "esp.h"
#include "espgen.h"

#if defined(RE4DC_ESP_HIT_THIN) && RE4DC_ESP_HIT_THIN
// ESP_HIT_THIN=N (shotfx20.mk; render only, visible): of the hit-burst particles an enemy, animal or object spawns
// (0x1A blood jitter, 0x00 spray, 0x10 drops; owner 0x10..0xCF), only those in every Nth pool slot are drawn. The rest
// are "ghosts": they live, animate and make their Rnd() draws as before (logic STRICT), but are not queued for drawing
// and skip their camera jitter (esp1a.cpp). A fixed slot test, so the same particles stay drawn (no flicker).
int re4dc_esp_hit_ghost(const cEsp* esp)
{
    const u32 id = esp->m_Id, own = esp->info.owner;
    if (own < 0x10 || own > 0xCF || (id != 0x1A && id != 0x00 && id != 0x10)) {
        return 0;
    }
    const u32 slot = (u32) ((const u8*) esp - (const u8*) g_pEspSys->pEspBuf) / 0x150;
    return (slot % RE4DC_ESP_HIT_THIN) != 0;
}
#endif
// number of live effects per owner id (debug display)
u16 esp_num_list[0xD3];
EspTransFunc EspTransTbl[0xFF];
#if RE4DC_PACE_TRANS_SKIP
// Logic-only queueing (PACE_TRANS_SKIP bit 2048, trans.cpp: an image that draws no source visuals).
// Most trans functions only draw. These also carry effect state and still queue: 0x09 (trail width
// m_Size_mul and the after-render hidden test), 0x0E and 0x45 (after-render visibility tests that
// drive alpha, and 0x0E's child spawns, which draw the shared RNG through est.cpp), 0x47 (m_Pos
// screen wrap).
extern "C" {
int re4dc_esp_logic_only;    // trans.cpp sets it around EspTrans / EspgenTrans
int re4dc_esp_logic_maybe;   // such an effect may be live: set on pull, cleared by a scan finding none
int re4dc_esp_logic_queued;  // the last logic-only EspTrans queued at least one trans
}
static inline int espLogicId(u32 id)
{
    return id == 0x09 || id == 0x0E || id == 0x45 || id == 0x47;
}
#if defined(RE4DC_COARSE_FX_SPRITES) && RE4DC_COARSE_FX_SPRITES
// COARSE_FX_SPRITES (effects30.mk): trans.cpp sets it around a drawn coarse image's logic-only EspTrans,
// which then also queues the effects the native sprite path draws (esp_sub.cpp).
extern "C" int re4dc_esp_sprite_pass;
int re4dc_esp_sprite_pass;
extern "C" int re4dc_esp_sprite_class(cEsp* esp);
#if defined(RE4DC_FX_STRIP21) && RE4DC_FX_STRIP21
extern "C" int re4dc_esp_strip21_eligible(cEsp* esp);
#endif

extern "C" int re4dc_esp_coarse_sprite_visible(cEsp* esp);
#if defined(RE4DC_ESP_SPRITE_FAST) && RE4DC_ESP_SPRITE_FAST
extern "C" void re4dc_esp_sprite_pass_begin();   // esp_sub.cpp
#endif
#endif
#endif
EspCreateFunc EspCreateTbl[0xFF];

extern "C" {
void EspDummyTrans(cEsp* esp);
void EspFuncTblInit();
int ESP_IsActive(cEsp* esp);
int EspMove();
f32 EspGetCameraPan();
f32 EspGetCameraPan2();
int EspTrans();
int EspDispInfo();
int EspArrayAlloc(u32 n);
int EspArrayFree();
int EspArrayPush(u32 n);
int EspArrayPop();
}

#if defined(RE4DC_ESP_OWNER) && RE4DC_ESP_OWNER
extern "C" {
unsigned short re4dc_esp_own[64];
unsigned long re4dc_esp_own_valid;
}
#if defined(RE4DC_FX_SCAN) && RE4DC_FX_SCAN
// GAME_FX_SCAN (esp.h): the live / owner-bucket slot maps.
extern "C" {
unsigned long re4dc_fx_esp_live[RE4DC_FX_ESP_WORDS];
unsigned long re4dc_fx_esp_ownmap[64][RE4DC_FX_ESP_WORDS];
unsigned long re4dc_fx_esp_ok;
unsigned long re4dc_fx_esp_gen;
unsigned long re4dc_fx_chk[16];
}
static u8* fxEspBuf;   // the pool the maps were built for
static u32 fxEspN;
// Slot `esp`'s bit in its owner bucket's row (Core_pEm 0 is in no row).
static inline void fxEspOwnBit(cEspSystem* sys, cEsp* esp, int on)
{
    u32 idx = (u32) ((u8*) esp - sys->pEspBuf) / 0x150;
    u32 pEm = esp->info.Core_pEm;

    if (idx < sys->nEsp && idx < 32 * RE4DC_FX_ESP_WORDS && pEm != 0) {
        unsigned long* w = &re4dc_fx_esp_ownmap[re4dcEspOwnB(pEm)][idx >> 5];
        if (on) {
            *w |= 1u << (idx & 31);
        } else {
            *w &= ~(1u << (idx & 31));
        }
    }
}
// Slot `esp`'s live bit and owner bit.
static inline void fxEspMark(cEspSystem* sys, cEsp* esp, int on)
{
    u32 idx = (u32) ((u8*) esp - sys->pEspBuf) / 0x150;

    if (idx < sys->nEsp && idx < 32 * RE4DC_FX_ESP_WORDS) {
        if (on) {
            re4dc_fx_esp_live[idx >> 5] |= 1u << (idx & 31);
        } else {
            re4dc_fx_esp_live[idx >> 5] &= ~(1u << (idx & 31));
        }
        fxEspOwnBit(sys, esp, on);
    }
}
#if defined(RE4DC_BENCH_CENSUS) && RE4DC_BENCH_CENSUS
// Benchmark census disc (dbgwarp_bridge.cpp, lane cache20): live effects in the pool now.
extern "C" unsigned re4dc_bench_esp_live()
{
    cEspSystem* sys = g_pEspSys;
    unsigned n = 0;
    for (u32 i = 0; sys && sys->pEspBuf != NULL && i < sys->nEsp; i++)
        if (((cEsp*) (sys->pEspBuf + i * 0x150))->m_Be_flg & 1) ++n;
    return n;
}
#endif
// Rebuilds the owner counts and the maps from the pool.
extern "C" void re4dc_fx_esp_sync()
{
    cEspSystem* sys = g_pEspSys;
    u32 i;

    for (i = 0; i < 64; i++) {
        re4dc_esp_own[i] = 0;
    }
    memclr_asm(re4dc_fx_esp_live, sizeof(re4dc_fx_esp_live));
    memclr_asm(re4dc_fx_esp_ownmap, sizeof(re4dc_fx_esp_ownmap));
    fxEspBuf = sys->pEspBuf;
    fxEspN = sys->nEsp;
    re4dc_fx_esp_gen++;
    re4dc_fx_esp_ok = sys->pEspBuf != NULL && sys->nEsp <= 32 * RE4DC_FX_ESP_WORDS;
    for (i = 0; sys->pEspBuf != NULL && i < sys->nEsp; i++) {
        cEsp* esp = (cEsp*) (sys->pEspBuf + i * 0x150);
        if (esp->m_Be_flg & 1) {
            re4dc_esp_own[re4dcEspOwnB(esp->info.Core_pEm)]++;
            if (re4dc_fx_esp_ok) {
                fxEspMark(sys, esp, 1);
            }
        }
    }
    re4dc_esp_own_valid = 1;
}
// 1 when the maps describe the current pool (rebuilt first when stale).
extern "C" int re4dc_fx_esp_ready()
{
    cEspSystem* sys = g_pEspSys;

    if (!re4dc_esp_own_valid || sys->pEspBuf != fxEspBuf || sys->nEsp != fxEspN) {
        re4dc_fx_esp_sync();
    }
    return re4dc_fx_esp_ok;
}
#endif
// Copies an owner block into a slot, moving a live slot between owner buckets.
extern "C" void re4dc_esp_info_set(cEsp* esp, const EspInfo* info)
{
    int live = re4dc_esp_own_valid && (esp->m_Be_flg & 1);
    if (live) {
        re4dc_esp_own[re4dcEspOwnB(esp->info.Core_pEm)]--;
#if defined(RE4DC_FX_SCAN) && RE4DC_FX_SCAN
        if (re4dc_fx_esp_ok) {
            fxEspOwnBit(g_pEspSys, esp, 0);
        }
#endif
    }
    esp->info = *info;
    if (live) {
        re4dc_esp_own[re4dcEspOwnB(esp->info.Core_pEm)]++;
#if defined(RE4DC_FX_SCAN) && RE4DC_FX_SCAN
        if (re4dc_fx_esp_ok) {
            fxEspOwnBit(g_pEspSys, esp, 1);
        }
#endif
    }
}
#if defined(RE4DC_FX_SCAN) && RE4DC_FX_SCAN
#define ESP_OWN_STALE() (re4dc_esp_own_valid = 0, re4dc_fx_esp_gen++)
#else
#define ESP_OWN_STALE() (re4dc_esp_own_valid = 0)
#endif
#else
#define ESP_OWN_STALE() ((void) 0)
#endif

// Default EspTransTbl entry: an effect whose id has no registered trans function is reported and
// released.
void EspDummyTrans(cEsp* esp)
{
    pLog->err(0, 0, "ESP_TRANS : ESP_ID[%x] invalid.", esp->m_Id);
    PushEsp(esp);
}

// Resets both per-id tables (0xFF ids) to "unregistered"; called once from the effect system init
// (eff_sys.cpp) before the esp units register themselves.
void EspFuncTblInit()
{
    int i;

    for (i = 0; i < 0xFF; i++) {
        EspTransTbl[i] = EspDummyTrans;
        EspCreateTbl[i] = NULL;
    }
}

// Registers the factory and draw function for effect id `id` (each esp??.cpp calls this at init).
void EspFuncTblSet(int id, EspCreateFunc create, EspTransFunc trans)
{
    EspCreateTbl[id] = create;
    EspTransTbl[id] = trans;
}

// 1 when `esp` is in use and should move/draw this frame. Under Status_flg[1] 0x10000000
// (event pause) only effects with Core_flg bit0 count, and an effect attached to a model only
// when that model carries be_flag 0x800 (moves during events, see emMove).
int ESP_IsActive(cEsp* esp)
{
    if (!(esp->m_Be_flg & 1)) {
        return 0;
    }
    if (pG->Status_flg[1] & 0x10000000) {
        if (!(esp->info.Core_flg & 1)) {
            return 0;
        }
        if (esp->parent != pEffParentWorld) {
            cModel* m = esp->m_pMod;
            if (m != NULL) {
                int off = !(m->be_flag & 0x800);
                if (off) {
                    return 0;
                }
            }
        }
    }
    return 1;
}

#if defined(RE4DC_ESP_POOL_DIAG) && RE4DC_ESP_POOL_DIAG
// ESP_POOL_DIAG (esppool.mk, test only): per room pool size, live-sprite peak, steals (a full pool recycling a
// Tool_flg 0x40000 sprite) and refusals (the dummy esp handed back).
extern "C" void re4dc_log(const char* fmt, ...);
static u32 espd_room = 0xFFFFFFFFu, espd_n, espd_peak, espd_logged, espd_steal, espd_refuse;
static void espd_report(const char* why)
{
    re4dc_log("esp pool: %s room %03x slots %u peak %u steals %u refused %u\n", why, (unsigned) espd_room,
              (unsigned) espd_n, (unsigned) espd_peak, (unsigned) espd_steal, (unsigned) espd_refuse);
}
#define ESPD_STEAL() (++espd_steal)
#else
#define ESPD_STEAL() ((void) 0)
#endif
// Allocates an effect of id `id`: runs its registered create (operator new picks a free slot),
// marks it live (m_Be_flg bit0), stores the id and bumps ActiveEspNum. Returns 1 on success;
// on a bad id or a full pool *out is the dummy esp (pDmyEsp) and 0 is returned.
int PullEsp(cEsp** out, int id)
{
    cEspSystem* sys = g_pEspSys;
    EspCreateFunc create = EspCreateTbl[id];
    cEsp* esp;
    int ret = 0;

    if (create == NULL) {
        pLog->err(0, 0, "ESP : EspID[%x] is invalid.", id);
        *out = sys->pDmyEsp;
        return 0;
    }
    esp = create();
    *out = esp;
    if (esp != sys->pDmyEsp) {
        esp->m_Be_flg |= 1;
#if defined(RE4DC_ESP_OWNER) && RE4DC_ESP_OWNER
        if (re4dc_esp_own_valid) {
            re4dc_esp_own[re4dcEspOwnB(esp->info.Core_pEm)]++;
#if defined(RE4DC_FX_SCAN) && RE4DC_FX_SCAN
            if (re4dc_fx_esp_ok) {
                fxEspMark(sys, esp, 1);
            }
#endif
        }
#endif
        ret = 1;
        sys->ActiveEspNum++;
#if defined(RE4DC_ESP_POOL_DIAG) && RE4DC_ESP_POOL_DIAG
        if ((u32) sys->ActiveEspNum > espd_peak) {
            espd_peak = sys->ActiveEspNum;
            if (espd_peak >= espd_logged + 32) { espd_logged = espd_peak; espd_report("peak"); }
        }
#endif
        (*out)->m_Id = id;
#if RE4DC_PACE_TRANS_SKIP
        if (espLogicId(id)) {
            re4dc_esp_logic_maybe = 1;
        }
#endif
    } else {
#if defined(RE4DC_ESP_POOL_DIAG) && RE4DC_ESP_POOL_DIAG
        if (espd_refuse++ < 4 || !(espd_refuse & 63)) espd_report("REFUSED");
#endif
        pLog->warn(6, 0, "ESP : ESP work full!!");
    }
    return ret;
}

// Pool slot search: scans the pool from the last hit (wrapping) for a free slot; if none, steals the
// first live slot flagged Tool_flg 0x40000 (low-priority, may be recycled) after releasing it.
// The found slot is zeroed. Returns pDmyEsp when nothing is available.
// The target's third loop has `mr r9,r10` (a copy of the sys+0x10000 base) before the loop and in
// its latch, with the pEspBuf load reading r9. That is cse_around_loop (cse.c): it only runs on a
// loop with LOOP_BEG/END notes whose latch jumps straight back to the header, and it rewrites the
// header's `sys+0x10000` into the latch's REG_LOOP_TEST_P copy. So loop3 is a real `for` loop;
// loop.c (find_and_verify_loops) would then move the `PushEsp; goto found` block behind the found:
// block (a guarded block ending in a jump out of the loop) and, with no call left in the loop,
// hoist the pEspBuf load. The `do { PushEsp(esp); goto found; } while (0)` wrapper stops that: the
// backward scan from the `goto` stops at the inner NOTE_INSN_LOOP_BEG instead of the guard jump.
// Loops 1/2/4 as for/while loops get strength-reduced `&esp->flag` givs the target lacks, so they
// stay goto loops.
void* cEsp::operator new(unsigned int size)
{
    static u32 old_hit = 0;
    cEspSystem* sys = g_pEspSys;
    u32 i;
    cEsp* esp;
    cEsp* ret;
    u32 start;
    u32 ofs;

    if (old_hit >= sys->nEsp) {
        BitSet(old_hit, 0);
    }
    i = old_hit;
    start = i;
    ret = sys->pDmyEsp;
    if (i < sys->nEsp) {
        ofs = i * 0x150;
loop1:
        esp = (cEsp*) (sys->pEspBuf + ofs);
        if (!(esp->m_Be_flg & 1)) {
            goto found;
        }
        i++;
        ofs += 0x150;
        if (i < sys->nEsp) {
            goto loop1;
        }
    }
    i = 0;
    if (i < start) {
        ofs = 0;
loop2:
        esp = (cEsp*) (sys->pEspBuf + ofs);
        if (!(esp->m_Be_flg & 1)) {
            goto found;
        }
        i++;
        ofs += 0x150;
        if (i < start) {
            goto loop2;
        }
    }
    if (ret == sys->pDmyEsp) {
        for (i = start; i < sys->nEsp; i++) {
            esp = (cEsp*) (sys->pEspBuf + i * 0x150);
            if ((esp->m_Be_flg & 1) && (esp->m_Tool_flg & 0x40000)) {
                do { // keeps loop.c from moving this block out of the loop (see above)
                    ESPD_STEAL();
                    PushEsp(esp);
                    goto found;
                } while (0);
            }
        }
        i = 0;
        if (i < start) {
            ofs = 0;
loop4:
            esp = (cEsp*) (sys->pEspBuf + ofs);
            if ((esp->m_Be_flg & 1) && (esp->m_Tool_flg & 0x40000)) {
#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_ESP_POOL_RECYCLE) && RE4DC_ESP_POOL_RECYCLE
                // Match the forward steal: retire the old owner/resources before
                // clearing its slot. Free-slot searches jump directly to found.
                ESPD_STEAL();
                PushEsp(esp);
#endif
found:
#if defined(RE4DC_ESP_POOL_DIAG) && RE4DC_ESP_POOL_DIAG
                if (esp->m_Be_flg & 1) ESPD_STEAL();
#endif
                RE4DC_CLOTH_SLOT_RETIRE11(esp) memclr_asm(esp, 0x150);
                old_hit = i + 1;
                return esp;
            }
            i++;
            ofs += 0x150;
            if (i < start) {
                goto loop4;
            }
        }
    }
    return ret;
}

u32 tubo_amb = 0;
#if defined(RE4DC_ESP_CENSUS) && RE4DC_ESP_CENSUS
#include <stdio.h>
#endif

#if defined(RE4DC_ESP_LOD) && RE4DC_ESP_LOD > 1
// ESP_LOD=N (logiclod.mk; lane logiclod20 2026-10-20; an APPROXIMATION, default 0 = off; 2..4): a world-parented effect
// (parent pEffParentWorld) that is off screen (more than 3 m from the camera and behind it or more than 60 degrees off
// its axis) or beyond ESP_LOD_FAR units from the camera (default 40 m) moves only every Nth tick, staggered by slot.
// Effects attached to a model keep every tick. A skipped effect keeps its slot, position and matrix, and its life runs
// 1/N as fast while skipped. Effect moves that draw Rnd() draw fewer, so this is gameplay-equivalent, not STRICT.
static inline int re4dc_esp_lod_skip(const cEsp* esp, u32 i)
{
    if (esp->parent != pEffParentWorld) {
        return 0;
    }
    if ((((u32) pG->Frame_cnt + i) % RE4DC_ESP_LOD) == 0) {
        return 0;
    }
    const Camera* cam = &pG->Cam;
    const f32 vx = esp->m_Pos.x - cam->param.pos.x;
    const f32 vy = esp->m_Pos.y - cam->param.pos.y;
    const f32 vz = esp->m_Pos.z - cam->param.pos.z;
    const f32 d2 = vx * vx + vy * vy + vz * vz;
    if (d2 > (f32) RE4DC_ESP_LOD_FAR * (f32) RE4DC_ESP_LOD_FAR) {
        return 1;
    }
    if (d2 <= 9000000.0f) {
        return 0;
    }
    const f32 f = -(vx * cam->Look.x + vy * cam->Look.y + vz * cam->Look.z);   // Look = pos - at: forward is -Look
    return !(f > 0.0f && f * f >= 0.25f * d2);
}
#define ESP_LOD_SKIP(esp, i) re4dc_esp_lod_skip((esp), (i))
#else
#define ESP_LOD_SKIP(esp, i) 0
#endif

// Releases a live effect: clears m_Be_flg bits 0-1, decrements ActiveEspNum and runs Destruct().
// Pushing a slot that is not live only warns.
void PushEsp(cEsp* esp)
{
    if (esp->m_Be_flg & 1) {
#if defined(RE4DC_ESP_OWNER) && RE4DC_ESP_OWNER
        if (re4dc_esp_own_valid) {
            re4dc_esp_own[re4dcEspOwnB(esp->info.Core_pEm)]--;
#if defined(RE4DC_FX_SCAN) && RE4DC_FX_SCAN
            if (re4dc_fx_esp_ok) {
                fxEspMark(g_pEspSys, esp, 0);
            }
#endif
        }
#endif
        esp->m_Be_flg &= ~3;
        g_pEspSys->ActiveEspNum--;
        esp->Destruct();
    } else {
        pLog->warn(0, 0, "PushEsp() : No alive work is pushed.");
    }
}

#if defined(RE4DC_FX_SCAN) && RE4DC_FX_SCAN
// ESP_IsActive, inline.
static inline int fxEspActive(cEsp* esp)
{
    if (!(esp->m_Be_flg & 1)) {
        return 0;
    }
    if (pG->Status_flg[1] & 0x10000000) {
        if (!(esp->info.Core_flg & 1)) {
            return 0;
        }
        if (esp->parent != pEffParentWorld) {
            cModel* m = esp->m_pMod;
            if (m != NULL) {
                int off = !(m->be_flag & 0x800);
                if (off) {
                    return 0;
                }
            }
        }
    }
    return 1;
}
// One slot of EspMove's loop, as the source body.
static inline void fxEspMoveOne(cEspSystem* sys, u32 i, int pause, u32* cnt)
{
    cEsp* esp = (cEsp*) (sys->pEspBuf + i * 0x150);

    if (!fxEspActive(esp)) {
        return;
    }
    if (esp->parent != pEffParentWorld) {
        cModel* m = esp->m_pMod;
        if (m != NULL) {
            if ((m->be_flag & 0x201) != 1 || m->serial != esp->m_Guid_pMod) {
                PushEsp(esp);
                return;
            }
        }
    }
    if (pause) {
        if (!(esp->info.Core_flg & 0x8000)) {
            return;
        }
    }
    if (!ESP_LOD_SKIP(esp, i)) {
        esp->move();
    }
    if (esp->m_Be_flg & 1) {
        (*cnt)++;
        if (pG->debug_mode == 0xE) {
            esp_num_list[esp->info.owner]++;
        }
    }
}
#if RE4DC_FX_SCAN == 2
// Check build: the slots a fast loop skips are tested the way the source loop tests them, and
// every one that the source would act on counts as a mismatch (counters: esp.h FXC_*).
extern "C" void re4dc_log(const char* fmt, ...);
// Every map bit against the pool.
static void fxChkMaps(cEspSystem* sys)
{
    u32 i;
    u32 own = 0;
    u32 set = 0;

    for (i = 0; i < 32 * RE4DC_FX_ESP_WORDS; i++) {
        int bit = (re4dc_fx_esp_live[i >> 5] >> (i & 31)) & 1;
        int live = i < sys->nEsp && (((cEsp*) (sys->pEspBuf + i * 0x150))->m_Be_flg & 1);
        if (bit != live) {
            re4dc_fx_chk[FXC_MAP_ERR]++;
        }
        if (live) {
            cEsp* esp = (cEsp*) (sys->pEspBuf + i * 0x150);
            if (esp->info.Core_pEm != 0) {
                own++;
                if (!((re4dc_fx_esp_ownmap[re4dcEspOwnB(esp->info.Core_pEm)][i >> 5] >> (i & 31)) & 1)) {
                    re4dc_fx_chk[FXC_MAP_ERR]++;
                }
            }
        }
    }
    for (i = 0; i < 64 * RE4DC_FX_ESP_WORDS; i++) {
        unsigned long w = re4dc_fx_esp_ownmap[i / RE4DC_FX_ESP_WORDS][i % RE4DC_FX_ESP_WORDS];
        while (w != 0) {
            set++;
            w &= w - 1;
        }
    }
    if (set != own) {
        re4dc_fx_chk[FXC_MAP_ERR]++;
    }
}
// EspMove skipped [from, to): none may be active.
static void fxChkMoveSkip(cEspSystem* sys, u32 from, u32 to)
{
    for (; from < to && from < sys->nEsp; from++) {
        if (fxEspActive((cEsp*) (sys->pEspBuf + from * 0x150))) {
            re4dc_fx_chk[FXC_MIS_ESP]++;
        }
    }
}
static void fxChkLog()
{
    if (re4dc_fx_chk[FXC_ESP_MOVE] % 128 == 1) {
        re4dc_log("FXS move=%u visit=%u espdel=%u egpass=%u egdel=%u efm=%u efmbuild=%u mis_esp=%u mis_eg=%u "
                  "mis_efm=%u maperr=%u fallback=%u\n",
                  re4dc_fx_chk[FXC_ESP_MOVE], re4dc_fx_chk[FXC_VISIT], re4dc_fx_chk[FXC_ESP_DEL],
                  re4dc_fx_chk[FXC_EG_MOVE], re4dc_fx_chk[FXC_EG_DEL], re4dc_fx_chk[FXC_EFM],
                  re4dc_fx_chk[FXC_EFM_BUILD], re4dc_fx_chk[FXC_MIS_ESP], re4dc_fx_chk[FXC_MIS_EG],
                  re4dc_fx_chk[FXC_MIS_EFM], re4dc_fx_chk[FXC_MAP_ERR], re4dc_fx_chk[FXC_FALLBACK]);
    }
}
#endif
#endif

// Per-frame update of all effects (game loop, after EspgenMove). Drops effects whose attached model
// died or was re-used (be_flag / serial mismatch); during the pause (Status_flg[1] bit1) only
// Core_flg 0x8000 effects move. Prints the live count (debug page 0xE also lists per-owner counts).
int EspMove()
{
    cEspSystem* sys = g_pEspSys;
    cEsp* esp;
    u32 cnt;
    u32 i;
    int pause;
    int color;
    int y;

    for (i = 0; i < 0xD3; i++) {
        esp_num_list[i] = 0;
    }
    pause = 0;
    if (pG->Status_flg[1] & 2) {
        pause = 1;
    }
    cnt = 0;
#if defined(RE4DC_FX_SCAN) && RE4DC_FX_SCAN
    // The source loop; a slot whose live bit is clear fails ESP_IsActive, so while the map is current
    // a run of them is stepped over without reading the slots.
    {
        const int use = re4dc_fx_esp_ready();
        const unsigned long gen = re4dc_fx_esp_gen;
#if RE4DC_FX_SCAN == 2
        if (use) {
            fxChkMaps(sys);
        }
        re4dc_fx_chk[FXC_ESP_MOVE]++;
#endif
        for (i = 0; i < sys->nEsp; i++) {
            if (use && re4dc_fx_esp_gen == gen) {
                unsigned long m = re4dc_fx_esp_live[i >> 5] >> (i & 31);
                if (m == 0) {
#if RE4DC_FX_SCAN == 2
                    fxChkMoveSkip(sys, i, (i | 31) + 1);
#endif
                    i |= 31;
                    continue;
                }
                m = re4dcFxCtz(m);
#if RE4DC_FX_SCAN == 2
                fxChkMoveSkip(sys, i, i + m);
                re4dc_fx_chk[FXC_VISIT]++;
#endif
                i += m;
            }
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
            if(!use || re4dc_fx_esp_gen!=gen)re4dc::fa29::hit(re4dc::fa29::EspScan);
#endif
#line 649
            fxEspMoveOne(sys, i, pause, &cnt);
        }
#if RE4DC_FX_SCAN == 2
        if (!use || re4dc_fx_esp_gen != gen) {
            re4dc_fx_chk[FXC_FALLBACK]++;
        }
        fxChkLog();
#endif
    }
#else
    for (i = 0; i < sys->nEsp; i++) {
        esp = (cEsp*) (sys->pEspBuf + i * 0x150);
        if (!ESP_IsActive(esp)) {
            continue;
        }
        if (esp->parent != pEffParentWorld) {
            cModel* m = esp->m_pMod;
            if (m != NULL) {
                if ((m->be_flag & 0x201) != 1 || m->serial != esp->m_Guid_pMod) {
                    PushEsp(esp);
                    continue;
                }
            }
        }
        if (pause) {
            if (!(esp->info.Core_flg & 0x8000)) {
                continue;
            }
        }
        if (!ESP_LOD_SKIP(esp, i)) {
            esp->move();
        }
        if (esp->m_Be_flg & 1) {
            cnt++;
            if (pG->debug_mode == 0xE) {
                esp_num_list[esp->info.owner]++;
            }
        }
    }
#endif
#if defined(RE4DC_ESP_CENSUS) && RE4DC_ESP_CENSUS
    // ESP_CENSUS=1 (logiclod20.mk; test only): every 120 frames, the live effects by id and by owner
    // ("espc:" lines: id:count / owner:count, the ten largest of each).
    if ((pG->Frame_cnt % 120) == 0) {
        static u16 byId[256];
        static u16 byOwn[256];
        for (i = 0; i < 256; i++) {
            byId[i] = 0;
            byOwn[i] = 0;
        }
        u32 live = 0;
        for (i = 0; i < sys->nEsp; i++) {
            esp = (cEsp*) (sys->pEspBuf + i * 0x150);
            if (esp->m_Be_flg & 1) {
                byId[esp->m_Id & 0xFF]++;
                byOwn[esp->info.owner & 0xFF]++;
                live++;
            }
        }
        for (int pass = 0; pass < 2; pass++) {
            u16* h = pass ? byOwn : byId;
            char buf[200];
            int n = 0;
            for (int k = 0; k < 10; k++) {
                int best = -1;
                for (int j = 0; j < 256; j++) {
                    if (h[j] && (best < 0 || h[j] > h[best])) {
                        best = j;
                    }
                }
                if (best < 0) {
                    break;
                }
                n += snprintf(buf + n, sizeof(buf) - n, " %02x:%u", best, (unsigned) h[best]);
                h[best] = 0;
            }
            re4dc_log("espc: f=%u room=%03x live=%u %s%s\n", (unsigned) pG->Frame_cnt, (unsigned) G_ROOM_ID,
                      (unsigned) live, pass ? "own" : "id", buf);
        }
    }
#endif
    color = 0;
    if ((f32) cnt > (f32) sys->nEsp * 0.7f) {
        color = 0x16;
    }
    if ((f32) cnt > (f32) sys->nEsp * 0.9f) {
        color = 2;
    }
    if (pG->Debug_flg[3] & 0x8000) {
        eprintf(0x1B0, 0xC8, color, 0, "%d/%d", sys->ActiveEspNum, cnt);
    } else {
        eprintf(0x1D8, 0xC8, color, 0xE, "%d", cnt);
    }
    if ((s32) pG->Debug_flg[0] >= 0 && pG->debug_mode == 0xE) {
        eprintf(0x20, 0x60, 0, 0xE, "TOTAL:%d", cnt);
        // y counts printed rows; `0x70 + y * 0x10` is a strength-reduced giv whose `li 0x70` init
        // is emitted by loop.c after the hoisted `lis`/`addi`s (a plain `y = 0x70; y += 0x10`
        // schedules the li before the call).
        y = 0;
        for (i = 0; i < 0xD3; i++) {
            if (esp_num_list[i] != 0) {
                eprintf(0x20, 0x70 + y * 0x10, 0, 0xE, "%s:%d", owner_name_tbl[i], esp_num_list[i]);
                y++;
            }
        }
    }
    return 1;
}

// Camera yaw in degrees as computed by the last EspTrans (used by the sprite transforms).
f32 EspGetCameraPan()
{
    return g_pEspSys->CameraPan;
}

// Camera pitch in degrees as computed by the last EspTrans.
f32 EspGetCameraPan2()
{
    return g_pEspSys->CameraPan2;
}

// Draw registration (trans.cpp, once per frame): computes the camera pan/pitch, then queues every
// active effect's trans function into the ordering tables: screen sprites (Parts_no 0xF8..0xFD) go
// to fixed OT slots, Tool_flg 0x10000 selects a texture-render target by Core_flg, 0x1000/0x400/
// 0x800/0x400000 pick the pre/post-world layers, everything else is Z-sorted by world position
// (with m_Radius when set). Tool_flg 0x100 hides an effect in the first-person (scope /
// binocular) view (Status_flg[0] 0x8000), 0x200 hides it outside that view.
int EspTrans()
{
    cEspSystem* sys = g_pEspSys;
    Vec dir;
    Vec wpos;
    Vec* wp;
    cEsp* esp;
    EspTransFunc trans;
    Camera* cam;
    u32 i;
    u16 prio;
    int ot;
    f32 zlimit;

    if (sys == NULL) {
        return 0;
    }
#if RE4DC_PACE_TRANS_SKIP
    const int logicOnly = re4dc_esp_logic_only;
    u32 logicLive = 0;
#if defined(RE4DC_COARSE_FX_SPRITES) && RE4DC_COARSE_FX_SPRITES
    const int spritePass = logicOnly && re4dc_esp_sprite_pass;
    int spriteEntry = 0;
#else
    const int spritePass = 0;
#endif
    if (logicOnly) {
        re4dc_esp_logic_queued = 0;
        if (!re4dc_esp_logic_maybe && !spritePass) {
            return 1;
        }
    }
#if defined(RE4DC_COARSE_FX_SPRITES) && RE4DC_COARSE_FX_SPRITES && defined(RE4DC_ESP_SPRITE_FAST) && RE4DC_ESP_SPRITE_FAST
    if (spritePass) {
        re4dc_esp_sprite_pass_begin();
    }
#endif
#endif
#if defined(RE4DC_ESP_TYPE_CAP) && RE4DC_ESP_TYPE_CAP
    static u8 espCapN[256];
    for (i = 0; i < 256; i++) {
        espCapN[i] = 0;
    }
#endif
    LightMgr.setEsp(&sys->lightList, 8);
    cam = &pG->Cam;
    dir.x = cam->param.at.x - cam->param.pos.x;
    dir.y = cam->param.at.y - cam->param.pos.y;
    dir.z = cam->param.at.z - cam->param.pos.z;
    if (dir.x == 0.0f && dir.y == 0.0f && dir.z == 0.0f) {
        dir.y = 1.0f;
    }
#line 584 "D:/Bio4/Prog/esp.cpp"
    VECNormalize(&dir, &dir);
    if (dir.x == 0.0f && dir.z == 0.0f) {
        sys->CameraPan = 0.0f;
    } else {
        sys->CameraPan = atan2f(dir.x, dir.z) * 57.295776f;
    }
    if (dir.y == 0.0f) {
        sys->CameraPan2 = 0.0f;
    } else {
        sys->CameraPan2 = -atan2f(dir.y, SQRTF(dir.x * dir.x + dir.z * dir.z)) * 57.295776f;
    }
    for (i = 0; i < sys->nEsp; i++) {
        esp = (cEsp*) (sys->pEspBuf + i * 0x150);
#if RE4DC_PACE_TRANS_SKIP
#if defined(RE4DC_COARSE_FX_SPRITES) && RE4DC_COARSE_FX_SPRITES
        spriteEntry = 0;
        if (logicOnly) {
            if (!(esp->m_Be_flg & 1)) {
                continue;
            }
            if (espLogicId(esp->m_Id)) {
                logicLive++;
            } else if (spritePass && re4dc_esp_sprite_class(esp)) {
                spriteEntry = 1;   // drawn, not state: does not hold a skipped iteration's Render()
            } else {
                continue;
            }
        }
#else
        if (logicOnly) {
            if (!(esp->m_Be_flg & 1) || !espLogicId(esp->m_Id)) {
                continue;
            }
            logicLive++;
        }
#endif
#endif
        if (!ESP_IsActive(esp)) {
            continue;
        }
        if (esp->m_pMod != NULL && !(esp->m_pMod->be_flag & 2) && esp->m_Release_time == 0xFF) {
            continue;
        }
        trans = EspTransTbl[esp->m_Id];
        if (trans == NULL) {
            continue;
        }
#if defined(RE4DC_ESP_HIT_THIN) && RE4DC_ESP_HIT_THIN
        if (trans == EspCommonTrans && re4dc_esp_hit_ghost(esp)) {
            continue;   // ESP_HIT_THIN: a ghost hit particle is not drawn
        }
#endif
#if defined(RE4DC_ESP_TYPE_CAP) && RE4DC_ESP_TYPE_CAP
        // ESP_TYPE_CAP=N (logiclod20.mk; render only, a visible APPROXIMATION): at most N effects of one id spawned by
        // an enemy, animal or object (owner 0x10..0xCF: blood sprays, hit sparks, death bursts) are queued for drawing
        // per pass, in pool order. Only effects drawn by the plain EspCommonTrans (a render-only body: no Rnd(), no
        // game state) are capped; room effects (0x01, 0xD0) and Leon's (0x03) never. Capped effects move and live as before.
        if (trans == EspCommonTrans && esp->info.owner >= 0x10 && esp->info.owner < 0xD0) {
            u8* n = &espCapN[esp->m_Id & 0xFF];
            if (*n >= RE4DC_ESP_TYPE_CAP) {
                continue;
            }
            ++*n;
        }
#endif
        if (esp->info.Core_flg & 0x400) {
            if (pG->Status_flg[1] & 0x04000000) {
                continue;
            }
        }
        if (pG->Status_flg[0] & 0x8000) {
            if (esp->m_Tool_flg & 0x100) {
                continue;
            }
        } else {
            if (esp->m_Tool_flg & 0x200) {
                continue;
            }
        }
#if RE4DC_PACE_TRANS_SKIP
#if defined(RE4DC_COARSE_FX_SPRITES) && RE4DC_COARSE_FX_SPRITES
        if (logicOnly && !spriteEntry) {
#else
        if (logicOnly) {
#endif
            re4dc_esp_logic_queued = 1;
        }
#endif
        prio = 0x10;
        if (trans == EspCommonTrans && esp->pad_EC[0] == 0 && !(esp->m_Tool_flg & 0x6000)) {
            prio = 8;
        }
#if defined(RE4DC_COARSE_FX_SPRITES) && RE4DC_COARSE_FX_SPRITES
        if (spriteEntry) {
            if (
#if defined(RE4DC_FX_STRIP21) && RE4DC_FX_STRIP21
                !re4dc_esp_strip21_eligible(esp) &&
#endif
                !re4dc_esp_coarse_sprite_visible(esp)) {
                continue;   // wholly outside the view bound (esp_sub.cpp): not queued
            }
            // Esp0b_Trans is EspCommonTrans after a camera jitter (Core_flg 0x8000) that draws the shared
            // Rnd(): a coarse image queues the common body only (same OT priority), so no game state moves.
#if defined(RE4DC_RAIN_PS2_SHEET_REF) && RE4DC_RAIN_PS2_SHEET_REF
            if (esp->m_Id != 0x08)   // RAIN_PS2_SHEET_REF: the rain sheet keeps Esp08_Trans (reference arm only)
#endif
#if defined(RE4DC_NATIVE_LASER) && RE4DC_NATIVE_LASER
            if (esp->m_Id != 0x19)
#endif
#if defined(RE4DC_FX_STRIP21) && RE4DC_FX_STRIP21
            if(!re4dc_esp_strip21_eligible(esp))
#endif
            trans = EspCommonTrans;
        }
#endif
        if (pG->Status_flg[1] & 2) {
            if (!(esp->info.Core_flg & 0x8000)) {
                continue;
            }
            AddOtDirect(0x14, esp, (void (*)()) trans, 0, prio, NULL, 0.0f);
            continue;
        }
        if (esp->m_Tool_flg & 0x10000) {
            BitOn(pG->Status_flg[1], 0x08000000);
            ot = 0;
            if (!(esp->info.Core_flg & 8)) {
                if (esp->info.Core_flg & 0x10) {
                    ot = 1;
                } else if (esp->info.Core_flg & 0x20) {
                    ot = 2;
                } else if (esp->info.Core_flg & 0x40) {
                    ot = 3;
                } else if (esp->info.Core_flg & 0x80) {
                    ot = 4;
                } else if (esp->info.Core_flg & 0x100) {
                    ot = 5;
                } else if (esp->info.Core_flg & 0x200) {
                    ot = 6;
                } else if ((s32) pG->Debug_flg[0] >= 0) {
                    pLog->err(6, 0, "ESP : FLG_TEX_RENDER but no set tex_no");
                }
            }
            if ((u8) (esp->m_Parts_no + 8) <= 5) {
                switch (esp->m_Parts_no) {
                case 0xFD:
                    AddOtDirect(ot, esp, (void (*)()) trans, 3, prio, NULL, 0.0f);
                    break;
                case 0xFC:
                    AddOtDirect(ot, esp, (void (*)()) trans, 2, prio, NULL, 0.0f);
                    break;
                case 0xFB:
                    AddOtDirect(ot, esp, (void (*)()) trans, 1, prio, NULL, 0.0f);
                    break;
                case 0xFA:
                    AddOtDirect(ot, esp, (void (*)()) trans, 5, prio, NULL, 0.0f);
                    break;
                case 0xF9:
                    AddOtDirect(ot, esp, (void (*)()) trans, 4, prio, NULL, 0.0f);
                    break;
                case 0xF8:
                    AddOtDirect(ot, esp, (void (*)()) trans, 6, prio, NULL, 0.0f);
                    break;
                default:
                    pLog->err(0, 0, "ESP : FLG_TEX_RENDER but no screen");
                    break;
                }
            } else {
                pLog->err(0, 0, "ESP : FLG_TEX_RENDER but no screen");
            }
            continue;
        }
        if (esp->m_Tool_flg & 0x1000) {
            if ((u8) (esp->m_Parts_no + 8) <= 5) {
                AddOtDirect(0x12, esp, (void (*)()) trans, 8, prio, NULL, 0.0f);
            } else {
                AddOtDirect(0x12, esp, (void (*)()) trans, 9, prio, NULL, 0.0f);
            }
            continue;
        }
        if (esp->m_Flg & 8) {
            AddOtDirect(0x12, esp, (void (*)()) trans, 6, prio, NULL, 0.0f);
            continue;
        }
        if (esp->m_Tool_flg & 0x400000) {
            if ((esp->m_Tool_flg & 0xC00) == 0xC00) {
                AddOtDirect(0xB, esp, (void (*)()) trans, 3, prio, NULL, 0.0f);
            } else {
                AddOtDirect(0x10, esp, (void (*)()) trans, 4, prio, NULL, 0.0f);
            }
            continue;
        }
        if (esp->m_Tool_flg & 0x400) {
            if (esp->m_Tool_flg & 0x800) {
                AddOtDirect(0x10, esp, (void (*)()) trans, 3, prio, NULL, 0.0f);
            } else {
                AddOtDirect(0x10, esp, (void (*)()) trans, 2, prio, NULL, 0.0f);
            }
            continue;
        }
        if (esp->m_Tool_flg & 0x800) {
            AddOtDirect(0x10, esp, (void (*)()) trans, 0, prio, NULL, 0.0f);
            continue;
        }
        if ((u8) (esp->m_Parts_no + 8) <= 5) {
            switch (esp->m_Parts_no) {
            case 0xFD:
                AddOtDirect(0x12, esp, (void (*)()) trans, 3, prio, NULL, 0.0f);
                break;
            case 0xFC:
                AddOtDirect(0x12, esp, (void (*)()) trans, 2, prio, NULL, 0.0f);
                break;
            case 0xFB:
                AddOtDirect(0x12, esp, (void (*)()) trans, 1, prio, NULL, 0.0f);
                break;
            case 0xFA:
                AddOtDirect(0x12, esp, (void (*)()) trans, 5, prio, NULL, 0.0f);
                break;
            case 0xF9:
                AddOtDirect(0x12, esp, (void (*)()) trans, 4, prio, NULL, 0.0f);
                break;
            case 0xF8:
                AddOtDirect(0x12, esp, (void (*)()) trans, 6, prio, NULL, 0.0f);
                break;
            }
            continue;
        }
        if (esp->parent != pEffParentWorld) {
            PSMTXMultVec(esp->parent->mat, &esp->m_Pos, &wpos);
        } else {
            wp = &wpos;
            *wp = esp->m_Pos;
        }
        wp = &wpos;
        zlimit = 0.0f;
        if (esp->m_Radius == zlimit) {
            AddOtWorldPos(esp, (void (*)(void*)) trans, wp, prio, 200.0f);
        } else {
            if ((esp->m_Flg & 2) == 0 && (esp->m_Tool_flg & 1) == 0) {
                zlimit = 200.0f;
            }
            AddOtWorldPosRadius(esp, (void (*)(void*)) trans, wp, esp->m_Radius, prio, zlimit);
        }
    }
#if RE4DC_PACE_TRANS_SKIP
    if (logicOnly && logicLive == 0) {
        re4dc_esp_logic_maybe = 0;
    }
#endif
    return 1;
}

// Debug page 12 "EP" row: current / peak / total esp slot usage.
int EspDispInfo()
{
    static u32 max = 0;
    cEspSystem* sys = g_pEspSys;
    u8* p = sys->pEspBuf;
    u32 cnt;
    u32 i;

    if (p == NULL) {
        return 0;
    }
    cnt = 0;
    for (i = 0; i < sys->nEsp; i++) {
        if (((cEsp*) (p + i * 0x150))->m_Be_flg & 1) {
            cnt++;
        }
    }
    eprintf(0x1A0, 0x38, 0, 0xC, "%3d/%3d/%4d", cnt, max, sys->nEsp);
    if (cnt > max) {
        max = cnt;
    }
    return 1;
}

u32 esp_dmy_amb = 0;

// Allocates the esp pool with `n` slots (game.cpp room start, count from the cons table); frees
// the previous pool first. Returns 1 on success.
int EspArrayAlloc(u32 n)
{
    cEspSystem* sys = g_pEspSys;
    u32 size;
    u8* p;

    EspArrayFree();
    ESP_OWN_STALE();
#if defined(RE4DC_ESP_POOL_DIAG) && RE4DC_ESP_POOL_DIAG
    if (espd_room != 0xFFFFFFFFu) espd_report("room end");
    espd_room = pG ? (u32) pG->room_id : 0; espd_n = n; espd_peak = espd_logged = espd_steal = espd_refuse = 0;
#endif
#if defined(RE4DC_ESP_POOL_CAP) && RE4DC_ESP_POOL_CAP
    // ESP_POOL_CAP (esppool.mk): the room asks for at most this many slots (heap 4; the GC cons values are 1024).
    if (n > RE4DC_ESP_POOL_CAP) {
        n = RE4DC_ESP_POOL_CAP;
    }
#endif
#if defined(RE4DC_ESP_POOL_ROOM_MIN) && RE4DC_ESP_POOL_ROOM_MIN
    // ESP_POOL_ROOM_MIN (mendezfx.mk; #55): the listed rooms get at least this many slots (r11f: the Mendez fight
    // fills the GC's 1,024 when the boss takes rapid hits; the barn's heap has the room).
    {
        static const u16 rooms[] = {RE4DC_ESP_POOL_ROOM_LIST};
        for (u32 k = 0; k < sizeof(rooms) / sizeof(rooms[0]); k++) {
            if (pG && rooms[k] == (u16) pG->room_id && n < RE4DC_ESP_POOL_ROOM_MIN) {
                n = RE4DC_ESP_POOL_ROOM_MIN;
            }
        }
    }
#endif
#if defined(RE4DC_ESP_POOL_DIAG) && RE4DC_ESP_POOL_DIAG
    espd_n = n;
#endif
    if (n == 0) {
        return 0;
    }
    size = n * 0x150;
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_SS_POOL_HIGH
    void* re4dc_ss_alloc_above(u32 size, const char* file, int line);  // sscrn_bridge.cpp
    p = (u8*) re4dc_ss_alloc_above(size, "esp.cpp", 879);
#else
#line 879 "D:/Bio4/Prog/esp.cpp"
    p = (u8*) MEM_ALLOC(size, 1, 0xD);
#endif
#line 880 "D:/Bio4/Prog/esp.cpp"
    sys->pEspBuf = p;
    if (p == NULL) {
        return 0;
    }
    sys->nEsp = n;
    memclr_asm(p, size);
    return 1;
}

// Frees the esp pool. Returns 0 when there was none.
int EspArrayFree()
{
    cEspSystem* sys = g_pEspSys;

    if (sys->pEspBuf == NULL) {
        return 0;
    }
    RE4DC_CLOTH_POOL_RETIRE11() Mem_free(sys->pEspBuf);
    sys->pEspBuf = NULL;
    ESP_OWN_STALE();
    return 1;
}

// Debug tools: swaps in a Debug_alloc'd pool of `n` slots, saving the game pool. 0 if one is
// already pushed.
int EspArrayPush(u32 n)
{
    cEspSystem* sys = g_pEspSys;

    if (sys->pEspBufSave != NULL) {
        return 0;
    }
    ESP_OWN_STALE();
    RE4DC_CLOTH_POOL_RETIRE11() sys->pEspBufSave = sys->pEspBuf;
    sys->pEspBuf = (u8*) Debug_alloc(n * 0x150, 1);
    sys->nEspBack = sys->nEsp;
    sys->nEsp = n;
    return 1;
}

// Debug tools: restores the pool saved by EspArrayPush. 0 if none was pushed.
int EspArrayPop()
{
    cEspSystem* sys = g_pEspSys;

    if (sys->pEspBufSave == NULL) {
        return 0;
    }
    ESP_OWN_STALE();
    RE4DC_CLOTH_POOL_RETIRE11() Debug_free(sys->pEspBuf);
    sys->pEspBuf = sys->pEspBufSave;
    sys->pEspBufSave = NULL;
    sys->nEsp = sys->nEspBack;
    return 1;
}

// Releases every live effect in the pool (room change, est.cpp).
void EspArrayClear()
{
    cEspSystem* sys = g_pEspSys;
    cEsp* esp;
    u32 i;

    for (i = 0; i < sys->nEsp; i++) {
        esp = (cEsp*) (sys->pEspBuf + i * 0x150);
        if (esp->m_Be_flg & 1) {
            PushEsp(esp);
        }
    }
}

// The dummy esp that PullEsp hands out when it fails; callers compare against it.
cEsp* EspGetDmyPtr()
{
    return g_pEspSys->pDmyEsp;
}

// Queues `func(esp)` in the after-render OT (0x16) so an effect can read the depth buffer (the
// HideCheck occlusion tests of esp09/esp0e/esp45). Skipped while the generator loop pre-runs.
void EspAddOtAfterRender(cEsp* esp, void (*func)(cEsp*))
{
    if (EspGenGetMoveLoop() == 0) {
        AddOtDirect(0x16, esp, (void (*)()) func, 0, 0x20, NULL, 0.0f);
    }
}
