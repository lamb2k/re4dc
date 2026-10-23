// actor_test.py substitutes the complete production TU and byte-extracted
// dispatch/reset bodies. Only model-source lookup and hardware emit boundaries
// are fixtures. This does not execute the full actor draw or a Dreamcast.
#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <initializer_list>
#include "@NATIVE_SOURCE@"

static unsigned checks, cases, log_calls;
static Re4dcActorSource fixture_source{};
static bool source_available = true;
#define CHECK(x) do { ++checks; if (!(x)) { std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #x); std::exit(2); } } while (0)
static void test_case(const char* name) { ++cases; std::printf("CASE %s\n", name); }
extern "C" int re4dc_actor_model_source(const void*, Re4dcActorSource* out) {
    if (!source_available) return 0;
    *out = fixture_source; return 1;
}
extern "C" void re4dc_log(const char*, ...) { ++log_calls; }

struct BlobFixture {
    alignas(32) std::array<u8, 1024> bytes{};
    alignas(8) short positions[16][4]{};
    Re4dcModelPart p{};
    static constexpr unsigned size = 512;
    BlobFixture(unsigned capacity = 1024) {
        auto& h = header();
        h.magic = kMagic; h.version = kVersion; h.meshlets = 1;
        h.rec4 = 16; h.idx4 = 64; h.lod4 = 80;
        meshlet().n = Counts::of(3, 3, 1);
        positions[0][0] = 0; positions[0][1] = 0;
        positions[1][0] = 1000; positions[1][1] = 0;
        positions[2][0] = 0; positions[2][1] = 1000;
        for (unsigned i = 0; i < 16; ++i) records()[i * 3] = u16(i);
        set_indices({0, 1, 130});
        p.stream = bytes.data(); p.stream_bytes = capacity;
        p.positions = reinterpret_cast<const u8*>(positions);
        p.position_stride = 8; p.position_count = 16;
        p.cull = 2; p.blend = 0;
        fixture_source = {p.positions, p.positions, 16, 16, 8, 0};
    }
    BlobHeader& header() { return *reinterpret_cast<BlobHeader*>(bytes.data()); }
    MeshletInfo& meshlet() { return *reinterpret_cast<MeshletInfo*>(bytes.data() + sizeof(BlobHeader)); }
    u16* records() { return reinterpret_cast<u16*>(bytes.data() + header().rec4 * 4U); }
    void set_indices(std::initializer_list<u8> indices) {
        std::copy(indices.begin(), indices.end(), bytes.data() + header().idx4 * 4U);
        meshlet().n = Counts::of(meshlet().n.vertices(), indices.size(), indices.size() / 3);
    }
    void set_lod(std::initializer_list<u8> indices, unsigned vertices = 3) {
        header().levels = 1;
        auto* lv = reinterpret_cast<LevelInfo*>(bytes.data() + header().lod4 * 4U);
        *lv = {1.0f, 88, 96};
        auto* ml = reinterpret_cast<MeshletLevel*>(bytes.data() + lv->table4 * 4U);
        *ml = {Counts::of(vertices, indices.size(), indices.size() / 3), 0, 0};
        std::copy(indices.begin(), indices.end(), bytes.data() + lv->lists4 * 4U);
    }
    const AbcCone* build() {
        fixture_source.positions = reinterpret_cast<const u8*>(positions);
        fixture_source.position_count = p.position_count;
        abc_build(p, size, 2);
        return abc_table(p.stream, p.stream_bytes);
    }
#if RE4DC_BACKFACE_CONE_FRONT
    const AbcFrontRecord* front() { return abc_front_table(p.stream, p.stream_bytes); }
    void no_front() { CHECK(front()); CHECK(front()[0].min_normal == 0.0f); }
#endif
};

