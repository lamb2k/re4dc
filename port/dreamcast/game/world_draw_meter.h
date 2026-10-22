#pragma once
#if defined(RE4DC_WORLD_DRAW_METER) && RE4DC_WORLD_DRAW_METER
#include <stdint.h>

namespace re4dc { namespace worldmeter {
enum Pass : unsigned { Opaque, PunchThrough, Translucent, FarShell, PassCount };
constexpr unsigned kWindow = 60;
struct Identity { unsigned room=0, generation=0; };
inline bool same(Identity a, Identity b) { return a.room==b.room && a.generation==b.generation; }
struct Snapshot {
    unsigned valid=0, room=0, generation=0, view_mm=0, first=0, last=0, samples=0;
    unsigned view_setting=~0u, far_mm[3]{}, shell_frames=0, shell_ok_frames=0;
    unsigned mean_us=0, peak_us=0, pass_us[PassCount]{};
    unsigned read_frames=0, stopped_frames=0, disc_known=0;
};
// No allocation and no timing dependencies: exercised with real aggregation on the host.
class Meter {
    Identity identity_{};
    Snapshot completed_{}, window_{};
    unsigned frame_=0, mask_=0, view_=0, read_start_=0, setting_=~0u, far_[3]{};
    uint64_t total_=0, pass_total_[PassCount]{};
    unsigned elapsed_[PassCount]{};
    bool open_=false, bad_=false, stopped_=false, disc_known_=false, shell_ok_=false;
    void clear_window() { completed_={}; window_={}; total_=0; for(auto& p:pass_total_)p=0; }
public:
    void reset() { *this=Meter{}; }
    void begin(unsigned frame, Identity id, bool disc_known, unsigned reads, bool stopped, unsigned setting=~0u) {
        // A missing end cannot contribute a partial frame to a later sample window.
        if(open_ || !same(id,identity_) || setting!=setting_)clear_window();
        identity_=id; frame_=frame; open_=true; bad_=false; mask_=view_=0;
        setting_=setting; shell_ok_=false; for(auto& f:far_)f=0;
        for(auto& p:elapsed_)p=0;
        read_start_=reads; disc_known_=disc_known; stopped_=stopped;
    }
    void pass(unsigned frame, Pass p, unsigned start, unsigned end, bool ok, unsigned view) {
        if(!open_ || frame!=frame_ || unsigned(p)>=PassCount)return;
        const unsigned bit=1u<<unsigned(p);
        if(mask_&bit)bad_=true; // Repeated entry is not a second world pass.
        mask_|=bit; elapsed_[p]=unsigned(end-start);
        if(p==FarShell)shell_ok_=ok;
        else {
            bad_=bad_ || !ok; far_[p]=view;
            if((window_.samples && window_.far_mm[p]!=view) ||
               (completed_.valid && completed_.far_mm[p]!=view))clear_window();
        }
        if(p==Opaque) {
            view_=view;
            if(!view || (window_.samples && window_.view_mm!=view) ||
               (completed_.valid && completed_.view_mm!=view))clear_window();
        }
    }
    void end(unsigned frame, Identity id, bool admitted, bool disc_known, unsigned reads, bool stopped) {
        if(!open_ || frame!=frame_)return;
        open_=false;
        if(!same(id,identity_)) { identity_=id; clear_window(); return; }
        // Zero-world, incomplete, discarded and failed frames never leave stale results visible.
        if(!admitted || bad_ || (mask_&7u)!=7u || !view_) { clear_window(); return; }
        const unsigned shell=unsigned((mask_&(1u<<FarShell))!=0);
        if((window_.samples && (bool(window_.shell_frames)!=bool(shell) || bool(window_.shell_ok_frames)!=shell_ok_)) ||
           (completed_.valid && (bool(completed_.shell_frames)!=bool(shell) || bool(completed_.shell_ok_frames)!=shell_ok_)))clear_window();
        if(!window_.samples) {
            window_.room=id.room; window_.generation=id.generation; window_.view_mm=view_;
            window_.view_setting=setting_; for(unsigned p=0;p<3;++p)window_.far_mm[p]=far_[p];
            window_.first=frame; window_.disc_known=1;
        }
        uint64_t us=0;
        for(unsigned p=0;p<PassCount;++p) { us+=elapsed_[p]; pass_total_[p]+=elapsed_[p]; }
        total_+=us;
        if(us>window_.peak_us)window_.peak_us=unsigned(us);
        window_.last=frame; ++window_.samples;
        window_.shell_frames+=shell; window_.shell_ok_frames+=unsigned(shell_ok_);
        window_.disc_known&=unsigned(disc_known_ && disc_known);
        if(disc_known_ && disc_known && reads!=read_start_)++window_.read_frames;
        if(stopped_ || stopped)++window_.stopped_frames;
        if(window_.samples==kWindow) {
            window_.valid=1; window_.mean_us=unsigned(total_/kWindow);
            for(unsigned p=0;p<PassCount;++p)window_.pass_us[p]=unsigned(pass_total_[p]/kWindow);
            completed_=window_; window_={}; total_=0; for(auto& p:pass_total_)p=0;
        }
    }
    Snapshot snapshot(Identity id, unsigned setting=~0u) const { return !open_ && same(id,identity_) && setting==setting_?completed_:Snapshot{}; }
};

unsigned clock_us();
void record(Pass pass, unsigned start, unsigned end, bool ok, float view);
template<class F> auto measure(Pass pass, float view, F call) -> decltype(call()) {
    const unsigned start=clock_us();
    const auto result=call();
    const unsigned end=clock_us();
    record(pass,start,end,result>0,view); // Source-world -1 is a failure, not success.
    return result;
}
}}
extern "C" void re4dc_world_meter_begin(unsigned frame);
extern "C" void re4dc_world_meter_end(unsigned frame, int drawn);
extern "C" void re4dc_world_meter_reset();
// Receipts describe guarded renderer submission/resolve decisions, not physical display.
extern "C" unsigned re4dc_world_meter_token();
extern "C" void re4dc_world_meter_outcome(unsigned token, unsigned frame, int accepted);
extern "C" re4dc::worldmeter::Snapshot re4dc_world_meter_snapshot(unsigned room);
#define RE4DC_WORLD_MEASURE(pass,view,expr) re4dc::worldmeter::measure(re4dc::worldmeter::pass,view,[&](){return (expr);})
#else
#define RE4DC_WORLD_MEASURE(pass,view,expr) (expr)
#endif
