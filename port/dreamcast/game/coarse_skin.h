// COARSE_SKIN_FTRV (game30.mk): the coarse actor adapters' palette matrices with FTRV
// (coarse_skin_sh4.S). =1: per used bone T = inv x P x B (two FTRV passes), per palette entry
// the weighted sum of its bones' T (entries grouped by bone set: three XMTRX loads per group, one
// FTRV per entry and block; one-bone entries copied). =2 check build: the C
// path is computed too and compared (largest translation and 3x3 element differences).
// Render-only: palettes never reach game logic. The palette output must be 32-byte aligned with
// room to the next 32-byte boundary (the routine allocates its lines with MOVCA).
#pragma once
#include <cstring>

// Finite test on the exponent bits: the same answer as __builtin_isfinite, which on this target is a
// libgcc __unordsf2 call per float (2.9 hw ms/frame in the kite fight from the bone-matrix guards).
inline bool coarse_finite(float f) { unsigned u; std::memcpy(&u, &f, 4); return (u & 0x7f800000U) != 0x7f800000U; }

struct CoarseBoneJob { const float* P; const float* B; float* T; };
extern "C" void re4dc_coarse_skin_bones(const float* inv, const CoarseBoneJob* jobs, unsigned n);
extern "C" void re4dc_coarse_skin_groups(const void* stream, unsigned groups, const float* T, float* out, unsigned entries);
struct CoarseGroupHeader { short offset[3]; unsigned short count, n, pad[3]; };
struct CoarseGroupEntry { float w[4]; unsigned out, pad; };
static_assert(sizeof(CoarseGroupHeader) == 16 && sizeof(CoarseGroupEntry) == 24, "coarse palette groups");
#if defined(RE4DC_SKIN_SH4ZAM) && RE4DC_SKIN_SH4ZAM
// SKIN_SH4ZAM (game30.mk; platform/sh4zam_skin.c): every caller goes through the run-time switch (mask bit 0x01 picks
// the SH4ZAM XMTRX bodies, else these asm routines).
extern "C" void re4dc_shz_skin_bones(const float* inv, const CoarseBoneJob* jobs, unsigned n);
extern "C" void re4dc_shz_skin_groups(const void* stream, unsigned groups, const float* T, float* out, unsigned entries);
#define re4dc_coarse_skin_bones re4dc_shz_skin_bones
#define re4dc_coarse_skin_groups re4dc_shz_skin_groups
#endif

// One chunk's palette entries from the generated Weight table ({u8 bone[3], count; float value[3]}),
// grouped by (count, bones) in order of first appearance. Marks used bones. Returns the stream bytes
// (0: does not fit in cap or more than 256 entries).
template <class Weight>
inline unsigned coarse_group_build(const Weight* w, unsigned n, unsigned char* out, unsigned cap, unsigned* groups,
                                   unsigned char* used) {
    if (n > 256) return 0;
    bool done[256] = {};
    unsigned bytes = 0, g = 0;
    for (unsigned j = 0; j < n; ++j) {
        if (done[j]) continue;
        if (bytes + sizeof(CoarseGroupHeader) > cap) return 0;
        auto* h = reinterpret_cast<CoarseGroupHeader*>(out + bytes);
        bytes += sizeof(CoarseGroupHeader); ++g;
        const unsigned c = w[j].count;
        for (unsigned k = 0; k < 3; ++k) h->offset[k] = short((k < c ? w[j].bone[k] : w[j].bone[0]) * 48U);
        h->count = (unsigned short)c; h->n = 0; h->pad[0] = h->pad[1] = h->pad[2] = 0;
        for (unsigned k = 0; k < c; ++k) used[w[j].bone[k]] = 1;
        for (unsigned i = j; i < n; ++i) {
            if (done[i] || w[i].count != c || std::memcmp(w[i].bone, w[j].bone, c)) continue;
            if (bytes + sizeof(CoarseGroupEntry) > cap) return 0;
            if (c == 1 && w[i].value[0] != 1.0f) return 0;  // one-bone groups are copied: weight must be 1
            done[i] = true;
            auto* e = reinterpret_cast<CoarseGroupEntry*>(out + bytes);
            bytes += sizeof(CoarseGroupEntry);
            for (unsigned k = 0; k < 4; ++k) e->w[k] = k < c ? w[i].value[k] : 0.0f;
            e->out = i * 48U; e->pad = 0;
            ++h->n;
        }
    }
    *groups = g;
    return bytes;
}
// The root inverse (row-major 3x4) as XMTRX: column-major 4x4 with the bottom row 0 0 0 1.
inline void coarse_inv_xmtrx(const float inv[3][4], float x[16]) {
    for (unsigned j = 0; j < 4; ++j) {
        for (unsigned i = 0; i < 3; ++i) x[j * 4 + i] = inv[i][j];
        x[j * 4 + 3] = j == 3 ? 1.0f : 0.0f;
    }
}

#if RE4DC_COARSE_SKIN_FTRV == 2
extern "C" void re4dc_log(const char*, ...);
// Reference (the =0 path's operations) for one palette entry, from the C local skin matrices.
struct CoarseSkinCheck {
    // translation column: absolute (model units); 3x3 elements: absolute (unit scale)
    float max_translation = 0.0f, max_rotation = 0.0f; unsigned entries = 0, over = 0, nonfinite = 0;
    template <class Weight>
    void entry(const Weight& w, const float (*local)[3][4], const float* got) {
        for (unsigned col = 0; col < 4; ++col)
            for (unsigned row = 0; row < 3; ++row) {
                float value = 0;
                for (unsigned k = 0; k < w.count; ++k) value += local[w.bone[k]][row][col] * w.value[k];
                const float g = got[col * 3 + row];
                if (!__builtin_isfinite(g) || !__builtin_isfinite(value)) { ++nonfinite; continue; }
                const float d = __builtin_fabsf(g - value);
                if (col == 3) { if (d > max_translation) max_translation = d; }
                else { if (d > max_rotation) max_rotation = d; if (d > 1e-5f) ++over; }
            }
        ++entries;
    }
    void log(const char* who, unsigned t) {
        re4dc_log("COARSE_SKIN_CHK %s t=%u entries=%u max_translation=%.7f max_rotation=%.9f rotation_over_1e-5=%u nonfinite=%u\n",
                  who, t, entries, double(max_translation), double(max_rotation), over, nonfinite);
    }
};
#endif
