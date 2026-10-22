#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
extern "C" void re4dc_backface_sh4_trace(const void*,const uint8_t*,unsigned,unsigned);
static std::vector<std::array<uint32_t,8>> got;
extern "C" void re4dc_ta_hash(const void* data,unsigned bytes) {
    assert(bytes==32);
    std::array<uint32_t,8> v;
    std::memcpy(v.data(),data,32);
    got.push_back(v);
}
int main() {
    std::array<std::array<uint32_t,8>,256> cache{};
    for(unsigned i=0;i<256;++i)
        for(unsigned w=0;w<8;++w) cache[i][w]=0x7f800001u ^ (i<<12) ^ (w<<4);
    const uint8_t indices[]={1,0x82,255,0};
    for(unsigned mask: {255u,127u,0x17fu})
        for(unsigned n: {0u,1u,3u,4u}) {
            got.clear();
            re4dc_backface_sh4_trace(cache.data(),indices,n,mask);
            assert(got.size()==n);
            for(unsigned k=0;k<n;++k) {
                auto expected=cache[indices[k] & (mask&255u)];
                if((mask&255u)==127u) expected[0]=0xe0000000u;
                if(k+1==n) expected[0]=0xf0000000u;
                assert(got[k]==expected);
            }
        }
}