#if RE4DC_BACKFACE_CONE_FRONT
// A nonoverlapping 8x8 planar grid: 64 transformed vertices, 98 independent
// triangle strips, 294 indices. It meets the measured dense-strip policy.
struct DenseFixture {
    alignas(32) std::array<u8, 2048> bytes{};
    alignas(8) short positions[64][4]{};
    Re4dcModelPart p{};
    DenseFixture() {
        auto& h = *reinterpret_cast<BlobHeader*>(bytes.data());
        h.magic = kMagic; h.version = kVersion; h.meshlets = 1; h.rec4 = 16; h.idx4 = 128;
        auto& m = *reinterpret_cast<MeshletInfo*>(bytes.data() + sizeof(BlobHeader));
        m.n = Counts::of(64, 294, 98);
        auto* records = reinterpret_cast<u16*>(bytes.data() + 64);
        for (unsigned y = 0; y < 8; ++y) for (unsigned x = 0; x < 8; ++x) {
            const unsigned i = y * 8 + x;
            positions[i][0] = short(x * 512); positions[i][1] = short(y * 512);
            records[i * 3] = u16(i);
        }
        auto* index = bytes.data() + 512; unsigned n = 0;
        for (unsigned y = 0; y < 7; ++y) for (unsigned x = 0; x < 7; ++x) {
            const unsigned a = y * 8 + x, b = a + 1, c = a + 8, d = c + 1;
            index[n++] = u8(a); index[n++] = u8(b); index[n++] = u8(c | 128U);
            index[n++] = u8(b); index[n++] = u8(d); index[n++] = u8(c | 128U);
        }
        p.stream = bytes.data(); p.stream_bytes = bytes.size(); p.positions = reinterpret_cast<const u8*>(positions);
        p.position_stride = 8; p.position_count = 64; p.cull = 2;
    }
    const AbcCone* build() { abc_build(p, 1024, 2); return abc_table(p.stream, p.stream_bytes); }
    const AbcFrontRecord* front() { return abc_front_table(p.stream, p.stream_bytes); }
};
#endif

