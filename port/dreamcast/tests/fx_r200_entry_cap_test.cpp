// Build18 host cases. The runner imports the real frame queue, effect/model/UI
// enqueue, packet, drain, reset and spill-provider code using the existing
// esp_setup_lean extraction scaffold. This file supplies fixtures and devices.
// Host ABI/FP and fake PVR compilation are not console output qualification.
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <functional>
#include <stdexcept>
#include <string>
#include <vector>

namespace gate {
unsigned passed = 0, failed = 0, assertions = 0;
void check(bool condition, const char* expression, int line) {
    ++assertions;
    if (!condition) throw std::runtime_error(std::string(expression) + " at line " + std::to_string(line));
}
#define CHECK(x) gate::check(bool(x), #x, __LINE__)
struct Packet {
    unsigned kind;
    std::vector<unsigned char> bytes;
    bool operator==(const Packet& other) const { return kind == other.kind && bytes == other.bytes; }
};
std::vector<Packet> packets;
std::vector<std::string> logs;
alignas(32) unsigned char slab[65536], room_cell[24 * 1024 + 32];
unsigned room = 0x200, mesh_room = 0x200, generation = 1, allocations = 0, allocated_bytes = 0, invalidations = 0;
bool room_live = true, allocation_ok = true;
std::vector<std::pair<std::string, std::vector<Packet>>> observations;

void run(const std::string& name, const std::function<void()>& body) {
    try {
        body(); ++passed;
        std::printf("CASE\t%s\tPASS\n", name.c_str());
    } catch (const std::exception& error) {
        ++failed;
        std::printf("CASE\t%s\tFAIL\t%s\n", name.c_str(), error.what());
    }
}
}

extern "C" unsigned re4dc_room_id_now() { return gate::room; }
extern "C" unsigned re4dc_ps2_mesh_room() { return gate::mesh_room; }
extern "C" int re4dc_room4_state(unsigned* generation, unsigned* cells, unsigned* bytes,
                                  unsigned* stale, unsigned* refused) {
    *generation = gate::generation; *cells = gate::allocations;
    *bytes = gate::allocated_bytes; *stale = *refused = 0;
    return gate::room_live;
}
extern "C" void* re4dc_static_alloc(unsigned bytes) {
    CHECK(bytes == 24 * 1024 + 32);
    ++gate::allocations;
    if (!gate::allocation_ok) return nullptr;
    gate::allocated_bytes += bytes;
    return gate::room_cell;
}

// Generated from production and the established runtime_queue.cpp.in. The
// runner records hashes of both inputs and all imported source in its receipt.
#include "fx_r200_test_scaffold.inc"

