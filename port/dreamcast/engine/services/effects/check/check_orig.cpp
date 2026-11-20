// Effect equivalence check (lane eng-e2), the ORIGINAL side's runtime: what the original effect functions (copied
// verbatim into orig_fx.cpp by orig_extract.py: EspSeqSet, cEsp::CommonMove / ColorUpdate / AnmMove / ApplyMatrix,
// the pool's PullEsp / operator new / PushEsp, espgen10_Update / EspgenDataSet, cEsp00::move, fRandSeed1_1) need
// around them: the effect system work (g_pEspSys) with its sprite pool, the sequence-player pool, the texture and est
// registries (data lookups of the same EffData blocks), and no-op logging. Every sprite id is created as the plain
// sprite cEsp00 (CommonMove + AnmMove), the model the native service simulates for every id; the per-id extras are the
// native service's stated approximation and are not part of this check.
#include "global.h"
#include "model.h"
#include "esp.h"
#include "espgen.h"
#include "db_log.h"
#include "obj.h"
#include "main_mem.h"
#include "check.h"
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

cEspSystem* g_pEspSys;
EspCreateFunc EspCreateTbl[0xFF];
EspTransFunc EspTransTbl[0xFF];
cCoord* pEffParentWorld;
cModel* EspEvModList[0x80];
static unsigned char log_obj[256];
cLogPtr pLog = {(cLog*) log_obj};
void cLog::err(int, int, const char* fmt, ...) { orig_log_count++; (void) fmt; }
void cLog::warn(int, int, const char*, ...) {}
unsigned orig_log_count;
void memclr_asm(void* dst, u32 n) { memset(dst, 0, n); }
GlobalWork* pG;
static unsigned char pg_storage[0x20000] __attribute__((aligned(32)));

// ---- the sprite pool (0x150 bytes a cEsp, as the original's) ----
cEsp* Esp00_Create();
static unsigned char pool[ORIG_POOL * 0x150] __attribute__((aligned(32)));
static unsigned char dummy[0x150] __attribute__((aligned(32)));
static cCoord world;
static cEsp* orig_create();
void orig_init()
{
    pG = (GlobalWork*) pg_storage;
    g_pEspSys = (cEspSystem*) calloc(1, sizeof(cEspSystem));
    g_pEspSys->pEspBuf = pool;
    g_pEspSys->nEsp = ORIG_POOL;
    g_pEspSys->pDmyEsp = (cEsp*) dummy;
    for (unsigned i = 0; i < 0xFF; i++) EspCreateTbl[i] = orig_create;
    for (unsigned i = 0; i < 0x100; i++) g_pEspSys->Esp_tex_tbl[i].Owner = 0xD2;
    pEffParentWorld = &world;
}
// spawn order of each live pool slot (the check matches sprites by it): the create function is the original's
// (Esp00_Create, esp00.cpp), wrapped to note the slot it returned
unsigned orig_uid[ORIG_POOL];
static unsigned next_uid;
static cEsp* orig_create()
{
    cEsp* e = Esp00_Create();
    const unsigned slot = ((unsigned char*) e - pool) / 0x150;
    if ((unsigned char*) e >= pool && slot < ORIG_POOL) orig_uid[slot] = next_uid++;
    return e;
}
cEsp* orig_slot(unsigned i) { return (cEsp*) (pool + i * 0x150); }

// ---- registries: est tables and texture animations of the registered EffData (eff_sys.cpp estRegist /
// espTexRegist / EspGetEstAddr / EspGetAnmAddr / EspChkTexId: the lookups, without the texture objects) ----
struct EffData { u32 version, ofsTexId, ofsEstList, ofsSstList, ofsPathList, ofsEfmId, ofsTpl, ofsAnm, ofsEstData, ofsSstData, ofsPathData, ofsEfm; };
struct EffIdTbl { u32 num; struct { u16 id, x2; u32 x4; } ent[1]; };
struct EffOfsTbl { u32 num; u32 ofs[1]; };
void orig_data_load(const void* addr, unsigned owner)
{
    const EffData* d = (const EffData*) addr;
    const EffIdTbl* ids = (const EffIdTbl*) ((const u8*) d + d->ofsTexId);
    const EffOfsTbl* anms = (const EffOfsTbl*) ((const u8*) d + d->ofsAnm);
    for (u32 i = 0; i < ids->num; i++) {
        EspTexWk& t = g_pEspSys->Esp_tex_tbl[ids->ent[i].id & 0xFF];
        t.pAnm = (EspAnmData*) ((const u8*) anms + anms->ofs[i]);
        t.Owner = owner;
    }
    SstTbl& e = g_pEspSys->estTbl[owner];
    e.data = (SstData*) ((const u8*) d + d->ofsEstData);
    e.list = (SstList*) ((const u8*) d + d->ofsEstList);
    e.owner = owner;
}
EspSeqData* orig_est_addr(u32 owner, int id)
{
    SstTbl& t = g_pEspSys->estTbl[owner];
    if (!t.list) return 0;
    for (u32 i = 0; i < t.list->num; i++)
        if (t.list->ent[i].no == (u16) id) return (EspSeqData*) ((u8*) t.data + t.data->ofs[i]);
    return 0;
}
extern "C" int EspGetAnmAddr(int no, EspAnmData** out)
{
    EspTexWk& t = g_pEspSys->Esp_tex_tbl[no & 0xFF];
    if (t.Owner == 0xD2 || !t.pAnm) return 0;
    *out = t.pAnm;
    return 1;
}
int EspChkTexId(int no) { return g_pEspSys->Esp_tex_tbl[no & 0xFF].Owner != 0xD2; }
extern "C" cEsp* EspGetDmyPtr() { return g_pEspSys->pDmyEsp; }
// Effect models, scroll-object parents, nested generators: not part of the check (counted)
unsigned orig_efm, orig_kind1;
cObj* EfmSeqSet(EspGenWork*, EfmCore*, u32*, cModel*, Mtx, int, f32, Vec*) { orig_efm++; return 0; }
cObj* SmdGetObjPtr(u32) { return 0; }
int EspgenSeqSet(EspSeqData*, int, EspInfo*, cModel*, u16, Mtx*, Vec*, Vec*, EspSeqOpt*, int) { orig_kind1++; return 1; }