static std::uint64_t hash_bytes(const void* ptr, unsigned n) {
    auto* p = static_cast<const u8*>(ptr); std::uint64_t h = 1469598103934665603ULL;
    for (unsigned i = 0; i < n; ++i) h = (h ^ p[i]) * 1099511628211ULL;
    return h;
}
static void producer_tests() {
    test_case("legacy-tail-and-optional-proof-fit");
    for (unsigned capacity : {544U, 556U, 572U, 1024U}) {
        BlobFixture f(capacity); const auto* cone = f.build(); CHECK(cone && cone->k);
        const unsigned at = abc_tail_at(capacity, 1);
        CHECK(cone->a[0] == 0 && cone->a[1] == 0 && cone->a[2] == 32767);
        unsigned cls = 0; CHECK(abc_table(f.p.stream, capacity, &cls) == cone && cls == 2);
        std::printf("ABC1 capacity=%u hash=%016llx\n", capacity,
                    static_cast<unsigned long long>(hash_bytes(f.bytes.data() + at, sizeof(AbcTail) + sizeof(AbcCone))));
#if RE4DC_BACKFACE_CONE_FRONT
        if (capacity < 572U) CHECK(!f.front());
        else {
            CHECK(f.front() && f.front()[0].min_normal == 524288.0f);
            CHECK(f.front()[0].extent[0] == 500 && f.front()[0].extent[1] == 500 && f.front()[0].extent[2] == 0);
            CHECK(f.front()[0].reserved == 0);
        }
#endif
    }
    test_case("legacy-insufficient-capacity");
    { BlobFixture f(540); CHECK(!f.build()); }

#if RE4DC_BACKFACE_CONE_FRONT
    test_case("optional-proof-validation-preserves-abc1");
    {
        BlobFixture f; CHECK(f.build()); CHECK(f.front());
        auto* proof_header = reinterpret_cast<AbcTail*>(f.bytes.data() + abc_front_at(f.p.stream_bytes, 1));
        const AbcTail saved = *proof_header;
        for (unsigned field = 0; field < 4; ++field) {
            *proof_header = saved; reinterpret_cast<u32*>(proof_header)[field] ^= 1;
            CHECK(!f.front()); CHECK(abc_table(f.p.stream, f.p.stream_bytes));
        }
        *proof_header = saved; CHECK(f.front());
        f.header().flags ^= kLodPending; CHECK(f.front());
        f.header().color_index ^= 1; CHECK(!f.front()); CHECK(!abc_table(f.p.stream, f.p.stream_bytes));
    }
    test_case("integer-cross-keeps-cancellation-normal");
    {
        BlobFixture f;
        f.positions[1][0] = 5363; f.positions[1][1] = 5362;
        f.positions[2][0] = 5362; f.positions[2][1] = 5361;
        f.positions[3][0] = 1000; f.positions[3][1] = 0;
        f.positions[4][0] = 0; f.positions[4][1] = -1000;
        f.meshlet().n = Counts::of(5, 6, 2); f.set_indices({0, 1, 130, 0, 3, 132});
        CHECK(f.build() && f.front()); CHECK(f.front()[0].min_normal == 1.0f);
    }
    test_case("degenerate-in-base-or-any-lod");
    {
        BlobFixture f; f.set_indices({0, 1, 130, 0, 0, 128}); CHECK(f.build()); f.no_front();
        BlobFixture g; g.set_lod({0, 0, 128}); CHECK(g.build()); g.no_front();
    }
    test_case("short-strip-in-base-or-any-lod");
    for (unsigned n : {1U, 2U}) {
        BlobFixture f; if (n == 1) f.set_indices({0, 1, 130, 128}); else f.set_indices({0, 1, 130, 0, 129});
        CHECK(f.build()); f.no_front();
        BlobFixture g; if (n == 1) g.set_lod({128}); else g.set_lod({0, 129});
        CHECK(g.build()); g.no_front();
    }
    test_case("missing-end-marker-in-base-or-any-lod");
    { BlobFixture f; f.set_indices({0, 1, 2}); CHECK(f.build()); f.no_front(); }
    { BlobFixture f; f.set_lod({0, 1, 2}); CHECK(f.build()); f.no_front(); }
    test_case("invalid-cache-index-does-not-map-to-zero");
    { BlobFixture f; f.set_indices({0, 1, 130, 0, 1, 255}); CHECK(f.build()); f.no_front(); }
    { BlobFixture f; f.set_lod({0, 1, 255}); CHECK(f.build()); f.no_front(); }
    test_case("lod-index-within-its-actual-transformed-prefix");
    { BlobFixture f; f.set_lod({0, 1, 130}, 2); CHECK(f.build()); f.no_front(); }
    { BlobFixture f; f.set_lod({0, 1, 130}, 4); CHECK(f.build()); f.no_front(); }
    test_case("collapsed-lod-and-valid-lod");
    { BlobFixture f; f.set_lod({}, 0); CHECK(f.build()); CHECK(f.front()->min_normal > 0); }
    { BlobFixture f; f.set_lod({0, 1, 130}, 3); CHECK(f.build()); CHECK(f.front()->min_normal > 0); }
    test_case("invalid-source-index-and-source-unavailable");
    { BlobFixture f; f.records()[3] = 16; CHECK(f.build()); f.no_front(); }
    { BlobFixture f; f.p.position_stride = 6; source_available = false; CHECK(!f.build()); source_available = true; }
    test_case("single-skin-palette-versus-mixed-palettes");
    {
        BlobFixture f; f.p.position_stride = 6;
        for (auto& pos : f.positions) pos[3] = 2;
        const auto* cone = f.build(); CHECK(cone && cone->k && cone->pal == 2); CHECK(f.front()->min_normal > 0);
        f.positions[1][3] = 3; cone = f.build(); CHECK(cone && !cone->k); f.no_front();
    }
    test_case("full-s16-cross-range-no-integer-overflow");
    {
        BlobFixture f;
        f.positions[0][0] = -32768; f.positions[0][1] = -32768;
        f.positions[1][0] = 32767; f.positions[1][1] = -32768;
        f.positions[2][0] = -32768; f.positions[2][1] = 32767;
        CHECK(f.build() && f.front()); CHECK(f.front()->min_normal == 2147483648.0f);
        CHECK(f.front()->extent[0] == 32768 && f.front()->extent[1] == 32768);
    }
#endif
}

