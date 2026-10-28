#pragma once
#include <cstdint>
struct pvr_vertex_t { std::uint32_t flags; float x,y,z,u,v; std::uint32_t argb,oargb; };
static_assert(sizeof(pvr_vertex_t)==32);
