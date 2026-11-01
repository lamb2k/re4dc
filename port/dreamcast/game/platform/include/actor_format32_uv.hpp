#pragma once
// ACTOR_FORMAT32 UV admission. No texture/global state and no allocation.
#include <cmath>
#include <cstdint>
#include <cstring>

namespace re4dc::format32 {
enum UvReason : unsigned {
    Uv16 = 0, Legacy = 1, Binding = 2, Precision = 3, Nonfinite = 4,
    NotRequested = 5, BeginFailed = 6, Source = 7
};

// The old FE3 field is significant-bit excess for a 16-bit raw component:
// legitimate old values are 0..8. New 16..31 values certify |raw| <= 2^e,
// e=1..16, for every referenced component. Zero and one share e=1. Keeping
// the tag in the existing five bits leaves the blob layout/length unchanged;
// an old/preconverted blob supplies no new precision certificate.
constexpr unsigned kUvCertificateEmpty = 16U;
// Out-of-band request only: FE3 stores five bits, so this cannot be a blob tag.
constexpr unsigned kUvSourceDeclined = 32U;
inline unsigned uv_certificate_add(unsigned certificate, int raw) {
    if (certificate < 16U || certificate > 31U || raw < -32768 || raw > 65535) return 0U;
    const unsigned magnitude = unsigned(raw < 0 ? -raw : raw);
    unsigned power = 2U, exponent = 1U;
    while (power < magnitude) { power <<= 1; ++exponent; }
    const unsigned value = 15U + exponent;
    return certificate > value ? certificate : value;
}
inline unsigned uv_certificate_exponent(unsigned certificate) {
    return certificate >= 16U && certificate <= 31U ? certificate - 15U : 0U;
}

// Check the CURRENT UV values, not merely the conversion-time summary. The
// caller validates this record range against the blob and supplies the same
// qualified UV backing used by the vertex reader (Re4dcModelPart has no UV
// allocation length). Every LOD uses a prefix of these level-zero records.
// Signedness is interpreted anew, so pointer replacement, changed components
// and signed/unsigned reinterpretation cannot retain a stale small bound.
inline bool uv_record_range(unsigned exponent, const std::uint16_t* records,
                            unsigned stride, unsigned count, const unsigned char* uv,
                            bool signed_uv, unsigned& scanned, unsigned readable_bytes = ~0U) {
    if (exponent < 1U || exponent > 16U || !records || !uv || stride < 3U || stride > 5U) return false;
    const unsigned limit = 1U << exponent, sign = signed_uv ? 0x8000U : 0U;
    for (unsigned i = 0; i < count; ++i) {
        const unsigned at = unsigned(records[i * stride + 2U]) * 4U;
        ++scanned;
        if (at > readable_bytes || readable_bytes - at < 4U) return false;
        const auto* pair = reinterpret_cast<const std::uint16_t*>(uv + at);
        const unsigned u = pair[0], v = pair[1];
        const unsigned au = (u & sign) ? 65536U - u : u;
        const unsigned av = (v & sign) ? 65536U - v : v;
        if (au > limit || av > limit) return false;
    }
    return true;
}

inline std::uint32_t uv_word(float value) {
    std::uint32_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}
inline float uv_float(std::uint32_t bits) {
    float value;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}
inline bool uv_finite(float value) {
    // This must remain a real check when the production TU uses fast-math.
    return (uv_word(value) & 0x7f800000U) != 0x7f800000U;
}
inline std::uint32_t uv_pack(std::uint32_t u, std::uint32_t v) {
    // Preserve the existing PVR bf16 round-to-nearest, half-away-from-zero
    // representation. Source u is separately retained in cache word seven.
    return ((u + 0x8000U) & 0xffff0000U) | ((v + 0x8000U) >> 16);
}

// For a closed interval [-M,M] with M a power of two, the largest bf16
// rounding error is M/512 (the half spacing immediately below M). At M
// itself packing is exact. A floating-point overshoot of <= M/1024 still
// rounds to M, so the same bound includes rounding in UV formation and the
// production near-plane interpolator's a+(b-a)*t, 0<=t<=1. The allowance is
// more than 1,000 single-precision ulps; it does not authorize extrapolation.
// The rounded bound calculation below can cross a power-of-two boundary by
// at most a few ulps; those also fit within that allowance. Texture units
// use the actual bound native image, after scale and scroll are resolved.
inline UvReason uv_axis(unsigned exponent, unsigned raw_shift, float scale,
                        float offset, unsigned texture_size) {
    if (exponent < 1U || exponent > 16U || (raw_shift != 8U && raw_shift != 15U)) return Legacy;
    if (texture_size < 8U || texture_size > 1024U || (texture_size & (texture_size - 1U))) return Binding;
    if (!uv_finite(scale) || !uv_finite(offset)) return Nonfinite;
    // A source image of 1..1024 pixels and a native texture of 8..1024
    // bound this ratio. Baked/RTT coordinates use scale one.
    if (!(scale >= 1.0f / 1024.0f && scale <= 128.0f)) return Binding;
    const float raw_scale = raw_shift == 8U ? 1.0f / 256.0f : 1.0f / 32768.0f;
    const float coefficient = raw_scale * scale;
    const float translation = offset * scale;
    const float bound = std::ldexp(std::fabs(coefficient), int(exponent)) + std::fabs(translation);
    if (!uv_finite(bound) || !(bound > 0.0f)) return Nonfinite;
    const std::uint32_t bits = uv_word(bound);
    std::uint32_t power = bits & 0x7f800000U;
    if (bits & 0x007fffffU) power += 0x00800000U; // ceil power of two
    // The smallest admitted coefficient is 2^-25, so subtracting nine
    // exponent steps is normal. Large UV ranges fail precision directly.
    if (power < (10U << 23) || power >= 0x7f800000U) return Precision;
    const float error = uv_float(power - (9U << 23));
    return error * float(int(texture_size)) <= 0.5f ? Uv16 : Precision;
}
inline UvReason uv_decide(unsigned certificate, bool signed_uv,
                          const float offsets[2], unsigned width, unsigned height,
                          float u_scale, float v_scale) {
    if (certificate == kUvSourceDeclined) return Source;
    const unsigned exponent = uv_certificate_exponent(certificate);
    if (!exponent) return Legacy;
    const unsigned shift = signed_uv ? 8U : 15U;
    UvReason result = uv_axis(exponent, shift, u_scale, offsets[0], width);
    if (result != Uv16) return result;
    return uv_axis(exponent, shift, v_scale, offsets[1], height);
}

// A request cannot survive begin(). Every early failure leaves BeginFailed,
// and an unrelated generic begin consumes no stale actor-format request.
struct UvRequest {
    unsigned pending = 0U;
    unsigned result = BeginFailed;
    void prepare(unsigned certificate) {
        pending = 0x100U | (certificate <= kUvSourceDeclined ? certificate : 0U);
        result = BeginFailed;
    }
    unsigned take() {
        const unsigned request = pending;
        pending = 0U; result = BeginFailed;
        return request;
    }
    void cancel() { pending = 0U; result = BeginFailed; }
};

struct UvCounters {
    unsigned parts = 0, admitted = 0, legacy = 0, binding = 0, precision = 0;
    unsigned nonfinite = 0, begin_failed = 0, source = 0, scanned_records = 0;
    unsigned splits = 0, packet = 0, direct = 0, shared = 0;
    void note(unsigned reason, unsigned path) {
        ++parts;
        if (reason == Uv16) ++admitted;
        else if (reason == Legacy) ++legacy;
        else if (reason == Binding) ++binding;
        else if (reason == Precision) ++precision;
        else if (reason == Nonfinite) ++nonfinite;
        else if (reason == Source) ++source;
        else ++begin_failed;
        if (path == 0U) ++packet;
        else if (path == 1U) ++direct;
        else if (path == 2U) ++shared;
    }
};
} // namespace re4dc::format32

struct Re4dcModelPart;
extern "C" void re4dc_model_uv16_request32(unsigned certificate);
extern "C" unsigned re4dc_model_uv16_result32();
extern "C" unsigned re4dc_model_uv16_live32(const Re4dcModelPart*, unsigned certificate);
