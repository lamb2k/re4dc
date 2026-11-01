#pragma once
#ifndef RE4DC_CLOTH_SHEET11
#define RE4DC_CLOTH_SHEET11 0
#endif
#if RE4DC_CLOTH_SHEET11
#include "native_ui.h"
#include "native_draw_result.hpp"
#if (defined(RE4DC_CLOTH_PUBLICATION11) && RE4DC_CLOTH_PUBLICATION11) || (defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11)
#include "cloth_publication11.hpp"
#endif
// Frame-scoped prepared native material; no source grid/pixel pointer retained.
// Ordinary materials preserve the existing approximation. MATERIAL11 adds
// bounded constant-white Esp4e and saturated pTobjA source proofs only.
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
// Only the new synchronous material path retains a call-scoped validation
// callback. The FIFO contains copied PVR packets, never this callback/context.
struct Re4dcClothMaterial11 { alignas(32) unsigned char state[320]{}; };
struct Re4dcClothCheck11 { const void* context;bool (*current)(const void*); };
namespace re4dc::cloth_material11 { struct Source; }
class Cloth;
extern "C" int re4dc_cloth_esp4e_words11(const Cloth*,unsigned words[8]);
// Existing cloth incarnation table fences source room/pool retirement too.
extern "C" void re4dc_cloth_material_retire11();
// Scalar source admission gate; no frame ownership or source pointer escapes.
extern "C" int re4dc_cloth_frame_open11();
extern "C" int re4dc_cloth_material11(const Re4dcEffectMesh21*,const re4dc::cloth_material11::Source*,
    Re4dcClothCheck11,Re4dcClothMaterial11*,re4dc::NativeDrawResult* stop);
#else
struct Re4dcClothMaterial11 { alignas(32) unsigned char state[256]{}; };
#endif
struct Re4dcClothBand11 {
    const float* top; const float* bottom;
    unsigned columns,first_column,row;
};
// 1: ready, nothing published. 0: stop holds the explicit draw outcome.
extern "C" int re4dc_cloth_prepare11(const Re4dcEffectMesh21*,Re4dcClothMaterial11*,re4dc::NativeDrawResult* stop);
#if defined(RE4DC_CLOTH_PUBLICATION11) && RE4DC_CLOTH_PUBLICATION11
extern "C" void re4dc_cloth_observe_bind11(Re4dcClothMaterial11*,unsigned);
#endif
extern "C" re4dc::NativeDrawResult re4dc_cloth_band11(const Re4dcClothMaterial11*,const Re4dcClothBand11*);
#endif
