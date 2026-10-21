// Actual native_ui helpers and actor leases; GPU/package/device boundaries are
// deterministic host adapters. This is not a PVR fence or gameplay simulation.
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <vector>
#include "actor_resource_lease.h"

using pvr_ptr_t = unsigned;
constexpr unsigned kTextureCount = 80, base_address = 0x01000000;
static unsigned closes, fence_calls, profile_evictions, frame, used;
static bool close_saw_retired;
static bool cap_observer;
static unsigned expected_note_at_close;
static std::vector<unsigned> blocks_off, blocks_len;
static unsigned pool;
static void observe_close(unsigned id);
namespace re4dc::texture {
struct Package {
    struct Header { unsigned texture_count = 0; } h;
    unsigned id = 0, bytes = 0;
    std::vector<unsigned> offsets;
    unsigned vram_bytes() const { return bytes; }
    const Header& header() const { return h; }
    pvr_ptr_t pvr_texture(unsigned n) const { return base_address + offsets.at(n); }
    void close() { observe_close(id); bytes = 0; offsets.clear(); h.texture_count = 0; }
};
}
#include "window_actual_types.inc"
Entry entries[kTextureCount];
re4dc_actor::TextureLeases<kTextureCount> actor_texture_leases;
static bool core[kTextureCount];
static bool core_pinned(const Entry& e) { return core[&e - entries]; }
#define RE4DC_CORE_PINNED(e) core_pinned(e)
#define RE4DC_FX_POOL_PINNED(e) false
#define RE4DC_ROOM_PINNED(e) false
#include "window_actual_entry_pin.inc"
static unsigned vram_claims, claim_released, frag_min_age;
static bool preload_pending;
#include "window_actual_hold.inc"

static void observe_close(unsigned id)
{
    assert(id < kTextureCount);
    // The real close_entry must revoke actual leases before Package::close.
    close_saw_retired = !actor_texture_leases.pinned(id);
    assert(close_saw_retired);
#if RE4DC_SS_HOLD_RESTORE
    const unsigned expected = cap_observer && RE4DC_SS_WINDOW_HOLD_RESTORE
        ? std::min(closes + 1, 64U) : expected_note_at_close;
    assert(hold_nkeys == expected);
#endif
    ++closes;
    ++fence_calls; // Package boundary observer; no hardware fence claim.
}
#define RE4DC_PROFILE_COUNT(name, n) (profile_evictions += (n))
void re4dc_log(const char*, ...) {}
extern "C" unsigned re4dc_vram_pages_snapshot(unsigned* off, unsigned* len,
                                              unsigned cap, unsigned* base, unsigned* size)
{
    assert(blocks_off.size() == blocks_len.size() && blocks_off.size() <= cap);
    std::copy(blocks_off.begin(), blocks_off.end(), off);
    std::copy(blocks_len.begin(), blocks_len.end(), len);
    *base = base_address; *size = pool;
    return blocks_off.size();
}
static unsigned pvr_mem_available() { return pool - used; }
static pvr_ptr_t pvr_mem_malloc(unsigned n) { return n <= pvr_mem_available() ? base_address : 0; }
static void pvr_mem_free(pvr_ptr_t) {}
static bool stream_scene, stream_aborted;
static unsigned stream_closes, present_fences, quiesces;
static void stream_close(bool show) { assert(!show); ++stream_closes; stream_scene = false; }
static void present_fence() { ++present_fences; }
namespace re4dc::gpu {
enum class FenceResult { ready, failed };
static bool refuse_fence;
FenceResult quiesce() { ++quiesces; return refuse_fence ? FenceResult::failed : FenceResult::ready; }
}
#include "window_actual_methods.inc"

static void reset(unsigned at = 100)
{
    actor_texture_leases.retire_frame();
    for (auto& e : entries) e = Entry{};
    std::fill(std::begin(core), std::end(core), false);
    frame = at; used = closes = fence_calls = profile_evictions = 0;
    vram_claims = claim_released = frag_min_age = 0; preload_pending = false;
    stream_scene = stream_aborted = false;
    stream_closes = present_fences = quiesces = expected_note_at_close = 0;
    cap_observer = false;
    re4dc::gpu::refuse_fence = false;
    blocks_off.clear(); blocks_len.clear(); pool = 0;
#if RE4DC_SS_HOLD_RESTORE
    hold_nkeys = hold_frame = hold_dropped = 0; hold_restore = false;
#endif
}
static void add(unsigned i, unsigned bytes, unsigned age, std::initializer_list<unsigned> offsets)
{
    auto& e = entries[i]; e.valid = true; e.key = {i + 1, i + 101};
    e.frame = frame - age; e.package.id = i; e.package.bytes = bytes;
    e.package.offsets.assign(offsets); e.package.h.texture_count = offsets.size(); used += bytes;
}
static void layout(std::initializer_list<unsigned> lengths)
{
    for (unsigned len : lengths) { blocks_off.push_back(pool); blocks_len.push_back(len); pool += len; }
}
static unsigned notes()
{
#if RE4DC_SS_HOLD_RESTORE
    return hold_nkeys;
#else
    return 0;
#endif
}
static void expect_note(unsigned n)
{
    expected_note_at_close = (RE4DC_SS_WINDOW_HOLD_RESTORE && RE4DC_SS_HOLD_RESTORE) ? n : 0;
}

