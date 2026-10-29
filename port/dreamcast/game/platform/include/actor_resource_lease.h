#pragma once
#include <cstdint>
struct Re4dcActorWorkspaceLease { unsigned slot=0,serial=0,epoch=0,bytes=0; };

// Separate pending ownership from the cache's existing submitted-scene pin.
// Token copies cannot double-release or release a reused slot. No serial wraps.
struct Re4dcActorTextureLease { std::uint32_t slot=0, serial=0; };
struct Re4dcActorStreamState { unsigned frame,invalid,resource,overflow; };
struct Re4dcUiImage;
extern "C" int re4dc_actor_texture_acquire(const Re4dcUiImage*,unsigned,unsigned,Re4dcActorTextureLease*);
extern "C" int re4dc_actor_texture_validate(const Re4dcActorTextureLease*);
extern "C" int re4dc_actor_texture_commit(const Re4dcActorTextureLease*);
extern "C" void re4dc_actor_texture_release(Re4dcActorTextureLease*);
extern "C" void re4dc_actor_texture_retire_all();
extern "C" int re4dc_actor_stream_state(Re4dcActorStreamState*);

namespace re4dc_actor {
template<unsigned Entries,unsigned Capacity=64> class TextureLeases {
    static_assert(Entries && Capacity && Capacity<=65535,"bounded lease table");
    struct Slot { std::uint32_t serial=0, frame=0, entry=0; };
    Slot slots_[Capacity]{};
    std::uint16_t refs_[Entries]{};
    std::uint32_t serial_;
public:
    constexpr explicit TextureLeases(std::uint32_t serial=0):serial_(serial){}
    TextureLeases(const TextureLeases&)=delete;
    TextureLeases& operator=(const TextureLeases&)=delete;
    bool pinned(unsigned entry)const{return entry<Entries && refs_[entry]!=0;}
    bool available()const{
        if(serial_==UINT32_MAX)return false;
        for(const auto& s:slots_)if(!s.serial)return true;
        return false;
    }
    bool acquire(unsigned entry,unsigned frame,Re4dcActorTextureLease& token){
        // Refuse overwriting any caller-held token, even an invalid/stale one.
        if(token.slot || token.serial || entry>=Entries || !available())return false;
        for(unsigned i=0;i<Capacity;++i)if(!slots_[i].serial){
            slots_[i]={++serial_,frame,entry};++refs_[entry];
            token={i+1,serial_};return true;
        }
        return false;
    }
    bool resolve(const Re4dcActorTextureLease& token,unsigned frame,unsigned& entry)const{
        if(!token.slot || token.slot>Capacity || !token.serial)return false;
        const auto& s=slots_[token.slot-1];
        if(s.serial!=token.serial || s.frame!=frame)return false;
        entry=s.entry;return true;
    }
    void release(Re4dcActorTextureLease& token){
        if(token.slot && token.slot<=Capacity && token.serial){
            auto& s=slots_[token.slot-1];
            if(s.serial==token.serial){--refs_[s.entry];s.serial=0;}
        }
        token={};
    }
    void retire_entry(unsigned entry){
        if(entry>=Entries)return;
        for(auto& s:slots_)if(s.serial && s.entry==entry)s.serial=0;
        refs_[entry]=0;
    }
#if RE4DC_ACTOR_EARLY_COARSE
    // A Trans ticket names the NEXT native UI frame. Keep only tickets that
    // name this exact frame; skipped, old and future frames are all revoked.
    // Forced owner/entry retirement remains unconditional below/above.
    void begin_frame(unsigned frame){
        for(auto& s:slots_)if(s.serial && s.frame!=frame){
            --refs_[s.entry];s.serial=0;
        }
    }
#endif
    void retire_frame(){
        for(auto& s:slots_)s.serial=0;
        for(auto& r:refs_)r=0;
    }
};
static_assert(sizeof(Re4dcActorTextureLease)==8,"SH4 token ABI");
}
