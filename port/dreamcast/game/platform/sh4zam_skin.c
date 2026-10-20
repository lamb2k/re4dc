/* sh4zam_skin.c: SKIN_SH4ZAM=1 (game30.mk; lane shzadopt20 2026-10-20; render only; default 0 = not built).
 *
 * Character skinning pass 1 (the skinned meshlet position pass of native_actor_fast.cpp avk_positions) through
 * SH4ZAM's shz_xmtrx_project_skinned_s16() / _u16() (third_party/sh4zam, MIT, Falco Girgis and SH4ZAM contributors).
 * Those routines are our avk_sh4.S pos_skin kernels contributed upstream (fork lamb2k/sh4zam, branch
 * shz-project-skinned; lane pin branch re4dc-pin-33fa485). AvkPos and shz_project_skinned_t have the same layout
 * (checked below), so the record batch is handed over as is.
 *
 * SKIN_SH4ZAM=2 (check build): every call also runs SH4ZAM's portable reference (_sw) into scratch and compares the
 * written words (relative) and the outcode bytes; "SKZCHK" log lines every 600 calls.
 */
#include <stdint.h>
#include <stddef.h>
#include <sh4zam/shz_xmtrx.h>

typedef struct {
    const uint8_t* rec; unsigned n; const uint8_t* pos; const uint8_t* uv;
    void* dst; uint8_t* oc; unsigned rs;
    const float* matrix; const uint8_t* ready; unsigned entries;
    float width, height, near_distance, far_distance, au, bu, av, bv;
} ShzAvkPos;  /* native_actor_fast.cpp AvkPos */

_Static_assert(offsetof(ShzAvkPos, rec) == offsetof(shz_project_skinned_t, records), "records");
_Static_assert(offsetof(ShzAvkPos, n) == offsetof(shz_project_skinned_t, count), "count");
_Static_assert(offsetof(ShzAvkPos, pos) == offsetof(shz_project_skinned_t, positions), "positions");
_Static_assert(offsetof(ShzAvkPos, uv) == offsetof(shz_project_skinned_t, uvs), "uvs");
_Static_assert(offsetof(ShzAvkPos, dst) == offsetof(shz_project_skinned_t, vertices), "vertices");
_Static_assert(offsetof(ShzAvkPos, oc) == offsetof(shz_project_skinned_t, outcodes), "outcodes");
_Static_assert(offsetof(ShzAvkPos, rs) == offsetof(shz_project_skinned_t, record_stride), "record_stride");
_Static_assert(offsetof(ShzAvkPos, matrix) == offsetof(shz_project_skinned_t, matrices), "matrices");
_Static_assert(offsetof(ShzAvkPos, ready) == offsetof(shz_project_skinned_t, matrix_ready), "matrix_ready");
_Static_assert(offsetof(ShzAvkPos, entries) == offsetof(shz_project_skinned_t, matrix_count), "matrix_count");
_Static_assert(offsetof(ShzAvkPos, width) == offsetof(shz_project_skinned_t, width), "width");
_Static_assert(offsetof(ShzAvkPos, near_distance) == offsetof(shz_project_skinned_t, near_z), "near_z");
_Static_assert(offsetof(ShzAvkPos, bv) == offsetof(shz_project_skinned_t, v_offset), "v_offset");
_Static_assert(sizeof(ShzAvkPos) == sizeof(shz_project_skinned_t), "size");

#if RE4DC_SKIN_SH4ZAM_CHECK
void re4dc_log(const char* fmt, ...);
unsigned int shz_xmtrx_project_skinned_s16_sw(const shz_project_skinned_t* batch);
unsigned int shz_xmtrx_project_skinned_u16_sw(const shz_project_skinned_t* batch);
static float chk_v[128 * 8] __attribute__((aligned(32)));
static uint8_t chk_oc[128];
static struct { unsigned calls, verts, words, bad, ocbad, stopbad; float maxrel; } chk;

static void check(const shz_project_skinned_t* b, unsigned left, int u16)
{
    if (b->count > 128u) return;
    shz_project_skinned_t r = *b;
    r.vertices = chk_v;
    r.outcodes = chk_oc;
    const unsigned rl = u16 ? shz_xmtrx_project_skinned_u16_sw(&r) : shz_xmtrx_project_skinned_s16_sw(&r);
    chk.calls++;
    if (rl != left) chk.stopbad++;
    const unsigned done = b->count - left;
    const float* g = (const float*) b->vertices;
    for (unsigned k = 0; k < done; k++) {
        for (unsigned w = 1; w <= 5; w++) {
            const float a = g[k * 8 + w], e = chk_v[k * 8 + w];
            const float d = a > e ? a - e : e - a, m = (e < 0 ? -e : e) > 1.0f ? (e < 0 ? -e : e) : 1.0f;
            const float rel = d / m;
            if (rel > chk.maxrel) chk.maxrel = rel;
            if (rel > 1e-4f) chk.bad++;
            chk.words++;
        }
        if ((b->outcodes[k] & 63u) != (chk_oc[k] & 63u)) chk.ocbad++;
    }
    chk.verts += done;
    if (!(chk.calls % 600u))
        re4dc_log("SKZCHK calls=%u verts=%u words=%u bad=%u maxrel_e9=%u ocbad=%u stopbad=%u\n", chk.calls, chk.verts,
                  chk.words, chk.bad, (unsigned) (chk.maxrel * 1e9f), chk.ocbad, chk.stopbad);
}
#endif

unsigned re4dc_shz_pos_skin_u16(const ShzAvkPos* a)
{
    const shz_project_skinned_t* b = (const shz_project_skinned_t*) a;
    const unsigned left = shz_xmtrx_project_skinned_u16(b);
#if RE4DC_SKIN_SH4ZAM_CHECK
    check(b, left, 1);
#endif
    return left;
}

unsigned re4dc_shz_pos_skin_s16(const ShzAvkPos* a)
{
    const shz_project_skinned_t* b = (const shz_project_skinned_t*) a;
    const unsigned left = shz_xmtrx_project_skinned_s16(b);
#if RE4DC_SKIN_SH4ZAM_CHECK
    check(b, left, 0);
#endif
    return left;
}
