/* edemo_engine.c: the Dreamcast-native enemy runtime, phase 0 (lane edemo18). See edemo_engine.h. */
#include "edemo_engine.h"
#include <string.h>
#include <stdlib.h>
#include <malloc.h>
#include <math.h>
#include <dc/pvr.h>
#include <sh4zam/shz_xmtrx.h>
#include <sh4zam/shz_scalar.h>
#include <sh4zam/shz_mem.h>

#define ED_NOINLINE __attribute__((noinline))
#ifndef ED_PF
#define ED_PF 1
#endif
#ifndef ED_MOVCA
#define ED_MOVCA 1
#endif

static inline uint32_t rd32(const uint8_t* p) { uint32_t v; memcpy(&v, p, 4); return v; }
static inline uint16_t rd16(const uint8_t* p) { return (uint16_t)(p[0] | (p[1] << 8)); }
static inline int16_t rds16(const uint8_t* p) { return (int16_t)(p[0] | (p[1] << 8)); }
static inline float rdf(const uint8_t* p) { float v; memcpy(&v, p, 4); return v; }

/* ------------------------------------------------------------------------------------------- load */
static const uint8_t* find_sec(const uint8_t* pak, const char* tag, uint32_t* size)
{
    uint32_t n = rd32(pak + 4);
    for (uint32_t i = 0; i < n; i++) {
        const uint8_t* e = pak + 8 + 12 * i;
        if (!memcmp(e, tag, 4)) {
            *size = rd32(e + 8);
            return pak + rd32(e + 4);
        }
    }
    *size = 0;
    return 0;
}

static void parse_clip(ed_clip* c, const uint8_t* p, const ed_data* d)
{
    const uint8_t* s = p;
    uint16_t nf = rd16(p);
    int n = p[2];
    p += 4;
    c->nf = nf;
    for (int i = 0; i < n && i < ED_NB; i++) {
        ed_track* t = &c->t[i];
        uint8_t fl = *p++;
        t->rshift = (fl >> 3) & 3;
        t->tshift = (fl >> 5) & 3;
        t->tmode = fl & 6;
        t->nrk = (fl & 1) ? (uint16_t) ((((nf - 1) + (1 << t->rshift) - 1) >> t->rshift) + 1) : 1;
        t->rq = p;
        p += 6 * t->nrk;
        memcpy(t->rest, d->rest[i], 12);
        t->ntk = 1;
        t->tk = 0;
        t->tsc = 0;
        if (t->tmode) {
            t->tsc = rdf(p);
            p += 4;
            t->ntk = (t->tmode == 2) ? 1 : (uint16_t) ((((nf - 1) + (1 << t->tshift) - 1) >> t->tshift) + 1);
            t->tk = p;
            p += 6 * t->ntk;
        }
        if (fl & 0x80) {
            p += 6 * nf;
        }
    }
    p = s + ((p - s + 3) & ~3);
    float rsc = rdf(p);
    p += 4;
    float sum = 0;
    for (int f = 0; f + 1 < nf; f++) {
        float dx = (rds16(p + 12 * (f + 1)) - rds16(p + 12 * f)) * rsc;
        float dz = (rds16(p + 12 * (f + 1) + 4) - rds16(p + 12 * f + 4)) * rsc;
        sum += sqrtf(dx * dx + dz * dz);
    }
    c->speed = nf > 1 ? sum / (nf - 1) : 0;
}

