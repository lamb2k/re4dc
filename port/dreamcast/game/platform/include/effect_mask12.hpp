#pragma once
#include <cstdint>
#include <cstring>
#include "cloth_material11_sampler.hpp"
// Ordinary RGB565 mask TEXA is exactly one: keep sampled base RGB and replace
// its alpha by the current raster alpha. No descriptor/layout change.
namespace re4dc::effect_mask12 {
enum : unsigned { sample_alpha = 0, opaque_mask = 1 };
// RE4DCTX v2 ordinary 16bpp only: RGB565/ARGB1555/ARGB4444,
// linear or twiddled, alpha/binary-alpha flags only. Replacement palettes,
// VQ, mip chains and coverage metadata lack preserved-transparent-RGB proof.
template<class Texture> bool native_rgb(const Texture& t){
    return t.format<=2U && t.payload<=1U && !(t.flags&~3U) && !t.reserved_0;
}
}