#if RE4DC_BACKFACE_CONE_FRONT
static void screen_matrix(float* m) {
    std::fill(m, m + 16, 0.0f);
    m[0] = 2.5f; m[5] = -1.875f; m[11] = -0.0078125f;
    m[12] = 327680.0f; m[13] = 245760.0f; m[15] = 1024.0f;
    m[10] = m[11]; m[14] = m[15];
}
static void matrix_matches(const abc_cert::Context& context, const float* matrix) {
    CHECK(context.valid);
    for (unsigned r = 0; r < 3; ++r) for (unsigned c = 0; c < 4; ++c)
        CHECK(context.matrix[r * 4 + c] == matrix[c * 4 + (r == 2 ? 3 : r)]);
}
static void context_tests() {
    test_case("rigid-context-actual-screen-matrix");
    Frame f; f.near_distance = 1.0f; screen_matrix(f.screen);
    const u16 flat[3] = {500, 500, 0}, volume[3] = {500, 500, 1};
    AbcFrontContext rigid; CHECK(abc_front_prepare(f, 0, flat, rigid)); matrix_matches(rigid.value, f.screen);
    CHECK(abc_front_prepare(f, 0, flat, rigid));
    test_case("depth-flatness-before-prepare-does-not-poison-palette-cache");
    AbcFrontContext first_nonflat; CHECK(!abc_front_prepare(f, 0, volume, first_nonflat));
    CHECK(first_nonflat.pal == ~0U && !first_nonflat.ok);
    CHECK(abc_front_prepare(f, 0, flat, first_nonflat)); CHECK(first_nonflat.ok);
    CHECK(!abc_front_prepare(f, 0, volume, first_nonflat)); CHECK(first_nonflat.ok);
    CHECK(abc_front_prepare(f, 0, flat, first_nonflat));
    test_case("skin-context-actual-position-matrix-and-palette-cache");
    float palette[24]{}; palette[0] = palette[4] = palette[8] = 1.0f;
    palette[12] = -1.0f; palette[16] = palette[20] = 1.0f; palette[21] = 50.0f;
    alignas(8) float prepared[32]{}; u8 ready[2]{};
    f.mode = kSkin; f.palette = palette; f.palette_entries = 2; f.q = 0.25f;
    f.skin_positions = prepared; f.skin_ready = ready;
    AbcFrontContext skin; CHECK(abc_front_prepare(f, 0, flat, skin)); CHECK(ready[0] && !ready[1]); matrix_matches(skin.value, prepared);
    CHECK(!abc_front_prepare(f, 1, volume, skin)); CHECK(skin.pal == 0 && skin.ok);
    CHECK(abc_front_prepare(f, 1, flat, skin)); CHECK(ready[1]); matrix_matches(skin.value, prepared + 16);
    CHECK(abc_front_prepare(f, 1, flat, skin)); CHECK(skin.pal == 1);
    CHECK(!abc_front_prepare(f, 2, flat, skin)); CHECK(skin.pal == 1 && skin.ok);
    f.palette = nullptr; CHECK(!abc_front_prepare(f, 0, flat, skin));
    f.mode = kSource; AbcFrontContext unsupported; CHECK(!abc_front_prepare(f, 0, flat, unsupported));
    test_case("skin-context-fallback-matrix-when-cache-absent");
    f.mode = kSkin; f.palette = palette; f.skin_positions = nullptr;
    AbcFrontContext fallback; CHECK(abc_front_prepare(f, 1, flat, fallback));
    float expected[16]; skin_position_matrix(f, 1, expected); matrix_matches(fallback.value, expected);
}

