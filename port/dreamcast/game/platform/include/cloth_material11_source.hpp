#pragma once
#include <cstdint>
#include <cstring>
#include "cloth_material11_sampler.hpp"
#include "native_draw_owner_stamp.hpp"
#include "native_ui.h"

namespace re4dc::cloth_material11 {
// This is an allocation/incarnation authority, never an immutable-content
// certificate. Keep and compare the bounded source bytes again after yields.
struct TextureSource {
    const void* object=nullptr;
    Re4dcDrawOwnerStamp object_owner{},pixel_owner{};
    unsigned words[8]{};
    unsigned char texels[128]{};
    Re4dcUiImage image{};
    bool copied_object=false;

    bool capture(const void* source) {
        object=source;copied_object=false;
        object_owner=re4dc_model_draw_owner_stamp(source,sizeof words);
        if(!source || !object_owner.valid())return false;
        std::memcpy(words,source,sizeof words);
        return capture_pixels();
    }
    // Embedded Esp4e GX objects belong to the effect slot, not an archive.
    // The source check proves that slot before comparing these copied words.
    bool capture_copied(const void* source,const unsigned snapshot[8]) {
        object=source;copied_object=true;
        std::memcpy(words,snapshot,sizeof words);
        return capture_pixels();
    }
    bool capture_pixels() {
        // One bounded raw GX RGB565 class, no mip/palette/coverage extension.
        if(words[1]!=0x00080008U || words[2]!=4U || !linear_clamp(words))return false;
        image={reinterpret_cast<const void*>(std::uintptr_t(words[0])),nullptr,8,8,4,~0U,0};
        pixel_owner=re4dc_model_draw_owner_stamp(image.pixels,sizeof texels);
        if(!image.pixels || !pixel_owner.valid())return false;
        std::memcpy(texels,image.pixels,sizeof texels);
        // An external/self-key reference is not a raw GX texel array. The
        // registered external-identity test also runs before native resolution.
        unsigned magic[2];std::memcpy(magic,texels,sizeof magic);
        return !(magic[0]==0x524e3452U && magic[1]==0x00004645U);
    }
    bool current() const {
        return pixel_owner.valid() &&
            re4dc_model_draw_owner_stamp(image.pixels,sizeof texels)==pixel_owner &&
            (copied_object || (object_owner.valid() &&
                re4dc_model_draw_owner_stamp(object,sizeof words)==object_owner &&
                !std::memcmp(object,words,sizeof words))) &&
            !std::memcmp(image.pixels,texels,sizeof texels);
    }
    bool white() const {
        for(unsigned char byte:texels)if(byte!=255)return false;
        return true;
    }
};
struct Source {
    TextureSource primary,secondary;
    bool single=false;
    bool capture(const void* first,const void* second) {
        single=false;return primary.capture(first) && primary.white() && secondary.capture(second);
    }
    bool capture_single(const void* first,const unsigned words[8]) {
        single=true;secondary={};return primary.capture_copied(first,words) && primary.white();
    }
    bool current() const { return primary.current() && (single || secondary.current()); }
};
static_assert(sizeof(Source)<=512,"bounded call-local source material proof");

// Actual uploaded RGB565 is little-endian, 8x8 twiddled even when a legacy
// linear package was twiddled by Package::upload(). GX RGB565 is big-endian
// in 4x4 tiles. Compare all texels, including the secondary, without assuming
// a cached source identity certifies the uploaded contents.
inline bool uploaded_texels(const volatile std::uint32_t* upload,const TextureSource& source) {
    std::uint32_t words[32];
    for(unsigned i=0;i<32;++i)words[i]=upload[i];
    for(unsigned y=0;y<8;++y)for(unsigned x=0;x<8;++x){
        const unsigned twiddle=(y&1U)|((x&1U)<<1)|((y&2U)<<1)|((x&2U)<<2)|((y&4U)<<2)|((x&4U)<<3);
        const unsigned gx=(((y/4)*2+x/4)*16+(y%4)*4+x%4)*2;
        const unsigned expected=unsigned(source.texels[gx])*256U+source.texels[gx+1];
        if(((words[twiddle/2]>>((twiddle&1U)*16))&65535U)!=expected)return false;
    }
    return true;
}
}
