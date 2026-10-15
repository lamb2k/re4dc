/* sh4zam_skin.c: SKIN_SH4ZAM=1 (game30.mk; lane sh4zam-direct 2026-10-15; render only; default 0 = not built).
 *
 * The actor skinning chain on the SH4ZAM API (kos-ports sh4zam, MIT, Copyright (c) 2025, 2026 Falco Girgis and
 * SH4ZAM Contributors; pin 0fd3a1e1 v0.9.0), as the user asked ("adopt SH4ZAM, call its API directly") after an SH4ZAM
 * author's review of our skinning loop ("shz_xmtrx_init_zero(); shz_xmtrx_blend(); ... Can all be done within XMTRX
 * registers using the XMTRX API" and "load it into XMTRX ONCE then just call shz_xmtrx_transform_vecN()").
 *
 * One image carries both paths; a run-time mask picks each stage (re4dc_skin_sh4zam_set; boot value
 * SKIN_SH4ZAM_BOOT, a data word only, so on / off arms share one code layout):
 *   0x01 bones + palette groups (replaces coarse_skin_sh4.S): per bone T = inv x P x B with XMTRX = inv, P's columns
 *        through shz_xmtrx_transform_vec4, then XMTRX = inv x P (shz_xmtrx_load_cols_4x4) and B's columns through it;
 *        per palette entry XMTRX = 0 (shz_xmtrx_init_zero) + shz_xmtrx_blend per (bone, weight), read back by columns.
 *   0x02 skin table (replaces native_actor_fast.cpp avk_build_all's asm): XMTRX = the screen matrix once, each entry's
 *        columns (x q) through shz_xmtrx_transform_vec4, each 64-byte entry's two lines taken by shz_dcache_alloc_line.
 *   0x04 probe light directions (replaces probe_dirs_all's scalar dots): XMTRX rows = the fold's directions once, each
 *        palette column through shz_xmtrx_transform_vec4 (one FTRV gives the column's dot with every direction).
 *   0x08 skinned position pass as C on SH4ZAM calls (comparator for avk_sh4.S re4dc_avk_pos_skin_u16): per palette
 *        run shz_xmtrx_load_4x4 of the skin table entry, per vertex shz_xmtrx_transform_vec4 + shz_inv_sqrtf.
 *   0x10 (with 0x08) the run's matrix is built in XMTRX, never stored: shz_xmtrx_load_4x4(screen) +
 *        shz_xmtrx_apply_3x4(palette entry) + shz_xmtrx_apply_scale(q) (no skin table at all).
 *   0x20 the GameCube-path weight palette (trans.cpp MakeWeightPalette): shz_xmtrx_init_zero + shz_xmtrx_blend.
 *   0x40 skinned meshlet cache lines allocated with shz_dcache_alloc_line before pass 1 (the SKIN_MOVCA lever: no
 *        RAM fill for write-only vertex lines; flags / oargb rewritten as prime() wrote them).
 * Results are render only (palettes and vertices never reach game logic). Not bit-exact where FTRV / blend's FMAC
 * replace scalar sums (0x01, 0x04, 0x10, 0x20); 0x02 / 0x08 / 0x40 do the asm's operations.
 *
 * ABI: -m4-single -ml, FPSCR PR=0 SZ=0 on entry and exit (SH4ZAM's inline asm pairs its fschg / frchg). Every routine
 * here CLOBBERS XMTRX and calls nothing in game code while it owns it (lane doc "XMTRX ownership rules").
 */
#include <stdint.h>
#include <stddef.h>
#include <sh4zam/shz_xmtrx.h>
#include <sh4zam/shz_vector.h>
#include <sh4zam/shz_scalar.h>
#include <sh4zam/shz_mem.h>

/* The vendored headers forward-declare shz_mat4x4_t / shz_mat3x4_t (shz_matrix.h is not vendored), so an SH4ZAM asm
 * "m" operand of those types does not tell GCC which bytes it reads or writes: a compiler barrier orders the local
 * matrices handed to those calls (stores before a read, a store before the C reads it back). */
#define SHZ_SKIN_BARRIER() __asm__ __volatile__("" ::: "memory")

#ifndef RE4DC_SKIN_SH4ZAM_BOOT
#define RE4DC_SKIN_SH4ZAM_BOOT 0
#endif
/* Always .data (a zero boot value would otherwise go to .bss and move the layout between arms). */
__attribute__((section(".data"))) unsigned re4dc_skin_sh4zam_mask = RE4DC_SKIN_SH4ZAM_BOOT;