namespace gate {
#if defined(RE4DC_FX_R200_ENTRY_CAP) && RE4DC_FX_R200_ENTRY_CAP
constexpr bool enabled = true;
#else
constexpr bool enabled = false;
#endif
constexpr unsigned expected_tail_bytes = 8192;
unsigned char* tail_start() {
    return slab + kModelPacketBytes + kModelPreparationBytes + kModelStaticLightBytes;
}
bool inside(const void* p, const void* base, size_t bytes) {
    const uintptr_t address = reinterpret_cast<uintptr_t>(p), first = reinterpret_cast<uintptr_t>(base);
    return address >= first && address < first + bytes;
}
bool in_tail(const void* p) { return inside(p, tail_start(), expected_tail_bytes); }
void guard_slab() {
    const size_t first = size_t(tail_start() - slab), end = first + expected_tail_bytes;
    CHECK(end <= sizeof(slab));
    CHECK(std::all_of(slab, slab + first, [](unsigned char v) { return v == 0xa5; }));
    CHECK(std::all_of(slab + end, slab + sizeof(slab), [](unsigned char v) { return v == 0xa5; }));
}
void pristine_tail() {
    CHECK(std::all_of(tail_start(), tail_start() + expected_tail_bytes,
                      [](unsigned char v) { return v == 0xa5; }));
}
void fresh(unsigned live_room = 0x200) {
    reset();
    room = mesh_room = live_room; ++generation; room_live = allocation_ok = true;
    allocations = allocated_bytes = invalidations = 0;
    model_packets = reinterpret_cast<pvr_vertex_t*>(slab);
    std::memset(slab, 0xa5, sizeof(slab));
    std::memset(room_cell, 0xa5, sizeof(room_cell));
    packets.clear(); logs.clear();
    nquad = 0; dropped = culled = unsupported = missing = frame_queue_drops = deferred_drops = deferred_peak = 0;
    drawn = 1; // suppress the unrelated first-UI-quad diagnostic
    fx_frame = frame;
    cloth21_calls = 1; cloth21_rows = cloth21_quads = cloth21_drop = cloth21_cull = 0;
    cloth21_log_frame = frame;
    std::fill(std::begin(cloth21_why), std::end(cloth21_why), 0u);
}
Re4dcModelPart model(unsigned serial = 7) {
    Re4dcModelPart part{};
    part.model = reinterpret_cast<void*>(uintptr_t(0x12340000));
    part.info = reinterpret_cast<void*>(uintptr_t(0x12341000));
    part.part = reinterpret_cast<void*>(uintptr_t(0x12342000));
    part.blend = 1; part.alpha_state = 255; part.serial = serial;
    part.modelview[0] = part.modelview[5] = part.modelview[10] = 1;
    return part;
}
void queue_model(const Re4dcModelPart& part) {
    const unsigned before = deferred_count;
    CHECK(re4dc_model_defer_part(&part) == 1);
    CHECK(deferred_count == before + 1 && !stream_aborted);
}
// Use the actual model snapshot allocator to fill the room cell; no parallel
// allocator decides which region an effect receives. The lower frame boundary
// is a synthetic pressure input representing already reserved frame work.
void fill_primary(unsigned leave = 0) {
    const auto part = model();
    queue_model(part); // establish the real shared view basis in frame storage
    deferred_top = 8192;
    queue_model(part); // actual provider lazily chooses room cell or slab tail
    CHECK(deferred_spill != nullptr && deferred_spill_top % 32 == 0 && leave % 32 == 0);
    CHECK(deferred_spill_top >= leave);
    unsigned iterations = 0;
    while (deferred_spill_top > leave) {
        const unsigned prior = deferred_spill_top;
        queue_model(part);
        CHECK(deferred_spill_top < prior && ++iterations < 2048);
    }
    CHECK(deferred_spill_top == leave);
}
std::vector<Packet> effect_packets() {
    std::vector<Packet> result;
    for (const auto& packet : packets) if (packet.kind == 1) result.push_back(packet);
    return result;
}
void observation(const std::string& name) { observations.push_back({name, packets}); }

enum class Kind { sprite, trim_octagon, haze_octagon, laser, strip, cloth, haze_batch, stage_alpha, stage_add };
const char* kind_name(Kind kind) {
    switch (kind) {
        case Kind::sprite: return "sprite";
        case Kind::trim_octagon: return "trim_octagon";
        case Kind::haze_octagon: return "haze_octagon";
        case Kind::laser: return "laser";
        case Kind::strip: return "strip";
        case Kind::cloth: return "cloth";
        case Kind::haze_batch: return "haze_batch";
        case Kind::stage_alpha: return "stage_alpha";
        case Kind::stage_add: return "stage_add";
    }
    return "invalid";
}
const std::array<Kind, 9> kinds = {Kind::sprite, Kind::trim_octagon, Kind::haze_octagon,
    Kind::laser, Kind::strip, Kind::cloth, Kind::haze_batch, Kind::stage_alpha, Kind::stage_add};

void projection(float* p, float* viewport) {
    p[0] = 0; p[1] = p[3] = 1; p[2] = p[4] = 0;
    p[5] = -1.0f / 99.0f; p[6] = -100.0f / 99.0f;
    viewport[0] = viewport[1] = 0; viewport[2] = 640; viewport[3] = 480;
    viewport[4] = 0; viewport[5] = 1;
}
int enqueue(Kind kind, unsigned identity = 0, unsigned batch_count = 3) {
    auto s = sprite();
    s.color ^= identity & 0x00ffffffu;
    if (kind == Kind::trim_octagon) {
        entries[0].package.t.width = entries[0].package.t.height = 128;
        entries[0].key.crc = kFxTrim[0].crc; entries[0].key.fnv = kFxTrim[0].fnv;
        s.image.width = s.image.height = 128;
        Re4dcEffectSprite trimmed; float p[8], q[8];
        CHECK(fx_trim(s, &entries[0], trimmed, p, q) == 2);
    } else {
        entries[0].package.t.width = entries[0].package.t.height = 64;
        entries[0].key.crc = entries[0].key.fnv = 0;
    }
    if (kind == Kind::haze_octagon) s.pad = 1;
    if (kind == Kind::sprite || kind == Kind::trim_octagon || kind == Kind::haze_octagon) {
        const auto original = s;
        const int result = re4dc_effect_sprite(&s);
        CHECK(std::memcmp(&original, &s, sizeof(s)) == 0);
        return result;
    }
    if (kind == Kind::laser) {
        Re4dcEffectLine line{{40, 100}, {90, 30}, {.01f, .02f}, {s.color, s.color ^ 0x00010101}, 4, 5, 1, 1};
        return re4dc_effect_line(&line);
    }
    if (kind == Kind::strip) {
        Re4dcEffectQuad quad{}; quad.image = s.image; quad.color = s.color; quad.src = 4; quad.dst = 5;
        projection(quad.projection, quad.viewport);
        const float positions[4][3] = {{-1, 1, -10}, {-1, -1, -10}, {1, -1, -10}, {1, 1, -10}};
        std::memcpy(quad.positions, positions, sizeof(positions));
        const float u[4] = {0, 0, 1, 1}, v[4] = {0, 1, 1, 0};
        std::memcpy(quad.u, u, sizeof(u)); std::memcpy(quad.v, v, sizeof(v));
        return re4dc_effect_quad(&quad);
    }
    if (kind == Kind::cloth) {
        const float positions[18] = {-1,1,-10, 0,1,-10, 1,1,-10, -1,-1,-10, 0,-1,-10, 1,-1,-10};
        Re4dcEffectMesh21 mesh{}; mesh.image = s.image; mesh.positions = positions;
        mesh.cols = 3; mesh.rows = 2; mesh.v_step = 1; mesh.color = s.color; mesh.src = 4; mesh.dst = 5;
        projection(mesh.projection, mesh.viewport);
        return re4dc_effect_mesh21(&mesh);
    }
    CHECK(batch_count <= 50);
    std::array<Re4dcEffectSprite, 50> local;
    for (unsigned i = 0; i < batch_count; ++i) {
        local[i] = s; local[i].color ^= i << 8;
        if (kind == Kind::stage_add) local[i].dst = 1;
    }
    unsigned submitted = 999;
    const int result = kind == Kind::haze_batch ? re4dc_effect_haze_batch(local.data(), batch_count, &submitted) :
        re4dc_effect_stage1_batch(local.data(), batch_count, kind == Kind::stage_add ? 1 : 5, &submitted);
    CHECK(submitted == (result ? batch_count : 0));
    return result;
}

void packet_and_capacity_cases() {
    for (Kind kind : kinds) {
        const std::string label = kind_name(kind);
        std::vector<Packet> oracle;
        run("no_overflow_" + label, [&] {
            fresh(); CHECK(enqueue(kind, 0x33) == 1);
            CHECK(deferred_first != nullptr && inside(deferred_first, frame_storage, sizeof(frame_storage)));
            CHECK(allocations == 0); pristine_tail();
            drain(); oracle = effect_packets(); CHECK(!oracle.empty());
            observation("no_overflow_" + label); guard_slab();
        });
        run("full_distinct_room_cell_" + label, [&] {
            fresh(); fill_primary();
            CHECK(deferred_spill == room_cell && deferred_spill_capacity == 24576);
            const unsigned nodes = deferred_count, old_allocs = allocations;
            DeferredPart* previous = deferred_last;
            CHECK(enqueue(kind, 0x33) == int(enabled));
            CHECK(allocations == old_allocs && allocated_bytes == 24576 + 32);
            CHECK(deferred_spill == room_cell && deferred_spill_top == 0);
            if (enabled) {
                CHECK(previous->next != nullptr && in_tail(previous->next) && in_tail(deferred_last));
                CHECK(deferred_count > nodes);
            } else CHECK(deferred_count == nodes && previous->next == nullptr && fx_dropped == 1);
            drain(); CHECK(effect_packets() == (enabled ? oracle : std::vector<Packet>{}));
            observation("full_distinct_room_cell_" + label); guard_slab();
        });
        run("other_room_unchanged_" + label, [&] {
            fresh(0x201); fill_primary();
            const unsigned nodes = deferred_count;
            CHECK(enqueue(kind, 0x33) == 0 && deferred_count == nodes && fx_dropped == 1);
            pristine_tail(); drain(); observation("other_room_" + label); guard_slab();
        });
    }
    run("room_spill_allocation_failure_already_uses_tail_no_alias", [] {
        fresh(); allocation_ok = false; fill_primary();
        CHECK(deferred_spill == tail_start() && deferred_spill_capacity == expected_tail_bytes);
        const auto before = std::vector<unsigned char>(slab, slab + sizeof(slab));
        const unsigned nodes = deferred_count;
        CHECK(enqueue(Kind::sprite) == 0 && deferred_count == nodes);
        CHECK(std::equal(before.begin(), before.end(), slab));
        CHECK(allocations == 1 && allocated_bytes == 0); guard_slab();
    });
    run("null_slab_does_not_allocate_or_extend_room_cell", [] {
        fresh(); fill_primary(); model_packets = nullptr;
        const unsigned nodes = deferred_count;
        CHECK(enqueue(Kind::sprite) == 0 && deferred_count == nodes && allocations == 1);
        pristine_tail(); guard_slab();
    });
    for (Kind kind : {Kind::haze_batch, Kind::stage_alpha, Kind::stage_add}) {
        run(std::string("batch_without_active_spill_does_not_allocate_") + kind_name(kind), [kind] {
            fresh(); deferred_top = 8192;
            CHECK(enqueue(kind) == 0 && allocations == 0 && !deferred_spill && deferred_count == 0);
            pristine_tail(); guard_slab();
        });
        run(std::string("batch_validation_after_selection_does_not_consume_") + kind_name(kind), [kind] {
            fresh(); fill_primary();
            const unsigned nodes = deferred_count;
            auto* last = deferred_last;
            texture_missing = true;
            CHECK(enqueue(kind) == 0 && deferred_count == nodes && deferred_last == last && last->next == nullptr);
            pristine_tail();
            texture_missing = false;
            CHECK(enqueue(kind) == int(enabled));
            if (enabled) {
                CHECK(last->next == reinterpret_cast<DeferredPart*>(tail_start() + expected_tail_bytes - 3 * (kSpriteNode + kSpritePacket)));
                CHECK(deferred_last == reinterpret_cast<DeferredPart*>(tail_start() + expected_tail_bytes - (kSpriteNode + kSpritePacket)));
            }
            CHECK(allocations == 1); guard_slab();
        });
    }
    run("exact_primary_fit_uses_room_cell_before_tail", [] {
        fresh(); fill_primary(kSpriteNode + kSpritePacket);
        CHECK(enqueue(Kind::sprite) == 1 && inside(deferred_last, room_cell, 24576));
        CHECK(deferred_spill_top == 0); pristine_tail(); guard_slab();
    });
    run("exact_8192_tail_fit_and_sprite_64_cap_unchanged", [] {
        fresh(); fill_primary();
        const unsigned nodes = deferred_count;
        if (enabled) {
            for (unsigned i = 0; i < 64; ++i) CHECK(enqueue(Kind::sprite, i) == 1);
            CHECK(fx_count == 64 && deferred_count == nodes + 64);
            CHECK(deferred_last == reinterpret_cast<DeferredPart*>(tail_start()));
            CHECK(enqueue(Kind::sprite, 64) == 0 && fx_capped == 1 && fx_dropped == 0);
        } else CHECK(enqueue(Kind::sprite) == 0 && fx_dropped == 1 && fx_capped == 0);
        guard_slab();
    });
    run("tail_exhaustion_with_laser_and_exact_final_sprite", [] {
        fresh(); fill_primary();
        if (enabled) {
            static_assert((8192 % (32 + 160)) == 128);
            for (unsigned i = 0; i < 42; ++i) CHECK(enqueue(Kind::laser, i) == 1);
            CHECK(enqueue(Kind::sprite, 43) == 1 && fx_count == 1);
            CHECK(deferred_last == reinterpret_cast<DeferredPart*>(tail_start()));
            const unsigned nodes = deferred_count;
            CHECK(enqueue(Kind::laser, 44) == 0 && deferred_count == nodes && fx_dropped == 1 && fx_capped == 0);
        } else CHECK(enqueue(Kind::laser) == 0 && fx_dropped == 1);
        guard_slab();
    });
    run("too_large_atomic_batch_preserves_queue_and_allocation_cursor", [] {
        fresh(); fill_primary();
        if (enabled) {
            for (unsigned i = 0; i < 40; ++i) CHECK(enqueue(Kind::laser, i) == 1);
            CHECK(fx_count == 0);
            const unsigned nodes = deferred_count;
            auto* last = deferred_last;
            const auto memory = std::vector<unsigned char>(tail_start(), tail_start() + expected_tail_bytes);
            CHECK(enqueue(Kind::haze_batch, 0, 5) == 0);
            CHECK(deferred_count == nodes && deferred_last == last && last->next == nullptr);
            CHECK(std::equal(memory.begin(), memory.end(), tail_start()));
            CHECK(enqueue(Kind::stage_alpha, 0, 4) == 1);
            CHECK(deferred_last == reinterpret_cast<DeferredPart*>(tail_start() + 3 * (kSpriteNode + kSpritePacket)));
        } else CHECK(enqueue(Kind::haze_batch, 0, 5) == 0);
        guard_slab();
    });
}

void ownership_and_reserve_cases() {
    run("interleaved_model_reuses_primary_fragment_and_preserves_fifo", [] {
        fresh(); fill_primary(64);
        auto* primary_before = deferred_spill;
        auto* before = deferred_last;
        CHECK(enqueue(Kind::sprite, 0x11) == int(enabled));
        if (!enabled) { guard_slab(); return; }
        auto* first_effect = deferred_last;
        CHECK(in_tail(first_effect) && before->next == first_effect && deferred_spill_top == 64);
        const auto part = model(); queue_model(part);
        auto* middle_model = deferred_last;
        CHECK(inside(middle_model, room_cell, 24576) && first_effect->next == middle_model);
        CHECK(deferred_spill_top == 32 && deferred_spill == primary_before);
        CHECK(enqueue(Kind::sprite, 0x22) == 1);
        auto* last_effect = deferred_last;
        CHECK(in_tail(last_effect) && middle_model->next == last_effect);
        drain();
        CHECK(packets.size() >= 3);
        CHECK(packets[packets.size() - 3].kind == 1 && packets[packets.size() - 2].kind == 2 && packets.back().kind == 1);
        CHECK(effect_packets().size() == 2); guard_slab();
    });
    run("models_do_not_borrow_effect_only_tail", [] {
        fresh(); fill_primary();
        const unsigned nodes = deferred_count, drops_before = deferred_drops;
        const auto part = model();
        CHECK(re4dc_model_defer_part(&part) == 1);
        CHECK(deferred_count == nodes && deferred_drops == drops_before + 1 && !stream_aborted);
        pristine_tail(); guard_slab();
    });
    run("frame_reset_releases_tail_ownership_for_next_frame", [] {
        fresh(); fill_primary(); CHECK(enqueue(Kind::laser) == int(enabled));
        drain();
        CHECK(deferred_first == nullptr && deferred_last == nullptr && deferred_count == 0);
        reset(); fx_frame = frame; fill_primary();
        CHECK(enqueue(Kind::laser) == int(enabled));
        CHECK(allocations == 1); guard_slab();
    });
    run("room_generation_change_refuses_until_owner_reset", [] {
        fresh(); fill_primary(); CHECK(enqueue(Kind::sprite) == int(enabled));
        const unsigned old_generation = generation, nodes = deferred_count;
        ++generation;
        CHECK(enqueue(Kind::sprite) == 0 && deferred_count == nodes);
        generation = old_generation;
        // Once invalidated, changing the externally observed generation back
        // cannot resurrect a retained pointer during the same queue lifetime.
        CHECK(enqueue(Kind::sprite) == 0 && deferred_count == nodes);
        ++generation; reset(); fx_frame = frame; fill_primary();
        CHECK(enqueue(Kind::sprite) == int(enabled));
        guard_slab();
    });
    run("live_room_change_and_room_end_refuse_retained_tail", [] {
        fresh(); fill_primary(); CHECK(enqueue(Kind::sprite) == int(enabled));
        const unsigned nodes = deferred_count;
        room = 0x201; CHECK(enqueue(Kind::sprite) == 0 && deferred_count == nodes);
        room = 0x200; room_live = false;
        CHECK(enqueue(Kind::sprite) == 0 && deferred_count == nodes);
        guard_slab();
    });
    run("native_pending_invalidation_clears_queue_before_reuse", [] {
        fresh(); fill_primary(); CHECK(enqueue(Kind::sprite) == int(enabled));
        re4dc_model_invalidate_pending();
        CHECK(stream_aborted && !deferred_first && !deferred_last && deferred_count == 0 && invalidations == 1);
        CHECK(enqueue(Kind::sprite) == 0);
        reset(); fx_frame = frame; fill_primary(); CHECK(enqueue(Kind::sprite) == int(enabled));
        guard_slab();
    });
    run("live_room_required_even_if_stale_mesh_room_would_match", [] {
        fresh(); fill_primary(); room = 0x201; mesh_room = 0x200;
        CHECK(enqueue(Kind::sprite) == 0); pristine_tail(); guard_slab();
    });
    run("effect_frame_margin_exact_boundary_is_unchanged", [] {
        fresh();
        const unsigned required = kSpriteNode + kSpritePacket;
        deferred_top = 8192 + RE4DC_FX_QUEUE_MARGIN + required;
        CHECK(enqueue(Kind::sprite) == 1 && inside(deferred_last, frame_storage, sizeof(frame_storage)));
        CHECK(deferred_top == 8192 + RE4DC_FX_QUEUE_MARGIN && allocations == 0);
        CHECK(enqueue(Kind::sprite) == 1 && inside(deferred_last, room_cell, 24576));
        CHECK(deferred_top == 8192 + RE4DC_FX_QUEUE_MARGIN && allocations == 1);
        pristine_tail(); guard_slab();
    });
    run("ui_above_8192_retains_its_actual_byte_reserve", [] {
        fresh();
        Re4dcUiQuad q{}; q.image = sprite().image; q.color = 0xff112233;
        const unsigned ui_count = 8192 / sizeof(Re4dcUiQuad) + 2;
        for (unsigned i = 0; i < ui_count; ++i) re4dc_ui_submit(&q);
        CHECK(nquad == ui_count);
        const unsigned ui_bytes = nquad * sizeof(Re4dcUiQuad), required = kSpriteNode + kSpritePacket;
        const unsigned reserve = (ui_bytes + 31u) & ~31u;
        const auto ui_copy = std::vector<unsigned char>(frame_storage, frame_storage + ui_bytes);
        deferred_top = reserve + RE4DC_FX_QUEUE_MARGIN + required;
        CHECK(enqueue(Kind::sprite) == 1 && deferred_top == reserve + RE4DC_FX_QUEUE_MARGIN);
        CHECK(enqueue(Kind::sprite) == 1 && inside(deferred_last, room_cell, 24576));
        CHECK(std::equal(ui_copy.begin(), ui_copy.end(), frame_storage));
        pristine_tail(); guard_slab();
    });
    run("ui_cannot_borrow_the_effect_tail", [] {
        fresh(); fill_primary();
        CHECK(enqueue(Kind::sprite) == int(enabled));
        Re4dcUiQuad q{}; q.image = sprite().image; q.color = 0xff112233;
        const unsigned limit = deferred_top / sizeof(Re4dcUiQuad);
        for (unsigned i = 0; i < limit; ++i) re4dc_ui_submit(&q);
        CHECK(nquad == limit && !stream_aborted);
        re4dc_ui_submit(&q);
        CHECK(nquad == limit && stream_aborted && dropped == 1);
        guard_slab();
    });
    run("global_sprite_cap_stays_64_without_pressure", [] {
        fresh();
        for (unsigned i = 0; i < 64; ++i) CHECK(enqueue(Kind::sprite, i) == 1);
        const unsigned nodes = deferred_count;
        CHECK(enqueue(Kind::sprite, 64) == 0 && fx_capped == 1 && deferred_count == nodes && fx_dropped == 0);
        pristine_tail(); drain(); observation("global_cap"); guard_slab();
    });
}

void write_observations(const char* path) {
    FILE* file = std::fopen(path, "wb"); CHECK(file != nullptr);
    auto write = [&](const void* p, size_t bytes) { CHECK(std::fwrite(p, 1, bytes, file) == bytes); };
    for (const auto& observation : observations) {
        uint32_t n = observation.first.size(); write(&n, sizeof(n)); write(observation.first.data(), n);
        n = observation.second.size(); write(&n, sizeof(n));
        for (const auto& packet : observation.second) {
            const uint32_t kind = packet.kind, size = packet.bytes.size();
            write(&kind, sizeof(kind)); write(&size, sizeof(size)); write(packet.bytes.data(), size);
        }
    }
    CHECK(std::fclose(file) == 0);
}
}

int main(int argc, char** argv) {
    std::setvbuf(stdout, nullptr, _IONBF, 0);
    if (argc != 2) return 2;
    gate::packet_and_capacity_cases();
    gate::ownership_and_reserve_cases();
    gate::write_observations(argv[1]);
    std::printf("TOTAL\tpassed=%u\tfailed=%u\tassertions=%u\n", gate::passed, gate::failed, gate::assertions);
    return gate::failed ? 1 : 0;
}
