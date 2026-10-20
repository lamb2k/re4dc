#pragma once
#include <cstdint>
#include <cstring>

namespace re4dc { namespace motion {
// Metadata only. The loader owns all payloads, leases, memory admission and I/O.
// A ticket never pins a key or grants access to an archive/slot table.
struct ResumeTickets {
    std::uint32_t generation[4]{};
    std::uint32_t keys[4][8]{};
    bool contains(unsigned binding,unsigned entry) const {
        return binding<4 && entry<255 && (keys[binding][entry/32]&(1u<<(entry%32)));
    }
};
class ResumeJournal {
    std::uint32_t used_[4][8]{},previous_[4][8]{},evicted_[4][8]{};
    std::uint32_t generation_[4]{},movie_generation_[4]{};
    std::uint32_t frame_{};
    bool frame_valid_{},movie_{};
    void advance(std::uint32_t frame) {
        if(frame_valid_ && frame==frame_)return;
        if(frame_valid_ && frame-frame_==1u)std::memcpy(previous_,used_,sizeof used_);
        else std::memset(previous_,0,sizeof previous_);
        std::memset(used_,0,sizeof used_);frame_=frame;frame_valid_=true;
    }
public:
    // Call on successful bind and before unbind/retire. Clearing every per-slot
    // mask also prevents stale tickets on counter wrap or archive-address reuse.
    void binding_changed(unsigned binding) {
        if(binding>=4)return;
        if(!++generation_[binding])++generation_[binding];
        std::memset(used_[binding],0,sizeof used_[binding]);
        std::memset(previous_[binding],0,sizeof previous_[binding]);
        std::memset(evicted_[binding],0,sizeof evicted_[binding]);
    }
    std::uint32_t generation(unsigned binding) const { return binding<4?generation_[binding]:0; }
    // Only an actual successful source acquire belongs here. Bind preload alone
    // is not evidence that a key participates in the source working set.
    void acquired(unsigned binding,unsigned entry,std::uint32_t frame) {
        if(movie_ || binding>=4 || entry>=255 || !generation_[binding])return;
        advance(frame);used_[binding][entry/32]|=1u<<(entry%32);
    }
    bool begin_movie(std::uint32_t frame) {
        if(movie_)return false;
        advance(frame);std::memset(evicted_,0,sizeof evicted_);
        std::memcpy(movie_generation_,generation_,sizeof generation_);movie_=true;return true;
    }
    // Call only after an actual movie-owned heap-key eviction. Reserved fills,
    // pressure/OOM/equipment eviction and unrelated keys are not resume tickets.
    void movie_evicted(unsigned binding,unsigned entry) {
        if(!movie_ || binding>=4 || entry>=255 || !generation_[binding] ||
           generation_[binding]!=movie_generation_[binding])return;
        const auto bit=1u<<(entry%32);const auto word=entry/32;
        if((used_[binding][word]|previous_[binding][word])&bit)evicted_[binding][word]|=bit;
    }
    ResumeTickets finish_movie() {
        ResumeTickets out{};
        if(!movie_)return out;
        std::memcpy(out.generation,movie_generation_,sizeof movie_generation_);
        std::memcpy(out.keys,evicted_,sizeof evicted_);
        std::memset(evicted_,0,sizeof evicted_);movie_=false;return out;
    }
    void cancel_movie() { std::memset(evicted_,0,sizeof evicted_);movie_=false; }
    bool current(const ResumeTickets& tickets,unsigned binding) const {
        return binding<4 && generation_[binding] && tickets.generation[binding]==generation_[binding];
    }
};
static_assert(sizeof(ResumeJournal)<=448,"motion resume tracking must stay below448 bytes");
static_assert(sizeof(ResumeTickets)==144,"bounded four-binding resume ticket metadata");
}} // namespace re4dc::motion
