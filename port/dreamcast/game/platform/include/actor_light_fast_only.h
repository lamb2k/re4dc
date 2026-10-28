#pragma once
/* Build 25. Render-only, default off. The reason order is part of the QA ABI. */
#if defined(RE4DC_ACTOR_LIGHT_FAST_ONLY) && RE4DC_ACTOR_LIGHT_FAST_ONLY
enum Re4dcActorLight25Reason {
    RE4DC_AL25_VERTEX_COLOUR,
    RE4DC_AL25_DIFFUSE_SCALE,
    RE4DC_AL25_LIGHT_OVERFLOW,
    RE4DC_AL25_PROBE_DECLINE,
    RE4DC_AL25_NORMAL_BASIS,
    RE4DC_AL25_REASONS
};
struct Re4dcActorLight25Stats {
    unsigned parts;             /* part folds, including generic model draws */
    unsigned fallback_parts;    /* fast-only dispatch invariant; MUST remain 0 */
    unsigned avoided[RE4DC_AL25_REASONS]; /* former declines, may overlap */
    unsigned flat_vertices, multiply_vertices; /* native actor meshlet inputs */
};
/* RGB is the constant non-vertex output; Q16 gain is intentionally NOT clamped
 * to 1.0 before a baked/source RGB multiply. 0x00ffffff bounds gain to <256;
 * gain*255+32768 still fits unsigned32. */
struct Re4dcActorLight25Colour { unsigned rgb, gain[3]; };
struct Re4dcModelPart;
extern "C" {
void re4dc_actor_light25_snapshot(Re4dcActorLight25Stats* out);
/* Same bounded part fold for representation fallbacks. Null centre = origin. */
unsigned re4dc_actor_light25_part_rgb(const Re4dcModelPart*, const float centre[3]);
void re4dc_actor_light25_part_colour(const Re4dcModelPart*, const float centre[3], Re4dcActorLight25Colour*);
}
/* One precomputed Q16 gain times a static/baked vertex RGB, then final clamp.
 * No normal, palette, light record or lighting evaluator is read here.
 * 1.0 (65536) preserves white exactly; callers own source alpha. */
inline unsigned re4dc_actor_light25_multiply(const Re4dcActorLight25Colour& colour, const unsigned char* c) {
    unsigned out = 0;
    for (unsigned channel = 0; channel < 3; ++channel) {
        const unsigned value = (colour.gain[channel] * c[channel] + 32768U) >> 16;
        out |= (value > 255U ? 255U : value) << (16U - channel * 8U);
    }
    return out;
}
#endif
