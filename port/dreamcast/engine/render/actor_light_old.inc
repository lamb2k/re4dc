/* Lane eng-draw5 (item 4): LOLD, the released game's character lighting as a LOOK ARM (boot file /cd/LOLD, read when the
   pack opens; off by default; never the engine's lighting unless the owner picks it from the sheet). Included by
   native_actor.inc after source_light.inc.

   What the released game (Test 27.2, platform/native_actor_fast.cpp build_lights / skin_light_dirs and the kernel
   re4dc_avk_light_skin_n16) does differently from the engine's rule (source_light.inc):
     - at most 3 lights a character (the strongest at the character: LCAP's pick);
     - each light's direction and distance terms evaluated once a character, at the object position (bone 1), not
       once a weight set at the set's origin; the directions are then turned into each weight set's space;
     - the sum through FTRV: colour = C x (m0, m1, m2, 1) with m = d + |d| and C's columns the lights' colours x 1/2 x
       the material scale and the ambient x the material scale; truncated, then clamped at 255 AFTER the material
       scale (the engine: k x min(1, sum), the clamp before the scale).
   The kernel is the released one generated again by its own tool (render/avk_xy_sh4.inc, m1_avk_light_skin_n16w: only
   its colour store stride changed, to the engine's colour array); it reads the engine's normals in place (s16, the
   weight set in the fourth word) through the position records' normal word. One variable: the look; the arm also
   lights a boundary part's whole normal range (the kernel writes colours in order), a small extra cost charged to it. */
typedef struct {
    const void* rec; unsigned n; const SourceVector* nrm; uint32_t* argb;
    unsigned rs; const float* color; const float* dirs; const uint8_t* ready; unsigned entries; uint32_t alpha;
} OldLightPass;
_Static_assert(sizeof(OldLightPass) == 40, "avk light ABI");
extern unsigned m1_avk_light_skin_n16w(const OldLightPass*);
static int lold_arm;
static float lold_color[16] __attribute__((aligned(8)));
static float lold_world[3][3];                 /* the character's light directions, world space (zero when unused) */
static float lold_dirs[ACTOR_WS_LIMIT][12] __attribute__((aligned(8)));
static unsigned lold_lights_n, lold_calls;

/* Per character, after source_lights_w (cur_lights holds at most 3 lights under the arm: src_light_cap = 3). o: the
   object position (bone 1's matrix, row-major 3x4). */
static void lold_character(const float* obj)
{
    const float o[3] = {obj[3], obj[7], obj[11]};
    for (unsigned k = 0; k < 16; k++) lold_color[k] = 0;
    for (unsigned j = 0; j < 3; j++) lold_world[j][0] = lold_world[j][1] = lold_world[j][2] = 0;
    const unsigned n = cur_lights.n < 3 ? cur_lights.n : 3;
    for (unsigned j = 0; j < n; j++) {
        const SrcLight* g = cur_lights.l + j;
        float L[3] = {g->pos[0] - o[0], g->pos[1] - o[1], g->pos[2] - o[2]}, d = sqrtf(L[0] * L[0] + L[1] * L[1] + L[2] * L[2]);
        const float id = d > 0 ? 1.f / d : 0; for (unsigned c = 0; c < 3; c++) L[c] *= id;
        float att = g->br;
        if (g->spot) { float cs = -(L[0] * g->axis[0] + L[1] * g->axis[1] + L[2] * g->axis[2]); att *= m1_maxf(0, g->sa0 + g->sa1 * cs); }
        att /= g->k0 + g->k1 * d + g->k2 * d * d;
        for (unsigned c = 0; c < 3; c++) { lold_world[j][c] = L[c]; lold_color[4 * j + c] = .5f * g->rgb[c] * att * cur_lights.k[c]; }
    }
    for (unsigned c = 0; c < 3; c++) lold_color[12 + c] = cur_lights.amb[c] * cur_lights.k[c];
    lold_lights_n += n; lold_calls++;
}
/* Per weight set (build_ws_once): the character's directions in the set's space, scaled for s16 normals (ws_light's
   transform); w slots 0 (the kernel's normal w is 0). */
static void lold_ws(unsigned i, const float* m)
{
    const float inv = 1.f / (16384.f * .0625f);
    float* d = lold_dirs[i];
    for (unsigned j = 0; j < 3; j++) {
        const float* L = lold_world[j];
        d[4 * j + 0] = (m[0] * L[0] + m[4] * L[1] + m[8] * L[2]) * inv;
        d[4 * j + 1] = (m[1] * L[0] + m[5] * L[1] + m[9] * L[2]) * inv;
        d[4 * j + 2] = (m[2] * L[0] + m[6] * L[1] + m[10] * L[2]) * inv;
        if (j < 2) d[4 * j + 3] = 0;
    }
}
/* A part's normals [first, first + count) into out[first..]; records: pos_records (the normal index in word 1). A weight
   set the visible parts did not build (the kernel stops before its first normal) is built and the kernel resumes. */
static void build_ws(const RtModel* m, unsigned i);
static void lold_light_range(const RtModel* m, unsigned first, unsigned count, uint32_t* out)
{
    DC_ADD(DC_A_NRM, count); DC_ADD(DC_A_NRMLIGHTS, count * 3);
    unsigned done = 0;
    for (unsigned guard = 0; done < count && guard < 64; guard++) {
        OldLightPass a = {pos_records[done], count - done, m->nrm + first, out + first + done, 8, lold_color, &lold_dirs[0][0],
                          ws_ready, m->h[1], 0xff000000u};
        a.nrm = m->nrm + first;   /* records hold indices from 0: the normals' base stays the part's first */
        done = count - m1_avk_light_skin_n16w(&a);
        if (done < count) { const unsigned w = m->nrm[first + done].bone; if (w >= m->h[1] || ws_ready[w]) break; build_ws(m, w); }
    }
}
