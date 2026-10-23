#pragma once
#include <cstdint>
// Read-only accepted TA packet cursor. A payload continuation is never a PCW.
// Format rules match native_ui.cpp::tabin::feed_block's existing native walker.
namespace re4dc_gcasset {
struct PacketCursor {
    unsigned address=0;
    bool textured=false, first=false, continuation=false, vertex64=false, header=false;
    bool feed(const std::uint32_t* words,bool every_textured_vertex=false) {
        if(continuation) { continuation=false;return false; }
        const unsigned pcw=words[0],type=pcw>>29;
        if(type==4 || type==5) {
            const bool sprite=type==5,vol=(pcw&64)!=0,offset=(pcw&4)!=0;
            const unsigned color=(pcw>>4)&3;
            address=(words[3]&0x001fffffU)<<3;textured=(pcw&8)!=0;first=header=true;
            continuation=!sprite && ((!vol && color==2 && textured && offset) || (vol && color==2));
            vertex64=sprite || (textured && color==1) || (vol && textured);
            return false;
        }
        if(type!=7 || !header)return false;
        continuation=vertex64;
        if(!textured || (!first && !every_textured_vertex))return false;
        first=false;return true;
    }
};
}
