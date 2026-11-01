// Exercises the actual observer and optional existing PM14 owner with a fake
// monotonic clock/registers. SIMULATED is never physical PMU qualification.
#include "draw_setup_audit.h"
#if RE4DC_PERF_PHASE_MISS
#include "perf_phase_miss.h"
#endif
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>
#include <vector>
namespace ds=re4dc::dsa24;
static uint64_t now,value;
static uintptr_t thread=1;
static unsigned key[7],logs,reads,starts,stops;
static std::vector<std::string> log_rows;
extern "C" uint64_t re4dc_dsa24_test_clock(){return now;}
extern "C" uintptr_t re4dc_dsa24_test_thread(){return thread;}
extern "C" void re4dc_dsa24_test_identity(unsigned* out){memcpy(out,key,sizeof(key));}
extern "C" void re4dc_dsa24_test_log(const char* s){++logs;log_rows.emplace_back(s);}
#if RE4DC_PERF_PHASE_MISS
namespace pm=re4dc::ppm14;
static unsigned event,clock_mode,control_read;
static bool running,calibrating;
extern "C" uint64_t re4dc_ppm14_test_clock(){now+=100;return now;}
extern "C" uintptr_t re4dc_ppm14_test_thread(){return thread;}
extern "C" bool re4dc_ppm14_test_config(unsigned c,unsigned* e,unsigned* m){assert(c==1);*e=event;*m=clock_mode;return running;}
extern "C" void re4dc_ppm14_test_start(unsigned c,unsigned e){assert(c==1&&!running);++starts;running=true;event=e;clock_mode=0;value=0;}
extern "C" void re4dc_ppm14_test_stop(unsigned c){assert(c==1&&running);++stops;running=false;}
extern "C" uint64_t re4dc_ppm14_test_count(unsigned c){
    assert(c==1&&running);++reads;
    if(calibrating){
        if(control_read&1U){const unsigned sample=control_read/2,pair=sample/2,arm=sample&1U;
            value+=((pair&1U)^arm)?400000:12;}
        ++control_read;
    }
    return value;
}
extern "C" void re4dc_ppm14_test_log(const char*){}
extern "C" void* re4dc_ppm14_test_alloc(unsigned alignment,unsigned bytes){calibrating=true;control_read=0;return aligned_alloc(alignment,bytes);}
extern "C" void re4dc_ppm14_test_free(void* p){calibrating=false;free(p);}
static void qualify(){assert(pm::run_controls());assert(pm::controls().qualification==pm::Simulated);}
#endif
static void advance(unsigned n){now+=n;value=(value+n)&((uint64_t(1)<<48)-1);}
static void begin(unsigned t){
#if RE4DC_PERF_PHASE_MISS
    pm::begin_tick(now);
#endif
    ds::begin_tick(t,0x103);
}
static void finish(){ds::scene_finished();ds::end_tick();}
static ds::Snapshot get(){ds::Snapshot s{};assert(ds::snapshot(&s));return s;}
static void empty(unsigned t,bool draw=true){begin(t);ds::decision(draw);advance(10);if(draw)ds::scene_finished();ds::end_tick();}
static void partition(){
#if RE4DC_PERF_PHASE_MISS
    qualify();
#endif
    const uint64_t start=now;
    for(unsigned t=0;t<3;++t){
        begin(t);ds::decision(true);advance(2);ds::begin_setup();advance(1);
        {ds::Scope before(ds::FrameBegin);advance(5);{ds::Scope submit(ds::Submit);advance(2);}}
        {ds::RenderScope render;advance(1);
            {ds::Scope model(ds::ModelList);advance(3);ds::count(ds::Models);ds::count(ds::TrianglesIn,5);
                {ds::Scope clip(ds::Clip);advance(7);{ds::Scope submit(ds::Submit);advance(2);}}
                ds::count(ds::TrianglesOut,4);advance(4);}
            {ds::Scope world(ds::WorldOpaque);advance(5);}
            advance(2);
        }
        ds::end_setup();finish();advance(10);
        assert(logs==0); // never formats in any phase/hot loop
    }
    begin(3);const auto s=get();assert(now-start==132);
    assert(s.ticks==3&&s.drawn==3&&s.attempts==3&&!s.skipped&&!s.errors);
    assert(s.wall_us==132&&s.setup_us==96&&s.render_us==72&&s.outside_us==36);
    assert(s.phase_us[ds::ModelList][ds::Work]==21);
    assert(s.phase_us[ds::ModelList][ds::Clip]==21&&s.phase_us[ds::ModelList][ds::Submit]==6);
    assert(s.phase_us[ds::FrameBegin][ds::Work]==15&&s.phase_us[ds::FrameBegin][ds::Submit]==6);
    assert(s.phase_us[ds::WorldOpaque][ds::Work]==15&&s.phase_us[ds::RenderOther][ds::Work]==12);
    assert(s.counters[ds::ModelList][ds::Models]==3&&s.counters[ds::ModelList][ds::TrianglesIn]==15&&s.counters[ds::ModelList][ds::TrianglesOut]==12);
    uint64_t sum=s.outside_us;for(auto& p:s.phase_us)for(auto q:p)sum+=q;assert(sum==s.wall_us);
#if RE4DC_PERF_PHASE_MISS
    assert(s.pm_qualification==pm::Simulated&&s.pm_samples&&!s.pm_gaps);
    assert(s.phase_events[ds::ModelList][ds::Clip]==21&&s.phase_events[ds::FrameBegin][ds::Submit]==6);
    assert(starts==2&&stops==1); // controls + original owner's start; DSA starts none
#else
    assert(s.pm_samples==0&&reads==0&&starts==0&&stops==0);
#endif
    assert(logs==1);
    for(unsigned row=0;row<ds::line_count();++row){char line[240];const int n=ds::format_line(row,line,sizeof(line));assert(n>0&&unsigned(n)<sizeof(line));}
    char zero[1]={'x'};assert(ds::format_line(0,zero,0)==0&&zero[0]=='x');
}
static void skipped(){
    for(unsigned t=0;t<6;++t)empty(t,t&1U);
    begin(6);const auto s=get();assert(s.ticks==6&&s.drawn==3&&s.skipped==3&&s.attempts==3&&s.wall_us==60);
}
static void lifecycle(){
    for(unsigned t=0;t<3;++t)empty(t);begin(3);const unsigned seq=get().sequence;
    const unsigned token=ds::enter(ds::ModelList);advance(100);ds::pause();advance(10000);ds::resume();ds::leave(token);
    assert(get().sequence==seq);
    for(unsigned t=4;t<7;++t)empty(t);begin(7);assert(get().wall_us==30&&!get().errors);
    ++key[6];begin(8);assert(!ds::snapshot(nullptr));
    for(unsigned t=9;t<12;++t)empty(t);begin(12);assert(get().identity[6]==1);
    ds::reset();assert(!ds::snapshot(nullptr));
}
static void nesting(){
    begin(0);ds::decision(true);
    const unsigned a=ds::enter(ds::WorldOpaque),b=ds::enter(ds::Clip);
    ds::leave(a); // deliberately out of order; fault remains visible
    advance(2);ds::leave(b);ds::leave(a);finish();
    for(unsigned t=1;t<3;++t)empty(t);begin(3);assert(get().errors&ds::ScopeOrder);
}
static void stale(){
    begin(0);const unsigned old=ds::enter(ds::WorldOpaque);ds::pause();ds::resume();
    begin(1);const unsigned current=ds::enter(ds::ModelList);ds::leave(old);advance(3);ds::leave(current);finish();
    empty(2);empty(3);begin(4);assert(!get().errors&&get().phase_us[ds::ModelList][ds::Work]==3);
}
static void alien(){
    begin(0);ds::decision(true);const unsigned before=reads;
    thread=2;{ds::Scope wrong(ds::ModelList);ds::count(ds::Models,99);ds::pause();ds::resume();ds::reset();}
    thread=1;assert(reads==before);advance(2);finish();empty(1);empty(2);begin(3);
    assert(!get().errors&&!get().counters[ds::ModelList][ds::Models]);
}
static void incomplete(){
    begin(0);advance(100); // no end_tick, dropped rather than admitted
    empty(1);empty(2);empty(3);begin(4);assert(get().wall_us==30&&get().first_tick==1);
}
static void backward(){
    now=100;begin(0);ds::decision(true);
    const unsigned token=ds::enter(ds::WorldOpaque);now=90;ds::leave(token);now=110;finish();
    empty(1);empty(2);begin(3);assert(get().errors&ds::ClockReversed);
}
static void depth_case(){
    begin(0);ds::decision(true);unsigned tokens[64];
    for(unsigned& t:tokens)t=ds::enter(ds::ModelList);
    assert(tokens[63]==ds::NoToken);
    for(int k=63;k>=0;--k)ds::leave(tokens[k]);finish();empty(1);empty(2);begin(3);
    assert(get().errors&ds::ScopeOrder);
}
static void invalid(){
    begin(0);ds::decision(true);assert(ds::enter(ds::PathCount)==ds::NoToken);
    ds::set_phase(ds::PhaseCount);ds::count(ds::CounterCount);finish();empty(1);empty(2);begin(3);
    assert(get().errors&ds::InvalidPhase);
}
#if RE4DC_PERF_PHASE_MISS
static void pm_loss(){
    qualify();begin(0);ds::decision(true);advance(10);
    {ds::Scope p(ds::ModelList);advance(5);event=event==15?37:15;}
    const unsigned stopped=stops;finish();empty(1);empty(2);begin(3);
    const auto s=get();assert(s.pm_gaps&&s.pm_qualification==pm::CounterLost&&stops==stopped);
    const unsigned r=reads;pm::AuditSample sample{};assert(!pm::read_audit_sample(&sample));assert(reads==r);
}
static void pm_unrun(){
    for(unsigned t=0;t<3;++t)empty(t);begin(3);const auto s=get();
    assert(s.pm_samples==0&&s.pm_qualification==pm::Unrun&&reads==0&&starts==0);
}
static void pm_wrap(){
    qualify();pm::begin_tick(now);value=(uint64_t(1)<<48)-3;ds::begin_tick(0,0x103);ds::decision(true);
    {ds::Scope p(ds::ModelList);advance(8);}finish();empty(1);empty(2);begin(3);
    const auto s=get();assert(s.pm_wraps==1&&!s.pm_gaps&&s.phase_events[ds::ModelList][ds::Work]==8);
}
#endif
int main(int argc,char** argv){
    assert(argc==2);const std::string name=argv[1];
    if(name=="partition")partition();else if(name=="skipped")skipped();else if(name=="lifecycle")lifecycle();
    else if(name=="nesting")nesting();else if(name=="stale")stale();else if(name=="alien")alien();
    else if(name=="incomplete")incomplete();else if(name=="backward")backward();else if(name=="depth")depth_case();
    else if(name=="invalid")invalid();
#if RE4DC_PERF_PHASE_MISS
    else if(name=="pm-loss")pm_loss();else if(name=="pm-unrun")pm_unrun();else if(name=="pm-wrap")pm_wrap();
#endif
    else assert(false);
    printf("PASS %s\n",name.c_str());
}