int edemo_load(ed_data* d, const uint8_t* pak, uint32_t size)
{
    uint32_t sz;
    const uint8_t* s;
    (void) size;
    if (memcmp(pak, "EDPK", 4)) return -1;
    s = find_sec(pak, "SKEL", &sz);
    if (!s || rd32(s) != ED_NB) return -2;
    for (int i = 0; i < ED_NB; i++) {
        const uint8_t* b = s + 4 + 80 * i;
        d->parent[i] = (int8_t) rd32(b);
        memcpy(d->rest[i], b + 4, 12);
        memcpy(d->inv_bind[i].m, b + 16, 64);
    }
    s = find_sec(pak, "CLIP", &sz);
    if (!s) return -3;
    uint32_t nc = rd32(s);
    for (uint32_t k = 0; k < nc && k < 4; k++) {
        const uint8_t* e = s + 4 + 8 * k;
        int role = rd16(e + 6);
        if (role > 3) continue;
        parse_clip(&d->clips[role], s + rd32(e), d);
        d->clips[role].role = role;
    }
    for (int l = 0; l < ED_NLOD; l++) {
        char tag[5] = { 'M', 'S', 'H', (char) ('0' + l), 0 };
        s = find_sec(pak, tag, &sz);
        if (!s) return -4;
        ed_mesh* m = &d->mesh[l];
        m->nv = rd32(s); m->nidx = rd32(s + 4); m->nstrip = rd32(s + 8); m->nrun = rd32(s + 12); m->nchunk = rd32(s + 16);
        const uint8_t* p = s + 20;
        m->pos = (const float*) p; p += 12 * m->nv;
        m->uv = (const float*) p; p += 8 * m->nv;
        m->b0 = p; p += m->nv;
        m->b1 = p; p += m->nv;
        m->w0 = p; p += m->nv;
        p = s + ((p - s + 3) & ~3);
        m->slen = (const uint16_t*) p; p += 2 * m->nstrip;
        m->idx = (const uint16_t*) p; p += 2 * m->nidx;
        p = s + ((p - s + 3) & ~3);
        m->runs = p;
        m->chunks = (const uint16_t*) (p + 4 * m->nrun);
        m->vb = memalign(32, 32 * m->nv);
        for (uint32_t i = 0; i < m->nv; i++) {
            uint32_t* w = (uint32_t*) (m->vb + 8 * i);
            w[0] = PVR_CMD_VERTEX;
            m->vb[8 * i + 4] = m->uv[2 * i];
            m->vb[8 * i + 5] = m->uv[2 * i + 1];
            w[7] = 0;
        }
    }
    s = find_sec(pak, "GRID", &sz);
    if (!s || memcmp(s, "EDGR", 4)) return -5;
    ed_grid* g = &d->grid;
    g->w = rd16(s + 4); g->h = rd16(s + 6);
    g->x0 = rdf(s + 8); g->z0 = rdf(s + 12);
    g->cell = rd16(s + 16); g->inv_cell = 1.0f / g->cell;
    g->nplane = rd16(s + 18); g->nseg = rd16(s + 20);
    g->cells = s + 24;
    g->planes = (const float*) (s + 24 + 6 * g->w * g->h);
    g->segs = (const int16_t*) ((const uint8_t*) g->planes + 12 * g->nplane);
    g->wl = (const uint16_t*) ((const uint8_t*) g->segs + 12 * g->nseg);
    s = find_sec(pak, "TEXR", &sz);
    if (!s) return -6;
    d->tex = s + 8;
    d->tex_bytes = sz - 8;
    s = find_sec(pak, "MISC", &sz);
    if (!s) return -7;
    memcpy(d->arena, s, 12);
    return 0;
}

/* ------------------------------------------------------------------------------------------- maths */
static inline float ed_rsqrt(float x, int zam)
{
    return zam ? shz_inv_sqrtf(x) : 1.0f / sqrtf(x);
}

static void mul_plain(ed_mat4* o, const ed_mat4* a, const ed_mat4* b)
{
    ed_mat4 t;
    for (int c = 0; c < 4; c++) {
        const float* bc = &b->m[c * 4];
        for (int r = 0; r < 4; r++) {
            t.m[c * 4 + r] = a->m[r] * bc[0] + a->m[4 + r] * bc[1] + a->m[8 + r] * bc[2] + a->m[12 + r] * bc[3];
        }
    }
    *o = t;
}

void ed_mat_mul(ed_mat4* o, const ed_mat4* a, const ed_mat4* b, int zam)
{
    if (zam) {
        shz_xmtrx_load_4x4((const shz_mat4x4_t*) a);
        shz_xmtrx_apply_4x4((const shz_mat4x4_t*) b);
        shz_xmtrx_store_4x4((shz_mat4x4_t*) o);
    } else {
        mul_plain(o, a, b);
    }
}

/* 48-bit smallest-three quaternion (x, y, z, w) */
static inline void q48(const uint8_t* b, float q[4], int zam)
{
    uint32_t lo = rd32(b);
    uint32_t hi = rd16(b + 4);
    int i = hi >> 13;
    const float K = 1.41421356f / 32767.0f, L = 0.70710678f;
    float v0 = (float) (((hi << 2) | (lo >> 30)) & 0x7FFF) * K - L;
    float v1 = (float) ((lo >> 15) & 0x7FFF) * K - L;
    float v2 = (float) (lo & 0x7FFF) * K - L;
    float s = 1.0f - (v0 * v0 + v1 * v1 + v2 * v2);
    float big = s > 1e-12f ? s * ed_rsqrt(s, zam) : 0.0f;
    switch (i) {
    case 0: q[0] = big; q[1] = v0; q[2] = v1; q[3] = v2; break;
    case 1: q[0] = v0; q[1] = big; q[2] = v1; q[3] = v2; break;
    case 2: q[0] = v0; q[1] = v1; q[2] = big; q[3] = v2; break;
    default: q[0] = v0; q[1] = v1; q[2] = v2; q[3] = big; break;
    }
}