void re4dc_skin_sh4zam_set(unsigned mask)
{
    re4dc_skin_sh4zam_mask = mask;
}

/* POC101's SKIN_MOVCA layer row (bench.cpp re4dc_skin_movca_set): this lane's bit 0x40. */
void re4dc_skin_movca_set(unsigned on)
{
    re4dc_skin_sh4zam_mask = on ? (re4dc_skin_sh4zam_mask | 0x40u) : (re4dc_skin_sh4zam_mask & ~0x40u);
}

typedef struct { const float* P; const float* B; float* T; } ShzBoneJob;  /* coarse_skin.h CoarseBoneJob */
typedef struct { short offset[3]; unsigned short count, n, pad[3]; } ShzGroupHeader;
typedef struct { float w[4]; unsigned out, pad; } ShzGroupEntry;
_Static_assert(sizeof(ShzGroupHeader) == 16 && sizeof(ShzGroupEntry) == 24, "coarse palette groups");

void re4dc_coarse_skin_bones(const float* inv, const ShzBoneJob* jobs, unsigned n);                  /* asm */
void re4dc_coarse_skin_groups(const void* stream, unsigned groups, const float* T, float* out, unsigned entries);

#ifndef RE4DC_SKIN_SH4ZAM_CHECK
#define RE4DC_SKIN_SH4ZAM_CHECK 0
#endif
#if RE4DC_SKIN_SH4ZAM_CHECK
/* SKIN_SH4ZAM=2 (check build, Flycast): each SH4ZAM stage that runs is compared with the previous path's result for
 * the same input ("SKZCHK" lines every 600 stage calls): words that differ, and the largest absolute difference
 * relative to the largest output magnitude (rel). Exact stages (0x02 table, 0x08 positions) must show words=0. */
void re4dc_log(const char* fmt, ...);
static struct { unsigned calls, words, diff; float rel; } chk[8];
static const char* const kChkName[8] = {"bones", "groups", "table", "dirs", "pos", "posfuse", "wpal", "-"};
static unsigned chk_total;
static float chk_rel(const float* a, const float* b, unsigned n, unsigned* words)
{
    float mx = 0.0f, md = 0.0f;
    unsigned w = 0;
    for (unsigned i = 0; i < n; i++) {
        union { float f; uint32_t u; } x = {a[i]}, y = {b[i]};
        if (x.u != y.u) w++;
        float d = a[i] - b[i];
        if (d < 0) d = -d;
        float m = b[i] < 0 ? -b[i] : b[i];
        if (d > md) md = d;
        if (m > mx) mx = m;
    }
    *words += w;
    return mx > 0.0f ? md / mx : md;
}
static void chk_note(int k, const float* got, const float* ref, unsigned n)
{
    unsigned w = 0;
    float r = chk_rel(got, ref, n, &w);
    chk[k].calls++;
    chk[k].words += w;
    chk[k].diff += w != 0;
    if (r > chk[k].rel) chk[k].rel = r;
    if (++chk_total % 600u == 0) {
        for (int i = 0; i < 7; i++)
            if (chk[i].calls)
                re4dc_log("SKZCHK %s calls=%u calls_diff=%u words=%u max_rel=%.3e\n", kChkName[i], chk[i].calls,
                          chk[i].diff, chk[i].words, (double) chk[i].rel);
        if (chk[7].calls) re4dc_log("SKZCHK outcode meshlets=%u bytes_diff=%u\n", chk[7].calls, chk[7].words);
    }
}
static float chk_buf[256 * 16] __attribute__((aligned(32)));
unsigned re4dc_avk_pos_skin_u16(const void* a);  /* avk_sh4.S */
#endif

