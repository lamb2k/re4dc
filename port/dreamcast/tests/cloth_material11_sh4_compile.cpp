// Compile only: no SDK link, assets, emulator or target execution required.
#include <cstdint>
#include <type_traits>
#include <dolphin/types.h>
#include <dolphin/gx/GXStruct.h>
#include "cloth_material11_sampler.hpp"

#if !defined(__sh__)
#error This fixture must compile with the SH-4 toolchain
#endif
static_assert(sizeof(unsigned)==4 && sizeof(unsigned long)==4 && sizeof(void*)==4);
static_assert(sizeof(GXTexObj)==32);
static_assert(std::is_same_v<u32,unsigned long>);
static_assert(std::is_same_v<std::uint32_t,u32>);
static_assert(!std::is_same_v<u32,unsigned>);
static_assert(std::is_same_v<std::remove_extent_t<decltype(GXTexObj::dummy)>,u32>);

extern "C" bool re4dc_cloth_sampler11_sh4_fixture(GXTexObj* object) {
    using namespace re4dc::cloth_material11;
    init_sampler(object->dummy,0);
    lod_sampler(object->dummy,1,1,0,0,0,0,1,0);
    // The production source adapter snapshots descriptor words into unsigned
    // values. Keep this reader contract; do not alias the original u32 array.
    unsigned copied[8];
    for(unsigned i=0;i<8;++i)copied[i]=object->dummy[i];
    return linear_clamp(copied);
}
