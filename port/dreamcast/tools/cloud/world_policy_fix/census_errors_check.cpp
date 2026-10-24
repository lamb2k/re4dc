// The actual core is included unchanged, allowing explicit synthetic boundary
// state injection without adding production test APIs. No timing evidence.
#include <cassert>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>
#include "world_census24.h"
#if RE4DC_PERF_PHASE_MISS
#include "perf_phase_miss.h"
#endif
static uint64_t fixture_now=1000,pm_value;
static uintptr_t fixture_thread=1;
static unsigned fixture_tick=1,fixture_room=0x101,fixture_key[7];
static std::vector<std::string> fixture_logs;
extern "C" uint64_t re4dc_wc24_test_clock(){return fixture_now;}
extern "C" uintptr_t re4dc_wc24_test_thread(){return fixture_thread;}
extern "C" void re4dc_wc24_test_log(const char* s){fixture_logs.emplace_back(s);}
extern "C" void re4dc_wc24_identity(unsigned out[7]){std::memcpy(out,fixture_key,sizeof(fixture_key));}
#if RE4DC_PERF_PHASE_MISS
static unsigned pm_event,pm_clock,pm_reads,pm_config,pm_starts,pm_stops,control_read;
static bool pm_running,calibrating;
extern "C" uint64_t re4dc_ppm14_test_clock(){fixture_now+=100;return fixture_now;}
extern "C" uintptr_t re4dc_ppm14_test_thread(){return fixture_thread;}
extern "C" bool re4dc_ppm14_test_config(unsigned c,unsigned* e,unsigned* k){assert(c==1);++pm_config;*e=pm_event;*k=pm_clock;return pm_running;}
extern "C" void re4dc_ppm14_test_start(unsigned c,unsigned e){assert(c==1&&!pm_running);++pm_starts;pm_running=true;pm_event=e;pm_clock=0;pm_value=0;}
extern "C" void re4dc_ppm14_test_stop(unsigned c){assert(c==1&&pm_running);++pm_stops;pm_running=false;}
extern "C" uint64_t re4dc_ppm14_test_count(unsigned c){
    assert(c==1&&pm_running);++pm_reads;
    if(calibrating){if(control_read&1U){const unsigned sample=control_read/2;
        pm_value+=(((sample/2)&1U)^(sample&1U))?400000:12;}++control_read;}
    return pm_value;
}
extern "C" void re4dc_ppm14_test_log(const char* s){fixture_logs.emplace_back(s);}
extern "C" void* re4dc_ppm14_test_alloc(unsigned align,unsigned bytes){assert(align==32);calibrating=true;control_read=0;return aligned_alloc(align,bytes);}
extern "C" void re4dc_ppm14_test_free(void* p){calibrating=false;free(p);}
#endif
#include RE4DC_WORLD_CENSUS24_SOURCE
namespace wc=re4dc::wc24;
using namespace re4dc::wc24;
#if RE4DC_WORLD_CENSUS24_ERRORS
#define REASON(x) unsigned(x)
#define SITE(x) unsigned(x)
#else
#define REASON(x) 0U
#define SITE(x) 0U
#endif
static void advance(unsigned amount){fixture_now+=amount;
#if RE4DC_PERF_PHASE_MISS
    if(pm_running)pm_value+=amount;
#endif
}
static void begin(){wc::reset();fixture_now=1000;fixture_tick=1;wc::begin_tick(fixture_tick,fixture_room);}
static void finish(unsigned delta=100){
    wc::decision(true);wc::scene_finished();wc::decision_posted(true);wc::end_tick();
    advance(delta);wc::begin_tick(++fixture_tick,fixture_room);
}
static void seal(unsigned count=300){for(unsigned i=0;i<count;++i)finish();}
static void emit(unsigned reason,unsigned site,uint32_t a=0,uint32_t b=0){
#if RE4DC_WORLD_CENSUS24_ERRORS
    wc::fault(static_cast<ErrorReason>(reason),static_cast<ErrorSite>(site),a,b);
#else
    (void)reason;(void)site;(void)a;(void)b;wc::fault();
#endif
}
static uint32_t context(unsigned path,unsigned phase,unsigned wait=0){return path|(phase<<3)|(wait<<6);}
#if RE4DC_WORLD_CENSUS24_ERRORS
static ErrorSnapshot diagnostic(){
    ErrorSnapshot d{};assert(wc::errors_snapshot(&d));Snapshot s{};assert(wc::snapshot(&s));
    assert(d.sequence==s.sequence&&d.room==s.identity[0]&&d.first_tick==s.first_tick&&d.last_tick==s.last_tick&&d.total==s.errors);
    assert(d.used<=ErrorBinCapacity);uint32_t sum=d.spill;
    for(unsigned i=0;i<d.used;++i)sum+=d.bins[i].count;
    assert(sum==d.total);return d;
}
static void expect_bin(unsigned reason,unsigned site,unsigned ctx,unsigned count,uint32_t a,uint32_t b,unsigned first=1){
    const auto d=diagnostic();const auto key=reason|(site<<8)|(ctx<<16);
    for(unsigned i=0;i<d.used;++i)if(d.bins[i].key==key){
        const auto& bin=d.bins[i];assert(bin.count==count&&bin.detail0==a&&bin.detail1==b&&bin.first_tick==first);return;
    }
    assert(false);
}
#define EXPECT_BIN(...) expect_bin(__VA_ARGS__)
#else
#define EXPECT_BIN(...) do{}while(0)
#endif
static void mix(uint64_t& h,uint64_t v){h=(h^uint32_t(v))*1099511628211ULL;h=(h^uint32_t(v>>32))*1099511628211ULL;}
static uint64_t digest(const Snapshot& s){
    uint64_t h=1469598103934665603ULL;mix(h,s.sequence);for(auto v:s.identity)mix(h,v);
    for(auto v:{s.first_tick,s.last_tick,s.ticks,s.draw_attempts,s.drawn,s.skipped,s.scenes,s.present_requests,s.discard_requests,s.errors})mix(h,v);
    mix(h,s.wall_us);mix(h,s.max_tick_us);mix(h,uint64_t(s.residual_us));
    for(const auto& row:s.phase_us)for(auto v:row)mix(h,v);
    for(auto v:s.wait_us)mix(h,v);for(const auto& row:s.counters)for(auto v:row)mix(h,v);
    const auto& p=s.presentation;
    for(auto v:{p.vblanks,p.flips,p.render_starts,p.render_dones,p.intervals,p.gaps_over_two_fields,p.max_fields,p.discontinuities})mix(h,v);
    mix(h,p.interval_us);mix(h,p.min_interval_us);mix(h,p.max_interval_us);return h;
}
static void report(const char* name,unsigned errors){
    Snapshot s{};assert(wc::snapshot(&s)&&s.errors==errors&&s.drawn==300&&s.ticks==300);
#if RE4DC_WORLD_CENSUS24_ERRORS
    const auto d=diagnostic();assert(d.total==errors);
    std::fprintf(stderr,"DIAG used=%u spill=%u wrapped=%u\n",d.used,d.spill,d.wrapped);
#endif
    char text[256];for(unsigned i=0;i<wc::line_count();++i){const int n=wc::format_line(i,text,sizeof(text));assert(n>=0&&n<int(sizeof(text)));}
    for(const auto& line:fixture_logs)assert(line.size()<240&&line.find("format_overflow")==std::string::npos);
    std::printf("{\"case\":\"%s\",\"errors\":%u,\"ticks\":%u,\"drawn\":%u,\"snapshot_digest\":\"%016llx\"}\n",
        name,s.errors,s.ticks,s.drawn,(unsigned long long)digest(s));
}
int main(int argc,char** argv){
    assert(argc==2);const std::string name=argv[1];begin();unsigned expected=0;
    if(name=="empty"){seal();}
    else if(name=="unspecified"){
        {Scope s(NearOP,Other);wc::fault();assert(fixture_logs.empty());}seal();expected=1;
        EXPECT_BIN(ErrorUnspecified,ErrorSiteUnspecified,context(1,Other),1,0,0);
    }else if(name=="typed-wait"){
        {Scope s(FarPT,Clip);WaitScope wait(PvrWait);emit(REASON(ErrorPassIncomplete),SITE(ErrorPs2Pass),7,9);}
        seal();expected=1;EXPECT_BIN(ErrorPassIncomplete,ErrorPs2Pass,context(5,Clip,1),1,7,9);
    }else if(name=="repeat"){
        {Scope s(NearTR,Selection);emit(REASON(ErrorPassIncomplete),SITE(ErrorPs2Pass),11,22);}
        finish();{Scope s(NearTR,Selection);emit(REASON(ErrorPassIncomplete),SITE(ErrorPs2Pass),33,44);}
        seal(299);expected=2;EXPECT_BIN(ErrorPassIncomplete,ErrorPs2Pass,context(3,Selection),2,11,22);
    }else if(name=="different-contexts"){
        for(unsigned p=0;p<2;++p)for(unsigned ph=0;ph<2;++ph){Scope s{Path(p),Phase(ph)};emit(REASON(ErrorPassIncomplete),SITE(ErrorPs2Pass),p,ph);}
        seal();expected=4;
#if RE4DC_WORLD_CENSUS24_ERRORS
        assert(diagnostic().used==4);
#endif
    }else if(name=="spill" || name=="spill-sum-wrap" || name=="formatter"){
        for(unsigned p=0;p<6;++p)for(unsigned ph=0;ph<6;++ph){Scope s{Path(p),Phase(ph)};emit(REASON(ErrorPassIncomplete),SITE(ErrorPs2Pass),p,ph);}
        expected=36;
        if(name=="spill"){{Scope s(NearOP,Selection);emit(REASON(ErrorPassIncomplete),SITE(ErrorPs2Pass),99,99);}++expected;}
        else {
            // Synthetic boundary injection checks modulo reporting without
            // pretending billions of faults ran in a real frame.
            wc::current.errors=UINT32_MAX;
#if RE4DC_WORLD_CENSUS24_ERRORS
            wc::errors_live.spill=UINT32_MAX-32U;
            for(unsigned i=0;i<32;++i)wc::errors_live.bins[i].count=1;
#endif
            {Scope s(FarTR,Other);emit(REASON(ErrorPassIncomplete),SITE(ErrorPs2Pass));}
            expected=0;
            if(name=="formatter"){
                wc::current.errors=UINT32_MAX-31U;
#if RE4DC_WORLD_CENSUS24_ERRORS
                wc::errors_live.spill=0;
                for(unsigned i=0;i<32;++i){auto& b=wc::errors_live.bins[i];b.count=UINT32_MAX;b.first_tick=UINT32_MAX;b.detail0=b.detail1=UINT32_MAX;}
#endif
            }
        }
        if(name=="formatter")expected=UINT32_MAX-31U;
        seal();
#if RE4DC_WORLD_CENSUS24_ERRORS
        const auto d=diagnostic();assert(d.used==32);
        if(name=="spill")assert(d.spill==4&&!d.wrapped);
        else assert(d.wrapped);
        if(name=="formatter"){
            char line[256];for(unsigned i=0;i<wc::errors_line_count();++i){const int n=wc::errors_format_line(i,line,sizeof(line));assert(n>0&&n<256);
                // QA's existing 320/640-width chunking covers every byte.
                for(unsigned cols:{43U,96U}){std::string rebuilt;for(unsigned at=0;at<unsigned(n);at+=cols)rebuilt.append(line+at,std::min(cols,unsigned(n)-at));assert(rebuilt==line);}
            }
        }
#endif
    }else if(name=="clock-reverse"){
        const auto t=wc::enter(NearOP,Selection);fixture_now=999;wc::leave(t);seal();expected=1;
        EXPECT_BIN(ErrorClockReversed,ErrorCoreCharge,context(1,Selection),1,1000,999);
    }else if(name=="tick-reverse"){
        fixture_now=900;finish(0);seal(299);expected=2;
        EXPECT_BIN(ErrorClockReversed,ErrorCoreCharge,0,1,1000,900);
        EXPECT_BIN(ErrorTickReversed,ErrorCoreFinish,0,1,1000,900);
    }else if(name=="phase-overrun"){
        const auto t=wc::enter(NearOP,Selection);fixture_now=1100;wc::set_phase(Transform);
        fixture_now=1050;wc::set_phase(Clip);fixture_now=1100;wc::leave(t);finish(0);seal(299);expected=2;
        EXPECT_BIN(ErrorClockReversed,ErrorCoreCharge,context(1,Transform),1,1100,1050);
        EXPECT_BIN(ErrorPhaseOverrun,ErrorCoreFinish,0,1,150,100);
    }else if(name=="scope-depth"){
        uint32_t tokens[64];for(auto& t:tokens)t=wc::enter(NearOP,Selection);
        assert(tokens[63]==UINT32_MAX);for(unsigned i=64;i-->0;)wc::leave(tokens[i]);seal();expected=1;
#if RE4DC_WORLD_CENSUS24_ERRORS
        assert((diagnostic().bins[0].key&255u)==ErrorScopeDepth);
#endif
    }else if(name=="scope-order"){
        const auto a=wc::enter(NearOP,Selection),b=wc::enter(Transform);wc::leave(a);wc::leave(b);wc::leave(a);seal();expected=1;
#if RE4DC_WORLD_CENSUS24_ERRORS
        assert((diagnostic().bins[0].key&255u)==ErrorScopeOrder);
#endif
    }else if(name=="scope-unclosed"){
        const auto token=wc::enter(NearOP,Selection);finish();wc::leave(token);seal(299);expected=1;
        EXPECT_BIN(ErrorUnclosedScope,ErrorCoreFinish,context(1,Selection),1,1,257);
    }else if(name=="counter-overflow"){
        {Scope s(NearOP,Transform);wc::count(Corners,UINT32_MAX);wc::count(Corners);wc::count(Corners,3);}
        seal();expected=2;EXPECT_BIN(ErrorCounterSaturated,ErrorCoreCount,context(1,Transform),2,Corners,1);
        Snapshot s{};wc::snapshot(&s);assert(s.counters[NearOP][Corners]==UINT32_MAX);
    }else if(name=="foreign-owner"){
        {Scope s(NearOP,Selection);fixture_thread=2;wc::fault();emit(REASON(ErrorPassAbort),SITE(ErrorPs2Pass));wc::count(Corners,UINT32_MAX);fixture_thread=1;wc::fault();}
        seal();expected=1;
    }else if(name=="inactive"){
        wc::reset();wc::fault();emit(REASON(ErrorPassAbort),SITE(ErrorPs2Pass));wc::pause();wc::fault();wc::resume();wc::begin_tick(fixture_tick,fixture_room);seal();
    }else if(name=="partial-restart"){
        wc::fault();finish();wc::fault();wc::begin_tick(++fixture_tick,fixture_room);seal();
    }else if(name=="pause-before-seal"){
        wc::fault();finish();wc::fault();wc::pause();assert(!wc::snapshot(nullptr));
#if RE4DC_WORLD_CENSUS24_ERRORS
        assert(!wc::errors_snapshot(nullptr));
#endif
        wc::resume();wc::begin_tick(++fixture_tick,fixture_room);seal();
    }else if(name=="pause-keep" || name=="resume-fresh" || name=="identity-change"){
        wc::fault();seal();Snapshot old{};wc::snapshot(&old);wc::fault();wc::pause();wc::resume();
        Snapshot kept{};wc::snapshot(&kept);assert(digest(kept)==digest(old));
#if RE4DC_WORLD_CENSUS24_ERRORS
        assert(diagnostic().total==1);
#endif
        if(name=="pause-keep")expected=1;
        else{
            if(name=="identity-change")++fixture_key[6];
            wc::begin_tick(++fixture_tick,fixture_room);
            if(name=="identity-change"){assert(!wc::snapshot(nullptr));
#if RE4DC_WORLD_CENSUS24_ERRORS
                assert(!wc::errors_snapshot(nullptr));
#endif
            }
            seal();
        }
    }else if(name=="window-continuity"){
        wc::fault();seal();Snapshot a{};wc::snapshot(&a);assert(a.errors==1);wc::fault();wc::fault();seal();expected=2;
#if RE4DC_WORLD_CENSUS24_ERRORS
        const auto d=diagnostic();assert(d.sequence==a.sequence+1&&d.used==1&&d.bins[0].first_tick==301&&d.bins[0].count==2);
#endif
    }else if(name=="first-evidence"){
        {Scope s(FarOP,HeaderMaterial);
#if RE4DC_WORLD_CENSUS24_ERRORS
            ErrorDetail why;why.tag(ErrorFarShell,ErrorShellUnavailable);why.first(ErrorShellBindRefusal,11,22);
#endif
            s.phase(Submit);
#if RE4DC_WORLD_CENSUS24_ERRORS
            why.first(ErrorShellScratchRefusal,33,44);why.report();
#else
            wc::fault();
#endif
        }seal();expected=1;EXPECT_BIN(ErrorShellBindRefusal,ErrorFarShell,context(4,HeaderMaterial),1,11,22);
    }else if(name=="bin-wrap"){
        wc::fault();wc::current.errors=UINT32_MAX;
#if RE4DC_WORLD_CENSUS24_ERRORS
        wc::errors_live.bins[0].count=UINT32_MAX;
#endif
        wc::fault();seal();
#if RE4DC_WORLD_CENSUS24_ERRORS
        const auto d=diagnostic();assert(d.used==1&&d.bins[0].count==0&&d.wrapped);
#endif
    }else if(name=="unknown-reason"){
        emit(999,999,11,22);seal();expected=1;EXPECT_BIN(ErrorUnspecified,ErrorSiteUnspecified,0,1,11,22);
    }
#if RE4DC_PERF_PHASE_MISS
    else if(name=="pmu-composition"){
        namespace pm=re4dc::ppm14;
        wc::pause();assert(pm::run_controls());assert(pm::controls().qualification==pm::Simulated);
        wc::resume();fixture_now=100000;wc::begin_tick(++fixture_tick,fixture_room);
        {Scope s(NearOP,HeaderMaterial);advance(10);const unsigned reads=pm_reads,config=pm_config,starts=pm_starts,stops=pm_stops;
            emit(REASON(ErrorPassIncomplete),SITE(ErrorWorldDraw),4,5);
            assert(reads==pm_reads&&config==pm_config&&starts==pm_starts&&stops==pm_stops);
            advance(20);
        }
        seal();expected=1;pm::Snapshot p{};Snapshot c{};assert(pm::snapshot(&p)&&wc::snapshot(&c));
        assert(p.sequence==c.sequence&&p.drawn==300&&p.ticks==300&&p.qualification==pm::Simulated&&p.errors==pm::CensusFault);
        uint64_t total=0;for(auto n:p.bins)total+=n;assert(total==p.total);
        unsigned row=25;
#if RE4DC_WORLD_CENSUS24_ERRORS
        row+=wc::errors_line_count();
#endif
        char line[256];wc::format_line(row,line,sizeof(line));assert(!std::strncmp(line,"PM14 PRFC1",10));
        assert(wc::line_count()==row+pm::line_count());
        std::fprintf(stderr,"PMU simulated total=%llu reads=%u config=%u starts=%u stops=%u\n",
            (unsigned long long)p.total,pm_reads,pm_config,pm_starts,pm_stops);
    }
#endif
    else assert(false);
    report(name.c_str(),expected);
}
