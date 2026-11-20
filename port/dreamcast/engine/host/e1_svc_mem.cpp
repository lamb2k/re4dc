// The native services' host side in the E1 image (lane eng-e1c; docs/engine/SERVICES.md section 7, items 2 and 7).
//
// Memory: one fixed region of the main RAM map, [E1_SVC_LO, E1_SVC_HI) (host/e1_engine.h, the top 1 MB of the old
// behaviour arena), independent of the image and of the KOS heap (the hill scene leaves 252 KB of KOS heap free):
//   - the skeleton pool, 256 KB at E1_SVC_LO (svc_pool_base: tables come and go with the actors);
//   - the room's collision tables above it (svc_pool_carve: room lifetime, carved upward, never freed in E1).
// The motion key lease of the old port (native_motion.h) is not used: the engine loads every clip in place at room
// entry, so the key decoder reads pHermite_data as the original does (re4dc_motion_acquire answers "not leased").
// Check build: the boot option SKELCHECK sets skel_poison (records outside the mailbox hold NaN, lost writes and
// parent mismatches are counted); the release default is skel_poison = 0.
#include "e1_kos.h"
#include "e1_engine.h"
#include "e1_core.h"
#include "skel.h"
#include "col.h"

static const uint32_t kPoolBytes = 256 * 1024;
static uint8_t* carve_next;
static uint32_t carve_used, carve_fails;

extern "C" void* svc_pool_base(u32* bytes)
{
    *bytes = kPoolBytes;
    if (!carve_next) carve_next = (uint8_t*) E1_SVC_LO + kPoolBytes;
    return (void*) E1_SVC_LO;
}

extern "C" void* svc_pool_carve(u32 bytes)
{
    if (!carve_next) carve_next = (uint8_t*) E1_SVC_LO + kPoolBytes;
    bytes = (bytes + 31u) & ~31u;
    if ((uint32_t) carve_next + bytes > E1_SVC_HI) {
        carve_fails++;
        e1_log("E1 SVCMEM carve refused %lu bytes (used %lu)\n", (unsigned long) bytes, (unsigned long) carve_used);
        return 0;
    }
    void* p = carve_next;
    carve_next += bytes;
    carve_used += bytes;
    return p;
}

extern "C" int re4dc_motion_acquire(const void*, unsigned**) { return 0; }
extern "C" void re4dc_motion_release(int) {}

void e1_prnd_seed(unsigned short s);
// ---- the cloth's shape statistics (lane eng-e1d; boot option CLOTHSTAT, diagnostic, outside the timed rows) ----
// The motion check of SERVICES.md section 12 on the console image: per chain, the mean over its links and the run of
// the horizontal distance of each link bone from the model's bone 0 (radius), and per link its mean offset from bone 0
// (x, y, z), from the skeleton tables after the tick. s/clothcmp.py compares them with re4ref's original cloth (odump
// build, wind on) on the same fixture: radius within 0.4 unit, link means within 2 units (the round-2 bounds).
static int cloth_stat = -1;
#ifndef E2_BOSS
#include "model.h"
#include "../services/cloth/cloth.h"   // the native cloth service (an original cloth.h is on the include path)
struct ClothStat { const cModel* m; u32 n, ticks; float r; float sum[64][3]; };
static ClothStat cstat[8];
void e1_cloth_stat_tick()
{
    if (cloth_stat <= 0) return;
    for (u32 i = 0; i < cloth_chain_count() && i < 8; i++) {
        const ClothChain* ch = cloth_chain_at(i);
        if (!ch || !ch->t) continue;
        ClothStat& s = cstat[i];
        s.m = ch->m;
        s.n = ch->n < 64 ? ch->n : 64;
        const SkelTable* t = ch->t;
        const float x0 = t->world[0].m[0][3], y0 = t->world[0].m[1][3], z0 = t->world[0].m[2][3];
        float r = 0;
        for (u32 k = 0; k < s.n; k++) {
            const SkelBone& b = t->world[ch->link[k].bone];
            const float dx = b.m[0][3] - x0, dy = b.m[1][3] - y0, dz = b.m[2][3] - z0;
            r += __builtin_sqrtf(dx * dx + dz * dz);
            s.sum[k][0] += dx; s.sum[k][1] += dy; s.sum[k][2] += dz;
        }
        s.r += s.n ? r / s.n : 0;
        s.ticks++;
    }
}
static void cloth_stat_report()
{
    if (cloth_stat <= 0) return;
    for (u32 i = 0; i < 8; i++) {
        const ClothStat& s = cstat[i];
        if (!s.ticks) continue;
        printf("E1 CLOTHSTAT chain %lu model %d links %lu ticks %lu radius %d/1000\n", (unsigned long) i,
               s.m ? (int) s.m->id : -1, (unsigned long) s.n, (unsigned long) s.ticks, (int) (1000 * s.r / s.ticks));
        for (u32 k = 0; k < s.n; k++)
            printf("E1 CLOTHLINK %lu %lu %d %d %d\n", (unsigned long) i, (unsigned long) k, (int) (1000 * s.sum[k][0] / s.ticks),
                   (int) (1000 * s.sum[k][1] / s.ticks), (int) (1000 * s.sum[k][2] / s.ticks));
    }
}
#else
void e1_cloth_stat_tick() {}
static void cloth_stat_report() {}
#endif
void e1_svc_boot()
{
    file_t f = fs_open("/cd/SKELCHECK", O_RDONLY);
    if (f >= 0) { fs_close(f); skel_poison = 1; e1_log("E1 SVC check build: skel_poison 1\n"); }
    // PSEED (diagnostic arm): the presentation generator starts from 0x5A5A instead of 0: shows which fields depend on
    // presentation randomness alone (the behaviour's generator is untouched)
    f = fs_open("/cd/PSEED", O_RDONLY);
    if (f >= 0) { fs_close(f); e1_prnd_seed(0x5A5A); e1_log("E1 PSEED: presentation generator 5a5a\n"); }
    f = fs_open("/cd/CLOTHSTAT", O_RDONLY);
    cloth_stat = f >= 0;
    if (f >= 0) { fs_close(f); e1_log("E1 CLOTHSTAT: the cloth chains' shape statistics\n"); }
#ifndef E2_BOSS
    // CLOTHCTL: the cloth statistics' control (must fail s/clothcmp.py): the native cloth with gravity off
    f = fs_open("/cd/CLOTHCTL", O_RDONLY);
    if (f >= 0) { fs_close(f); cloth_control_nogravity = 1; e1_log("E1 CLOTHCTL: cloth gravity off (control)\n"); }
#endif
}

