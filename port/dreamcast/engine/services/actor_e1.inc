/* E1 actor pass (lane eng-e1), included after render/native_actor.inc by services/render_e1.c.

   The E0 actor pass reads recorded poses (ActorPose records, a copy of each bone's world matrix). The E1 pass reads
   the engine actor table in place: bone 0 is the model's own coordinate matrix (cCoord::mat at +0x0C), bone k + 1
   is the k-th cParts on the model's pParts chain (cCoord::mat at +0x0C, next part at +0xF4), written once per tick
   by the skeleton service. Only pointers are gathered per picture; no matrix is converted. The lights use the
   source rule (source_light.inc) with the room's light set and the model's light record from the pack (the hosted
   light manager is not in E1). Lane eng-e1e: the light rule reads the model's and its light-origin part's matrices
   by pointer (source_lights_w), and step 2 is gone: the skeleton service publishes the palette in this pass's skinning
   layout (see step 2 below).
   Steps 1, 3 to 6 are native_actor_pass's.

   Lane eng-e1c: the bones come from the native skeleton's table (E1SkelView, services/e1_skel_view.h), not from the
   cParts records (only the mailbox records are written now): the world records for the whole-actor test and the
   lights, the palette (world x bind, written once a tick by the skeleton service) for the skin. The palette replaces
   step 2's world x bind multiplication when the pack's bind is the table's (identity rotation, the same translation:
   checked once, for every bone the model uses); otherwise step 2 multiplies the table's world records as before. */
/* Lane eng-e1d: two characters a picture (Leon, catalogue 0; Ashley in the hill scene, catalogue 6 of the hill pack,
   141 bones). Each has its own slot: bone pointers, part states and projected / lit pools (the translucent call of a
   character reads what its own opaque call left). The palette check is kept per catalogue model (lane eng-e2's
   Ganado models included). Light inputs: Leon keeps his record from the pack (the capture's, stream 8); every other
   character is lit by its OWN record, built from its model record in the actor table (cModel::LightInfo, material
   colour, TEV group, added ambient: services/draw.cpp e1_light_record), the TEV scale of its group taken from the
   pack's records (the room's gxCsScale is not hosted). Checked once against Leon's: his live record against the
   recorded one (E1 LIGHT check). */
#include "e1_skel_view.h"
#define E1_BONES 160
#define E1_SLOTS 2
static const float* e1_bone_slot[E1_SLOTS][E1_BONES + 1];
static signed char e1_pal_ok_model[256];   /* per catalogue model: 0 not checked, 1 the palette is the pack's world x bind, -1 multiply */
int e1_light_record(const void* model, uint32_t* out17);   /* services/draw.cpp: the model's light inputs, ModelLight layout */
static void e1_live_light(const NativeScene* s, const void* model_record, ModelLight* out)
{
    e1_light_record(model_record, (uint32_t*) out);
    const unsigned group = out->tev & 255;
    const ModelLight* rec = (const void*) s->state[8]; const unsigned n = s->words[8] * 4 / sizeof(ModelLight);
    int scale = -1, leon = -1;   /* the scale of a record with the same group, else Leon's, else 255 (x4) */
    for (unsigned i = 0; i < n; i++) {
        if ((rec[i].tev & 255) == group && scale < 0) scale = rec[i].tev >> 8 & 255;
        if (rec[i].role == 0 && leon < 0) leon = rec[i].tev >> 8 & 255;
    }
    out->tev = group | (unsigned) (scale >= 0 ? scale : leon >= 0 ? leon : 255) << 8;
}
/* Lane eng-e1e (E1 audit section 2): the light service (services/draw.cpp) keeps every character's record but Leon's,
   rebuilt only when its inputs change; the pass reads it in place (e1_light_rec_of). The TEV scale of each group is
   resolved once from the pack at open (the rule of e1_live_light above: the first record of the group, else Leon's,
   else 255), into the table the service builds its records with (value + 1; 0 = not resolved). */
extern uint16_t e1_tev_scale_of_group[256];
const uint32_t* e1_light_rec_of(const void* model);
void e1_log(const char* fmt, ...);
extern int e1_pal_control;   /* services/draw.cpp: the PALCTL control */   /* core/globals.cpp: buffered while the ticks run (lane eng-e1e) */
unsigned e1_light_miss;   /* pictures a character had no record from the service (lit by the fallback record) */
void e1_light_tables(const NativeScene* s)
{
    const ModelLight* rec = (const void*) s->state[8]; const unsigned n = s->words[8] * 4 / sizeof(ModelLight);
    int leon = -1;
    for (unsigned i = 0; i < n; i++) if (rec[i].role == 0 && leon < 0) leon = rec[i].tev >> 8 & 255;
    for (unsigned g = 0; g < 256; g++) {
        int scale = -1;
        for (unsigned i = 0; i < n && scale < 0; i++) if ((rec[i].tev & 255) == g) scale = rec[i].tev >> 8 & 255;
        e1_tev_scale_of_group[g] = (uint16_t) ((scale >= 0 ? scale : leon >= 0 ? leon : 255) + 1);
    }
}
/* The bone's sphere test on the published palette (lane eng-e1e): part_class's rule (render/part_cull.h) reading the
   palette in place, 16 floats a bone, its word 12 the bone's sphere scale. */