/* 0x01: T = inv x P x B (P, B row-major 3x4; T four columns of three floats: the palette layout). */
void re4dc_shz_skin_bones(const float* inv, const ShzBoneJob* jobs, unsigned n)
{
    if (!(re4dc_skin_sh4zam_mask & 0x01u)) {
        re4dc_coarse_skin_bones(inv, jobs, n);
        return;
    }
#if RE4DC_SKIN_SH4ZAM_CHECK
    const ShzBoneJob* const j0 = jobs;
    const unsigned n0 = n <= 256u ? n : 256u;
    re4dc_coarse_skin_bones(inv, jobs, n0);
    for (unsigned k = 0; k < n0; k++)
        for (int e = 0; e < 12; e++) chk_buf[k * 12 + e] = jobs[k].T[e];
#endif
    for (; n; --n, ++jobs) {
        const float* P = jobs->P;
        const float* B = jobs->B;
        float* T = jobs->T;
        shz_xmtrx_load_4x4((const shz_mat4x4_t*) inv);
        shz_vec4_t a0 = shz_xmtrx_transform_vec4(shz_vec4_init(P[0], P[4], P[8], 0.0f));
        shz_vec4_t a1 = shz_xmtrx_transform_vec4(shz_vec4_init(P[1], P[5], P[9], 0.0f));
        shz_vec4_t a2 = shz_xmtrx_transform_vec4(shz_vec4_init(P[2], P[6], P[10], 0.0f));
        shz_vec4_t a3 = shz_xmtrx_transform_vec4(shz_vec4_init(P[3], P[7], P[11], 1.0f));
        shz_xmtrx_load_cols_4x4(&a0, &a1, &a2, &a3);
        for (int c = 0; c < 4; c++) {
            shz_vec4_t t = shz_xmtrx_transform_vec4(shz_vec4_init(B[c], B[4 + c], B[8 + c], c == 3 ? 1.0f : 0.0f));
            T[c * 3 + 0] = t.x;
            T[c * 3 + 1] = t.y;
            T[c * 3 + 2] = t.z;
        }
    }
#if RE4DC_SKIN_SH4ZAM_CHECK
    for (unsigned k = 0; k < n0; k++) chk_note(0, j0[k].T, chk_buf + k * 12, 12);
#endif
}

/* Blended entry: XMTRX = sum of w_k x T_bone_k. shz_xmtrx_blend reads 16 floats (a 4x4) from a 48-byte T: elements
 * 12..15 come from the next bone's words (readable: the T tables are static arrays followed by more data) and are
 * never stored; elements 0..11 are the entry, read back as XMTRX columns 0..2 (column-major: 4 floats each). */
static inline void shz_entry_store(float* o)
{
    float t[16] __attribute__((aligned(8)));
    shz_xmtrx_store_4x4((shz_mat4x4_t*) t);
    SHZ_SKIN_BARRIER();  /* the struct types are forward-declared here: tell GCC t was written */
    for (int k = 0; k < 12; k++) o[k] = t[k];
}

/* 0x01: the palette entries of one chunk from the group stream (coarse_skin.h coarse_group_build). out is 32-byte
 * aligned with room to the next 32-byte boundary (the asm's contract): its lines are allocated first, then written. */
void re4dc_shz_skin_groups(const void* stream, unsigned groups, const float* T, float* out, unsigned entries)
{
    if (!(re4dc_skin_sh4zam_mask & 0x01u)) {
        re4dc_coarse_skin_groups(stream, groups, T, out, entries);
        return;
    }
#if RE4DC_SKIN_SH4ZAM_CHECK
    const unsigned ce = entries <= 256u ? entries : 0u;
    if (ce) {
        re4dc_coarse_skin_groups(stream, groups, T, out, entries);
        for (unsigned k = 0; k < ce * 12u; k++) chk_buf[k] = out[k];
    }
#endif
    if (!((uintptr_t) out & 31u)) {
        uint8_t* line = (uint8_t*) out;
        for (unsigned k = (entries * 48u + 31u) >> 5; k; --k, line += 32)
            shz_dcache_alloc_line(line);
    }
    const uint8_t* s = (const uint8_t*) stream;
    for (; groups; --groups) {
        const ShzGroupHeader* h = (const ShzGroupHeader*) s;
        s += sizeof(*h);
        const unsigned c = h->count;
        const float* t0 = (const float*) ((const uint8_t*) T + h->offset[0]);
        const float* t1 = (const float*) ((const uint8_t*) T + h->offset[1]);
        const float* t2 = (const float*) ((const uint8_t*) T + h->offset[2]);
        for (unsigned i = h->n; i; --i, s += sizeof(ShzGroupEntry)) {
            const ShzGroupEntry* e = (const ShzGroupEntry*) s;
            float* o = (float*) ((uint8_t*) out + e->out);
            if (c == 1) {  /* weight 1.0 (coarse_group_build): the bone's T itself */
                for (int k = 0; k < 12; k++) o[k] = t0[k];
                continue;
            }
            shz_xmtrx_init_zero();
            shz_xmtrx_blend((const shz_mat4x4_t*) t0, e->w[0]);
            shz_xmtrx_blend((const shz_mat4x4_t*) t1, e->w[1]);
            if (c > 2) shz_xmtrx_blend((const shz_mat4x4_t*) t2, e->w[2]);
            shz_entry_store(o);
        }
    }
#if RE4DC_SKIN_SH4ZAM_CHECK
    if (ce) chk_note(1, out, chk_buf, ce * 12u);
#endif
}

