// svc_dump.cpp (game side; lane eng-svc): the per-tick record that compares the original skeleton and collision
// units with the native services directly. Linked into two builds of re4ref (svc/svc.mk):
//   odump   the reference (plain objects) with this dump
//   native  the native services (services/skeleton, services/collision) with this dump
// RE4_SVC_OUT=<dir> receives:
//   pal.bin   every tick, every live model with parts (characters, then objects): per bone the world matrix (3x4),
//             the world position and the skin palette (world x bind); the reference takes them from the cParts
//             records (palette: cParts::mat x cParts::lt_inv_mat), the native build from its tables after
//             skel_publish (once a tick, as the renderer would read it)
//   col.txt   every collision query the behaviour (and the IK) makes, in call order: kind, inputs, outputs as float
//             bits (--wrap on the entry points; queries made inside another query are not logged, so both builds
//             log the same boundary)
//   hist.bin  world_old and world_old2: every bone (reference), the history bones (native; lane eng-svc2)
//   svc.txt   the native services' counters (native build)
// Controls (native build, RE4_SVC_CONTROL): parent=<bone> (that bone's parent one bone too low), floor=<units>
// (floor triangles raised), noik (the IK pass skipped); poison off with RE4_SVC_POISON=0.
#include "hostref.h"
#include "model.h"
#include "motion.h"
#include "em.h"
#include "obj.h"
#include "atari.h"
#include "global.h"
#include "../../services/skeleton/skel.h"
#include "../../services/collision/col.h"
#include "../../services/cloth/cloth.h"

// svc_io.cpp (PC side)
extern "C" {
void* svc_out_open(const char* name, const char* mode);
void svc_out_write(void* f, const void* data, unsigned bytes);
void svc_out_printf(void* f, const char* fmt, ...);
void svc_out_close(void* f);
const char* svc_env(const char* name);
double svc_atof(const char* s);
}
typedef void FILE_;
#define fprintf svc_out_printf
#define fclose svc_out_close
static int svc_atoi(const char* s) { int v = 0; while (*s >= '0' && *s <= '9') v = v * 10 + (*s++ - '0'); return v; }
static int svc_prefix(const char* s, const char* p) { while (*p) if (*s++ != *p++) return 0; return 1; }
// native build only (weak: absent from odump)
extern "C" void skel_publish_all(void) __attribute__((weak));
extern "C" SkelTable* skel_table_of(const cModel* m) __attribute__((weak));
extern "C" void col_bake_all(void) __attribute__((weak));
extern "C" u32 skel_table_count(void) __attribute__((weak));
extern "C" u32 col_piece_count(void) __attribute__((weak));
extern "C" ColPiece* col_piece_at(u32 i) __attribute__((weak));
extern "C" u32 col_file_bytes(const ColPiece* pc) __attribute__((weak));
extern "C" SkelTable* skel_table_at(u32 i) __attribute__((weak));
extern "C" SkelCounters skel_cnt __attribute__((weak));
extern "C" ColCounters col_cnt __attribute__((weak));
extern "C" ClothCounters cloth_cnt __attribute__((weak));
extern "C" u32 cloth_chain_count(void) __attribute__((weak));
extern "C" ClothChain* cloth_chain_at(u32 i) __attribute__((weak));
extern "C" int skel_control_parent __attribute__((weak));
extern "C" int skel_control_no_ik __attribute__((weak));
extern "C" int skel_poison __attribute__((weak));
extern "C" f32 col_control_floor __attribute__((weak));