int main()
{
    unsigned checks = 0;
    // A hold journals only recently drawn entries; its 60-frame boundary is inclusive.
    for (unsigned age : {1U, 30U, 59U, 60U, 61U, 100U}) {
        for (bool holding : {false, true}) {
            reset(); layout({2048}); add(0, 2048, age, {0});
            if (holding) re4dc_ui_vram_hold();
            const unsigned expected = holding && age <= 60 ? 1 : 0;
            expect_note(expected); unsigned bytes = 0;
            assert(movie_window_release(2048, false, bytes) == 1);
            assert(bytes == 2048 && used == 0 && closes == 1 && fence_calls == 1 && profile_evictions == 1);
            assert(notes() == expected_note_at_close);
            re4dc_ui_vram_unclaim();
#if RE4DC_SS_HOLD_RESTORE
            assert(preload_pending == (expected_note_at_close != 0));
            assert(hold_restore == (expected_note_at_close != 0));
#endif
            ++checks;
        }
    }
    // A package owning multiple VRAM blocks is retired and remembered exactly once.
    reset(); layout({2048, 2048}); add(0, 4096, 1, {0, 2048}); re4dc_ui_vram_hold();
    expect_note(1); unsigned bytes = 7;
    assert(movie_window_release(4096, false, bytes) == 1 && bytes == 4103);
    assert(closes == 1 && profile_evictions == 1 && notes() == expected_note_at_close); ++checks;

    // Frame pins, actual actor leases and core pins stay ineligible in ordinary windows.
    for (unsigned pin = 0; pin < 3; ++pin) {
        reset(); layout({2048}); add(0, 2048, 1, {0});
        Re4dcActorTextureLease lease{};
        if (pin == 0) entries[0].frame = frame;
        if (pin == 1) assert(actor_texture_leases.acquire(0, frame, lease));
        if (pin == 2) core[0] = true;
        re4dc_ui_vram_hold(); bytes = 0;
        assert(movie_window_release(2048, false, bytes) == 0);
        assert(entries[0].valid && !bytes && !closes && !notes());
        expect_note(1);
        assert(movie_window_release(2048, true, bytes) == 1);
        assert(!entries[0].valid && !actor_texture_leases.pinned(0) && closes == 1);
        actor_texture_leases.release(lease); ++checks;
    }
    // Fragment window age policy still rejects a recently drawn texture.
    for (unsigned age : {29U, 30U}) {
        reset(); layout({2048}); add(0, 2048, age, {0}); re4dc_ui_vram_hold(); frag_min_age = 30;
        expect_note(age >= 30 ? 1 : 0); bytes = 0;
        assert(movie_window_release(2048, false, bytes) == (age >= 30 ? 1U : 0U));
        assert(notes() == expected_note_at_close); ++checks;
    }
    // Cheapest-window ownership, opaque blocks and zero/invalid entries retain selection.
    reset(); layout({2048, 2048, 2048});
    add(0, 4096, 1, {0, 2048}); add(1, 2048, 1, {4096}); re4dc_ui_vram_hold();
    expect_note(1); bytes = 0; assert(movie_window_release(2048, false, bytes) == 1);
    assert(entries[0].valid && !entries[1].valid && bytes == 2048); ++checks;
    reset(); layout({2048}); re4dc_ui_vram_hold(); bytes = 0;
    assert(movie_window_release(2048, false, bytes) == 0 && !bytes && !notes()); ++checks;

    // A nested hold is restored only on final unclaim; it uses the existing journal.
    reset(); layout({2048}); add(0, 2048, 1, {0}); re4dc_ui_vram_hold(); re4dc_ui_vram_hold();
    expect_note(1); bytes = 0; assert(movie_window_release(2048, false, bytes) == 1);
    re4dc_ui_vram_unclaim(); assert(vram_claims == 1 && !preload_pending);
    re4dc_ui_vram_unclaim(); assert(!vram_claims && preload_pending == (notes() != 0)); ++checks;

    // Actual claim callers keep their original preload and fence/fallback outcomes.
    for (bool movie : {false, true}) {
        reset(); layout({2048}); add(0, 2048, 1, {0});
        expect_note(movie ? 1 : 0);
        assert(vram_claim(2048, movie) == 1 && claim_released == 1 && closes == 1);
        assert(!stream_closes && !present_fences && !quiesces);
        re4dc_ui_vram_unclaim(); assert(preload_pending && !vram_claims && !claim_released); ++checks;
    }
    reset(); layout({2048}); add(0, 2048, 0, {0}); stream_scene = true;
    expect_note(1); assert(vram_claim(2048, true) == 1);
    assert(stream_closes == 1 && present_fences == 1 && quiesces == 1 && stream_aborted && closes == 1); ++checks;
    reset(); layout({2048}); add(0, 2048, 0, {0}); stream_scene = true; re4dc::gpu::refuse_fence = true;
    assert(vram_claim(2048, true) == 0 && entries[0].valid && !closes && !notes()); ++checks;

    // The existing fixed 64-key cap is retained. Additional admissions only count a drop.
#if RE4DC_SS_HOLD_RESTORE
    reset(); re4dc_ui_vram_hold();
    for (unsigned i = 0; i < 65; ++i) {
        layout({2048}); add(i, 2048, 1, {i * 2048});
    }
    cap_observer = true; bytes = 0;
    assert(movie_window_release(pool, true, bytes) == 65);
    assert(hold_nkeys == (RE4DC_SS_WINDOW_HOLD_RESTORE ? 64U : 0U));
    assert(hold_dropped == (RE4DC_SS_WINDOW_HOLD_RESTORE ? 1U : 0U)); ++checks;
#endif
    std::cout << "actual movie_window_release/hold/unclaim/close/claim: window_note="
              << RE4DC_SS_WINDOW_HOLD_RESTORE << " hold=" << RE4DC_SS_HOLD_RESTORE
              << " checks=" << checks << " PASS\n";
}
