#pragma once
#include <cstdint>
#include <cmath>

namespace re4dc::pvs23 {
// R4PV v1 remains unchanged. Widen every product before comparing offsets.
template<class Head> bool layout(const Head& h,unsigned bytes){
    const std::uint64_t cells=std::uint64_t(h.nx)*h.nz;
    const std::uint64_t used=sizeof(Head)+8*cells+std::uint64_t(h.nsets)*h.set_bytes;
    return h.nx && h.nz && cells<=65536 && h.ninst && h.ninst<65536 &&
        h.nsets<=65535 && h.ncells<=cells && h.set_bytes==(h.ninst+7U)/8U &&
        used<=bytes && bytes-used<32 && !h.pad[0] && !h.pad[1] &&
        std::isfinite(h.x0) && std::isfinite(h.z0) && std::isfinite(h.cell) && h.cell>0 &&
        std::isfinite(h.x0+float(h.nx)*h.cell) && std::isfinite(h.z0+float(h.nz)*h.cell);
}
}