namespace {
FILE_* g_pal;
FILE_* g_col;
FILE_* g_hist;
unsigned g_tick;
int g_depth;

FILE_* open_out(const char* name, const char* mode) { return svc_out_open(name, mode); }
u32 bits(f32 f)
{
    u32 u;
    __builtin_memcpy(&u, &f, 4);
    return u;
}
void put_vec(const Vec* v) { fprintf(g_col, " %08x,%08x,%08x", bits(v->x), bits(v->y), bits(v->z)); }

struct PalBone {
    f32 m[12];
    f32 w[3];
    f32 p[12];
};
void dump_model(cModel* m, u32 code)
{
    if (!m->pParts || !m->nParts) return;
    static PalBone buf[256];
    u32 n = 0;
    SkelTable* t = skel_table_of ? skel_table_of(m) : 0;
    if (skel_table_of && !t) return;
    if (t) {
        n = t->n;
        for (u32 b = 0; b < n && b < 256; b++) {
            __builtin_memcpy(buf[b].m, t->world[b].m, 48);
            buf[b].w[0] = t->soa[SK_WX * t->cap + b];
            buf[b].w[1] = t->soa[SK_WY * t->cap + b];
            buf[b].w[2] = t->soa[SK_WZ * t->cap + b];
            __builtin_memcpy(buf[b].p, t->pal[b].m, 48);
        }
    } else {
        for (cParts* p = m->pList; p && n < 256; p = p->pList, n++) {
            __builtin_memcpy(buf[n].m, p->mat, 48);
            buf[n].w[0] = p->world.x;
            buf[n].w[1] = p->world.y;
            buf[n].w[2] = p->world.z;
            Mtx pal;
            PSMTXConcat(p->mat, p->lt_inv_mat, pal);
            __builtin_memcpy(buf[n].p, pal, 48);
        }
    }
    u32 hdr[2] = {code, n};
    svc_out_write(g_pal, hdr, 8);
    svc_out_write(g_pal, buf, sizeof(PalBone) * n);
    // hist.bin (lane eng-svc2): world_old and world_old2, every bone (reference) / the history bones (native)
    static f32 hb[256][7];
    u32 nh = 0;
    if (t) {
        for (u32 k = 0; k < t->nHist && nh < 256; k++, nh++) {
            u32 b = t->hlist[k];
            __builtin_memcpy(&hb[nh][0], &b, 4);
            __builtin_memcpy(&hb[nh][1], t->hold[k].old, 12);
            __builtin_memcpy(&hb[nh][4], t->hold[k].old2, 12);
        }
    } else {
        for (cParts* p = m->pList; p && nh < 256; p = p->pList, nh++) {
            __builtin_memcpy(&hb[nh][0], &nh, 4);
            __builtin_memcpy(&hb[nh][1], &p->world_old, 12);
            __builtin_memcpy(&hb[nh][4], &p->world_old2, 12);
        }
    }
    u32 hh[2] = {code, nh};
    svc_out_write(g_hist, hh, 8);
    svc_out_write(g_hist, hb, 28 * nh);
}
}   // namespace

extern "C" void host_svc_ready()
{
    const char* c = svc_env("RE4_SVC_CONTROL");
    if (c && *c) host_log("svc control: %s", c);
    if (col_bake_all) col_bake_all();   // the room's collision tables, baked at room load
    g_pal = open_out("pal.bin", "wb");
    g_col = open_out("col.txt", "w");
    g_hist = open_out("hist.bin", "wb");
}

extern "C" void host_svc_tick(unsigned t, int begin)
{
    g_tick = t;
    if (begin) return;
    if (skel_publish_all) skel_publish_all();
    if (!g_pal) return;
    u32 hdr[2] = {0x4B434954u, t};   // "TICK"
    svc_out_write(g_pal, hdr, 8);
    svc_out_write(g_hist, hdr, 8);
    const u32 elo = (u32) EmMgr.pArray, olo = (u32) ObjMgr.pArray;
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext) dump_model(e, ((u32) e - elo) / EmMgr.size);
    for (cObj* o = ObjMgr.pAlive; o; o = (cObj*) o->pNext) dump_model(o, 64 + ((u32) o - olo) / ObjMgr.size);
    u32 end[2] = {0x444E4524u, 0};   // "$END"
    svc_out_write(g_pal, end, 8);
    svc_out_write(g_hist, end, 8);
}

