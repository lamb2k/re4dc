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
#include "routes.h"
#include "input.h"
#include "volumes.h"
#include "follow.h"
#include "model_svc.h"
#include "camera_svc.h"
#include "col_model.h"
#include "global.h"
#include "main.h"
#include "svc_prof.h"

static const uint32_t kPoolBytes = 256 * 1024;
static uint8_t* carve_next;
static uint32_t carve_used, carve_fails;
// Lane eng-skel1 (eng-load1's request R2): the region's other end is the room's. The room carve takes from the top down
// (svc_pool_carve_room: the collision tables) and is given back when the room is left (svc_pool_room_reset), so a room's
// tables do not outlive it. The boot carve (the cloth pool, the account's buffers) grows up from the skeleton pool; each
// is refused (and counted) where it would cross the other.
static uint8_t* room_top = (uint8_t*) E1_SVC_HI;
static uint32_t room_used, room_peak;

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
    if (carve_next + bytes > room_top) {
        carve_fails++;
        e1_log("E1 SVCMEM carve refused %lu bytes (used %lu, room %lu)\n", (unsigned long) bytes, (unsigned long) carve_used,
               (unsigned long) room_used);
        return 0;
    }
    void* p = carve_next;
    carve_next += bytes;
    carve_used += bytes;
    return p;
}
extern "C" void* svc_pool_carve_room(u32 bytes)
{
    if (!carve_next) carve_next = (uint8_t*) E1_SVC_LO + kPoolBytes;
    bytes = (bytes + 31u) & ~31u;
    if ((u32) (room_top - carve_next) < bytes) {
        carve_fails++;
        e1_log("E1 SVCMEM room carve refused %lu bytes (room %lu, boot %lu)\n", (unsigned long) bytes, (unsigned long) room_used,
               (unsigned long) carve_used);
        return 0;
    }
    room_top -= bytes;
    room_used += bytes;
    if (room_used > room_peak) room_peak = room_used;
    return room_top;
}
// The room carve given back down to `keep` (NULL: all of it; a block of the room carve: it and every block carved before
// it stay). Returns the bytes given back.
extern "C" u32 svc_pool_room_reset(void* keep)
{
    uint8_t* to = keep ? (uint8_t*) keep : (uint8_t*) E1_SVC_HI;
    if (to < room_top || to > (uint8_t*) E1_SVC_HI) return 0;
    const u32 back = (u32) (to - room_top);
    room_top = to;
    room_used -= back;
    return back;
}
extern "C" u32 svc_pool_room_used(void) { return room_used; }

extern "C" int re4dc_motion_acquire(const void*, unsigned**) { return 0; }
extern "C" void re4dc_motion_release(int) {}

void e1_prnd_seed(unsigned short s);
// lane eng-e1e: the round-4 services' control switches (services/routes, services/input) and the rumble exercise
extern "C" int route_control;
extern "C" int input_control;
static int rumble_exercise;
extern "C" unsigned e1_light_miss;   // services/actor_e1.inc (renderer)
#include "camera/eng_camera.h"   // lane eng-e1j: the conversion counters (E1 PUB)
extern "C" void VibSet(u32 time, u32 level, u16 wait, u16 type);
void e1_svc_tick_begin(unsigned t)
{
    if (!rumble_exercise || t < 20 || (t - 20) % 40 != 0) return;
    pSys->flags |= 0x08000000;
    VibSet(30, 0xC0, 0, 0x8001);
    VibSet(12, 0x40, 4, 0x0002);
}
// ---- the cloth's shape statistics (lane eng-e1d; boot option CLOTHSTAT, diagnostic, outside the timed rows) ----
// The motion check of SERVICES.md section 12 on the console image: per chain, the mean over its links and the run of
// the horizontal distance of each link bone from the model's bone 0 (radius), and per link its mean offset from bone 0
// (x, y, z), from the skeleton tables after the tick. s/clothcmp.py compares them with re4ref's original cloth (odump
// build, wind on) on the same fixture: radius within 0.4 unit, link means within 2 units (the round-2 bounds).
static int cloth_stat = -1;
#ifdef E1_CLOTH_SVC   // lane eng-skel1: wherever the cloth service is linked (game/Makefile CLOTH_SVC)
#include "model.h"
#include "../services/cloth/cloth.h"   // the native cloth service (an original cloth.h is on the include path)
#include "../services/cloth/cloth_kernel.h"
struct ClothStat { const cModel* m; u32 n, ticks; float r; float sum[64][3]; };
static ClothStat cstat[8];
static void cloth_stat_tick()
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
static void cloth_count_report()
{
    const ClothCounters& c = cloth_cnt;
    const ClothKCounters& k = cloth_k_cnt;
    e1_log("E1 CLOTH chains %lu fallback %lu moves %lu links %lu volumes %lu resets %lu | kernel links %lu passes %lu normalize %lu "
           "sqrt %lu acos %lu rotations %lu volume-tests %lu volume-hits %lu volume-skips %lu\n", (unsigned long) c.chains, (unsigned long) c.fallback,
           (unsigned long) c.moves, (unsigned long) c.links, (unsigned long) c.at_volumes, (unsigned long) c.resets,
           (unsigned long) k.links, (unsigned long) k.passes, (unsigned long) k.normalize, (unsigned long) k.sqrt,
           (unsigned long) k.acos, (unsigned long) k.rotations, (unsigned long) k.vol_tests, (unsigned long) k.vol_hits, (unsigned long) k.vol_skips);
}
#else
static void cloth_stat_tick() {}
static void cloth_stat_report() {}
static void cloth_count_report() {}
#endif

