// backface_census.cpp (lane backface22, 2026-10-22): BACKFACE_CENSUS=1 (backface.mk; test builds only, needs TA_HASH=1).
// Default 0: this file is empty and the image is unchanged.
// Every TA burst the game sends already passes re4dc_ta_hash (native_ui.cpp) in TA_HASH builds; this observer parses
// those bursts (polygon header -> PVR cull mode from ISP/TSP word bits 28:27; vertices -> screen x, y; EOS ends a
// strip) and counts, per draw class (re4dc_bfc_class, set by the world / static / actor submitters) and per scene:
//   v    all strip vertices sent        cv  vertices of strips whose header culls (CCW / CW)
//   t    triangles of culling strips    b   triangles the ISP rejects (and zero-area ones)
//   r    vertices inside back runs of >= 3 triangles (k + 2 per run)
//   s    vertices a strip split would save: whole strip back = n; a run at a strip end = k; inside = k - 2 (k >= 3)
// The PVR sign is counted both ways (h0: CW rejects positive area, the pvr_geometry.hpp convention native_ui.cpp
// states at re4dc_coarse_begin_mode; h1: the opposite), so a wrong convention shows as a mirrored row, not a wrong
// result. Strip parity: triangle i of a strip flips its winding when i is odd, as the TA does.
// Lists: OP, TR, PT polygons only (modifier lists and sprites skipped); 64-byte vertex formats are counted in v only.
// One "bfc:" line per class every 60 presented scenes (sums over those scenes).
#if defined(RE4DC_BACKFACE_CENSUS) && RE4DC_BACKFACE_CENSUS
#include <cstdint>
#include <cstring>
extern "C" void re4dc_log(const char* fmt, ...);
extern "C" { volatile unsigned re4dc_bfc_class; volatile unsigned re4dc_bfc_id; }
namespace {
constexpr unsigned kClasses = 8;
struct Sum { unsigned v, cv, t, b[2], r[2], s[2], id, st, cst; };  // st/cst: strips (EOS) all / culling
Sum win[kClasses];
unsigned win_scenes, win_first;
struct List {
    unsigned cull = 0, vsz = 32, half = 0;
    bool skip = true, open = false;
    unsigned n = 0, cls = 0;
    float x[2], y[2];
    unsigned k[2]; bool front[2];  // per hypothesis: current back run, a front triangle before it
};
List lists[5];
void close_run(Sum& s, unsigned h, unsigned k, bool before, bool after) {
    if (!k) return;
    if (k >= 3) s.r[h] += k + 2;
    if (!before && !after) s.s[h] += k + 2;
    else if (!before || !after) s.s[h] += k;
    else if (k >= 3) s.s[h] += k - 2;
}
void vertex(List& L, const std::uint32_t* q) {
    const unsigned c = re4dc_bfc_class < kClasses ? re4dc_bfc_class : 0;
    if (!L.open) { L.open = true; L.n = 0; L.cls = c; L.k[0] = L.k[1] = 0; L.front[0] = L.front[1] = false; }
    Sum& S = win[L.cls];
    ++S.v;
    if (re4dc_bfc_id > S.id) S.id = re4dc_bfc_id;  // largest actor id of the class
    const bool eos = (q[0] >> 28) & 1;
    if (L.vsz == 32 && (L.cull == 2 || L.cull == 3)) {
        ++S.cv;
        float x, y; std::memcpy(&x, q + 1, 4); std::memcpy(&y, q + 2, 4);
        if (L.n >= 2) {
            float area = (L.x[1] - L.x[0]) * (y - L.y[0]) - (L.y[1] - L.y[0]) * (x - L.x[0]);
            if ((L.n - 2) & 1) area = -area;
            ++S.t;
            // h0: CW (3) rejects area > 0, CCW (2) rejects area < 0. h1: mirrored. Zero area draws nothing: back.
            const bool back0 = area == 0.0f || (L.cull == 3 ? area > 0 : area < 0);
            const bool back1 = area == 0.0f || (L.cull == 3 ? area < 0 : area > 0);
            const bool back[2] = {back0, back1};
            for (unsigned h = 0; h < 2; ++h) {
                if (back[h]) { ++S.b[h]; ++L.k[h]; }
                else { close_run(S, h, L.k[h], L.front[h], true); L.k[h] = 0; L.front[h] = true; }
            }
        }
        L.x[0] = L.x[1]; L.y[0] = L.y[1]; L.x[1] = x; L.y[1] = y;
    }
    ++L.n;
    if (eos) {
        ++S.st;
        if (L.vsz == 32 && (L.cull == 2 || L.cull == 3)) ++S.cst;
        if (L.vsz == 32 && (L.cull == 2 || L.cull == 3))
            for (unsigned h = 0; h < 2; ++h) close_run(S, h, L.k[h], L.front[h], false);
        L.open = false;
    }
}
}
extern "C" void re4dc_bfc_feed(unsigned list, const void* data, unsigned bytes) {
    if (list != 0 && list != 2 && list != 4) return;
    if (bytes < 32) return;
    List& L = lists[list];
    const auto* w = static_cast<const std::uint32_t*>(data);
    for (unsigned b = 0; b < bytes / 32; ++b) {
        const std::uint32_t* q = w + b * 8;
        if (L.half) { L.half = 0; continue; }  // second half of a 64-byte vertex
        const unsigned t = q[0] >> 29;
        if (t == 4u) {
            L.open = false;
            L.skip = false;
            L.cull = (q[1] >> 27) & 3;
            const unsigned col = (q[0] >> 4) & 3, tex = (q[0] >> 3) & 1, vol = (q[0] >> 6) & 1;
            L.vsz = (vol || (col == 1 && tex)) ? 64 : 32;
        } else if (t == 5u) { L.open = false; L.skip = true; }
        else if (t == 7u) {
            if (L.skip) continue;
            vertex(L, q);
            if (L.vsz == 64) L.half = 1;
        } else if (t == 0u) { L.open = false; }
    }
}
extern "C" void re4dc_bfc_scene(unsigned frame, int present) {
    for (auto& L : lists) { L.open = false; L.half = 0; L.skip = true; }
    if (!present) return;
    if (!win_scenes) win_first = frame;
    if (++win_scenes < 60) return;
    for (unsigned c = 0; c < kClasses; ++c) {
        const Sum& s = win[c];
        if (!s.v) continue;
        re4dc_log("bfc: frame=%u..%u scenes=%u cls=%u v=%u cv=%u t=%u b=%u/%u r=%u/%u s=%u/%u id=%02x st=%u cst=%u\n", win_first, frame,
                  win_scenes, c, s.v, s.cv, s.t, s.b[0], s.b[1], s.r[0], s.r[1], s.s[0], s.s[1], s.id, s.st, s.cst);
    }
    std::memset(win, 0, sizeof win);
    win_scenes = 0;
}
#endif
