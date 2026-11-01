#pragma once
// EF12: a value copy of the two rows loaded by EspTexSet as GX_TG_MTX2x4.
// CommonStateSet feeds this matrix (s,t,1,1), so both constant columns count.
// The third EspTexWk row is not loaded for this texture-coordinate generator.
namespace re4dc::effect_uv12 {
struct Matrix24 { float row[2][4]; };

inline bool finite(float value) { return __builtin_isfinite(value); }

inline bool capture(const float (&source)[3][4], Matrix24& out) {
    for (unsigned row = 0; row != 2; ++row)
        for (unsigned col = 0; col != 4; ++col) {
            const float value = source[row][col];
            if (!finite(value)) return false;
            out.row[row][col] = value;
        }
    return true;
}

inline bool transform(const Matrix24& matrix, float s, float t, float& out_s, float& out_t) {
    if (!finite(s) || !finite(t)) return false;
    const float next_s = matrix.row[0][0] * s + matrix.row[0][1] * t + matrix.row[0][2] + matrix.row[0][3];
    const float next_t = matrix.row[1][0] * s + matrix.row[1][1] * t + matrix.row[1][2] + matrix.row[1][3];
    if (!finite(next_s) || !finite(next_t)) return false;
    out_s = next_s;
    out_t = next_t;
    return true;
}
} // namespace re4dc::effect_uv12
