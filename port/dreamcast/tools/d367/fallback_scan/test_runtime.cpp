// Synthetic bytes are supplied by test_runtime.py. Include the production
// implementation so admission, meshlet decoding, light dispatch, baked colour
// unpacking and the packet emitter are the actual functions under test.
#include <cassert>
#include <cstdio>
#include <fstream>
#include <iterator>
#include <vector>
#include "../../../game/platform/native_actor_fast.cpp"

static pvr_vertex_t packet29[1400];
static std::vector<pvr_vertex_t> emitted29;
static unsigned status29;
static int model_id29 = 0x12;
extern "C" int re4dc_actor_model_id(const void*) { return model_id29; }
extern "C" void re4dc_log(const char*, ...) {}
extern "C" int re4dc_model_packet_reserve(const Re4dcModelPart*, Re4dcModelPacket* p) {
    *p = {packet29, 1400, 1, 1}; return 1;
}
extern "C" int re4dc_model_packet_begin(const Re4dcModelPart* p, Re4dcModelPacket* q) {
    return re4dc_model_packet_reserve(p, q);
}
extern "C" void re4dc_model_packet_commit(unsigned n) { emitted29.insert(emitted29.end(), packet29, packet29 + n); }
extern "C" void re4dc_model_packet_abort() { assert(false); }
extern "C" int re4dc_model_packet_streaming() { return 1; }
extern "C" void re4dc_model_result(unsigned why, unsigned, unsigned) { status29 = why; }
extern "C" int re4dc_model_defer_part(const Re4dcModelPart*) { return 0; }
extern "C" void re4dc_model_next_header_pcw(unsigned, unsigned) {}
extern "C" int re4dc_actor_model_source(const void*, Re4dcActorSource*) { return 0; }
extern "C" int re4dc_actor_model_prelit(const void*, const void*) { return 0; }
extern "C" int re4dc_actor_model_class(const void*, const void*) { return 0; }
extern "C" int re4dc_skin_materialize(const void*, const float*) { return 0; }
int pvr_prim(const void*, std::size_t) { assert(false); return -1; }

