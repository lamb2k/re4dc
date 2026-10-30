// Current EspSpriteEmit body; preserve policy and transform cadence.
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
#define RE4DC_ESPSPRITE03_RETURN(state) return {re4dc::NativeDrawOutcome::state}
    if(!esp)RE4DC_ESPSPRITE03_RETURN(UnsupportedBeforePublication);
#else
#define RE4DC_ESPSPRITE03_RETURN(state) return
#endif

    // GX blend factors 0..7 (ZERO ONE DSTCLR/SRCCLR INVxCLR SRCA INVSRCA DSTA INVDSTA) have the
    // PVR_BLEND_* values 0..7 (PVR "DESTCOLOR" is the other colour on either side).
    // Local corners of g_EspCommonDisplayList in PVR sprite order A(0,1) B(1,1) C(1,0) D(0,0).
    static const f32 cx[4] = {0.0f, 1.0f, 1.0f, 0.0f}, cy[4] = {1.0f, 1.0f, 0.0f, 0.0f};
    static const f32 cu[4] = {0.0f, 1.0f, 1.0f, 0.0f}, cv[4] = {0.0f, 0.0f, 1.0f, 1.0f};
#if RE4DC_PS2_FX_POPULATION
    const Ps2fxHaze* population_haze = Ps2fxHazeFor(esp);
    const int population_selected = Ps2fxPopulationState(esp, population_haze) == 1;
    const unsigned draw_tex = population_selected && population_haze->room == 0x10f ? 0x1f : esp->m_Tex_id;
    EspTexWk* tw = &g_pEspSys->Esp_tex_tbl[draw_tex];
#else
    EspTexWk* tw = &g_pEspSys->Esp_tex_tbl[esp->m_Tex_id];
#endif
    if (tw->Owner == 0xD2 || !tw->pTpl || esp->m_Ptn_no >= tw->pTpl->numDescriptors) {
        RE4DC_ESPSPRITE03_RETURN(Refused);
    }
#if defined(RE4DC_MIST_CUT)
    {   // a recipe haze sprite (Esp15 with a PS2 row) is declined further down, after the fog rows' notes
        const unsigned cls = MistCutClass(esp);
        if ((re4dc_mist_cut & cls) && (cls != 1 || esp->m_Id == 0x48 || !Ps2fxHazeFor(esp))) {
            MistCutNote(cls);
            RE4DC_ESPSPRITE03_RETURN(PolicySkip);
        }
    }
#endif
#if defined(RE4DC_HAZE_SPRITE_CUT)
    // A PS2 recipe haze sprite is declined in its branch below, after HW_FOG_HAZE has seen it.
    if (esp->m_Id == 0x48 || (esp->m_Id == 0x15 && !Ps2fxHazeFor(esp))) {
        HazeCutNote(esp);
        RE4DC_ESPSPRITE03_RETURN(PolicySkip);
    }
#endif
#if defined(RE4DC_ESP_CENSUS) && RE4DC_ESP_CENSUS
    ESPCT(3);
    {   // ESP_CENSUS: sprites reaching the emit, by (id, owner, tex), the 12 largest every 120 frames ("espe:")
        struct K { u32 k; u16 n; };
        static K tab[64];
        static u32 frame0, frames;
        if (pG->Frame_cnt != frame0) {
            frame0 = pG->Frame_cnt;
            if (++frames == 120) {
                char buf[240];
                int n = 0;
                for (int c = 0; c < 12; c++) {
                    int b = -1;
                    for (int j = 0; j < 64; j++) if (tab[j].n && (b < 0 || tab[j].n > tab[b].n)) b = j;
                    if (b < 0) break;
                    n += snprintf(buf + n, sizeof(buf) - n, " %06x:%u", (unsigned) tab[b].k, (unsigned) tab[b].n / 120);
                    tab[b].n = 0;
                }
                re4dc_log("espe: f=%u room=%03x id.own.tex:per-frame%s\n", (unsigned) frame0, (unsigned) G_ROOM_ID, buf);
                re4dc_log("espt: per-frame trans=%u body=%u channel_ok=%u emit=%u\n", re4dc_esp_ct[0] / 120,
                          re4dc_esp_ct[1] / 120, re4dc_esp_ct[2] / 120, re4dc_esp_ct[3] / 120);
                re4dc_esp_ct[0] = re4dc_esp_ct[1] = re4dc_esp_ct[2] = re4dc_esp_ct[3] = 0;
                for (int j = 0; j < 64; j++) tab[j].n = 0, tab[j].k = 0;
                frames = 0;
            }
        }
        const u32 key = ((u32) esp->m_Id << 16) | ((u32) esp->info.owner << 8) | esp->m_Tex_id;
        for (int j = 0; j < 64; j++) {
            if (tab[j].n == 0 || tab[j].k == key) { tab[j].k = key; tab[j].n++; break; }
        }
    }