/* 0x02: skin table entries screen x [R_i q | t_i] (16 floats, column-major), the operations of avk_build_all's asm
 * (columns 0-2 x q with w 0, the translation with w 1, each through FTRV). out 8-byte aligned; when 32-byte aligned
 * each entry's two lines are allocated (every word is stored). */
void re4dc_shz_skin_table(const float* screen, const float* P, unsigned entries, float q, float* out)
{
    const int lines = !((uintptr_t) out & 31u);
    shz_xmtrx_load_4x4((const shz_mat4x4_t*) screen);
    for (; entries; --entries, P += 12, out += 16) {
        if (lines) {
            shz_dcache_alloc_line(out);
            shz_dcache_alloc_line(out + 8);
        }
        shz_vec4_t c0 = shz_xmtrx_transform_vec4(shz_vec4_init(P[0] * q, P[1] * q, P[2] * q, 0.0f));
        shz_vec4_t c1 = shz_xmtrx_transform_vec4(shz_vec4_init(P[3] * q, P[4] * q, P[5] * q, 0.0f));
        shz_vec4_t c2 = shz_xmtrx_transform_vec4(shz_vec4_init(P[6] * q, P[7] * q, P[8] * q, 0.0f));
        shz_vec4_t c3 = shz_xmtrx_transform_vec4(shz_vec4_init(P[9], P[10], P[11], 1.0f));
        out[0] = c0.x; out[1] = c0.y; out[2] = c0.z; out[3] = c0.w;
        out[4] = c1.x; out[5] = c1.y; out[6] = c1.z; out[7] = c1.w;
        out[8] = c2.x; out[9] = c2.y; out[10] = c2.z; out[11] = c2.w;
        out[12] = c3.x; out[13] = c3.y; out[14] = c3.z; out[15] = c3.w;
#if RE4DC_SKIN_SH4ZAM_CHECK
        {  /* scalar reference (skin_position_matrix's mul4 form): rel only, FTRV rounds differently */
            float ref[16];
            for (int c = 0; c < 4; c++) {
                const float v0 = c < 3 ? P[c * 3] * q : P[9], v1 = c < 3 ? P[c * 3 + 1] * q : P[10];
                const float v2 = c < 3 ? P[c * 3 + 2] * q : P[11], v3 = c < 3 ? 0.0f : 1.0f;
                for (int r = 0; r < 4; r++)
                    ref[c * 4 + r] = screen[r] * v0 + screen[4 + r] * v1 + screen[8 + r] * v2 + screen[12 + r] * v3;
            }
            chk_note(2, out, ref, 16);
        }
#endif
    }
}

/* 0x04: probe light directions of every palette entry: out[c] = col_c(R_i) . l, out[4 + c] = col_c(R_i) . m (m: the
 * LEON_LIGHT_FILL camera fill, or none), the rest 0. XMTRX rows = l, m, 0, 0: one FTRV per column gives both dots. */