// ---- the sequence players (EspgenWork, controller 10) ----
static EspgenWork gens[ORIG_GENS];
extern "C" void espgen10_Update(EspgenWork* w);
void PushEspgen(EspgenWork* w) { w->flag &= ~1; }
void orig_est_start(u32 owner, int id, int parts, const Vec* pos, const Vec* rot, u32 seed)
{
    EspSeqData* head = orig_est_addr(owner, id);
    if (!head || !head->num) return;
    for (EspgenWork& g : gens) {
        if (g.flag & 1) continue;
        memset(&g, 0, sizeof(g));
        g.flag = 1;
        g.id = 0x10;
        Espgen10Work* p = (Espgen10Work*) ((u8*) &g + 0x14);
        p->head = head;   // est.cpp EstSet, verbatim in order; the seed is the call's (the engine's generator)
        p->pMod = 0;
        p->Guid_pMod = 0;
        p->no = p->Time_cnt = 0;
        p->Null_parts_no = parts == -1 ? head->parts : parts;
        if (pos) { p->Flg |= 2; p->Offset = *pos; } else p->Offset = head->pos;
        if (rot) p->Ang = *rot;
        else { p->Ang = head->rot; PSVECScale(&p->Ang, &p->Ang, 3.14f / 180.0f); }
        p->Rand_seed = seed;
        p->p8 = 0;
        return;
    }
}
// One tick of the original effect frame for this check: every live controller's frame (EspgenMove), then every live
// sprite's move (EspMove's loop, knobs off; no model-attached sprites here).
void orig_tick()
{
    for (EspgenWork& g : gens) if (g.flag & 1) espgen10_Update(&g);
    for (unsigned i = 0; i < ORIG_POOL; i++) {
        cEsp* e = orig_slot(i);
        if (!(e->m_Be_flg & 1)) continue;
        e->move();
    }
}

// ---- the Dreamcast tree's packed effect records (port/dreamcast/game/platform/native_effect.cpp's format, read here as
// the original side's data adapter; the native service has its own reader): an archive's ESQ table lists the sequences
// whose record words are offsets (bit 0: packed, a 12-byte presence mask then the present words of the 300 bytes) ----
struct OrigArc { const u8* base; unsigned bytes; const u8* entries; unsigned count; };
static OrigArc oarcs[8];
static u32 w32(const u8* p) { u32 v; memcpy(&v, p, 4); return v; }
void orig_bind_archive(const void* base, unsigned bytes)
{
    const u8* a = (const u8*) base;
    const u32 n = w32(a);
    if (n > (bytes - 16) / 8) return;
    for (u32 i = 0; i < n; i++) {
        if (memcmp(a + 16 + 4 * n + 4 * i, "ESQ", 4)) continue;
        const u32 off = w32(a + 16 + 4 * i);
        if (off > bytes - 32 || memcmp(a + off, "R4ESQTBL", 8)) return;
        for (OrigArc& r : oarcs) if (!r.base) { r = {a, bytes, a + off + 32, w32(a + off + 12)}; return; }
    }
}
extern "C" void* re4dc_effect_record_ref(void* head, unsigned index)
{
    const u8* h = (const u8*) head;
    for (const OrigArc& r : oarcs) {
        if (!r.base || h < r.base || h >= r.base + r.bytes) continue;
        const u32 off = h - r.base;
        for (unsigned i = 0; i < r.count; i++)
            if (w32(r.entries + 12 * i) == off) {
                const u32 ref = w32(h + 48 + 4 * index);
                return (void*) ((uintptr_t) (h + (ref & ~1u)) | (ref & 1));
            }
    }
    return (void*) (h + 48 + 300 * index);
}
extern "C" void* re4dc_effect_record_read(void* reference, void* scratch)
{
    uintptr_t p = (uintptr_t) reference;
    if (!(p & 1)) return reference;
    const u8* rec = (const u8*) (p & ~(uintptr_t) 1);
    u8* out = (u8*) scratch;
    unsigned at = 12;
    for (unsigned i = 0; i < 75; i++) {
        u32 v = 0;
        if (w32(rec + 4 * (i / 32)) & (1u << (i % 32))) { v = w32(rec + at); at += 4; }
        memcpy(out + 4 * i, &v, 4);
    }
    return scratch;
}

// model parts: no model-attached sprite reaches the check (the driver starts model calls at their world position)
cModel* cModel::getPartsPtr(int) { abort(); }
extern "C" void host_free(void* p) { free(p); }
