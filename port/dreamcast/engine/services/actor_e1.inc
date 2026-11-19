/* E1 actor pass (lane eng-e1), included after render/native_actor.inc by services/render_e1.c.

   The E0 actor pass reads recorded poses (ActorPose records, a copy of each bone's world matrix). The E1 pass reads
   the engine actor table in place: bone 0 is the model's own coordinate matrix (cCoord::mat at +0x0C), bone k + 1
   is the k-th cParts on the model's pParts chain (cCoord::mat at +0x0C, next part at +0xF4), written once per tick
   by the skeleton service. Only pointers are gathered per picture; no matrix is converted. The lights use the
   source rule (source_light.inc) with the room's light set and the model's light record from the pack (the hosted
   light manager is not in E1); those helpers take ActorPose records for the model and its light-origin part, so the
   two matrices they read are copied (96 bytes a picture).
   Steps 1 to 6 are native_actor_pass's, unchanged. */
#define E1_BONES 128
static const float* e1_bone[E1_BONES + 1];

static unsigned e1_gather(const uint8_t* model)
{
    unsigned n = 0;
    e1_bone[0] = (const float*) (model + 0x0C);
    const uint8_t* p = *(const uint8_t* const*) (model + 0xF4);
    while (p && n < E1_BONES) {
        e1_bone[++n] = (const float*) (p + 0x0C);
        p = *(const uint8_t* const*) (p + 0xF4);
    }
    return n;
}

void e1_actor_pass(NativeScene* s, const void* model_record, unsigned model, unsigned identity, unsigned translucent)
{
    const RtCatalog* cat = s->runtime;
    const float* camera = (const float*) s->state[0];
    float near = camera[18] / (camera[17] - 1);
    static unsigned bones;
    if (!translucent) { actor_frame_setup(s); ++actor_serial; bones = e1_gather((const uint8_t*) model_record); }
    const RtModel* m = cat->m + model;
    const unsigned* h = m->h;
    if (bones < h[0]) return;
    pvr_vertex_t* sq = (pvr_vertex_t*) sq_lock((void*) PVR_TA_INPUT);
    uint8_t* state = part_state[0];
    const pvr_vertex_t* proj = projected_pool[0]; uint32_t* lit = colors_pool[0]; uint8_t* codes = outcode_pool[0];
    cur_projected = proj; cur_lit = lit; cur_codes = codes; cur_pos = m->pos;
    if (translucent) {
        unsigned emitted = 0;
        for (unsigned p = 0; p < h[4]; p++)
            if (m->parts[p].src->role == 7 && state[p]) sq = emit_part(sq, s, m, m->parts + p, state[p], near, &emitted);
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
    /* 2. bones */
    for (unsigned i = 0; i < m->nbones_used; i++) {
        unsigned b = m->bones_used[i]; float* r = bone_rows[b];
        multiply34(r, e1_bone[b + 1], m->bind + 12 * b);
        for (unsigned k = 0; k < 3; k++) { r[k] *= .0625f; r[4 + k] *= .0625f; r[8 + k] *= .0625f; }
        bone_scale[b] = column_scale(r);
    }
    /* 3. parts */
    unsigned visible = 0;
    for (unsigned p = 0; p < h[4]; p++) {
        const RtPart* rp = m->parts + p;
        unsigned st = part_class((const float (*)[4]) frustum, m->spheres + rp->sphere_first, rp->sphere_count,
                                 (const float (*)[12]) bone_rows, bone_scale);
        state[p] = st; visible += st != 0;
    }
    if (!visible) { sq_wait(); sq_unlock(); return; }
    /* 4. lights (model and light-origin part records) and weight sets */
    ActorPose lite[2];
    lite[0].role = 0; lite[0].index = 0; lite[0].identity = identity; lite[0].bone = 0;
    memcpy(lite[0].world, e1_bone[0], 48);
    lite[1] = lite[0]; lite[1].bone = 1; memcpy(lite[1].world, e1_bone[1], 48);
    source_lights(s, lite, 1, model_light(s, lite), &cur_lights);
    memset(ws_ready, 0, h[1]);
    for (unsigned p = 0; p < h[4]; p++) {
        if (!state[p]) continue; const RtPart* rp = m->parts + p;
        for (unsigned k = 0; k < rp->ws_count; k++) { unsigned i = m->part_ws[rp->ws_first + k]; if (!ws_ready[i]) build_ws(m, i); }
    }
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
    /* 6. opaque parts (hair in the translucent call); Leon's knife part only in the knife stance */
    unsigned emitted = 0;
    for (unsigned p = 0; p < h[4]; p++) {
        if (!state[p] || m->parts[p].src->role == 7) continue;
        if (!model && m->parts[p].src->role == 2 && knife_stance(s) == 0) continue;
        sq = emit_part(sq, s, m, m->parts + p, state[p], near, &emitted);
    }
    sq_wait(); sq_unlock();
}
