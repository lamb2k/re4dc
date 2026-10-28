#ifndef RE4DC_DRAW_FALLBACK_LINK26_HPP
#define RE4DC_DRAW_FALLBACK_LINK26_HPP

#include <cstdint>
#include <cstdio>
#include <cstring>

// Build 26's complete counter snapshot exceeds link28's bulk queue cap.
// Keep one snapshot, retry its unaccepted part, and never overwrite it with
// a newer tick. Existing transport admission and command priority stay intact.
namespace re4dc { namespace dfa26 {
template<unsigned Capacity>
struct Telemetry {
    char text[Capacity]{};
    unsigned length=0, offset=0, sequence=0, stamp=0, parts=0;
    std::uint64_t retry_at=0;
    bool pending=false;
    void cancel() { pending=false; offset=length=0; retry_at=0; }
    bool begin(unsigned bytes, unsigned seq, unsigned ms) {
        if (pending || bytes>Capacity) return false;
        length=bytes; offset=0; sequence=seq; stamp=ms;
        parts=bytes?(bytes+1099U)/1100U:1U;
        retry_at=0; pending=true; return true;
    }
    template<class Send>
    bool step(std::uint64_t now, Send&& send) {
        if (!pending || now<retry_at) return false;
        retry_at=now+50U; // at most20 attempts/second, including heap/backlog refusals
        const unsigned remaining=length-offset;
        const unsigned n=remaining<1100U?remaining:1100U;
        char packet[1164];
        const int h=::snprintf(packet,sizeof(packet),"T %u %u %u/%u\n",
            sequence,stamp,offset/1100U+1U,parts);
        if (h<0 || unsigned(h)+n>1200U || unsigned(h)+n>sizeof(packet)) {
            cancel(); return false;
        }
        std::memcpy(packet+h,text+offset,n);
        if (!send(packet,unsigned(h)+n)) return false;
        offset+=n;
        if (offset==length) pending=false;
        return true;
    }
};
} }
#endif