static const float inv_step[4] = { 1.0f, 0.5f, 0.25f, 0.125f };

static inline int seg_of(int n, int shift, int nf, float f, float* t)
{
    int k = ((int) f) >> shift;
    if (k > n - 2) k = n - 2;
    int a = k << shift, b = (k + 1) << shift;
    if (b > nf - 1) b = nf - 1;
    if (b == a) { *t = 0; return k; }
    float tt = (b - a == (1 << shift)) ? (f - a) * inv_step[shift] : (f - a) / (float) (b - a);
    *t = tt < 0 ? 0 : (tt > 1 ? 1 : tt);
    return k;
}

static inline void track_local(const ed_track* t, int nf, float f, ed_mat4* l, int zam)
{
    float q[4], tr[3];
    if (t->nrk == 1) {
        q48(t->rq, q, zam);
    } else {
        float u, a[4], b[4];
        int k = seg_of(t->nrk, t->rshift, nf, f, &u);
        q48(t->rq + 6 * k, a, zam);
        q48(t->rq + 6 * k + 6, b, zam);
        float dot = a[0] * b[0] + a[1] * b[1] + a[2] * b[2] + a[3] * b[3];
        if (dot < 0) { b[0] = -b[0]; b[1] = -b[1]; b[2] = -b[2]; b[3] = -b[3]; }
        q[0] = a[0] + (b[0] - a[0]) * u; q[1] = a[1] + (b[1] - a[1]) * u;
        q[2] = a[2] + (b[2] - a[2]) * u; q[3] = a[3] + (b[3] - a[3]) * u;
        float r = ed_rsqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3], zam);
        q[0] *= r; q[1] *= r; q[2] *= r; q[3] *= r;
    }
    if (t->tmode == 0) {
        tr[0] = t->rest[0]; tr[1] = t->rest[1]; tr[2] = t->rest[2];
    } else if (t->ntk == 1) {
        tr[0] = rds16(t->tk) * t->tsc; tr[1] = rds16(t->tk + 2) * t->tsc; tr[2] = rds16(t->tk + 4) * t->tsc;
    } else {
        float u;
        int k = seg_of(t->ntk, t->tshift, nf, f, &u);
        const uint8_t* p = t->tk + 6 * k;
        for (int c = 0; c < 3; c++) {
            float a = rds16(p + 2 * c), b = rds16(p + 6 + 2 * c);
            tr[c] = (a + (b - a) * u) * t->tsc;
        }
    }
    float x = q[0], y = q[1], z = q[2], w = q[3];
    float* m = l->m;
    m[0] = 1 - 2 * (y * y + z * z); m[1] = 2 * (x * y + z * w); m[2] = 2 * (x * z - y * w); m[3] = 0;
    m[4] = 2 * (x * y - z * w); m[5] = 1 - 2 * (x * x + z * z); m[6] = 2 * (y * z + x * w); m[7] = 0;
    m[8] = 2 * (x * z + y * w); m[9] = 2 * (y * z - x * w); m[10] = 1 - 2 * (x * x + y * y); m[11] = 0;
    m[12] = tr[0]; m[13] = tr[1]; m[14] = tr[2]; m[15] = 1;
}

/* affine a (parent, model space) x affine b (local): only the 3x4 part is live */
static inline void mul_affine_plain(ed_mat4* o, const ed_mat4* a, const ed_mat4* b)
{
    const float* A = a->m;
    const float* B = b->m;
    float* O = o->m;
    for (int c = 0; c < 4; c++) {
        float b0 = B[c * 4], b1 = B[c * 4 + 1], b2 = B[c * 4 + 2];
        O[c * 4 + 0] = A[0] * b0 + A[4] * b1 + A[8] * b2 + (c == 3 ? A[12] : 0);
        O[c * 4 + 1] = A[1] * b0 + A[5] * b1 + A[9] * b2 + (c == 3 ? A[13] : 0);
        O[c * 4 + 2] = A[2] * b0 + A[6] * b1 + A[10] * b2 + (c == 3 ? A[14] : 0);
        O[c * 4 + 3] = (c == 3) ? 1.0f : 0.0f;
    }
}

ED_NOINLINE void edemo_anim_pose(const ed_data* d, const ed_clip* c, float frame, ed_pose* p, int zam)
{
    ed_mat4 local;
    for (int i = 0; i < ED_NB; i++) {
        track_local(&c->t[i], c->nf, frame, &local, zam);
        int par = d->parent[i];
        if (par < 0) {
            p->model[i] = local;
        } else if (zam) {
            /* XMTRX = parent; apply the local transform (4 FTRV), store */
            shz_xmtrx_load_4x4((const shz_mat4x4_t*) &p->model[par]);
            shz_xmtrx_apply_4x4((const shz_mat4x4_t*) &local);
            shz_xmtrx_store_4x4((shz_mat4x4_t*) &p->model[i]);
        } else {
            mul_affine_plain(&p->model[i], &p->model[par], &local);
        }
    }
}

