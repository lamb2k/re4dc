// Actual census + PMU observer with synthetic register responses. Not hardware qualification.
#include "perf_phase_accounting.hpp"
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <string>
#include <vector>
namespace wc=re4dc::wc24;
namespace pm=re4dc::ppm14;
static uint64_t now, value;
static uintptr_t thread=1;
static unsigned event,clock_mode,config_calls,count_calls,starts,stops,allocations,frees;
static unsigned key[7],control_read;
static unsigned pm_log_events,wc_log_events;
static bool running,calibrating,contrast=true,allocation_fails,near_wrap;
static std::vector<std::string> logs;
extern "C" uint64_t re4dc_wc24_test_clock(){return now;}
extern "C" uintptr_t re4dc_wc24_test_thread(){return thread;}
extern "C" void re4dc_wc24_identity(unsigned out[7]){memcpy(out,key,sizeof(key));}
extern "C" void re4dc_wc24_test_log(const char* s){logs.emplace_back(s);now+=wc_log_events;if(running)value+=wc_log_events;}
extern "C" uint64_t re4dc_ppm14_test_clock(){now+=100;return now;}
extern "C" uintptr_t re4dc_ppm14_test_thread(){return thread;}
extern "C" bool re4dc_ppm14_test_config(unsigned counter,unsigned* e,unsigned* c){
    assert(counter==1&&thread==1);++config_calls;*e=event;*c=clock_mode;return running;
}
extern "C" void re4dc_ppm14_test_start(unsigned counter,unsigned e){
    assert(counter==1&&!running&&thread==1);++starts;event=e;clock_mode=0;running=true;value=0;
}
extern "C" void re4dc_ppm14_test_stop(unsigned counter){assert(counter==1&&running&&thread==1);++stops;running=false;}
extern "C" uint64_t re4dc_ppm14_test_count(unsigned counter){
    assert(counter==1&&running&&thread==1);++count_calls;
    if(near_wrap){value=(uint64_t(1)<<48)-4;near_wrap=false;}
    if(calibrating){
        if(control_read&1U){
            const unsigned sample=control_read/2,pair=sample/2,arm=sample&1U;
            const bool heavy=((pair&1U)^arm)!=0;
            value+=contrast?(heavy?400000:12):0;
        }
        ++control_read;
    }
    return value;
}
extern "C" void re4dc_ppm14_test_log(const char* s){assert(!calibrating);logs.emplace_back(s);now+=pm_log_events;if(running)value+=pm_log_events;}
extern "C" void* re4dc_ppm14_test_alloc(unsigned alignment,unsigned bytes){
    assert(alignment==32&&bytes==pm::ResidentBytes+pm::MissHeavyBytes);++allocations;
    if(allocation_fails)return nullptr;
    calibrating=true;control_read=0;return aligned_alloc(alignment,bytes);
}
extern "C" void re4dc_ppm14_test_free(void* p){assert(p);++frees;calibrating=false;free(p);}
static void advance(unsigned n){now+=n;if(running)value=(value+n)&((uint64_t(1)<<48)-1);}
static void qualify(){
    wc::pause();assert(pm::run_controls());const auto c=pm::controls();
    assert(c.qualification==pm::Simulated&&c.pairs==8&&!c.errors&&allocations==frees);
    for(unsigned i=0;i<8;++i)assert(c.resident[i]==12&&c.heavy[i]==400000);
    assert(!running);
}
static pm::Snapshot get(){pm::Snapshot s{};assert(pm::snapshot(&s));return s;}
static void empty(unsigned tick){wc::begin_tick(tick,0x101);wc::decision(true);advance(1);wc::scene_finished();wc::end_tick();}
static void partition(){
    qualify();
    for(unsigned t=0;t<300;++t){
        wc::begin_tick(t,0x101);wc::decision(true);advance(2);
        {
            wc::Scope world(wc::NearOP,wc::Other);advance(1);
            {wc::Scope select(wc::Selection);advance(3);
                const unsigned calls=count_calls;{wc::Scope same(wc::Selection);advance(2);}assert(count_calls==calls);}
            {wc::Scope transform(wc::Transform);advance(7);
                const unsigned calls=config_calls;thread=2;{wc::Scope alien(wc::FarTR,wc::Clip);pm::transition(1,now);}thread=1;assert(calls==config_calls);}
            {wc::Scope clip(wc::Clip);advance(10);{wc::Scope submit(wc::Submit);advance(3);}}
            {wc::Scope header(wc::HeaderMaterial);advance(2);}
            {wc::Scope submit(wc::Submit);advance(11);}
            advance(4);
        }
        {wc::WaitScope wait(wc::PvrWait);advance(13);const unsigned c=count_calls;
            {wc::WaitScope same(wc::PvrWait);advance(4);}assert(c==count_calls);}
        wc::scene_finished();wc::end_tick();advance(23);
    }
    wc::begin_tick(300,0x101);auto s=get();
    const uint64_t phases[]={5,7,10,2,14,5};
    for(unsigned p=0;p<6;++p)assert(s.bins[p]==phases[p]*300);
    assert(s.bins[pm::WaitBase]==17*300&&s.bins[pm::Residual]==25*300&&s.total==85*300);
    assert(s.qualification==pm::Simulated&&!s.errors&&s.drawn==300&&s.ticks==300);
    uint64_t sum=0;for(auto x:s.bins)sum+=x;assert(sum==s.total);
    char line[256];pm::summary(line,sizeof(line));assert(strstr(line,"valid=0"));
    assert(wc::line_count()==54);
    for(unsigned i=0;i<wc::line_count();++i){const int n=wc::format_line(i,line,sizeof(line));assert(n>=0&&n<int(sizeof(line)));}
    const unsigned calls=config_calls;assert(!pm::run_controls());assert(config_calls==calls);
    char small[80];pm::summary(small,sizeof(small));assert(strstr(small,"summary_overflow=1"));
}
static void pause_identity(){
    qualify();for(unsigned t=0;t<300;++t)empty(t);wc::begin_tick(300,0x101);const auto old=get();
    const uint32_t token=wc::enter(wc::NearOP,wc::Transform);advance(1000);wc::pause();
    assert(!running);advance(10000);wc::resume();wc::leave(token);assert(get().sequence==old.sequence);
    wc::pause();assert(pm::run_controls());assert(!pm::snapshot(nullptr));wc::resume();
    for(unsigned t=301;t<601;++t)empty(t);
    wc::begin_tick(601,0x101);
    assert(get().total==300&&!get().errors);
    ++key[6];wc::begin_tick(602,0x101);assert(!pm::snapshot(nullptr));
    for(unsigned t=603;t<903;++t)empty(t);
    wc::begin_tick(903,0x101);assert(get().identity[7]==1);
}
static void continuity(){
    qualify();pm_log_events=3;wc_log_events=7;
    for(unsigned t=0;t<300;++t)empty(t);
    wc::begin_tick(300,0x101);assert(get().total==300);
    wc::decision(true);advance(1);wc::scene_finished();wc::end_tick();
    for(unsigned t=301;t<600;++t)empty(t);
    wc::begin_tick(600,0x101);assert(get().total==310&&get().ticks==300&&!get().errors);
}
static void skipped(){
    qualify();
    for(unsigned t=0;t<600;++t){wc::begin_tick(t,0x101);wc::decision(t&1U);advance(2);if(t&1U)wc::scene_finished();wc::end_tick();}
    wc::begin_tick(600,0x101);const auto s=get();assert(s.drawn==300&&s.ticks==600&&s.total==1200);
}
static void accounting(){
    uint64_t delta;bool wrap;
    assert(pm::counter_delta(0xfffffffeULL,0x100000003ULL,1,delta,wrap)&&delta==5&&!wrap);
    assert(pm::counter_delta((uint64_t(1)<<48)-3,2,1,delta,wrap)&&delta==5&&wrap);
    assert(!pm::counter_delta(10000,0,1,delta,wrap));
    assert(!pm::counter_delta(0,uint64_t(1)<<48,1,delta,wrap));
    assert(!pm::counter_delta(0,1,60000001,delta,wrap));
    pm::Snapshot s{};s.total=UINT64_MAX;s.bins[0]=UINT64_MAX;
    assert(!pm::accumulate(s,0,1,false)&&s.total==UINT64_MAX);
    s={};s.samples=UINT32_MAX;assert(!pm::accumulate(s,0,1,false));
    s={};s.wraps=UINT32_MAX;assert(!pm::accumulate(s,0,1,true));
    assert(pm::effective_bin(0)==pm::Residual&&pm::effective_bin(1|(2<<3))==2);
    assert(pm::effective_bin(1|(2<<3)|(2<<6))==pm::WaitBase+1);
    assert(pm::effective_bin(7)==pm::BinCount);
}
static void wrap_case(){
    qualify();near_wrap=true;wc::begin_tick(0,0x101);advance(9);
    {wc::Scope world(wc::NearOP,wc::Other);advance(5);}wc::decision(true);wc::scene_finished();wc::end_tick();
    for(unsigned t=1;t<300;++t)empty(t);
    wc::begin_tick(300,0x101);
    const auto s=get();assert(s.wraps==1&&s.total==313&&!s.errors);
}
static void loss(const char* kind){
    qualify();wc::begin_tick(0,0x101);
    if(!strcmp(kind,"lost-mode"))event=0x23;
    if(!strcmp(kind,"lost-clock"))clock_mode=1;
    if(!strcmp(kind,"lost-stop"))running=false;
    const unsigned before_stop=stops;
    {wc::Scope world(wc::NearOP,wc::Selection);}
    assert(pm::controls().qualification==pm::CounterLost&&stops==before_stop);
    const unsigned before_calls=config_calls+count_calls+starts+stops;
    wc::pause();wc::resume();for(unsigned t=1;t<5;++t)empty(t);wc::pause();assert(!pm::run_controls());
    assert(before_calls==config_calls+count_calls+starts+stops);
}
static void busy(bool stopped){
    event=0x23;running=!stopped;wc::pause();assert(!pm::run_controls());
    assert(pm::controls().qualification==pm::CounterBusy&&!starts&&!stops&&!count_calls&&frees==allocations);
    const unsigned c=config_calls;assert(!pm::run_controls());wc::begin_tick(0,0x101);assert(config_calls==c);
}
static void invalid_case(const char* kind){
    qualify();wc::begin_tick(0,0x101);advance(2000);{wc::Scope world(wc::NearOP,wc::Other);}
    if(!strcmp(kind,"invalid-high"))value=uint64_t(1)<<48;
    if(!strcmp(kind,"invalid-reset"))value=0;
    if(!strcmp(kind,"invalid-clock"))now=0;
    {wc::Scope world(wc::NearOP,wc::Selection);}
    assert(pm::controls().errors&pm::InvalidSample);assert(!running);
    const unsigned reads=count_calls;wc::begin_tick(1,0x101);assert(reads==count_calls);
}
static void unqualified(bool allocation){
    if(allocation)allocation_fails=true;else contrast=false;
    wc::pause();assert(!pm::run_controls());assert(pm::controls().qualification==pm::Inconclusive);
    if(allocation){assert(pm::controls().errors==pm::AllocationFailed&&!starts&&!frees);return;}
    for(unsigned t=0;t<300;++t)empty(t);
    wc::begin_tick(300,0x101);
    const auto s=get();assert(s.qualification==pm::Inconclusive&&s.total==300);
    char line[256];pm::summary(line,sizeof(line));assert(strstr(line,"valid=0"));
}
static void census_fault(){
    qualify();for(unsigned t=0;t<300;++t){empty(t);if(t==10)wc::fault();}
    wc::begin_tick(300,0x101);assert(get().errors&pm::CensusFault);
}
static void unrun(){
    for(unsigned t=0;t<300;++t)empty(t);
    wc::begin_tick(300,0x101);
    const auto s=get();assert(s.qualification==pm::Unrun&&!s.samples&&!starts&&!config_calls&&!count_calls);
}
int main(int argc,char** argv){
    assert(argc==2);const std::string c=argv[1];
    if(c=="partition")partition();else if(c=="pause-identity")pause_identity();else if(c=="skipped")skipped();else if(c=="continuity")continuity();
    else if(c=="accounting")accounting();else if(c=="wrap48")wrap_case();
    else if(c.rfind("lost-",0)==0)loss(c.c_str());else if(c=="busy")busy(false);else if(c=="busy-stopped")busy(true);
    else if(c.rfind("invalid-",0)==0)invalid_case(c.c_str());else if(c=="no-contrast")unqualified(false);
    else if(c=="allocation")unqualified(true);else if(c=="census-fault")census_fault();else if(c=="unrun")unrun();
    else assert(false);
    printf("PASS %s: synthetic accounting only; no console event qualification\n",argv[1]);
}