void re4dc_shz_probe_dirs(const float* P, unsigned entries, const float* l, const float* m, float* out)
{
    const shz_vec4_t r0 = shz_vec4_init(l[0], l[1], l[2], 0.0f);
    const shz_vec4_t r1 = m ? shz_vec4_init(m[0], m[1], m[2], 0.0f) : shz_vec4_init(0.0f, 0.0f, 0.0f, 0.0f);
    const shz_vec4_t r2 = shz_vec4_init(0.0f, 0.0f, 0.0f, 0.0f);
    shz_xmtrx_load_rows_4x4(&r0, &r1, &r2, &r2);
    for (; entries; --entries, P += 12, out += 12) {
        shz_vec4_t d0 = shz_xmtrx_transform_vec4(shz_vec4_init(P[0], P[1], P[2], 0.0f));
        shz_vec4_t d1 = shz_xmtrx_transform_vec4(shz_vec4_init(P[3], P[4], P[5], 0.0f));
        shz_vec4_t d2 = shz_xmtrx_transform_vec4(shz_vec4_init(P[6], P[7], P[8], 0.0f));
        out[0] = d0.x; out[1] = d1.x; out[2] = d2.x; out[3] = 0.0f;
        out[4] = d0.y; out[5] = d1.y; out[6] = d2.y; out[7] = 0.0f;
        out[8] = 0.0f; out[9] = 0.0f; out[10] = 0.0f; out[11] = 0.0f;
#if RE4DC_SKIN_SH4ZAM_CHECK
        {  /* probe_dirs_all's scalar dots */
            float ref[12] = {0};
            for (int c = 0; c < 3; c++) {
                ref[c] = P[c * 3] * l[0] + P[c * 3 + 1] * l[1] + P[c * 3 + 2] * l[2];
                if (m) ref[4 + c] = P[c * 3] * m[0] + P[c * 3 + 1] * m[1] + P[c * 3 + 2] * m[2];
            }
            chk_note(3, out, ref, 12);
        }
#endif
    }
}

/* 0x08 / 0x10: pass 1 of a skinned meshlet with u16 uv, as re4dc_avk_pos_skin_u16 computes it (positions_c's
 * operations: FTRV, 1/|w| = FSRRA(w w), x / y scaled, z = 1/|w|, u / v = t a + b, one outcode byte with the AVK bit
 * order). Records: u16 vi, ni, ti (sign-extended, as the kernel's mov.w); positions stride 8 (s16 x y z, palette).
 * fuse = 0: XMTRX per palette run from the skin table (matrix, 16 floats an entry); fuse = 1: built in XMTRX from
 * the screen matrix and the palette entry, no table. Returns the records done (all of them). */
typedef struct {
    const uint8_t* rec; unsigned n; const uint8_t* pos; const uint8_t* uv;
    void* dst; uint8_t* oc; unsigned rs;
    const float* matrix; const uint8_t* ready; unsigned entries;
    float width, height, near_distance, far_distance, au, bu, av, bv;
} ShzPos;  /* native_actor_fast.cpp AvkPos */
enum { kShzOcBottom = 1, kShzOcTop = 2, kShzOcRight = 4, kShzOcLeft = 8, kShzOcFar = 16, kShzOcNear = 32 };