#endif
    const TEXDescriptor* td = TEXGet(tw->pTpl, RE4DC_FX_FLIP_PTN(esp->m_Ptn_no, tw->pTpl->numDescriptors));   // effects30.mk
    const TEXHeader* th = td->textureHeader;
    Re4dcEffectSprite s;
    s.image.pixels = th->data;
    s.image.palette = NULL;
    s.image.width = th->width;
    s.image.height = th->height;
    s.image.format = th->format;
    s.image.palette_format = 0xffffffffU;
    s.image.palette_bytes = 0;
    if (td->CLUTHeader) {
        s.image.palette = td->CLUTHeader->data;
        s.image.palette_format = td->CLUTHeader->format;
        s.image.palette_bytes = td->CLUTHeader->numEntries * 2;
    }
    f32 P[7], V[6];
    RE4DC_GXF_GET_PROJECTION(P);
    RE4DC_GXF_GET_VIEWPORT(V);
    if (V[2] <= 0.0f || V[3] <= 0.0f) {
        RE4DC_ESPSPRITE03_RETURN(UnsupportedBeforePublication);
    }
    const int ortho = P[0] != 0.0f;
    const f32 near_d = ortho ? 0.0f : P[6] / (P[5] - 1.0f), far_d = ortho ? 0.0f : P[6] / P[5];
    const Mtx& m = esp->m_Mat;
#if RE4DC_PS2_FX_STAGE1
    const Ps2fxStatic* fixed=ortho ? NULL : Ps2fxStaticFor(esp);
    f32 fixed_dx=0.0f,fixed_dy=0.0f,fixed_ox=0.0f,fixed_oy=0.0f;
    if(fixed && tw->pAnm) {
        fixed_dx=fixed->ps_x/fixed->gc_x-1.0f; fixed_dy=fixed->ps_y/fixed->gc_y-1.0f;
        fixed_ox=tw->pAnm->Cx ? -(f32)tw->pAnm->Cx/tw->pAnm->Width : -0.5f;
        fixed_oy=tw->pAnm->Cy ? (f32)tw->pAnm->Cy/tw->pAnm->Height-1.0f : -0.5f;
    } else fixed=NULL;
#endif
#if RE4DC_PS2_FX_POPULATION
    f32 shift_x = 0.0f, shift_y = 0.0f, shift_z = 0.0f;
    if (!ortho && population_selected) {
        // Remap only the camera-relative centre. Quad dimensions and every source particle field stay intact.
        const f32 change = population_haze->range / population_haze->gc_range - 1.0f;
        shift_x = (m[0][0] * 0.5f + m[0][1] * 0.5f + m[0][2] + m[0][3]) * change;
        shift_y = (m[1][0] * 0.5f + m[1][1] * 0.5f + m[1][2] + m[1][3]) * change;
        shift_z = (m[2][0] * 0.5f + m[2][1] * 0.5f + m[2][2] + m[2][3]) * change;
    }
#endif
#if RE4DC_WATER45_NATIVE
    f32 corner[4][3];
