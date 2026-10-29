#include "platform/include/fallback_window35.h"
#include "platform/include/fallback_window35_core.hpp"
#include "platform/include/draw_fallback_audit.h"
#include "platform/include/fallback_audit29.h"
#include <cstdio>

#if !defined(RE4DC_FALLBACK_WINDOW35) || RE4DC_FALLBACK_WINDOW35<1 || RE4DC_FALLBACK_WINDOW35>64
#error "FALLBACK_WINDOW35 must be 1..64 for the window translation unit"
#endif

namespace re4dc { namespace fw35 {
namespace {
using Window=Ring<dfa26::ReasonCount,fa29::ReasonCount,RE4DC_FALLBACK_WINDOW35>;
alignas(32) Window window{};
int checked(int n,char* out,unsigned capacity) {
    if(n<0 || unsigned(n)>=capacity){out[capacity-1]=0;return -1;}
    return n;
}
}
void begin_tick(uint32_t tick,uint32_t room) { window.begin(tick,room); }
void end_tick(bool draw,const uint32_t* dfa,uint32_t dfa_overflow,
              const uint32_t* fa,uint32_t fa_overflow,uint32_t outside_room) {
    window.end(draw,dfa,fa,(dfa_overflow?1U:0U)|(fa_overflow?2U:0U),outside_room);
}
void pause() { window.pause(); }
void resume() { window.resume(); }
void reset() { window.reset(); }
bool available() { return window.available(); }
uint64_t fa_sum(unsigned reason) { return reason<fa29::ReasonCount?window.sums[dfa26::ReasonCount+reason]:0; }
unsigned dfa_line_count() { return 3U+(window.available()?(dfa26::ReasonCount+3U)/4U:0U); }
int dfa_format_line(unsigned row,char* out,unsigned capacity) {
    if(!out || !capacity || row>=dfa_line_count())return -1;
    int n;
    if(!row)n=::snprintf(out,capacity,
        "F26W N=%u used=%u full=%u exact=%u room=%03x first=%u last=%u satrows=%u paused=%u reset=%u",
        Window::Capacity,window.used,unsigned(window.used==Window::Capacity),unsigned(window.exact()),
        unsigned(window.room),unsigned(window.first_draw_tick()),unsigned(window.last_draw_tick()),
        window.overflow_rows,unsigned(window.paused),unsigned(window.reset_cause));
    else if(row==1)n=::snprintf(out,capacity,
        "F26W logic=%llu draws=%llu skipped=%llu incomplete=%llu count_overflow=%u",
        static_cast<unsigned long long>(window.logic),static_cast<unsigned long long>(window.draws),
        static_cast<unsigned long long>(window.skipped),static_cast<unsigned long long>(window.incomplete),
        unsigned(window.counter_overflow));
    else if(row==2){
        if(window.available())n=::snprintf(out,capacity,
            "F26W span_logic=%llu span_skip=%llu outside_room=%u drawn_only=1 gpu_present=unobserved",
            static_cast<unsigned long long>(window.span_logic()),static_cast<unsigned long long>(window.span_skipped()),
            unsigned(window.outside_room));
        else n=::snprintf(out,capacity,"F26W collecting=1 span_logic=NA span_skip=NA drawn_only=1 gpu_present=unobserved");
    }else{
        n=::snprintf(out,capacity,"F26W");
        const unsigned first=(row-3U)*4U;
        for(unsigned i=first;i<dfa26::ReasonCount && i<first+4U;++i){
            if(n<0 || unsigned(n)>=capacity){out[capacity-1]=0;return -1;}
            const int added=::snprintf(out+n,capacity-unsigned(n)," %s=%llu",
                dfa26::label(static_cast<dfa26::Reason>(i)),static_cast<unsigned long long>(window.sums[i]));
            if(added<0){out[capacity-1]=0;return -1;}n+=added;
        }
    }
    return checked(n,out,capacity);
}
int fa_header(char* out,unsigned capacity) {
    if(!out || !capacity)return -1;
    const int n=::snprintf(out,capacity,
        "FA29W N=%u used=%u full=%u exact=%u first=%u last=%u collecting=%u sums=drawn_only",
        Window::Capacity,window.used,unsigned(window.used==Window::Capacity),unsigned(window.exact()),
        unsigned(window.first_draw_tick()),unsigned(window.last_draw_tick()),unsigned(!window.available()));
    return checked(n,out,capacity);
}
} }