unsigned re4dc_shz_pos_skin_u16(const ShzPos* a, const float* screen, const float* palette, float q)
{
    const uint8_t* rec = a->rec;
    const unsigned rs = a->rs, entries = a->entries;
    const uint8_t* pos = a->pos;
    const uint8_t* uv = a->uv;
    float* d = (float*) a->dst;
    uint8_t* oc = a->oc;
    const float W = a->width, H = a->height, N = a->near_distance, F = a->far_distance;
    const float au = a->au, bu = a->bu, av = a->av, bv = a->bv;
    unsigned cur = ~0u;
    unsigned i;
    for (i = 0; i < a->n; ++i, rec += rs, d += 8) {
        const int16_t* r = (const int16_t*) rec;
        const int16_t* s = (const int16_t*) (pos + (int) r[0] * 8);
        unsigned pi = (unsigned) (int) s[3];
        if (pi >= entries) pi = 0;
        if (pi != cur) {
            cur = pi;
            if (screen) {
                /* XMTRX = screen x [R q | t]. The dequantisation q goes into the entry's columns 0-2 first:
                 * shz_xmtrx_apply_scale scales rows 0-2 only (it assumes an affine bottom row), and the screen
                 * matrix's row 3 is W, which must scale too. */
                const float* P = palette + pi * 12;
                float pq[12];
                for (int k = 0; k < 9; k++) pq[k] = P[k] * q;
                pq[9] = P[9]; pq[10] = P[10]; pq[11] = P[11];
                shz_xmtrx_load_4x4((const shz_mat4x4_t*) screen);
                SHZ_SKIN_BARRIER();  /* pq stored before the asm reads it (forward-declared struct operand) */
                shz_xmtrx_apply_3x4((const shz_mat3x4_t*) pq);
            } else {
                shz_xmtrx_load_4x4((const shz_mat4x4_t*) (a->matrix + pi * 16));
            }
        }
        const uint16_t* t = (const uint16_t*) (uv + (int) r[2] * 4);
        const float tu = (float) t[0], tv = (float) t[1];
        shz_vec4_t v = shz_xmtrx_transform_vec4(shz_vec4_init((float) s[0], (float) s[1], (float) s[2], 1.0f));
        const float w = v.w;
        const float inv = shz_inv_sqrtf(w * w);
        const float x = v.x * inv, y = v.y * inv;
        unsigned code = 0;
        if (N > w) code |= kShzOcNear;
        if (w > F) code |= kShzOcFar;
        if (0.0f > x) code |= kShzOcLeft;
        if (x > W) code |= kShzOcRight;
        if (0.0f > y) code |= kShzOcTop;
        if (y > H) code |= kShzOcBottom;
        d[1] = x;
        d[2] = y;
        d[3] = inv;
        d[4] = tu * au + bu;
        d[5] = tv * av + bv;
        oc[i] = (uint8_t) code;
    }
#if RE4DC_SKIN_SH4ZAM_CHECK
    /* the asm kernel over the same records (the caller built the skin table) into scratch: x y z u v + outcode */
    if (a->n && a->n <= 128u) {
        static uint8_t chk_oc[128] __attribute__((aligned(32)));
        ShzPos b = *a;
        b.dst = chk_buf;
        b.oc = chk_oc;
        re4dc_avk_pos_skin_u16(&b);
        const float* g = (const float*) a->dst;
        float got[5 * 128], ref[5 * 128];
        unsigned ocbad = 0;
        for (unsigned k = 0; k < a->n; k++) {
            for (int e = 0; e < 5; e++) {
                got[k * 5 + e] = g[k * 8 + 1 + e];
                ref[k * 5 + e] = chk_buf[k * 8 + 1 + e];
            }
            ocbad += (a->oc[k] & 63u) != (chk_oc[k] & 63u);
        }
        chk_note(screen ? 5 : 4, got, ref, a->n * 5u);
        chk[7].words += ocbad;
        chk[7].calls++;
    }
#endif
    return i;
}

/* 0x40: the meshlet's n vertex lines (32 bytes each, 32-byte aligned P1 RAM) allocated without a RAM fill; the two
 * words prime() writes (flags = PVR_CMD_VERTEX, oargb = 0) are written again; passes 1 and 2 write the rest. */
void re4dc_shz_cache_lines(void* v, unsigned n, uint32_t flags)
{
    uint32_t* w = (uint32_t*) v;
    for (; n; --n, w += 8) {
        shz_dcache_alloc_line(w);
        w[0] = flags;
        w[7] = 0;
    }
}

/* 0x20: trans.cpp MakeWeightPalette entries (Weight: u8 id[3], num, u8 wht[4]; mtx 48-byte 3x4 parts matrices;
 * dst 48 bytes an entry, stored transposed as PSMTXReorder does). rate = wht * 0.01, the last 1 - total (the same
 * rates as the C loop); the blend runs in XMTRX (init_zero + blend: elements 0..11 = the row-major sum), then the
 * entry is stored transposed from XMTRX's columns. Returns the weight count. */
typedef struct { uint8_t id[3], num, wht[4]; } ShzWeight;
int re4dc_shz_weight_palette(const ShzWeight* w, int n, const float* mtx, float* dst)
{
    int cnt = 0;
    for (; n > 0; --n, ++w, dst += 12) {
        float total = 0.0f;
        shz_xmtrx_init_zero();
        for (int j = 0; j < w->num; j++) {
            float rate = (float) w->wht[j] * 0.01f;
            if (j == w->num - 1) rate = 1.0f - total;
            total += rate;
            shz_xmtrx_blend((const shz_mat4x4_t*) (mtx + w->id[j] * 12), rate);
        }
        cnt += w->num;
        float t[16] __attribute__((aligned(8)));  /* t[4 r + c] = row r, column c of the summed Mtx */
        shz_xmtrx_store_4x4((shz_mat4x4_t*) t);
        SHZ_SKIN_BARRIER();  /* the struct types are forward-declared here: tell GCC t was written */
        for (int c = 0; c < 4; c++) {
            dst[c * 3 + 0] = t[c];
            dst[c * 3 + 1] = t[4 + c];
            dst[c * 3 + 2] = t[8 + c];
        }
    }
    return cnt;
}
