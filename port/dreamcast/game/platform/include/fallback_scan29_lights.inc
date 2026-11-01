// Own dispatch block, after existing RE4DC_PART_LIGHTS choices. Ordinary data
// and every unsupported dynamic state retain the selected pre-Build29 path.
bool scan29_part_lights(const Re4dcModelPart& p, const Frame& f, const float center[3], Lights& L) {
    L.scan29_bake = nullptr;
#if !defined(RE4DC_ACTOR_PRELIT) || RE4DC_ACTOR_PRELIT
    const auto* bake = re4dc::fallback29::tagged(p.stream, p.stream_bytes);
    unsigned gain[3];
    if (bake && p.lighting && p.blend == 0 && p.alpha_state <= 255U &&
        p.material_flags == 0 && !p.mask.pixels &&
        re4dc::fallback29::gains(*p.lighting, *bake, gain)) {
        lights_reset(L);
        L.fast = true;
        L.source = p.lighting;
        L.scan29_bake = bake;
        for (unsigned c = 0; c < 3; ++c) L.scan29_gain[c] = gain[c];
        return true;
    }
#endif
    return RE4DC_PART_LIGHTS(p, f, center, L);
}
#undef RE4DC_PART_LIGHTS
#define RE4DC_PART_LIGHTS scan29_part_lights