// ---- the services row's phase account (lane eng-svcspd1; services/skeleton/svc_prof.h). Boot file SVCPROF: each
// tick's exclusive time per phase (us, 16 bits) kept in the service region and printed after play (serial only),
// outside the timed rows. SVCPROFCTL: the control, a 200 us busy wait a tick inside SP_PUBLISH. ----
extern "C" unsigned long long svc_prof_clock(void) { return timer_ns_gettime64(); }
static const char* const kSpName[SP_N] = {"rest", "sample", "matcalc", "world_pre", "world_post", "world_hokan", "world_entry", "ik",
                                          "hokan", "blend", "blendtbl", "mailbox", "translate", "publish", "motion_rest",
                                          "cloth_pre", "cloth_kernel", "cloth_post", "col_line", "col_floor", "col_sphere"};
static const u32 kSpTicks = 1024;
static uint16_t* sp_buf;   // [kSpTicks][SP_N]
static uint8_t* sp_cbuf;   // [kSpTicks][SP_N] entries a phase a tick (255: at least)
static u32 sp_last_calls[SP_N];
static u32 sp_ticks;
static uint64_t sp_total[SP_N];
static void svc_prof_tick()
{
    if (!svc_prof_on) return;
    if (sp_ticks < kSpTicks && sp_buf)
        for (u32 k = 0; k < SP_N; k++) {
            const u32 us = (svc_prof_ns[k] + 500) / 1000;
            sp_buf[sp_ticks * SP_N + k] = (uint16_t) (us > 65535 ? 65535 : us);
            const u32 n = svc_prof_calls[k] - sp_last_calls[k];
            if (sp_cbuf) sp_cbuf[sp_ticks * SP_N + k] = (uint8_t) (n > 255 ? 255 : n);
        }
    for (u32 k = 0; k < SP_N; k++) sp_last_calls[k] = svc_prof_calls[k];
    for (u32 k = 0; k < SP_N; k++) {
        sp_total[k] += svc_prof_ns[k];
        svc_prof_ns[k] = 0;
    }
    sp_ticks++;
}
static void svc_prof_report()
{
    if (!svc_prof_on) return;
    printf("E1 SVCPROF ticks %lu control %lu us phases", (unsigned long) sp_ticks, (unsigned long) svc_prof_ctl_us);
    for (u32 k = 0; k < SP_N; k++) printf(" %s", kSpName[k]);
    printf("\n");
    for (u32 k = 0; k < SP_N; k++)
        printf("E1 SVCPROF total %s us %lu calls %lu\n", kSpName[k], (unsigned long) (sp_total[k] / 1000), (unsigned long) svc_prof_calls[k]);
    for (u32 t = 0; t < sp_ticks && t < kSpTicks && sp_buf; t++) {
        printf("SP %lu", (unsigned long) (t + 1));
        for (u32 k = 0; k < SP_N; k++) printf(" %u", (unsigned) sp_buf[t * SP_N + k]);
        printf("\n");
        if (!sp_cbuf) continue;
        printf("SPC %lu", (unsigned long) (t + 1));
        for (u32 k = 0; k < SP_N; k++) printf(" %u", (unsigned) sp_cbuf[t * SP_N + k]);
        printf("\n");
    }
}
void e1_cloth_stat_tick()
{
    cloth_stat_tick();
    svc_prof_tick();
}
void e1_svc_boot()
{
    file_t f = fs_open("/cd/SVCPROF", O_RDONLY);
    if (f >= 0) {
        fs_close(f);
        sp_buf = (uint16_t*) svc_pool_carve(kSpTicks * SP_N * 2);
        sp_cbuf = (uint8_t*) svc_pool_carve(kSpTicks * SP_N);
        svc_prof_on = sp_buf != 0;
        e1_log("E1 SVCPROF: the services row's phase account (lab arm, %s)\n", svc_prof_on ? "on" : "no memory: off");
    }
    f = fs_open("/cd/SVCPROFCTL", O_RDONLY);
    if (f >= 0) { fs_close(f); svc_prof_ctl_us = 200; e1_log("E1 SVCPROFCTL: 200 us a tick waited inside the palette phase (control)\n"); }
    f = fs_open("/cd/SKELCHECK", O_RDONLY);
    if (f >= 0) { fs_close(f); skel_poison = 1; e1_log("E1 SVC check build: skel_poison 1\n"); }
    // PSEED (diagnostic arm): the presentation generator starts from 0x5A5A instead of 0: shows which fields depend on
    // presentation randomness alone (the behaviour's generator is untouched)
    f = fs_open("/cd/PSEED", O_RDONLY);
    if (f >= 0) { fs_close(f); e1_prnd_seed(0x5A5A); e1_log("E1 PSEED: presentation generator 5a5a\n"); }
    f = fs_open("/cd/CLOTHSTAT", O_RDONLY);
    cloth_stat = f >= 0;
    if (f >= 0) { fs_close(f); e1_log("E1 CLOTHSTAT: the cloth chains' shape statistics\n"); }
    // lane eng-e1e: the round-4 services' controls in the image (each must move the play: the image runs the native
    // service, not an original unit) and the rumble exercise:
    //   ROUTENEAR  routes: the nearest-point search returns the second reachable point (re4ref control routenear)
    //   RUMBLERND  input: the random rumble strength from the behaviour generator Rnd (the audit's fault; control)
    //   RUMBLEX    every 40 ticks from tick 20 a 30-tick random-strength rumble and a 12-tick constant one (rumble
    //              switched on), as eng-svc4's re4ref exercise: the strength draws come from the presentation generator
    f = fs_open("/cd/ROUTENEAR", O_RDONLY);
    if (f >= 0) { fs_close(f); route_control = 1; e1_log("E1 ROUTENEAR: routes control (second reachable point)\n"); }
    f = fs_open("/cd/RUMBLERND", O_RDONLY);
    if (f >= 0) { fs_close(f); input_control = 2; e1_log("E1 RUMBLERND: rumble strength from Rnd (control)\n"); }
    f = fs_open("/cd/RUMBLEX", O_RDONLY);
    if (f >= 0) { fs_close(f); rumble_exercise = 1; e1_log("E1 RUMBLEX: random-strength rumble exercise\n"); }
#ifdef E1_CLOTH_SVC   // lane eng-skel1: wherever the cloth service is linked (game/Makefile CLOTH_SVC)
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
           (unsigned long) tri, (unsigned long) room_used, (unsigned long) carve_used, (unsigned long) carve_fails);
}

