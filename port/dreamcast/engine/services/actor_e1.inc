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
/* Lane eng-e1j (second E1 audit section 3, ruling H-016.2): every character but Leon (who keeps the pack's record) is lit
   from its model record in place: the light rule reads its light volume, masks, flags, material colour, TEV group,
   added ambient and the room status word where the behaviour keeps them (services/light_view.h; e1_light_view gathers
   their addresses for the picture). No record is assembled or compared per tick (the light service of lane eng-e1e is
   gone: hill 728 compares, fight 3,600, now 0). The TEV scale of each group is resolved once from the pack at open (the
   rule of e1_live_light above: the first record of the group, else Leon's, else 255; value + 1, 0 = not resolved). */
extern uint16_t e1_tev_scale_of_group[256];
void e1_log(const char* fmt, ...);
extern int e1_pal_control;   /* services/draw.cpp: the PALCTL control */   /* core/globals.cpp: buffered while the ticks run (lane eng-e1e) */
unsigned e1_light_miss;   /* pictures a character had no light view (lit by the fallback record) */
/* lane eng-e1n (H-017.5): a light-view miss fails the scene (the E1 PUB line, loader/selector.c). LIGHTMISS (boot file,
   lab arm; the control): every character's light view refused, as a miss */
int e1_light_miss_control;
static void e1_weapon_open(const NativeScene* s);   /* lane eng-look1: services/weapon_draw.inc, once a pack (below) */
static void e1_arms_open(void);   /* lane eng-draw4: the look arms' boot files (below) */
void e1_light_tables(const NativeScene* s)
{
    e1_weapon_open(s);
    e1_arms_open();
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
        out &= sphere_planes6_flat(fr, c, sp->r * r[12], &inside);   /* lane eng-draw3: no branch per plane */
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

/* Lane eng-draw4, step 4: three LOOK ARMS for the owner (run-time only, never the default; one variable each), each a
   boot file read once when the pack opens (e1_light_tables, before play):
     LVL   character detail levels by screen size: the pack's PS2 levels and rigid far variants ('LODV' rows, already in
           every E1 pack), picked as the bench's owner-approved step 3 (render/content_actor.inc content_pick: level 1
           under 480 px, 2 under 160, 3 under 70, the rigid variant under 100, 10% hysteresis per character);
     LCAP  at most 3 lights a character: the strongest at the character's position (render/source_light.inc);
     LHALF each character's normals lit every other picture: a lit picture lights every normal of its visible parts
           into the character's own colour buffer; the next picture draws from it unchanged (no light pick, no weight-set
           lights, no normals lit) unless a part became visible that was not lit (then it lights again). Skinning and
           emission stay every picture. A character with no buffer (out of memory) is lit every picture, counted. */
/* Lane eng-draw5 (item 5): LSTAG, LHALF staggered (look arm, boot file, off by default): each character lights on the
   pictures of its own parity (its colour cache slot's index plus the picture number), so half of the characters light
   on one picture and half on the next, and a character's colours are at most one picture old while it stays drawn. Under
   LHALF every character lit on the same picture, which halved the mean but not the worst picture (eng-draw4). Memory: the
   same colour buffers as LHALF (one per character, 4 bytes a normal of its drawn model, from the heap). */
/* Lane eng-draw6 (item 3): character detail levels by screen size (eng-draw4's LVL, approved by the owner from its
   sheet) are the default. One pick per character: the fight's Ganados are picked by their caller (fight/fight_draw.inc,
   content_pick, step 3: CS_LEVELS, which the E1 images start at 0 and this open sets to 3), every other character
   (Leon, the partner, a held weapon) by this pass (content_pick on its bone-sphere box). The level asked and the level
   drawn are counted (e1_lvl_n; a variant whose bone count exceeds the skeleton's is refused and drawn at the base).
   LVL0 (boot file, comparison lab arm): levels off, the base model always (the image before this lane). */
static int e1_levels, e1_arm_lhalf, e1_arm_lstag, e1_pix_ctl;
static unsigned e1_lvl_slot[E1_SLOTS];            /* the catalogue model the slot's last opaque call drew */
static const uint32_t* e1_lit_slot[E1_SLOTS];     /* the colours it emitted from */
static unsigned e1_arm_n[8], e1_arm_calls;        /* LHALF lit, reused, no buffer [5-7] */
static unsigned e1_lvl_n[5][5];                   /* characters a picture by level asked (0-3, 4 rigid) and level drawn */
static int e1_arm_boot(const char* p) { file_t f = fs_open(p, O_RDONLY); if (f < 0) return 0; fs_close(f); return 1; }
static void e1_arms_open(void)
{
    static int done; if (done) return; done = 1;
    e1_levels = !e1_arm_boot("/cd/LVL0"); src_light_cap = e1_arm_boot("/cd/LCAP") ? 3 : 0; e1_arm_lhalf = e1_arm_boot("/cd/LHALF");
    e1_arm_lstag = e1_arm_boot("/cd/LSTAG"); if (e1_arm_lstag) e1_arm_lhalf = 1;
    m1_content[CS_LEVELS] = e1_levels ? 3 : 0;
    e1_log("E1 LVL: character detail levels by screen size %s\n", e1_levels ? "(step 3, the default)" : "off (LVL0, comparison lab arm)");
    if (src_light_cap) e1_log("E1 ARM LCAP: at most %u lights a character (the strongest), look arm\n", src_light_cap);
    if (e1_arm_lhalf) e1_log("E1 ARM LHALF: each character's normals lit every other picture%s, look arm\n",
                             e1_arm_lstag ? " (LSTAG: staggered, half the characters a picture)" : "");
    lold_arm = e1_arm_boot("/cd/LOLD"); if (lold_arm) src_light_cap = 3;   /* lane eng-draw5 item 4 (render/actor_light_old.inc) */
    if (lold_arm) e1_log("E1 ARM LOLD: the released game's character lighting (at most 3 lights a character, FTRV kernel, clamp after the scale), look arm\n");
    e1_pix_ctl = e1_arm_boot("/cd/PIXCTL");
    if (e1_pix_ctl) e1_log("E1 PIXCTL: control, one blue step flipped on every character colour (the pixel comparison must FAIL)\n");
}
static unsigned e1_lvl_key(const void* rec)   /* a content_pick ordinal (64..127) per character record */
{
    static const void* keys[63];
    for (unsigned i = 0; i < 63; i++) { if (keys[i] == rec) return 64 + i; if (!keys[i]) { keys[i] = rec; return 64 + i; } }
    return 127;
}
typedef struct { const void* rec; unsigned model, cap; uint32_t* buf; uint16_t mask; uint8_t fresh; } E1LitCache;
static E1LitCache e1_lc[16];
static E1LitCache* e1_lc_get(const void* rec, unsigned model, unsigned nrm)
{
    E1LitCache* c = 0;
    for (unsigned i = 0; i < 16 && !c; i++) if (e1_lc[i].rec == rec) c = e1_lc + i;
    for (unsigned i = 0; i < 16 && !c; i++) if (!e1_lc[i].rec) { c = e1_lc + i; c->rec = rec; }
    if (!c) return 0;
    if (c->model != model) { c->model = model; c->fresh = 0; }
    if (c->cap < nrm) { free(c->buf); c->buf = memalign(32, 4 * nrm + 32); c->cap = c->buf ? nrm : 0; c->fresh = 0; }
    return c->buf ? c : 0;
}
static void e1_arms_report(void)
{
    if (++e1_arm_calls != 640) return;
    if (src_light_cap || e1_arm_lhalf)
        e1_log("E1 ARM counts over 640 pictures: LHALF lit %u reused %u no-buffer %u\n", e1_arm_n[5], e1_arm_n[6], e1_arm_n[7]);
    /* lane eng-draw6 (item 1): eng-draw4's "no Ganado changed level" counter counted the model drawn against the model
       the pass was given, which for a Ganado is already the fight's pick: it now counts the level asked (the caller's
       pick or this pass's) against the level of the model drawn */
    char line[400]; unsigned at = 0, changed = 0, refused = 0;
    for (unsigned a = 0; a < 5; a++)
        for (unsigned d = 0; d < 5; d++) {
            if (!e1_lvl_n[a][d]) continue;
            if (d) changed += e1_lvl_n[a][d];
            if (a != d) refused += e1_lvl_n[a][d];
            if (at < sizeof line - 32) at += (unsigned) snprintf(line + at, sizeof line - at, " %u>%u %u", a, d, e1_lvl_n[a][d]);
        }
    line[at] = 0;
    e1_log("E1 LVL counts over 640 pictures (asked>drawn, 4 rigid):%s; drawn at another level %u, asked level not drawn %u, pool guard %u, "
           "translucent models outside slot 0 %u\n", line, changed, refused, actor_pool_refused, actor_trans_other);
    for (unsigned b = 0; b < CONTENT_MODELS; b++) {
        const volatile uint32_t* r = m1_lod_models[b];
        if ((r[1] | r[2] | r[3] | r[4] | r[0]) && lod_base_of[b] == b)
            e1_log("E1 LVL model %u: picks at level 0 %u, 1 %u, 2 %u, 3 %u, rigid %u; variants %u %u %u %u\n", b,
                   (unsigned) r[0], (unsigned) r[1], (unsigned) r[2], (unsigned) r[3], (unsigned) r[4], lod_variant[b][1],
                   lod_variant[b][2], lod_variant[b][3], lod_variant[b][4]);
    }
}
/* Lane eng-draw6 (item 3): on a still picture of a STILLS run (never a timing run), each character's screen box (the
   projected positions of its drawn parts) with its base model and the levels asked and drawn, for the stills check
   tools/engine/lvlcheck.py (a still may differ from the base only inside the box of a character drawn at another level). */
extern volatile uint32_t m1_frame;
int e1_draw_stills_c(void);
static void e1_lvl_box(unsigned model, unsigned drawn, unsigned asked, const RtModel* m, const uint8_t* state, const pvr_vertex_t* proj)
{
    static uint32_t frame; static unsigned index;
    const uint32_t f = m1_frame;
    if (!(f == 1 || f % 40 == 0) || !e1_draw_stills_c()) return;
    if (frame != f) { frame = f; index = 0; }
    float x0 = 1e9f, y0 = 1e9f, x1 = -1e9f, y1 = -1e9f;
    for (unsigned p = 0; p < m->h[4]; p++) {
        if (!state[p]) continue; const RtPart* rp = m->parts + p;
        for (unsigned i = rp->pos_first; i < (unsigned) rp->pos_first + rp->pos_count; i++) {
            const pvr_vertex_t* v = proj + i;
            if (!(v->z > 0)) continue;
            x0 = m1_minf(x0, v->x); y0 = m1_minf(y0, v->y); x1 = m1_maxf(x1, v->x); y1 = m1_maxf(y1, v->y);
        }
    }
    const unsigned base = model < 256 ? lod_base_of[model] : model, ld = drawn < 256 ? lod_level_of[drawn] : 0;
    if (x1 < x0) { x0 = y0 = 0; x1 = y1 = -1; }
    /* straight to the serial line, not the tick-time log buffer: in FIGHT that buffer overflows (the room carve's
       refusal lines, from the memory map, 1,600 lines dropped) and these lines were lost. A still picture already waits
       for the host to read the frame buffer; a STILLS run is never a timing run. */
    printf("E1 LVLBOX f %u c %u base %u asked %u drawn %u model %u box %d %d %d %d\n", (unsigned) f, index++, base, asked, ld,
           drawn, (int) floorf(x0), (int) floorf(y0), (int) ceilf(x1), (int) ceilf(y1));
}

/* lane eng-look1: one character or object; 0 when it cannot be drawn at all (no such catalogue model, or a skeleton with
   fewer bones than the model), 1 when it went through the pass (drawn, or culled by the frustum). frame_setup 0: the
   picture's frustum, projection and lamp order are already set by the call before it (the weapon after Leon) */
static int e1_actor_pass_one(NativeScene* s, const void* model_record, const E1SkelView* skel, unsigned model, unsigned identity,
                             unsigned translucent, int frame_setup)
{
    const RtCatalog* cat = s->runtime;
    const float* camera = (const float*) s->state[0];
    float near = camera[18] / (camera[17] - 1);
    const unsigned slot = model ? 1 : 0;
    static unsigned bones_slot[E1_SLOTS];
    const float** e1_bone = e1_bone_slot[slot];
    if (model >= cat->n) return 0;
    if (!translucent) { if (frame_setup) actor_frame_setup(s); ++actor_serial; bones_slot[slot] = e1_gather(e1_bone, (const uint8_t*) model_record, skel); }
    const unsigned bones = bones_slot[slot];
    const RtModel* m = cat->m + model;
    const unsigned* h = m->h;
    if (bones < h[0]) return 0;
    if (model < 256 && !e1_pal_ok_model[model]) e1_pal_ok_model[model] = e1_pal_check(m, skel) ? 1 : -1;
    const int e1_pal_ok = model < 256 && e1_pal_ok_model[model] > 0;
    pvr_vertex_t* sq = (pvr_vertex_t*) sq_lock((void*) PVR_TA_INPUT);
    uint8_t* state = part_state[slot];
    const pvr_vertex_t* proj = projected_pool[slot]; uint32_t* lit = colors_pool[slot]; uint8_t* codes = outcode_pool[slot];
    cur_projected = proj; cur_lit = lit; cur_codes = codes; cur_pos = m->pos;
    uint8_t* strip_codes = strip_code_pool[slot]; cur_strip_codes = strip_codes;
    if (translucent) {   /* Leon's alone: no model outside slot 0 has a translucent part (actor_trans_other, guard) */
        unsigned emitted = 0;
        m = cat->m + e1_lvl_slot[slot]; h = m->h; cur_pos = m->pos;   /* the model the opaque call drew (its level) */
        if (e1_arm_lhalf && e1_lit_slot[slot]) cur_lit = e1_lit_slot[slot];               /* arm LHALF: its colours */
        for (unsigned p = 0; p < h[4]; p++)
            if (m->parts[p].src->role == 8 && state[p]) sq = emit_part(sq, s, m, m->parts + p, state[p], near, &emitted);
        sq_wait(); sq_unlock();
        return 1;
    }
    /* 1. whole actor */
    unsigned all = 63;
    for (unsigned i = 0; i < m->nbones_used; i++) {
        unsigned b = m->bones_used[i]; const float* wm = e1_bone[b + 1]; int dummy = 1;
        float c[3] = {wm[3], wm[7], wm[11]}, r = m->bone_radius[b] * column_scale(wm) * 1.02f + 1;
        all &= sphere_planes(c, r, &dummy);
    }
    if (all) { memset(state, 0, h[4]); e1_lvl_slot[slot] = model; sq_wait(); sq_unlock(); return 1; }
    unsigned drawn = model, asked = model < 256 ? lod_level_of[model] : 0;
    if (e1_levels) {
        /* a model its caller picked this picture (the fight's Ganados) is drawn as given; any other character with
           levels is picked here by the projected size of its bone-sphere box (content_pick) */
        const int caller = model < 256 && lod_stamp[model] == (uint16_t) m1_state[1];
        if (caller) asked = lod_asked[model];
        else if (model < CONTENT_MODELS && (lod_variant[model][1] != model || lod_variant[model][4] != 0xffff)) {
            float lo[3] = {1e30f, 1e30f, 1e30f}, hi[3] = {-1e30f, -1e30f, -1e30f};
            for (unsigned i = 0; i < m->nbones_used; i++) {
                unsigned b = m->bones_used[i]; const float* wm = e1_bone[b + 1];
                float r = m->bone_radius[b] * column_scale(wm) * 1.02f + 1, c[3] = {wm[3], wm[7], wm[11]};
                for (unsigned a = 0; a < 3; a++) { lo[a] = m1_minf(lo[a], c[a] - r); hi[a] = m1_maxf(hi[a], c[a] + r); }
            }
            const unsigned key = e1_lvl_key(model_record);
            lod_mark_on = 0;
            const unsigned v = content_pick(s, model, lo, hi, key);
            lod_mark_on = 1;
            asked = v == lod_variant[model][4] && v != model ? 4 : lod_last[key] & 3;
            if (v != model && v < cat->n && cat->m[v].h[0] <= bones) {
                m = cat->m + v; h = m->h; cur_pos = m->pos; drawn = v;
                if (v < 256 && !e1_pal_ok_model[v]) e1_pal_ok_model[v] = e1_pal_check(m, skel) ? 1 : -1;
            }
        }
        e1_lvl_n[asked > 4 ? 4 : asked][drawn < 256 ? lod_level_of[drawn] : 0]++;
    }
    e1_lvl_slot[slot] = drawn;
    if (!actor_pool_fits(slot, m)) { memset(state, 0, h[4]); e1_lvl_slot[slot] = model; sq_wait(); sq_unlock(); return 0; }   /* lane eng-draw6 */
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
    if (DC_ARM(DL_CLASS2)) {   /* lane eng-draw4 lab arm C (set E): the whole-character test and the part classes again */
        static volatile unsigned sink; unsigned again = 63;
        for (unsigned i = 0; i < m->nbones_used; i++) {
            unsigned b = m->bones_used[i]; const float* wm = e1_bone[b + 1]; int dummy = 1;
            float c[3] = {wm[3], wm[7], wm[11]}, r = m->bone_radius[b] * column_scale(wm) * 1.02f + 1;
            again &= sphere_planes(c, r, &dummy);
        }
        for (unsigned p = 0; p < h[4]; p++)
            again += e1_part_class((const float (*)[4]) frustum, m->spheres + m->parts[p].sphere_first, m->parts[p].sphere_count, pal);
        sink = again;
    }
    if (!visible) { sq_wait(); sq_unlock(); return 1; }
    /* lane eng-draw3 (E3): Leon's knife part (role 2) is drawn in the knife stance only: out of it, it is not skinned,
       lit or given weight sets either */
    if (!model && !knife_stance(s))
        for (unsigned p = 0; p < h[4]; p++) if (m->parts[p].src->role == 2) state[p] = 0;
    /* 4. lights and weight sets. The light rule reads the model's and its bone 0's matrices in place (no ActorPose
       copies). Leon: the pack's record (looked up once a pack); every other character: its model record in place. */
    const ModelLight* ml = &src_light_fallback;
    E1LightView lv;
    const E1LightView* live = 0;
    if (model) {
        if (!e1_light_miss_control && e1_light_view(model_record, &lv)) live = &lv;
        else e1_light_miss++;
    } else {
        static const void* leon_scene; static const ModelLight* leon_rec;
        if (leon_scene != s->state[8]) { leon_scene = s->state[8]; leon_rec = model_light_ri(s, 0, 0); }
        e1_light_check(s, model_record, leon_rec);
        if (leon_rec) ml = leon_rec;
    }
    E1LitCache* lc = 0; int reuse = 0; uint16_t vis = 0;
    if (e1_arm_lhalf) {   /* arm LHALF: this picture lights, or draws from the colours of the last */
        for (unsigned p = 0; p < h[4]; p++) if (state[p]) vis |= (uint16_t) (1u << p);
        const RtPart* lp = m->parts + h[4] - 1;
        lc = e1_lc_get(model_record, drawn, lp->nrm_first + lp->nrm_count);
        if (lc && e1_arm_lstag) {   /* LSTAG: the character's own parity; fresh = its buffer holds this model's colours */
            reuse = lc->fresh && ((m1_state[1] + (unsigned) (lc - e1_lc)) & 1) && !(vis & ~lc->mask);
            e1_arm_n[reuse ? 6 : 5]++;
        } else if (lc) { reuse = lc->fresh && !(vis & ~lc->mask); e1_arm_n[reuse ? 6 : 5]++; } else e1_arm_n[7]++;
    }
    if (!reuse) {
        /* the light volume's origin: part 1 (bone 0) or the model */
        const unsigned parts = live ? (unsigned) (uint8_t) live->info->parts : ml->info >> 8 & 255;
        source_lights_w(s, e1_bone[0], parts == 1 ? e1_bone[1] : e1_bone[0], e1_bone[1], ml, live, &cur_lights);
        if (lold_arm) lold_character(e1_bone[1]);   /* LOLD arm: directions and distance terms once a character */
        if (DC_ARM(DL_PICK2)) source_lights_w(s, e1_bone[0], parts == 1 ? e1_bone[1] : e1_bone[0], e1_bone[1], ml, live, &cur_lights);   /* lane eng-draw4 arm P */
    }
    memset(ws_ready, 0, h[1]);
    ws_rows = pal; ws_stride = e1_pal_control ? 12 : 16;   /* build_ws blends the palette rows in place (PALCTL: wrong stride) */
    ws_begin();
    ws_light_off = reuse;   /* arm LHALF: no weight-set lights on a reused picture */
    for (unsigned p = 0; p < h[4]; p++) {
        if (!state[p]) continue; const RtPart* rp = m->parts + p;
        for (unsigned k = 0; k < rp->ws_count; k++) { unsigned i = m->part_ws[rp->ws_first + k]; if (!ws_ready[i]) build_ws(m, i); }
    }
    ws_light_off = 0;
    ws_rows = &bone_rows[0][0]; ws_stride = 12;
    /* 5. positions and normals */
    for (unsigned p = 0; p < h[4]; p++) {
        if (!state[p]) continue; const RtPart* rp = m->parts + p;
        unsigned n = rp->pos_count;
        pos_records[n][0] = pos_records[n + 1][0] = 0;
        PositionPass a = {pos_records, n, m->pos + rp->pos_first, dummy_uv, (void*) (proj + rp->pos_first), codes + rp->pos_first, 8,
                          skin_project[0].elem, ws_ready, h[1], 640, 480, near, camera[25], 0, 0, 0, 0};
        m1_avk_pos_skin_xy(&a);   /* lane eng-draw5 (item 2): no u, v; lane eng-draw6 (item 2): the kernel (C arm SKC deleted) */
        if (DC_ARM(DL_SKIN2)) m1_avk_pos_skin_xy(&a);   /* lane eng-draw4 arm K (set E): positions skinned twice */
        pos_records[n][0] = n; pos_records[n + 1][0] = n + 1;
        /* lane eng-draw3 (E3): a boundary part lights only the normals its kept strips use */
        if (!lc) {
            light_part(m, rp, state[p], codes, strip_codes, lit, 1);
            /* lane eng-draw4, the pixel comparison's control PIXCTL (boot file): one step of blue in RGB565 (8 of 255)
               flipped on every lit colour of the part: the exact-step comparison (cmp.py) must find differing pixels */
            if (e1_pix_ctl) for (unsigned i = rp->nrm_first; i < (unsigned) rp->nrm_first + rp->nrm_count; i++) lit[i] ^= 8;
        }
        else {   /* arm LHALF: strip codes as usual; a lit picture lights the part's whole normal range into the buffer */
            light_part(m, rp, state[p], codes, strip_codes, lc->buf, 0);
            if (!reuse) light_normals_source(m->nrm + rp->nrm_first, rp->nrm_count, lc->buf + rp->nrm_first);
        }
    }
    e1_lvl_box(model, drawn, asked, m, state, proj);   /* lane eng-draw6: still pictures of a STILLS run only */
    if (lc) { cur_lit = lc->buf; lc->fresh = e1_arm_lstag ? 1 : !reuse; if (!reuse) lc->mask = vis; }
    e1_lit_slot[slot] = cur_lit;
    if (!model) e1_arms_report();
    /* 6. opaque parts (lane eng-e1d: as the bench's pass since eng-look, the hair part, role 7, is opaque with the body
       atlas and the hair run, role 8, is drawn in the translucent call, in the translucent list); Leon's knife part only
       in the knife stance (its state is 0 otherwise, above) */
    unsigned emitted = 0;
    for (unsigned p = 0; p < h[4]; p++) {
        if (!state[p] || m->parts[p].src->role == 8) continue;
        sq = emit_part(sq, s, m, m->parts + p, state[p], near, &emitted);
    }
    sq_wait(); sq_unlock();
    return 1;
}

/* Lane eng-look1: the weapons Leon holds (services/weapon_draw.inc), drawn after his body in the same opaque list. */
#include "weapon_draw.inc"
void e1_actor_pass(NativeScene* s, const void* model_record, const E1SkelView* skel, unsigned model, unsigned identity,
                   unsigned translucent)
{
    e1_actor_pass_one(s, model_record, skel, model, identity, translucent, 1);
    if (!model && !translucent) e1_weapon_pass(s);
}