static abc_cert::Proof accepted_proof;
static constexpr unsigned accepted_nv = 64, accepted_ni = 294;
static pvr_vertex_t accepted_vertices[accepted_nv]{};
static u8 accepted_indices[accepted_ni]{};
static void finish_tests() {
    test_case("complete-front-proof-from-produced-dense-abc2");
    DenseFixture f; const auto* cone = f.build(); CHECK(cone && f.front());
    CHECK(abc_front_worth(*f.front(), accepted_nv, accepted_ni, 98));
    std::memcpy(accepted_indices, f.bytes.data() + 512, accepted_ni);
    Frame frame; frame.near_distance = 1.0f; screen_matrix(frame.screen);
    AbcFrontContext context; CHECK(abc_front_prepare(frame, 0, f.front()->extent, context));
    auto geometry = abc_front_cone(*cone, f.front());
    CHECK(abc_cert::classify(context.value, geometry, 2, accepted_proof) == abc_cert::FrontCandidate);
    for (unsigned i = 0; i < accepted_nv; ++i) {
        const auto* p = f.positions[i]; double h[3]{};
        for (unsigned r = 0; r < 3; ++r) {
            const unsigned row = r == 2 ? 3 : r;
            h[r] = frame.screen[12 + row];
            for (unsigned c = 0; c < 3; ++c) h[r] += double(frame.screen[c * 4 + row]) * p[c];
        }
        accepted_vertices[i].x = float(h[0] / h[2]); accepted_vertices[i].y = float(h[1] / h[2]);
        accepted_vertices[i].z = float(1.0 / h[2]);
    }
    CHECK(abc_cert::projected_front(accepted_proof, accepted_vertices, accepted_nv));
    CHECK(abc_cert::strict_front(accepted_vertices, accepted_indices, accepted_ni, 127, 2, true));
    CHECK(abc_front_finish(accepted_proof, accepted_vertices, accepted_nv, accepted_indices, accepted_ni, 2));
    test_case("dense-strip-policy-declines-small-long-quad-and-volumetric-groups");
    CHECK(!abc_front_worth(*f.front(), 3, 3, 1));
    CHECK(!abc_front_worth(*f.front(), 64, 126, 98));
    CHECK(!abc_front_worth(*f.front(), 64, 196, 98));
    CHECK(!abc_front_worth(*f.front(), 128, 294, 98));
    CHECK(!abc_front_worth(*f.front(), 64, 294, 99));
    CHECK(!abc_front_worth(*f.front(), 64, 294, 295));
    auto volume = *f.front(); volume.extent[2] = 1; CHECK(!abc_front_worth(volume, 64, 294, 98));
    CHECK(abc_front_worth(*f.front(), 64, 256, 128));
    test_case("final-check-rejects-bad-reciprocal-and-invalid-proof");
    auto invalid = accepted_proof; invalid.valid = false;
    CHECK(!abc_front_finish(invalid, accepted_vertices, accepted_nv, accepted_indices, accepted_ni, 2));
    accepted_vertices[0].z = 0;
    CHECK(!abc_front_finish(accepted_proof, accepted_vertices, accepted_nv, accepted_indices, accepted_ni, 2));
    accepted_vertices[0].z = 1.0f / 1024.0f;
    test_case("check-mode-fault-injection-falls-back-and-logs");
    const u8 reversed[3] = {accepted_indices[1], accepted_indices[0], accepted_indices[2]};
    const unsigned prior_bad = abc_front_bad, prior_logs = log_calls;
    const bool fault_result = abc_front_finish(accepted_proof, accepted_vertices, accepted_nv, reversed, 3, 2);
#if RE4DC_BACKFACE_CONE_FRONT == 2
    CHECK(!fault_result); CHECK(abc_front_bad == prior_bad + 1 && log_calls == prior_logs + 1);
#else
    CHECK(fault_result); CHECK(abc_front_bad == prior_bad && log_calls == prior_logs);
#endif
}
#endif

