#pragma once
#if defined(RE4DC_HOUSE_ARENA27_COUNTS) && RE4DC_HOUSE_ARENA27_COUNTS
#include <stdint.h>

// Diagnostic arithmetic/TA work only. Counts are per actual world-pass call,
// including empty PT/TR calls, and must never be reported as timing.
struct Re4dcHouseArena27Geometry {
    uint32_t schema, sequence, pass, ui_frame, room_frame;
    uint32_t mesh_crc, mesh_bytes, camera_hash;
    uint32_t transformed_positions, transformed_cache, transformed_clip;
    uint32_t emitted_corners, emitted_triangles, fallback, aborts;
    int32_t result;
    uint32_t valid;
};
extern "C" void re4dc_house_arena27_geometry(const Re4dcHouseArena27Geometry*);
extern "C" unsigned re4dc_house_arena27_room_frame(void);
#endif