extern "C" void host_svc_finish()
{
    if (g_pal) fclose(g_pal);
    if (g_col) fclose(g_col);
    if (g_hist) fclose(g_hist);
    g_hist = 0;
    g_pal = 0;
    g_col = 0;
    if (&skel_cnt) {
        FILE_* f = open_out("svc.txt", "w");
        if (!f) return;
        const SkelCounters& s = skel_cnt;
        fprintf(f, "skel entries %u mat_local %u mat_world %u mat_world_slow %u xmtrx_loads %u add_rot %u samples %u "
                   "hokan_bones %u blend_bones %u ik_chains %u palette %u serve_bones %u pull_bones %u poison_bones %u parent_mismatch %u serve_ancestors %u lost_writes %u\n",
                s.entries, s.mat_local, s.mat_world, s.mat_world_slow, s.xmtrx_loads, s.add_rot, s.samples, s.hokan_bones,
                s.blend_bones, s.ik_chains, s.palette, s.serve_bones, s.pull_bones, s.poison_bones, s.parent_mismatch, s.serve_ancestors, s.lost_writes);
        if (&col_cnt) {
            const ColCounters& k = col_cnt;
            fprintf(f, "col bakes %u late_bakes %u line_queries %u sphere_queries %u nodes_tested %u leaves %u tris_line %u "
                       "tris_sphere %u tri_bytes %u cold_line %u cold_sphere %u tris_skipped %u filter_miss %u filter_end %u\n",
                    k.bakes, k.late_bakes, k.line_queries, k.sphere_queries, k.nodes_tested, k.leaves, k.tris_line,
                    k.tris_sphere, k.tri_bytes, k.cold_line, k.cold_sphere, k.tris_skipped, k.filter_miss, k.filter_end);
        }
        for (u32 i = 0; col_piece_count && i < col_piece_count(); i++) {
            ColPiece* pc = col_piece_at(i);
            fprintf(f, "piece %u sat %08x nodes %u leaves %u idx %u polys %u bytes %u file_bytes %u\n", i, (u32) pc->sat, pc->nNode,
                    pc->nLeaf, pc->nIdx, pc->nTri, pc->bytes, col_file_bytes(pc));
        }
        for (u32 i = 0; skel_table_of && i < skel_table_count(); i++) {
            SkelTable* t = skel_table_at(i);
            fprintf(f, "table %u model %08x bones %u bytes %u mailbox %u:", i, (u32) t->model, t->n, t->bytes, t->nMbox);
            for (u32 b = 0; b < t->n; b++)
                if (t->mbox[b]) fprintf(f, " %u%s", b, t->mbox[b] == 2 ? "a" : "");
            fprintf(f, "\n");
        }
        fprintf(f, "motion samples: integer frame %u fractional %u at or past the end %u\n", s.samp_int, s.samp_frac, s.samp_end);
        fprintf(f, "motion keys: clips bound %u unbound %u; calls from rows %u from cold keys %u original decoder %u\n", s.mk_bound,
                s.mk_unbound, s.mk_rows, s.mk_cold, s.mk_orig);
        if (&cloth_cnt) {
            fprintf(f, "cloth: chains %u (original fallback %u), steps %u, links stepped %u, volumes built %u, resets %u\n",
                    cloth_cnt.chains, cloth_cnt.fallback, cloth_cnt.moves, cloth_cnt.links, cloth_cnt.at_volumes, cloth_cnt.resets);
            // the chains' link bones by model code (pal.bin's), for svc/cloth_stats.py
            const u32 elo = (u32) EmMgr.pArray, olo = (u32) ObjMgr.pArray;
            for (u32 i = 0; i < cloth_chain_count(); i++) {
                ClothChain* ch = cloth_chain_at(i);
                const u32 a = (u32) ch->m;
                const u32 code = a >= elo && a < elo + EmMgr.size * EmMgr.nArray ? (a - elo) / EmMgr.size
                                                                                 : 64 + (a - olo) / ObjMgr.size;
                fprintf(f, "chain %u model %u links", i, code);
                for (u32 k = 0; k < ch->n; k++) fprintf(f, " %u", ch->link[k].bone);
                fprintf(f, "\n");
            }
        }
        fprintf(f, "history: bones joined %u (after the first updateOldPos %u), bone moves %u, set full %u\n", s.hist_join,
                s.hist_late, s.hist_moves, s.hist_full);
        fclose(f);
    }
}

// ---- the cloth's comparison mode (lane eng-svc2): RE4_SVC_CLOTH_WIND=0 sets every chain's no-wind flag (0x40) as
// it is set up, in both builds, so the cloth draws no random number and native and original compare bit for bit ----
#include "pendulum.h"
extern "C" void __real_PenClothSet(cModel* m, PenCloth* c, f32 len);
extern "C" void __wrap_PenClothSet(cModel* m, PenCloth* c, f32 len)
{
    const char* w = svc_env("RE4_SVC_CLOTH_WIND");
    if (w && *w == '0') c->Flag |= 0x40;
    __real_PenClothSet(m, c, len);
}

