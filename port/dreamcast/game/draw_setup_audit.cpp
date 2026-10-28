// Build 24: bounded exclusive drawing-time observer. No allocation, renderer
// mutation, timer/PMU reads per vertex, or new performance-counter ownership.
#include "platform/include/draw_setup_audit.h"
#include <stdio.h>
#include <string.h>
#if defined(RE4DC_PERF_PHASE_MISS) && RE4DC_PERF_PHASE_MISS
#include "platform/include/perf_phase_accounting.hpp"
#endif

#ifndef RE4DC_DRAW_SETUP_AUDIT_WINDOW
#define RE4DC_DRAW_SETUP_AUDIT_WINDOW 300
#endif
#if !defined(RE4DC_DRAW_SETUP_AUDIT_HOST) && (RE4DC_DRAW_SETUP_AUDIT_WINDOW < 300 || RE4DC_DRAW_SETUP_AUDIT_WINDOW > 600)
#error DRAW_SETUP_AUDIT_WINDOW must be between 300 and 600 drawn ticks
#endif

#if defined(RE4DC_DRAW_SETUP_AUDIT_HOST)
extern "C" uint64_t re4dc_dsa24_test_clock();
extern "C" uintptr_t re4dc_dsa24_test_thread();
extern "C" void re4dc_dsa24_test_identity(unsigned*);
extern "C" void re4dc_dsa24_test_log(const char*);
static uint64_t clock_us(){return re4dc_dsa24_test_clock();}
static uintptr_t thread_id(){return re4dc_dsa24_test_thread();}
static void identity(unsigned* out){re4dc_dsa24_test_identity(out);}
static void log_line(const char* s){re4dc_dsa24_test_log(s);}
#else
#include <arch/timer.h>
#include <kos/thread.h>
extern "C" void re4dc_world_meter_identity(unsigned*);
extern "C" void re4dc_log(const char*,...);
static uint64_t clock_us(){return timer_us_gettime64();}
static uintptr_t thread_id(){return reinterpret_cast<uintptr_t>(thd_current);}
static void identity(unsigned* out){re4dc_world_meter_identity(out);}
static void log_line(const char* s){re4dc_log("%s\n",s);}
#endif

