/* Lane eng-draw5 (item 2, widened by H-038): skinned positions in C on SH4ZAM, the engine's way, as a SPEED LAB ARM (boot
   file /cd/SKC, read when the pack opens; never the default unless it measures better). Included by native_actor.inc.

   The same contract and the same arithmetic as the kernel (m1_avk_pos_skin_xy): per position (s16 xyz and its weight
   set, the part's stream already sorted by weight set at load), the weight set's projected matrix in XMTRX once per run
   (shz_xmtrx_load_4x4), FTRV (shz_xmtrx_transform_vec4), 1/w = FSRRA(w x w) (shz_inv_sqrtf_fsrra), x, y times 1/w; the
   entry's x, y, 1/w at +4, +8, +12 and the outcode byte (near far left right top bottom, MSB first: z < near, z > far,
   x < 0, x > width, y < 0, y > height; z = w in this matrix). No u, v, no records (the stream is read in place). A weight
   set not built stops the call (the records not done are returned), as the kernel. */
static int skc_arm;
static unsigned m1_skin_pos_c(const PositionPass* a)
{
    const SourceVector* v = a->positions; pvr_vertex_t* out = (pvr_vertex_t*) a->output; uint8_t* oc = a->outcode;
    const unsigned n = a->count, entries = a->entries; const uint8_t* ready = a->ready;
    const float W = a->width, H = a->height, N = a->near_plane, F = a->far_plane;
    unsigned cur = ~0u;
    for (unsigned i = 0; i < n; i++, v++, out++) {
        const unsigned b = v->bone;
        if (b != cur) {
            const unsigned e = b < entries ? b : 0;
            if (!ready[e]) return n - i;
            shz_xmtrx_load_4x4((const shz_mat4x4_t*) (a->matrices + 16 * e)); cur = b;
        }
        const shz_vec4_t r = shz_xmtrx_transform_vec4(shz_vec4_init((float) v->xyz[0], (float) v->xyz[1], (float) v->xyz[2], 1.f));
        const float rw = shz_inv_sqrtf_fsrra(r.w * r.w), x = r.x * rw, y = r.y * rw;
        out->x = x; out->y = y; out->z = rw;
        oc[i] = (uint8_t) ((N > r.z) << 5 | (r.z > F) << 4 | (0.f > x) << 3 | (x > W) << 2 | (0.f > y) << 1 | (y > H));
    }
    return 0;
}
