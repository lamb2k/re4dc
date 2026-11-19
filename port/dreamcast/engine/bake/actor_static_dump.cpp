// Run on the build host with the private generated header directories on the include path.
#include <cstdio>
#include <cstdint>
#include <cstdlib>
#include "ps2leon_runtime_handpack.h"
#include "ganado_cast_runtime_lod.h"
static void write(const void* p,size_t n){if(std::fwrite(p,1,n,stdout)!=n)std::abort();}
int main(){
    write(leon4k::bind,sizeof(leon4k::bind));write(ganadocast::bind,sizeof(ganadocast::bind));
    write(ganadocast::textures,sizeof(ganadocast::textures));
    const unsigned uv_bytes[]={sizeof(ganadocast::a0_i2_uv),sizeof(ganadocast::a0_i3_uv),sizeof(ganadocast::a1_i2_uv),sizeof(ganadocast::a1_i3_uv),sizeof(ganadocast::a2_i2_uv),sizeof(ganadocast::a2_i3_uv),sizeof(ganadocast::a3_i2_uv),sizeof(ganadocast::a3_i3_uv),sizeof(ganadocast::a4_i2_uv),sizeof(ganadocast::a4_i3_uv)};
    for(unsigned a=0;a<5;a++)for(unsigned r=2;r<4;r++){
        const auto &c=ganadocast::chunks[a][r];
        uint32_t count[]={c.position_count,c.normal_count,c.palette_count,c.stream_bytes,uv_bytes[2*a+r-2]};
        write(count,sizeof(count));write(c.positions,c.position_count*8);write(c.normals,c.normal_count*8);
        write(c.weights,c.palette_count*16);write(c.stream,c.stream_bytes);
        write(c.uv,uv_bytes[2*a+r-2]);
    }
}
