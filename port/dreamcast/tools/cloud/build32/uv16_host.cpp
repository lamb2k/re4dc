#include "../../../game/platform/include/actor_format32_uv.hpp"
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdio>
#include <limits>

using namespace re4dc::format32;
static unsigned checks = 0, raw_cases = 0, clip_cases = 0;
#define CHECK(test) do { assert(test); ++checks; } while (0)

static unsigned old_excess(int raw) {
    unsigned value = unsigned(raw < 0 ? -raw : raw), bits = 0;
    if (!value) return 0;
    while (!(value & 1U)) value >>= 1;
    while (value >> bits) ++bits;
    return bits > 8 ? bits - 8 : 0;
}
static float rounded(float value) {
    // Independent numerical reference: nearest multiple of the bf16 spacing
    // in this binade, including exponent carry and both signs.
    if (!value) return value;
    int exponent;
    const double fraction = std::frexp(std::fabs(double(value)), &exponent);
    const double integer = std::floor(fraction * 256.0 + 0.5);
    return std::copysign(float(std::ldexp(integer, exponent - 8)), value);
}
static void packed_value(float value) {
    const auto packed = uv_pack(uv_word(value), 0U);
    CHECK(uv_float(packed & 0xffff0000U) == rounded(value));
}

int main() {
    const float zero[2] = {0, 0};
    CHECK(uv_certificate_add(16U, -32769) == 0U);
    CHECK(uv_certificate_add(16U, 65536) == 0U);
    CHECK(uv_certificate_add(0U, 1) == 0U);
    CHECK(uv_axis(0, 8, 1, 0, 8) == Legacy);
    CHECK(uv_axis(17, 8, 1, 0, 8) == Legacy);
    CHECK(uv_axis(8, 9, 1, 0, 8) == Legacy);
    for (int raw = -32768; raw <= 65535; ++raw) {
        const unsigned certificate = uv_certificate_add(16U, raw);
        const unsigned exponent = uv_certificate_exponent(certificate);
        CHECK(old_excess(raw) <= 8U); // exhaustive legacy/nonlegacy tag separation
        CHECK(certificate >= 16U && certificate <= 31U);
        CHECK(std::fabs(double(raw)) <= std::ldexp(1.0, int(exponent)));
        CHECK(uv_certificate_add(certificate, 0) == certificate);
        ++raw_cases;
    }
    for (unsigned legacy = 0; legacy < 16; ++legacy)
        CHECK(uv_decide(legacy, true, zero, 8, 8, 1, 1) == Legacy);

    // Old track_uv drops the two low zero bits of 1036 (259*4). It stores
    // excess 1, predicting <=1 raw-unit error, but bf16 actually loses four.
    CHECK(old_excess(1036) == 1U);
    CHECK(std::fabs(double(rounded(1036.0f)) - 1036.0) == 4.0);
    const unsigned bad_old = uv_certificate_add(16U, 1036);
    CHECK(uv_decide(bad_old, true, zero, 64, 64, 1, 1) == Precision);
    CHECK(uv_decide(bad_old, true, zero, 32, 32, 1, 1) == Uv16);

    // Exact endpoints do not certify a clipped interpolation. 0 and 256
    // have old excess zero, yet arbitrary near intersections at 1024px do
    // exceed half a texel. The new complete interval declines that texture.
    const unsigned unit = uv_certificate_add(16U, 256);
    CHECK(old_excess(0) == 0U && old_excess(256) == 0U);
    CHECK(uv_decide(unit, true, zero, 256, 256, 1, 1) == Uv16);
    CHECK(uv_decide(unit, true, zero, 1024, 1024, 1, 1) == Precision);
    const float near_intersection = 0.501953125f;
    CHECK(std::fabs(rounded(near_intersection) - near_intersection) * 1024.0f > .5f);

    // Actual binding, not source dimensions, determines the texel size.
    CHECK(uv_decide(unit, true, zero, 512, 512, .5f, .5f) == Uv16);
    CHECK(uv_decide(unit, true, zero, 512, 512, 1, 1) == Precision);
    CHECK(uv_decide(unit, true, zero, 256, 256, 0, 1) == Binding);
    CHECK(uv_decide(unit, true, zero, 257, 256, 1, 1) == Binding);
    CHECK(uv_decide(unit, true, zero, 2048, 256, 1, 1) == Binding);
    CHECK(uv_decide(unit, true, zero, 256, 256, 129, 1) == Binding);
    float offset[2] = {std::numeric_limits<float>::quiet_NaN(), 0};
    CHECK(uv_decide(unit, true, offset, 256, 256, 1, 1) == Nonfinite);
    offset[0] = 4;
    CHECK(uv_decide(unit, true, offset, 256, 256, 1, 1) == Precision);
    offset[0] = .125f;
    CHECK(uv_decide(unit, true, offset, 64, 64, 1, 1) == Uv16);

    // Certificate authority belongs to the current values and signedness.
    // Referenced pairs only; nonreferenced values cannot change the result.
    std::array<std::uint16_t, 8> current = {1, 0, 256, 255, 0xff80U, 0, 1036, 0};
    std::array<std::uint16_t, 15> records{};
    const auto* bytes = reinterpret_cast<const unsigned char*>(current.data());
    unsigned scanned = 0;
    records[2] = 0;
    CHECK(uv_record_range(1, records.data(), 3, 1, bytes, true, scanned));
    CHECK(scanned == 1);
    current[0] = 1036; // same address, changed contents
    CHECK(!uv_record_range(1, records.data(), 3, 1, bytes, true, scanned));
    current[0] = 1;
    CHECK(!uv_record_range(1, records.data(), 3, 1, bytes + 12, true, scanned)); // changed pointer
    records[2] = 2;
    CHECK(uv_record_range(7, records.data(), 3, 1, bytes, true, scanned)); // signed -128
    CHECK(!uv_record_range(7, records.data(), 3, 1, bytes, false, scanned)); // unsigned 65408
    CHECK(uv_decide(kUvSourceDeclined, false, zero, 256, 256, 1, 1) == Source);
    CHECK(std::fabs(rounded(65408.0f / 32768.0f) - 65408.0f / 32768.0f) * 256.0f == 1.0f);
    for (unsigned stride : {3U, 4U, 5U}) {
        records.fill(0);
        records[2] = 0; records[stride + 2] = 1; records[stride * 2 + 2] = 2;
        scanned = 0;
        CHECK(uv_record_range(8, records.data(), stride, 3, bytes, true, scanned));
        CHECK(scanned == 3);
        current[1] = 257; // V must be checked as well as U
        CHECK(!uv_record_range(8, records.data(), stride, 3, bytes, true, scanned));
        current[1] = 0;
        CHECK(!uv_record_range(8, records.data(), stride, 3, bytes, true, scanned, 11));
    }
    CHECK(!uv_record_range(0, records.data(), 3, 1, bytes, true, scanned));
    CHECK(!uv_record_range(17, records.data(), 3, 1, bytes, true, scanned));
    CHECK(!uv_record_range(8, nullptr, 3, 1, bytes, true, scanned));
    CHECK(!uv_record_range(8, records.data(), 2, 1, bytes, true, scanned));
    CHECK(!uv_record_range(8, records.data(), 6, 1, bytes, true, scanned));
    current[0] = 0x8000; current[1] = 65535;
    records[2] = 0;
    CHECK(uv_record_range(16, records.data(), 3, 1, bytes, false, scanned));
    CHECK(uv_record_range(15, records.data(), 3, 1, bytes, true, scanned));

    // Exhaust all u16 source magnitudes with scaling, signed values, carry
    // and exact half cases. This also checks the production packing helper
    // against a numerical reference rather than its bit expression.
    for (unsigned raw = 0; raw <= 65535; ++raw) {
        packed_value(float(raw) / 32768.0f);
        packed_value(-float(raw) / 32768.0f);
        packed_value(float(raw) / 256.0f);
    }

    // Exercise the allowed texture/scale/scroll combinations and complete
    // convex near-clip interpolation, including slight float overshoot at
    // the power-of-two interval endpoint. Check the rendered texel error.
    const float scales[] = {1.0f / 128, .5f, 1, 1.5f, 2, 128};
    const float offsets[] = {0, .001f, -.125f, .5f, 4};
    const unsigned sizes[] = {8, 32, 64, 128, 256, 512, 1024};
    const int maxima[] = {1, 255, 256, 257, 1036, 32768, 65535};
    for (const bool signed_uv : {false, true}) for (int maximum : maxima) {
        if (signed_uv && maximum > 32768) continue;
        const unsigned code = uv_certificate_add(16U, maximum);
        const float raw_scale = signed_uv ? 1.0f / 256 : 1.0f / 32768;
        for (float scale : scales) for (float scroll : offsets) for (unsigned size : sizes) {
            const float offsets2[2] = {scroll, scroll};
            if (uv_decide(code, signed_uv, offsets2, size, size, scale, scale) != Uv16) continue;
            const float coefficient = raw_scale * scale;
            const float translation = scroll * scale;
            const float a = -float(maximum) * coefficient + translation;
            const float b = float(maximum) * coefficient + translation;
            for (unsigned step = 0; step <= 1024; ++step) {
                const float t = float(step) / 1024;
                const float uv = a + (b - a) * t;
                CHECK(std::fabs(double(rounded(uv)) - uv) * size <= .5);
                ++clip_cases;
            }
        }
    }
    for (int exponent = -24; exponent <= 4; ++exponent) {
        const float m = std::ldexp(1.0f, exponent), error = m / 512;
        for (int sign : {-1, 1}) for (float fraction : {1.0f, 1.0f - 1.0f / 1024, 1.0f + 1.0f / 1024}) {
            const float uv = sign * m * fraction;
            CHECK(std::fabs(rounded(uv) - uv) <= error);
        }
    }

    UvRequest request;
    request.prepare(unit);
    const unsigned taken = request.take();
    CHECK(taken == (0x100U | unit) && !request.pending && request.result == BeginFailed);
    CHECK(request.take() == 0U && request.result == BeginFailed);
    request.prepare(unit); request.cancel();
    CHECK(request.take() == 0U && request.result == BeginFailed);
    request.prepare(255U);
    CHECK(request.take() == 0x100U); // malformed code cannot wrap into a tag
    request.prepare(kUvSourceDeclined);
    CHECK(request.take() == (0x100U | kUvSourceDeclined));

    UvCounters counters;
    for (unsigned reason = Uv16; reason <= Source; ++reason) counters.note(reason, reason % 3);
    CHECK(counters.parts == 8 && counters.admitted == 1 && counters.legacy == 1 && counters.source == 1);
    CHECK(counters.binding == 1 && counters.precision == 1 && counters.nonfinite == 1 && counters.begin_failed == 2);
    std::printf("PASS UV32: %u checks, %u exhaustive raw-component cases, %u near-interpolation cases\n",
                checks, raw_cases, clip_cases);
}
