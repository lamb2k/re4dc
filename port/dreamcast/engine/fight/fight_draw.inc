/* E2 fight picture (lane eng-e2), included at the end of services/render_e1.c in the FIGHT=1 image: the Ganados from the
   engine actor table and the native effect service's sprites, drawn by the E0 renderer's passes. Nothing is converted
   per picture: the Ganados go through the E1 actor pass (bone matrices read in place from the actor table, the
   character level picked from their on-screen size: the owner's default, step 3), the sprites are projected straight
   from the effect arrays (fx_sprites) with the material header of their texture picture (FXMAP.BIN, from the pack's
   recorded sprites), density cap as the owner's default (step 2: the 64 largest). */
#include "fx.h"
unsigned e2_actor_list(const void** models, unsigned* bases, unsigned* idents, unsigned max);   /* fight_trace.cpp */

/* ---- the effect map: (texture id, pattern) -> material header, glow header ---- */
typedef struct { uint16_t tex, ptn; uint32_t hdr, glow; } FxMapRow;
static FxMapRow* fxmap;
static unsigned fxmap_n;
static uint16_t fxmap_first[257];   /* first row of each texture id (rows sorted by texture, pattern) */
volatile uint32_t e2_fx_counts[4];  /* sprites this picture: live, drawable (header known), on screen, after the cap */
void e2_draw_open(void)
{
    file_t f = fs_open("/cd/FXMAP.BIN", O_RDONLY);
    if (f < 0) { printf("E2 draw: no FXMAP.BIN (native sprites not drawn)\n"); return; }
    uint32_t n = 0;
    fs_read(f, &n, 4);
    fxmap = (FxMapRow*) malloc(n * sizeof(FxMapRow) + 4);
    if (fxmap && fs_read(f, fxmap, n * sizeof(FxMapRow)) == (ssize_t) (n * sizeof(FxMapRow))) fxmap_n = n;
    fs_close(f);
    unsigned r = 0;
    for (unsigned t = 0; t <= 256; t++) { while (r < fxmap_n && fxmap[r].tex < t) r++; fxmap_first[t] = r; }
    printf("E2 draw: effect map %u sprite pictures\n", fxmap_n);
}
static const FxMapRow* fx_lookup(unsigned tex, unsigned ptn)
{
    if (tex > 255) return NULL;
    const FxMapRow* best = NULL;
    for (unsigned i = fxmap_first[tex]; i < fxmap_first[tex + 1]; i++) {
        if (fxmap[i].ptn == ptn) return fxmap + i;
        if (!best) best = fxmap + i;   /* a pattern the capture never showed: the texture's first */
    }
    return best;
}

/* ---- Ganados ---- */
void e2_draw_actors(NativeScene* s)
{
    const void* m[8]; unsigned base[8], ident[8];
    const unsigned n = e2_actor_list(m, base, ident, 8);
    for (unsigned i = 0; i < n; i++) {
        const unsigned bones = e1_gather((const uint8_t*) m[i]);
        float lo[3] = {1e30f, 1e30f, 1e30f}, hi[3] = {-1e30f, -1e30f, -1e30f};
        for (unsigned b = 0; b <= bones; b++)
            for (unsigned k = 0; k < 3; k++) {
                const float v = e1_bone[b][3 + 4 * k];
                if (v - 300.f < lo[k]) lo[k] = v - 300.f;
                if (v + 300.f > hi[k]) hi[k] = v + 300.f;
            }
        const unsigned model = content_pick(s, base[i], lo, hi, 1 + i);
        e1_actor_pass(s, m[i], model, ident[i], 0);
    }
}

/* ---- the native effect sprites ---- */
void e2_draw_effects(NativeScene* s)
{
    const float* c = (const float*) s->state[0];
    shz_mat4x4_t screen = projection_grid(c, identity_grid); shz_xmtrx_load_4x4(&screen);
    const float near = c[18] / (c[17] - 1);
    unsigned count = 0, known = 0;
    const struct FxSprites* S = &fx_sprites;
    for (unsigned i = 0; i < S->n; i++) {
        const FxMapRow* r = fxmap_n ? fx_lookup(S->tex[i], S->ptn[i]) : NULL;
        if (!r || !(S->ca[i] > 0)) continue;
        known++;
        float w[3] = {S->px[i], S->py[i], S->pz[i]};
        const float* a = S->parent[i];
        if (a) { float p[3] = {w[0], w[1], w[2]};
            for (unsigned k = 0; k < 3; k++, a += 4) w[k] = a[0] * p[0] + a[1] * p[1] + a[2] * p[2] + a[3]; }
        shz_vec4_t q = shz_xmtrx_transform_vec4(shz_vec4_init(w[0], w[1], w[2], 1));
        if (q.w < near || q.w > c[25]) continue;
        const float iw = 1.f / q.w, x = q.x * iw, y = q.y * iw;
        const float rx = fabsf(160 * c[13] * S->sbx[i] * S->smul[i] * iw), ry = fabsf(120 * c[15] * S->sby[i] * S->smul[i] * iw);
        if (x + rx < 0 || y + ry < 0 || x - rx > 640 || y - ry > 480 || count == 1024) continue;
        float col[4] = {S->cr[i], S->cg[i], S->cb[i], S->ca[i]};
        if (!(S->tool[i] & 0x40)) {   /* the source's TEV scale (content_fx.inc fx_color) */
            if (S->tool[i] & 0x80) { col[0] *= 4; col[1] *= 4; col[2] *= 4; }
            if (S->tool[i] & 0x20000) col[3] *= 4;
        }
        particle_slot[count] = (uint16_t) (S->uid[i] & 511);
        particles[count++] = (Billboard) {x, y, iw, rx, ry, S->rz[i], r->hdr, argb4(col)};
    }
    e2_fx_counts[0] = S->n; e2_fx_counts[1] = known; e2_fx_counts[2] = count;
    count = fx_cap(particles, count);   /* the owner's effect cap (CS_EFFECTS, default step 2) */
    e2_fx_counts[3] = count;
    qsort(particles, count, sizeof(Billboard), depth_sort);
    static const float uv[] = {0, 0, 1, 1};
    unsigned last = ~0u;
    for (unsigned i = 0; i < count; i++) {
        Billboard* b = particles + i;
        if (last != b->hdr) { last = b->hdr; submit_header(&s->assets, last); }
        rectangle(b->x, b->y, b->iw, b->rx, b->ry, b->angle, uv, b->color);
    }
}