#endif
    for (int i = 0; i < 4; ++i) {
        f32 x = m[0][0] * cx[i] + m[0][1] * cy[i] + m[0][2] + m[0][3]
#if RE4DC_PS2_FX_POPULATION
            + shift_x
#endif
            ;
        f32 y = m[1][0] * cx[i] + m[1][1] * cy[i] + m[1][2] + m[1][3]
#if RE4DC_PS2_FX_POPULATION
            + shift_y
#endif
            ;
        f32 z = m[2][0] * cx[i] + m[2][1] * cy[i] + m[2][2] + m[2][3]
#if RE4DC_PS2_FX_POPULATION
            + shift_z
#endif
            ;
#if RE4DC_PS2_FX_STAGE1
        if(fixed) {
            x+=ps2fx::anchored_corner_delta(m[0][0],m[0][1],fixed_dx,fixed_dy,cx[i],cy[i],fixed_ox,fixed_oy);
            y+=ps2fx::anchored_corner_delta(m[1][0],m[1][1],fixed_dx,fixed_dy,cx[i],cy[i],fixed_ox,fixed_oy);
            z+=ps2fx::anchored_corner_delta(m[2][0],m[2][1],fixed_dx,fixed_dy,cx[i],cy[i],fixed_ox,fixed_oy);
        }
#endif
        f32 px, py, inv;
        if (ortho) {
            px = P[1] * x + P[2];
            py = P[3] * y + P[4];
            inv = 1.0f;
        } else {
            if (-z < near_d || -z > far_d) {
                RE4DC_ESPSPRITE03_RETURN(PolicySkip); // near/far crossing: drop, never clip
            }
            inv = 1.0f / -z;
            px = (P[1] * x + P[2] * z) * inv;
            py = (P[3] * y + P[4] * z) * inv;
        }
        s.x[i] = (V[2] * 0.5f * px + V[0] + V[2] * 0.5f) * 640.0f / V[2];
        s.y[i] = (-V[3] * 0.5f * py + V[1] + V[3] * 0.5f) * 480.0f / V[3];
        s.z[i] = inv;
        s.u[i] = tw->mtx[0][0] * cu[i] + tw->mtx[0][1] * cv[i] + tw->mtx[0][3];
        s.v[i] = tw->mtx[1][0] * cu[i] + tw->mtx[1][1] * cv[i] + tw->mtx[1][3];
#if RE4DC_WATER45_NATIVE
        corner[i][0] = x;
        corner[i][1] = y;
        corner[i][2] = z;
#endif
    }
#if RE4DC_WATER45_NATIVE
    // WATER45_NATIVE: the GameCube's water writes Z (Espgen45_TransSub GXSetZMode(1, LEQUAL, 1)) before the effect
    // layers, so a sprite wholly under the surface seen from above it is never drawn (r10b's lake mist sheets).
    if (!ortho && re4dc_water45_hides(corner)) {
        RE4DC_ESPSPRITE03_RETURN(Culled);
    }
