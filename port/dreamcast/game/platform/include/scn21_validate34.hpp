#ifndef RE4DC_SCN21_VALIDATE34_HPP
#define RE4DC_SCN21_VALIDATE34_HPP

#include <cstdint>
#include <cstring>

// SCCN/SCPS v1 reader checks, only used by the existing scenery21 switches.
// These are format and extent checks, not a proof that a finite cone encloses
// the source triangles. scn21_build.py still owns that geometric certificate.
namespace re4dc_scn21 {

inline std::uint32_t word(const std::uint8_t* p) {
    std::uint32_t w;
    std::memcpy(&w, p, sizeof w);
    return w;
}

inline const char* header(const std::uint8_t* sec, unsigned len, std::uint32_t (&w)[4]) {
    if (!sec || len < 16U) return "short header";
    // The admitted SCCN table is read as floats, and SCPS slots are written as
    // uint32_t. The room-file reader normally provides 32-byte alignment.
    if (reinterpret_cast<std::uintptr_t>(sec) & 3U) return "alignment";
    std::memcpy(w, sec, 16U);
    return nullptr;
}

inline const char* cone(const std::uint8_t* sec, unsigned len, unsigned version,
                        std::uint32_t crc, std::uint32_t bytes, std::uint32_t meshlets,
                        unsigned groups, std::uint32_t (&w)[4]) {
    if (const char* why = header(sec, len, w)) return why;
    if (version != 1U || w[0] != crc || w[1] != bytes || w[2] != meshlets || w[3] != groups)
        return "package";
    // R4SG already admits only 1..8 groups; do not trust a matching malformed
    // SCCN count to justify a product before the section extent is known.
    if (!groups || groups > 8U) return "groups";
    if (len < 272U) return "short table";
    if (meshlets > ((len - 272U) / 8U) / groups) return "records";

    // Positive IEEE binary32 bit patterns have the same order as their values.
    // Integer checks remain meaningful with the production fast-math flags.
    std::uint32_t previous = word(sec + 16U);
    if (previous != 0U) return "cone table";
    for (unsigned k = 1; k < 64U; ++k) {
        const std::uint32_t v = word(sec + 16U + 4U * k);
        if ((v & 0x80000000U) || (v & 0x7f800000U) == 0x7f800000U || v <= previous)
            return "cone table";
        previous = v;
    }

    const unsigned count = meshlets * groups; // bounded by the division above
    for (unsigned i = 0; i < count; ++i) {
        const std::uint8_t* r = sec + 272U + 8U * i;
        if (r[3] >= 64U) return "cone index";
        const std::uint32_t radius = word(r + 4U);
        if ((radius & 0x80000000U) || (radius & 0x7f800000U) == 0x7f800000U)
            return "cone radius";
        if (!r[3]) continue; // k=0 is the builder's inactive/no-cone record
        if (!radius) return "cone radius";
        int length2 = 0;
        for (unsigned a = 0; a < 3U; ++a) {
            if (r[a] == 128U) return "cone axis"; // builder quantizes to [-127,127]
            const int v = r[a] < 128U ? int(r[a]) : int(r[a]) - 256;
            length2 += v * v;
        }
        if (!length2 || length2 > 128 * 128) return "cone axis";
    }
    return nullptr;
}

inline const char* piece(const std::uint8_t* sec, unsigned len, unsigned version,
                         std::uint32_t crc, std::uint32_t bytes, std::uint32_t parts,
                         std::uint32_t (&w)[4]) {
    if (const char* why = header(sec, len, w)) return why;
    if (version != 1U || w[0] != crc || w[1] != bytes || w[2] != parts || w[3] != 0U)
        return "package";
    if (parts > (len - 16U) / 4U) return "slots";
    return nullptr;
}

} // namespace re4dc_scn21
#endif