/* the head (4) and right-hand (16) chains only: 0 1 2 3 4 / 11 13 14 15 16 */
ED_NOINLINE void edemo_logic_bones(const ed_data* d, const ed_clip* c, float frame, float head[3], float hand[3])
{
    static const uint8_t chain[] = { 0, 1, 2, 3, 4, 11, 13, 14, 15, 16 };
    ed_mat4 m[ED_NB];
    ed_mat4 local;
    for (unsigned k = 0; k < sizeof chain; k++) {
        int i = chain[k];
        track_local(&c->t[i], c->nf, frame, &local, 1);
        int par = d->parent[i];
        if (par < 0) m[i] = local;
        else mul_affine_plain(&m[i], &m[par], &local);
    }
    head[0] = m[4].m[12]; head[1] = m[4].m[13]; head[2] = m[4].m[14];
    hand[0] = m[16].m[12]; hand[1] = m[16].m[13]; hand[2] = m[16].m[14];
}

/* ------------------------------------------------------------------------------------------- draw */
ED_NOINLINE void edemo_draw_skinmats(const ed_data* d, const ed_mat4* vpw, ed_pose* p, int zam)
{
    for (int i = 0; i < ED_NB; i++) {
        if (zam) {
            shz_xmtrx_load_4x4((const shz_mat4x4_t*) vpw);
            shz_xmtrx_apply_4x4((const shz_mat4x4_t*) &p->model[i]);
            shz_xmtrx_apply_4x4((const shz_mat4x4_t*) &d->inv_bind[i]);
            shz_xmtrx_store_4x4((shz_mat4x4_t*) &p->skin[i]);
        } else {
            ed_mat4 t;
            mul_plain(&t, vpw, &p->model[i]);
            mul_plain(&p->skin[i], &t, &d->inv_bind[i]);
        }
    }
}

static inline void xf_plain(const float* m, const float* v, float* X, float* Y, float* W)
{
    *X = m[0] * v[0] + m[4] * v[1] + m[8] * v[2] + m[12];
    *Y = m[1] * v[0] + m[5] * v[1] + m[9] * v[2] + m[13];
    *W = m[3] * v[0] + m[7] * v[1] + m[11] * v[2] + m[15];
}

static ED_NOINLINE void edemo_draw_skin_zam(const ed_mesh* m, const ed_pose* p, ed_proj* o, int skin2)
{
    const float* pos = m->pos;
    const uint8_t* r = m->runs;
    int v = 0, loaded = -1;
    for (uint32_t k = 0; k < m->nrun; k++, r += 4) {
        int cnt = rd16(r), b0 = r[2], b1 = r[3];
        int end = v + cnt;
        if (b0 != loaded) {
            shz_xmtrx_load_4x4((const shz_mat4x4_t*) &p->skin[b0]);
            loaded = b0;
        }
        if (!skin2 || b0 == b1) {
            for (int i = v; i < end; i++) {
                const float* q = pos + 3 * i;
                shz_vec4_t t = shz_xmtrx_transform_vec4((shz_vec4_t) { .x = q[0], .y = q[1], .z = q[2], .w = 1.0f });
                float rw = shz_invf(t.w);
                o[i].x = t.x * rw; o[i].y = t.y * rw; o[i].z = rw;
            }
        } else {
            for (int i = v; i < end; i++) {
                const float* q = pos + 3 * i;
                shz_vec4_t t = shz_xmtrx_transform_vec4((shz_vec4_t) { .x = q[0], .y = q[1], .z = q[2], .w = 1.0f });
                o[i].x = t.x; o[i].y = t.y; o[i].z = t.w;
            }
            shz_xmtrx_load_4x4((const shz_mat4x4_t*) &p->skin[b1]);
            loaded = b1;
            for (int i = v; i < end; i++) {
                const float* q = pos + 3 * i;
                shz_vec4_t t = shz_xmtrx_transform_vec4((shz_vec4_t) { .x = q[0], .y = q[1], .z = q[2], .w = 1.0f });
                float w = m->w0[i] * (1.0f / 255.0f);
                float X = t.x + (o[i].x - t.x) * w;
                float Y = t.y + (o[i].y - t.y) * w;
                float W = t.w + (o[i].z - t.w) * w;
                float rw = shz_invf(W);
                o[i].x = X * rw; o[i].y = Y * rw; o[i].z = rw;
            }
        }
        v = end;
    }
}