namespace re4dc { namespace dsa24 {
namespace {
struct Frame {
    Snapshot sums;
    uint64_t begin, last, setup_begin;
    uint32_t tick, setup_token;
    bool active, complete, attempt, finished, in_setup;
};
Frame current;
Snapshot window, sealed;
uint32_t key[IdentityWords], sequence, epoch=1, state;
uintptr_t owner;
bool have_key, have_sealed, paused;
#if defined(RE4DC_PERF_PHASE_MISS) && RE4DC_PERF_PHASE_MISS
ppm14::AuditSample previous_pm;
bool have_pm;
#endif
// Low four bits: path+1 (zero=outside named drawing); next two: phase;
// next six: nesting depth. The upper half of a token is its tick epoch.
unsigned path_word(){return state&15U;}
unsigned phase_word(){return (state>>4)&3U;}
unsigned depth(){return (state>>6)&63U;}
bool ours(){return current.active&&!paused&&owner==thread_id();}
void advance_epoch(){epoch=(epoch+1)&65535U;if(!epoch)epoch=1;}
void add(uint64_t& to,uint64_t value){
    if(value>UINT64_MAX-to){to=UINT64_MAX;current.sums.errors|=Overflow;}
    else to+=value;
}
void clear(bool erase_snapshot){
    current=Frame{};window=Snapshot{};state=0;advance_epoch();
#if defined(RE4DC_PERF_PHASE_MISS) && RE4DC_PERF_PHASE_MISS
    have_pm=false;
#endif
    if(erase_snapshot)have_sealed=false;
}
void sample_pm(uint64_t now){
#if defined(RE4DC_PERF_PHASE_MISS) && RE4DC_PERF_PHASE_MISS
    ppm14::AuditSample sample{};
    const bool valid=ppm14::read_audit_sample(&sample);
    current.sums.pm_event=sample.event;
    current.sums.pm_qualification=sample.qualification;
    uint64_t delta=0;bool wrapped=false;
    if(valid&&have_pm&&sample.generation==previous_pm.generation&&now>=current.last&&
       ppm14::counter_delta(previous_pm.value,sample.value,now-current.last,delta,wrapped)){
        if(path_word())add(current.sums.phase_events[path_word()-1][phase_word()],delta);
        else add(current.sums.outside_events,delta);
        ++current.sums.pm_samples;current.sums.pm_wraps+=wrapped;
    }else if(have_pm||valid){
        // A first reading seeds an interval. Any broken subsequent interval
        // stays visible; never present a missing PMU measurement as zero misses.
        if(have_pm)++current.sums.pm_gaps;
    }
    previous_pm=sample;have_pm=valid;
#else
    (void)now;
#endif
}
void charge(uint64_t now){
    sample_pm(now);
    if(now<current.last){current.sums.errors|=ClockReversed;current.last=now;return;}
    const uint64_t delta=now-current.last;
    if(path_word())add(current.sums.phase_us[path_word()-1][phase_word()],delta);
    else add(current.sums.outside_us,delta);
    current.last=now;
}
unsigned mean(uint64_t n,unsigned d){
    if(!d)return 0;
    const uint64_t q=n/d;return q>UINT32_MAX?UINT32_MAX:unsigned(q);
}
uint64_t named_us(const Snapshot& s){
    uint64_t n=0;for(unsigned p=0;p<PathCount;++p)for(unsigned q=0;q<PhaseCount;++q)n+=s.phase_us[p][q];return n;
}
uint64_t total_counter(const Snapshot& s,unsigned c){
    uint64_t n=0;for(unsigned p=0;p<PathCount;++p)n+=s.counters[p][c];return n;
}
const char* const paths[PathCount]={"WORLD OP/PT","WORLD TR","SHELL","MODELS","FRAME BEGIN","RENDER OTHER","OTHER DRAW"};
const char* pm_status(unsigned q){
    static const char* const names[]={"UNRUN","QUALIFIED","INCONCLUSIVE","SIMULATED","BUSY","LOST"};
    return q<6?names[q]:"INVALID";
}
void finish(uint64_t now){
    charge(now);
    if(depth()||current.in_setup)current.sums.errors|=Incomplete;
    if(now<current.begin)current.sums.errors|=ClockReversed;
    const uint64_t wall=now>=current.begin?now-current.begin:0;
    if(!window.ticks)window.first_tick=current.tick;
    window.last_tick=current.tick;++window.ticks;
    window.drawn+=current.finished;window.attempts+=current.attempt;
    window.skipped+=!current.attempt;window.scenes+=current.sums.scenes;
    window.errors|=current.sums.errors;
    add(window.wall_us,wall);add(window.setup_us,current.sums.setup_us);add(window.render_us,current.sums.render_us);
    if(wall>window.max_tick_us)window.max_tick_us=wall;
    for(unsigned p=0;p<PathCount;++p){
        for(unsigned q=0;q<PhaseCount;++q){
            add(window.phase_us[p][q],current.sums.phase_us[p][q]);
            add(window.phase_events[p][q],current.sums.phase_events[p][q]);
        }
        for(unsigned c=0;c<CounterCount;++c)add(window.counters[p][c],current.sums.counters[p][c]);
    }
    add(window.outside_us,current.sums.outside_us);add(window.outside_events,current.sums.outside_events);
    window.pm_event=current.sums.pm_event;window.pm_qualification=current.sums.pm_qualification;
    window.pm_samples+=current.sums.pm_samples;window.pm_gaps+=current.sums.pm_gaps;window.pm_wraps+=current.sums.pm_wraps;
    window.errors|=current.sums.errors;
    if(window.drawn>=RE4DC_DRAW_SETUP_AUDIT_WINDOW){
        window.sequence=++sequence;memcpy(window.identity,key,sizeof(key));
        sealed=window;have_sealed=true;window=Snapshot{};
        char row[240];summary(row,sizeof(row));log_line(row);
#if defined(RE4DC_BARN28_DIAG) && RE4DC_BARN28_DIAG
        // BARN28_DIAG (barn28.mk): every page row in the log too (Flycast runs read the per-path rows).
        for(unsigned i=0;i<line_count();++i){if(format_line(i,row,sizeof(row))>0)log_line(row);}
#endif
        // A bounded window summary only. Full per-path/counter data is sealed
        // for the paginated QA/QR display; nothing formats in a drawing loop.
    }
}
uint32_t enter_state(unsigned next){
    if(!ours())return NoToken;
    if(depth()==63){current.sums.errors|=ScopeOrder;return NoToken;}
    if((state&63U)!=(next&63U))charge(clock_us());
    const uint32_t token=(epoch<<16)|state;
    state=(next&63U)|((depth()+1)<<6);return token;
}
}

void begin_tick(uint32_t tick,uint32_t room){
    if(current.active&&owner!=thread_id()){current.sums.errors|=WrongThread;return;}
    const uint64_t now=clock_us();unsigned fresh[IdentityWords];identity(fresh);
    // Main's room is authoritative even if an external renderer key is stale.
    fresh[0]=room;
    const bool same=have_key&&!memcmp(key,fresh,sizeof(key));
    if(!same){clear(true);memcpy(key,fresh,sizeof(key));have_key=true;}
    else if(current.active){
        if(current.complete&&!paused)finish(now);else clear(false);
    }
    current=Frame{};advance_epoch();state=0;owner=thread_id();paused=false;
    current.begin=current.last=now;current.tick=tick;current.active=true;
#if defined(RE4DC_PERF_PHASE_MISS) && RE4DC_PERF_PHASE_MISS
    have_pm=false;sample_pm(now);
#endif
}
void end_tick(){if(ours())current.complete=true;}
void decision(bool attempt){if(ours())current.attempt=attempt;}
void scene_finished(){if(ours()){current.finished=true;++current.sums.scenes;}}
void pause(){if(current.active&&owner!=thread_id())return;paused=true;clear(false);}
void resume(){if(current.active&&owner!=thread_id())return;clear(false);paused=false;}
void reset(){if(current.active&&owner!=thread_id())return;clear(true);have_key=false;paused=false;}
uint32_t enter(Path p,Phase q){
    if(unsigned(p)>=PathCount||unsigned(q)>=PhaseCount){fault(InvalidPhase);return NoToken;}
    return enter_state((unsigned(p)+1)|(unsigned(q)<<4));
}
uint32_t enter(Phase q){
    if(unsigned(q)>=PhaseCount){fault(InvalidPhase);return NoToken;}
    return enter_state((path_word()?path_word():unsigned(OtherDraw)+1)|(unsigned(q)<<4));
}
void leave(uint32_t token){
    if(token==NoToken||!ours()||(token>>16)!=epoch)return;
    const unsigned previous=token&65535U;
    if(((previous>>6)&63U)+1!=depth()){current.sums.errors|=ScopeOrder;return;}
    if((state&63U)!=(previous&63U))charge(clock_us());
    state=previous;
}
void set_phase(Phase q){
    if(!ours())return;
    if(unsigned(q)>=PhaseCount||!path_word()){fault(InvalidPhase);return;}
    if(unsigned(q)==phase_word())return;
    charge(clock_us());state=(state&~48U)|(unsigned(q)<<4);
}
void count(Counter c,uint32_t n){
    if(!ours())return;
    if(unsigned(c)>=CounterCount){fault(InvalidPhase);return;}
    add(current.sums.counters[path_word()?path_word()-1:unsigned(OtherDraw)][c],n);
}
void fault(Error e){if(ours())current.sums.errors|=unsigned(e);}
void begin_setup(){
    if(!ours())return;
    if(current.in_setup){fault(ScopeOrder);return;}
    current.setup_token=enter(RenderOther);current.setup_begin=current.last;current.in_setup=true;
}
void end_setup(){
    if(!ours()||!current.in_setup)return;
    leave(current.setup_token);
    if(current.last>=current.setup_begin)add(current.sums.setup_us,current.last-current.setup_begin);
    else fault(ClockReversed);
    current.in_setup=false;
}
uint64_t render_begin(){return ours()?clock_us():UINT64_MAX;}
void render_end(uint64_t stamp){
    if(!ours()||stamp==UINT64_MAX||stamp<current.begin)return;
    const uint64_t now=clock_us();
    if(now<stamp)fault(ClockReversed);else add(current.sums.render_us,now-stamp);
}
int snapshot(Snapshot* out){if(!have_sealed)return 0;if(out)*out=sealed;return 1;}
int summary(char* out,unsigned cap){
    if(!cap)return 0;
    if(!have_sealed)return snprintf(out,cap,"DSA24 collecting %u drawn ticks",unsigned(RE4DC_DRAW_SETUP_AUDIT_WINDOW));
    const auto& s=sealed;
    return snprintf(out,cap,"DSA24 q=%u r=%03x t=%u d=%u setup/t=%u render/t=%u draw/d=%u outside/t=%u tri=%llu/%llu err=%x pm=%s gaps=%u",
        s.sequence,s.identity[0],s.ticks,s.drawn,mean(s.setup_us,s.ticks),mean(s.render_us,s.ticks),
        mean(named_us(s),s.drawn),mean(s.outside_us,s.ticks),
        (unsigned long long)total_counter(s,TrianglesIn),(unsigned long long)total_counter(s,TrianglesOut),s.errors,
        pm_status(s.pm_qualification),s.pm_gaps);
}
unsigned line_count(){return 10+PathCount*4;}
int format_line(unsigned row,char* out,unsigned cap){
    if(!cap)return 0;out[0]=0;
    if(!have_sealed)return row?0:summary(out,cap);
    const auto& s=sealed;
    if(row==0)return snprintf(out,cap,"DSA24 #%u room=%03x ticks=%u drawn=%u scenes=%u attempts=%u skip=%u err=%x",s.sequence,s.identity[0],s.ticks,s.drawn,s.scenes,s.attempts,s.skipped,s.errors);
    if(row==1)return snprintf(out,cap,"Inclusive us/tick: legacy setup=%u Render()=%u wall=%u max=%llu",mean(s.setup_us,s.ticks),mean(s.render_us,s.ticks),mean(s.wall_us,s.ticks),(unsigned long long)s.max_tick_us);
    if(row==2)return snprintf(out,cap,"Exclusive us/drawn tick: WORK CLIP SUBMIT. At least one finished scene; not display flips.");
    if(row>=3&&row<3+PathCount){
        const unsigned p=row-3;return snprintf(out,cap,"%-12s %u %u %u",paths[p],mean(s.phase_us[p][Work],s.drawn),mean(s.phase_us[p][Clip],s.drawn),mean(s.phase_us[p][Submit],s.drawn));
    }
    row-=3+PathCount;
    if(row==0)return snprintf(out,cap,"Raw us: named=%llu outside=%llu wall=%llu sum_ok=%u",(unsigned long long)named_us(s),(unsigned long long)s.outside_us,(unsigned long long)s.wall_us,named_us(s)+s.outside_us==s.wall_us);
    if(row==1)return snprintf(out,cap,"PMU ev=%u ctl=%s samples=%u gaps=%u wrap=%u (CPU-wide; observer/IRQ included)",s.pm_event,pm_status(s.pm_qualification),s.pm_samples,s.pm_gaps,s.pm_wraps);
    if(row>=2&&row<2+PathCount){
        const unsigned p=row-2;
        if(!s.pm_samples)return snprintf(out,cap,"PM %-12s NA (run PM14 controls first)",paths[p]);
        return snprintf(out,cap,"PM %-12s %llu %llu %llu per draw%s",paths[p],
            (unsigned long long)(s.phase_events[p][0]/s.drawn),(unsigned long long)(s.phase_events[p][1]/s.drawn),(unsigned long long)(s.phase_events[p][2]/s.drawn),s.pm_gaps?" INCOMPLETE":"");
    }
    row-=2+PathCount;
    if(row==0)return snprintf(out,cap,"Raw counts per path: model calls/parts, tri IN/OUT, clip tri/rebuild/strips, gathered vertices");
    if(row>=1&&row<1+PathCount){
        const unsigned p=row-1;const auto* c=s.counters[p];
        return snprintf(out,cap,"%-12s %llu/%llu tri=%llu/%llu clip=%llu/%llu/%llu gather=%llu",paths[p],
            (unsigned long long)c[Models],(unsigned long long)c[Parts],(unsigned long long)c[TrianglesIn],(unsigned long long)c[TrianglesOut],
            (unsigned long long)c[ClipTriangles],(unsigned long long)c[ClipRebuilds],(unsigned long long)c[ClipStrips],(unsigned long long)c[StreamGatherVertices]);
    }
    row-=1+PathCount;
    if(row==0)return snprintf(out,cap,"XLU sent/view-overlap are triangles; overlap is conservative screen coverage, not depth visibility.");
    if(row>=1&&row<1+PathCount){
        const unsigned p=row-1;return snprintf(out,cap,"%-12s XLU=%llu/%llu unsupported=%llu",paths[p],(unsigned long long)s.counters[p][XluSubmitted],(unsigned long long)s.counters[p][XluViewOverlap],(unsigned long long)s.counters[p][Unsupported]);
    }
    row-=1+PathCount;
    if(row==0)return snprintf(out,cap,"Identity view=%u PVS=%u opq=%u xlu=%u shell=%u epoch=%u",s.identity[1],s.identity[2],s.identity[3],s.identity[4],s.identity[5],s.identity[6]);
    if(row==1)return snprintf(out,cap,"Window ticks=%u-%u; paired observer OFF is required for performance acceptance.",s.first_tick,s.last_tick);
    if(row==2)return snprintf(out,cap,"Frame begin includes PVR waits; submit includes SQ/TA backpressure. No GPU-only attribution.");
    return 0;
}
} }
