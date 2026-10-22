// bfc_class.h (lane backface22): BACKFACE_CENSUS=1 draw-class tags for platform/backface_census.cpp.
// 1 PS2 world mesh, 2 static parts, 3 Leon, 4 Ganado (id 0x10..0x20), 5 other actor (bosses, animals, Ashley).
// Default: the macro expands to nothing (no code).
#pragma once
#if defined(RE4DC_BACKFACE_CENSUS) && RE4DC_BACKFACE_CENSUS
extern "C" { extern volatile unsigned re4dc_bfc_class; extern volatile unsigned re4dc_bfc_id; }
struct Re4dcBfcScope {
    unsigned old, old_id;
    Re4dcBfcScope(unsigned c, unsigned id) : old(re4dc_bfc_class), old_id(re4dc_bfc_id) { re4dc_bfc_class = c; re4dc_bfc_id = id; }
    ~Re4dcBfcScope() { re4dc_bfc_class = old; re4dc_bfc_id = old_id; }
};
#define RE4DC_BFC_SCOPE(c, id) Re4dcBfcScope re4dc_bfc_scope_((c), (id))
#else
#define RE4DC_BFC_SCOPE(c, id) do {} while (0)
#endif