/* SH4ZAM arm: XMTRX-resident skin + project straight into the 32-byte PVR vertex images */
static ED_NOINLINE int edemo_draw_skin_vb(const ed_mesh* m, const ed_pose* p, int skin2, uint32_t argb, uint32_t r0, uint32_t r1,
                                          int v, int loaded)
{
    const float* pos = m->pos;
    const uint8_t* r = m->runs + 4 * r0;
    float* vb = m->vb;
    const float* uv = m->uv;
    union { uint32_t u; float f; } col = { argb };
    for (uint32_t k = r0; k < r1; k++, r += 4) {
        int cnt = rd16(r), b0 = r[2], b1 = r[3];
        int end = v + cnt;
        if (b0 != loaded) {
            shz_xmtrx_load_4x4((const shz_mat4x4_t*) &p->skin[b0]);
            loaded = b0;
        }
        if (!skin2 || b0 == b1) {
            for (int i = v; i < end; i++) {
                const float* q = pos + 3 * i;
                if (ED_PF) __builtin_prefetch(q + 16);   /* positions stream: the line 64 B ahead */
                float* o = vb + 8 * i;
                shz_vec4_t t = shz_xmtrx_transform_vec4((shz_vec4_t) { .x = q[0], .y = q[1], .z = q[2], .w = 1.0f });
                float rw = shz_invf(t.w);
                if (ED_MOVCA) {
                    /* allocate the image's cache line without fetching it (MOVCA.L), then write all 8 words */
                    shz_dcache_alloc_line(o);
                    ((uint32_t*) o)[0] = PVR_CMD_VERTEX; o[4] = uv[2 * i]; o[5] = uv[2 * i + 1]; ((uint32_t*) o)[7] = 0;
                }
                o[1] = t.x * rw; o[2] = t.y * rw; o[3] = rw; o[6] = col.f;
            }
        } else {
            for (int i = v; i < end; i++) {
                const float* q = pos + 3 * i;
                if (ED_PF) __builtin_prefetch(q + 16);   /* positions stream: the line 64 B ahead */
                float* o = vb + 8 * i;
                shz_vec4_t t = shz_xmtrx_transform_vec4((shz_vec4_t) { .x = q[0], .y = q[1], .z = q[2], .w = 1.0f });
                if (ED_MOVCA) {
                    shz_dcache_alloc_line(o);
                    ((uint32_t*) o)[0] = PVR_CMD_VERTEX; o[4] = uv[2 * i]; o[5] = uv[2 * i + 1]; ((uint32_t*) o)[7] = 0;
                }
                o[1] = t.x; o[2] = t.y; o[3] = t.w;
            }
            shz_xmtrx_load_4x4((const shz_mat4x4_t*) &p->skin[b1]);
            loaded = b1;
            for (int i = v; i < end; i++) {
                const float* q = pos + 3 * i;
                if (ED_PF) __builtin_prefetch(q + 16);   /* positions stream: the line 64 B ahead */
                float* o = vb + 8 * i;
                shz_vec4_t t = shz_xmtrx_transform_vec4((shz_vec4_t) { .x = q[0], .y = q[1], .z = q[2], .w = 1.0f });
                float w = m->w0[i] * (1.0f / 255.0f);
                float X = t.x + (o[1] - t.x) * w;
                float Y = t.y + (o[2] - t.y) * w;
                float W = t.w + (o[3] - t.w) * w;
                float rw = shz_invf(W);
                o[1] = X * rw; o[2] = Y * rw; o[3] = rw; o[6] = col.f;
            }
        }
        v = end;
    }
    return loaded;
}

/* strip vertices to the TA: one 32-byte paired-move copy per vertex from the images into the store queue
 * (FPSCR.SZ = 1 for the strip, restored), pref fires the queue; the strip's last vertex is written with EOL. */
