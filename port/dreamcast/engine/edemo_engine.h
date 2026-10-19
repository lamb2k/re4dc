/* edemo_engine.h: the Dreamcast-native enemy runtime, phase 0 (lane edemo18, 2026-10-18).
 *
 * Standalone: not linked into the game. Proves the cost of the design in ENEMY-ENGINE-CONTRARIAN-20261018.md
 * with the baked clips (EDCL v1, tools/enginebake/bake_clips.py), the r101 room grid (EDGR v1, build_grid.py) and
 * the real PS2 Ganado meshes (EDPK MSHk, pack_demo.py).
 *
 * Function name prefixes are the hw-model areas (hwproject --area-rules): edemo_logic_* (decisions, movement, grid
 * collision, flow field, gameplay bones), edemo_anim_* (pose sampling + hierarchy on drawn frames),
 * edemo_draw_* (skin matrices, skin + project, store-queue submission), edemo_scene_* (scenery / Leon / overhead).
 *
 * Maths: column-major 4x4 (m[c * 4 + r]), mm, y up; a Ganado faces +z in model space.
 * FPSCR: -m4-single, PR = 0, SZ = 0 on entry and exit of every routine (SH4ZAM's paired moves restore SZ).
 * XMTRX: owned by the caller of an edemo_* routine only between calls; every routine that uses it loads it first.
 */
#ifndef EDEMO_ENGINE_H
#define EDEMO_ENGINE_H
#include <stdint.h>

#define ED_NB 34          /* em12:440 skeleton */
#define ED_MAXG 16
#define ED_NLOD 3

typedef struct { float m[16]; } __attribute__((aligned(32))) ed_mat4;

typedef struct {
    const uint8_t* rq;     /* 6-byte smallest-three keys */
    const uint8_t* tk;     /* s16 x3 keys (unaligned) */
    float tsc;             /* translation scale */
    float rest[3];
    uint16_t nrk, ntk;
    uint8_t rshift, tshift, tmode; /* tmode 0 rest, 2 static, 6 animated */
} ed_track;

typedef struct {
    uint16_t nf, role;
    float speed;           /* mean root speed, mm per frame (walk / run) */
    ed_track t[ED_NB];
} ed_clip;

typedef struct {
    uint32_t nv, nidx, nstrip, nrun, nchunk;
    const float* pos;      /* nv x 3 */
    const float* uv;       /* nv x 2 */
    const uint8_t *b0, *b1, *w0;
    const uint16_t* slen;
    const uint16_t* idx;
    const uint8_t* runs;   /* nrun x {u16 count, u8 b0, u8 b1} */
    const uint16_t* chunks;/* nchunk x {vertex_end, strip_end, run_end, pad} */
    float* vb;             /* nv x 32-byte PVR vertex images (flags, x, y, z, u, v, argb, oargb), 32-aligned: u / v / flags
                              static, x / y / z / argb written by the skin pass, copied to the store queues per strip vertex */
} ed_mesh;

typedef struct {
    uint16_t w, h;
    float x0, z0, cell, inv_cell;
    uint16_t nplane, nseg;
    const uint8_t* cells;  /* 6 B: floor, nwall, nbr, pad, u16 wofs */
    const float* planes;   /* 3 f32: y = a x + c z + d */
    const int16_t* segs;   /* 6 s16 cm: x0 z0 x1 z1 ymin ymax */
    const uint16_t* wl;
} ed_grid;

typedef struct {
    int n;                 /* Ganados */
    int skin2;             /* 1: 2-bone, 0: rigid (dominant bone) */
    int lod;               /* 0 g70, 1 g50, 2 g33, 3 distance (g70 < 10 m < g50 < 20 m < g33) */
    int logic_hz;          /* 30 or 15 (staggered halves, render interpolation) */
    int zam;               /* 1: SH4ZAM XMTRX/FTRV/FSRRA paths, 0: plain C */
    int frames;            /* segment length */
    int still;             /* 0 run; 1 / 2 still pair (walk / attack pose, one Ganado, fixed camera) */
    int scen;              /* 0 melee (spawn 4-8 m from the arena centre), 1 approach (spawn 10-25 m) */
} ed_arm;

typedef struct {
    float x, y, z;         /* logic position (feet) */
    float px, py, pz;      /* previous logic position (15 Hz interpolation) */
    float fx, fz;          /* facing (unit) */
    float pfx, pfz;
    float frame;           /* clip frame */
    int clip;              /* role index */
    int state;             /* 0 chase, 1 attack, 2 recover */
    int cooldown;
    int since_logic;
    int hits;
    int attacks;
    int lod_used;
    float hand[3], head[3];/* gameplay bones (model -> world) */
    uint32_t argb;
} ed_ganado;

typedef struct {
    ed_mat4 model[ED_NB];  /* model space, current drawn pose */
    ed_mat4 skin[ED_NB];   /* VP * world * model * inv_bind */
} ed_pose;

typedef struct {
    float x, y, z, rw;     /* screen x, y, 1/w, pad */
} ed_proj;

typedef struct {
    ed_clip clips[4];
    ed_mesh mesh[ED_NLOD];
    ed_grid grid;
    int8_t parent[ED_NB];
    float rest[ED_NB][3];
    ed_mat4 inv_bind[ED_NB];
    float arena[3];
    const uint8_t* tex;
    uint32_t tex_bytes;
} ed_data;

typedef struct {
    uint64_t logic_ns, flow_ns, anim_ns, draw_ns, scene_ns;
    uint32_t verts, ganados_drawn, flow_runs;
} ed_stats;

int edemo_load(ed_data* d, const uint8_t* pak, uint32_t size);

/* animation (drawn frames): full skeleton into pose->model */
void edemo_anim_pose(const ed_data* d, const ed_clip* c, float frame, ed_pose* p, int zam);
/* gameplay bones on logic ticks: the head (4) and right hand (16) chains only, model space */
void edemo_logic_bones(const ed_data* d, const ed_clip* c, float frame, float head[3], float hand[3]);

/* drawing */
void edemo_draw_skinmats(const ed_data* d, const ed_mat4* vpw, ed_pose* p, int zam);
uint32_t edemo_draw_mesh(const ed_mesh* m, const ed_pose* p, ed_proj* scratch, int skin2, int zam, uint32_t argb);

/* logic */
void edemo_logic_flow(const ed_data* d, float lx, float lz);
void edemo_logic_tick(const ed_data* d, ed_ganado* g, int n, int tick, int logic_hz, float lx, float ly, float lz);

/* maths shared by the demo */
void ed_mat_mul(ed_mat4* o, const ed_mat4* a, const ed_mat4* b, int zam);
float ed_floor_y(const ed_grid* g, float x, float z, int* ok);
#endif
