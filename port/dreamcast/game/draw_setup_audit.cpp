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
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
extern "C" unsigned re4dc_dsa28_model_key(const void*);  // model_bridge.cpp
#endif
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
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
// Per-model rows for the open window (by kind/id/type key), top 8 sealed.
struct ModelRow{uint32_t key,calls,parts,tin,tout,xtris,lights;uint32_t paths;float xpx;uint64_t us;};
#ifndef RE4DC_DSA_XLU28_EVERY
#define RE4DC_DSA_XLU28_EVERY 8
#endif
#if RE4DC_DSA_XLU28_EVERY < 1 || RE4DC_DSA_XLU28_EVERY > 16
#error DRAW_SETUP_AUDIT_XLU_EVERY must be 1..16
#endif
unsigned x28_phase;
// Per-tick float sums (one conversion per tick at finish, not per strip).
float acc_area[PathCount][3];unsigned acc_tris[PathCount];
void acc_flush(){
    for(unsigned p=0;p<PathCount;++p){
        for(unsigned c=0;c<3;++c){current.sums.counters[p][AreaOpaque+c]+=uint64_t(acc_area[p][c]+0.5f);acc_area[p][c]=0.0f;}
        current.sums.counters[p][AreaTriangles]+=acc_tris[p];acc_tris[p]=0;
    }
}
enum{ModelRows=32,ModelTop=8};
unsigned x28_first(){return 10U+PathCount*4U;}  // the Build 24 rows come first
ModelRow mrows[ModelRows],mtop[ModelTop];
unsigned nmrows,nmtop,mdepth;int mcur=-1;uint64_t mt0;
void models_clear(){nmrows=0;mcur=-1;}
void models_seal(){
    nmtop=0;
    for(unsigned k=0;k<ModelTop;++k){
        int best=-1;
        for(unsigned i=0;i<nmrows;++i)if(mrows[i].calls && (best<0||mrows[i].us>mrows[best].us))best=int(i);
        if(best<0)break;
        mtop[nmtop++]=mrows[best];mrows[best].calls=0;
    }
    models_clear();
}
#if defined(RE4DC_DSA_OCC28) && RE4DC_DSA_OCC28
enum{GridW=40,GridH=30,OccRecords=2048};
float grid[GridW*GridH];
struct OccRecord{uint8_t x0,y0,x1,y1,path,cls;float z,area;};
OccRecord records[OccRecords];
unsigned nrecords;uint64_t occ_eval_us,occ_eval_sealed;
void occ_reset(){for(unsigned i=0;i<GridW*GridH;++i)grid[i]=-1.0e30f;nrecords=0;}
unsigned cell_x(float x){return x<=0.0f?0U:(x>=639.0f?unsigned(GridW-1):unsigned(x)>>4);}
unsigned cell_y(float y){return y<=0.0f?0U:(y>=479.0f?unsigned(GridH-1):unsigned(y)>>4);}
// Every recorded TR/PT triangle: hidden when each cell of its box holds an
// opaque depth nearer than the triangle's nearest corner. Charged to the
// recording path. Its own time is reported as eval_us (it lands in the next
// tick's outside time, not in any named path).
void occ_eval(){
    const uint64_t t0=clock_us();
    for(unsigned r=0;r<nrecords;++r){
        const OccRecord& o=records[r];bool hidden=true;
        for(unsigned y=o.y0;y<=o.y1 && hidden;++y)for(unsigned x=o.x0;x<=o.x1;++x)if(!(grid[y*GridW+x]>o.z)){hidden=false;break;}
        auto* c=current.sums.counters[o.path];
        const uint64_t px=uint64_t(o.area+0.5f);
        ++c[OccTested];c[OccTestedPixels]+=px;
        if(hidden){++c[OccHidden];c[OccHiddenPixels]+=px;}
    }
    nrecords=0;
    const uint64_t t1=clock_us();
    if(t1>=t0)occ_eval_us+=t1-t0;
}
#endif
#endif
void clear(bool erase_snapshot){
    current=Frame{};window=Snapshot{};state=0;advance_epoch();
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
    models_clear();
#if defined(RE4DC_DSA_OCC28) && RE4DC_DSA_OCC28
    occ_eval_us=0;
#endif
#endif
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
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
    if(x28::sample)acc_flush();
#endif
#if defined(RE4DC_DSA_OCC28) && RE4DC_DSA_OCC28
    if(x28::sample)occ_eval();
#endif
    charge(now);
    if(depth()||current.in_setup)current.sums.errors|=Incomplete;
    if(now<current.begin)current.sums.errors|=ClockReversed;
    const uint64_t wall=now>=current.begin?now-current.begin:0;
    if(!window.ticks)window.first_tick=current.tick;
    window.last_tick=current.tick;++window.ticks;
    window.drawn+=current.finished;window.attempts+=current.attempt;
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
    window.sampled+=current.finished && x28::sample;
#endif
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
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
        models_seal();
#if defined(RE4DC_DSA_OCC28) && RE4DC_DSA_OCC28
        occ_eval_sealed=occ_eval_us;occ_eval_us=0;
#endif
#endif
#if defined(RE4DC_BARN28_DIAG) && RE4DC_BARN28_DIAG
        // BARN28_DIAG (barn28.mk): every page row in the log too (Flycast runs read the per-path rows).
        for(unsigned i=0;i<line_count();++i){if(format_line(i,row,sizeof(row))>0)log_line(row);}
#elif defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
        // Once per sealed window: the XLU28 rows into the RAM log (Flycast
        // evidence); the QA page and link telemetry read the same rows.
        for(unsigned i=x28_first();i<line_count();++i)if(format_line(i,row,sizeof(row))>0)log_line(row);
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
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
    x28::sample=++x28_phase>=RE4DC_DSA_XLU28_EVERY;
    if(x28::sample)x28_phase=0;
    for(unsigned q=0;q<PathCount;++q){acc_tris[q]=0;for(unsigned c=0;c<3;++c)acc_area[q][c]=0.0f;}
#if defined(RE4DC_DSA_OCC28) && RE4DC_DSA_OCC28
    if(x28::sample)occ_reset();
#endif
#endif
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
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
    if(mcur>=0){
        ModelRow& m=mrows[mcur];
        if(c==Parts)m.parts+=n;else if(c==TrianglesIn)m.tin+=n;else if(c==TrianglesOut)m.tout+=n;
        else if(c==XluSubmitted)m.xtris+=n;
    }
#endif
}
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
namespace x28 {
bool sample;
void add(unsigned cls,float area,unsigned triangles){
    if(!ours()||cls>2U)return;
    const unsigned p=path_word()?path_word()-1:unsigned(OtherDraw);
    acc_area[p][cls]+=area;acc_tris[p]+=triangles;
    if(cls==Tr && mcur>=0)mrows[mcur].xpx+=area;
}
#if defined(RE4DC_DSA_OCC28) && RE4DC_DSA_OCC28
void occ(unsigned cls,float ax,float ay,float az,float bx,float by,float bz,float qx,float qy,float qz,float area){
    if(!ours())return;
    float x0=ax<bx?ax:bx;x0=x0<qx?x0:qx;float x1=ax>bx?ax:bx;x1=x1>qx?x1:qx;
    float y0=ay<by?ay:by;y0=y0<qy?y0:qy;float y1=ay>by?ay:by;y1=y1>qy?y1:qy;
    if(x1<0.0f||y1<0.0f||x0>640.0f||y0>480.0f)return;
    const unsigned c0=cell_x(x0),c1=cell_x(x1),r0=cell_y(y0),r1=cell_y(y1);
    if(cls==Op){
        // Cells whose centre lies inside the triangle take its farthest depth.
        float zf=az<bz?az:bz;zf=zf<qz?zf:qz;
        const float s=((bx-ax)*(qy-ay)-(by-ay)*(qx-ax))<0.0f?-1.0f:1.0f;
        for(unsigned r=r0;r<=r1;++r){
            const float py=float(r*16U+8U);
            for(unsigned k=c0;k<=c1;++k){
                const float px=float(k*16U+8U);
                const float e0=s*((bx-ax)*(py-ay)-(by-ay)*(px-ax));
                const float e1=s*((qx-bx)*(py-by)-(qy-by)*(px-bx));
                const float e2=s*((ax-qx)*(py-qy)-(ay-qy)*(px-qx));
                if(e0>=0.0f&&e1>=0.0f&&e2>=0.0f){float& g=grid[r*GridW+k];if(zf>g)g=zf;}
            }
        }
        return;
    }
    const unsigned path=path_word()?path_word()-1:unsigned(OtherDraw);
    if(nrecords>=OccRecords){++current.sums.counters[path][OccLost];return;}
    float zn=az>bz?az:bz;zn=zn>qz?zn:qz;
    records[nrecords++]=OccRecord{uint8_t(c0),uint8_t(r0),uint8_t(c1),uint8_t(r1),uint8_t(path),uint8_t(cls),zn,area};
}
#endif
void model_enter(const void* model){
    if(mdepth++ || !ours())return;
    const unsigned key=re4dc_dsa28_model_key(model);
    int row=-1;
    for(unsigned i=0;i<nmrows;++i)if(mrows[i].key==key){row=int(i);break;}
    if(row<0){
        if(nmrows<ModelRows){row=int(nmrows++);mrows[row]=ModelRow{};mrows[row].key=key;}
        else row=ModelRows-1;  // full: the last row absorbs the rest
    }
    mcur=row;++mrows[row].calls;mt0=clock_us();
}
void model_leave(){
    if(!mdepth)return;
    if(--mdepth || mcur<0)return;
    const uint64_t now=clock_us();
    if(now>=mt0)mrows[mcur].us+=now-mt0;
    mcur=-1;
}
void light(unsigned path,unsigned lights){
    if(mcur<0||path>3U)return;
    ModelRow& m=mrows[mcur];m.paths|=1U<<path;if(lights>m.lights)m.lights=lights;
}
}
#endif
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
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
#if defined(RE4DC_DSA_OCC28) && RE4DC_DSA_OCC28
enum{X28Occ=1+PathCount};
#else
enum{X28Occ=0};
#endif
enum{X28Rows=1+PathCount+1+X28Occ+1+ModelTop};
unsigned line_count(){return x28_first()+X28Rows;}
namespace {
// Pixels per drawn tick as screens x100 (640x480 = 307200 px).
unsigned screens100(uint64_t px,unsigned drawn){return drawn?unsigned((px*100U+153600U)/307200U/drawn):0U;}
int x28_line(unsigned row,char* out,unsigned cap){
    const auto& s=sealed;const unsigned d=s.sampled,dt=s.drawn;
    if(row==0)return snprintf(out,cap,"XLU28 px/tick OP PT TR (clamped, front faces) over %u sampled of %u drawn; sc=screens x100; tri=measured/out",d,dt);
    --row;
    if(row<PathCount){
        const auto* c=s.counters[row];
        if(!c[AreaTriangles]&&!c[TrianglesOut])return 0;
        return snprintf(out,cap,"XA %-12s op=%u pt=%u tr=%u sc=%u/%u/%u tri=%u/%u",paths[row],mean(c[AreaOpaque],d),mean(c[AreaPunch],d),
            mean(c[AreaTranslucent],d),screens100(c[AreaOpaque],d),screens100(c[AreaPunch],d),screens100(c[AreaTranslucent],d),
            mean(c[AreaTriangles],d),mean(c[TrianglesOut],dt));
    }
    row-=PathCount;
    if(row==0){
        uint64_t op=0,pt=0,tr=0;for(unsigned p=0;p<PathCount;++p){op+=s.counters[p][AreaOpaque];pt+=s.counters[p][AreaPunch];tr+=s.counters[p][AreaTranslucent];}
        return snprintf(out,cap,"XA TOTAL        op=%u pt=%u tr=%u sc=%u/%u/%u overdraw_xlu=%u.%02u",mean(op,d),mean(pt,d),mean(tr,d),
            screens100(op,d),screens100(pt,d),screens100(tr,d),screens100(pt+tr,d)/100U,screens100(pt+tr,d)%100U);
    }
    --row;
#if defined(RE4DC_DSA_OCC28) && RE4DC_DSA_OCC28
    if(row==0){
        uint64_t lost=0;for(unsigned p=0;p<PathCount;++p)lost+=s.counters[p][OccLost];
        return snprintf(out,cap,"XO grid40x30 hidden = every box cell has nearer opaque; eval_us/d=%u lost/d=%u",mean(occ_eval_sealed,d),mean(lost,d));
    }
    --row;
    if(row<PathCount){
        const auto* c=s.counters[row];
        if(!c[OccTested])return 0;
        return snprintf(out,cap,"XO %-12s hid tri=%u/%u px=%u/%u",paths[row],mean(c[OccHidden],d),mean(c[OccTested],d),
            mean(c[OccHiddenPixels],d),mean(c[OccTestedPixels],d));
    }
    row-=PathCount;
#endif
    if(row==0)return snprintf(out,cap,"XM top%u by us/d: calls parts tri in/out xlu tri/px L=P probe B fold X exact C flat + lights",nmtop);
    --row;
    if(row>=nmtop)return 0;
    const ModelRow& m=mtop[row];
    char name[12];const unsigned k=m.key>>16,id=(m.key>>8)&255U,ty=m.key&255U;
    if(m.key==0xffffffU)snprintf(name,sizeof(name),"other");
    else if(k==0)snprintf(name,sizeof(name),"em%02x",id);
    else if(k==1)snprintf(name,sizeof(name),"om%02x",id);
    else snprintf(name,sizeof(name),"k%u:%02x",k,id);
    char lp[6];unsigned n=0;
    static const char codes[4]={'P','B','X','C'};
    for(unsigned b=0;b<4;++b)if(m.paths&(1U<<b))lp[n++]=codes[b];
    if(!n)lp[n++]='-';
    lp[n]=0;
    return snprintf(out,cap,"XM %-6s t%02x us=%u c=%u p=%u tri=%u/%u x=%u/%u L=%s%u",name,ty,mean(m.us,dt),mean(m.calls,dt),mean(m.parts,dt),
        mean(m.tin,dt),mean(m.tout,dt),mean(m.xtris,dt),d?unsigned(m.xpx/float(d)+0.5f):0U,lp,m.lights);
}
}
#else
unsigned line_count(){return 10+PathCount*4;}
#endif
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
#if defined(RE4DC_DSA_XLU28) && RE4DC_DSA_XLU28
    if(row>=3)return x28_line(row-3,out,cap);
#endif
    return 0;
}
} }
