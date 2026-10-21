#include "world_rect_bind.h"
#include <cassert>
#include <cstdio>
#include <cstring>
using namespace re4dc::rect21;
int main(){
    unsigned accepted=0,rejected=0;
    for(const auto& r:qualified){
        float u=-123,v=456;
        assert(!adapt(r.crc,r.fnv,r.logical_width,r.logical_height,r.stored,u,v));
        assert(u==-123 && v==456);++rejected;
        assert(adapt(r.crc,r.fnv,r.logical_width,r.logical_height,r.stored,u,v,true));
        assert(u==r.u_scale && v==r.v_scale);++accepted;
        for(unsigned field=0;field<11;++field){
            Descriptor bad=r.stored;unsigned crc=r.crc,fnv=r.fnv,w=r.logical_width,h=r.logical_height;
            switch(field){
                case 0:crc^=1;break;case 1:fnv^=1;break;case 2:w^=1;break;case 3:h^=1;break;
                case 4:bad.width^=1;break;case 5:bad.height^=1;break;case 6:bad.format^=1;break;
                case 7:bad.flags^=1;break;case 8:bad.payload^=1;break;case 9:bad.bytes^=1;break;
                case 10:bad.checksum^=1;break;
            }
            u=-123;v=456;
            assert(!adapt(crc,fnv,w,h,bad,u,v,true));assert(u==-123 && v==456);++rejected;
        }
        // Load-time top-drop must not enter the selected representation path.
        Descriptor dropped=r.stored;dropped.flags|=1U<<30;u=-123;v=456;
        assert(!adapt(r.crc,r.fnv,r.logical_width,r.logical_height,dropped,u,v,true));
        assert(u==-123 && v==456);++rejected;
        const unsigned code=(unsigned(__builtin_ctz(r.stored.width))-3U)*8U+unsigned(__builtin_ctz(r.stored.height))-3U;
        assert(header_dimensions(0xffffffc0U|code,r.stored.width,r.stored.height));
        assert(!header_dimensions(code,r.stored.width/2,r.stored.height));
        assert(!header_dimensions(code,r.stored.width,r.stored.height/2));
    }
    assert(!header_dimensions(0,0,8));assert(!header_dimensions(0,8,0));
    assert(!header_dimensions(0,3,8));assert(!header_dimensions(0,8,2048));
    std::printf("selected=%u rejected=%u cached_extent_checks=%u\n",accepted,rejected,accepted*3+4);
}