#endif
#if RE4DC_EFFECT_PS2_HAZE
    const Ps2fxHaze* hz = ortho ? NULL : Ps2fxHazeFor(esp);
    if (hz) {
        // PS2 size: the camera-facing square scaled about its centre (its anchor is the centre: tex 0x1f Cx/Cy 0)
        const f32 mx = (s.x[0] + s.x[1] + s.x[2] + s.x[3]) * 0.25f, my = (s.y[0] + s.y[1] + s.y[2] + s.y[3]) * 0.25f;
        for (int i = 0; i < 4; ++i) {
            s.x[i] = mx + (s.x[i] - mx) * hz->scale;
            s.y[i] = my + (s.y[i] - my) * hz->scale;
        }
        // PS2 colour and fades from the view depth (every corner of the square has the same z)
        const f32 d = 1.0f / s.z[0];
        const Ps2fxEsp15Work* w = &static_cast<cPs2fxEsp15*>(esp)->m_Free;
        f32 fa = (f32) hz->a;
        if (w->Room_del_frame != 0 && w->Room_del_cnt != 0
#if RE4DC_PS2_FX_POPULATION
            && hz->room != 0x112 // PS2 source Work8[3] is zero: no indoor fade for its area-5 haze.
#endif
            ) {
            const u32 cnt = w->Room_del_cnt < w->Room_del_frame ? w->Room_del_cnt : w->Room_del_frame;
            fa *= 1.0f - (f32) cnt / w->Room_del_frame;
        }
        if (d > hz->range * 0.7f) {
            fa *= 1.0f - (d - hz->range * 0.7f) / (hz->range * 0.3f);
        }
#if RE4DC_PS2_FX_ROOMS
        const f32 nf = hz->near_far != 0.0f ? hz->near_far : 3000.0f;
        const f32 nn = hz->near_far != 0.0f ? hz->near_near : 500.0f;
        if (d < nf) {
            const f32 rate = 1.0f - (nf - d) / (nf - nn);
            fa *= rate > 0.0f ? rate : 0.0f;
        }
#else
        if (d < 3000.0f) {
            const f32 rate = 1.0f - (3000.0f - d) / 2500.0f;
            fa *= rate > 0.0f ? rate : 0.0f;
        }
#endif
#if defined(RE4DC_HW_FOG_HAZE) && RE4DC_HW_FOG_HAZE
        {   // HW_FOG_HAZE (hwfog.mk): a haze sprite beyond the room's keep depth is carried by the PVR fog table
            f32 indoor = 1.0f;
            if (w->Room_del_frame != 0 && w->Room_del_cnt != 0) {
                const u32 cnt = w->Room_del_cnt < w->Room_del_frame ? w->Room_del_cnt : w->Room_del_frame;
                indoor = 1.0f - (f32) cnt / w->Room_del_frame;
            }
            if (re4dc_hwfog_haze(hz->room, d, indoor)) {
                RE4DC_ESPSPRITE03_RETURN(PolicySkip);
            }
        }
#endif
#if defined(RE4DC_MIST_CUT)
        if (re4dc_mist_cut & 1) {   // MIST_CUT bit 1: not even the near haze (after the fog rows' notes)
            MistCutNote(1);
            RE4DC_ESPSPRITE03_RETURN(PolicySkip);
        }
#endif
#if defined(RE4DC_HAZE_SPRITE_CUT)
        HazeCutNote(esp);   // HAZE_SPRITE_CUT: not the near haze either (the fog rows above have seen the sprite)
        RE4DC_ESPSPRITE03_RETURN(PolicySkip);
#endif
#if defined(RE4DC_EFFECT_HAZE_LEAN) && (RE4DC_EFFECT_HAZE_LEAN & 2)
        if (RE4DC_HZ(2) && Ps2fxEvery2(hz->room)) {
            fa *= 1.5f;   // M3: the sparse subset carries the drifting blotches
        }
#endif
        u32 hr = hz->r, hg = hz->g, hb = hz->b, ha = fa > 0.0f ? (u32) fa : 0;
        if (!(esp->m_Flg & 4) && EffIsSetFinalCol()) {
            GXColor fin;
            EffGetFinalCol(&fin);
            hr = hr * fin.r >> 8;
            hg = hg * fin.g >> 8;
            hb = hb * fin.b >> 8;
            ha = ha * fin.a >> 8;
        }
        if (ha == 0) {
            RE4DC_ESPSPRITE03_RETURN(PolicySkip);
        }
        s.color = (ha << 24) | (hr << 16) | (hg << 8) | hb;
        s.src = esp->xA5 & 7;
        s.dst = esp->xA6 & 7;
        s.screen = 0;
#if defined(RE4DC_EFFECT_HAZE_LEAN) && (RE4DC_EFFECT_HAZE_LEAN & 4)
        s.pad = RE4DC_HZ(4) ? 1 : 0;   // M2: native_ui draws a haze sprite as an octagon
#else
        s.pad = 0;
#endif
#if RE4DC_TA_BIN_DIAG
        s.pad |= 2;   // TA_BIN_DIAG fill: a PS2 haze sprite
#endif
#if defined(RE4DC_FX_LEVEL)
        if (!FxLevelSprite(esp, &s)) {
            RE4DC_ESPSPRITE03_RETURN(PolicySkip);
        }
#endif
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
        return re4dc_effect_sprite_result(&s);
#else
        re4dc_effect_sprite(&s);
        return;
#endif
    }
