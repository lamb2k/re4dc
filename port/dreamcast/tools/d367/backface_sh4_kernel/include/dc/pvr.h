#pragma once
#include <cstdint>
struct pvr_vertex_t {
    std::uint32_t flags;
    float x,y,z,u,v;
    std::uint32_t argb,oargb;
};
static_assert(sizeof(pvr_vertex_t)==32);
constexpr std::uint32_t PVR_CMD_VERTEX=0xe0000000U;
constexpr std::uint32_t PVR_CMD_VERTEX_EOL=0xf0000000U;