// ---- the collision boundary log (--wrap) ----
#define COLW(ret, mangled, params, args, log_in, log_out)                                                            \
    extern "C" ret __real_##mangled params;                                                                          \
    extern "C" ret __wrap_##mangled params                                                                           \
    {                                                                                                                \
        const bool top = g_depth == 0;                                                                               \
        if (top && g_col) { fprintf(g_col, "%u", g_tick); log_in; }                                                 \
        g_depth++;                                                                                                   \
        ret r = __real_##mangled args;                                                                               \
        g_depth--;                                                                                                   \
        if (top && g_col) { fprintf(g_col, " ->"); log_out; fprintf(g_col, "\n"); }                                 \
        return r;                                                                                                    \
    }

static const char* mgr(cSatMgr* s) { return s == &EatMgr ? "E" : "S"; }
static u32 actor(cModel* m)
{
    const u32 a = (u32) m, elo = (u32) EmMgr.pArray, olo = (u32) ObjMgr.pArray;
    if (a >= elo && a < elo + EmMgr.size * EmMgr.nArray) return (a - elo) / EmMgr.size;
    if (a >= olo && a < olo + ObjMgr.size * ObjMgr.nArray) return 64 + (a - olo) / ObjMgr.size;
    return 999;
}

COLW(f32, _ZN7cSatMgr8getFloorEP3VecffPmi, (cSatMgr* s, Vec* pos, f32 up, f32 down, u32* attr, int flag),
     (s, pos, up, down, attr, flag),
     { fprintf(g_col, " F%s", mgr(s)); put_vec(pos); fprintf(g_col, " %08x %08x %x", bits(up), bits(down), flag); },
     { fprintf(g_col, " %08x %08x", bits(r), attr ? *attr : 0); })
COLW(int, _ZN7cSatMgr8hitCheckEP3VecS1_S1_S1_ii, (cSatMgr* s, Vec* p0, Vec* p1, Vec* hit, Vec* nrm, int flag, int mask),
     (s, p0, p1, hit, nrm, flag, mask),
     { fprintf(g_col, " H%s", mgr(s)); put_vec(p0); put_vec(p1); fprintf(g_col, " %x %x", flag, mask); },
     { fprintf(g_col, " %08x", r); if (hit) put_vec(hit); if (nrm && r) put_vec(nrm); put_vec(p1); })
COLW(int, _ZN7cSatMgr9hitCheck2EP3VecS1_S1_Pmii, (cSatMgr* s, Vec* p0, Vec* p1, Vec* hit, u32* attr, int flag, int mask),
     (s, p0, p1, hit, attr, flag, mask),
     { fprintf(g_col, " L%s", mgr(s)); put_vec(p0); put_vec(p1); fprintf(g_col, " %x %x", flag, mask); },
     { fprintf(g_col, " %08x", r); if (hit) put_vec(hit); if (attr && r) fprintf(g_col, " %08x", *attr); put_vec(p1); })
COLW(int, _ZN7cSatMgr12polySphereCkEP3VecS1_fiS1_i, (cSatMgr* s, Vec* p0, Vec* p1, f32 rad, int flag, Vec* nrm, int mask),
     (s, p0, p1, rad, flag, nrm, mask),
     { fprintf(g_col, " P%s", mgr(s)); put_vec(p0); put_vec(p1); fprintf(g_col, " %08x %x %x", bits(rad), flag, mask); },
     { fprintf(g_col, " %x", r); put_vec(p1); if (nrm) put_vec(nrm); })
COLW(int, _ZN7cSatMgr5checkEP6cModeli, (cSatMgr* s, cModel* m, int flag), (s, m, flag),
     { fprintf(g_col, " C%s %u", mgr(s), actor(m)); put_vec(&m->pos); fprintf(g_col, " %x", flag); },
     { fprintf(g_col, " %x", r); put_vec(&m->pos); put_vec(&m->Wall_norm); fprintf(g_col, " %08x", (u32) m->pFloor_norm); })
COLW(int, _ZN7cSatMgr8checkAirEP6cModeli, (cSatMgr* s, cModel* m, int flag), (s, m, flag),
     { fprintf(g_col, " A%s %u", mgr(s), actor(m)); put_vec(&m->pos); fprintf(g_col, " %x", flag); },
     { fprintf(g_col, " %x", r); put_vec(&m->pos); put_vec(&m->Wall_norm); })