static inline unsigned e1_part_class(const float (*fr)[4], const PartSphere* sp, unsigned n, const float* pal)
{
    unsigned out = 63; int inside = 1;
    for (unsigned k = 0; k < n && (out || inside); k++, sp++) {
        const float* r = pal + 16 * sp->bone; float c[3];
        for (unsigned a = 0; a < 3; a++) c[a] = r[4 * a] * sp->c[0] + r[4 * a + 1] * sp->c[1] + r[4 * a + 2] * sp->c[2] + r[4 * a + 3];
        out &= sphere_planes6(fr, c, sp->r * r[12], &inside);
    }
    return out ? 0 : inside ? 1 : 2;
}
static void e1_light_check(const NativeScene* s, const void* leon_record, const ModelLight* recorded)
{
    static int done;
    if (done++ || !recorded) return;
    ModelLight live;
    e1_live_light(s, leon_record, &live);
    unsigned diff = 0;
    diff += live.info != recorded->info; diff += live.select != recorded->select;
    for (unsigned k = 0; k < 3; k++) diff += live.offset[k] != recorded->offset[k], diff += live.size[k] != recorded->size[k];
    diff += memcmp(live.color, recorded->color, 4) != 0; diff += live.tev != recorded->tev; diff += live.addamb != recorded->addamb;
    e1_log("E1 LIGHT check: Leon's live light inputs vs the pack's record: %u of 12 fields differ (info %08x/%08x select %08x/%08x tev %x/%x)\n",
           diff, live.info, recorded->info, live.select, recorded->select, live.tev, recorded->tev);
}
unsigned e1_pal_mismatch;    /* bones whose pack bind differs from the table's (report) */
float e1_pal_worst;          /* the largest difference found by the check */

static unsigned e1_gather(const float** e1_bone, const uint8_t* model, const E1SkelView* sk)
{
    unsigned n = 0;
    e1_bone[0] = (const float*) (model + 0x0C);
    if (!sk) return 0;
    for (; n < sk->n && n < E1_BONES; n++) e1_bone[n + 1] = sk->world + 16 * n;
    return n;
}

static int e1_pal_check(const RtModel* m, const E1SkelView* sk)
{
    unsigned bad = 0; float worst = 0;
    for (unsigned i = 0; i < m->nbones_used; i++) {
        unsigned b = m->bones_used[i]; const float* p = m->bind + 12 * b;
        const float want[12] = {1, 0, 0, sk->bind[0][b], 0, 1, 0, sk->bind[1][b], 0, 0, 1, sk->bind[2][b]};
        float d = 0;
        for (unsigned k = 0; k < 12; k++) { float e = fabsf(p[k] - want[k]) / ((k & 3) == 3 ? 1.0f : 1e-2f); if (e > d) d = e; }
        if (d > 1e-2f) bad++;
        if (d > worst) worst = d;
    }
    e1_pal_mismatch = bad; e1_pal_worst = worst;
    e1_log("E1 PAL check: %u of %u bones differ (worst %d/1000 unit, rotation in 1/100000), %s\n", bad, m->nbones_used,
           (int) (worst * 1000), bad ? "FAULT: the pack's bind is not the skeleton's (drawn from the palette)" : "palette used");
    return bad == 0;
}

