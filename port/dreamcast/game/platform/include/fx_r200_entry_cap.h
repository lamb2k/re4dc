#ifndef RE4DC_FX_R200_ENTRY_CAP_H
#define RE4DC_FX_R200_ENTRY_CAP_H

#include <cstdint>

// A third, render-only queue arena. The room spill has already been acquired by
// the existing scalar path; this selector never allocates or consumes bytes.
// A caller that can build its packet decrements the returned cursor exactly once.
namespace re4dc { namespace fx_r200 {
constexpr unsigned kTailBytes=8192;

enum class Result : unsigned {
    Accepted=0, OtherRoom, RoomClosed, NoRoomSpill, StaleGeneration,
    WrongSpill, NoTail, InvalidStorage, Overlap, BadRequest,
    SpillAvailable, Exhausted, OwnerChanged
};

struct Context {
    unsigned room=0;
    bool room_live=false;
    unsigned generation=0;
    unsigned char* room_cell=nullptr;
    unsigned room_generation=0,room_bytes=0;
    unsigned char* spill=nullptr;
    unsigned spill_top=0,spill_bytes=0;
    unsigned char* tail=nullptr;
    unsigned tail_bytes=0;
};

struct Tail {
    unsigned char* data=nullptr;
    unsigned char* owner=nullptr;
    unsigned generation=0,top=0;
    bool poisoned=false;

    void reset(){data=nullptr;owner=nullptr;generation=top=0;poisoned=false;}

    Result select(const Context& c,unsigned required,unsigned char*& storage,unsigned*& cursor){
        if(poisoned)return Result::OwnerChanged;
        // Never rewind/rebind live FIFO storage on a room or slab change. Only
        // reset_deferred, after retirement/drain, may make it reusable again.
        if(data && (c.room!=0x200U || !c.room_live || c.generation!=generation ||
                    c.room_generation!=generation || c.room_cell!=owner ||
                    c.spill!=owner || c.tail!=data)){
            poisoned=true;return Result::OwnerChanged;
        }
        if(c.room!=0x200U)return Result::OtherRoom;
        if(!c.room_live)return Result::RoomClosed;
        if(!c.room_cell)return Result::NoRoomSpill;
        if(c.room_generation!=c.generation)return Result::StaleGeneration;
        if(c.spill!=c.room_cell || !c.room_bytes || c.spill_bytes!=c.room_bytes ||
           c.spill_top>c.spill_bytes)return Result::WrongSpill;
        if(!c.tail || c.tail_bytes<kTailBytes)return Result::NoTail;
        const std::uintptr_t cell=reinterpret_cast<std::uintptr_t>(c.room_cell);
        const std::uintptr_t tail=reinterpret_cast<std::uintptr_t>(c.tail);
        const std::uintptr_t last=~std::uintptr_t(0);
        if((cell&31U) || (tail&31U) || c.room_bytes>last-cell || kTailBytes>last-tail)
            return Result::InvalidStorage;
        if(cell<tail+kTailBytes && tail<cell+c.room_bytes)return Result::Overlap;
        if(!required || (required&31U))return Result::BadRequest;
        if(required<=c.spill_top)return Result::SpillAvailable;
        if(required>(data?top:kTailBytes))return Result::Exhausted;
        if(!data){data=c.tail;owner=c.room_cell;generation=c.generation;top=kTailBytes;}
        storage=data;cursor=&top;return Result::Accepted;
    }
};
}} // namespace re4dc::fx_r200

#endif