void e1_svc_report()
{
    cloth_stat_report();
    cloth_count_report();
    svc_prof_report();
    u32 bytes = 0;
    for (u32 i = 0; i < skel_table_count(); i++) {
        const SkelTable* t = skel_table_at(i);
        bytes += t->bytes;
        e1_log("E1 SKEL table %lu model %p bones %u bytes %lu mailbox %lu\n", (unsigned long) i, (void*) t->model, (unsigned) t->n,
               (unsigned long) t->bytes, (unsigned long) t->nMbox);
    }
    e1_log("E1 SVCMEM region %08lx-%08lx pool %lu (tables %lu B in %lu) carve %lu fails %lu\n", (unsigned long) E1_SVC_LO,
           (unsigned long) E1_SVC_HI, (unsigned long) kPoolBytes, (unsigned long) bytes, (unsigned long) skel_table_count(),
           (unsigned long) carve_used, (unsigned long) room_used, (unsigned long) room_peak, (unsigned long) carve_fails);
    const SkelCounters& c = skel_cnt;
    e1_log("E1 SKEL poison %d entries %lu serve %lu pull %lu ancestors %lu poisoned %lu lost_writes %lu parent_mismatch %lu "
           "palette %lu samples %lu world %lu slow %lu ik %lu\n", skel_poison, (unsigned long) c.entries, (unsigned long) c.serve_bones,
           (unsigned long) c.pull_bones, (unsigned long) c.serve_ancestors, (unsigned long) c.poison_bones, (unsigned long) c.lost_writes,
           (unsigned long) c.parent_mismatch, (unsigned long) c.palette, (unsigned long) c.samples, (unsigned long) c.mat_world,
           (unsigned long) c.mat_world_slow, (unsigned long) c.ik_chains);
    // lane eng-svcspd1: the rest of the skeleton's work counters (the account's units)
    e1_log("E1 SKEL2 local %lu xmtrx_loads %lu add_rot %lu hokan_bones %lu blend_bones %lu samp_int %lu samp_frac %lu samp_end %lu "
           "mk_rows %lu mk_dec %lu mk_miss %lu mk_root_rows %lu mk_root_dec %lu mk_axes %lu hist_moves %lu trig_hits %lu trig_miss %lu pre_bones %lu mk_bound %lu mk_unbound %lu mk_rebinds %lu mk_nohash %lu\n",
           (unsigned long) c.mat_local, (unsigned long) c.xmtrx_loads, (unsigned long) c.add_rot, (unsigned long) c.hokan_bones,
           (unsigned long) c.blend_bones, (unsigned long) c.samp_int, (unsigned long) c.samp_frac, (unsigned long) c.samp_end,
           (unsigned long) c.mk_rows, (unsigned long) c.mk_dec, (unsigned long) c.mk_miss, (unsigned long) c.mk_root_rows,
           (unsigned long) c.mk_root_dec, (unsigned long) c.mk_axes, (unsigned long) c.hist_moves, (unsigned long) c.trig_hits,
           (unsigned long) c.trig_miss, (unsigned long) c.pre_bones, (unsigned long) c.mk_bound, (unsigned long) c.mk_unbound,
           (unsigned long) c.mk_rebinds, (unsigned long) c.mk_nohash);
    // lane eng-svcspd1: the queries made again in a tick with the same inputs
    e1_log("E1 COL2 line_repeats %lu sphere_repeats %lu\n", (unsigned long) col_cnt.line_repeats, (unsigned long) col_cnt.sphere_repeats);
    e1_log("E1 COL bakes %lu late %lu line %lu sphere %lu nodes %lu tris_line %lu tris_sphere %lu\n", (unsigned long) col_cnt.bakes,
           (unsigned long) col_cnt.late_bakes, (unsigned long) col_cnt.line_queries, (unsigned long) col_cnt.sphere_queries,
           (unsigned long) col_cnt.nodes_tested, (unsigned long) col_cnt.tris_line, (unsigned long) col_cnt.tris_sphere);
    // lane eng-e1e: the round-4 native services' counters (they run in this image) and the light service's
    e1_log("E1 SVC4 routes near %lu cached %lu lines %lu steps %lu direct %lu | input reads %lu vib %lu random %lu queued %lu | "
           "volumes at %lu pairs %lu pushes %lu lines %lu hits %lu | follow sets %lu moves %lu | model inits %lu infos %lu parts %lu | "
           "camera frames %lu frustums %lu keys %lu | colm checks %lu slides %lu floors %lu pieces %lu\n",
           (unsigned long) route_cnt.near_calls, (unsigned long) route_cnt.near_cached, (unsigned long) route_cnt.near_lines,
           (unsigned long) route_cnt.steps, (unsigned long) route_cnt.steps_direct, (unsigned long) input_cnt.reads,
           (unsigned long) input_cnt.vib_ticks, (unsigned long) input_cnt.vib_random, (unsigned long) input_cnt.vib_queued,
           (unsigned long) vol_cnt.at_checks, (unsigned long) vol_cnt.pairs, (unsigned long) vol_cnt.pushes,
           (unsigned long) vol_cnt.line_tests, (unsigned long) vol_cnt.line_hits, (unsigned long) follow_cnt.sets,
           (unsigned long) follow_cnt.moves, (unsigned long) model_cnt.inits, (unsigned long) model_cnt.infos,
           (unsigned long) model_cnt.parts_made, (unsigned long) cam_cnt.frames, (unsigned long) cam_cnt.frustums,
           (unsigned long) cam_cnt.keys, (unsigned long) colm_cnt.checks, (unsigned long) colm_cnt.slides,
           (unsigned long) colm_cnt.floors, (unsigned long) colm_cnt.pieces);
    // lane eng-e1j: the camera service's evaluation counters, and the conversions of game state into draw records (the
    // selector fails a scene where one is not 0: ruling H-016.2). Today none exists: the camera is the service's record,
    // the HUD and the characters' light inputs are read in place; the light view misses are pictures a character had
    // no view (lit by the fallback record).
    e1_log("E1 CAMSVC frames %lu records %lu blends %lu smooths %lu areas %lu probes %lu rails %lu shoulder %lu attached %lu "
           "tracks %lu frames-orient %lu debug %lu\n", (unsigned long) cam_cnt.frames, (unsigned long) eng_cam.tick,
           (unsigned long) cam_cnt.blends, (unsigned long) cam_cnt.smooths, (unsigned long) cam_cnt.areas,
           (unsigned long) cam_cnt.probes, (unsigned long) cam_cnt.rails, (unsigned long) cam_cnt.shoulder,
           (unsigned long) cam_cnt.attached, (unsigned long) cam_cnt.tracks, (unsigned long) cam_cnt.orient_cams,
           (unsigned long) cam_cnt.debug_draws);
    // lane eng-e1n (H-017.5): only what has a producer: the camera copy control (PUBCOPY) and the light-view misses;
    // the selector fails a scene where either is not 0 or the line is missing
    e1_log("E1 PUB camera %lu light-view-misses %lu\n", (unsigned long) eng_pub.camera, (unsigned long) e1_light_miss);
    {   // lane eng-e1n (H-017.2): the camera tracks' part-frame decodes (one a frame and part converted), moves, tracks
        // not played, the track store's use; lane eng-e1p (H-018.1): tracks converted at room load and in play, cut
        // switches served by lookup, the room's tracks and bytes. The selector fails a timing scene with a conversion in play.
        u32 now, peak, size, cuts, tracks, refused, bytes, limit;
        cam_track_store_use(&now, &peak, &size);
        cam_track_room(&cuts, &tracks, &refused, &bytes, &limit);
        e1_log("E1 CAMTRACK part-frame-decodes %lu moves %lu not-played %lu conversions %lu in-play %lu lookups %lu "
               "room-tracks %lu room-bytes %lu store-peak %lu of %lu\n", (unsigned long) cam_cnt.keys,
               (unsigned long) cam_cnt.tracks, (unsigned long) cam_cnt.key_errors, (unsigned long) cam_cnt.conversions,
               (unsigned long) cam_cnt.play_conversions, (unsigned long) cam_cnt.lookups, (unsigned long) tracks,
               (unsigned long) bytes, (unsigned long) peak, (unsigned long) size);
    }
    // lane eng-e1l: the camera record's finite check (every tick; the selector fails a scene with a non-finite tick or
    // without this line) and the renderer's planes the record holds
    e1_log("E1 CAMREC ticks %lu non-finite %lu (first tick %lu word %lu bits %08lx) near %d far %d\n",
           (unsigned long) eng_cam_check.ticks, (unsigned long) eng_cam_check.nonfinite_ticks,
           (unsigned long) eng_cam_check.first_tick, (unsigned long) eng_cam_check.first_word,
           (unsigned long) eng_cam_check.first_bits, (int) (eng_cam.p23 / (eng_cam.p22 - 1.0f)), (int) eng_cam.zfar);
}