void e1_svc_room_ready()
{
    col_bake_all();
    u32 tri = 0;
    for (u32 i = 0; i < col_piece_count(); i++) tri += col_piece_at(i)->nPoly;
    e1_log("E1 SVCMEM collision pieces %lu polygons %lu tables %lu B (fails %lu)\n", (unsigned long) col_piece_count(),
           (unsigned long) tri, (unsigned long) carve_used, (unsigned long) carve_fails);
}

void e1_svc_report()
{
    cloth_stat_report();
    u32 bytes = 0;
    for (u32 i = 0; i < skel_table_count(); i++) {
        const SkelTable* t = skel_table_at(i);
        bytes += t->bytes;
        e1_log("E1 SKEL table %lu model %p bones %u bytes %lu mailbox %lu\n", (unsigned long) i, (void*) t->model, (unsigned) t->n,
               (unsigned long) t->bytes, (unsigned long) t->nMbox);
    }
    e1_log("E1 SVCMEM region %08lx-%08lx pool %lu (tables %lu B in %lu) carve %lu fails %lu\n", (unsigned long) E1_SVC_LO,
           (unsigned long) E1_SVC_HI, (unsigned long) kPoolBytes, (unsigned long) bytes, (unsigned long) skel_table_count(),
           (unsigned long) carve_used, (unsigned long) carve_fails);
    const SkelCounters& c = skel_cnt;
    e1_log("E1 SKEL poison %d entries %lu serve %lu pull %lu ancestors %lu poisoned %lu lost_writes %lu parent_mismatch %lu "
           "palette %lu samples %lu world %lu slow %lu ik %lu\n", skel_poison, (unsigned long) c.entries, (unsigned long) c.serve_bones,
           (unsigned long) c.pull_bones, (unsigned long) c.serve_ancestors, (unsigned long) c.poison_bones, (unsigned long) c.lost_writes,
           (unsigned long) c.parent_mismatch, (unsigned long) c.palette, (unsigned long) c.samples, (unsigned long) c.mat_world,
           (unsigned long) c.mat_world_slow, (unsigned long) c.ik_chains);
    e1_log("E1 COL bakes %lu late %lu line %lu sphere %lu nodes %lu tris_line %lu tris_sphere %lu\n", (unsigned long) col_cnt.bakes,
           (unsigned long) col_cnt.late_bakes, (unsigned long) col_cnt.line_queries, (unsigned long) col_cnt.sphere_queries,
           (unsigned long) col_cnt.nodes_tested, (unsigned long) col_cnt.tris_line, (unsigned long) col_cnt.tris_sphere);
}