static ED_NOINLINE uint32_t edemo_draw_submit_sq(const ed_mesh* m, uint32_t s0, uint32_t s1, const uint16_t* idx)
{
    const float* vb = m->vb;
    uint32_t sq = pvr_dr_addr;
    uint32_t n = 0;
    const uint32_t t32 = 32;
    for (uint32_t s = s0; s < s1; s++) {
        int len = m->slen[s];
        int body = len - 1;
        if (body > 0) {
            const uint16_t* ip = idx;
            int c = body;
            __asm__ __volatile__(
                "fschg\n"
                "1:\n\t"
                "mov.w @%[ip]+, r0\n\t"
                "extu.w r0, r0\n\t"
                "shll2 r0\n\t"
                "shll2 r0\n\t"
                "shll r0\n\t"
                "add %[vb], r0\n\t"
                "fmov.d @r0+, dr0\n\t"
                "fmov.d @r0+, dr2\n\t"
                "fmov.d @r0+, dr4\n\t"
                "fmov.d @r0+, dr6\n\t"
                "xor %[t32], %[sq]\n\t"
                "add #32, %[sq]\n\t"
                "fmov.d dr6, @-%[sq]\n\t"
                "fmov.d dr4, @-%[sq]\n\t"
                "fmov.d dr2, @-%[sq]\n\t"
                "fmov.d dr0, @-%[sq]\n\t"
                "dt %[c]\n\t"
                "bf/s 1b\n\t"
                "pref @%[sq]\n\t"
                "fschg\n"
                : [ip] "+r" (ip), [sq] "+r" (sq), [c] "+r" (c)
                : [vb] "r" (vb), [t32] "r" (t32)
                : "r0", "fr0", "fr1", "fr2", "fr3", "fr4", "fr5", "fr6", "fr7", "t", "memory");
            idx += body;
        }
        /* last vertex: end of strip */
        const uint32_t* src = (const uint32_t*) (vb + 8 * *idx++);
        sq ^= 32;
        uint32_t* d = (uint32_t*) sq;
        d[0] = PVR_CMD_VERTEX_EOL; d[1] = src[1]; d[2] = src[2]; d[3] = src[3];
        d[4] = src[4]; d[5] = src[5]; d[6] = src[6]; d[7] = 0;
        __asm__ __volatile__("pref @%0" : : "r" (d), "m" (*(uint32_t (*)[8]) d));
        n += len;
    }
    pvr_dr_addr = sq;
    return n;
}

static ED_NOINLINE void edemo_draw_skin_plain(const ed_mesh* m, const ed_pose* p, ed_proj* o, int skin2)
{
    const float* pos = m->pos;
    const uint8_t* r = m->runs;
    int v = 0;
    for (uint32_t k = 0; k < m->nrun; k++, r += 4) {
        int cnt = rd16(r), b0 = r[2], b1 = r[3];
        int end = v + cnt;
        const float* s0 = p->skin[b0].m;
        const float* s1 = p->skin[b1].m;
        for (int i = v; i < end; i++) {
            float X, Y, W;
            xf_plain(s0, pos + 3 * i, &X, &Y, &W);
            if (skin2 && b0 != b1) {
                float X1, Y1, W1;
                xf_plain(s1, pos + 3 * i, &X1, &Y1, &W1);
                float w = m->w0[i] * (1.0f / 255.0f);
                X = X1 + (X - X1) * w; Y = Y1 + (Y - Y1) * w; W = W1 + (W - W1) * w;
            }
            float rw = 1.0f / W;
            o[i].x = X * rw; o[i].y = Y * rw; o[i].z = rw;
        }
        v = end;
    }
}

static ED_NOINLINE uint32_t edemo_draw_submit(const ed_mesh* m, const ed_proj* o, uint32_t argb)
{
    const uint16_t* idx = m->idx;
    const float* uv = m->uv;
    uint32_t n = 0;
    for (uint32_t s = 0; s < m->nstrip; s++) {
        int len = m->slen[s];
        for (int j = 0; j < len; j++) {
            int i = *idx++;
            pvr_vertex_t* vx = pvr_dr_target();
            vx->flags = (j == len - 1) ? PVR_CMD_VERTEX_EOL : PVR_CMD_VERTEX;
            vx->x = o[i].x;
            vx->y = o[i].y;
            vx->z = o[i].z;
            vx->u = uv[2 * i];
            vx->v = uv[2 * i + 1];
            vx->argb = argb;
            vx->oargb = 0;
            pvr_dr_commit(vx);
        }
        n += len;
    }
    return n;
}

uint32_t edemo_draw_mesh(const ed_mesh* m, const ed_pose* p, ed_proj* scratch, int skin2, int zam, uint32_t argb)
{
    if (zam == 1) {
        /* chunked: skin a chunk's new vertices (bone runs), then submit the chunk's strips while the images are cached */
        uint32_t r0 = 0, s0 = 0, n = 0;
        int v = 0, loaded = -1;
        const uint16_t* idx = m->idx;
        for (uint32_t c = 0; c < m->nchunk; c++) {
            const uint16_t* ch = m->chunks + 4 * c;
            loaded = edemo_draw_skin_vb(m, p, skin2, argb, r0, ch[2], v, loaded);
            v = ch[0];
            uint32_t k = edemo_draw_submit_sq(m, s0, ch[1], idx);
            idx += k;
            n += k;
            r0 = ch[2];
            s0 = ch[1];
        }
        return n;
    }
    if (zam == 4) {   /* the same paths, not chunked: every image first, then every strip */
        edemo_draw_skin_vb(m, p, skin2, argb, 0, m->nrun, 0, -1);
        return edemo_draw_submit_sq(m, 0, m->nstrip, m->idx);
    }
    if (zam == 2) edemo_draw_skin_zam(m, p, scratch, skin2);   /* SH4ZAM skin, C submit (the first measured layout) */
    else edemo_draw_skin_plain(m, p, scratch, skin2);
    return edemo_draw_submit(m, scratch, argb);
}

