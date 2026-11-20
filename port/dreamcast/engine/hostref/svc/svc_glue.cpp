// svc_glue.cpp (game side; lane eng-svc): what the service census needs from the game's records. The pools (parts,
// characters, objects) and, at every tick start, which actor and bone each parts slot belongs to (walk of the
// character and object alive lists and each model's pParts chain). replay.cpp's hooks (host_svc_*) call it.
#include "hostref.h"
#include "svc_census.h"
#include "model.h"
#include "em.h"
#include "obj.h"
#include "global.h"

extern "C" int sprintf(char*, const char*, ...);

namespace {
uint8_t g_owner[4096], g_bone[4096];
char g_actors[16384];
unsigned g_actors_len;
bool g_seen[128];

void note_actor(unsigned code, const cModel* m, unsigned t)
{
    if (code >= 128 || g_seen[code] || g_actors_len > sizeof g_actors - 256) return;
    g_seen[code] = true;
    g_actors_len += sprintf(g_actors + g_actors_len, "%u\t%s\t%u\t%02x\t%02x\t%u\t%u\n", code, code < 64 ? "em" : "obj",
                            code & 63, m->id, m->type, m->nParts, t);
}
void own_chain(const cModel* m, unsigned code, unsigned t)
{
    const u32 lo = (u32) PartsMgr.pArray, stride = PartsMgr.size;
    unsigned b = 0;
    for (const cModel* p = m->pParts; p && b < 255; p = p->pParts, b++) {
        const u32 a = (u32) p;
        if (a < lo || a >= lo + stride * PartsMgr.nArray) break;
        const unsigned slot = (a - lo) / stride;
        g_owner[slot] = (uint8_t) code;
        g_bone[slot] = (uint8_t) b;
    }
    note_actor(code, m, t);
}
}   // namespace

extern "C" void col_bake_all(void) __attribute__((weak));        // native builds
extern "C" void skel_publish_all(void) __attribute__((weak));

extern "C" void host_svc_ready()
{
    if (col_bake_all) col_bake_all();
    SvcRegion r[SVC_REGIONS];
    __builtin_memset(r, 0, sizeof r);
    r[SVC_R_PARTS].lo = (u32) PartsMgr.pArray;
    r[SVC_R_PARTS].hi = (u32) PartsMgr.pArray + PartsMgr.size * PartsMgr.nArray;
    r[SVC_R_PARTS].stride = PartsMgr.size;
    r[SVC_R_EM].lo = (u32) EmMgr.pArray;
    r[SVC_R_EM].hi = (u32) EmMgr.pArray + EmMgr.size * EmMgr.nArray;
    r[SVC_R_EM].stride = EmMgr.size;
    r[SVC_R_OBJ].lo = (u32) ObjMgr.pArray;
    r[SVC_R_OBJ].hi = (u32) ObjMgr.pArray + ObjMgr.size * ObjMgr.nArray;
    r[SVC_R_OBJ].stride = ObjMgr.size;
    host_log("svc census: parts %08x x%u (%u B), em %08x x%u (%u B), obj %08x x%u (%u B)", r[0].lo, PartsMgr.nArray,
             PartsMgr.size, r[1].lo, EmMgr.nArray, EmMgr.size, r[2].lo, ObjMgr.nArray, ObjMgr.size);
    svc_census_regions(r);
    g_actors_len = (unsigned) sprintf(g_actors, "# code\tpool\tslot\tid\ttype\tnparts\tfirst_tick\n");
}

extern "C" void host_svc_tick(unsigned t, int begin)
{
    if (!begin && skel_publish_all) skel_publish_all();   // the palette, once a tick (traced: native work)
    if (begin) {
        __builtin_memset(g_owner, 128, sizeof g_owner);
        __builtin_memset(g_bone, 255, sizeof g_bone);
        const u32 elo = (u32) EmMgr.pArray, olo = (u32) ObjMgr.pArray;
        for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext) own_chain(e, ((u32) e - elo) / EmMgr.size, t);
        for (cObj* o = ObjMgr.pAlive; o; o = (cObj*) o->pNext) own_chain(o, 64 + ((u32) o - olo) / ObjMgr.size, t);
        svc_census_parts((u32) PartsMgr.pArray, PartsMgr.size, PartsMgr.nArray < 4096 ? PartsMgr.nArray : 4096, g_owner, g_bone);
    }
    svc_census_tick(t, begin);
}

extern "C" void host_svc_finish() { svc_census_finish(g_actors); }