// The complete TU above selects its portable, non-SQ branch. For the three
// direct-dispatch methods below, only hardware emitters are stubbed. Method
// bodies are byte-extracted unchanged, including their preprocessor guards.
#undef RE4DC_ACTOR_DIRECT
#define RE4DC_ACTOR_DIRECT 1
namespace dispatch_fixture {
unsigned exact_strip, exact_whole, lean_strip, lean_whole, ram_strip, ram_whole;
static std::uint32_t* emit_sq(std::uint32_t* out, const pvr_vertex_t*, const u8*, unsigned n) { ++lean_strip; return out + 8U * n; }
static void emit(pvr_vertex_t*, const pvr_vertex_t*, const u8*, unsigned) { ++ram_strip; }
template<bool SQ> static void* emit_meshlet(void* out, const pvr_vertex_t*, const u8*, unsigned n) {
    if constexpr (SQ) ++lean_whole; else ++ram_whole;
    return static_cast<u8*>(out) + 32U * n;
}
struct Part {
    const Re4dcModelPart& p;
    Cache cache{};
    bool direct = true, cone_front = false, room_available = true;
    unsigned slots = 0, used = 0, input = 0, output = 0;
    std::uint32_t words[2048]{}; std::uint32_t* sq = words;
    bool room(unsigned) { return room_available; }
    pvr_vertex_t* at() { return reinterpret_cast<pvr_vertex_t*>(words); }
    void bf_send(const u8*, unsigned n) { ++exact_strip; slots += n; }
    void bf_whole(const u8*, unsigned n) { ++exact_whole; slots += n; }
@BF_ON@
@STRIP@
@WHOLE@
};
static void tests() {
    test_case("actual-part-dispatch-front-exact-and-material-routes");
    Re4dcModelPart p{}; p.cull = 2;
    Part d{p}; const u8 index[3] = {0, 1, 130};
    CHECK(d.bf_on()); d.strip(index, 3); CHECK(exact_strip == 1 && !lean_strip);
    CHECK(d.whole(index, 3, 1)); CHECK(exact_whole == 1 && !lean_whole);
#if RE4DC_BACKFACE_CONE_FRONT
    d.cone_front = true; CHECK(!d.bf_on()); d.strip(index, 3); CHECK(lean_strip == 1);
    CHECK(d.whole(index, 3, 1)); CHECK(lean_whole == 1);
    d.cone_front = false; CHECK(d.bf_on());
#endif
    for (unsigned fault = 0; fault < 3; ++fault) {
        p.cull = fault == 0 ? 0 : 2; p.material_flags = fault == 1 ? 4 : 0; p.depth_mode = fault == 2 ? 1 : 0;
        CHECK(!d.bf_on());
    }
    p.cull = 2; p.material_flags = p.depth_mode = 0;
    d.direct = false; d.strip(index, 3); CHECK(ram_strip == 1);
    CHECK(d.whole(index, 3, 1)); CHECK(ram_whole == 1);
    d.room_available = false; CHECK(!d.whole(index, 3, 1));
}
}

#if RE4DC_BACKFACE_CONE_FRONT
// Both draw-loop reset and completion statements are exact source extracts.
// Positions have already been supplied; no transform or lighting is mocked
// as proof of a full draw. These isolate stale-state and clipping decisions.
static void reset_regular() {
    test_case("regular-draw-reset-and-outcode-gate");
    Re4dcModelPart p{}; p.cull = 2; dispatch_fixture::Part e{p}; e.cache.v = accepted_vertices;
    const unsigned nv = accepted_nv, ni = accepted_ni; const u8* index = accepted_indices;
    for (unsigned any : {0U, unsigned(kOcNear), unsigned(kOcFar), unsigned(kOcLeft), 0U}) {
        e.cone_front = true;
@RESET_REGULAR@
        CHECK(!e.cone_front); abc_candidate = true; abc_proof = accepted_proof;
@FINISH_REGULAR@
        CHECK(e.cone_front == (any == 0));
    }
}
static void reset_chunk() {
    test_case("one-chunk-draw-reset-and-outcode-gate");
    Re4dcModelPart p{}; p.cull = 2; dispatch_fixture::Part e{p}; e.cache.v = accepted_vertices;
    const unsigned nv = accepted_nv, ni = accepted_ni; const u8* index = accepted_indices;
    for (unsigned any : {0U, unsigned(kOcNear), unsigned(kOcFar), unsigned(kOcRight), 0U}) {
        e.cone_front = true;
@RESET_CHUNK@
        CHECK(!e.cone_front); abc_candidate = true; abc_proof = accepted_proof;
@FINISH_CHUNK@
        CHECK(e.cone_front == (any == 0));
    }
}
#endif

int main() {
    producer_tests(); dispatch_fixture::tests();
#if RE4DC_BACKFACE_CONE_FRONT
    context_tests(); finish_tests(); reset_regular(); reset_chunk();
#endif
    std::printf("PASS mode=%u cases=%u checks=%u\n", unsigned(RE4DC_BACKFACE_CONE_FRONT), cases, checks);
}