#endif
#if defined(RE4DC_HAZE_SPRITE_CUT)
    if (esp->m_Id == 0x15) {
        HazeCutNote(esp);
        RE4DC_ESPSPRITE03_RETURN(PolicySkip);
    }
#endif
#if RE4DC_PS2_FX_STAGE1
    const GXColor draw_col=fixed ? Ps2fxStaticColor(esp,fixed) : s_effect_col;
    u32 r=draw_col.r,g=draw_col.g,b=draw_col.b,a=draw_col.a;
#else
    u32 r = s_effect_col.r, g = s_effect_col.g, b = s_effect_col.b, a = s_effect_col.a;
#endif
    if (!(esp->m_Tool_flg & 0x40)) {
        if (esp->m_Tool_flg & 0x80) { // TEV colour scale 4
            r = r * 4 > 255 ? 255 : r * 4;
            g = g * 4 > 255 ? 255 : g * 4;
            b = b * 4 > 255 ? 255 : b * 4;
        }
        if (esp->m_Tool_flg & 0x20000) { // TEV alpha scale 4
            a = a * 4 > 255 ? 255 : a * 4;
        }
    }
    s.color = (a << 24) | (r << 16) | (g << 8) | b;
    s.src = esp->xA5 & 7;
    s.dst = esp->xA6 & 7;
    s.screen = ortho;
    s.pad = 0;
#if defined(RE4DC_EFFECT_TORCH) && RE4DC_EFFECT_TORCH
    // EFFECT_TORCH: an Esp0e glow's screen copy is drawn at its source's view depth (Esp0e_HideCheck's
    // 150 mm in front) with the depth test on, in place of the GameCube's Z-buffer peek (GXPeekZ has no
    // PVR equivalent): scenery in front hides it per pixel.
    if (re4dc_esp0e_glow && ortho) {
        const f32 d = re4dc_esp0e_depth > 10.0f ? re4dc_esp0e_depth : 10.0f;
        for (int i = 0; i < 4; ++i) {
            s.z[i] = 1.0f / d;
        }
        s.screen = 0;
        ++re4dc_esp0e_drawn;
        static u32 s_glow_window = ~0U;
        if (pG->Frame_cnt / 120 != s_glow_window) {   // the running total, once per 120 frames with a glow
            s_glow_window = pG->Frame_cnt / 120;
            re4dc_log("torch glow: frame=%u room=%03x owner=%02x tex=%02x total=%u argb=%08x x=%d..%d y=%d..%d d=%d\n",
                      (unsigned) pG->Frame_cnt, (unsigned) G_ROOM_ID, (unsigned) esp->info.owner,
                      (unsigned) esp->m_Tex_id, (unsigned) re4dc_esp0e_drawn, (unsigned) s.color, (int) s.x[0],
                      (int) s.x[2], (int) s.y[0], (int) s.y[2], (int) d);
        }
    }
#endif
#if RE4DC_TA_BIN_DIAG
    if (esp->info.owner == 0xD0 && esp->m_Id == 0x48 &&   // TA_BIN_DIAG fill: a GameCube mist sheet (EFFECT_HAZE_LEAN M1's)
        (esp->m_Tex_id == 0xf6 || esp->m_Tex_id == 0xcb || esp->m_Tex_id == 0xd0 || esp->m_Tex_id == 0xf3 ||
         esp->m_Tex_id == 0x33)) {
        s.pad |= 4;
    }
#endif
#if defined(RE4DC_FX_LEVEL)
    if (!FxLevelSprite(esp, &s)) {
        RE4DC_ESPSPRITE03_RETURN(PolicySkip);
    }
#endif
#if defined(RE4DC_NATIVE_DRAW_OUTCOMES) && RE4DC_NATIVE_DRAW_OUTCOMES
    return re4dc_effect_sprite_result(&s);
#else
    re4dc_effect_sprite(&s);
#endif

#undef RE4DC_ESPSPRITE03_RETURN