void e1_actor_pass(NativeScene* s, const void* model_record, const E1SkelView* skel, unsigned model, unsigned identity,
                   unsigned translucent)
{
    const RtCatalog* cat = s->runtime;
    const float* camera = (const float*) s->state[0];
    float near = camera[18] / (camera[17] - 1);
    const unsigned slot = model ? 1 : 0;
    static unsigned bones_slot[E1_SLOTS];
    const float** e1_bone = e1_bone_slot[slot];
    if (model >= cat->n) return;
    if (!translucent) { actor_frame_setup(s); ++actor_serial; bones_slot[slot] = e1_gather(e1_bone, (const uint8_t*) model_record, skel); }
    const unsigned bones = bones_slot[slot];
    const RtModel* m = cat->m + model;
    const unsigned* h = m->h;
    if (bones < h[0]) return;
    if (model < 256 && !e1_pal_ok_model[model]) e1_pal_ok_model[model] = e1_pal_check(m, skel) ? 1 : -1;
    const int e1_pal_ok = model < 256 && e1_pal_ok_model[model] > 0;
    pvr_vertex_t* sq = (pvr_vertex_t*) sq_lock((void*) PVR_TA_INPUT);
    uint8_t* state = part_state[slot];
    const pvr_vertex_t* proj = projected_pool[slot]; uint32_t* lit = colors_pool[slot]; uint8_t* codes = outcode_pool[slot];
    cur_projected = proj; cur_lit = lit; cur_codes = codes; cur_pos = m->pos;
    if (translucent) {
        unsigned emitted = 0;
        for (unsigned p = 0; p < h[4]; p++)
            if (m->parts[p].src->role == 8 && state[p]) sq = emit_part(sq, s, m, m->parts + p, state[p], near, &emitted);
        sq_wait(); sq_unlock();
        return;
    }
    /* 1. whole actor */
    unsigned all = 63;
    for (unsigned i = 0; i < m->nbones_used; i++) {
        unsigned b = m->bones_used[i]; const float* wm = e1_bone[b + 1]; int dummy = 1;
        float c[3] = {wm[3], wm[7], wm[11]}, r = m->bone_radius[b] * column_scale(wm) * 1.02f + 1;
        all &= sphere_planes(c, r, &dummy);
    }
    if (all) { memset(state, 0, h[4]); sq_wait(); sq_unlock(); return; }
    /* 2. bones (lane eng-e1e, E1 audit section 2): none. The skeleton service publishes the palette once a tick in
       this pass's final skinning layout (world x bind, the position quantum 1/16 in the basis, word 12 the sphere
       scale; skel.cpp SKEL_PAL_DRAW); steps 3 and 4 read it in place. No per-actor copy, rescale or bind recompute:
       a model whose pack bind is not the table's (e1_pal_check) is a bake fault, counted, and drawn from the palette. */
    (void) e1_pal_ok;
    const float* pal = skel->pal;
    /* 3. parts */
    unsigned visible = 0;
    for (unsigned p = 0; p < h[4]; p++) {
        const RtPart* rp = m->parts + p;
        unsigned st = e1_part_class((const float (*)[4]) frustum, m->spheres + rp->sphere_first, rp->sphere_count, pal);
        state[p] = st; visible += st != 0;
    }
    if (!visible) { sq_wait(); sq_unlock(); return; }
    /* 4. lights and weight sets. The light rule reads the model's and its bone 0's matrices in place (no ActorPose
       copies). Leon: the pack's record (looked up once a pack); every other character: the light service's record. */
    const ModelLight* ml;
    if (model) {
        ml = (const ModelLight*) e1_light_rec_of(model_record);
        if (!ml) { ml = &src_light_fallback; e1_light_miss++; }
    } else {
        static const void* leon_scene; static const ModelLight* leon_rec;
        if (leon_scene != s->state[8]) { leon_scene = s->state[8]; leon_rec = model_light_ri(s, 0, 0); }
        e1_light_check(s, model_record, leon_rec);
        ml = leon_rec ? leon_rec : &src_light_fallback;
    }
    {
        const unsigned parts = ml->info >> 8 & 255;   /* the light volume's origin: part 1 (bone 0) or the model */
        source_lights_w(s, e1_bone[0], parts == 1 ? e1_bone[1] : e1_bone[0], e1_bone[1], ml, &cur_lights);
    }
    memset(ws_ready, 0, h[1]);
    ws_rows = pal; ws_stride = e1_pal_control ? 12 : 16;   /* build_ws blends the palette rows in place (PALCTL: wrong stride) */
    for (unsigned p = 0; p < h[4]; p++) {
        if (!state[p]) continue; const RtPart* rp = m->parts + p;
        for (unsigned k = 0; k < rp->ws_count; k++) { unsigned i = m->part_ws[rp->ws_first + k]; if (!ws_ready[i]) build_ws(m, i); }
    }
    ws_rows = &bone_rows[0][0]; ws_stride = 12;
    /* 5. positions and normals */
    for (unsigned p = 0; p < h[4]; p++) {
        if (!state[p]) continue; const RtPart* rp = m->parts + p;
        unsigned n = rp->pos_count;
        pos_records[n][0] = pos_records[n + 1][0] = 0;
        PositionPass a = {pos_records, n, m->pos + rp->pos_first, dummy_uv, (void*) (proj + rp->pos_first), codes + rp->pos_first, 8,
                          skin_project[0].elem, ws_ready, h[1], 640, 480, near, camera[25], 0, 0, 0, 0};
        re4dc_avk_pos_skin_u16(&a);
        pos_records[n][0] = n; pos_records[n + 1][0] = n + 1;
        light_normals_source(m->nrm + rp->nrm_first, rp->nrm_count, lit + rp->nrm_first);
    }
    /* 6. opaque parts (lane eng-e1d: as the bench's pass since eng-look, the hair part, role 7, is opaque with the body
       atlas and the hair run, role 8, is drawn in the translucent call, in the translucent list); Leon's knife part only
       in the knife stance */
    unsigned emitted = 0;
    for (unsigned p = 0; p < h[4]; p++) {
        if (!state[p] || m->parts[p].src->role == 8) continue;
        if (!model && m->parts[p].src->role == 2 && knife_stance(s) == 0) continue;
        sq = emit_part(sq, s, m, m->parts + p, state[p], near, &emitted);
    }
    sq_wait(); sq_unlock();
}