static std::vector<unsigned char> read29(const char* path) {
    std::ifstream in(path, std::ios::binary); assert(in);
    return {std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>()};
}
static SourceLighting light29() {
    SourceLighting s{};
    s.enable = 1; s.diffuse = 2; s.attenuation = 2; s.mask = 1;
    for (unsigned c = 0; c < 3; ++c) {
        s.ambient[c] = 64; s.material[c] = 128; s.lights[0].color[c] = 64;
    }
    s.normal_matrix[0] = s.normal_matrix[5] = s.normal_matrix[10] = 1;
    s.lights[0].position[2] = 1.0e12f;
    return s;
}
static Re4dcModelPart part29(std::vector<unsigned char>& bytes, SourceLighting& light) {
    Re4dcModelPart p{};
    p.model = &light; p.info = &light; p.part = bytes.data() + 224;
    p.positions = bytes.data() + 96; p.normals = bytes.data() + 128;
    p.colors = bytes.data() + 144; p.uv = bytes.data() + 160;
    p.stream = bytes.data() + 256; p.stream_bytes = bytes.size() - 256;
    p.flags = 0xa0000000U; p.shift = 4; p.position_stride = 8;
    p.normal_stride = 4; p.normal_shift = 6; p.position_count = p.normal_count = 3;
    p.alpha_state = 73; p.lighting = &light;
    p.modelview[0] = p.modelview[5] = p.modelview[10] = 1;
    p.modelview[11] = -10;
    p.projection[1] = p.projection[3] = 1;
    p.projection[5] = -1.f/99; p.projection[6] = -100.f/99;
    p.viewport[2] = 640; p.viewport[3] = 480; p.viewport[5] = 1;
    p.image.width = p.image.height = 32;
    return p;
}
static std::vector<pvr_vertex_t> draw29(const Re4dcModelPart& p) {
    static std::vector<unsigned char> workspace29(256 * 1024);
    emitted29.clear(); status29 = 99;
    re4dc_actor_lod(0, 0);
    re4dc_actor_frame(workspace29.data(), workspace29.size());
    assert(qualifies(p));
    assert(re4dc_actor_submit(&p) == 1);
    assert(status29 == 0 && emitted29.size() == 96);
    return emitted29;
}
static void geometry29(const std::vector<pvr_vertex_t>& a, const std::vector<pvr_vertex_t>& b) {
    assert(a.size() == b.size());
    for (unsigned i = 0; i < a.size(); ++i) {
        assert(a[i].flags == b[i].flags);
        assert(a[i].x == b[i].x && a[i].y == b[i].y && a[i].z == b[i].z);
        assert(a[i].u == b[i].u && a[i].v == b[i].v);
        assert((a[i].argb >> 24) == (b[i].argb >> 24));
    }
}
int main(int argc, char** argv) {
    assert(argc == 5);
    auto original = read29(argv[1]), converted = read29(argv[2]), probe = read29(argv[3]), vertex = read29(argv[4]);
    const auto saved = converted;
    SourceLighting light = light29();
    Re4dcModelPart before = part29(original, light), after = part29(converted, light);
    assert(!blob_of(before) && blob_of(after));
    assert(!re4dc_actor_stream_encoded(before.stream, before.stream_bytes));
    assert(re4dc_actor_stream_encoded(after.stream, after.stream_bytes));
    const BlobHeader& blob = *blob_of(after);
    assert(blob.meshlets == 1 && blob.color_index == 0 && uv_excess_bits(blob) == 0);
    assert(blob.flags == (kHasCi | kHasBake) && blob.levels == 0 && blob.lod4 == 0);
    Frame frame{}; frame.nq = 1.0f/64;
    const float center[3] = {};
#if !RE4DC_ACTOR_LIGHT_FAST_ONLY
    Lights old, baked;
    assert(probe_eligible(before));
    assert(!probe_lights(before, frame, old));
    assert(!build_lights(before, frame, center, old));
    assert(!part_lights(before, frame, center, old));
    const auto old_draw = draw29(before);
    const unsigned slow = stats.slow_light_vertices, normals = stats.normals_lit, declined = probe_stats.declined;
    assert(slow == 3);
    const auto baked_draw = draw29(after);
#if RE4DC_FALLBACK_SCAN29
    assert(RE4DC_PART_LIGHTS(after, frame, center, baked));
    assert(baked.fast && !baked.constant && baked.scan29_bake);
    assert(stats.slow_light_vertices == slow && stats.normals_lit == normals && probe_stats.declined == declined);
    assert(saved == converted);  // ordinary bake_prepare must not rewrite the offline record
    geometry29(old_draw, baked_draw);
    for (unsigned i = 0; i < old_draw.size(); ++i) for (unsigned shift : {0U, 8U, 16U}) {
        const int a = (old_draw[i].argb >> shift) & 255, b = (baked_draw[i].argb >> shift) & 255;
        assert(std::abs(a - b) <= 7);  // RGB565 quantization, same captured axis light
    }
    // Current live colour/flash energy changes the output, without exact or probe work.
    light.lights[0].color[0] = 128;
    auto flash = draw29(after);
    assert(flash[0].argb != baked_draw[0].argb);
    assert(stats.slow_light_vertices == slow && stats.normals_lit == normals && probe_stats.declined == declined);
    geometry29(flash, baked_draw);
    light = light29();
    // Reuse the same Lights with MEMSET_LEAN/NO_CLEAR: old dispatch must clear the pointer.
    assert(RE4DC_PART_LIGHTS(after, frame, center, baked) && baked.scan29_bake);
    assert(!RE4DC_PART_LIGHTS(before, frame, center, baked) && !baked.scan29_bake);
    // An unsupported mode uses the old evaluator and leaves the immutable offline palette intact.
    light.diffuse = 1;
    auto unsupported = draw29(after);
    assert(stats.slow_light_vertices > slow && saved == converted);
    light = light29();
    assert(draw29(after)[0].argb == baked_draw[0].argb && saved == converted);
    // Special Leon/headroom policies retain their existing selected evaluator.
    for (unsigned marker : {3U, 7U}) {
        light = light29(); light.normal_matrix[marker] = 1.0e30f;
        const bool prior = part_lights(after, frame, center, old);
        assert(RE4DC_PART_LIGHTS(after, frame, center, baked) == prior && !baked.scan29_bake);
        draw29(after); assert(saved == converted);
    }
    light = light29();
    // Untagged FE data retains the old dispatch (the original stream was converted by draw29).
    assert(!RE4DC_PART_LIGHTS(before, frame, center, baked) && !baked.scan29_bake);
    // Independent probe flag, actor-class decline: old fold is cheap but probe is ineligible.
    model_id29 = 0x41;
    for (unsigned c = 0; c < 3; ++c) light.material[c] = 255;
    Re4dcModelPart pp = part29(probe, light);
    assert(!probe_eligible(pp) && !probe_lights(pp, frame, old));
    assert(RE4DC_PART_LIGHTS(pp, frame, center, baked) && baked.scan29_bake);
    draw29(pp);
    // Static per-vertex RGB: old fold + probe decline; production baked path preserves constant alpha.
    model_id29 = 0x12; light = light29(); light.ambient_vertex = light.material_vertex = 1;
    Re4dcModelPart vp = part29(vertex, light);
    assert(!probe_eligible(vp) && !build_lights(vp, frame, center, old));
    assert(RE4DC_PART_LIGHTS(vp, frame, center, baked) && baked.scan29_bake);
    auto vc = draw29(vp); assert(vc[0].argb != vc[1].argb);
    for (const auto& v : vc) assert((v.argb >> 24) == 73);
    // Runtime alpha/material policy is narrower than source qualification.
    vp.alpha_state |= 256;
    assert(!RE4DC_PART_LIGHTS(vp, frame, center, baked) && !baked.scan29_bake);
    vp.alpha_state = 73; vp.blend = 1;
    assert(!RE4DC_PART_LIGHTS(vp, frame, center, baked) && !baked.scan29_bake);
#else
    assert(stats.slow_light_vertices > slow && probe_stats.declined > declined);
    assert(saved == converted);  // no fast fold means no ordinary rebake
    geometry29(old_draw, baked_draw);
    for (unsigned i = 0; i < old_draw.size(); ++i) assert(old_draw[i].argb == baked_draw[i].argb);
#endif
#else
    // FAST_ONLY dispatch deliberately owns the render policy. Build29 fields
    // are never consumed in this configuration, including MEMSET_LEAN=1.
    auto a = draw29(before), b = draw29(after);
    geometry29(a, b);
    for (unsigned i = 0; i < a.size(); ++i) assert(a[i].argb == b[i].argb);
    assert(saved == converted);
#if RE4DC_FALLBACK_SCAN29
    Lights unused;
    assert(unused.scan29_bake == nullptr);
    for (unsigned gain : unused.scan29_gain) assert(gain == 0);
#endif
#endif
    std::printf("PASS production FE admission/draw SCAN29=%d FAST_ONLY=%d MEMSET_LEAN=%d HEADROOM=%d; source geometry/UV/alpha retained\n",
                RE4DC_FALLBACK_SCAN29, RE4DC_ACTOR_LIGHT_FAST_ONLY, RE4DC_MEMSET_LEAN, RE4DC_LEON_LIGHT_HEADROOM);
}