/* ------------------------------------------------------------------------------------------- logic */
static const int8_t DX[8] = { 1, 1, 0, -1, -1, -1, 0, 1 };
static const int8_t DZ[8] = { 0, 1, 1, 1, 0, -1, -1, -1 };
static const float UX[8] = { 1, 0.70710678f, 0, -0.70710678f, -1, -0.70710678f, 0, 0.70710678f };
static const float UZ[8] = { 0, 0.70710678f, 1, 0.70710678f, 0, -0.70710678f, -1, -0.70710678f };
#define FLOW_R 24

static uint8_t* flow_dir;
static uint16_t* flow_stamp;
static uint16_t flow_gen;
static int flow_cell = -1;
static uint16_t flow_q[(2 * FLOW_R + 1) * (2 * FLOW_R + 1)];

static inline int cell_of(const ed_grid* g, float x, float z)
{
    int cx = (int) ((x - g->x0) * g->inv_cell), cz = (int) ((z - g->z0) * g->inv_cell);
    if (cx < 0 || cz < 0 || cx >= g->w || cz >= g->h) return -1;
    return cx + cz * g->w;
}

float ed_floor_y(const ed_grid* g, float x, float z, int* ok)
{
    int c = cell_of(g, x, z);
    if (c < 0 || g->cells[6 * c] == 0xFF) { *ok = 0; return 0; }
    const float* pl = g->planes + 3 * g->cells[6 * c];
    *ok = 1;
    return pl[0] * x + pl[1] * z + pl[2];
}

/* one shared flow field toward Leon: BFS over the 8-neighbour passability bits inside a (2R+1)^2 window,
 * rerun only when Leon changes cell */
ED_NOINLINE void edemo_logic_flow(const ed_data* d, float lx, float lz)
{
    const ed_grid* g = &d->grid;
    int c0 = cell_of(g, lx, lz);
    if (c0 == flow_cell || c0 < 0) return;
    if (!flow_dir) {
        flow_dir = malloc(g->w * g->h);
        flow_stamp = calloc(g->w * g->h, 2);
    }
    flow_cell = c0;
    if (++flow_gen == 0) { memset(flow_stamp, 0, 2 * g->w * g->h); flow_gen = 1; }
    int cx0 = c0 % g->w, cz0 = c0 / g->w;
    int head = 0, tail = 0;
    flow_q[tail++] = (uint16_t) c0;
    flow_stamp[c0] = flow_gen;
    flow_dir[c0] = 0xFF;
    while (head < tail) {
        int c = flow_q[head++];
        int cx = c % g->w, cz = c / g->w;
        uint8_t nb = g->cells[6 * c + 2];
        for (int k = 0; k < 8; k++) {
            if (!(nb & (1 << k))) continue;
            int nx = cx + DX[k], nz = cz + DZ[k];
            if (nx < cx0 - FLOW_R || nx > cx0 + FLOW_R || nz < cz0 - FLOW_R || nz > cz0 + FLOW_R) continue;
            int n = nx + nz * g->w;
            if (flow_stamp[n] == flow_gen) continue;
            flow_stamp[n] = flow_gen;
            flow_dir[n] = (uint8_t) ((k + 4) & 7);   /* from n back toward c */
            flow_q[tail++] = (uint16_t) n;
        }
    }
}

static inline void collide_walls(const ed_grid* g, ed_ganado* e)
{
    int c = cell_of(g, e->x, e->z);
    if (c < 0) return;
    const uint8_t* cl = g->cells + 6 * c;
    int nw = cl[1];
    const uint16_t* wl = g->wl + rd16(cl + 4);
    for (int k = 0; k < nw; k++) {
        const int16_t* s = g->segs + 6 * wl[k];
        float ymin = s[4] * 10.0f, ymax = s[5] * 10.0f;
        if (ymax < e->y + 300.0f || ymin > e->y + 1600.0f) continue;
        float x0 = s[0] * 10.0f, z0 = s[1] * 10.0f, x1 = s[2] * 10.0f, z1 = s[3] * 10.0f;
        float dx = x1 - x0, dz = z1 - z0;
        float L = dx * dx + dz * dz;
        float t = L > 0 ? ((e->x - x0) * dx + (e->z - z0) * dz) / L : 0;
        t = t < 0 ? 0 : (t > 1 ? 1 : t);
        float px = e->x - (x0 + t * dx), pz = e->z - (z0 + t * dz);
        float d2 = px * px + pz * pz;
        if (d2 < 300.0f * 300.0f && d2 > 1e-6f) {
            float r = shz_inv_sqrtf(d2);
            float push = 300.0f - d2 * r;
            e->x += px * r * push;
            e->z += pz * r * push;
        }
    }
}

