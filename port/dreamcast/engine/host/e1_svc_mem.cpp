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
void e1_svc_boot()
{
    file_t f = fs_open("/cd/SKELCHECK", O_RDONLY);
    if (f >= 0) { fs_close(f); skel_poison = 1; e1_log("E1 SVC check build: skel_poison 1\n"); }
    // PSEED (diagnostic arm): the presentation generator starts from 0x5A5A instead of 0: shows which fields depend on
    // presentation randomness alone (the behaviour's generator is untouched)
    f = fs_open("/cd/PSEED", O_RDONLY);
    if (f >= 0) { fs_close(f); e1_prnd_seed(0x5A5A); e1_log("E1 PSEED: presentation generator 5a5a\n"); }
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
