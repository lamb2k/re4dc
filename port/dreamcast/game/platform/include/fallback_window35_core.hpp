#ifndef RE4DC_FALLBACK_WINDOW35_CORE_HPP
#define RE4DC_FALLBACK_WINDOW35_CORE_HPP

#include <cstdint>

// Main-thread only. A row is one completed pace draw-attempt tick, not an
// asserted GPU presentation. Skipped and incomplete ticks never enter rows.
// Counter saturation marks that row inexact until it expires. The rolling
// sum itself is exact uint64 arithmetic for every allowed N and uint32 input.
namespace re4dc { namespace fw35 {
enum ResetCause { Startup, RoomChange, Resume, ExplicitReset };
template<unsigned FirstReasons,unsigned SecondReasons,unsigned N>
struct Ring {
    static_assert(FirstReasons && SecondReasons && N>=1 && N<=64,"bounded audit window");
    static constexpr unsigned Reasons=FirstReasons+SecondReasons,Capacity=N;
    struct Row {
        std::uint32_t items[Reasons];
        std::uint64_t ordinal;
        std::uint32_t tick, flags;
    };
    Row rows[N]{};
    std::uint64_t sums[Reasons]{};
    std::uint64_t logic=0, draws=0, skipped=0, incomplete=0;
    std::uint32_t room=0, tick=0, last_tick=0, outside_room=0, epoch=0;
    unsigned next=0, used=0, overflow_rows=0;
    ResetCause reset_cause=Startup;
    bool active=false, paused=false, have_room=false, counter_overflow=false;

    void clear(ResetCause why,bool keep_room) {
        // Old row storage is unreachable until rewritten; no N-row memset.
        for(auto& sum:sums)sum=0;
        logic=draws=skipped=incomplete=0;
        tick=last_tick=outside_room=0;next=used=overflow_rows=0;
        active=false;counter_overflow=false;reset_cause=why;++epoch;
        if(!keep_room){have_room=false;room=0;}
    }
    bool increment(std::uint64_t& value) {
        if(value==UINT64_MAX){counter_overflow=true;return false;}
        ++value;return true;
    }
    void reset() { clear(ExplicitReset,false);paused=false; }
    void pause() {
        if(active)increment(incomplete);
        active=false;paused=true;
    }
    void resume() { clear(Resume,true);paused=false; }
    void begin(std::uint32_t next_tick,std::uint32_t next_room) {
        if(paused)return;
        if(!have_room || next_room!=room){
            clear(RoomChange,false);have_room=true;room=next_room;
        }else if(active)increment(incomplete);
        tick=next_tick;active=true;
    }
    bool end(bool draw,const std::uint32_t* first,const std::uint32_t* second,
             std::uint32_t flags,std::uint32_t outside) {
        if(!active || paused)return false;
        active=false;last_tick=tick;outside_room=outside;
        if(draw && (!first || !second)){increment(incomplete);return false;}
        if(!increment(logic))return false;
        if(!draw){increment(skipped);return true;}
        if(!increment(draws))return false;
        Row& row=rows[next];
        const bool replace=used==N;
        if(replace)overflow_rows-=row.flags!=0;
        else ++used;
        for(unsigned i=0;i<FirstReasons;++i){
            if(replace)sums[i]-=row.items[i];
            row.items[i]=first[i];sums[i]+=first[i];
        }
        for(unsigned i=0;i<SecondReasons;++i){
            const unsigned to=FirstReasons+i;
            if(replace)sums[to]-=row.items[to];
            row.items[to]=second[i];sums[to]+=second[i];
        }
        row.ordinal=logic;row.tick=tick;row.flags=flags;
        overflow_rows+=flags!=0;
        if(++next==N)next=0;
        return true;
    }
    bool available() const { return used!=0; }
    bool exact() const { return available() && !overflow_rows && !counter_overflow; }
    unsigned oldest() const { return used==N?next:0; }
    unsigned newest() const { return next?next-1:N-1; }
    std::uint32_t first_draw_tick() const { return used?rows[oldest()].tick:0; }
    std::uint32_t last_draw_tick() const { return used?rows[newest()].tick:0; }
    std::uint64_t span_logic() const { return used?logic-rows[oldest()].ordinal+1:0; }
    std::uint64_t span_skipped() const { return used?span_logic()-used:0; }
};
} }
#endif
