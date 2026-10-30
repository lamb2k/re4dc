#pragma once
#ifndef RE4DC_CLOTH_SHEET11
#define RE4DC_CLOTH_SHEET11 0
#endif
#if RE4DC_CLOTH_SHEET11
#include "native_ui.h"
#include "native_draw_result.hpp"
// Frame-scoped prepared native material; no source grid/pixel pointer retained.
// This preserves CLOTH_NATIVE's existing single-texture approximation. Source
// TEV scale/clamp, alpha>4/depth policy and pTobjA remain separate coverage gaps.
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
// Only the new synchronous material path retains a call-scoped validation
// callback. The FIFO contains copied PVR packets, never this callback/context.
struct Re4dcClothMaterial11 { alignas(32) unsigned char state[320]{}; };
struct Re4dcClothCheck11 { const void* context;bool (*current)(const void*); };
namespace re4dc::cloth_material11 { struct Source; }
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
extern "C" re4dc::NativeDrawResult re4dc_cloth_band11(const Re4dcClothMaterial11*,const Re4dcClothBand11*);
#endif
