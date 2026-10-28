#ifndef RE4DC_QA_LINK_REVIEW28_HPP
#define RE4DC_QA_LINK_REVIEW28_HPP

#include <cstdint>
#include <cstdio>
#include <cstring>

// QA_LINK_REVIEW28 only. One immutable snapshot owns the existing telemetry
// storage. Nothing here allocates, sleeps, touches the network or masks IRQs.
namespace re4dc { namespace ql28 {
template<unsigned Capacity>
struct Snapshot {
    char text[Capacity]{};
    char id[16]{};
    unsigned length=0, offset=0, sequence=0, stamp=0, parts=0;
    std::uint64_t retry_at=0;
    char kind=0; // begin sets the kind; keep the static snapshot entirely in BSS
    bool pending=false;
    void cancel() { pending=false; offset=length=0; retry_at=0; }
    bool begin(char type, const char* command, unsigned bytes, unsigned seq, unsigned ms) {
        if (pending || bytes>Capacity || (type!='T' && type!='D')) return false;
        if (type=='D' && (!command || std::strlen(command)>=sizeof(id))) return false;
        if (type=='D') std::strcpy(id,command); else id[0]=0;
        kind=type; length=bytes; offset=0; sequence=seq; stamp=ms;
        parts=bytes?(bytes+1099U)/1100U:1U;
        retry_at=0; pending=true; return true;
    }
    template<class Send>
    bool step(std::uint64_t now, Send&& send) {
        if (!pending || now<retry_at) return false;
        retry_at=now+50U;
        const unsigned remaining=length-offset;
        const unsigned n=remaining<1100U?remaining:1100U;
        char packet[1164];
        const int h=kind=='T'
            ? ::snprintf(packet,sizeof(packet),"T %u %u %u/%u\n",sequence,stamp,offset/1100U+1U,parts)
            : ::snprintf(packet,sizeof(packet),"D %s %u/%u\n",id,offset/1100U+1U,parts);
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

// Count bytes actually stored by snprintf, never its would-have-written count.
inline unsigned stored(int result, unsigned capacity) {
    return result<=0 || !capacity ? 0U : unsigned(result)>=capacity ? capacity-1U : unsigned(result);
}

// Exact integer order statistics for RECORD (at most1800 samples), with bounded
// O(n log n) work and constant scratch. Keep insertion sort's cheap ordered /
// nearly ordered case; after at most4*n shifts, finish with a heap. The old
// completion tick had an unbounded O(n^2) shift count.
inline void sift_ticks(unsigned* values, unsigned root, unsigned count) {
    const unsigned value=values[root];
    while (root<count/2U) {
        unsigned child=root*2U+1U;
        if (child+1U<count && values[child]<values[child+1U]) ++child;
        if (value>=values[child]) break;
        values[root]=values[child]; root=child;
    }
    values[root]=value;
}
inline void heap_ticks(unsigned* values, unsigned count) {
    if (count<2U) return;
    for (unsigned root=count/2U;root;) sift_ticks(values,--root,count);
    for (unsigned end=count-1U;end;--end) {
        const unsigned value=values[0]; values[0]=values[end]; values[end]=value;
        sift_ticks(values,0,end);
    }
}
inline void sort_ticks(unsigned* values, unsigned count) {
    if (count<2U) return;
    unsigned remaining=count*4U;
    for (unsigned i=1;i<count;++i) {
        const unsigned value=values[i];
        unsigned j=i;
        for (;j && values[j-1U]>value;--j) {
            values[j]=values[j-1U];
            if (!--remaining) {
                values[j-1U]=value; // retain the complete multiset before switching
                heap_ticks(values,count); return;
            }
        }
        values[j]=value;
    }
}
} }
#endif
