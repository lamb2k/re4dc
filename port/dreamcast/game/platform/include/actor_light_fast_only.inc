// Included inside native_actor_fast.cpp's namespace after the shared live probe.
// A bounded light set is sampled once at a part centre; the vertex pass only
// writes this colour or multiplies it by static RGB. No normal matrix is used.
Re4dcActorLight25Stats light25_stats{};
inline void light25_add(unsigned& value, unsigned n = 1U) {
    value = n > ~0U - value ? ~0U : value + n;
}
inline float light25_finite(float x) {
    return re4dc::render::is_finite(x) ? x : 0.0f;
}
inline float light25_mean(unsigned diffuse, float view_dot, bool residual) {
    if (!diffuse) return 1.0f;
    const float weight = residual ? 0.25f : 0.30f;
    return diffuse == 2U ? std::max(0.0f, weight * (1.0f + view_dot)) : weight * view_dot;
}
bool fast_only_lights(const Re4dcModelPart& p, const Frame&, const float center[3], Lights& L) {
    const SourceLighting& S = *p.lighting;
    lights_reset(L);
    L.source = &S;
    L.fast = L.constant = true;
    light25_add(light25_stats.parts);
    if (S.ambient_vertex || S.material_vertex)
        light25_add(light25_stats.avoided[RE4DC_AL25_VERTEX_COLOUR]);
    bool old_caps = true;
    float scale[3], ambient[3];
    for (unsigned c = 0; c < 3; ++c) {
        old_caps &= S.material[c] * S.tev_scale >= 255.0f;
        scale[c] = light25_finite((S.material_vertex ? 255.0f : float(S.material[c])) * S.tev_scale);
        ambient[c] = S.enable ? S.ambient[c] * (1.0f / 255.0f) : 1.0f;
    }
    if (S.enable && (S.diffuse != 2U || !old_caps))
        light25_add(light25_stats.avoided[RE4DC_AL25_DIFFUSE_SCALE]);
    const bool leon = S.normal_matrix[3] == 1.0e30f;
#if RE4DC_LEON_LIGHT_HEADROOM
    // Compensation for the source's 2x Leon textures is part-level too.
    // An outside-owner half-scale record already carries its x0.5 in tev_scale.
    if (leon) for (float& c : scale) c *= 0.5f;
#endif
    bool have_probe = false;
#if RE4DC_ACTOR_PROBE_LIGHT
    bool probe_model = leon;
#if RE4DC_ACTOR_PROBE_LIGHT >= 2
    if (!leon) {
        const int id = re4dc_actor_model_id(p.model);
        probe_model = id >= 0x10 && id <= 0x20;
#if RE4DC_GANADO_LIT_TOGGLE
        probe_model = probe_model && re4dc_ganlit_mode != 0U;
#endif
    }
#endif
    if (S.enable && probe_model) {
        const ProbeEntry& e = probe_of(p); // live lights and the shared shadow probe
        bool old_normal = true;
        if (leon) {
            const float* m = p.modelview;
            const float determinant = m[0] * (m[5] * m[10] - m[6] * m[9]) +
                m[1] * (m[6] * m[8] - m[4] * m[10]) + m[2] * (m[4] * m[9] - m[5] * m[8]);
            old_normal = determinant != 0.0f && re4dc::render::is_finite(determinant);
            if (!old_normal) light25_add(light25_stats.avoided[RE4DC_AL25_NORMAL_BASIS]);
        }
        if (S.ambient_vertex || S.material_vertex || S.diffuse != 2U || !old_caps || !old_normal || !e.ok)
            light25_add(light25_stats.avoided[RE4DC_AL25_PROBE_DECLINE]);
        if (e.ok) {
            have_probe = true;
            L.probe = true;
            L.count = 1;
            L.view_dot[0] = e.view_dot;
            const float mean = light25_mean(S.diffuse, e.view_dot, false);
            for (unsigned c = 0; c < 3; ++c) {
                ambient[c] = e.amb[c] + mean * e.dcol[c];
#if RE4DC_LEON_LIGHT_FILL
                if (leon) ambient[c] += (0.6f * float(RE4DC_LEON_LIGHT_FILL) / 100.0f) * (e.dcol[c] + e.amb[c]);
#endif
#if RE4DC_GANADO_LIT_FILL
                if (!leon && ganlit_fill > 0)
                    ambient[c] += (0.6f * float(ganlit_fill) / 100.0f) * (e.dcol[c] + e.amb[c]);
#endif
            }
        }
    }
#endif
    if (S.enable && !have_probe) {
        const float* m = p.modelview;
        const float px = m[0] * center[0] + m[1] * center[1] + m[2] * center[2] + m[3];
        const float py = m[4] * center[0] + m[5] * center[1] + m[6] * center[2] + m[7];
        const float pz = m[8] * center[0] + m[9] * center[1] + m[10] * center[2] + m[11];
        const float distance2 = px * px + py * py + pz * pz;
        const float inverse = distance2 > 0.0f && re4dc::render::is_finite(distance2) ? -1.0f / std::sqrt(distance2) : 0.0f;
        struct Candidate { float rgb[3], view_dot, weight; } chosen[3];
        unsigned significant = 0;
        for (unsigned i = 0; i < 8; ++i) {
            if (!(S.mask & (1U << i))) continue;
            const SourceLight& s = S.lights[i];
            float lx = s.position[0] - px, ly = s.position[1] - py, lz = s.position[2] - pz;
            const float d2 = lx * lx + ly * ly + lz * lz;
            if (!re4dc::render::is_finite(d2)) continue;
            const float d = std::sqrt(d2);
            if (d > 0.0f) { const float r = 1.0f / d; lx *= r; ly *= r; lz *= r; }
            else { lx = 0.0f; ly = 0.0f; lz = 1.0f; }
            float attenuation = 1.0f;
            if (S.attenuation == 1U) {
                const float cosine = std::max(0.0f, lx * s.direction[0] + ly * s.direction[1] + lz * s.direction[2]);
                const float angular = std::max(0.0f, s.a[0] + s.a[1] * cosine + s.a[2] * cosine * cosine);
                const float denominator = s.k[0] + s.k[1] * d + s.k[2] * d2;
                attenuation = denominator > 0.0f ? angular / denominator : 0.0f;
            }
            Candidate candidate;
            for (unsigned c = 0; c < 3; ++c)
                candidate.rgb[c] = light25_finite(s.color[c] * (1.0f / 255.0f) * attenuation);
            candidate.weight = std::max(candidate.rgb[0], std::max(candidate.rgb[1], candidate.rgb[2]));
            if (candidate.weight <= 1.0f / 1024.0f) continue;
            candidate.view_dot = light25_finite((lx * px + ly * py + lz * pz) * inverse);
            ++significant;
            unsigned at = 0;
            while (at < L.count && candidate.weight <= chosen[at].weight) ++at;
            if (L.count == 3U) {
                const Candidate& dropped = at == 3U ? candidate : chosen[2];
                const float mean = light25_mean(S.diffuse, dropped.view_dot, true);
                for (unsigned c = 0; c < 3; ++c) ambient[c] += mean * dropped.rgb[c];
            } else ++L.count;
            if (at < 3U) {
                for (unsigned j = L.count - 1U; j > at; --j) chosen[j] = chosen[j - 1U];
                chosen[at] = candidate;
            }
        }
        if (significant > 3U) light25_add(light25_stats.avoided[RE4DC_AL25_LIGHT_OVERFLOW]);
        for (unsigned l = 0; l < L.count; ++l) {
            L.view_dot[l] = chosen[l].view_dot;
            const float mean = light25_mean(S.diffuse, chosen[l].view_dot, false);
            for (unsigned c = 0; c < 3; ++c) ambient[c] += mean * chosen[l].rgb[c];
        }
    }
    L.constant_rgb = 0;
    for (unsigned c = 0; c < 3; ++c) {
        const float value = light25_finite(ambient[c] * scale[c]);
        const float gain = value * (65536.0f / 255.0f);
        L.colour25.gain[c] = gain >= 16777215.0f ? 0x00FFFFFFU : gain > 0.0f ? unsigned(gain + 0.5f) : 0U;
        L.constant_rgb = (L.constant_rgb << 8) | channel(value);
    }
    L.colour25.rgb = L.constant_rgb;
    ++stats.light_sets;
    return true;
}