ED_NOINLINE void edemo_logic_tick(const ed_data* d, ed_ganado* g, int n, int tick, int logic_hz, float lx, float ly, float lz)
{
    const ed_grid* gr = &d->grid;
    int attackers = 0;
    for (int i = 0; i < n; i++) attackers += g[i].state == 1;
    for (int i = 0; i < n; i++) {
        ed_ganado* e = &g[i];
        const ed_clip* cl = &d->clips[e->clip];
        /* the clip clock runs every tick (drawn pose continuity) */
        e->frame += 1.0f;
        if (e->frame >= cl->nf - 1) e->frame = (e->clip == 1) ? (float) (cl->nf - 1) : e->frame - (cl->nf - 1);
        e->since_logic++;
        if (logic_hz == 15 && ((tick + i) & 1)) continue;
        int dt = logic_hz == 15 ? 2 : 1;
        e->since_logic = 0;
        e->px = e->x; e->py = e->y; e->pz = e->z;
        e->pfx = e->fx; e->pfz = e->fz;
        float dx = lx - e->x, dz = lz - e->z;
        float d2 = dx * dx + dz * dz;
        float rd = shz_inv_sqrtf(d2 + 1e-3f);
        if (e->cooldown > 0) e->cooldown -= dt;
        if (e->state == 0) {
            if (d2 < 1400.0f * 1400.0f && attackers < 2 && e->cooldown <= 0) {
                e->state = 1; e->clip = 1; e->frame = 0; attackers++; e->attacks++;
            } else {
                float ux = dx * rd, uz = dz * rd;
                int c = cell_of(gr, e->x, e->z);
                if (c >= 0 && flow_stamp && flow_stamp[c] == flow_gen && flow_dir[c] != 0xFF && d2 > 2500.0f * 2500.0f) {
                    ux = UX[flow_dir[c]]; uz = UZ[flow_dir[c]];
                }
                float fx = e->fx + ux * 0.25f * dt, fz = e->fz + uz * 0.25f * dt;
                float r = shz_inv_sqrtf(fx * fx + fz * fz + 1e-6f);
                e->fx = fx * r; e->fz = fz * r;
                if (d2 > 1100.0f * 1100.0f) {
                    float step = d->clips[0].speed * dt;
                    e->x += e->fx * step; e->z += e->fz * step;
                }
            }
        } else if (e->state == 1) {
            e->fx = dx * rd; e->fz = dz * rd;
            float f = e->frame;
            if (f > cl->nf * 0.35f && f < cl->nf * 0.65f) {
                float head[3], hand[3];
                edemo_logic_bones(d, cl, f, head, hand);
                /* model -> world (yaw from facing) */
                float wx = e->x + hand[0] * e->fz + hand[2] * e->fx;
                float wz = e->z - hand[0] * e->fx + hand[2] * e->fz;
                float wy = e->y + hand[1];
                e->hand[0] = wx; e->hand[1] = wy; e->hand[2] = wz;
                e->head[0] = e->x + head[0] * e->fz + head[2] * e->fx;
                e->head[1] = e->y + head[1];
                e->head[2] = e->z - head[0] * e->fx + head[2] * e->fz;
                float hx = wx - lx, hy = wy - (ly + 1100.0f), hz = wz - lz;
                if (hx * hx + hy * hy + hz * hz < 700.0f * 700.0f) e->hits++;
            }
            if (e->frame >= cl->nf - 1) {
                e->state = 0; e->clip = 0; e->frame = 0; e->cooldown = 45;
            }
        }
        collide_walls(gr, e);
        int ok;
        float y = ed_floor_y(gr, e->x, e->z, &ok);
        if (ok) e->y = y;
        else { e->x = e->px; e->z = e->pz; }
    }
    /* body to body (and Leon) */
    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j <= n; j++) {
            float bx = (j == n) ? lx : g[j].x, bz = (j == n) ? lz : g[j].z;
            float dx = g[i].x - bx, dz = g[i].z - bz;
            float d2 = dx * dx + dz * dz;
            const float R = 650.0f;
            if (d2 < R * R && d2 > 1e-3f) {
                float r = shz_inv_sqrtf(d2);
                float push = (R - d2 * r) * (j == n ? 1.0f : 0.5f);
                g[i].x += dx * r * push; g[i].z += dz * r * push;
                if (j < n) { g[j].x -= dx * r * push; g[j].z -= dz * r * push; }
            }
        }
    }
}
