#pragma once
#include <cstdint>

namespace re4dc { namespace texture {
// Copied metadata for one immutable disc room. No texture payload, archive pointer or heap allocation.
struct ResidentListRecord {
    std::uint16_t room,width,height,format;
    std::uint32_t crc,fnv;
};
static_assert(sizeof(ResidentListRecord)==16,"resident list record");
class ResidentListCache {
public:
    static constexpr unsigned kRecords=256;
    bool matches(unsigned room)const{return valid_ && room_==room;}
    void begin(unsigned room){room_=room;count_=0;valid_=false;overflow_=false;}
    void append(const ResidentListRecord& r){
        // Other rooms cannot affect this pass. Zero-width core padding has no parser side effects.
        // Preserve every own-room row and nonzero-width core row, including malformed ones: the
        // original admission/core-pin checks still decide their behavior on every replay.
        if((r.room && r.room!=room_) || (!r.room && !r.width))return;
        if(count_==kRecords){overflow_=true;return;}
        records_[count_++]=r;
    }
    void finish(bool complete){valid_=complete && !overflow_;}
    const ResidentListRecord* data()const{return records_;}
    unsigned size()const{return count_;}
private:
    ResidentListRecord records_[kRecords]{};
    unsigned room_=0,count_=0;
    bool valid_=false,overflow_=false;
};
static_assert(sizeof(ResidentListCache)<=4112,"resident cache metadata bound");
} }
